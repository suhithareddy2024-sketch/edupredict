# EduPredict — Deployment Guide

## Quick Deploy on Render (Free)

1. Push this folder to GitHub
2. Go to https://render.com → New Web Service
3. Connect your GitHub repo
4. Settings:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app`
   - Add Disk: Mount path `/data`, Size 1GB (for SQLite persistence)
5. Add environment variable:
   - `SECRET_KEY` = any random string

## Default Login
- Username: `admin`
- Password: `admin123`
⚠️ Change this immediately after first login via Settings page!

## Local Run
```
pip install -r requirements.txt
python fix_db.py   # run once to fix DB
python app.py
```
