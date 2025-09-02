package io.example.a2a;

import java.util.List;
import java.util.Map;
import java.util.NoSuchElementException;
import java.util.Optional;

import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import io.camunda.client.CamundaClient;
import io.example.a2a.a2a.A2AAction;
import io.example.a2a.a2a.A2ACard;
import io.example.a2a.a2a.A2AInvokeRequest;
import io.example.a2a.a2a.A2AInvokeResponse;

@RestController
@RequestMapping("/a2a")
public class A2AController {

  private final AgentRegistry registry;
  
  private final CamundaClient camunda;

  public A2AController(AgentRegistry registry, CamundaClient camundaClient) {
    this.registry = registry;
    this.camunda = camundaClient;
  }

  /** Service manifest (simple discovery) */
  @GetMapping(value = "/manifest", produces = MediaType.APPLICATION_JSON_VALUE)
  public Map<String, Object> manifest() {
    return Map.of(
      "service", "io.example.a2a",
      "version", "1.0.0",
      "endpoints", Map.of(
        "listAgents", "/a2a/agents",
        "card", "/a2a/agents/{id}/card",
        "invoke", "/a2a/agents/{id}/invoke"
      )
    );
  }

  /** List agents (name + skills) */
  @GetMapping(value = "/agents", produces = MediaType.APPLICATION_JSON_VALUE)
  public List<Map<String, Object>> listAgents() {
    return registry.list().stream()
      .map(a -> Map.of("id", a.getId(), "skills", a.getSkills()))
      .toList();
  }

  /** Card for a given agent (used by UI to render and to know how to invoke) */
  @GetMapping(value = "/agents/{name}/card", produces = MediaType.APPLICATION_JSON_VALUE)
  public A2ACard card(@PathVariable("name") String name) {
    Agent a = registry.get(name).orElseThrow(() -> new NoSuchElementException("Unknown agent: " + name));

    // Minimal input schema the UI can turn into a form
    Map<String, Object> inputSchema = Map.of(
      "type", "object",
      "properties", Map.of(
        "inputText", Map.of("type", "string", "title", "Instruction / Request"),
        "intent", Map.of("type", "string", "title", "Intent (optional)"),
        "parameters", Map.of("type", "object", "title", "Parameters (optional)")
      )
    );

    A2AAction invoke = new A2AAction(
      "invoke",
      "Invoke Agent",
      "POST",
      "/a2a/agents/" + a.getId() + "/invoke",
      inputSchema
    );

    return new A2ACard(
      "agent:" + a.getId(),
      a.getId(),
      "Reusable A2A Agent",
      "Skills: " + String.join(", ", a.getSkills()),
      a.getSkills(),
      List.of(invoke),
      Map.of("icon", "sparkles", "category", "Banking")
    );
  }

  /** Invoke an agent (A2A call) */
  @PostMapping(value = "/agents/{id}/invoke", consumes = MediaType.APPLICATION_JSON_VALUE,
               produces = MediaType.APPLICATION_JSON_VALUE)
  public A2AInvokeResponse invoke(@PathVariable("id") String id, @RequestBody A2AInvokeRequest req) {
    Agent agent = registry.get(id).orElseThrow(() -> new NoSuchElementException("Unknown agent: " + id));

    // --- Very simple mock execution ---
    // If you already have internal routing, call into it here.
    String plan = planFromSkills(agent.getSkills(), req);
    Map<String, Object> result = Map.of(
      "agent", agent.getId(),
      "skillsUsed", plan,
      "echo", Map.of(
        "inputText", req.inputText(),
        "intent", req.intent(),
        "parameters", Optional.ofNullable(req.parameters()).orElse(Map.of())
      )
    );
    
    // Start a process instance here
    Map<String, Object> vars = Map.of("userRequest", req.inputText());
    agent.onEvent(vars);

    return A2AInvokeResponse.ok(
      "Agent " + agent.getId() + " executed.",
      result,
      "select-agent", "plan", "execute"
    );
  }

  private String planFromSkills(List<String> skills, A2AInvokeRequest req) {
    // naive selection: if an intent matches a skill, use it; else pick first skill
    String chosen = (req.intent() != null && skills.stream().anyMatch(s -> s.equalsIgnoreCase(req.intent())))
        ? req.intent()
        : skills.stream().findFirst().orElse("default");
    return chosen;
  }
}
