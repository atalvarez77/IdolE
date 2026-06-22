import sqlite3
import networkx as nx
import pandas as pd
import os

def build_knowledge_graph(db_path: str) -> nx.Graph:
    """
    Loads normalized data from SQLite and constructs the weighted Adjacency List.
    Implements multi-layered edge logic based on IdolE Project Charter.
    """
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Database not found at {db_path}. Run builder.py first.")

    print("Querying SQLite cache...")
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query("SELECT * FROM idols", conn)
    conn.close()

    G = nx.Graph()
    print("Constructing in-memory Knowledge Graph...")

    for _, row in df.iterrows():
        # Disambiguation: Combine Stage Name and Group to create a unique Node ID
        # because multiple idols share stage names (e.g., "Mark" in NCT vs GOT7)
        group_name = row['Group'] if row['Group'] else "Solo/Unknown"
        idol_id = f"{row['Stage Name']} ({group_name})"
        
        # 1. Add the Idol Node
        G.add_node(idol_id, 
                   type='idol', 
                   stage_name=row['Stage Name'],
                   full_name=row['Full Name'], 
                   dob=row['Date of Birth'])

        # ---------------------------------------------------------
        # LAYER 1 & 2: Structural Gatekeeping 
        # Path: Idol -> Group -> Label -> Parent Company
        # ---------------------------------------------------------
        sub_comp = row['Company_Sub']
        parent_comp = row['Company_Parent']
        
        has_active_group = False
        
        # 1. Primary Group Logic
        if row['Group'] and str(row['Group']).lower() != 'solo':
            has_active_group = True
            g_id = f"Group_{row['Group']}"
            G.add_node(g_id, type='group', name=row['Group'])
            G.add_edge(idol_id, g_id, weight=0.5, relationship='current_group')
            
            # GATEKEEPER: Connect the Group to the Label, NOT the Idol
            if sub_comp and sub_comp != 'Independent':
                sc_id = f"Label_{sub_comp}"
                G.add_node(sc_id, type='label', name=sub_comp)
                G.add_edge(g_id, sc_id, weight=0.6, relationship='group_label')

        # 2. Former & Temporary Group Logic (e.g., IZ*ONE)
        for col, rel in [('Other Group', 'other_group'), ('Former Group', 'former_group')]:
            if row[col]:
                for group in str(row[col]).split(','):
                    group = group.strip()
                    if group and group.lower() != 'solo':
                        has_active_group = True
                        g_id = f"Group_{group}"
                        G.add_node(g_id, type='group', name=group)
                        G.add_edge(idol_id, g_id, weight=0.5, relationship=rel)
                        
                        # Project groups act as proxy hubs to the member's current agency
                        if sub_comp and sub_comp != 'Independent':
                            sc_id = f"Label_{sub_comp}"
                            G.add_node(sc_id, type='label', name=sub_comp)
                            G.add_edge(g_id, sc_id, weight=0.8, relationship='former_group_label')

        # 3. The Soloist Exception
        # If no group exists at all, connect the Idol directly to the Label
        if not has_active_group and sub_comp and sub_comp != 'Independent':
            sc_id = f"Label_{sub_comp}"
            G.add_node(sc_id, type='label', name=sub_comp)
            G.add_edge(idol_id, sc_id, weight=0.6, relationship='solo_label')

        # 4. Corporate Ladder
        if sub_comp and sub_comp != 'Independent' and parent_comp and parent_comp != sub_comp:
            pc_id = f"Company_{parent_comp}"
            sc_id = f"Label_{sub_comp}"
            G.add_node(pc_id, type='company', name=parent_comp)
            G.add_edge(sc_id, pc_id, weight=0.6, relationship='parent_company')

        # ---------------------------------------------------------
        # LAYER 3: Debut Cohort (Target Path Weight: 5)
        # Edge Weight: 2.5 (Idol -> Year -> Idol = 5.0)
        # ---------------------------------------------------------
        if row['Debut_Year'] and int(row['Debut_Year']) > 0:
            d_id = f"Debut_{row['Debut_Year']}"
            G.add_node(d_id, type='debut_year', name=str(row['Debut_Year']))
            G.add_edge(idol_id, d_id, weight=2.5, relationship='debut_cohort')

        # ---------------------------------------------------------
        # LAYER 4: Biographical (Target Path Weight: 10)
        # Edge Weight: 5.0 (Idol -> Location -> Idol = 10.0)
        # ---------------------------------------------------------
        if row['Birthplace']:
            bp_id = f"Location_{row['Birthplace']}"
            G.add_node(bp_id, type='birthplace', name=row['Birthplace'])
            G.add_edge(idol_id, bp_id, weight=5.0, relationship='birthplace')
            
        if row['Country']:
            ct_id = f"Country_{row['Country']}"
            G.add_node(ct_id, type='country', name=row['Country'])
            G.add_edge(idol_id, ct_id, weight=5.0, relationship='country')

    return G

if __name__ == "__main__":
    base_dir = os.path.dirname(__file__)
    db_file = os.path.join(base_dir, "..", "data", "processed_idols.db")
    
    # Let's test the engine and output some diagnostics
    graph = build_knowledge_graph(db_file)
    
    print(f"\n--- Graph Diagnostics ---")
    print(f"Total Nodes: {graph.number_of_nodes()}")
    print(f"Total Edges: {graph.number_of_edges()}")
    
    # Count node types to ensure meta-nodes populated correctly
    node_types = {}
    for _, data in graph.nodes(data=True):
        t = data.get('type', 'unknown')
        node_types[t] = node_types.get(t, 0) + 1
        
    print(f"Node Distribution: {node_types}")
    print(f"Engine built successfully.")