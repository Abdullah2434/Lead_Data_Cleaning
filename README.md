# Lead Data Cleaner

A Streamlit application for cleaning and processing lead data from Lead411 and similar export tools.

## Features

- **Multi-file Upload**: Upload multiple CSV files at once
- **Smart Column Detection**: Automatically detects columns using both header mapping and content analysis
- **Data Cleaning**: Removes duplicates, validates emails, and standardizes formats
- **Export Functionality**: Download cleaned data as CSV

## Installation

### Option 1: Using Virtual Environment (Recommended)

1. Create a virtual environment:
```bash
python -m venv lead_cleaner_env
```

2. Activate the virtual environment:

**Windows:**
```bash
lead_cleaner_env\Scripts\activate
```

**macOS/Linux:**
```bash
source lead_cleaner_env/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run the application:
```bash
streamlit run app.py
```

5. When done, deactivate the virtual environment:
```bash
deactivate
```

### Option 2: Direct Installation

1. Install dependencies directly (not recommended):
```bash
pip install -r requirements.txt
```

2. Run the application:
```bash
streamlit run app.py
```

## Usage

1. Upload your CSV files from Lead411 exports
2. The app will automatically detect and map columns like:
   - Names
   - Email addresses
   - LinkedIn profiles
   - Job titles
   - Company information
   - Revenue data
   - Head count
   - Location/Industry

3. Review the cleaned data
4. Download the merged and deduplicated results

## Column Detection

The app uses two methods for column detection:

### 1. Header Mapping
Maps CSS class names commonly found in Lead411 exports:
- `MuiTypography-root href` → LinkedIn URL
- `hidden` → Name
- `cursor-pointer` → Email
- `max-w-full` → Job Title
- `linkdesign` → Company
- `MuiTableCell-root` → Revenue/Head Count
- `Industry Name` → Location

### 2. Content Analysis
If header mapping fails, the app analyzes cell content:
- LinkedIn: URLs containing `linkedin.com/in`
- Email: Valid email format detection
- Names: 2-3 word strings without symbols
- Job Titles: Contains management/role keywords
- Revenue: Contains $ or "million"/"billion"
- Head Count: Number ranges or patterns like "< 500k"

## Data Cleaning

- Removes rows missing both email and LinkedIn
- Deduplicates based on email and LinkedIn
- Standardizes column names
- Handles missing values appropriately