#!/bin/bash
set -u
pkill -f "uvicorn app.main:app" >/dev/null 2>&1
sleep 2
bash /home/jasanika/apps/AIChatBot/scripts/start_server.sh