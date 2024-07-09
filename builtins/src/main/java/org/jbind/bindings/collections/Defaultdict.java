package org.jbind.bindings.collections;

import org.jbind.annotation.PyClassInfo;
import org.jbind.bindings.builtins.Dict;

@PyClassInfo(className = "Defaultdict", module = "collections")
public interface Defaultdict<K, V> extends Dict<K, V> {
}
