# Quick Start Guide

## First Time Setup

```bash
# 1. Clone the repository
git clone https://github.com/Kawzmp3/youtube-transcriber.git
cd youtube-transcriber

# 2. Create virtual environment
python -m venv venv

# 3. Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Create .env file with your OpenAI API key
echo "OPENAI_API_KEY=your_api_key_here" > .env
```

## Running the App

Every time you want to run the app:

```bash
# 1. Make sure you're in the project directory
cd youtube-transcriber

# 2. Activate virtual environment (if not already activated)
source venv/bin/activate

# 3. Run the app
python app.py
```

## Troubleshooting
77z
If you see "ModuleNotFoundError", make sure:
1. Your virtual environment is activated (you should see `(venv)` in your terminal)
2. You've installed all requirements (`pip install -r requirements.txt`)
3. You're in the project directory when running the app

To deactivate the virtual environment when you're done:
```bash
deactivate
``` 