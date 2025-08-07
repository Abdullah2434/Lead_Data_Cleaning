@echo off
echo Creating virtual environment for Lead Data Cleaner...
python -m venv lead_cleaner_env

echo.
echo Activating virtual environment...
call lead_cleaner_env\Scripts\activate

echo.
echo Installing dependencies...
pip install -r requirements.txt

echo.
echo Setup complete! 
echo.
echo To run the app:
echo 1. Activate the environment: lead_cleaner_env\Scripts\activate
echo 2. Run the app: streamlit run app.py
echo 3. When done, deactivate: deactivate
echo.
pause