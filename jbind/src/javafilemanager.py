from pathlib import Path
import bind

def ensure_dir_exists(file_path: str):
    # Convert the file path to a Path object
    path = Path(file_path)
    # Create the parent directory (and any necessary parents) if it doesn't exist
    path.parent.mkdir(parents=True, exist_ok=True)

cached = set()

class PrintWritter(bind.PrintWritter):
    def __init__(self, classpath: str, dir: str = "."):
        self.filepath = dir + "/src/main/java/" + classpath.replace(".", "/") + ".java"
        cached.add(self.filepath)
        ensure_dir_exists(self.filepath)
        self.file = open(self.filepath, "w")

    def println(self, text: str) -> None:
        self.file.write(text + "\n")

    def close(self) -> None:
        self.file.close()

    def cached(self) -> bool:
        self.filepath in cached


class JavaFileManager(bind.JavaFileManager):
    def __init__(self, target_dir: str):
        self.target_dir = target_dir

    def get_printwritter(self, class_name: str) -> bind.PrintWritter:
        return PrintWritter(class_name, dir=self.target_dir)
