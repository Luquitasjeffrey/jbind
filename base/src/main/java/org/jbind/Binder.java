package org.jbind;

import org.jbind.annotation.PyClassInfo;
import org.jbind.annotation.PyMethodInfo;
import org.jbind.annotation.PyModuleInfo;
import org.jbind.base.Binding;
import org.jbind.internal.ObjectMapper;
import org.jpy.PyModule;
import org.jpy.PyObject;

import java.lang.reflect.Proxy;

public class Binder {
    public static <T> T getNewInstance(Class<T> clazz, Object... args) {
        PyClassInfo classInfo = clazz.getAnnotation(PyClassInfo.class);
        String className = classInfo.className();
        String moduleName = classInfo.module();

        try (PyModule pyModule = PyModule.importModule(moduleName);
             PyObject objectClass = pyModule.getAttribute(className)){
            PyObject instance = objectClass.call("__call__", mapArgs(args));
            PyObject type = instance.getType();
            if (!ObjectMapper.getInstance().hasMapping(clazz, type)) {
                ObjectMapper.getInstance().addMapping(clazz, type);
            }
            return buildProxy(clazz, instance);
        } catch (Exception e) {
            throw new RuntimeException(e);
        }
    }

    public static <T> T buildStaticProxy(Class<T> staticProxyInterface) {
        if (staticProxyInterface.getAnnotation(PyModuleInfo.class) != null) {
            PyModuleInfo moduleInfo = staticProxyInterface.getAnnotation(PyModuleInfo.class);
            String moduleName = moduleInfo.value();
            PyObject module = PyModule.importModule(moduleName);
            return buildProxy(staticProxyInterface, module);
        } else if (staticProxyInterface.getAnnotation(PyClassInfo.class) != null) {
            PyClassInfo classInfo = staticProxyInterface.getAnnotation(PyClassInfo.class);
            String moduleName = classInfo.module();
            String className = classInfo.className();
            try (PyObject module = PyModule.importModule(moduleName)) {
                PyObject pyClass = module.getAttribute(className);
                return buildProxy(staticProxyInterface, pyClass);
            }
        }
        return null;
    }

    private static Object[] mapArgs(Object[] args) {
        Object[] mappedArgs = new Object[args.length];
        for (int i = 0; i< mappedArgs.length; i++) {
            if (args[i] instanceof Binding binding) {
                mappedArgs[i] = binding._unwrap();
            } else {
                mappedArgs[i] = args[i];
            }
        }
        return mappedArgs;
    }

    public static <T> T buildProxy(Class<T> iface, PyObject wrapped) {
        Object ret = Proxy.newProxyInstance(iface.getClassLoader(), new Class[]{iface}, (proxy, method, args) -> {
            switch (method.getName()) {
                case "_unwrap" -> {
                    return wrapped;
                }
                case "toString" -> {
                    if (args == null || args.length == 0) {
                        return wrapped.str();
                    }
                }
                case "equals" -> {
                    if (args.length == 1) {
                        return wrapped.equals(args[0]);
                    }
                }
                case "hashCode" -> {
                    if (args == null || args.length == 0) {
                        return wrapped.hashCode();
                    }
                }
                case "close" -> {
                    if (args == null || args.length == 0) {
                        wrapped.close();
                        return null;
                    }
                }
            }

            String methodName = method.getAnnotation(PyMethodInfo.class).name();
            if (args == null) {
                args = new Object[0];
            }
            PyObject retVal = wrapped.call(methodName, args);
            Class<?> returnType = method.getReturnType();
            return ObjectMapper.getInstance().map(returnType, retVal);
        });
        return (T)ret;
    }
}
