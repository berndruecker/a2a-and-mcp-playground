package io.example.a2a.connector.inbound;

import org.springframework.beans.factory.config.ConfigurableBeanFactory;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Scope;

import io.example.a2a.A2AConnectorRuntimeApplication;
import io.example.a2a.AgentRegistry;

@Configuration
public class ConnectorConfig {

  @Bean
  @Scope(ConfigurableBeanFactory.SCOPE_PROTOTYPE)
  public A2AInboundConnector a2aInboundConnector(AgentRegistry registry) {
    return new A2AInboundConnector(registry);
  }
}