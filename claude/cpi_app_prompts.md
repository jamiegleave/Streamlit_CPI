# Development Prompts for CPI Weights Comparison Tool

## 1. Data Acquisition Module

```prompt
Project: CPI Weights Comparison Tool
Component: Data Acquisition Module
Priority: P0

Please implement a Python module for data acquisition with the following specifications:

Requirements:
1. Create a class ONSDataLoader:
   - Method to download Excel file from ONS URL
   - Method to parse Excel data into pandas DataFrame
   - Error handling for network issues and file format changes
   - Data validation checks

2. Create a class EurostatLoader:
   - Implementation of SDMX REST API client
   - Methods to fetch HICP weights using 'prc_hicp_inw' dataset
   - Caching mechanism for API responses
   - Error handling for API failures

3. Create a DataManager class to:
   - Coordinate both data sources
   - Implement retry logic
   - Handle data freshness checks
   - Provide unified data access interface

Error Handling:
- Network connectivity issues
- Invalid/changed data formats
- API rate limiting
- Missing or corrupt data

Testing Requirements:
1. Unit tests for each class
2. Integration tests for data loading
3. Mock responses for API calls
4. Validation of data structures

Documentation:
- Update README.md with setup instructions
- Document API endpoints and data structures
- Add error codes and resolution steps
- Include sample usage examples

The code should follow PEP 8 style guidelines and include comprehensive docstrings.
```

## 2. Data Processing Module

```prompt
Project: CPI Weights Comparison Tool
Component: Data Processing Module
Priority: P0

Please implement a Python module for data processing with the following specifications:

Requirements:
1. Create a CategoryMapper class:
   - Define mapping between ONS and HICP categories
   - Handle hierarchical category structures
   - Methods for category standardization
   - Logging of unmapped categories

2. Create a WeightStandardizer class:
   - Methods to normalize weights to common base
   - Validation of weight totals
   - Handling of missing values
   - Precision management

3. Create a DataProcessor class to:
   - Coordinate transformation pipeline
   - Handle data quality checks
   - Generate metadata
   - Manage data versioning

Error Handling:
- Category mapping failures
- Invalid weight values
- Incompatible data structures
- Version conflicts

Testing Requirements:
1. Unit tests for transformation logic
2. Integration tests for full pipeline
3. Edge case testing
4. Data quality validation

Documentation:
- Document category mapping methodology
- Update CHANGELOG.md with changes
- Add data dictionary
- Include validation rules

The code should include logging and performance monitoring.
```

## 3. Streamlit UI - Core Interface

```prompt
Project: CPI Weights Comparison Tool
Component: Streamlit UI Core
Priority: P1

Please implement the main Streamlit interface with the following specifications:

Requirements:
1. Create main.py with:
   - Sidebar implementation
   - Country selection interface
   - Year selection widget
   - Data refresh controls
   - Error messaging system

2. Implement core displays:
   - Summary statistics panel
   - Interactive comparison table
   - Basic visualizations
   - Data export functionality

3. Add state management:
   - Session state handling
   - Cache management
   - User preferences
   - View persistence

Error Handling:
- Invalid user inputs
- Data loading failures
- Display rendering issues
- Session management errors

Testing Requirements:
1. UI component testing
2. User interaction testing
3. Performance testing
4. Cross-browser compatibility

Documentation:
- Update README.md with usage instructions
- Add UI/UX guidelines
- Document state management
- Include troubleshooting guide

Follow Streamlit best practices for layout and performance.
```

## 4. Visualization Module

```prompt
Project: CPI Weights Comparison Tool
Component: Visualization Module
Priority: P1

Please implement a visualization module with the following specifications:

Requirements:
1. Create ChartManager class:
   - Bar chart comparisons
   - Heatmap generation
   - Time series plots
   - Category breakdown visualizations

2. Implement interactive features:
   - Click-through details
   - Dynamic filtering
   - Custom view options
   - Export capabilities

3. Add visualization utilities:
   - Color scheme management
   - Layout optimization
   - Responsive design
   - Accessibility features

Error Handling:
- Data format issues
- Rendering failures
- Memory management
- Browser compatibility

Testing Requirements:
1. Visual regression testing
2. Performance benchmarking
3. Accessibility testing
4. Cross-device testing

Documentation:
- Document chart types and usage
- Add visualization guidelines
- Include performance tips
- Update CHANGELOG.md

Use Plotly and Altair best practices for interactive visualizations.
```

## 5. Data Export Module

```prompt
Project: CPI Weights Comparison Tool
Component: Data Export Module
Priority: P2

Please implement a data export module with the following specifications:

Requirements:
1. Create ExportManager class:
   - Excel export functionality
   - CSV export
   - JSON export
   - PDF report generation

2. Implement export options:
   - Selected data only
   - Full dataset
   - Custom formatting
   - Metadata inclusion

3. Add export utilities:
   - Format validation
   - File naming
   - Compression
   - Batch processing

Error Handling:
- File system issues
- Format conversion errors
   - Memory constraints
   - Permission issues

Testing Requirements:
1. Format validation testing
2. Large dataset handling
3. Error recovery testing
4. Performance testing

Documentation:
- Document export formats
- Add usage examples
- Include file format specs
- Update README.md

Follow security best practices for file handling.
```

## Usage Instructions

1. Use these prompts sequentially to build each component
2. Adapt prompts based on implementation feedback
3. Update documentation after each component
4. Test integration between components
5. Validate against user stories

## Implementation Order
1. Data Acquisition Module
2. Data Processing Module
3. Core Streamlit UI
4. Visualization Module
5. Data Export Module

Each prompt should be used with an LLM coding assistant, and the output should be reviewed and tested before moving to the next component.
