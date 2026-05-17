@echo off
cd /d C:\Users\Admin\Documents\Codex\Exam\backend
"C:\Program Files\python310\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 1>> uvicorn.out.log 2>> uvicorn.err.log
