package io.example;

import io.camunda.client.CamundaClientConfiguration;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.context.event.ApplicationReadyEvent;
import org.springframework.context.event.EventListener;
import org.springframework.core.env.Environment;
import org.springframework.stereotype.Component;

@Component
public class StartupLogger {

    private static final Logger logger = LoggerFactory.getLogger(StartupLogger.class);

    private final Environment environment;
    private final CamundaClientConfiguration camundaClientConfiguration;

    public StartupLogger(Environment environment, 
                        @Autowired(required = false) CamundaClientConfiguration camundaClientConfiguration) {
        this.environment = environment;
        this.camundaClientConfiguration = camundaClientConfiguration;
    }

    @EventListener(ApplicationReadyEvent.class)
    public void logStartup() {
        String port = environment.getProperty("server.port", "8080");
        
        logger.info("=".repeat(80));
        logger.info("🚀 A2A Connector started successfully!");
        logger.info("📡 Server running on port: {}", port);
        logger.info("🏥 Health check: http://localhost:{}/actuator/health", port);
        logger.info("=".repeat(80));
        
        
        // Log actual CamundaClientConfiguration if available
        if (camundaClientConfiguration != null) {
            logger.info("🔧 CAMUNDA CLIENT CONFIGURATION (ACTUAL):");
            try {
                // Use reflection to safely access configuration properties
                logger.info("   Configuration Object: {}", camundaClientConfiguration.getClass().getSimpleName());
                logger.info("   Configuration String: {}", camundaClientConfiguration.toString());
                
            } catch (Exception e) {
                logger.warn("   Could not read CamundaClientConfiguration: {}", e.getMessage());
            }
        } else {
            logger.warn("🔧 CAMUNDA CLIENT CONFIGURATION: Not available (bean not found)");
        }
        
        logger.info("=".repeat(80));
    }
    
}