import sys
import math
import random
from PyQt6.QtWidgets import (QCompleter, QLineEdit, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QGraphicsView, QGraphicsScene, QGraphicsEllipseItem, 
                             QGraphicsTextItem, QGraphicsLineItem, QApplication, QGraphicsItem, QFrame)
from PyQt6.QtCore import Qt, QTimer, QPointF, QRectF
from PyQt6.QtGui import QColor, QPen, QBrush, QFont, QPainter
from src.engine.pathfinder import IdolPathfinder

# ==========================================
# CUSTOM GRAPHICS ITEMS FOR PHYSICS ENGINE
# ==========================================

class NodeItem(QGraphicsEllipseItem):
    """Custom Node that handles its own physics state and UI interactions."""
    def __init__(self, node_id: str, node_type: str, label: str, start_x: float, start_y: float, on_click_callback, radius: float = 25):
        super().__init__(-radius, -radius, radius * 2, radius * 2)
        self.node_id = node_id
        self.node_type = node_type
        self.label_text = label
        self.on_click_callback = on_click_callback
        
        # Physics State (Spawned with a topology hint to prevent criss-crossing)
        self.pos_x = start_x + float(random.uniform(-10, 10))
        self.pos_y = start_y + float(random.uniform(-10, 10))
        self.vel_x = 0.0
        self.vel_y = 0.0
        self.fx = 0.0
        self.fy = 0.0
        
        # UI Properties
        self.setZValue(1)
        self.setAcceptHoverEvents(True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Apply Colors
        self.base_color = self._get_node_color(node_type)
        self.setBrush(QBrush(self.base_color))
        # Add a subtle border
        self.setPen(QPen(QColor('#e6edf3'), 1.5))
        
        # Label Text
        self.text_item = QGraphicsTextItem(label, self)
        self.text_item.setDefaultTextColor(QColor('#e6edf3'))
        self.text_item.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        text_rect = self.text_item.boundingRect()
        self.text_item.setPos(-text_rect.width() / 2, radius + 2)

    def _get_node_color(self, node_type: str) -> QColor:
        colors = {
            'idol': QColor('#fcb344'), 'group': QColor('#ff6b6b'),
            'company': QColor('#4dabf7'), 'country': QColor('#20c997'),
            'birthplace': QColor('#20c997'), 'debut_year': QColor('#cc5de8')
        }
        return colors.get(node_type, QColor('#8b949e'))

    # Replace faulty tooltips with a robust click event
    def mousePressEvent(self, event):
        """Triggers the HUD panel when clicked."""
        self.on_click_callback(self.node_type, self.label_text)
        super().mousePressEvent(event)
        
    def hoverEnterEvent(self, event):
        """Visual feedback on hover."""
        self.setPen(QPen(QColor('#ffffff'), 3))
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.setPen(QPen(QColor('#e6edf3'), 1.5))
        super().hoverLeaveEvent(event)


class EdgeItem(QGraphicsLineItem):
    """Custom solid edge that dynamically updates based on connected nodes."""
    def __init__(self, source_node: NodeItem, target_node: NodeItem, weight: float, relationship: str):
        super().__init__()
        self.source_node = source_node
        self.target_node = target_node
        self.relationship = relationship
        self.weight = weight
        
        self.setZValue(-1) 
        thickness = max(1.5, 4.0 - (weight * 0.2)) 
        self.setPen(QPen(QColor('#495057'), thickness, Qt.PenStyle.SolidLine))

    def update_position(self):
        self.setLine(self.source_node.pos_x, self.source_node.pos_y, 
                     self.target_node.pos_x, self.target_node.pos_y)


# ==========================================
# THE MAP SCREEN & PHYSICS ENGINE
# ==========================================

class MapScreen(QWidget):
    def __init__(self, path_result: dict, on_reset_callback, valid_idols: list, engine: IdolPathfinder, on_add_callback):
        super().__init__()
        self.path_result = path_result
        self.on_reset_callback = on_reset_callback
        self.on_add_callback = on_add_callback
        self.valid_idols = valid_idols
        self.engine = engine
        
        self.active_nodes = {} 
        self.active_edges = [] 
        self.spawn_index = 0 # Used for topology hinting
        
        self._setup_window()
        self._init_ui()
        self._parse_graph_data()
        
        self.spawn_timer = QTimer(self)
        self.spawn_timer.timeout.connect(self._spawn_next_node)
        self.spawn_timer.start(400)
        
        self.physics_timer = QTimer(self)
        self.physics_timer.timeout.connect(self._apply_physics)
        self.physics_timer.start(16) 

    def _setup_window(self):
        self.setWindowTitle("IdolE - Network Visualization")
        self.resize(1100, 800)
        self.setStyleSheet("background-color: #1b1f24; color: #e6edf3;")

    def _init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Top Bar
        top_bar = QHBoxLayout()
        self.reset_btn = QPushButton("← New Search")
        self.reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.reset_btn.setFixedWidth(150)
        self.reset_btn.clicked.connect(self.on_reset_callback)
        self.reset_btn.setStyleSheet("QPushButton { background-color: #30363d; border-radius: 6px; padding: 8px; font-weight: bold; } QPushButton:hover { background-color: #8b949e; color: #0d1117; }")
        top_bar.addWidget(self.reset_btn)

        stats_text = f"Degrees of Separation: {self.path_result.get('degrees_of_separation', '?')}  |  Path Strength: {self.path_result.get('total_path_weight', '?')}"
        stats_label = QLabel(stats_text)
        stats_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        stats_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        stats_label.setStyleSheet("color: #fcb344;")
        top_bar.addWidget(stats_label)
        top_bar.addSpacing(150) 
        main_layout.addLayout(top_bar)

        # The Canvas
        self.scene = QGraphicsScene()
        self.scene.setSceneRect(-2000, -2000, 4000, 4000) 
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.view.setStyleSheet("border: 1px solid #30363d; background-color: #0d1117; border-radius: 8px;")
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        main_layout.addWidget(self.view)

        # HUD Inspector Panel (Solves the Tooltip issue)
        self.hud_panel = QFrame()
        self.hud_panel.setStyleSheet("background-color: #21262d; border: 1px solid #30363d; border-radius: 8px;")
        self.hud_panel.setFixedHeight(60)
        hud_layout = QHBoxLayout(self.hud_panel)
        hud_layout.setContentsMargins(20, 0, 20, 0)
        
        self.hud_label = QLabel("Click any node to inspect data.")
        self.hud_label.setFont(QFont("Arial", 14))
        self.hud_label.setStyleSheet("color: #8b949e;")
        hud_layout.addWidget(self.hud_label)

        # Add to HUD Layout
        self.add_input = QLineEdit()
        self.add_input.setPlaceholderText("Add Idol to network...")
        self.add_input.setFixedWidth(200)
        self.add_btn = QPushButton("Add")

        # Configure the Completer
        completer = QCompleter(self.valid_idols)
        # MatchContains allows users to type "Loona" and see all members
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setMaxVisibleItems(7)
        
        # Attach completer to input
        self.add_input.setCompleter(completer)

        self.add_btn.clicked.connect(self._add_idol_to_network)
        hud_layout.addWidget(self.add_input)
        hud_layout.addWidget(self.add_btn)
        
        main_layout.addWidget(self.hud_panel)
        self.setLayout(main_layout)

    def _update_hud(self, node_type: str, label: str):
        """Callback triggered when a node is clicked."""
        self.hud_label.setStyleSheet("color: #e6edf3;") # Brighten text
        self.hud_label.setText(f"<b>Type:</b> <span style='color:#fcb344;'>{node_type.upper()}</span> &nbsp;&nbsp;|&nbsp;&nbsp; <b>ID:</b> {label}")

    def _parse_graph_data(self):
        self.queue_nodes = []
        self.queue_edges = []
        
        # Check if we have the new Network format or the old Path format
        if 'nodes' in self.path_result:
            # Steiner Network Format
            for node in self.path_result.get('nodes', []):
                self.queue_nodes.append(node)
            for edge in self.path_result.get('edges', []):
                self.queue_edges.append({
                    'source': edge['source'], 'target': edge['target'], 
                    'weight': edge['weight'], 'rel': edge['relationship']
                })
        else:
            # Dijkstra Path Format
            path = self.path_result.get('path', [])
            prev_id = None
            for step in path:
                self.queue_nodes.append(step)
                if prev_id:
                    self.queue_edges.append({
                        'source': prev_id, 'target': step['id'], 
                        'weight': step.get('edge_weight', 1.0),
                        'rel': step.get('edge_relationship', 'linked')
                    })
                prev_id = step['id']

    def _add_idol_to_network(self):
        new_idol = self.add_input.text().strip()
        
        # 1. Validate against the Engine
        if new_idol not in self.engine.G:
            self.hud_label.setStyleSheet("color: #ff6b6b;") # Red text for error
            self.hud_label.setText(f"Error: '{new_idol}' not found. Use exact dropdown format.")
            return
            
        # 2. Let main.py handle the state and calculation!
        self.hud_label.setStyleSheet("color: #fcb344;") 
        self.hud_label.setText("Calculating Network...")
        self.on_add_callback(new_idol)

    def _spawn_next_node(self):
        if not self.queue_nodes:
            self.spawn_timer.stop()
            return
            
        node_data = self.queue_nodes.pop(0)
        
        # TOPOLOGY HINT: Fermat's Spiral (Golden Ratio)
        # Distributes nodes in a tight, sunflower-like pattern radiating outward
        golden_angle = 2.39996 # Radians
        radius = 30 + (self.spawn_index * 15) 
        angle = self.spawn_index * golden_angle
        
        hint_x = radius * math.cos(angle)
        hint_y = radius * math.sin(angle)
        self.spawn_index += 1
        
        new_node = NodeItem(node_data['id'], node_data['type'], node_data['name'], 
                            start_x=hint_x, start_y=hint_y, on_click_callback=self._update_hud)
                            
        self.active_nodes[node_data['id']] = new_node
        self.scene.addItem(new_node)
        
        edges_to_remove = []
        for edge_data in self.queue_edges:
            s_id = edge_data['source']
            t_id = edge_data['target']
            if s_id in self.active_nodes and t_id in self.active_nodes:
                new_edge = EdgeItem(self.active_nodes[s_id], self.active_nodes[t_id], 
                                    edge_data['weight'], edge_data['rel'])
                self.active_edges.append(new_edge)
                self.scene.addItem(new_edge)
                edges_to_remove.append(edge_data)
                
        for e in edges_to_remove:
            self.queue_edges.remove(e)

    def _apply_physics(self):
        if not self.active_nodes:
            return

        # TUNED PHYSICS FOR A CLEANER WEB
        REPULSION = 7000.0  
        SPRING_K = 0.04     
        SPRING_LEN = 180.0  
        DAMPING = 0.50      # Lower number = Higher Friction (settles much faster)
        CENTER_PULL = 0.003 # Gentle pull for normal nodes
        MAX_VELOCITY = 20.0 # Slightly higher cap to let them untangle fast

        nodes = list(self.active_nodes.values())
        hub_id = self.path_result.get('central_hub')

        # 1. Apply Gravity
        for n in nodes:
            gravity = CENTER_PULL
            
            # HUB ANCHORING: If this is the central hub, lock it to the middle
            if hub_id and n.node_id == hub_id:
                gravity = 0.15 
                
            n.fx = -n.pos_x * gravity
            n.fy = -n.pos_y * gravity

        # 2. Coulomb Repulsion
        for i in range(len(nodes)):
            n1 = nodes[i]
            for j in range(i + 1, len(nodes)):
                n2 = nodes[j]
                dx = n1.pos_x - n2.pos_x
                dy = n1.pos_y - n2.pos_y
                dist = max(math.hypot(dx, dy), 1.0)
                
                force = REPULSION / (dist * dist)
                fx = (dx / dist) * force
                fy = (dy / dist) * force
                
                n1.fx += fx
                n1.fy += fy
                n2.fx -= fx
                n2.fy -= fy

        # 3. Hooke's Law Attraction
        for edge in self.active_edges:
            n1 = edge.source_node
            n2 = edge.target_node
            dx = n2.pos_x - n1.pos_x
            dy = n2.pos_y - n1.pos_y
            dist = max(math.hypot(dx, dy), 1.0)
            
            force = (dist - SPRING_LEN) * SPRING_K
            fx = (dx / dist) * force
            fy = (dy / dist) * force
            
            n1.fx += fx
            n1.fy += fy
            n2.fx -= fx
            n2.fy -= fy

        # Calculate Barycenter (Center of Mass) to prevent screen drifting
        cx = sum(n.pos_x for n in nodes) / len(nodes)
        cy = sum(n.pos_y for n in nodes) / len(nodes)

        # 4. Apply Forces
        min_x, min_y, max_x, max_y = 0, 0, 0, 0
        
        for n in nodes:
            n.vel_x = (n.vel_x + n.fx) * DAMPING
            n.vel_y = (n.vel_y + n.fy) * DAMPING
            
            speed = math.hypot(n.vel_x, n.vel_y)
            if speed > MAX_VELOCITY:
                n.vel_x = (n.vel_x / speed) * MAX_VELOCITY
                n.vel_y = (n.vel_y / speed) * MAX_VELOCITY

            n.pos_x += n.vel_x - (cx * 0.05) 
            n.pos_y += n.vel_y - (cy * 0.05)
            n.setPos(n.pos_x, n.pos_y)
            
            min_x, max_x = min(min_x, n.pos_x), max(max_x, n.pos_x)
            min_y, max_y = min(min_y, n.pos_y), max(max_y, n.pos_y)

        for edge in self.active_edges:
            edge.update_position()
            
        if nodes:
            # 1. Find the node that is furthest from the dead center
            max_dist = max(math.hypot(n.pos_x, n.pos_y) for n in nodes)
            
            # 2. Add padding so nodes don't touch the absolute edge of the window
            padding = 50 
            side = (max_dist + padding) * 2
            
            # 3. Create a perfect mathematical square centered at (0,0)
            target_rect = QRectF(-side/2, -side/2, side, side)
            
            # 4. Command the view to auto-zoom to fit this square
            self.view.fitInView(target_rect, Qt.AspectRatioMode.KeepAspectRatio)


# ==========================================
# TEST BLOCK
# ==========================================
if __name__ == "__main__":
    app = QApplication(sys.path)
    
    mock_dijkstra_result = {
        'success': True, 'degrees_of_separation': 3, 'total_path_weight': 12.0,
        'path': [
            {'id': 'Yuta (Nct)', 'type': 'idol', 'name': 'Yuta'},
            {'id': 'Group_Nct', 'type': 'group', 'name': 'Nct', 'edge_weight': 0.5, 'edge_relationship': 'group'},
            {'id': 'Lucas (Nct)', 'type': 'idol', 'name': 'Lucas', 'edge_weight': 0.5, 'edge_relationship': 'group'},
            {'id': 'Country_Hong Kong', 'type': 'country', 'name': 'Hong Kong', 'edge_weight': 5.0, 'edge_relationship': 'country'},
            {'id': 'Vivi (Loona)', 'type': 'idol', 'name': 'Vivi', 'edge_weight': 5.0, 'edge_relationship': 'country'},
            {'id': 'Group_Loona', 'type': 'group', 'name': 'Loona', 'edge_weight': 0.5, 'edge_relationship': 'group'},
            {'id': 'Yves (Loona)', 'type': 'idol', 'name': 'Yves', 'edge_weight': 0.5, 'edge_relationship': 'group'}
        ]
    }
    
    window = MapScreen(mock_dijkstra_result, lambda: print("Reset Clicked!"))
    window.show()
    sys.exit(app.exec())