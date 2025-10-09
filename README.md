# Bank Support Agent Demo

This is bank support agent demo I used for CamundaCon NYC 2025.

It features:
- Agentic BPMN
- Multi-agent collaboration
- Omni-channel interaction in agents
- Employee engagement in agents
- Long running agents
- ...

# Business Architecture

Here is the overal business architecture this demo plays in. We use the levels from [Enterprise Process Orchestration](https://www.amazon.com/Enterprise-Process-Orchestration-Hands-Technology/dp/1394309678/).

 The yellow parts are covered in the demo.

![Simple example process](pics/business-architecture.png)

There are 4 business capabilities built out:

* Bank Support Agent (level 3 - end-to-end process): Agentic BPMN process in Camunda. See [process model](pics/banking-support-agent.png).
* Account Support Agent (level 4 - business capability): Simple Agentic BPMN process in Camunda. [process model](pics/account-support-agent.png)
* Loan Support Agent (level 4 - business capability): Agentic BPMN process in Camunda also using long-term memory and agent as a judge. [process model](pics/loan-support-agent.png)
* Card Support Agent (level 4 - business capability): Agent written in Python and Langchain. No graphical model.
* Loan Application Process (level 4 - business capability): Determinsitic BPMN process in Camunda. [process model](pics/loan-application.png)

![Simple example process](pics/agent-collaboration.png)

The Card Support Agent is pulled in via Agent-to-Agent protocol (A2A). Currently this runs on the prototypical connector in [a2a-connector](a2a-connector/), but can e switched to Camunda nativ capabilities once developed (targeting Camunda 8.9). It will call a dummy card management agent which can be found here: [python-agents/credit-card-support-a2a/](python-agents/credit-card-support-a2a/))

The Account Support Agent uses Model Context Protocol (MCP) to get available Account Management Tools from a MCP server (a dummy server written in python is contained in [python-agents/account-management-mcp/](python-agents/account-management-mcp/)).

# How to run


## Setup Camunda Orchestration Cluster 

* You need version >= 8.8.0
  * You could use the docker-compose file provided, but might want to switch to SaaS for integrating Chat

* Set the following Keys:
```properties
todo
```

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



## Data Format

Here are two examples of the typical data format for an agent:


```
supportCase
{
	"subject": "Help",
	"request": "I need to get my bank details to receive money internationally. My customer id = ACC123456789",
	"originalMessageInFull": "",
	"communicationContext": {
		"channel": "email",
		"channelId": "<UUID of the channel>",
		"emailAddress": "bernd.it.depends.ruecker@gmail.com",
		"conversationId": null
	},
	"customer": {
		"name": "Ruecker",
		"email": "bernd.it.depends.ruecker@gmail.com",
		"firstname": "Bernd",
		"id": 7839451262, // ACC123456789?
		"address": "Hauptstrasse 123, 10115 Berlin, Germany"
	}
}

riskAssesment
{
  riskClass: "B",
  riskAssesment: "No risks specific discovered, fair customer history, payback realistic",
  approval: true
}

loanApplication
{
  customerId: "15",
  lastName: "Ruecker",
  firstName: "Bernd",
  newCustomer: false,
  emailAddress: "bernd.it.depends.ruecker@gmail.com",
  requestedTerm: 36,
  amountRequested: 2000,
  moreData: "..."
}
```

Variable called **supportCase**:

```json

{
    "subject": "Request for bank details",
    "request": "I need to get my bank details to receive money internationally. My customer id = ACC123456789",
    "originalMessageInFull": "",
    "communicationContext": {
        "channel" : "email",
        "emailAddress": "bernd.ruecker@amunda.com",
        "conversationId": "emailmessageId"
    }
}

{
    "subject": "Request for bank details",
    "request": "I need to get my bank details to receive money internationally. My customer id = ACC123456789",
    "originalMessageInFull": "",
    "communicationContext": {
        "channel" : "chat",
        "channelId": "<UUID of the channel>",
        "emailAddress": "bernd.ruecker@amunda.com",
        "conversationId": "<UUID of the conversation>"
    }
}

{
    "subject": "Request for bank details",
    "request": "I need to get my bank details to receive money internationally. My customer id = ACC123456789",
    "originalMessageInFull": "",
    "resolution": "You need to do this",
    "communicationContext": {
        "channel" : "chat",
        "channelId": "<UUID of the channel>",
        "emailAddress": "bernd.ruecker@amunda.com",
        "conversationId": "<UUID of the conversation>"
    }
}
```

Response:

```json
{
  "resolution": "..."
  "thinking": "..."
}
```

Email Interface:

* communicationContext
* communicationContent
```JSON
{
    "subject": "RE: " + supportCase.subject,
    "text": fromAi(toolCall.response, "The text response to reply to the customer")
}
```

* response:
```JSON
{
  "status": "success",
  "email": "...",
  "text": "This is what we got"
}
```