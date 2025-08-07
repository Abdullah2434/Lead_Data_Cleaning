import streamlit as st
import pandas as pd
import re
from typing import Dict, List, Optional, Tuple
from difflib import SequenceMatcher
import io

# Configure Streamlit page
st.set_page_config(
    page_title="Lead Data Cleaner",
    page_icon="📊",
    layout="wide"
)

# Header mapping dictionary for Lead411 exports
HEADER_MAP = {
    "MuiTypography-root href": "linkedin",
    "MuiTypography-root href 1": "linkedin", 
    "MuiTypography-root href 2": "linkedin",
    "MuiTypography-root href 3": "linkedin",
    "MuiTypography-root href 4": "linkedin",
    "hidden": "name",
    "max-w-full": "job_title",
    "linkdesign": "company",
    "cursor-pointer": "email",
    "MuiTableCell-root": "revenue",
    "MuiTableCell-root 1": "head_count",
    "MuiTableCell-root 2": "head_count"
}

def similarity(a: str, b: str) -> float:
    """Calculate similarity between two strings."""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def verify_column_content(df: pd.DataFrame, col_idx: int, expected_type: str) -> bool:
    """Verify if column content matches expected type by sampling first few rows."""
    if col_idx >= len(df.columns) or len(df) < 2:
        return False
    
    # Sample first 3-5 data rows (skip potential header row)
    sample_data = df.iloc[1:6, col_idx].dropna().astype(str)
    if len(sample_data) == 0:
        return False
    
    if expected_type == "linkedin":
        linkedin_pattern = r'https?://(?:www\.)?linkedin\.com/in/'
        matches = sum(1 for val in sample_data if re.search(linkedin_pattern, val, re.IGNORECASE))
        return matches >= 1  # At least 1 LinkedIn URL
    
    elif expected_type == "email":
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        matches = sum(1 for val in sample_data if re.search(email_pattern, val))
        return matches >= 1  # At least 1 email
    
    elif expected_type == "name":
        name_matches = 0
        for val in sample_data:
            val_clean = val.strip()
            # Check if it looks like a name (2-4 words, no @ or http)
            if (2 <= len(val_clean.split()) <= 4 and 
                '@' not in val_clean and 
                'http' not in val_clean.lower() and
                not re.search(r'^\d+', val_clean) and
                len(val_clean) > 3):
                name_matches += 1
        return name_matches >= 1
    
    elif expected_type == "job_title":
        job_keywords = ['manager', 'director', 'ceo', 'cto', 'cfo', 'president', 'vp', 'head', 
                       'chief', 'senior', 'lead', 'coordinator', 'specialist', 'analyst', 'officer']
        job_matches = 0
        for val in sample_data:
            val_lower = val.lower()
            if any(keyword in val_lower for keyword in job_keywords) or len(val.split()) >= 2:
                job_matches += 1
        return job_matches >= 1
    
    elif expected_type == "company":
        company_matches = 0
        for val in sample_data:
            val_clean = val.strip()
            # Company names are usually 1-6 words, no @ or http
            if (1 <= len(val_clean.split()) <= 6 and 
                '@' not in val_clean and 
                'http' not in val_clean.lower() and
                len(val_clean) > 2):
                company_matches += 1
        return company_matches >= 1
    
    return False

