# IdolE (Idol Exchange) v2.0 🌐

**A high-performance, physics-driven Knowledge Graph engine for K-Pop artist discovery.**

IdolE moves beyond simple "Group/Label" connectivity by utilizing multi-layered graph mathematics to reveal hidden professional, corporate, and biographical relationships between idols. It calculates the "Shortest + Strongest" path between any two individuals, and can generate dynamic Minimum Spanning Trees (Steiner Trees) to find central hubs connecting up to 5 idols simultaneously.

---

## 🛑 The Problem
Traditional K-Pop databases rely on flat-file formats (CSVs, wikis). Flat data fundamentally fails to capture the multi-dimensional complexity of the industry. It cannot dynamically visualize:
* **Corporate Hierarchies:** Sub-labels operating under massive parent conglomerates (e.g., ADOR → HYBE, WakeOne → CJ ENM).
* **Temporary Hubs:** Project groups (like IZ*ONE or Wanna One) that briefly unite idols from completely different, rival agencies.
* **Generational Cohorts:** Hidden connections between idols who debuted in the same year or hail from the same obscure hometowns.

## 💡 The Solution
IdolE translates flat data into a mathematically weighted **Knowledge Graph**. By enforcing "Structural Gatekeeping" (forcing paths to logically flow from *Idol → Group → Sub-Label → Parent Company*), the engine accurately mirrors real-world industry logic. It then visualizes these connections using a custom, 60fps force-directed physics engine.

---

## ⚙️ Technical Architecture

IdolE is built entirely in **Python** and is designed to be local-first, memory-safe, and sub-second responsive.

### 1. Data Persistence & Ingestion Layer (`pandas`, `sqlite3`)
* Ingests a raw, sanitized CSV of idol metadata.
* Applies a recursive JSON mapping patch (`companies.json`) to accurately link independent sub-labels to their parent conglomerates.
* Normalizes and caches the data into a local SQLite database (`processed_idols.db`) for instant boot times (< 500ms).

### 2. The Knowledge Graph Engine (`networkx`)
* **Layered Edge Weights:** Prioritizes corporate/group connections (weights 0.5 - 0.6) over distant biographical data (Layer 4 fallback). 
* **Super-Node Penalties:** Automatically applies logarithmic weight penalties to massive hubs (like `South Korea` or `Company_Kakao`) to prevent the algorithm from taking "lazy" shortcuts, forcing it to find hyper-specific, meaningful bridges.
* **Multi-Source Dijkstra Search:** Employs incremental greedy searches to rapidly build networks, abandoning computationally punishing all-pairs calculations for instantaneous multi-node rendering.

### 3. The Visualization Engine (`PyQt6`)
* **Force-Directed Physics:** Custom engine utilizing Coulomb Repulsion (nodes push away) and Hooke's Law (edges pull together) to organically unroll the graph.
* **Barycentric Anchoring & Fermat's Spiral:** Nodes spawn in a Golden Ratio spiral and are anchored to their center of mass to prevent the graph from drifting off-screen.
* **Auto-Scaling Camera:** The `QGraphicsView` dynamically calculates bounding boxes on every frame to smoothly zoom and keep the entire blooming network perfectly framed.

---

## 🚀 How to Run Locally

### Prerequisites
Ensure you have Python 3.9+ installed on your machine. 

### 1. Set up a Virtual Environment
It is highly recommended to run IdolE in a virtual environment to manage dependencies (especially for macOS dynamic linking).
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate

### 2. Install Dependencies
Note: We specifically use PyQt6 v6.4.2 for stable dynamic linking on macOS.
pip install pandas networkx PyQt6==6.4.2
Or use requirements.txt

### 3. Build the Database
Before running the app, you must build the local SQLite cache from the CSV data.
# Generates the corporate hierarchy map
python src/engine/setup_patch.py

# Ingests the CSV, applies the patch, and builds processed_idols.db
python src/engine/setup_builder.py

### 4. Launch IdolE
python main.py