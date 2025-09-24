package io.example.other;

import org.springframework.stereotype.Component;

import io.camunda.spring.client.annotation.JobWorker;

@Component
public class NoopWorker {
  
  @JobWorker(type="noop")
  public void noop() {
    System.out.println("Noop worker does nothing...");
  }

}
