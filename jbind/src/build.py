import subprocess
import os

def run_maven(project_dir: str):
    original_dir = os.getcwd()
    try:
        os.chdir(project_dir)
        subprocess.run(["mvn", "clean", "install"])

    finally:
        os.chdir(original_dir)