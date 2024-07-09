from abc import ABC
from dataclasses import dataclass
from typing import Any, Iterable, Literal, Union, Any
import collections

from util import dbg, capitalize_first
import dependencymanager

BASE_CLASS = "org.jbind.base.Binding"
NATIVE_CONVERSIONS = {
    Any: "java.lang.Object",
    object: "java.lang.Object",
    str: "java.lang.String",
    int: "int",
    bool: "boolean",
    float: "double",
    type: "org.jbind.types.PythonType",
    list: "org.jbind.bindings.builtins.List",
    dict: "org.jbind.bindings.builtins.Dict",
    collections.defaultdict: "org.jbind.bindings.collections.Defaultdict",
    slice: "org.jbind.bingins.builtins.Slice",
    bytes: "byte[]",
    Exception: "org.jbind.types.PythonExceptionWrapper",
    Literal: "java.lang.Object",
    Union: "java.lang.Object",
    UserWarning: "org.jbind.bindings.builtins.UserWarning",
    None: "void"
}

def _is_builtin(t: type):
    return t in NATIVE_CONVERSIONS

def _is_inheritable(t: type):
    return not t in {
        bool, float, None, int, str, object, ABC
    }

def _convert_to_valid_identifier(identifier: str) -> str:
    identifier = identifier.replace("-", "_")
    if identifier in {"interface", "abstract", "instanceof", "extends", "implements", "new", "final", "case", "default", "throw",
                      "boolean", "byte", "char", "short", "int", "long", "float", "double",
                      "assert", "const", "package"}:
        return identifier + "_"
    else:
        return identifier

def _get_package_name(module_name: str, base_package: str):
    rbp = dependencymanager.get_real_base_package(module_name, base_package)
    module_name_valid = ".".join(_convert_to_valid_identifier(identifier) for identifier in module_name.split("."))
    return f"{rbp}.{module_name_valid}"

def get_type_qn(t: type, base_package: str):
    if hasattr(t, '__origin__'):
        t = t.__origin__
        print(t)
    if _is_builtin(t):
        return NATIVE_CONVERSIONS[t]
    else:
        return f"{_get_package_name(t.__module__, base_package)}.{t.__name__}"

def _unsnakify(snake_case: str):
    try:
        [first, *words] = (word for word in snake_case.split("_") if word)
        ret = first + "".join(capitalize_first(word) for word in words if word)
        if ret == snake_case:
            ret = ""
            for c in snake_case:
                if c.isupper():
                    ret += "_"
                ret += c
        return ret
    except ValueError:
        return "_"

def _is_ambiguous(f: "Function"):
    if f.name == "close" and f.return_type != None:
        return True
    elif f.name == "_unwrap":
        return True
    return False

@dataclass(frozen=True)
class Parameter:
    name: str
    type: type
    is_keyword: bool = False

    def bind(self, use_conventions = True, *, base_package: str):
        name = _convert_to_valid_identifier(_unsnakify(self.name) if use_conventions else self.name)
        try:
            return f"{get_type_qn(self.type, base_package)} {name}"
        except Exception as e:
            print(self)
            raise e
    
    def bind_name(self, use_conventions = True):
        return _convert_to_valid_identifier(_unsnakify(self.name) if use_conventions else self.name)

@dataclass
class Function:
    name: str
    params: list[Parameter]
    return_type: type

    def __hash__(self) -> int:
        return hash(self.name)
    
    def __eq__(self, other) -> bool:
        return self.name == other.name

    def bind(self, force_static = False, use_conventions = True, put_methodname_annotation = True, use_staticproxy = True, *, base_package: str):
        is_static = self.is_static() or force_static
        name = _convert_to_valid_identifier(_unsnakify(self.name) if use_conventions else self.name)
        if _is_ambiguous(self):
            name += "_"
        if is_static:
            params = ",".join(param.bind(use_conventions = use_conventions, base_package=base_package) for param in self.params)
            if use_staticproxy:
                retls = []
                retls.append(f"    public static {get_type_qn(self.return_type, base_package)} {name}({params}){{")
                retls.append(f"        {'return ' if self.return_type is not None else ''}_staticProxy.{name}({','.join(param.bind_name(use_conventions = use_conventions) for param in self.params)});")
                
                retls.append( "    }")
                ret = "\n".join(retls)
            else:
                ret = f"    public static {get_type_qn(self.return_type, base_package)} {name}({params})"
        else:
            params = ",".join(param.bind(use_conventions = use_conventions, base_package=base_package) for param in self.params[1:])
            ret = f"    {get_type_qn(self.return_type, base_package)} {name}({params})"
        if put_methodname_annotation:
            return f'    @org.jbind.annotation.PyMethodInfo(name="{self.name}")\n' + ret
        else:
            return ret

    def is_instance(self):
        return len(self.params) >= 1 and self.params[0].name == "self"
    
    def is_static(self):
        return not self.is_instance()

