@echo off
echo Starting APEX Quant-Forge Server...
echo ===================================
call .venv\Scripts\activate.bat
streamlit run app.py
pause
