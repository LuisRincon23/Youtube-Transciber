# YouTube Transcriber and Note Generator

A modern desktop application that generates detailed, timestamped notes from YouTube videos using AI. The application uses OpenAI's GPT to create comprehensive, well-structured notes from video transcripts, making it perfect for study sessions, content analysis, or quick video summarization.

## Features

- 🎥 Extract transcripts from any YouTube video
- 📝 Generate detailed, timestamped notes using GPT
- 💬 Chat with AI about the video content
- 🎨 Modern, clean Google-like interface
- 📊 Real-time progress tracking for long videos
- 📋 Copy notes to clipboard functionality
- 🌙 Dark mode chat interface
- ⏱️ Timestamp preservation in notes

## Screenshots

[Your screenshots will go here]

## Requirements

- Python 3.8+
- OpenAI API key
- Internet connection for YouTube access
- FFmpeg (optional, for audio processing)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/Kawzmp3/Youtube-Transciber.git
cd Youtube-Transciber
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

4. Create a `.env` file from the example:
```bash
cp .env.example .env
```

5. Add your OpenAI API key to the `.env` file:
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
4. Wait for the processing to complete:
   - Transcript extraction
   - Note generation
   - Chat preparation
5. Use the tabs to:
   - View the raw transcript with timestamps
   - Read the AI-generated structured notes
   - Chat with AI about the video content
6. Use the "Copy to Clipboard" button to copy any tab's content

## Project Structure

```
youtube-transcriber/
├── app.py              # Main application file (GUI)
├── transcript_service.py# YouTube transcript extraction
├── gpt_service.py      # GPT integration for notes
├── requirements.txt    # Project dependencies
├── .env.example       # Example environment variables
├── docs/              # Documentation
│   └── implementation_plan.md
└── tests/             # Test files
    ├── test_transcript.py
    └── test_gpt.py
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Credits

This project uses:
- [youtube-transcript-api](https://github.com/jdepoix/youtube-transcript-api) for transcript extraction
- OpenAI's GPT API for note generation
- PyQt6 for the graphical user interface

## Support

If you encounter any problems or have suggestions, please [open an issue](https://github.com/Kawzmp3/Youtube-Transciber/issues) on GitHub. 