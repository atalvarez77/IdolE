import sys
import os
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QLineEdit, QPushButton, QCompleter, QGraphicsDropShadowEffect)
from PyQt6.QtCore import Qt, QStringListModel
from PyQt6.QtGui import QFont, QColor

class SearchScreen(QWidget):
    def __init__(self, valid_idols: list, on_search_callback):
        """
        Initializes the Gateway UI.
        :param valid_idols: List of strings e.g., ["Yuta (Nct)", "Yves (Loona)"]
        :param on_search_callback: Function to call when user hits submit.
        """
        super().__init__()
        self.valid_idols = valid_idols
        self.on_search_callback = on_search_callback
        
        self._setup_window()
        self._init_ui()
        self._apply_styles()

    def _setup_window(self):
        self.setWindowTitle("IdolE - Knowledge Graph Engine")
        # Default window size for the Gateway
        self.resize(800, 600)
        self.setStyleSheet("background-color: #1b1f24;")

    def _init_ui(self):
        # Main layout (centered)
        main_layout = QVBoxLayout()
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.setSpacing(30)

        # 1. Logo / Title
        title_label = QLabel("Idol Exchange")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setObjectName("titleLabel") # For QSS targeting
        main_layout.addWidget(title_label)

        # 2. Subtitle
        subtitle_label = QLabel("Discover hidden pathways in the K-Pop industry.")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle_label.setObjectName("subtitleLabel")
        main_layout.addWidget(subtitle_label)

        # 3. Input Fields Layout
        inputs_layout = QHBoxLayout()
        inputs_layout.setSpacing(20)
        inputs_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Origin Input
        self.origin_input = self._create_autocomplete_input("Origin Idol (e.g., Minji (Newjeans))")
        inputs_layout.addWidget(self.origin_input)

        # Arrow separator
        arrow_label = QLabel("→")
        arrow_label.setObjectName("arrowLabel")
        inputs_layout.addWidget(arrow_label)

        # Target Input
        self.target_input = self._create_autocomplete_input("Target Idol (e.g., Chaewon (Le Sserafim))")
        inputs_layout.addWidget(self.target_input)

        main_layout.addLayout(inputs_layout)

        # 4. Action Button
        self.search_btn = QPushButton("EXCHANGE")
        self.search_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.search_btn.clicked.connect(self._handle_search)
        
        # Add a subtle drop shadow to the button for depth
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(252, 179, 68, 80)) # Sunset orange shadow
        shadow.setOffset(0, 4)
        self.search_btn.setGraphicsEffect(shadow)

        button_layout = QHBoxLayout()
        button_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        button_layout.addWidget(self.search_btn)
        
        main_layout.addLayout(button_layout)
        
        # 5. Error Label (Hidden by default)
        self.error_label = QLabel("")
        self.error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.error_label.setObjectName("errorLabel")
        self.error_label.hide()
        main_layout.addWidget(self.error_label)

        self.setLayout(main_layout)

    def _create_autocomplete_input(self, placeholder: str) -> QLineEdit:
        """Creates a styled text box with QCompleter attached."""
        line_edit = QLineEdit()
        line_edit.setPlaceholderText(placeholder)
        line_edit.setFixedWidth(280)
        line_edit.setFixedHeight(45)

        # Configure the Completer
        completer = QCompleter(self.valid_idols)
        # MatchContains allows users to type "Loona" and see all members
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setMaxVisibleItems(7)
        
        # Attach completer to input
        line_edit.setCompleter(completer)
        
        # Trigger search on Enter key
        line_edit.returnPressed.connect(self._handle_search)
        
        return line_edit

    def _apply_styles(self):
        """Applies the Dark Slate Gray & Sunset Orange design language."""
        self.setStyleSheet("""
            QWidget {
                background-color: #1b1f24;
                color: #e6edf3;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            }
            QLabel#titleLabel {
                font-size: 48px;
                font-weight: 800;
                color: #fcb344;
                letter-spacing: -1px;
            }
            QLabel#subtitleLabel {
                font-size: 16px;
                color: #7d8590;
                margin-bottom: 20px;
            }
            QLabel#arrowLabel {
                font-size: 24px;
                color: #7d8590;
                font-weight: bold;
            }
            QLabel#errorLabel {
                color: #ff6b6b;
                font-size: 14px;
                margin-top: 10px;
            }
            QLineEdit {
                background-color: #0d1117;
                border: 1px solid #30363d;
                border-radius: 8px;
                padding: 10px 15px;
                font-size: 16px;
                color: #c9d1d9;
            }
            QLineEdit:focus {
                border: 1px solid #fcb344;
                background-color: #161b22;
            }
            QPushButton {
                background-color: #fcb344;
                color: #0d1117;
                font-size: 16px;
                font-weight: bold;
                border: none;
                border-radius: 8px;
                padding: 12px 30px;
                margin-top: 20px;
            }
            QPushButton:hover {
                background-color: #e5a03c;
            }
            QPushButton:pressed {
                background-color: #cc8e35;
            }
            /* Style the dropdown menu of the QCompleter */
            QListView {
                background-color: #161b22;
                border: 1px solid #30363d;
                border-radius: 4px;
                color: #c9d1d9;
                font-size: 14px;
                padding: 5px;
            }
            QListView::item:selected {
                background-color: #238636; /* Subtle green highlight for selection */
                color: #ffffff;
                border-radius: 4px;
            }
        """)

    def _handle_search(self):
        """Validates inputs and triggers the callback."""
        origin = self.origin_input.text().strip()
        target = self.target_input.text().strip()

        if not origin or not target:
            self.show_error("Please fill in both idol fields.")
            return

        if origin not in self.valid_idols or target not in self.valid_idols:
            self.show_error("Invalid selection. Please use the exact names from the dropdown.")
            return

        if origin == target:
            self.show_error("Origin and target must be different idols.")
            return

        # Clear error and trigger transition
        self.error_label.hide()
        self.on_search_callback(origin, target)

    def show_error(self, message: str):
        self.error_label.setText(message)
        self.error_label.show()


# ==========================================
# TEST BLOCK: Run this script directly to view
# ==========================================
if __name__ == "__main__":
    # We will temporarily import the backend just to test the UI with real data
    # In the final build, main.py will handle this.
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'engine'))
    from src.engine.pathfinder import IdolPathfinder
    
    app = QApplication(sys.path)
    
    # 1. Initialize Engine (Wait a few ms for SQLite to load)
    print("Booting local engine for UI test...")
    base_dir = os.path.dirname(__file__)
    db_file = os.path.abspath(os.path.join(base_dir, "..", "data", "processed_idols.db"))
    
    try:
        engine = IdolPathfinder(db_file)
        # Extract only the valid strings from the graph nodes where type='idol'
        valid_idol_strings = [n for n, d in engine.G.nodes(data=True) if d.get('type') == 'idol']
    except Exception as e:
        print(f"Failed to load DB: {e}")
        valid_idol_strings = ["Test (Group)", "Another (Group)"] # Fallback if DB not found

    # 2. Define what happens when we click search
    def mock_transition(source, target):
        print(f"\n[UI EVENT] Transitioning to Map Screen!")
        print(f"Requesting Dijkstra calculation for: {source} -> {target}")
        
        # Actually run the calculation to prove it works end-to-end
        res = engine.find_path(source, target)
        if res.get('success'):
            print(f"Engine Success! Weight: {res['total_path_weight']}")
        else:
            print(f"Engine Error: {res['error']}")

    # 3. Render the Window
    window = SearchScreen(valid_idol_strings, mock_transition)
    window.show()
    sys.exit(app.exec())