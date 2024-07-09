package org.jbind;

import org.jbind.annotation.PyClassInfo;
import org.jbind.annotation.PyMethodInfo;
import org.jbind.base.Binding;
import org.junit.Test;

public class TestBinder {
    @PyClassInfo(className = "Path", module = "pathlib")
    public interface Path extends Binding {
        static Path newInstance(String path) {
            return Binder.getNewInstance(Path.class, path);
        }

        @PyMethodInfo(name = "absolute")
        Path absolute();
    }

    @Test
    public void testInstanceCreation() {
        JBind.initialize();
        try (Path path = Path.newInstance("./myfile.txt");
             Path absolute = path.absolute()) {
            System.out.println(path);
            System.out.println(absolute);
        }
    }
}