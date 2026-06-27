@echo off
cd /d "c:\Users\admin\Downloads\icb10proj2"
call .venv\Scripts\activate.bat
pip install scrapling playwright
playwright install
