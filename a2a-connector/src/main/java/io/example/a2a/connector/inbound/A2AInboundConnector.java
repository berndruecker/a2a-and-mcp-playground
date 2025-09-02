
package io.example.a2a.connector.inbound;

import java.util.List;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.fasterxml.jackson.databind.ObjectMapper;

import io.camunda.connector.api.annotation.InboundConnector;
import io.camunda.connector.api.inbound.InboundConnectorContext;
import io.camunda.connector.api.inbound.InboundConnectorExecutable;
import io.example.a2a.Agent;
import io.example.a2a.AgentRegistry;
import jakarta.validation.constraints.NotBlank;

//@Component
@InboundConnector(
    name = "A2A_INBOUND",
    type = "io.example:a2a:1"   // must match element template 'inbound.type'
)
public class A2AInboundConnector implements InboundConnectorExecutable {

  private static final Logger LOG = LoggerFactory.getLogger(A2AInboundConnector.class);

  private final AgentRegistry registry;
  private final ObjectMapper om = new ObjectMapper();

  // keep the agent id so we can deregister on deactivate
  private volatile String agentId;
  private volatile List<String> skills;

  public A2AInboundConnector(AgentRegistry registry) {
    this.registry = registry;
  }

  public static final class Properties {
    @NotBlank private String agentId;
    /** comma separated list of skills */
    private String skills;

    public String getAgentId() { return agentId; }
    public void setAgentId(String agentId) { this.agentId = agentId; }
    public String getSkills() { return skills; }
    public void setSkills(String skills) { this.skills = skills; }
  }

  @Override
  public void activate(InboundConnectorContext ctx) {
    var props = ctx.bindProperties(Properties.class); // validation supported by connector runtime
    this.agentId = props.getAgentId();
    List<String> skills = AgentRegistry.parseCsv(props.getSkills());
    registry.register(new Agent(ctx).setId(agentId).setSkills(skills));
    LOG.info("[A2A] Registered agent '{}' with {} skills via inbound connector", agentId, skills.size());
  }

  @Override
  public void deactivate() {
    if (agentId != null) {
      registry.remove(agentId);
      LOG.info("[A2A] Deactivated inbound connector; agent '{}' removed", agentId);
    }
  }
}
