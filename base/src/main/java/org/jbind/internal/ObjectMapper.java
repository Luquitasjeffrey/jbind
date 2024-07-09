package org.jbind.internal;

import org.jbind.Binder;
import org.jbind.JBind;
import org.jpy.PyInputMode;
import org.jpy.PyObject;

import java.util.HashMap;
import java.util.Map;
import java.util.Set;

public class ObjectMapper {
    private static final ObjectMapper instance = new ObjectMapper();

    public static ObjectMapper getInstance() {
        return instance;
    }

    private static final Set<Class<?>> nativeMappings = Set.of(
            Integer.class,
            Double.class,
            Boolean.class,
            String.class
    );

    private final Map<PyObject, Class<?>> mappings = new HashMap<>();

    public ObjectMapper() {
        JBind.initialize();
        initNativeMappings();
    }

    private void initNativeMappings() {
        try(PyObject pyInt = PyObject.executeCode("1", PyInputMode.EXPRESSION);
            PyObject pyFloat = PyObject.executeCode("1.0", PyInputMode.EXPRESSION);
            PyObject pyBoolean = PyObject.executeCode("True", PyInputMode.EXPRESSION);
            PyObject pyString = PyObject.executeCode("''", PyInputMode.EXPRESSION)) {
            mappings.put(pyInt.getType(), Integer.class);
            mappings.put(pyFloat.getType(), Double.class);
            mappings.put(pyBoolean.getType(), Boolean.class);
            mappings.put(pyString.getType(), String.class);
        }
    }

    public boolean hasMapping(Class<?> javaType, PyObject pythonType) {
        return mappings.containsKey(pythonType) && javaType.isAssignableFrom(mappings.get(pythonType));
    }

    public void addMapping(Class<?> javaType, PyObject pythonType) {
        if (mappings.containsKey(pythonType) && nativeMappings.contains(mappings.get(pythonType))) {
            throw new RuntimeException("Attempting to create a custom wrapper for a native python type. You shouldnt be doing that!");
        }
        mappings.put(pythonType, javaType);
    }

    public Class<?> getMappedClass(Class<?> returnType, PyObject pyObject) {
        if (nativeMappings.contains(returnType)) {
            return returnType;
        }
        return mappings.get(pyObject.getType());
    }

    public Object map(Class<?> returnType, PyObject pyObject) {
        Class<?> mappedClass = getMappedClass(returnType, pyObject);
        if (nativeMappings.contains(mappedClass)) {
            if (mappedClass.equals(String.class)) {
                return pyObject.getStringValue();
            } else if (mappedClass.equals(Integer.class)) {
                return pyObject.getIntValue();
            } else if (mappedClass.equals(Boolean.class)) {
                return pyObject.getBooleanValue();
            } else if (mappedClass.equals(Double.class)) {
                return pyObject.getDoubleValue();
            }
        }
        return Binder.buildProxy(mappedClass, pyObject);
    }
}
