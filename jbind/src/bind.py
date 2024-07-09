import builtins
from abc import ABC, abstractmethod
import inspect
from pathlib import Path
from types import ModuleType, FunctionType

from util import dbg, capitalize_first
from model import Function, Class, Parameter, get_type_qn

def _getcompositeattr(obj, compisite_attrname: str):
    ret = obj
    for attrname in compisite_attrname.split("."):
        ret = getattr(ret, attrname)
    return ret

def _get_module_functions(module: ModuleType) -> list[Function]:
    functions = []
    for _, obj in inspect.getmembers(module, inspect.isfunction):
        fn = _convert_function_signature(obj, module)
        if fn:
            functions.append(fn)

    return functions

def _get_module_classes(module: ModuleType) -> list[Class]:
    classes = []    
    for name, cls in inspect.getmembers(module, inspect.isclass):
        if cls.__module__ != module.__name__:
            continue
        #TODO: solve for __get__ and __set__ methods
        try:
            methods = []
            for _, method_obj in inspect.getmembers(cls, inspect.isfunction):
                method = _convert_function_signature(method_obj, module)
                if method:
                    methods.append(method)
            classes.append(Class(name=name, methods=methods, inherits=cls.__bases__, type_=cls, has_metaclass=cls.__class__!=type))
        except:
            pass
    return classes

def _get_type(type_hint, module: ModuleType) -> type:
    if type_hint == inspect.Parameter.empty or type_hint == inspect.Signature.empty:
        return object
    
    if isinstance(type_hint, type):
        return type_hint

    elif isinstance(type_hint, str):
        if hasattr(builtins, type_hint):
            return getattr(builtins, type_hint)
        else:
            try:
                return _getcompositeattr(module, type_hint)
            except:
                return object
    else:
        return object


def _convert_function_signature(func: FunctionType, module: ModuleType):
    if not func.__name__.isidentifier():
        return None
    sig = inspect.signature(func)
    params: list[Parameter] = []

    ignore_count = 0
    for param in sig.parameters.values():
        param_type = _get_type(param.annotation, module)
        is_keyword = param.default != inspect.Parameter.empty
        params.append(Parameter(name=param.name, type=param_type, is_keyword=is_keyword))

    for param in params:
        if not param.name.replace("_", ""):
            ignore_count += 1
            param.name = f"ignored{ignore_count}"

    return_type = _get_type(sig.return_annotation, module)
    return Function(name=func.__name__, params=params, return_type=return_type)

class PrintWritter(ABC):
    @abstractmethod
    def println(self, text: str) -> None: ...

    @abstractmethod
    def cached(self) -> bool: ...

    @abstractmethod
    def close(self) -> None: ...

class JavaFileManager(ABC):
    @abstractmethod
    def get_printwritter(self, class_name: str) -> PrintWritter: ...

def bind_simplemodule(module: ModuleType, file_manager: JavaFileManager,use_conventions = True, bind_public_only = True, bind_globals = True, *, base_package: str):
    module_name = module.__name__
    for clazz in _get_module_classes(module):
        printwritter = file_manager.get_printwritter(get_type_qn(clazz.type_, base_package))
        if not printwritter.cached():
            dbg(module_name)
            printwritter.println(clazz.bind(module_name, use_conventions=use_conventions,bind_public_only=bind_public_only, base_package=base_package))
        printwritter.close()

    if bind_globals:
        global_decls_name = capitalize_first(module_name.split(".")[-1])
        if global_decls_name == module_name.split(".")[-1]:
            global_decls_name += "Globals"
        global_decls_module_qualname = ".".join(module_name.split(".")[:-1])
        global_decls = Class([], global_decls_name, [], realname=module_name)
        dbg(f"{global_decls_module_qualname}.{global_decls_name}")
        for func in _get_module_functions(module):
            global_decls.methods.append(func)
        printwritter = file_manager.get_printwritter(base_package + "." + global_decls_module_qualname + "." + global_decls_name)
        printwritter.println(global_decls.bind(global_decls_module_qualname, use_conventions=use_conventions, bind_public_only=bind_public_only, force_static=True, base_package=base_package))
        printwritter.close()

def _iter_submodules(initfile: str):
    dir = "/".join(initfile.split("/")[:-1])
    for entry in Path(dir).iterdir():
        filename = entry.name
        if filename.startswith("__"):
            continue
        yield filename.replace(".py", "")

def _import_submodule(submodule: ModuleType, module_qualname: str):
    submodules = module_qualname.split(".")[1:]
    ret = submodule
    for submodule in submodules:
        try:
            ret = getattr(ret, submodule)
        except AttributeError:
            return None
    dbg(ret)
    return ret

def bind_recursive(module: ModuleType, file_manager: JavaFileManager, use_conventions = True, bind_public_only = True, *, base_package: str):
    if (not hasattr(module, '__file__')) or not module.__file__:
        return
    #base case: file
    if not module.__file__.endswith("__init__.py"):
        bind_simplemodule(module, file_manager=file_manager, use_conventions=use_conventions, bind_public_only=bind_public_only, base_package=base_package)

    #recursive case: module
    for submodule_name in _iter_submodules(module.__file__):
        submodule_qualname = module.__name__ + "." + submodule_name
        try:
            if submodule := _import_submodule(__import__(submodule_qualname), submodule_qualname):
                bind_recursive(submodule, file_manager, use_conventions, bind_public_only, base_package=base_package)    
        except ModuleNotFoundError:
            pass

