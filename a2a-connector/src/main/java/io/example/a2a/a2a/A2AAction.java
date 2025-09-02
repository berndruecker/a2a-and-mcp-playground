package io.example.a2a.a2a;

import java.util.Map;

public record A2AAction(
    String id,
    String label,
    String method,        // "POST"
    String href,          // where to POST
    Map<String, Object> inputSchema // JSON Schema-ish for form rendering
) {}
