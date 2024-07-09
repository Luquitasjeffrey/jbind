from dataclasses import dataclass
from pathlib import Path
import xml.etree.ElementTree as ET

@dataclass
class TargetModule:
    qualname: str
    public_only: bool
    use_conventions: bool
    manual: bool = False

@dataclass
class Dependency:
    group_id: str
    artifact_id: str
    version: str

@dataclass
class BuildOptions:
    target_dir: str
    java_version: str
    run_mvn: bool

def _get_build_options(root: ET.Element, base_dir: str):
    build = root.find("build")
    if build:
        target_dir = str(Path(base_dir) / build.get("targetDir", default="build"))
        java_version = build.get("java_version", default="11")
        run_mvn = _get_boolean(build.get("runMvn", default="true"))
        return BuildOptions(target_dir, java_version, run_mvn)
    else:
        return BuildOptions(str(Path(base_dir) / "build"), "11", True)


def _get_dependencies(root: ET.Element):
    dependencies = root.find("dependencies")
    if not dependencies:
        return
    
    for dependency in dependencies.findall("dependency"):
        group_id = dependency.find("groupId").text
        artifact_id = dependency.find("artifactId").text
        version = dependency.find("version").text
        yield Dependency(group_id, artifact_id, version)

def _get_boolean(boolstring: str):
    return boolstring.lower() == "true"

def _get_target_modules(root: ET.Element):
    modules = root.find("modules")
    for module in modules.findall("module"):
        qualname = module.get("qualname")
        public_only = _get_boolean(module.get("publicOnly", default="true"))
        use_conventions = _get_boolean(module.get("useConventions", default="true"))
        manual = _get_boolean(module.get("manual", default="false"))
        yield TargetModule(qualname, public_only, use_conventions, manual=manual)

class BindingConfiguration:
    def __init__(self, config_file: str, base_dir: str):
        tree = ET.parse(config_file)
        binding = tree.getroot()
        self.group_id = binding.find("groupId").text
        self.artifact_id = binding.find("artifactId").text
        self.version = binding.find("version").text
        self.target_modules = list(_get_target_modules(binding))
        self.dependencies = list(_get_dependencies(binding))
        self.build_options = _get_build_options(binding, base_dir)
        self._config_file = config_file

    @property
    def config_file(self):
        return self._config_file

def load_config(base_dir: str):
    return BindingConfiguration(str(Path(base_dir) / "jbindconfig.xml"), base_dir)

        
        



