
from src.manifest.check import check_structure
from src.manifest.generate import generate_manifest


def test_generate_manifest(tmp_path):
    # Setup dummy src structure
    src = tmp_path / "src"
    src.mkdir()
    (src / "domain").mkdir()
    (src / "domain" / "entities.py").write_text("code")
    
    manifest = generate_manifest(src)
    
    assert "modules" in manifest
    assert "domain" in manifest["modules"]
    files = manifest["modules"]["domain"]
    assert len(files) == 1
    assert files[0]["path"] == "domain/entities.py"
    assert files[0]["hash"] is not None

def test_check_structure_pass(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    
    # Valid Structure
    for name in ["domain", "ports", "services"]:
        d = src / name
        d.mkdir()
        (d / "__init__.py").touch()
        
    errors = check_structure(src)
    assert len(errors) == 0

def test_check_structure_fail(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    
    # 1. Illegal dir
    (src / "utils").mkdir() # 'utils' not allowed root
    
    # 2. Missing init
    (src / "domain").mkdir() # missing __init__
    
    # 3. Root file
    (src / "script.py").touch()
    
    errors = check_structure(src)
    assert len(errors) >= 3
    # Updated to match "Illegal dir" abbreviation in check.py
    assert any("Illegal dir" in e and "utils" in e for e in errors)
    assert any("Missing __init__" in e and "domain" in e for e in errors)
    assert any("Illegal file" in e and "script.py" in e for e in errors)
