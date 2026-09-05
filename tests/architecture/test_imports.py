import os
import ast
from pathlib import Path

def get_all_python_files(directory: str) -> list[Path]:
    p = Path(directory)
    if not p.exists():
        return []
    return list(p.rglob("*.py"))

def test_latent_leakage():
    # Directories that must NEVER import from src.simulation.latent
    restricted_dirs = [
        "src/features",
        "src/models",
        "src/decision",
        "src/evaluation",
        "src/configs" # We will also check this
    ]
    
    base_dir = Path(__file__).parent.parent.parent
    
    for r_dir in restricted_dirs:
        dir_path = base_dir / r_dir
        if not dir_path.exists():
            continue
            
        py_files = get_all_python_files(str(dir_path))
        
        for file_path in py_files:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                
            tree = ast.parse(content, filename=str(file_path))
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        assert "simulation.latent" not in alias.name, f"Leakage found in {file_path}"
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        assert "simulation.latent" not in node.module, f"Leakage found in {file_path}"
