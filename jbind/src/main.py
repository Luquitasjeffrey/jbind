from dataclasses import dataclass
import inspect
from types import ModuleType

BASE_PACKAGE = "org.jbind.bingings"
BASE_CLASS = "org.jbind.base.Binding"
NATIVE_CONVERSIONS = {
    object: "java.lang.Object",
    str: "java.lang.String",
    int: "int",
    bool: "boolean",
    float: "double",
    type: "java.lang.Class",
    None: "void"
}

def is_builtin(t: type):
    return t in NATIVE_CONVERSIONS

def is_inheritable(t: type):
    return not t in {
        bool, float, None, int, str, object
    }

def get_type_qn(t: type):
    if is_builtin(t):
        return NATIVE_CONVERSIONS[t]
    else:
        return f"{BASE_PACKAGE}.{t.__module__}.{t.__name__}"

def capitalize_first(s: str):
    return s[0].capitalize() + s[1:]

def globals_qual_class_name(module_name: str):
    subpackages = module_name.split(".")
    last = subpackages[-1]
    namesp = ".".join(subpackages[:-1])
    classname = capitalize_first(last)
    return f"{BASE_PACKAGE}.{namesp}.{classname}".replace("..", ".")

def unsnakify(snake_case: str):
    [first, *words] = (word for word in snake_case.split("_") if word)
    return first + "".join(capitalize_first(word) for word in words if word)

def get_package_name(module_name: str):
    return f"{BASE_PACKAGE}.{module_name}"

@dataclass
class Parameter:
    name: str
    type: type
    is_keyword: bool = False

    def bind(self, use_conventions = True):
        name = unsnakify(self.name) if use_conventions else self.name
        return f"{get_type_qn(self.type)} {name}"

@dataclass
class Function:
    name: str
    params: list[Parameter]
    return_type: type

    def bind(self, force_static = False, use_conventions = True, put_methodname_annotation = True):
        is_static = self.is_static() or force_static
        name = unsnakify(self.name) if use_conventions else self.name
        if is_static:
            params = ",".join(param.bind(use_conventions = use_conventions) for param in self.params)
            ret = f"    public static {get_type_qn(self.return_type)} {name}({params})"
        else:
            params = ",".join(param.bind(use_conventions = use_conventions) for param in self.params[1:])
            ret = f"    {get_type_qn(self.return_type)} {name}({params})"
        if put_methodname_annotation:
            return f'    @org.jbind.PyMethodName("{self.name}")\n' + ret
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

    #ignore properties
    def bind(self, module_qn: str, use_conventions = True, bind_public_only = True) -> str:
        ret = []
        ret.append(f"package {module_qn};")
        inheritted_classes = ",".join(get_type_qn(t) for t in self.inherits if is_inheritable(t))
        if inheritted_classes:
            inheritted_classes += f",{BASE_CLASS}"
        else:
            inheritted_classes = BASE_CLASS

        ret.append(f"public interface {self.name} extends {inheritted_classes} {{")
        if self.type_:
            ret.append(self.newinstance_method())
        for method in self.methods:
            if bind_public_only and method.name.startswith("_"):
                continue
            ret.append(f"{method.bind(use_conventions = use_conventions)};")
        ret.append("}")
        return "\n".join(ret)
    
    def newinstance_method(self):
        ret = []
        init_method = Function("__init__", "self", None)
        for m in self.methods:
            if m.name == "__init__":
                init_method = m
                break
        newinstance = Function("newInstance", init_method.params[1:], self.type_)
        return newinstance.bind(force_static=True, use_conventions=False, put_methodname_annotation=False) + ";"


@dataclass
class ModuleGlobals:
    functions: list[Function]

def get_module_functions(module: ModuleType):
    functions = []
    
    for _, obj in inspect.getmembers(module, inspect.isfunction):
        functions.append(convert_function_signature(obj))
    
    return functions

def get_module_classes(module: ModuleType) -> list[Class]:
    classes = []
    
    for name, obj in inspect.getmembers(module, inspect.isclass):
        methods = []
        for _, method_obj in inspect.getmembers(obj, inspect.isfunction):
            methods.append(convert_function_signature(method_obj))
        
        classes.append(Class(name=name, methods=methods, inherits=obj.__bases__, type_ = obj))
    
    return classes

def convert_function_signature(func):
    sig = inspect.signature(func)
    params = []

    for param in sig.parameters.values():
        param_type = param.annotation if param.annotation != inspect.Parameter.empty else object
        is_keyword = param.default != inspect.Parameter.empty
        params.append(Parameter(name=param.name, type=param_type, is_keyword=is_keyword))

    return_type = sig.return_annotation if sig.return_annotation != inspect.Signature.empty else object
    return Function(name=func.__name__, params=params, return_type=return_type)


def bind_module(module: ModuleType):
    module_name = module.__name__
    print(globals_qual_class_name(module_name))
    #print(get_module_functions(module))
    for clazz in get_module_classes(module):
        print(clazz.bind(get_package_name(module_name)))

if __name__ == "__main__":
    import monero.wallet as mod
    bind_module(mod)