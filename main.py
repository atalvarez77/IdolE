import sys
import os
from PyQt6.QtWidgets import QApplication, QMainWindow, QStackedWidget, QMessageBox
from PyQt6.QtGui import QIcon

# Import our custom modules
from src.engine.pathfinder import IdolPathfinder
from src.ui.search_screen import SearchScreen
from src.ui.map_screen import MapScreen

class IdolEApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("IdolE - Knowledge Graph Engine")
        self.resize(1100, 800)
        self.setStyleSheet("background-color: #1b1f24;")

        # 1. Initialize Engine Data
        self._boot_engine()

        # 2. Setup Central UI Stack
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        # 3. Load Screens
        self.search_screen = SearchScreen(self.valid_idols, self.handle_initial_search)
        self.stack.addWidget(self.search_screen)
        
        # We don't instantiate the Map Screen until a search is actually made
        self.map_screen = None 

    def _boot_engine(self):
        """Loads SQLite data into the NetworkX Graph in memory."""
        db_path = os.path.join(os.path.dirname(__file__), "src", "data", "processed_idols.db")
        
        if not os.path.exists(db_path):
            QMessageBox.critical(self, "Fatal Error", f"Database not found at:\n{db_path}\n\nPlease run src/engine/builder.py first.")
            sys.exit(1)
            
        try:
            print("Booting IdolE Engine...")
            self.engine = IdolPathfinder(db_path)
            
            # Extract all valid idol names for the QCompleter dropdowns
            self.valid_idols = sorted([
                n for n, d in self.engine.G.nodes(data=True) 
                if d.get('type') == 'idol'
            ])
            print(f"Engine Ready. Loaded {len(self.valid_idols)} anchor nodes.")
            
        except Exception as e:
            QMessageBox.critical(self, "Engine Failure", f"Failed to build Knowledge Graph:\n{str(e)}")
            sys.exit(1)

    def handle_initial_search(self, source_id: str, target_id: str):
        """Callback from SearchScreen: Triggers Dijkstra and transitions to MapScreen."""
        print(f"Executing Pathfinding: {source_id} -> {target_id}")
        
        # 1. Run Dijkstra
        result = self.engine.find_path(source_id, target_id)
        
        if not result.get('success'):
            self.search_screen.show_error(result.get('error', 'Unknown pathfinding error.'))
            return
            
        # 2. Build the Map Screen with the result
        self.map_screen = MapScreen(result, self.handle_reset_search, self.valid_idols, self.engine, self.handle_add_idol_to_network)
        self.stack.addWidget(self.map_screen)
        
        # 3. Transition the UI
        self.stack.setCurrentWidget(self.map_screen)
        
        # Store current active idols for when we implement the MST "Add Idol" feature later
        self.active_idols = [source_id, target_id]
    
    def handle_add_idol_to_network(self, new_idol_id: str):
        """Called by MapScreen when user adds a 3rd/4th/5th idol."""
        # 1. Update our state
        if new_idol_id not in self.active_idols:
            self.active_idols.append(new_idol_id)
        
        # 2. Call the new Steiner Tree engine method
        result = self.engine.find_network(self.active_idols)
        
        if not result.get('success'):
            # You could add a signal to show this error in the HUD
            print(f"Engine Error: {result.get('error')}")
            return
            
        # 3. Refresh the UI with the updated Steiner Tree
        # We destroy the old map and create a new one with the expanded dataset
        if self.map_screen:
            self.stack.removeWidget(self.map_screen)
            self.map_screen.deleteLater()
            
        self.map_screen = MapScreen(result, self.handle_reset_search, self.valid_idols, self.engine, self.handle_add_idol_to_network)
        self.stack.addWidget(self.map_screen)
        self.stack.setCurrentWidget(self.map_screen)

    def handle_reset_search(self):
        """Callback from MapScreen: Destroys the map and returns to Search."""
        self.stack.setCurrentWidget(self.search_screen)
        
        # Clean up memory by deleting the old map screen
        if self.map_screen:
            self.stack.removeWidget(self.map_screen)
            self.map_screen.deleteLater()
            self.map_screen = None
            
        self.active_idols = []

if __name__ == "__main__":
    app = QApplication(sys.path)
    
    # Optional: Force macOS dark mode palette consistency
    app.setStyle("Fusion")
    
    window = IdolEApp()
    window.show()
    sys.exit(app.exec())