def map_headers_by_class_names(df: pd.DataFrame) -> pd.DataFrame:
    """Map columns using the header mapping dictionary with content verification."""
    if df.empty:
        return df
    
    # Get the first row as potential headers
    first_row = df.iloc[0].astype(str)
    column_mapping = {}
    used_targets = {}  # Track how many times each target has been used
    
    for col_idx, header_value in enumerate(first_row):
        header_clean = str(header_value).strip()
        target_field = None
        
        # Check for partial matches with key patterns
        if "mui" in header_clean.lower() and "href" in header_clean.lower():
            # This is likely a LinkedIn column, verify with content
            if verify_column_content(df, col_idx, "linkedin"):
                target_field = "linkedin"
        elif "hidden" in header_clean.lower():
            # This is likely a name column, verify with content
            if verify_column_content(df, col_idx, "name"):
                target_field = "name"
        elif "max-w-full" in header_clean.lower():
            # This is likely a job title column, verify with content
            if verify_column_content(df, col_idx, "job_title"):
                target_field = "job_title"
        elif "linkdesign" in header_clean.lower():
            # This is likely a company column, verify with content
            if verify_column_content(df, col_idx, "company"):
                target_field = "company"
        elif "cursor-pointer" in header_clean.lower():
            # This is likely an email column, verify with content
            if verify_column_content(df, col_idx, "email"):
                target_field = "email"
        elif "muitable" in header_clean.lower() and "root" in header_clean.lower():
            # MuiTableCell-root variations - need to check content to determine if revenue or headcount
            sample_data = df.iloc[1:6, col_idx].dropna().astype(str)
            if len(sample_data) > 0:
                revenue_score = 0
                headcount_score = 0
                
                for val in sample_data:
                    val_clean = val.strip().lower()
                    
                    # Revenue indicators (stronger patterns)
                    if any(pattern in val_clean for pattern in ['million', 'billion', 'k', '$']):
                        revenue_score += 3
                    elif re.search(r'\d+\s*-\s*\d+\.?\d*\s*(million|billion|k)', val_clean):
                        revenue_score += 4
                    elif re.search(r'<\s*\d+k', val_clean):  # "< 500k" type patterns
                        revenue_score += 3
                    elif re.search(r'>\s*\d+k', val_clean):  # "> 1k" type patterns  
                        revenue_score += 3
                    
                    # Head count indicators (simpler numbers)
                    elif re.search(r'^<\s*\d+$', val_clean):  # Just "< 5", "< 10"
                        headcount_score += 3
                    elif re.search(r'^\d+\s*(may|employees?|people)?$', val_clean):  # "19 may", "50", "19"
                        headcount_score += 2
                    elif re.search(r'^\d+\s*-\s*\d+$', val_clean):  # Simple ranges like "10-50"
                        # Could be either, check if numbers are small (likely headcount)
                        numbers = re.findall(r'\d+', val_clean)
                        if numbers and all(int(num) < 1000 for num in numbers):
                            headcount_score += 2
                        else:
                            revenue_score += 1
                    
                    # Additional headcount patterns
                    if any(word in val_clean for word in ['may', 'employees', 'people', 'staff']):
                        headcount_score += 2
                
                print(f"Column {col_idx} ({header_clean}): Revenue score={revenue_score}, Headcount score={headcount_score}")
                print(f"Sample data: {list(sample_data)}")
                
                if revenue_score > headcount_score:
                    target_field = "revenue"
                elif headcount_score > revenue_score:
                    target_field = "head_count"
                else:
                    # Default assignment based on order
                    existing_revenue = any("revenue" in str(col) for col in column_mapping.values())
                    target_field = "head_count" if existing_revenue else "revenue"
        else:
            # Direct match or fuzzy matching
            if header_clean in HEADER_MAP:
                target_field = HEADER_MAP[header_clean]
            else:
                # Fuzzy matching for similar headers
                best_match = None
                best_score = 0.7  # Minimum similarity threshold
                
                for map_key, map_value in HEADER_MAP.items():
                    score = similarity(header_clean, map_key)
                    if score > best_score:
                        best_score = score
                        best_match = map_value
                        
                if best_match:
                    target_field = best_match
        
        # If we found a target field, handle duplicates
        if target_field:
            if target_field in used_targets:
                used_targets[target_field] += 1
                # Create unique column name for duplicates
                unique_name = f"{target_field}_{used_targets[target_field]}"
                column_mapping[col_idx] = unique_name
            else:
                used_targets[target_field] = 1
                column_mapping[col_idx] = target_field
    
    # If we found mappings, apply them and remove the header row
    if column_mapping:
        new_columns = []
        for i in range(len(df.columns)):
            if i in column_mapping:
                new_columns.append(column_mapping[i])
            else:
                new_columns.append(f"unknown_{i}")
        
        df.columns = new_columns
        # Remove the first row since it was used as headers
        df = df.iloc[1:].reset_index(drop=True)
    
    return df

