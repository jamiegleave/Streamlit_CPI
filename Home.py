import streamlit as st
import pandas as pd
import json
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, List, Tuple, Optional
from unified_cpi_system import UnifiedCPIManager
from dotenv import load_dotenv
import os

# Constants
load_dotenv()
FRED_API_KEY = os.getenv('FRED_API_KEY')
if not FRED_API_KEY:
    raise ValueError("FRED_API_KEY not found in environment variables")

COUNTRY_MAPPINGS_FILE = 'cpi_weight_countries.json'
START_DATE = "2000-01-01"

TIME_PERIODS = {
    'Pre-GFC': [2000, 2009],
    'Post-GFC': [2010, 2019],
    'Post-COVID': [2020, 2024]
}

def initialize_page() -> None:
    """Initialize the Streamlit page configuration."""
    st.set_page_config(
        page_title="CPI Data Explorer",
        layout="wide"
    )
    st.title("Consumer Price Index")

@st.cache_data
def load_country_mappings() -> Optional[Dict]:
    """Load country mappings from JSON file."""
    try:
        with open(COUNTRY_MAPPINGS_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Error loading country mappings: {str(e)}")
        return None

@st.cache_data(ttl=3600)
def load_data(country_codes: List[str], start_date: str, ratio_periods: Dict[str, List[int]]) -> Optional[Dict]:
    """Load CPI data for selected countries."""
    try:
        manager = UnifiedCPIManager(fred_api_key=FRED_API_KEY)
        return manager.get_complete_cpi_data(
            countries=country_codes,
            start_date=start_date,
            ratio_periods=ratio_periods
        )
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return None

def create_cpi_line_plot(filtered_cpi: pd.DataFrame) -> go.Figure:
    """Create line plot for CPI values."""
    fig = px.line(
        filtered_cpi,
        x='date',
        y='value',
        color='country',
        labels={'value': 'CPI Index (2015=100)', 'date': 'Date', 'country': 'Country'},
        markers=True
    )
    fig.update_layout(yaxis_range=[50, max(filtered_cpi['value']) * 1.1])
    return fig

def create_rate_of_change_barchart(df: pd.DataFrame) -> go.Figure:
    """Create bar chart for rate of change data."""
    # Convert the data to percentage format
    df_pct = df * 100

    # Create labels with year ranges using TIME_PERIODS constant
    period_labels = {
        period: f'{period}<br>({years[0]}-{years[1]})'
        for period, years in TIME_PERIODS.items()
    }
    
    fig = go.Figure()
    
    # Add a bar for each country
    for country in df_pct.index:
        fig.add_trace(go.Bar(
            name=country,
            x=[period_labels[col] for col in df_pct.columns],
            y=df_pct.loc[country],
            text=[f'{val:.2f}%' for val in df_pct.loc[country]],
            textposition='auto',
        ))

    fig.update_layout(
        title='Annualised Rate of Change by Period',
        yaxis_title='Rate of Change (%)',
        xaxis_title='Time Period',
        barmode='group',
        width=800,
        height=400,
        font=dict(size=12),
        showlegend=True,
        legend_title='Country'
    )

    # Add a horizontal line at y=0 for reference
    fig.add_hline(y=0, line_dash="dash", line_color="gray")

    return fig

def display_cpi_tab(data: Dict) -> None:
    """Display CPI data tab content."""
    st.header("Consumer Price Index (2015=100)")
    
    # Date range filter
    st.sidebar.header("CPI Data Filters")
    cpi_df = data['cpi']
    date_range = st.sidebar.date_input(
        "Select Date Range",
        value=(cpi_df['date'].min(), cpi_df['date'].max()),
        key="cpi_date_range"
    )
    
    # Filter and display data
    mask = (cpi_df['date'] >= pd.Timestamp(date_range[0])) & \
           (cpi_df['date'] <= pd.Timestamp(date_range[1]))
    filtered_cpi = cpi_df[mask]
    
    st.subheader("Time Series")
    st.plotly_chart(create_cpi_line_plot(filtered_cpi), use_container_width=True)
    
    st.subheader("Annualised Rate of Change")
    st.plotly_chart(create_rate_of_change_barchart(data['roc']), use_container_width=True)
    
    st.subheader("Detailed CPI Data")
    st.dataframe(
        filtered_cpi.sort_values(['country', 'date'])
        .style.format({
            'value': '{:.1f}',
            'date': lambda x: x.strftime('%Y-%m-%d')
        }),
        use_container_width=True
    )

def display_weights_tab(data: Dict) -> None:
    """Display weights data tab content."""
    st.header("Weights Analysis")
    
    # Filters
    st.sidebar.header("Weights Data Filters")
    weights_df = data['weights']
    
    years = sorted(weights_df['Year'].unique())
    selected_years = st.sidebar.select_slider(
        "Select Year Range",
        options=years,
        value=(min(years), max(years)),
        key="weights_year_range"
    )
    
    categories = sorted(weights_df['Category_Description'].unique())
    selected_categories = st.sidebar.multiselect(
        "Select Categories",
        categories,
        default=categories,
        key="weights_categories"
    )
    
    # Filter and display data
    filtered_weights = weights_df[
        (weights_df['Year'].between(selected_years[0], selected_years[1])) &
        (weights_df['Category_Description'].isin(selected_categories))
    ]
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total Records", len(filtered_weights))
    with col2:
        st.metric("Number of Countries", len(filtered_weights['Country'].unique()))
    
    st.subheader("Detailed Weights Data")
    st.dataframe(
        filtered_weights.sort_values(['Country', 'Year', 'Category_Description'])
        .style.format({'Weight': '{:.1f}'}),
        use_container_width=True
    )
    
    # Download buttons
    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            label="Download weights data as CSV",
            data=filtered_weights.to_csv(index=False),
            file_name="cpi_weights_filtered.csv",
            mime="text/csv"
        )
    with col2:
        st.download_button(
            label="Download CPI data as CSV",
            data=data['cpi'].to_csv(index=False),
            file_name="cpi_data_filtered.csv",
            mime="text/csv"
        )

def main():
    """Main application function."""
    initialize_page()
    
    if 'data_loaded' not in st.session_state:
        st.session_state.data_loaded = False
    
    country_mappings = load_country_mappings()
    if not country_mappings:
        st.error("Failed to load country mappings. Please check the JSON file.")
        return
    
    country_dict = {item['Country']: item['Code'] for item in country_mappings}
    selected_countries = st.multiselect(
        "Select Countries to Analyze",
        options=sorted(country_dict.keys()),
        help="Select countries to include in the analysis"
    )
    
    if st.button("Load Data", disabled=len(selected_countries) == 0):
        selected_codes = [country_dict[country] for country in selected_countries]
        with st.spinner(f'Loading data for {", ".join(selected_countries)}...'):
            data = load_data(selected_codes, START_DATE, TIME_PERIODS)
            if data is not None:
                st.session_state.data = data
                st.session_state.data_loaded = True
                st.success("Data loaded successfully!")
                st.experimental_rerun()
    
    if st.session_state.data_loaded:
        tab1, tab2 = st.tabs(["CPI Data", "Weights Data"])
        with tab1:
            display_cpi_tab(st.session_state.data)
        with tab2:
            display_weights_tab(st.session_state.data)
        
        if st.button("Select Different Countries"):
            st.session_state.data_loaded = False
            st.experimental_rerun()
    elif len(selected_countries) == 0:
        st.info("Please select at least one country and click 'Load Data'")

if __name__ == "__main__":
    main()
