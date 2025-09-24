package io.example.other;

import java.util.Map;

import org.springframework.stereotype.Component;

import io.camunda.client.api.response.ActivatedJob;
import io.camunda.connector.api.annotation.Variable;
import io.camunda.spring.client.annotation.JobWorker;

@Component
public class EchoWorker {
  
  @JobWorker(type="echo")
  public Map<String, Object> echo(ActivatedJob job) {
    return Map.of("output", job.getVariable("input"));
  }

}
