from pathlib import Path
import xml.etree.ElementTree as ET
from configloader import BindingConfiguration
import util

def create_pom(config: BindingConfiguration):
    project = ET.Element("project")
    ET.SubElement(project, "modelVersion").text = "4.0.0"
    ET.SubElement(project, "groupId").text = config.group_id
    ET.SubElement(project, "artifactId").text = config.artifact_id
    ET.SubElement(project, "version").text = config.version
    properties = ET.SubElement(project, "properties")
    ET.SubElement(properties, "maven.compiler.source").text = config.build_options.java_version
    ET.SubElement(properties, "maven.compiler.target").text = config.build_options.java_version
    ET.SubElement(properties, "project.build.sourceEncoding").text = "UTF-8"
    dependencies = ET.SubElement(project, "dependencies")
    for dependency in config.dependencies:
        dependency_elem = ET.SubElement(dependencies, "dependency")
        ET.SubElement(dependency_elem, "groupId").text = dependency.group_id
        ET.SubElement(dependency_elem, "artifactId").text = dependency.artifact_id
        ET.SubElement(dependency_elem, "version").text = dependency.version
    
    tree = ET.ElementTree(project)
    filepath = str(Path(config.build_options.target_dir) / "pom.xml")
    util.ensure_dir_exists(filepath)
    tree.write(filepath, "utf-8", xml_declaration=True)