def detect_linkedin_column(df: pd.DataFrame) -> Optional[str]:
    """Detect LinkedIn column by content."""
    linkedin_pattern = r'https?://(?:www\.)?linkedin\.com/in/'
    
    for col in df.columns:
        sample_data = df[col].dropna().astype(str).head(10)
        linkedin_matches = sum(1 for val in sample_data if re.search(linkedin_pattern, val, re.IGNORECASE))
        if linkedin_matches >= 2:  # At least 2 matches in sample
            return col
    return None

def detect_email_column(df: pd.DataFrame) -> Optional[str]:
    """Detect email column by content."""
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    
    for col in df.columns:
        sample_data = df[col].dropna().astype(str).head(10)
        email_matches = sum(1 for val in sample_data if re.search(email_pattern, val))
        if email_matches >= 2:  # At least 2 matches in sample
            return col
    return None

def detect_name_column(df: pd.DataFrame) -> Optional[str]:
    """Detect name column by content."""
    for col in df.columns:
        sample_data = df[col].dropna().astype(str).head(10)
        name_score = 0
        
        for val in sample_data:
            val_clean = val.strip()
            # Check if it looks like a name (2-3 words, no @ or http)
            if (2 <= len(val_clean.split()) <= 4 and 
                '@' not in val_clean and 
                'http' not in val_clean.lower() and
                not re.search(r'^\d+', val_clean)):
                name_score += 1
                
        if name_score >= 3:  # At least 3 name-like entries
            return col
    return None

def detect_job_title_column(df: pd.DataFrame) -> Optional[str]:
    """Detect job title column by content."""
    job_keywords = ['manager', 'director', 'ceo', 'cto', 'cfo', 'president', 'vp', 'head', 
                   'chief', 'senior', 'lead', 'coordinator', 'specialist', 'analyst', 'officer']
    
    for col in df.columns:
        sample_data = df[col].dropna().astype(str).head(10)
        job_score = 0
        
        for val in sample_data:
            val_lower = val.lower()
            if any(keyword in val_lower for keyword in job_keywords):
                job_score += 1
                
        if job_score >= 2:  # At least 2 job-title-like entries
            return col
    return None

def detect_head_count_column(df: pd.DataFrame) -> Optional[str]:
    """Detect head count column by content."""
    
    for col in df.columns:
        sample_data = df[col].dropna().astype(str).head(10)
        headcount_score = 0
        
        for val in sample_data:
            val_clean = val.strip().lower()
            
            # Head count specific patterns
            if re.search(r'^<\s*\d+$', val_clean):  # "< 5", "< 10"
                headcount_score += 3
            elif re.search(r'^\d+\s*(may|employees?|people|staff)?$', val_clean):  # "19 may", "50"
                headcount_score += 2
            elif re.search(r'^\d+\s*-\s*\d+$', val_clean):  # Simple ranges
                numbers = re.findall(r'\d+', val_clean)
                if numbers and all(int(num) < 1000 for num in numbers):
                    headcount_score += 2
            elif any(word in val_clean for word in ['may', 'employees', 'people', 'staff']):
                headcount_score += 2
                
        if headcount_score >= 3:  # At least 3 headcount-like entries
            return col
    return None

def detect_revenue_column(df: pd.DataFrame) -> Optional[str]:
    """Detect revenue column by content."""
    
    for col in df.columns:
        sample_data = df[col].dropna().astype(str).head(10)
        revenue_score = 0
        
        for val in sample_data:
            val_clean = val.strip().lower()
            
            # Revenue specific patterns
            if any(pattern in val_clean for pattern in ['million', 'billion', '$']):
                revenue_score += 3
            elif re.search(r'\d+\s*-\s*\d+\.?\d*\s*(million|billion)', val_clean):
                revenue_score += 4
            elif re.search(r'<\s*\d+k', val_clean):  # "< 500k"
                revenue_score += 3
            elif re.search(r'>\s*\d+k', val_clean):  # "> 1k"  
                revenue_score += 3
            elif 'revenue' in val_clean:
                revenue_score += 2
                
        if revenue_score >= 3:  # At least 3 revenue-like entries
            return col
    return None



