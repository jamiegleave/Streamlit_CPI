# CPI Weights Comparison Tool
## Application Concept
A Streamlit-based application that retrieves, standardizes, and compares Consumer Price Index (CPI) weights across the UK and major EU economies. The tool will provide interactive visualizations and analysis of how different countries weight various categories in their inflation calculations.

## Core Functionality
1. Data Acquisition
   - UK data: Parse Excel file from ONS website
   - EU data: Connect to Eurostat API using SDMX queries
   - Data caching to minimize API calls
   - Automated category mapping/standardization

2. Data Processing
   - Standardize category classifications across countries
   - Normalize weights to common base (100 or 1000)
   - Handle missing data and inconsistencies
   - Track and display data vintage/reference periods

3. Analysis Features
   - Cross-country comparisons
   - Category-level deep dives
   - Time series analysis (if available)
   - Statistical summaries

## UX/UI Requirements and User Flow
### Interface Layout
1. Sidebar
   - Country selection (multiple)
   - Year selection
   - Category filtering
   - Display options
   - Data refresh trigger

2. Main Content Area
   - Summary statistics
   - Interactive comparison table
   - Visualization dashboard
   - Data export options

### User Flow
1. Initial Landing
   - Welcome message
   - Quick guide to interpretation
   - Data freshness indicator

2. Data Selection
   - Country/region selection
   - Time period selection
   - Category granularity selection

3. Analysis View
   - Tabular comparisons
   - Visual comparisons
   - Detailed category breakdowns

## Key Features (Priority Order)
1. MVP Features (P0)
   - Basic data extraction from both sources
   - Simple tabular comparison
   - Category standardization
   - Single year view

2. Core Features (P1)
   - Interactive tables with sorting/filtering
   - Basic visualizations (bar charts, heatmaps)
   - Data export functionality
   - Category grouping/aggregation

3. Enhancement Features (P2)
   - Time series comparison
   - Advanced visualizations
   - Statistical analysis
   - Category mapping customization

4. Future Features (P3)
   - Additional countries
   - API caching layer
   - Custom category groupings
   - Automated data updates

## Technical Stack
### Required Libraries
1. Core Framework
   ```
   streamlit
   pandas
   numpy
   openpyxl
   requests
   ```

2. Data Processing
   ```
   pandassdmx
   xlrd
   pandas-excel
   ```

3. Visualization
   ```
   plotly
   altair
   seaborn
   ```

4. Utilities
   ```
   python-dotenv
   cachetools
   datetime
   ```

### Infrastructure Requirements
- Python 3.8+
- Memory: 2GB+ RAM
- Storage: ~100MB for cached data
- Internet access for API calls

## Data Sources and Processing
### Data Sources
1. UK Data
   - Source: ONS Excel file
   - Format: XLSX
   - Update frequency: Annual
   - Key fields: Category, Weight

2. Eurostat Data
   - Source: SDMX REST API
   - Format: JSON/XML
   - Dataset: 'prc_hicp_inw' (HICP weights)
   - Key fields: Country, Category, Weight

### Data Processing Requirements
1. Category Standardization
   - Create mapping between ONS and HICP categories
   - Handle hierarchical category structures
   - Document unmapped categories

2. Weight Normalization
   - Convert to common base (e.g., per 1000)
   - Handle rounding and precision
   - Validate totals

## User Stories
1. Policy Analyst
   "As a policy analyst, I want to compare how different countries weight housing costs in their CPI to understand methodological differences."
   - Select specific categories
   - Compare across countries
   - Export data for reports

2. Economic Researcher
   "As a researcher, I need to analyze the evolution of CPI weights across countries over time."
   - Access historical data
   - Generate time series
   - Perform statistical analysis

3. Financial Analyst
   "As a financial analyst, I want to understand differences in consumption patterns across countries."
   - Quick country comparisons
   - Category-level analysis
   - Visual representations

## Implementation Notes
1. Development Phases
   - Phase 1: Data acquisition and standardization
   - Phase 2: Basic UI and visualization
   - Phase 3: Advanced features
   - Phase 4: Optimization and scaling

2. Error Handling
   - API connection issues
   - Data format changes
   - Missing or incomplete data
   - Category mapping errors

3. Performance Considerations
   - Cache API responses
   - Optimize data transformations
   - Lazy loading of visualizations
   - Memory management

4. Documentation Requirements
   - Data source documentation
   - Category mapping methodology
   - Known limitations
   - User guide
