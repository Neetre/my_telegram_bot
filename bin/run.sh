#!/bin/bash

cd /home/mattia/Documents/Git/my_telegram_bot/

if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python -m venv venv
fi

source .venv/bin/activate  # For Unix/Linux

if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
fi

cd bin
python bot.py

deactivate