package io.example.a2a.a2a;

import java.util.Map;

public record A2AInvokeResponse(
    String status,                    // "ok" | "error"
    String message,                   // human-readable
    Map<String, Object> result,       // structured payload
    String[] actionsTaken,            // trace
    Boolean handoffRequired,
    String handoffReason
) {
  public static A2AInvokeResponse ok(String msg, Map<String,Object> res, String... steps) {
    return new A2AInvokeResponse("ok", msg, res, steps, false, null);
  }
  public static A2AInvokeResponse err(String msg) {
    return new A2AInvokeResponse("error", msg, Map.of(), new String[0], true, "Invocation failed");
  }
}
