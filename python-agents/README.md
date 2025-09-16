## A2A Agent

Run it:

```shell
pip install -r requirements.txt
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

## MCP Server

```shell
$env:EXTERNAL_BASE_URL="http://host.docker.internal:8200/"
SET EXTERNAL_BASE_URL=http://host.docker.internal:8200/
python account_support_agent.py
```

http://localhost:8200/sse

It provides the following tools:

1. Customer Account Lookup Tool, Functions:
  - search_customer(identifier --> account no, IBAN, card no) — returns customer ID 
  - get_customer_profile(customer_id) — returns name, contact info, KYC status
  - get_active_products(customer_id) — returns list of products (current accounts, cards, loans, etc.)
2. Account Action Management Tool, Functions:
  - freeze_account(account_id) / unfreeze_account(account_id) - returns success_status
  - reset_password(customer_id) - returns success_status
  - update_address(customer_id, new_address) - returns success_status