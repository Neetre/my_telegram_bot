#!/bin/bash

# Navigate to the project directory (adjust the path if needed)
cd /home/mattia/Documents/Git/my_telegram_bot/

# Check if virtual environment exists, if not create it
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python -m venv venv
fi

# Activate virtual environment
source .venv/bin/activate  # For Unix/Linux
# For Windows, use: source venv/Scripts/activate

# Install requirements if needed
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
fi

# Run the main program (adjust the path to your main script)
cd bin
python bot.py

# Deactivate virtual environment
deactivate