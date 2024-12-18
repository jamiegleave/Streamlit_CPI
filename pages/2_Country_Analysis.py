import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from io import BytesIO
from datetime import datetime

# Page configuration
st.set_page_config(page_title="Country Analysis", layout="wide")
st.title("CPI Weights Country Analysis")

# Check if data is loaded
if 'data' not in st.session_state or not st.session_state.data_loaded:
    st.warning("Please load data from the Home page first")
    st.stop()

# Get the data from session state
df = st.session_state.data['weights']

# Function to clean category descriptions
def clean_category(category):
    # Remove leading digits and spaces while preserving the rest of the description
    parts = category.split(maxsplit=1)
    return parts[1] if len(parts) > 1 and parts[0].strip().isdigit() else category

# Function to create PDF report
def create_pdf_report(primary_country, second_country, year, filtered_df, comparison_df):
    """Create a PDF report with the analysis results."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=72)
    styles = getSampleStyleSheet()
    
    # Create custom style for headers
    styles.add(ParagraphStyle(
        name='CustomHeader',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=30
    ))
    
    # List to hold the PDF elements
    elements = []
    
    # Title
    title = Paragraph(f"CPI Weights Analysis Report", styles['CustomHeader'])
    elements.append(title)
    elements.append(Spacer(1, 20))
    
    # Report metadata
    elements.append(Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
    elements.append(Paragraph(f"Analysis Year: {year}", styles['Normal']))
    elements.append(Spacer(1, 20))
    
    # Primary country analysis
    elements.append(Paragraph(f"Weight Distribution for {primary_country}", styles['Heading2']))
    elements.append(Spacer(1, 10))
    
    # Convert primary country data to table format
    primary_data = filtered_df[['Clean_Category', 'Weight']].values.tolist()
    primary_data.insert(0, ['Category', 'Weight'])
    
    table = Table(primary_data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 14),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('BOX', (0, 0), (-1, -1), 2, colors.black),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 20))
    
    # Comparison section
    if second_country is not None and not comparison_df.empty:
        elements.append(Paragraph(f"Comparison with {second_country}", styles['Heading2']))
        elements.append(Spacer(1, 10))
        
        # Convert comparison data to table format
        comparison_data = comparison_df.values.tolist()
        comparison_data.insert(0, comparison_df.columns.tolist())
        
        comp_table = Table(comparison_data)
        comp_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BOX', (0, 0), (-1, -1), 2, colors.black),
        ]))
        elements.append(comp_table)
    
    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer

# Clean category descriptions
df['Clean_Category'] = df['Category_Description'].apply(clean_category)

# Country and year selection
col1, col2 = st.columns(2)

with col1:
    # Select country
    countries = sorted(df['Country'].unique())
    selected_country = st.selectbox(
        "Select Primary Country",
        countries,
        key='primary_country'
    )

with col2:
    # Select year
    years = sorted(df['Year'].unique())
    selected_year = st.selectbox(
        "Select Year",
        years,
        index=len(years)-1
    )

# Filter data for selected country and year
filtered_df = df[
    (df['Country'] == selected_country) &
    (df['Year'] == selected_year)
].sort_values('Weight', ascending=False)

# Create visualizations and analysis
if not filtered_df.empty:
    st.subheader(f"Weight Distribution for {selected_country}")
    
    # Verify total weights
    total_weight = filtered_df['Weight'].sum()
    if abs(total_weight - 1000) > 10:
        st.warning(f"Total weights sum to {total_weight:.1f}, expected ~1000")
    
    # Create pie chart
    fig = px.pie(
        filtered_df,
        values='Weight',
        names='Clean_Category',
        title=f'CPI Weights Distribution: {selected_country} ({selected_year})',
        height=700
    )
    
    fig.update_layout(
        title_x=0.5,
        showlegend=True,
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=1.0
        ),
        margin=dict(t=50, l=50, r=250, b=50)
    )
    
    fig.update_traces(
        textposition='inside',
        textinfo='label+percent',
        texttemplate='%{label}<br>%{value:.1f} (%{percent:.1f}%)',
        insidetextorientation='horizontal'
    )
    
    st.plotly_chart(fig, use_container_width=True)

    # Country Comparison Section
    st.subheader("Country Comparison")
    
    # Select second country
    second_country = st.selectbox(
        "Select Country to Compare With",
        [c for c in countries if c != selected_country],
        key='second_country'
    )
    
    # Get data for second country
    second_country_data = df[
        (df['Country'] == second_country) &
        (df['Year'] == selected_year)
    ]
    
    if not second_country_data.empty:
        # Create comparison dataframe
        comparison_df = pd.merge(
            filtered_df[['Clean_Category', 'Weight']],
            second_country_data[['Clean_Category', 'Weight']],
            on='Clean_Category',
            suffixes=(f'_{selected_country}', f'_{second_country}')
        )
        
        # Calculate differences
        comparison_df['Difference'] = (
            comparison_df[f'Weight_{selected_country}'] - 
            comparison_df[f'Weight_{second_country}']
        )
        
        # Create difference bar chart
        fig_diff = go.Figure()
        
        fig_diff.add_trace(go.Bar(
            y=comparison_df['Clean_Category'],
            x=comparison_df['Difference'],
            orientation='h',
            text=comparison_df['Difference'].round(1),
            textposition='auto',
        ))
        
        fig_diff.update_layout(
            title=f'Weight Differences: {selected_country} vs {second_country} ({selected_year})',
            xaxis_title='Weight Difference',
            yaxis_title='Category',
            height=600,
            showlegend=False,
            yaxis={'categoryorder': 'total ascending'},
            margin=dict(l=200)
        )
        
        # Color bars based on values
        fig_diff.update_traces(
            marker_color=comparison_df['Difference'].apply(
                lambda x: 'red' if x < 0 else 'blue'
            )
        )
        
        st.plotly_chart(fig_diff, use_container_width=True)
        
        # Display comparison table
        st.subheader("Detailed Comparison")
        comparison_display = comparison_df.copy()
        comparison_display.columns = [
            'Category',
            f'{selected_country} Weight',
            f'{second_country} Weight',
            'Difference'
        ]
        
        st.dataframe(
            comparison_display.style.format({
                f'{selected_country} Weight': '{:.1f}',
                f'{second_country} Weight': '{:.1f}',
                'Difference': '{:.1f}'
            }),
            use_container_width=True
        )
        
        # Add PDF export button
        st.sidebar.markdown("---")
        st.sidebar.subheader("Export Report")
        
        if st.sidebar.button("Generate PDF Report"):
            with st.spinner('Generating PDF report...'):
                # Create PDF
                pdf_buffer = create_pdf_report(
                    selected_country,
                    second_country,
                    selected_year,
                    filtered_df,
                    comparison_display
                )
                
                # Create download button
                st.sidebar.download_button(
                    label="Download PDF Report",
                    data=pdf_buffer,
                    file_name=f"cpi_weights_report_{selected_country}_{selected_year}.pdf",
                    mime="application/pdf"
                )
                st.sidebar.success("PDF generated successfully!")
else:
    st.error("No data available for the selected country and year")
