"""
unified_cpi_system.py
A comprehensive module for fetching and managing CPI data and weights from multiple sources.
"""
import logging
import os
from datetime import datetime, timedelta
import pandas as pd
import requests
import time
from functools import wraps
from pathlib import Path
import tempfile
from typing import Dict, Optional, Union, List
from requests.exceptions import RequestException
from cachetools import TTLCache
from fredapi import Fred
import re
from io import StringIO

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DataAcquisitionError(Exception):
    """Base exception class for data acquisition errors."""
    pass

class NetworkError(DataAcquisitionError):
    """Raised when network-related errors occur."""
    pass

class DataValidationError(DataAcquisitionError):
    """Raised when data validation fails."""
    pass

def retry_on_failure(max_retries: int = 3, delay: int = 1):
    """Decorator for implementing retry logic."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    logger.warning(f"Attempt {attempt + 1} failed: {str(e)}")
                    if attempt < max_retries - 1:
                        time.sleep(delay * (attempt + 1))
            raise last_exception
        return wrapper
    return decorator

class ONSWeightsLoader:
    """Handler for downloading and processing ONS CPI weights data."""
    
    def __init__(self, cache_dir: Optional[str] = None):
        self.cache_dir = cache_dir or tempfile.gettempdir()
        self.cache_duration = timedelta(hours=24)
    
    @retry_on_failure()
    def download_excel(self, url: str) -> Path:
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            cache_file = Path(self.cache_dir) / f"ons_data_{hash(url)}.xlsx"
            
            with open(cache_file, 'wb') as f:
                f.write(response.content)
            
            return cache_file
            
        except RequestException as e:
            raise NetworkError(f"Failed to download ONS data: {str(e)}")
    
    def parse_excel(self, file_path: Path) -> pd.DataFrame:
        """Parse ONS Excel file into DataFrame."""
        try:
            # First read the year row (Row 3)
            year_row = pd.read_excel(
                file_path,
                sheet_name='W3-CPIH',
                skiprows=2,
                nrows=1,
                usecols='B:AB'
            )
            
            # Then read the data
            raw_df = pd.read_excel(
                file_path,
                sheet_name='W3-CPIH',
                skiprows=4,
                nrows=13,
                usecols='B:AB'
            )
            
            # Extract years from year row, handling split years
            years = []
            for col in year_row.columns[2:]:  # Skip Code and Description columns
                year_val = year_row.iloc[0, year_row.columns.get_loc(col)]
                if pd.notna(year_val):
                    # Extract year using regex to handle different formats
                    year_match = re.search(r'(\d{4})', str(year_val))
                    if year_match:
                        years.append(year_match.group(1))
            
            logger.info(f"Processing ONS weights data for years: {min(years)} to {max(years)}")
            
            # Create mapping of original columns to extracted years
            year_mapping = {
                col: year for col, year in zip(raw_df.columns[2:], years)
            }
            
            # Rename columns using the mapping
            new_columns = ['Code', 'Description'] + [year_mapping[col] for col in raw_df.columns[2:]]
            raw_df.columns = new_columns
            raw_df = raw_df.loc[:,~raw_df.columns.duplicated()]
            
            logger.info(f"After cleanup columns: {raw_df.columns.tolist()}")
            
            # Get the overall index code from the first row
            overall_index_code = str(raw_df.iloc[0, 0]).strip()
            
            # Create a new DataFrame excluding the overall index row
            df = raw_df[raw_df.Code != overall_index_code].copy()
            
            # Clean up the description column
            df.loc[:, 'Description'] = df['Description'].str.strip()
            
            # Get unique years and use the latest value for each year
            years = sorted(set(str(col) for col in df.columns if str(col).isdigit()))
            logger.info(f"Year columns found: {years}")
            
            # For each year, if there are multiple columns, use the latest value
            final_data = []
            for code_idx, code_row in df.iterrows():
                for year in years:
                    matching_cols = [col for col in df.columns if str(col) == year]
                    if matching_cols:
                        final_data.append({
                            'Code': code_row['Code'],
                            'Description': code_row['Description'],
                            'Year': int(year),
                            'Weight': float(code_row[matching_cols[-1]])  # Use last column for each year
                        })
            
            # Create DataFrame from processed data
            years_df = pd.DataFrame(final_data)
            
            # Add source and country
            years_df = years_df.assign(
                Source='ONS',
                Country='UK'
            )
            
            # Rename columns to match expected format
            years_df = years_df.rename(columns={
                'Code': 'Category_Code',
                'Description': 'Category_Description'
            })
            
            # Remove any rows with missing weights
            years_df = years_df.dropna(subset=['Weight'])
            
            # Validate the data
            self._validate_weights_data(years_df)
            
            return years_df
            
        except Exception as e:
            logger.error(f"Excel parsing error. Exception: {str(e)}")
            logger.error(f"Exception type: {type(e)}")
            raise DataValidationError(f"Failed to parse ONS Excel file: {str(e)}")
    
    def _validate_weights_data(self, df: pd.DataFrame) -> None:
        """Validate the weights data from ONS."""
        # Check for required columns
        required_columns = ['Category_Code', 'Category_Description', 'Year', 'Weight', 'Source', 'Country']
        missing_cols = [col for col in required_columns if col not in df.columns]
        if missing_cols:
            raise DataValidationError(f"Missing required columns: {missing_cols}")
        
        # Validate we have exactly 12 categories for each year
        for year in df['Year'].unique():
            year_categories = df[df['Year'] == year]['Category_Code'].nunique()
            if year_categories != 12:
                raise DataValidationError(f"Expected 12 categories for year {year}, found {year_categories}")
        
        # Validate weights sum to approximately 1000 per year
        for year in df['Year'].unique():
            year_sum = df[df['Year'] == year]['Weight'].sum()
            if not (995 <= year_sum <= 1005):
                logger.warning(
                    f"Weights for year {year} sum to {year_sum:.2f}, expected ~1000"
                )
        
        # Check for invalid weights
        if (df['Weight'] < 0).any():
            raise DataValidationError("Negative weights detected")
        
        # Check reasonable upper bound for individual weights
        max_weight = df['Weight'].max()
        if max_weight > 400:  # Based on the data shown
            logger.warning(f"Unusually high weight detected: {max_weight}")
        
        # Validate year range
        min_year = df['Year'].min()
        max_year = df['Year'].max()
        current_year = datetime.now().year
        if min_year < 2000 or max_year > current_year + 1:
            raise DataValidationError(f"Invalid year range: {min_year} to {max_year}")
        
        # Check for source consistency
        if not (df['Source'] == 'ONS').all():
            raise DataValidationError("Inconsistent data source detected")
        
        # Check for country consistency
        if not (df['Country'] == 'UK').all():
            raise DataValidationError("Inconsistent country detected")
        
        # Check for duplicates
        duplicates = df.duplicated(subset=['Category_Code', 'Year'], keep=False)
        if duplicates.any():
            duplicate_rows = df[duplicates][['Category_Code', 'Year']]
            raise DataValidationError(
                f"Duplicate entries found for category-year combinations:\n{duplicate_rows}"
            )

class EurostatWeightsLoader:
    """Handler for fetching CPI weights data from Eurostat."""
    
    def __init__(self):
        self.base_url = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data"
        self.dataset = "prc_hicp_inw"
        self.cache = TTLCache(maxsize=100, ttl=3600)
        
        self.logger = logging.getLogger(__name__)
        
        # Map COICOP codes to ONS categories
        self.category_mapping = {
            'CP01': ('L5CZ', '01    Food and non-alcoholic beverages'),
            'CP02': ('L5D2', '02    Alcoholic beverages and tobacco'),
            'CP03': ('L5D3', '03    Clothing and footwear'),
            'CP04': ('L5D4', '04    Housing, water, electricity, gas and other fuels'),
            'CP05': ('L5D5', '05    Furniture, household equipment and maintenance'),
            'CP06': ('L5D6', '06    Health'),
            'CP07': ('L5D7', '07    Transport'),
            'CP08': ('L5D8', '08    Communication'),
            'CP09': ('L5D9', '09    Recreation and culture'),
            'CP10': ('L5DA', '10    Education'),
            'CP11': ('L5DB', '11    Restaurants and hotels'),
            'CP12': ('L5DC', '12    Miscellaneous goods and services')
        }

    def _fetch_category_timeseries(self, country: str, coicop: str) -> Dict[int, float]:
        """Fetch weight data time series for a single category and country."""
        try:
            params = {
                'format': 'JSON',
                'lang': 'en',
                'geo': country,
                'coicop': coicop
            }
            
            url = f"{self.base_url}/{self.dataset}"
            
            self.logger.info(f"Fetching {coicop} data for {country}")
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # Get time index mapping
            time_index = data['dimension']['time']['category']['index']
            
            # Create year to value mapping
            weights = {}
            for year, position in time_index.items():
                weight = data['value'].get(str(position))
                if weight is not None:
                    weights[int(year)] = float(weight)
            
            return weights
            
        except Exception as e:
            self.logger.error(f"Failed to fetch {coicop} data for {country}: {str(e)}")
            raise

    def _fetch_single_country(self, country: str) -> pd.DataFrame:
        """Fetch HICP weights data for all categories for a single country."""
        try:
            records = []
            
            # Fetch data for each COICOP category
            for coicop, (ons_code, category_desc) in self.category_mapping.items():
                try:
                    weights = self._fetch_category_timeseries(country, coicop)
                    
                    # Add records for each year
                    for year, weight in weights.items():
                        records.append({
                            'Category_Code': ons_code,
                            'Category_Description': category_desc,
                            'Year': year,
                            'Weight': weight,
                            'Source': 'Eurostat',
                            'Country': country
                        })
                    
                except Exception as e:
                    self.logger.error(f"Error fetching {coicop} for {country}: {str(e)}")
                    continue
            
            if not records:
                raise ValueError(f"No data retrieved for {country}")
                
            # Create DataFrame with specific column order to match format
            df = pd.DataFrame(records, columns=[
                'Category_Code',
                'Category_Description',
                'Year',
                'Weight',
                'Source',
                'Country'
            ])
            
            # Format Weight column to match source format
            # Use 4 decimal places for 2024, 1 decimal place for other years
            df['Weight'] = df.apply(lambda x: 
                round(x['Weight'], 4) if x['Year'] == 2024 
                else round(x['Weight'], 1), axis=1)
            
            # Sort to match source format
            df = df.sort_values(['Year', 'Category_Code']).reset_index(drop=True)
            
            # Validate the data
            self._validate_data(df)
            
            return df
            
        except Exception as e:
            self.logger.error(f"Failed to fetch data for {country}: {str(e)}")
            raise

    def fetch_hicp_weights(self, countries: List[str]) -> pd.DataFrame:
        """Fetch HICP weights data for specified countries."""
        cache_key = "-".join(sorted(countries))
        
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        country_data = []
        for country in countries:
            try:
                df = self._fetch_single_country(country)
                if not df.empty:
                    country_data.append(df)
            except Exception as e:
                self.logger.error(f"Error fetching data for {country}: {str(e)}")
                continue
        
        if not country_data:
            raise ValueError("Failed to fetch data for any country")
        
        combined_df = pd.concat(country_data, ignore_index=True)
        self.cache[cache_key] = combined_df
        
        return combined_df

    def _validate_data(self, df: pd.DataFrame) -> None:
        """Validate the transformed data meets requirements."""
        if df.empty:
            raise ValueError("No data retrieved")
            
        required_columns = ['Category_Code', 'Category_Description', 'Year', 'Weight', 'Source', 'Country']
        missing_columns = set(required_columns) - set(df.columns)
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")
        
        # Check category counts for each year
        for country in df['Country'].unique():
            for year in df['Year'].unique():
                mask = (df['Country'] == country) & (df['Year'] == year)
                category_count = df[mask]['Category_Code'].nunique()
                if category_count != len(self.category_mapping):
                    self.logger.warning(f"Missing categories for {country} in {year}: found {category_count} of {len(self.category_mapping)}")
        
        # Validate weight ranges
        if (df['Weight'] < 0).any() or (df['Weight'] > 1000).any():
            raise ValueError("Invalid weights detected (outside range 0-1000)")
        
        # Check weight sums for each year
        for country in df['Country'].unique():
            for year in df['Year'].unique():
                mask = (df['Country'] == country) & (df['Year'] == year)
                total = df[mask]['Weight'].sum()
                if not (995 <= total <= 1005):
                    self.logger.warning(f"Weights for {country} in {year} sum to {total:.1f}, expected ~1000")

class PriceIndexDataLoader:
    """Handler for fetching CPI and CPIH index values from ONS and Eurostat."""
    
    def __init__(self, fred_api_key: str):
        self.fred_api_key = fred_api_key
        self.cache = TTLCache(maxsize=100, ttl=3600)
    
    @retry_on_failure()
    def fetch_uk_cpih_data(self, start_date: str) -> pd.DataFrame:
        """Fetch UK CPIH index data from ONS API."""
        try:
            logger.info("Fetching UK CPIH data from ONS")
            BASE_URL = "https://api.beta.ons.gov.uk/v1"
            
            # Get latest version
            version_response = requests.get(
                f"{BASE_URL}/datasets/cpih01/editions/time-series/versions"
            )
            version_response.raise_for_status()
            latest_version = version_response.json()['items'][0]['version']
            
            # Get CPIH data
            response = requests.get(
                f"{BASE_URL}/datasets/cpih01/editions/time-series/versions/{latest_version}/observations",
                params={
                    "time": "*",
                    "geography": "K02000001",  # UK
                    "aggregate": "CP00"  # All items
                }
            )
            response.raise_for_status()
            
            # Process data
            records = []
            for obs in response.json()['observations']:
                records.append({
                    'date': pd.to_datetime(obs['dimensions']['Time']['label'], format='%b-%y'),
                    'value': float(obs['observation']),
                    'country': 'UK',
                    'source': 'ONS'
                })
            
            # Create and filter DataFrame
            df = pd.DataFrame(records)
            df = df[df['date'] >= pd.to_datetime(start_date)]
            logger.info(f"Successfully fetched UK CPIH data from {df['date'].min():%Y-%m} to {df['date'].max():%Y-%m}")
            return df.sort_values('date').reset_index(drop=True)
            
        except Exception as e:
            logger.error(f"Failed to fetch UK CPIH data: {str(e)}")
            raise NetworkError(f"Failed to fetch UK CPIH data: {str(e)}")

    @retry_on_failure()
    def fetch_eurostat_data(self, countries: List[str]) -> pd.DataFrame:
        """Fetch HICP index data from Eurostat."""
        base_url = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/prc_hicp_midx"
        params = {
            "format": "JSON",
            "unit": "I15",  # Index, annual average = 100
            "coicop": "CP00",
            "lang": "en"
        }
        
        all_data = []
        for country in countries:
            try:
                params["geo"] = country
                response = requests.get(base_url, params=params)
                response.raise_for_status()
                data = response.json()
                
                values = data["value"]
                time_mapping = data["dimension"]["time"]["category"]["index"]
                
                for time_str, idx in time_mapping.items():
                    if str(idx) in values:
                        all_data.append({
                            "date": pd.to_datetime(time_str),
                            "value": float(values[str(idx)]),
                            "country": country,
                            "source": "Eurostat"
                        })
            except Exception as e:
                logger.warning(f"Failed to fetch data for {country}: {str(e)}")
                continue
        
        return pd.DataFrame(all_data) if all_data else pd.DataFrame()

    def get_cpi_data(self, countries: List[str], start_date: str) -> pd.DataFrame:
        """Fetch CPI/CPIH data for specified countries."""
        uk_data = 'UK' in countries
        eurostat_countries = [c for c in countries if c != 'UK']
        dfs = []
        
        # Handle UK CPIH data
        if uk_data:
            try:
                uk_cpih_df = self.fetch_uk_cpih_data(start_date)
                if not uk_cpih_df.empty:
                    dfs.append(uk_cpih_df)
            except Exception as e:
                logger.warning(f"Failed to fetch UK CPIH data: {str(e)}")
        
        # Handle Eurostat data
        if eurostat_countries:
            try:
                eurostat_df = self.fetch_eurostat_data(eurostat_countries)
                if not eurostat_df.empty:
                    dfs.append(eurostat_df)
            except Exception as e:
                logger.warning(f"Failed to fetch Eurostat data: {str(e)}")
        
        if dfs:
            return pd.concat(dfs, ignore_index=True).sort_values(['country', 'source', 'date'])
        return pd.DataFrame()

    def calculate_cpi_rate_of_change(self, df_cpi: pd.DataFrame, time_periods: Dict[str, List[int]]) -> pd.DataFrame:
        """
        Calculate CPI rates of change for specified time periods.
        
        Args:
            df_cpi (pd.DataFrame): DataFrame containing CPI data with columns:
                - date: DateTime of the observation
                - value: CPI value
                - country: Country code
            time_periods (Dict[str, List[int]]): Dictionary mapping period names to [start_year, end_year]
                Example: {'Pre-GFC': [2000, 2009], 'Post-GFC': [2010, 2019]}
        
        Returns:
            pd.DataFrame: DataFrame with countries as index and time periods as columns,
                            containing CPI rates of change for each period
        """
        
        if df_cpi.empty:
            raise ValueError("Input DataFrame is empty")
        
        required_columns = {'date', 'value', 'country'}
        if not all(col in df_cpi.columns for col in required_columns):
            raise ValueError(f"Data must contain columns: {required_columns}")
        
        try:
            result_df = pd.DataFrame(index=df_cpi['country'].unique())
            
            for period_name, [start_year, end_year] in time_periods.items():
                rocs = []
                
                for country in result_df.index:
                    # Filter data for the specific country and time period
                    mask = (
                        (df_cpi['country'] == country) & 
                        (df_cpi['date'].dt.year >= start_year) & 
                        (df_cpi['date'].dt.year <= end_year) &
                        (df_cpi['date'].dt.month == 1)
                    )
                    period_data = df_cpi[mask]['value']
                    
                    if len(period_data) < 2:
                        logger.warning(
                            f"Insufficient data for {country} in period {period_name}. "
                            f"Setting rate of change to NaN."
                        )
                        rocs.append(float('nan'))
                    else:
                        # Calculate rate of change
                        rate_of_change = (period_data.iloc[-1] - period_data.iloc[0])/period_data.iloc[0]
                        t_elapsed = end_year - start_year
                        rocs.append(rate_of_change/t_elapsed)
                
                result_df[period_name] = rocs
            
            return result_df
            
        except Exception as e:
            raise DataValidationError(f"Failed to calculate CPI rates of change: {str(e)}")

class UnifiedCPIManager:
    """Unified manager for handling both CPI values and weights data from multiple sources."""
    
    def __init__(self, fred_api_key: str, cache_dir: Optional[str] = None):
        self.price_loader = PriceIndexDataLoader(fred_api_key)
        self.ons_weights = ONSWeightsLoader(cache_dir)
        self.eurostat_weights = EurostatWeightsLoader()
    
    def get_cpi_data(self, countries: List[str], start_date: str) -> pd.DataFrame:
        """Fetch CPI data for specified countries."""
        uk_requested = 'UK' in countries
        eurostat_countries = [c for c in countries if c != 'UK']
        dfs = []
        
        if uk_requested:
            uk_df = self.price_loader.fetch_uk_cpih_data(start_date)
            if not uk_df.empty:
                dfs.append(uk_df)
        
        if eurostat_countries:
            eurostat_df = self.price_loader.fetch_eurostat_data(eurostat_countries)
            if not eurostat_df.empty:
                dfs.append(eurostat_df)
        
        if dfs:
            return pd.concat(dfs, ignore_index=True).sort_values(['country', 'date'])
        return pd.DataFrame()
    
    def get_weights_data(self, countries: List[str]) -> pd.DataFrame:
        """Fetch weights data for specified countries."""
        try:
            # Get UK data from ONS
            ons_url = "https://www.ons.gov.uk/file?uri=/economy/inflationandpriceindices/datasets/consumerpriceinflationupdatingweightsannexatablesw1tow3/annexatablesw1tow3weights2024/annexaw1w3weights2024.xlsx"
            uk_data = self.ons_weights.parse_excel(
                self.ons_weights.download_excel(ons_url)
            )
            
            # Get EU data from Eurostat
            eu_countries = [c for c in countries if c != 'UK']
            if eu_countries:
                try:
                    eu_data = self.eurostat_weights.fetch_hicp_weights(eu_countries)
                    combined_data = pd.concat([uk_data, eu_data], ignore_index=True)
                except Exception as e:
                    logger.warning(f"Failed to fetch Eurostat weights: {str(e)}")
                    combined_data = uk_data
            else:
                combined_data = uk_data
            
            return combined_data
            
        except Exception as e:
            raise DataAcquisitionError(f"Failed to get weights data: {str(e)}")
        
    def get_rate_of_change_data(self, df_cpi: pd.DataFrame, time_periods: Dict[str, List[int]]) -> pd.DataFrame:
        """Get annualized rate of change data for the specified time periods."""
        return self.price_loader.calculate_cpi_rate_of_change(df_cpi, time_periods)
    
    def get_complete_cpi_data(self, countries: List[str], start_date: str, ratio_periods: Dict[str, List[int]]) -> Dict[str, pd.DataFrame]:
        """
        Fetch both CPI values and weights data for specified countries.
        
        Returns:
            Dictionary containing three DataFrames:
            - 'cpi': Time series of CPI values
            - 'roc': Annualized rates of change
            - 'weights': Current weights data
        """
        cpi = self.get_cpi_data(countries, start_date)

        return {
            'cpi': cpi,
            'roc': self.get_rate_of_change_data(cpi, ratio_periods),
            'weights': self.get_weights_data(countries)
        }
    
