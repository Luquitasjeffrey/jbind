from pathlib import Path
import os

def capitalize_first(s: str):
    idx = 0
    while s[idx] == "_": idx+=1
    return s[0:idx] + s[idx].capitalize() + s[idx+1:]

def ensure_dir_exists(file_path: str):
    # Convert the file path to a Path object
    path = Path(file_path)
    # Create the parent directory (and any necessary parents) if it doesn't exist
    path.parent.mkdir(parents=True, exist_ok=True)

DEBUG = os.getenv("DEBUG") == "true"

def dbg(*args):
    if DEBUG:
        print(*args)