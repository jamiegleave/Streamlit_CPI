import streamlit as st
import pandas as pd
import json
from unified_cpi_system import UnifiedCPIManager

# Configure the page
st.set_page_config(
    page_title="CPI Data Explorer",
    layout="wide"
)

# Add title
st.title("Consumer Price Index - Headline & Weights")

# Initialize session state for storing the data
if 'data_loaded' not in st.session_state:
    st.session_state.data_loaded = False

# Load country mappings
@st.cache_data
def load_country_mappings():
    try:
        with open('cpi_weight_countries.json', 'r') as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Error loading country mappings: {str(e)}")
        return None

# Load data for selected countries
@st.cache_data(ttl=3600)  # Cache for 1 hour
def load_data(country_codes, start_date):
    try:
        manager = UnifiedCPIManager(fred_api_key="899901ba06f09b9961a73113b1834a15")
        return manager.get_complete_cpi_data(countries=country_codes, start_date=start_date)
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return None

# Load country mappings
country_mappings = load_country_mappings()

if country_mappings:
    # Create a dictionary of Country: Code for the dropdown
    country_dict = {item['Country']: item['Code'] for item in country_mappings}
    
    # Country selector
    selected_countries = st.multiselect(
        "Select Countries to Analyze",
        options=sorted(country_dict.keys()),
        help="Select countries to include in the analysis"
    )
    
    # Date range selector
    start_date = st.date_input(
        "Select Start Date",
        value=pd.to_datetime("2020-01-01"),
        help="Select the start date for CPI data"
    )
    
    # Submit button
    if st.button("Load Data", disabled=len(selected_countries) == 0):
        selected_codes = [country_dict[country] for country in selected_countries]
        
        with st.spinner(f'Loading data for {", ".join(selected_countries)}...'):
            data = load_data(selected_codes, start_date.strftime("%Y-%m-%d"))
            if data is not None:
                st.session_state.data = data
                st.session_state.data_loaded = True
                st.success("Data loaded successfully!")
                st.experimental_rerun()

    # Only show filters and data if data has been loaded
    if st.session_state.data_loaded:
        data = st.session_state.data
        
        # Create tabs for CPI and Weights data
        tab1, tab2 = st.tabs(["CPI Data", "Weights Data"])
        
        with tab1:
            st.header("CPI Analysis")
            
            # CPI data filters
            st.sidebar.header("CPI Data Filters")
            
            # Filter CPI data by date range
            cpi_df = data['cpi']
            date_range = st.sidebar.date_input(
                "Select Date Range",
                value=(cpi_df['date'].min(), cpi_df['date'].max()),
                key="cpi_date_range"
            )
            
            # Apply date filter
            mask = (cpi_df['date'] >= pd.Timestamp(date_range[0])) & \
                   (cpi_df['date'] <= pd.Timestamp(date_range[1]))
            filtered_cpi = cpi_df[mask]
            
            # Display CPI statistics
            st.subheader("CPI Summary Statistics")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric(
                    "Average Inflation Rate",
                    f"{filtered_cpi['value'].mean():.1f}%"
                )
            
            with col2:
                st.metric(
                    "Maximum Inflation Rate",
                    f"{filtered_cpi['value'].max():.1f}%"
                )
            
            with col3:
                st.metric(
                    "Minimum Inflation Rate",
                    f"{filtered_cpi['value'].min():.1f}%"
                )
            
            # Display CPI data
            st.subheader("Detailed CPI Data")
            st.dataframe(
                filtered_cpi.sort_values(['country', 'date'])
                .style.format({
                    'value': '{:.1f}%',
                    'date': lambda x: x.strftime('%Y-%m-%d')
                }),
                use_container_width=True
            )
        
        with tab2:
            st.header("Weights Analysis")
            
            # Weights data filters
            st.sidebar.header("Weights Data Filters")
            
            # Year filter
            weights_df = data['weights']
            years = sorted(weights_df['Year'].unique())
            selected_years = st.sidebar.select_slider(
                "Select Year Range",
                options=years,
                value=(min(years), max(years)),
                key="weights_year_range"
            )
            
            # Category filter
            categories = sorted(weights_df['Category_Description'].unique())
            selected_categories = st.sidebar.multiselect(
                "Select Categories",
                categories,
                default=categories,
                key="weights_categories"
            )
            
            # Filter weights data
            mask = (
                weights_df['Year'].between(selected_years[0], selected_years[1]) &
                weights_df['Category_Description'].isin(selected_categories)
            )
            filtered_weights = weights_df[mask]
            
            # Display weights statistics
            st.subheader("Weights Summary Statistics")
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric(
                    "Total Records",
                    len(filtered_weights)
                )
        
            with col2:
                st.metric(
                    "Number of Countries",
                    len(filtered_weights['Country'].unique())
                )
                       
            # Display filtered weights data
            st.subheader("Detailed Weights Data")
            st.dataframe(
                filtered_weights.sort_values(['Country', 'Year', 'Category_Description'])
                .style.format({'Weight': '{:.1f}'}),
                use_container_width=True
            )
            
            # Add download buttons for both datasets
            col1, col2 = st.columns(2)
            with col1:
                csv_weights = filtered_weights.to_csv(index=False)
                st.download_button(
                    label="Download weights data as CSV",
                    data=csv_weights,
                    file_name="cpi_weights_filtered.csv",
                    mime="text/csv"
                )
            
            with col2:
                csv_cpi = filtered_cpi.to_csv(index=False)
                st.download_button(
                    label="Download CPI data as CSV",
                    data=csv_cpi,
                    file_name="cpi_data_filtered.csv",
                    mime="text/csv"
                )
        
        # Add button to reset and select new countries
        if st.button("Select Different Countries"):
            st.session_state.data_loaded = False
            st.experimental_rerun()
            
    elif len(selected_countries) == 0:
        st.info("Please select at least one country and click 'Load Data'")
else:
    st.error("Failed to load country mappings. Please check the JSON file.")