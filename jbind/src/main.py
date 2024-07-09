import argparse
from typing import Iterable
from configloader import TargetModule, load_config
from javafilemanager import JavaFileManager
import dependencymanager
import bind
import pom
import build

def bind_modules(targets: Iterable[TargetModule], target_dir: str, base_package: str):
    for target in targets:
        bind.bind_recursive(__import__(target.qualname), JavaFileManager(target_dir), base_package=base_package)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("base_dir")
    args = parser.parse_args()
    base_dir: str = args.base_dir
    config = load_config(base_dir)
    #bind_modules(config.target_modules, config.build_options.target_dir)
    pom.create_pom(config)
    bind_modules((module for module in config.target_modules if not module.manual), config.build_options.target_dir, base_package=config.group_id)
    
    if config.build_options.run_mvn:
        if any(module.manual for module in config.target_modules):
            build.run_maven(base_dir)

        if any(not module.manual for module in config.target_modules):
            build.run_maven(config.build_options.target_dir)

    dependencymanager.persist_binding(base_dir)

if __name__ == "__main__":
    main()