def detect_company_column(df: pd.DataFrame) -> Optional[str]:
    """Detect company column by content."""
    # Look for columns that might contain company names
    for col in df.columns:
        sample_data = df[col].dropna().astype(str).head(10)
        company_score = 0
        
        for val in sample_data:
            val_clean = val.strip()
            # Company names are usually 1-4 words, no @ or http, might have Inc, LLC, etc.
            if (1 <= len(val_clean.split()) <= 6 and 
                '@' not in val_clean and 
                'http' not in val_clean.lower() and
                len(val_clean) > 2):
                company_score += 1
                
        if company_score >= 4:  # At least 4 company-like entries
            return col
    return None

def map_columns_by_content(df: pd.DataFrame) -> pd.DataFrame:
    """Map columns based on their content using detection functions."""
    if df.empty:
        return df
    
    column_mapping = {}
    
    # Detect each field type
    detectors = {
        'linkedin': detect_linkedin_column,
        'email': detect_email_column,
        'name': detect_name_column,
        'job_title': detect_job_title_column,
        'head_count': detect_head_count_column,
        'revenue': detect_revenue_column,
        'company': detect_company_column
    }
    
    used_columns = set()
    
    for field_name, detector_func in detectors.items():
        detected_col = detector_func(df)
        if detected_col and detected_col not in used_columns:
            column_mapping[detected_col] = field_name
            used_columns.add(detected_col)
    
    # Apply the mapping
    if column_mapping:
        df = df.rename(columns=column_mapping)
    
    return df

