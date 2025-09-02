package io.example.a2a.connector.outbound;


import jakarta.validation.constraints.NotBlank;
import java.util.Map;
import java.util.List;

public class A2AConnectorRequest {
  /** Base URL, e.g. http://localhost:8000 */
  @NotBlank
  private String baseUrl;

  /** One of: REST or A2A */
  private String mode = "REST";

  /** For REST mode: field values aligning with your FastAPI A2ARequest */
  private String intent; // optional
  private Map<String, Object> parameters; // optional
  private String inputText; // optional
  private List<Map<String, String>> chatHistory; // optional

  /** For A2A mode: raw JSON you want to POST to A2A endpoint (advanced) */
  private Map<String, Object> a2aPayload;

  /** Optional HTTP headers */
  private Map<String, String> headers;

  public String getBaseUrl() {
    return baseUrl;
  }

  public void setBaseUrl(String baseUrl) {
    this.baseUrl = baseUrl;
  }

  public String getMode() {
    return mode;
  }

  public void setMode(String mode) {
    this.mode = mode;
  }

  public String getIntent() {
    return intent;
  }

  public void setIntent(String intent) {
    this.intent = intent;
  }

  public Map<String, Object> getParameters() {
    return parameters;
  }

  public void setParameters(Map<String, Object> parameters) {
    this.parameters = parameters;
  }

  public String getInputText() {
    return inputText;
  }

  public void setInputText(String inputText) {
    this.inputText = inputText;
  }

  public List<Map<String, String>> getChatHistory() {
    return chatHistory;
  }

  public void setChatHistory(List<Map<String, String>> chatHistory) {
    this.chatHistory = chatHistory;
  }

  public Map<String, Object> getA2aPayload() {
    return a2aPayload;
  }

  public void setA2aPayload(Map<String, Object> a2aPayload) {
    this.a2aPayload = a2aPayload;
  }

  public Map<String, String> getHeaders() {
    return headers;
  }

  public void setHeaders(Map<String, String> headers) {
    this.headers = headers;
  }


}
