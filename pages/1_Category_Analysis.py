import streamlit as st
import pandas as pd
import plotly.express as px

# Configure the page
st.set_page_config(page_title="Category Analysis", layout="wide")
st.title("CPI Weights Category Analysis")

# Check if data is loaded
if 'data' not in st.session_state or not st.session_state.data_loaded:
    st.warning("Please load data from the Home page first")
    st.stop()

# Get the data from session state
weights_df = st.session_state.data['weights']

# Sidebar filters
st.sidebar.header("Category Analysis Filters")

# Year filter
years = sorted(weights_df['Year'].unique())
selected_year = st.sidebar.selectbox(
    "Select Year",
    years,
    index=len(years)-1  # Default to latest year
)

# Category filter
categories = sorted(weights_df['Category_Description'].unique())
selected_category = st.sidebar.selectbox(
    "Select Category to Analyze",
    categories
)

# Filter data for selected category and year
filtered_df = weights_df[
    (weights_df['Category_Description'] == selected_category) &
    (weights_df['Year'] == selected_year)
].sort_values('Weight', ascending=True)  # Sort for better visualization

if not filtered_df.empty:
    # Create horizontal bar chart for better readability with many countries
    fig = px.bar(
        filtered_df,
        y='Country',  # Switch to y-axis for horizontal bars
        x='Weight',
        title=f'CPI Weights Comparison: {selected_category} ({selected_year})',
        labels={'Weight': 'Weight Value', 'Country': 'Country'},
        height=max(400, len(filtered_df) * 40)  # Dynamic height based on number of countries
    )
    
    # Update layout for better readability
    fig.update_layout(
        yaxis_title="",
        xaxis_title="Weight",
        showlegend=False,
        title_x=0.5,
        margin=dict(t=50, l=50, r=50, b=50)
    )
    
    # Add value labels
    fig.update_traces(
        texttemplate='%{x:.1f}',
        textposition='outside'
    )
    
    # Display the plot
    st.plotly_chart(fig, use_container_width=True)
    
    # Display summary statistics in columns
    st.subheader("Summary Statistics")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Average Weight",
            f"{filtered_df['Weight'].mean():.1f}"
        )
    
    with col2:
        st.metric(
            "Minimum Weight",
            f"{filtered_df['Weight'].min():.1f}",
            delta=f"{filtered_df.iloc[0]['Country']}"  # Show country with min weight
        )
    
    with col3:
        st.metric(
            "Maximum Weight",
            f"{filtered_df['Weight'].max():.1f}",
            delta=f"{filtered_df.iloc[-1]['Country']}"  # Show country with max weight
        )
    
    with col4:
        st.metric(
            "Standard Deviation",
            f"{filtered_df['Weight'].std():.1f}"
        )
    
    # Display the data table with improved formatting
    st.subheader("Detailed Data")
    
    # Create a styled dataframe
    styled_df = (
        filtered_df[['Country', 'Weight', 'Source']]
        .sort_values('Weight', ascending=False)
        .style
        .format({'Weight': '{:.1f}'})
        .bar(subset=['Weight'], color='lightblue')
    )
    
    st.dataframe(styled_df, use_container_width=True)
    
    # Add download button
    csv = filtered_df.to_csv(index=False)
    st.download_button(
        label="Download data as CSV",
        data=csv,
        file_name=f"cpi_weights_{selected_category}_{selected_year}.csv",
        mime="text/csv"
    )
else:
    st.error("No data available for the selected category and year")
