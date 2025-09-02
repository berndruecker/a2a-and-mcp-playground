// src/main/java/io/example/a2a/a2a/A2AInvoke.java
package io.example.a2a.a2a;

import java.util.Map;

public record A2AInvokeRequest(
    String inputText,                 // free text
    String intent,                    // optional structured intent
    Map<String, Object> parameters    // name/value parameters
) {}

