# YouTube Transcriber and Note Generator

A modern desktop application that generates detailed, timestamped notes from YouTube videos using AI.

## Features

- Extract transcripts from any YouTube video
- Generate detailed, timestamped notes using GPT
- Modern, clean Google-like interface
- Progress tracking for long videos
- Copy notes to clipboard functionality

## Requirements

- Python 3.8+
- OpenAI API key
- YouTube video URL

## Installation

1. Clone the repository:
```bash
git clone [repository-url]
cd youtube-transcriber
```

2. Create a virtual environment and activate it:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file and add your OpenAI API key:
```
OPENAI_API_KEY=your_api_key_here
```

## Usage

1. Run the application:
```bash
python app.py
```

2. Enter a YouTube URL in the input field
3. Click "Generate Detailed Notes"
4. Wait for the notes to be generated
5. Use the "Copy to Clipboard" button to copy the notes

## Project Structure

- `app.py`: Main application file with GUI implementation
- `transcript_service.py`: YouTube transcript extraction service
- `gpt_service.py`: GPT integration for note generation
- `requirements.txt`: Project dependencies

## Credits

This project uses:
- [youtube-transcript-api](https://github.com/jdepoix/youtube-transcript-api)
- OpenAI's GPT API
- PyQt6 for the GUI 