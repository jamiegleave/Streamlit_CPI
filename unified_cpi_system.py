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
        """
        Parse ONS Excel file into DataFrame.
        Specifically handles the W1-CPI sheet, excluding the 'overall index' row
        and processing only the individual category weights.
        
        Args:
            file_path: Path to Excel file
            
        Returns:
            DataFrame with CPI weights data
            
        Raises:
            DataValidationError: If data format is invalid or unexpected
        """
        try:
            # First, read the entire relevant section to validate structure
            raw_df = pd.read_excel(
                file_path,
                sheet_name='W1-CPI',
                skiprows=4,  # Skip header rows
                nrows=13,    # Read overall index + 12 categories
                usecols='B:AB'
            )
                       
            # Validate the overall index row
            raw_df.columns = [str(i)[0:4] for i in raw_df.columns]
            raw_df.columns = ['Code', 'Description'] + raw_df.columns[2:].tolist()
            raw_df = raw_df.loc[:,~raw_df.columns.duplicated()]

            first_row_code = str(raw_df.iloc[0, 0]).strip()

            if not first_row_code.startswith('CHZQ') or abs(raw_df.iloc[0, raw_df.columns.get_loc('2024')] - 1000) > 0.1:
                raise DataValidationError("First row is not the expected overall index with value 1000")
            
            # Create a new DataFrame instead of modifying a slice
            df = raw_df[raw_df.Code!='CHZQ'].copy()
            
            # Clean up the description column
            df.loc[:, 'Description'] = df['Description'].str.strip()
            
            # Get year columns (all numeric columns except the first two)
            year_columns = [col for col in df.columns if str(col).isdigit()]
            
            # Melt the DataFrame to create the long format
            years_df = df.melt(
                id_vars=['Code', 'Description'],
                value_vars=year_columns,
                var_name='Year',
                value_name='Weight'
            )
            
            # Clean up and type the data
            years_df = years_df.assign(
                Year=lambda x: x['Year'].astype(int),
                Weight=lambda x: x['Weight'].astype(float),
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
            raise DataValidationError(f"Failed to parse ONS Excel file: {str(e)}")
    
    def _validate_weights_data(self, df: pd.DataFrame) -> None:
        """
        Validate the weights data from ONS.
        
        Args:
            df: DataFrame to validate with columns:
               - Category_Code (e.g., 'CHZR')
               - Category_Description (e.g., 'Food and non-alcoholic beverages')
               - Year (e.g., 2024)
               - Weight (e.g., 112.9084)
               - Source ('ONS')
               - Country ('UK')
            
        Raises:
            DataValidationError: If validation fails
        """
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
        
        # Validate specific category codes exist
        expected_codes = {
            'CHZR', 'CHZS', 'CHZT', 'CHZU', 'CHZV', 'CHZW',
            'CHZX', 'CHZY', 'CHZZ', 'CJUU', 'CJUV', 'CJUW'
        }
        actual_codes = set(df['Category_Code'].unique())
        missing_codes = expected_codes - actual_codes
        if missing_codes:
            raise DataValidationError(f"Missing expected category codes: {missing_codes}")
        
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
        if max_weight > 200:  # Based on historical data, no category typically exceeds 200
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
        
        # Modified description format validation
        invalid_descriptions = df[
            ~df['Category_Description'].str.match(r'^\s*(?:\d+\s+)?[A-Za-z, ]+')
        ]['Category_Description'].unique()
        if len(invalid_descriptions) > 0:
            logger.warning(f"Potentially invalid descriptions found: {invalid_descriptions}")
        
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
        
        # Map COICOP codes to ONS categories with exact description format
        self.category_mapping = {
            'CP01': ('CHZR', '01    Food and non-alcoholic beverages'),
            'CP02': ('CHZS', '02    Alcoholic beverages and tobacco'),
            'CP03': ('CHZT', '03    Clothing and footwear'),
            'CP04': ('CHZU', '04    Housing, water, electricity, gas and other fuels'),
            'CP05': ('CHZV', '05    Furniture, household equipment and maintenance'),
            'CP06': ('CHZW', '06    Health'),
            'CP07': ('CHZX', '07    Transport'),
            'CP08': ('CHZY', '08    Communication'),
            'CP09': ('CHZZ', '09    Recreation and culture'),
            'CP10': ('CJUU', '10    Education'),
            'CP11': ('CJUV', '11    Restaurants and hotels'),
            'CP12': ('CJUW', '12    Miscellaneous goods and services')
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

class CPIDataLoader:
    """Handler for fetching CPI values from FRED and Eurostat."""
    
    def __init__(self, fred_api_key: str):
        self.fred_api_key = fred_api_key
        self.fred_client = Fred(api_key=fred_api_key)
        self.cache = TTLCache(maxsize=100, ttl=3600)
    
    @retry_on_failure()
    def fetch_uk_data(self, start_date: str = '1999-01-01') -> pd.DataFrame:
        """Fetch UK CPI data from FRED."""
        try:
            uk_cpi = self.fred_client.get_series(
                'GBRCPIALLMINMEI',
                observation_start=start_date,
                frequency='m'
            )
            
            df = pd.DataFrame(uk_cpi, columns=['value'])
            df.index.name = 'date'
            df.reset_index(inplace=True)
            df['country'] = 'UK'
            df['source'] = 'FRED'
            
            # Calculate YoY change
            df['value'] = df['value'].pct_change(periods=12) * 100
            return df.dropna()
            
        except Exception as e:
            raise NetworkError(f"Failed to fetch UK CPI data: {str(e)}")

    @retry_on_failure()
    def fetch_eurostat_data(self, countries: List[str]) -> pd.DataFrame:
        """Fetch HICP data from Eurostat."""
        base_url = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/prc_hicp_mv12r"
        params = {
            "format": "JSON",
            "unit": "RCH_MV12MAVR",
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

class UnifiedCPIManager:
    """
    Unified manager for handling both CPI values and weights data from multiple sources.
    """
    
    def __init__(self, fred_api_key: str, cache_dir: Optional[str] = None):
        self.cpi_loader = CPIDataLoader(fred_api_key)
        self.ons_weights = ONSWeightsLoader(cache_dir)
        self.eurostat_weights = EurostatWeightsLoader()
        
    def get_cpi_data(self, countries: List[str], start_date: str = '1999-01-01') -> pd.DataFrame:
        """Fetch CPI data for specified countries."""
        uk_requested = 'UK' in countries
        eurostat_countries = [c for c in countries if c != 'UK']
        dfs = []
        
        if uk_requested:
            uk_df = self.cpi_loader.fetch_uk_data(start_date)
            if not uk_df.empty:
                dfs.append(uk_df)
        
        if eurostat_countries:
            eurostat_df = self.cpi_loader.fetch_eurostat_data(eurostat_countries)
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
    
    def get_complete_cpi_data(self, countries: List[str], start_date: str = '1999-01-01') -> Dict[str, pd.DataFrame]:
        """
        Fetch both CPI values and weights data for specified countries.
        
        Returns:
            Dictionary containing two DataFrames:
            - 'cpi': Time series of CPI values
            - 'weights': Current weights data
        """
        return {
            'cpi': self.get_cpi_data(countries, start_date),
            'weights': self.get_weights_data(countries)
        }
