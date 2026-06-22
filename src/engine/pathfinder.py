import networkx as nx
import math
import os
from src.engine.graph_builder import build_knowledge_graph
from networkx.algorithms import approximation

class IdolPathfinder:
    def __init__(self, db_path: str):
        """Initializes the Graph and applies Super-Node penalties to prevent shortcutting."""
        self.G = build_knowledge_graph(db_path)
        self._apply_super_node_penalties()

    def _apply_super_node_penalties(self):
        """
        Dynamically penalizes massive nodes (e.g., South Korea, 2020 Debut Year)
        by scaling their edge weights logarithmically based on their degree.
        This forces Dijkstra to prefer highly specific, meaningful connections.
        """
        print("Applying Super-Node algorithmic penalties...")
        for node, data in self.G.nodes(data=True):
            node_type = data.get('type')
            
            # We don't penalize groups, but we do penalize broader meta-nodes
            if node_type in ['country', 'debut_year', 'company', 'birthplace', 'label']:
                degree = self.G.degree(node)
                
                # If a node has more than 15 connections, it starts losing priority
                if degree > 15:
                    # Log10 creates a smooth penalty curve that scales with density
                    penalty_multiplier = math.log10(degree) 
                    
                    for neighbor in self.G.neighbors(node):
                        # Apply penalty to both directions of the edge
                        current_weight = self.G[node][neighbor].get('weight', 1.0)
                        self.G[node][neighbor]['weight'] = current_weight * penalty_multiplier

        print("Graph optimized and ready for querying.")

    def find_path(self, source_id: str, target_id: str) -> dict:
        """
        Executes Dijkstra's algorithm to find the shortest/strongest path.
        Returns a structured dictionary ready for UI rendering.
        """
        missing = []
        if source_id not in self.G: missing.append(f"Origin: '{source_id}'")
        if target_id not in self.G: missing.append(f"Target: '{target_id}'")
        
        if missing:
            return {"error": f"Node not found: {', '.join(missing)}. Check the exact ID format in the dropdown."}
        
        try:
            # The core routing logic
            path_nodes = nx.shortest_path(self.G, source=source_id, target=target_id, weight='weight')
            
            detailed_path = []
            total_weight = 0.0
            
            for i in range(len(path_nodes)):
                node = path_nodes[i]
                node_data = self.G.nodes[node]
                step_info = {
                    "id": node, 
                    "type": node_data.get('type'),
                    "name": node_data.get('name', node_data.get('stage_name', node))
                }
                
                if i > 0:
                    prev_node = path_nodes[i-1]
                    edge_data = self.G[prev_node][node]
                    step_info['edge_relationship'] = edge_data.get('relationship')
                    step_info['edge_weight'] = round(edge_data.get('weight', 0), 2)
                    total_weight += edge_data.get('weight', 0)
                    
                detailed_path.append(step_info)
                
            # Degrees of separation is hops / 2 (because of the Meta-Node in the middle)
            degrees = len(path_nodes) // 2 
                
            return {
                "success": True,
                "degrees_of_separation": degrees,
                "total_path_weight": round(total_weight, 2),
                "path": detailed_path
            }
            
        except nx.NetworkXNoPath:
            return {"error": "No continuous path exists between these individuals."}
        
    def find_network(self, idol_ids: list) -> dict:
        """
        Executes an Incremental Greedy Search to connect multiple idols.
        Substantially faster and visually cleaner than a full Steiner Tree.
        """
        valid_ids = [i for i in idol_ids if i in self.G]
        if len(valid_ids) < 2:
            return {"error": "Network calculation requires at least 2 valid idols."}
            
        try:
            # 1. Initialize the network with the first two idols (Standard Dijkstra)
            base_path = nx.shortest_path(self.G, source=valid_ids[0], target=valid_ids[1], weight='weight')
            
            network_nodes = set(base_path)
            network_edges = set()
            
            for i in range(len(base_path) - 1):
                # Ensure we store edges consistently (undirected)
                u, v = base_path[i], base_path[i+1]
                network_edges.add(frozenset([u, v]))

            # 2. Incrementally attach each subsequent idol
            for next_idol in valid_ids[2:]:
                if next_idol in network_nodes:
                    continue
                    
                # MULTI-SOURCE DIJKSTRA: Finds the shortest path from ANY active node to the new idol
                try:
                    length, path = nx.multi_source_dijkstra(self.G, sources=network_nodes, target=next_idol, weight='weight')
                    
                    # Merge the new path into our active network
                    for node in path:
                        network_nodes.add(node)
                    for i in range(len(path) - 1):
                        u, v = path[i], path[i+1]
                        network_edges.add(frozenset([u, v]))
                except nx.NetworkXNoPath:
                    continue # Skip if an idol is completely unreachable

            # 3. Format the data for the UI
            formatted_nodes = []
            hub_candidate = None
            max_degree = 0
            node_degree_counts = {node: 0 for node in network_nodes}
            
            # Calculate degrees for hub detection
            for u, v in network_edges:
                node_degree_counts[u] += 1
                node_degree_counts[v] += 1

            for node in network_nodes:
                node_data = self.G.nodes[node]
                degree = node_degree_counts[node]
                node_type = node_data.get('type')
                
                if node_type != 'idol' and degree > max_degree:
                    max_degree = degree
                    hub_candidate = node
                    
                formatted_nodes.append({
                    "id": node,
                    "type": node_type,
                    "name": node_data.get('name', node_data.get('stage_name', node)),
                    "tree_degree": degree
                })

            formatted_edges = []
            total_weight = 0.0
            for u, v in network_edges:
                edge_data = self.G[u][v]
                weight = round(edge_data.get('weight', 0), 2)
                total_weight += weight
                formatted_edges.append({
                    "source": u,
                    "target": v,
                    "relationship": edge_data.get('relationship'),
                    "weight": weight
                })

            return {
                "success": True,
                "total_network_weight": round(total_weight, 2),
                "central_hub": hub_candidate,
                "nodes": formatted_nodes,
                "edges": formatted_edges
            }
            
        except Exception as e:
            return {"error": f"Could not calculate network: {str(e)}"}

if __name__ == "__main__":
    # Test the Pathfinder
    base_dir = os.path.dirname(__file__)
    db_file = os.path.join(base_dir, "..", "data", "processed_idols.db")
    
    pathfinder = IdolPathfinder(db_file)
    
    # NOTE: You must use the exact Disambiguation ID format: "Stage Name (Group)"
    source = "Felix (Stray Kids)"
    target = "Hanni (Newjeans)"
    
    print(f"\n--- Calculating Path: {source} -> {target} ---")
    result = pathfinder.find_path(source, target)
    
    if result.get("success"):
        print(f"\nDegrees of Separation: {result['degrees_of_separation']}")
        print(f"Total Path Weight: {result['total_path_weight']} (Lower is stronger)")
        print("\nTraversal Steps:")
        for step in result['path']:
            if 'edge_relationship' in step:
                print(f"  --[{step['edge_relationship']} (wt: {step['edge_weight']})]--> ", end="")
            print(f"[{step['type'].upper()}: {step['name']}]")
    else:
        print(result["error"])