@dataclass
class Class:
    inherits: list[type]
    name: str
    methods: list[Function]
    type_: type | None = None
    instantiatable: bool = False
    realname: str | None = None
    has_metaclass: bool = False

    def __post_init__(self):
        method_map: dict[str, Function] = {}
        for meth in self.methods:
            if meth.name in method_map:
                continue
            method_map[meth.name] = meth
        self.methods = list(method_map.values())
        self.name = _convert_to_valid_identifier(self.name)

    #ignore properties
    def bind(self, module_qn: str | None = None, use_conventions=True, bind_public_only=True, force_static=False, is_public=True, force_instance=False, *, base_package: str) -> str:
        
        statics = lambda: (method for method in self.methods if (not force_instance) and (force_static or method.is_static()))
        instances = lambda: (method for method in self.methods if force_instance or ((not force_static) and method.is_instance()))
        ret = []
        if module_qn:
            ret.append(f"package {_get_package_name(module_qn, base_package)};")
        if staticproxy := self._build_staticproxy(statics(), module_qn, use_conventions=use_conventions, bind_public_only=bind_public_only, base_package=base_package):
            ret.append(staticproxy)
        
        if not self.has_metaclass:
            inheritted_classes = ",".join(get_type_qn(t, base_package) for t in self.inherits if _is_inheritable(t))
        else:
            inheritted_classes = None
        
        if inheritted_classes:
            inheritted_classes += f",{BASE_CLASS}"
        else:
            inheritted_classes = BASE_CLASS
        
        if module_qn:
            ret.append(self._get_class_info_annotation(module_qn))
        ret.append(f"{'public ' if is_public else ''}interface {self.name} extends {inheritted_classes} {{")
        if staticproxy:
            sp_name = self._get_staticproxy_name()
            ret.append(f"    static {sp_name} _staticProxy = org.jbind.Binder.buildStaticProxy({sp_name}.class);")
        if self.type_:
            ret.append(self.newinstance_method(use_conventions, base_package=base_package))

        for instance in set(instances()):
            if bind_public_only and instance.name.startswith("_"):
                continue
            ret.append(f"{instance.bind(use_conventions=use_conventions, base_package=base_package)};")

        
        for static in set(statics()):
            if bind_public_only and static.name.startswith("_"):
                continue
            ret.append(static.bind(force_static=True, use_conventions=use_conventions, put_methodname_annotation=False, base_package=base_package))

        ret.append("}")
        return "\n".join(ret)
    
    def _get_class_info_annotation(self, module_qn: str):
        return f'@org.jbind.annotation.PyClassInfo(module="{module_qn}",className="{self.name}")'
    
    def _get_staticproxy_name(self):
        return f"_{self.name}StaticProxy"

    def _is_module(self):
        return not self.type_
    
    def _build_staticproxy(self, staticmethods: Iterable[Function], module_qn: str,use_conventions=True, bind_public_only=True, *, base_package: str) -> str:
        fake_instance = []
        for s in staticmethods:
            params = [Parameter("self", Any, False)]
            params.extend(s.params)
            fake_instance.append(Function(s.name, params, s.return_type))
        static_proxy = Class([], self._get_staticproxy_name(), fake_instance)
        if len(fake_instance)==0:
            return None
        ret = []
        if self._is_module():
            ret.append(f'@org.jbind.annotation.PyModuleInfo("{self.realname}")')
        else:
            ret.append(self._get_class_info_annotation(module_qn))
        ret.append(static_proxy.bind(use_conventions=use_conventions, bind_public_only=bind_public_only, is_public=False, base_package=base_package))
        return "\n".join(ret)

    
    def newinstance_method(self, use_conventions: bool, *, base_package: str):
        init_method = Function("__init__", [Parameter("self", Any)], None)
        for m in self.methods:
            if m.name == "__init__":
                init_method = m
                break
        newinstance = Function("new_instance", init_method.params[1:], self.type_)
        signature = newinstance.bind(force_static=True, use_conventions=use_conventions, put_methodname_annotation=False, use_staticproxy=False, base_package=base_package)
        parameters = ",".join(_convert_to_valid_identifier(_unsnakify(param.name)) for param in newinstance.params)
        if parameters:
            parameters = "," + parameters
        implementation = f"        return org.jbind.Binder.getNewInstance({self.name}.class{parameters});"
        return "\n".join((signature + "{", implementation, "    }")
                         )


@dataclass
class ModuleGlobals:
    functions: list[Function]