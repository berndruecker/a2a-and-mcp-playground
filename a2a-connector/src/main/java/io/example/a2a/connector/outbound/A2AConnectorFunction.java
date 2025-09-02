package io.example.a2a.connector.outbound;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import io.camunda.connector.api.annotation.OutboundConnector;
import io.camunda.connector.api.error.ConnectorException;
import io.camunda.connector.api.outbound.OutboundConnectorFunction;
import io.camunda.connector.api.outbound.OutboundConnectorContext;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.HashMap;
import java.util.Map;

@OutboundConnector(
  name = "A2A Connector",
  inputVariables = {"baseUrl","mode","intent","parameters","inputText","chatHistory","a2aPayload","headers"},
  type = "dev.example:a2a:1"
)
public class A2AConnectorFunction implements OutboundConnectorFunction {

  private static final ObjectMapper MAPPER = new ObjectMapper();
  private static final HttpClient CLIENT = HttpClient.newBuilder()
      .connectTimeout(Duration.ofSeconds(5))
      .build();

  @Override
  public Object execute(OutboundConnectorContext context) throws Exception {
    var req = context.bindVariables(A2AConnectorRequest.class);
    String mode = (req.getMode() == null ? "REST" : req.getMode()).trim().toUpperCase();

    // Build URL and payload
    String url;
    Map<String, Object> payload = new HashMap<>();

    switch (mode) {
      case "REST":
        // Call your FastAPI wrapper: POST /agents/card/handle
        url = normalize(req.getBaseUrl()) + "/agents/card/handle";
        if (req.getIntent() != null) payload.put("intent", req.getIntent());
        if (req.getParameters() != null) payload.put("parameters", req.getParameters());
        if (req.getInputText() != null) payload.put("input_text", req.getInputText());
        if (req.getChatHistory() != null) payload.put("chat_history", req.getChatHistory());
        break;

      case "A2A":
        // Call the mounted A2A app; default to generic JSON-RPC-style endpoint
        // If your A2A server uses a different path, just change here or pass full path in baseUrl.
        url = req.getBaseUrl() ;
        if (req.getA2aPayload() == null || req.getA2aPayload().isEmpty()) {
          // Minimal “text message” payload; adjust to your A2A flavor as needed.
          payload.put("text", req.getInputText() != null ? req.getInputText() : "Help with card management.");
        } else {
          payload.putAll(req.getA2aPayload());
        }
        break;

      default:
        throw new ConnectorException("config", "Unsupported mode: " + mode + " (use REST or A2A)");
    }

    var requestBuilder = HttpRequest.newBuilder()
        .uri(URI.create(url))
        .timeout(Duration.ofSeconds(15))
        .header("Content-Type", "application/json");

    if (req.getHeaders() != null) {
      req.getHeaders().forEach(requestBuilder::header);
    }

    var bodyBytes = MAPPER.writeValueAsBytes(payload);
    var httpReq = requestBuilder.POST(HttpRequest.BodyPublishers.ofByteArray(bodyBytes)).build();

    HttpResponse<String> resp;
    try {
      resp = CLIENT.send(httpReq, HttpResponse.BodyHandlers.ofString());
    } catch (Exception e) {
      throw new ConnectorException("network", "HTTP call failed: " + e.getMessage(), e);
    }

    Map<String, Object> respBody;
    try {
      respBody = MAPPER.readValue(resp.body(), new TypeReference<Map<String, Object>>(){});
    } catch (Exception parse) {
      // Return raw text if not JSON
      respBody = Map.of("raw", resp.body());
    }

    return new A2AConnectorResult(resp.statusCode(), respBody);
  }

  private static String normalize(String base) {
    if (base.endsWith("/")) return base.substring(0, base.length()-1);
    return base;
  }
}
