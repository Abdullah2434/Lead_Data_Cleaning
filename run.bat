@echo off
echo Activating virtual environment...
call lead_cleaner_env\Scripts\activate

echo Starting Lead Data Cleaner...
streamlit run app.py

pause