package io.example.a2a;

import java.util.List;
import java.util.Map;

import io.camunda.connector.api.inbound.CorrelationRequest;
import io.camunda.connector.api.inbound.InboundConnectorContext;

public class Agent {
  
  private String id; 
  private List<String> skills;
  private String bpmnProcessId;
  private InboundConnectorContext connectorContext;
  
  public Agent(InboundConnectorContext connectorContext) {
    this.connectorContext = connectorContext;
  }

  public void onEvent(Map<String, Object> variables) {
    connectorContext.correlate(
        CorrelationRequest.builder().variables(variables).build());
  }
  
  public String getId() {
    return id;
  }
  public Agent setId(String id) {
    this.id = id;
    return this;
  }
  public List<String> getSkills() {
    return skills;
  }
  public Agent setSkills(List<String> skills) {
    this.skills = skills;
    return this;
  }
  public String getBpmnProcessId() {
    return bpmnProcessId;
  }
  public Agent setBpmnProcessId(String bpmnProcessId) {
    this.bpmnProcessId = bpmnProcessId;
    return this;
  }
}
