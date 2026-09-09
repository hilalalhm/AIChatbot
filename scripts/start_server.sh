#!/bin/bash
set -u
cd /home/jasanika/apps/AIChatBot || exit 0
venv=/home/jasanika/virtualenv/apps/AIChatBot/3.12/bin
log=/home/jasanika/apps/AIChatBot/uvicorn.log
if pgrep -f "uvicorn app.main:app" >/dev/null 2>&1; then
    exit 0
fi
nohup "$venv/python" -m uvicorn app.main:app --host 127.0.0.1 --port 8799 >>"$log" 2>&1 &