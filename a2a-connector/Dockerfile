# Use multi-stage build for optimal image size
FROM maven:3.9-eclipse-temurin-21 AS build

# Set working directory
WORKDIR /app

# Copy pom.xml first for better layer caching
COPY pom.xml .

# Download dependencies (cached if pom.xml hasn't changed)
RUN mvn dependency:go-offline -B

# Copy source code
COPY src ./src

# Build the application
RUN mvn clean package -DskipTests -B

# Runtime stage with minimal JRE
FROM eclipse-temurin:21-jre

# Install curl for health checks
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd -r spring && useradd -r -g spring spring

# Set working directory
WORKDIR /app

# Copy the built JAR from build stage
COPY --from=build /app/target/a2a-connector-runtime-0.0.1.jar app.jar

# Change ownership to spring user
RUN chown spring:spring app.jar

# Switch to non-root user
USER spring

# Expose port (Cloud Run will override this with $PORT)
EXPOSE 8081

# Set default port if not provided
ENV PORT=8080

# Add health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:$PORT/actuator/health || exit 1

# Set JVM options for Cloud Run
ENV JAVA_OPTS="-Xmx512m -Xms256m -XX:+UseG1GC -XX:+UseContainerSupport -Djava.security.egd=file:/dev/./urandom"

# Run the application with verbose logging
CMD echo "Starting A2A Connector on port $PORT..." && \
    exec java $JAVA_OPTS \
    -Dserver.port=$PORT \
    -Dspring.profiles.active=${SPRING_PROFILES_ACTIVE:-production} \
    -Dlogging.level.root=INFO \
    -jar app.jar