def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Clean and standardize the dataframe."""
    if df.empty:
        return df
    
    # Target columns we want in the final output
    target_columns = ['name', 'job_title', 'email', 'linkedin', 'head_count', 'revenue', 'company']
    
    # Handle duplicate columns by merging them
    for target_col in target_columns:
        # Find all columns that start with this target (including numbered versions)
        matching_cols = [col for col in df.columns if col == target_col or col.startswith(f"{target_col}_")]
        
        if len(matching_cols) > 1:
            # Merge multiple columns of the same type
            merged_series = pd.Series([''] * len(df), index=df.index)
            
            for col in matching_cols:
                col_data = df[col].fillna('').astype(str)
                # For each row, use the first non-empty value
                for idx in df.index:
                    if merged_series[idx] == '' and col_data[idx] not in ['', 'nan', 'None']:
                        merged_series[idx] = col_data[idx]
            
            # Replace the original column and drop the numbered versions
            df[target_col] = merged_series
            for col in matching_cols:
                if col != target_col:
                    df = df.drop(columns=[col])
        elif len(matching_cols) == 1 and matching_cols[0] != target_col:
            # Rename single numbered column to target name
            df = df.rename(columns={matching_cols[0]: target_col})
    
    # Add missing columns with empty values
    for col in target_columns:
        if col not in df.columns:
            df[col] = ''
    
    # Select only the target columns
    df = df[target_columns]
    
    # Clean the data
    df = df.astype(str)
    df = df.replace(['nan', 'None', 'NaN', ''], pd.NA)
    
    # Drop rows where both email and linkedin are missing
    df = df.dropna(subset=['email', 'linkedin'], how='all')
    
    # Remove duplicates based on email first, then linkedin
    if 'email' in df.columns:
        df = df.drop_duplicates(subset=['email'], keep='first')
    if 'linkedin' in df.columns:
        df = df.drop_duplicates(subset=['linkedin'], keep='first')
    
    # Reset index
    df = df.reset_index(drop=True)
    
    return df

def process_uploaded_file(uploaded_file) -> pd.DataFrame:
    """Process a single uploaded CSV file."""
    try:
        # Read CSV without headers
        df = pd.read_csv(uploaded_file, header=None)
        
        if df.empty:
            return pd.DataFrame()
        
        # First try header-based mapping
        df_mapped = map_headers_by_class_names(df.copy())
        
        # Check if we got good mappings from headers
        target_fields = ['name', 'job_title', 'email', 'linkedin', 'head_count', 'revenue', 'location', 'company']
        mapped_fields = [col for col in df_mapped.columns if col in target_fields]
        
        # If we didn't get enough mappings from headers, try content-based detection
        if len(mapped_fields) < 3:  # Less than 3 fields mapped
            df_mapped = map_columns_by_content(df.copy())
        
        # Clean the dataframe
        df_cleaned = clean_dataframe(df_mapped)
        
        return df_cleaned
        
    except Exception as e:
        st.error(f"Error processing file {uploaded_file.name}: {str(e)}")
        return pd.DataFrame()

# Streamlit UI
def main():
    st.title("📊 Lead Data Cleaner")
    st.markdown("Upload your Lead411 CSV files to clean and merge lead data automatically.")
    
    # File upload section
    st.header("📂 Upload CSV Files")
    uploaded_files = st.file_uploader(
        "Choose CSV files", 
        type="csv", 
        accept_multiple_files=True,
        help="Upload CSV files exported from Lead411 or similar tools"
    )
    
    if uploaded_files:
        st.success(f"Uploaded {len(uploaded_files)} file(s)")
        
        # Process files
        with st.spinner("Processing files..."):
            all_dataframes = []
            
            for uploaded_file in uploaded_files:
                st.write(f"Processing: {uploaded_file.name}")
                df = process_uploaded_file(uploaded_file)
                if not df.empty:
                    all_dataframes.append(df)
                    st.success(f"✅ {uploaded_file.name}: {len(df)} records processed")
                else:
                    st.warning(f"⚠️ {uploaded_file.name}: No valid data found")
            
            if all_dataframes:
                # Ensure all dataframes have the same columns before concatenation
                target_columns = ['name', 'job_title', 'email', 'linkedin', 'head_count', 'revenue', 'company']
                
                # Standardize all dataframes to have the same columns
                standardized_dfs = []
                for df in all_dataframes:
                    # Ensure all target columns exist
                    for col in target_columns:
                        if col not in df.columns:
                            df[col] = ''
                    # Select only target columns in the correct order
                    df_standardized = df[target_columns].copy()
                    standardized_dfs.append(df_standardized)
                
                # Merge all dataframes
                try:
                    merged_df = pd.concat(standardized_dfs, ignore_index=True)
                except Exception as e:
                    st.error(f"Error merging dataframes: {str(e)}")
                    # Fallback: use the first dataframe if concatenation fails
                    merged_df = standardized_dfs[0] if standardized_dfs else pd.DataFrame()
                
                # Final deduplication
                merged_df = merged_df.drop_duplicates(subset=['email'], keep='first')
                merged_df = merged_df.drop_duplicates(subset=['linkedin'], keep='first')
                
                st.header("📊 Cleaned Data")
                st.write(f"**Total records:** {len(merged_df)}")
                
                # Show statistics
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Total Records", len(merged_df))
                with col2:
                    email_count = merged_df['email'].notna().sum()
                    st.metric("With Email", email_count)
                with col3:
                    linkedin_count = merged_df['linkedin'].notna().sum()
                    st.metric("With LinkedIn", linkedin_count)
                with col4:
                    complete_count = merged_df[['email', 'linkedin']].notna().all(axis=1).sum()
                    st.metric("Complete Records", complete_count)
                
                # Display the data
                st.dataframe(merged_df, use_container_width=True)
                
                # Download button
                csv_buffer = io.StringIO()
                merged_df.to_csv(csv_buffer, index=False)
                csv_string = csv_buffer.getvalue()
                
                st.download_button(
                    label="📥 Download Cleaned Data",
                    data=csv_string,
                    file_name="cleaned_leads.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            else:
                st.error("No valid data found in any of the uploaded files.")
    
    else:
        st.info("Please upload one or more CSV files to get started.")
        
        # Show example of expected format
        st.header("📋 Expected File Format")
        st.markdown("""
        Your CSV files should contain lead data with columns that may have class names like:
        - `MuiTypography-root href` (LinkedIn URLs)
        - `hidden` (Names) 
        - `cursor-pointer` (Email addresses)
        - `max-w-full` (Job titles)
        - `linkdesign` (Company names)
        - `MuiTableCell-root` (Revenue/Head count)
        
        The app will automatically detect and map these columns to standard field names.
        """)

if __name__ == "__main__":
    main()