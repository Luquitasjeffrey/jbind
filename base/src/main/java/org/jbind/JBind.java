package org.jbind;

import org.jpy.PyLib;

public class JBind {
    private static boolean isInitialized = false;

    public static void initialize() {
        if (isInitialized) {
            return;
        }
        initializeInternal();
        isInitialized = true;
    }

    private static void initializeInternal() {
        PyLib.startPython();
    }
}
