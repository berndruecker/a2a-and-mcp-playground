package io.example.a2a.connector.outbound;

import java.util.Map;

public class A2AConnectorResult {
  private int statusCode;
  private Map<String, Object> body;

  public A2AConnectorResult(int statusCode, Map<String, Object> body) {
    this.statusCode = statusCode;
    this.body = body;
  }
  public int getStatusCode() { return statusCode; }
  public Map<String, Object> getBody() { return body; }
}
