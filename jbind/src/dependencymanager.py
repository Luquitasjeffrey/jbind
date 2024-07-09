from functools import lru_cache
import os
import configloader
import shutil

HOME = os.path.expanduser("~")
LOCAL_BINDING_CACHE = f"{HOME}/.jbind"
MODULES_CONFIG_CACHE = f"{LOCAL_BINDING_CACHE}/modules"

def persist_binding(config_dir: str) -> None:
    config = configloader.load_config(config_dir)
    if not os.path.exists(MODULES_CONFIG_CACHE):
        os.makedirs(MODULES_CONFIG_CACHE)
    for module in config.target_modules:
        shutil.copy(config.config_file, f"{MODULES_CONFIG_CACHE}/{module.qualname}.xml")

@lru_cache(maxsize=None, typed=True)
def get_real_base_package(module_name: str, base_package: str) -> str:
    config_filepath = f"{MODULES_CONFIG_CACHE}/{module_name}"
    if not os.path.exists(config_filepath):
        return base_package
    config = configloader.BindingConfiguration(config_filepath, MODULES_CONFIG_CACHE)
    return config.group_id