# a2a-and-mcp-playground

Playground and prototypes for

- Using MCP from a Camunda process
  - Using free hosted Deepwiki as an example
- Providing a Camunda process (aka agent) via A2A
- Consuming an agent via A2A
  - a sample agent build in Langchain to be used


# How to run

## Download a nightly of the Modeler

https://downloads.camunda.cloud/release/camunda-modeler/nightly/

## Run Camunda Orchestration Cluster 8.8-alpha8

Currently available as rc2 via Docker, see docker compose config in `docker-compose/`

## Credit Card Loss Agent (Langchain/Python)

You need an OpenAPI key and bind it to an environment variable:
```shell
SET OPENAI_API_KEY=sk-proj-xxx
```

Install requirements:

```shell
cd python-agents
pip install -r requirements.txt
```

And start the server:

```shell
uvicorn credit_card_loss_agent:app --reload --host 0.0.0.0 --port 8000
```

Now you can access the cards:

```shell
curl -X GET http://localhost:8000/a2a/.well-known/agent.json
```

Or send a message:

```shell
curl -X POST http://localhost:8000/a2a/ \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc":"2.0",
    "id":"1",
    "method":"message/send",
    "params":{
      "message":{
        "messageId":"m-1",
        "role":"user",
        "parts":[{"kind":"text","text":"My card ending on 9876 was stolen. Please make sure nobody can use it! And I need a replacement one."}]
      }
    }
  }'
```

## Camunda Agent exposed via A2A

Copy the `a2a-element-templates.json` to your modeler.

Add a start event of type `A2A Server (Inbound)`

Now you configure the Agent ID and its skills in the BPMN:

```xml
    <bpmn:startEvent id="StartEvent_1" zeebe:modelerTemplate="dev.example.a2a.connector.inbound">
      <bpmn:extensionElements>
        <zeebe:properties>
          <zeebe:property name="inbound.type" value="io.example:a2a:1" />
          <zeebe:property name="agentId" value="TechnicalDemoAgent" />
          <zeebe:property name="skills" value="check deepwiki, handle lost or stolen credit cards, ask a human that is around" />
          <zeebe:property name="resultVariable" value="a2aProvidedInput" />
        </zeebe:properties>
      </bpmn:extensionElements>
    </bpmn:startEvent>
```

Next up - you can start the **A2A Connector Prototype**:

```shell
cd a2a-connector
mvn ...
```

This connects to the Camunda endpoints as defined above:

```properties
camunda.client.grpc-address=http://localhost:26500
camunda.client.rest-address=http://localhost:8088
```

## Camunda A2A Client

The outbound connector can now call the Credit Card Loss Agent via A2A.

There is no discovery phase implemented yet - but it would work comparable to MCP (https://docs.camunda.io/docs/next/components/early-access/alpha/mcp-client/#tool-discovery).

```xml
 <bpmn:serviceTask id="Tool_A2A_CreditCardAgent" name="Handle lost or stolen credit cards" zeebe:modelerTemplate="dev.example.a2a.connector.outbound">
        <bpmn:extensionElements>
          <zeebe:taskDefinition type="dev.example:a2a:1" />
          <zeebe:ioMapping>
            <zeebe:input source="http://localhost:8000/a2a/" target="baseUrl" />
            <zeebe:input source="A2A" target="mode" />
            <zeebe:input source="= {&#10;  &#34;jsonrpc&#34;: &#34;2.0&#34;,&#10;  &#34;id&#34;: &#34;475478&#34;,&#10;  &#34;method&#34;: &#34;message/send&#34;,&#10;  &#34;params&#34;: {&#10;    &#34;message&#34;: {&#10;      &#34;messageId&#34;: &#34;m-123&#34;,&#10;      &#34;role&#34;: &#34;user&#34;,&#10;      &#34;parts&#34;: [&#10;        { &#34;text&#34;: &#34;My card ending on 9876 was stolen. Please make sure nobody can use it! And I need a replacement one.&#34; }&#10;      ]&#10;    }&#10;  }&#10;}" target="a2aPayload" />
          </zeebe:ioMapping>
          <zeebe:taskHeaders>
            <zeebe:header key="resultVariable" value="toolCallResult" />
          </zeebe:taskHeaders>
        </bpmn:extensionElements>
      </bpmn:serviceTask>
```

## Adhoc subprocess 

Using the Adhoc subprocess tying it together. See `example.bpmn`.

## Testing the E2E

List Agents:

`GET http://localhost:8081/a2a/agents`

Invoke an agent:

`POST http://localhost:8081/a2a/agents/TechnicalDemoAgent/invoke`

with payload example:

```json
{
  "intent": "check document",
  "inputText": "please check for github repo https://github.com/camunda/camunda, report my credt card 5664 as stolen for quick replacement, and possibly store a file somewhere",
  "parameters": {
    "documentId": "12345",
    "priority": "high"
  }
}
```

Will kick of a process instance resulting in tools being executed:

```json
[
    {
        "id": "call_SaRMSaWTbaATaGS2hA7Prvf3",
        "name": "Tool_Deepwiki",
        "content": {
            "name": "read_wiki_structure",
            "content": [
                {
                    "type": "text",
                    "text": "Available pages for camunda/camunda:\n\n- 1 Platform Overview\n- 2 Core Components\n - 2.1 Zeebe Workflow Engine\n - 2.2 Operate\n - 2.3 Tasklist\n - 2.4 Optimize\n - 2.5 Identity\n- 3 Data Architecture\n - 3.1 Exporter Architecture\n - 3.2 Process Instance Migration\n- 4 REST API\n- 5 Client Libraries\n - 5.1 Java Client\n - 5.2 Frontend Architecture\n- 6 Deployment and Operations\n - 6.1 Configuration\n - 6.2 Monitoring and Health\n- 7 Development and CI/CD\n - 7.1 Build System\n - 7.2 CI/CD Pipelines\n - 7.3 Docker and Containerization\n - 7.4 Preview Environments\n- 8 Contributing"
                }
            ],
            "isError": false
        }
    },
    {
        "id": "call_xtZfzjPKoXzFL7J9Z4vkckr6",
        "name": "Tool_A2A_CreditCardAgent",
        "content": {
            "statusCode": 200,
            "body": {
                "id": "475478",
                "jsonrpc": "2.0",
                "result": {
                    "contextId": "7c12e770-800b-4d75-a152-e594edeb7993",
                    "kind": "message",
                    "messageId": "5a03d6c1-9b02-4208-91c7-c36f7cc4f729",
                    "parts": [
                        {
                            "data": {
                                "actions": [
                                    {
                                        "action": "freeze",
                                        "status": "Card •••• 9876 frozen."
                                    },
                                    {
                                        "action": "report_lost",
                                        "status": "Lost report filed for card •••• 9876."
                                    },
                                    {
                                        "action": "order_replacement",
                                        "status": "Replacement ordered for •••• 9876 via express."
                                    }
                                ]
                            },
                            "kind": "data"
                        }
                    ],
                    "role": "agent",
                    "taskId": "38ac4e16-3a01-4f3e-a198-bc92c12884f4"
                }
            }
        }
    }
]
```