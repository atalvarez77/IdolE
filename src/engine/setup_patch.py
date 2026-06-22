import json
import os

# The Hierarchical Patch: Maps sub-labels (lowercase) to parent agencies
COMPANY_MAP = {
    # HYBE Corporation
    "ador": "hybe",
    "bighit": "hybe",
    "bighit music": "hybe",
    "big hit music": "hybe",
    "pledis": "hybe",
    "source music": "hybe",
    "source": "hybe",
    "belift lab": "hybe",
    "be:lift": "hybe",
    "koz": "hybe",
    
    # SM Entertainment
    "sm": "sm entertainment",
    "sm c&c": "sm entertainment",
    "mystic": "sm entertainment",
    
    # Kakao Entertainment
    "starship": "kakao",
    "ist": "kakao",
    "edam": "kakao",
    "high up": "kakao",
    "antena": "kakao",
    
    # CJ ENM
    "wakeone": "cj enm",
    "stone music": "cj enm",
    "swing": "cj enm",
    "off the record": "cj enm",
    
    # Standardizations for major single-tier labels
    "jyp": "jyp entertainment",
    "yg": "yg entertainment",
    "the black label": "yg entertainment",
    "cube": "cube entertainment"
}

def build_company_json(output_path: str):
    """Generates the companies.json file for graph normalization."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(COMPANY_MAP, f, indent=4)
        
    print(f"Success: Hierarchical patch saved to {output_path}")

if __name__ == "__main__":
    # Assuming script is run from the project root or src/engine/
    target_path = os.path.join(os.path.dirname(__file__), "..", "data", "companies.json")
    build_company_json(target_path)