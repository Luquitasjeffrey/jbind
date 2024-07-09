package org.jbind.base;

import org.jpy.PyObject;

public interface Binding extends AutoCloseable {
    PyObject _unwrap();

    @Override
    default void close() {
        _unwrap().close();
    }

    void decref();
}
