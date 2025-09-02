// src/main/java/io/example/a2a/a2a/A2ACard.java
package io.example.a2a.a2a;

import java.util.List;
import java.util.Map;

public record A2ACard(
    String id,
    String title,
    String subtitle,
    String description,
    List<String> skills,
    List<A2AAction> actions,              // UI actions (e.g., Invoke)
    Map<String, Object> uiSchema          // optional, for client hints
) {}

