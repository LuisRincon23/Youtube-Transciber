import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QLineEdit, QPushButton, QTextEdit, QLabel, QMessageBox,
                            QProgressBar, QHBoxLayout, QTabWidget, QSplitter, QScrollArea)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QTextCursor
from transcript_service import get_transcript
from gpt_service import GPTService, GPTServiceError

class TranscriptionWorker(QThread):
    """Worker thread for handling transcription and note generation."""
    finished = pyqtSignal(tuple)
    error = pyqtSignal(str)
    progress = pyqtSignal(str)
    chunk_progress = pyqtSignal(int, int, str)  # Added string parameter for detailed status

    def __init__(self, url):
        super().__init__()
        self.url = url

    def run(self):
        try:
            self.progress.emit("Fetching transcript from YouTube...")
            transcript = get_transcript(self.url)
            
            # Format raw transcript
            self.progress.emit("Formatting transcript with timestamps...")
            raw_transcript = self.format_raw_transcript(transcript)
            
            self.progress.emit(f"Transcript fetched! Processing {len(transcript)} entries in chunks...")
            
            gpt_service = GPTService()
            
            # Monkey patch the print function in GPTService to emit progress
            def progress_callback(current, total, chunk_text):
                self.chunk_progress.emit(current, total, chunk_text)
                self.progress.emit(f"Processing chunk {current}/{total}...")
            
            original_print = print
            def custom_print(message):
                if "Processing chunk" in message:
                    try:
                        parts = message.split()
                        if len(parts) >= 3:
                            chunk_info = parts[2].split('/')
                            if len(chunk_info) == 2:
                                current = int(chunk_info[0])
                                total = int(chunk_info[1])
                                # Extract timestamp from current chunk being processed
                                chunk_start = (current - 1) * 5  # 5 minutes per chunk
                                chunk_end = current * 5
                                chunk_text = f"Processing {chunk_start:02d}:00 - {chunk_end:02d}:00"
                                progress_callback(current, total, chunk_text)
                    except (ValueError, IndexError):
                        original_print(message)
                else:
                    original_print(message)
            
            import builtins
            builtins.print = custom_print
            
            try:
                self.progress.emit("Initializing GPT for note generation...")
                notes = gpt_service.generate_notes(transcript)
            finally:
                builtins.print = original_print
            
            self.progress.emit("Finalizing notes...")
            self.finished.emit((raw_transcript, notes))
        except Exception as e:
            self.error.emit(str(e))

    def format_raw_transcript(self, transcript):
        """Format raw transcript with timestamps."""
        formatted_lines = []
        for entry in transcript:
            minutes = int(entry['start'] // 60)
            seconds = int(entry['start'] % 60)
            formatted_lines.append(f"[{minutes:02d}:{seconds:02d}] {entry['text']}")
        return "\n".join(formatted_lines)

class ChatWorker(QThread):
    """Worker thread for handling chat interactions."""
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    
    def __init__(self, prompt, transcript_context):
        super().__init__()
        self.prompt = prompt
        self.transcript_context = transcript_context
        self.gpt_service = GPTService()
    
    def run(self):
        try:
            # Create a chat prompt that includes context and the user's question
            chat_prompt = f"""Based on the following transcript, please answer this question: {self.prompt}

Transcript context:
{self.transcript_context}

Please provide a detailed, accurate response based solely on the information in the transcript."""

            response = self.gpt_service.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant analyzing a transcript. Provide accurate, relevant information based solely on the transcript content."},
                    {"role": "user", "content": chat_prompt}
                ],
                temperature=0.3
            )
            
            self.finished.emit(response.choices[0].message.content)
        except Exception as e:
            self.error.emit(str(e))

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("YouTube Transcriber")
        self.setMinimumSize(1200, 800)
        
        # Store the current transcript for chat context
        self.current_transcript = ""
        
        # Main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)

        # URL input section
        url_section = QWidget()
        url_layout = QVBoxLayout(url_section)
        url_layout.setSpacing(10)
        
        url_label = QLabel("Enter YouTube URL:")
        url_label.setFont(QFont("Arial", 12))
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://www.youtube.com/watch?v=...")
        self.url_input.setMinimumHeight(40)
        self.url_input.setStyleSheet("""
            QLineEdit {
                border: 2px solid #ddd;
                border-radius: 20px;
                padding: 0 15px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 2px solid #2196F3;
            }
        """)
        
        url_layout.addWidget(url_label)
        url_layout.addWidget(self.url_input)
        layout.addWidget(url_section)

        # Progress section
        progress_section = QWidget()
        progress_layout = QVBoxLayout(progress_section)
        progress_layout.setSpacing(10)
        
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("""
            QLabel {
                color: #666;
                font-size: 14px;
                font-weight: bold;
            }
        """)
        
        self.chunk_status = QLabel("")
        self.chunk_status.setStyleSheet("""
            QLabel {
                color: #2196F3;
                font-size: 12px;
                font-style: italic;
            }
        """)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #ddd;
                border-radius: 10px;
                text-align: center;
                height: 25px;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background-color: #2196F3;
                border-radius: 8px;
            }
        """)
        self.progress_bar.hide()
        
        progress_layout.addWidget(self.status_label)
        progress_layout.addWidget(self.chunk_status)
        progress_layout.addWidget(self.progress_bar)
        layout.addWidget(progress_section)

        # Button section
        button_section = QWidget()
        button_layout = QHBoxLayout(button_section)
        button_layout.setSpacing(10)
        
        self.transcribe_btn = QPushButton("Generate Detailed Notes")
        self.transcribe_btn.setMinimumHeight(40)
        self.transcribe_btn.setStyleSheet("""
            QPushButton {
                background-color: #E3F2FD;
                color: black;
                border: 2px solid #2196F3;
                border-radius: 20px;
                font-size: 14px;
                font-weight: bold;
                padding: 0 30px;
            }
            QPushButton:hover {
                background-color: #BBDEFB;
                border-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #90CAF9;
                border-color: #1565C0;
            }
            QPushButton:disabled {
                background-color: #F5F5F5;
                border-color: #BDBDBD;
                color: #9E9E9E;
            }
        """)
        self.transcribe_btn.clicked.connect(self.generate_notes)
        
        self.copy_btn = QPushButton("Copy to Clipboard")
        self.copy_btn.setMinimumHeight(40)
        self.copy_btn.setStyleSheet("""
            QPushButton {
                background-color: #E8F5E9;
                color: black;
                border: 2px solid #4CAF50;
                border-radius: 20px;
                font-size: 14px;
                font-weight: bold;
                padding: 0 30px;
            }
            QPushButton:hover {
                background-color: #C8E6C9;
                border-color: #388E3C;
            }
            QPushButton:pressed {
                background-color: #A5D6A7;
                border-color: #2E7D32;
            }
            QPushButton:disabled {
                background-color: #F5F5F5;
                border-color: #BDBDBD;
                color: #9E9E9E;
            }
        """)
        self.copy_btn.clicked.connect(self.copy_to_clipboard)
        self.copy_btn.setEnabled(False)
        
        button_layout.addWidget(self.transcribe_btn)
        button_layout.addWidget(self.copy_btn)
        layout.addWidget(button_section)

        # Tab widget for transcript, notes, and chat
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 2px solid #ddd;
                border-radius: 10px;
                padding: 5px;
            }
            QTabBar::tab {
                background-color: #f0f0f0;
                border: 2px solid #ddd;
                border-bottom: none;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
                padding: 8px 15px;
                margin-right: 2px;
                font-size: 13px;
                color: black;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background-color: white;
                border-bottom: none;
                color: #2196F3;
            }
            QTabBar::tab:hover {
                background-color: #e0e0e0;
            }
        """)
        
        # Raw transcript tab
        self.transcript_display = QTextEdit()
        self.transcript_display.setReadOnly(True)
        self.transcript_display.setStyleSheet("""
            QTextEdit {
                border: none;
                padding: 15px;
                font-size: 14px;
                font-family: Arial;
                line-height: 1.6;
            }
        """)
        
        # Notes tab
        self.notes_display = QTextEdit()
        self.notes_display.setReadOnly(True)
        self.notes_display.setStyleSheet(self.transcript_display.styleSheet())
        
        # Chat tab
        chat_widget = QWidget()
        chat_layout = QVBoxLayout(chat_widget)
        chat_layout.setSpacing(10)
        
        # Chat history
        self.chat_history = QTextEdit()
        self.chat_history.setReadOnly(True)
        self.chat_history.setStyleSheet("""
            QTextEdit {
                border: 2px solid #333;
                border-radius: 10px;
                padding: 15px;
                font-size: 14px;
                font-family: Arial;
                line-height: 1.6;
                background-color: #1e1e1e;
                color: #ffffff;
            }
        """)
        
        # Chat input area
        chat_input_widget = QWidget()
        chat_input_layout = QHBoxLayout(chat_input_widget)
        chat_input_layout.setSpacing(10)
        
        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("Ask a question about the transcript...")
        self.chat_input.setMinimumHeight(40)
        self.chat_input.setStyleSheet("""
            QLineEdit {
                border: 2px solid #333;
                border-radius: 20px;
                padding: 0 15px;
                font-size: 14px;
                background-color: #2d2d2d;
                color: #ffffff;
            }
            QLineEdit:focus {
                border: 2px solid #2196F3;
            }
            QLineEdit::placeholder {
                color: #888;
            }
        """)
        self.chat_input.returnPressed.connect(self.send_chat_message)
        
        self.send_button = QPushButton("Send")
        self.send_button.setMinimumHeight(40)
        self.send_button.setStyleSheet("""
            QPushButton {
                background-color: #E3F2FD;
                color: black;
                border: 2px solid #2196F3;
                border-radius: 20px;
                font-size: 14px;
                font-weight: bold;
                padding: 0 30px;
            }
            QPushButton:hover {
                background-color: #BBDEFB;
                border-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #90CAF9;
                border-color: #1565C0;
            }
            QPushButton:disabled {
                background-color: #F5F5F5;
                border-color: #BDBDBD;
                color: #9E9E9E;
            }
        """)
        self.send_button.clicked.connect(self.send_chat_message)
        self.send_button.setEnabled(False)
        
        chat_input_layout.addWidget(self.chat_input)
        chat_input_layout.addWidget(self.send_button)
        
        chat_layout.addWidget(self.chat_history)
        chat_layout.addWidget(chat_input_widget)
        
        # Add all tabs
        self.tab_widget.addTab(self.transcript_display, "Raw Transcript")
        self.tab_widget.addTab(self.notes_display, "Generated Notes")
        self.tab_widget.addTab(chat_widget, "Chat with AI")
        
        layout.addWidget(self.tab_widget)

        # Initialize workers
        self.worker = None
        self.chat_worker = None

    def generate_notes(self):
        """Handle note generation process."""
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Error", "Please enter a YouTube URL")
            return

        # Disable UI elements
        self.transcribe_btn.setEnabled(False)
        self.url_input.setEnabled(False)
        self.copy_btn.setEnabled(False)
        self.transcript_display.clear()
        self.notes_display.clear()
        
        # Show progress elements
        self.status_label.setText("Initializing...")
        self.chunk_status.setText("")
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)

        # Create and start worker thread
        self.worker = TranscriptionWorker(url)
        self.worker.finished.connect(self.handle_success)
        self.worker.error.connect(self.handle_error)
        self.worker.progress.connect(self.update_status)
        self.worker.chunk_progress.connect(self.update_progress)
        self.worker.start()

    def update_status(self, message):
        """Update status message."""
        self.status_label.setText(message)

    def update_progress(self, current, total, chunk_text):
        """Update progress bar and chunk status."""
        progress = int((current / total) * 100)
        self.progress_bar.setValue(progress)
        self.chunk_status.setText(chunk_text)

    def handle_success(self, result):
        """Handle successful note generation."""
        transcript, notes = result
        self.current_transcript = transcript
        self.transcript_display.setText(transcript)
        self.notes_display.setText(notes)
        self.transcribe_btn.setEnabled(True)
        self.url_input.setEnabled(True)
        self.copy_btn.setEnabled(True)
        self.send_button.setEnabled(True)
        self.status_label.setText("✅ Notes generated successfully!")
        self.chunk_status.setText("")
        self.progress_bar.hide()

    def handle_error(self, error_msg):
        """Handle note generation error."""
        QMessageBox.critical(self, "Error", f"Failed to generate notes: {error_msg}")
        self.transcribe_btn.setEnabled(True)
        self.url_input.setEnabled(True)
        self.copy_btn.setEnabled(False)
        self.transcript_display.clear()
        self.notes_display.clear()
        self.status_label.setText("Error occurred during processing")
        self.progress_bar.hide()

    def copy_to_clipboard(self):
        """Copy current tab content to clipboard."""
        clipboard = QApplication.clipboard()
        current_tab = self.tab_widget.currentWidget()
        if current_tab:
            clipboard.setText(current_tab.toPlainText())
            self.status_label.setText(f"Content from {self.tab_widget.tabText(self.tab_widget.currentIndex())} copied to clipboard!")

    def send_chat_message(self):
        """Handle sending a chat message."""
        if not self.current_transcript:
            QMessageBox.warning(self, "Error", "Please generate a transcript first")
            return
            
        message = self.chat_input.text().strip()
        if not message:
            return
            
        # Disable input while processing
        self.chat_input.setEnabled(False)
        self.send_button.setEnabled(False)
        
        # Add user message to chat history
        self.chat_history.append(f"<b>You:</b> {message}")
        self.chat_input.clear()
        
        # Create and start chat worker
        self.chat_worker = ChatWorker(message, self.current_transcript)
        self.chat_worker.finished.connect(self.handle_chat_response)
        self.chat_worker.error.connect(self.handle_chat_error)
        self.chat_worker.start()
        
    def handle_chat_response(self, response):
        """Handle successful chat response."""
        self.chat_history.append(f"<b>AI:</b> {response}\n")
        self.chat_input.setEnabled(True)
        self.send_button.setEnabled(True)
        self.chat_input.setFocus()
        
    def handle_chat_error(self, error_msg):
        """Handle chat error."""
        QMessageBox.critical(self, "Error", f"Failed to get response: {error_msg}")
        self.chat_input.setEnabled(True)
        self.send_button.setEnabled(True)

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main() 