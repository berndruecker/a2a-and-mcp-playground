// src/main/java/io/example/a2a/agent/AgentRegistry.java
package io.example.a2a;

import org.springframework.stereotype.Component;

import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.stream.Stream;

@Component
public class AgentRegistry {

  private final Map<String, Agent> agents = new ConcurrentHashMap<>();

  public Agent register(Agent agent) {
    agents.put(agent.getId(), agent);
    return agent;
  }

  public Optional<Agent> get(String name) {
    return Optional.ofNullable(agents.get(name));
  }

  public List<Agent> list() {
    return List.copyOf(agents.values());
  }

  public static List<String> parseCsv(String csv) {
    if (csv == null || csv.isBlank()) return List.of();
    return Stream.of(csv.split(","))
        .map(String::trim)
        .filter(s -> !s.isEmpty())
        .distinct()
        .toList();
  }

  public void remove(String agentId) {
    agents.remove(agentId);
  }
}
