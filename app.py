import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QLineEdit, QPushButton, QTextEdit, QLabel, QMessageBox,
                            QProgressBar, QHBoxLayout)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QTextCursor
from transcript_service import get_transcript
from gpt_service import GPTService, GPTServiceError

class TranscriptionWorker(QThread):
    """Worker thread for handling transcription and note generation."""
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    progress = pyqtSignal(str)  # For progress updates
    chunk_progress = pyqtSignal(int, int)  # For chunk progress (current, total)

    def __init__(self, url):
        super().__init__()
        self.url = url

    def run(self):
        try:
            self.progress.emit("Fetching transcript...")
            transcript = get_transcript(self.url)
            self.progress.emit(f"Transcript fetched! Processing {len(transcript)} entries...")
            
            gpt_service = GPTService()
            
            # Monkey patch the print function in GPTService to emit progress
            def progress_callback(current, total):
                self.chunk_progress.emit(current, total)
                self.progress.emit(f"Processing chunk {current}/{total}...")
            
            # Override the print function in generate_notes
            original_print = print
            def custom_print(message):
                if "Processing chunk" in message:
                    try:
                        # Extract numbers more safely
                        parts = message.split()
                        if len(parts) >= 3:
                            chunk_info = parts[2].split('/')
                            if len(chunk_info) == 2:
                                current = int(chunk_info[0])
                                total = int(chunk_info[1])
                                progress_callback(current, total)
                    except (ValueError, IndexError):
                        # If parsing fails, just print the message
                        original_print(message)
                else:
                    original_print(message)
            
            import builtins
            builtins.print = custom_print
            
            try:
                notes = gpt_service.generate_notes(transcript)
            finally:
                builtins.print = original_print
            
            self.finished.emit(notes)
        except Exception as e:
            self.error.emit(str(e))

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("YouTube Transcriber")
        self.setMinimumSize(1000, 800)
        
        # Main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)

        # URL input section
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

        # Progress section
        progress_layout = QVBoxLayout()
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #666;")
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #ddd;
                border-radius: 10px;
                text-align: center;
                height: 25px;
            }
            QProgressBar::chunk {
                background-color: #2196F3;
                border-radius: 8px;
            }
        """)
        self.progress_bar.hide()
        progress_layout.addWidget(self.status_label)
        progress_layout.addWidget(self.progress_bar)

        # Button layout
        button_layout = QHBoxLayout()
        
        # Transcribe button
        self.transcribe_btn = QPushButton("Generate Detailed Notes")
        self.transcribe_btn.setMinimumHeight(40)
        self.transcribe_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 20px;
                font-size: 14px;
                font-weight: bold;
                padding: 0 30px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #1565C0;
            }
            QPushButton:disabled {
                background-color: #BDBDBD;
            }
        """)
        self.transcribe_btn.clicked.connect(self.generate_notes)
        
        # Copy button
        self.copy_btn = QPushButton("Copy to Clipboard")
        self.copy_btn.setMinimumHeight(40)
        self.copy_btn.setStyleSheet(self.transcribe_btn.styleSheet().replace("#2196F3", "#4CAF50"))
        self.copy_btn.clicked.connect(self.copy_to_clipboard)
        self.copy_btn.setEnabled(False)
        
        button_layout.addWidget(self.transcribe_btn)
        button_layout.addWidget(self.copy_btn)

        # Notes display
        self.notes_display = QTextEdit()
        self.notes_display.setReadOnly(True)
        self.notes_display.setStyleSheet("""
            QTextEdit {
                border: 2px solid #ddd;
                border-radius: 10px;
                padding: 15px;
                font-size: 14px;
                font-family: Arial;
                line-height: 1.6;
            }
        """)

        # Add widgets to layout
        layout.addWidget(url_label)
        layout.addWidget(self.url_input)
        layout.addLayout(progress_layout)
        layout.addLayout(button_layout)
        layout.addWidget(self.notes_display)

        # Initialize worker
        self.worker = None

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
        self.notes_display.clear()
        
        # Show progress elements
        self.status_label.setText("Initializing...")
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

    def update_progress(self, current, total):
        """Update progress bar."""
        progress = int((current / total) * 100)
        self.progress_bar.setValue(progress)

    def handle_success(self, notes):
        """Handle successful note generation."""
        self.notes_display.setText(notes)
        self.transcribe_btn.setEnabled(True)
        self.url_input.setEnabled(True)
        self.copy_btn.setEnabled(True)
        self.status_label.setText("Notes generated successfully!")
        self.progress_bar.hide()

    def handle_error(self, error_msg):
        """Handle note generation error."""
        QMessageBox.critical(self, "Error", f"Failed to generate notes: {error_msg}")
        self.transcribe_btn.setEnabled(True)
        self.url_input.setEnabled(True)
        self.copy_btn.setEnabled(False)
        self.notes_display.clear()
        self.status_label.setText("Error occurred during processing")
        self.progress_bar.hide()

    def copy_to_clipboard(self):
        """Copy generated notes to clipboard."""
        clipboard = QApplication.clipboard()
        clipboard.setText(self.notes_display.toPlainText())
        self.status_label.setText("Notes copied to clipboard!")

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main() 