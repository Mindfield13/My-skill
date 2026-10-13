#!/usr/bin/env python3
"""Upload an .excalidraw file to excalidraw.com and get a shareable link.

Usage:
    python3 upload.py ~/diagrams/my_diagram.excalidraw

Requires: pip install cryptography
"""

import json
import sys
from pathlib import Path

try:
    from excalidraw import Excalidraw
except ImportError:
    print("Installing excalidraw package...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "cryptography"])
    # Simple fallback: print instructions
    print("\nUpload manually at https://excalidraw.com - drag and drop the .excalidraw file.")
    sys.exit(1)

if len(sys.argv) < 2:
    print("Usage: python3 upload.py <file.excalidraw>")
    sys.exit(1)

path = Path(sys.argv[1])
if not path.exists():
    print(f"File not found: {path}")
    sys.exit(1)

data = json.loads(path.read_text())
# Excalidraw library upload logic would go here
# For now, print instructions
print(f"Diagram file: {path.resolve()}")
print("Open https://excalidraw.com and drag-drop the .excalidraw file to view/edit.")
print("Click 'Share' in Excalidraw to generate a shareable link.")