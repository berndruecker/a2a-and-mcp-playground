import asyncio
import json
import logging
import os
import uuid
from typing import Any, Callable, Dict, Optional, Tuple
from datetime import datetime

from fastapi import FastAPI, Header, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse
from urllib.parse import urljoin

# -----------------------------------------------------------------------------
# Logging
# -----------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
log = logging.getLogger("account-support-mcp")

def _short(obj: Any, maxlen: int = 500) -> str:
    try:
        s = json.dumps(obj, ensure_ascii=False, default=str)
    except Exception:
        s = str(obj)
    return s if len(s) <= maxlen else s[:maxlen] + f"... (+{len(s)-maxlen} chars)"

# -----------------------------------------------------------------------------
# App Configuration
# -----------------------------------------------------------------------------
app = FastAPI(title="Account Support MCP Server", version="1.0.0")

EXTERNAL_BASE_URL = os.getenv("EXTERNAL_BASE_URL", "http://host.docker.internal:8200/")
ALLOWED_ORIGINS = {
    "http://localhost:3000", 
    "http://localhost", 
    "http://127.0.0.1",
    "http://host.docker.internal:8200",
    "http://host.docker.internal:3000",
    "http://host.docker.internal",
}
SESSIONS: Dict[str, asyncio.Queue] = {}
SESSION_QUEUE_MAX = 100
SSE_PING_SECONDS = 15
MCP_PROTOCOL_VERSION = "2025-06-18"

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(ALLOWED_ORIGINS),
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

def check_origin(origin: Optional[str]):
    if origin is None:
        return
    base = origin.split("/", 3)[:3]
    host = "/".join(base)
    if host not in ALLOWED_ORIGINS:
        raise HTTPException(status_code=403, detail="Origin not allowed")

def external_base_url(request: Request) -> str:
    # If EXTERNAL_BASE_URL is explicitly set, use it
    if EXTERNAL_BASE_URL:
        return EXTERNAL_BASE_URL.rstrip("/") + "/"
    
    # Otherwise, construct from request headers
    scheme = request.headers.get("x-forwarded-proto") or request.url.scheme
    host = request.headers.get("x-forwarded-host") or request.headers.get("host") or request.url.netloc
    prefix = request.headers.get("x-forwarded-prefix", "").rstrip("/")
    
    # Special handling for Docker internal networking
    if "host.docker.internal" in str(host):
        base = f"{scheme}://host.docker.internal:8200/"
    else:
        base = f"{scheme}://{host}/"
    
    return base if not prefix else f"{scheme}://{host}{prefix}/"

# -----------------------------------------------------------------------------
# JSON-RPC helpers
# -----------------------------------------------------------------------------
def jrpc_result(id_, result): 
    return {"jsonrpc": "2.0", "id": id_, "result": result}

def jrpc_error(id_, code, msg, data=None): 
    return {"jsonrpc": "2.0", "id": id_, "error": {"code": code, "message": msg, "data": data or {}}}

# -----------------------------------------------------------------------------
# Mock Customer Database
# -----------------------------------------------------------------------------
MOCK_CUSTOMERS = {
    "CUST001": {
        "customer_id": "CUST001",
        "name": "John Smith",
        "email": "john.smith@email.com",
        "phone": "+1-555-0123",
        "address": "123 Main St, New York, NY 10001",
        "kyc_status": "VERIFIED",
        "date_created": "2020-01-15"
    },
    "CUST002": {
        "customer_id": "CUST002", 
        "name": "Sarah Johnson",
        "email": "sarah.johnson@email.com",
        "phone": "+1-555-0456",
        "address": "456 Oak Ave, Los Angeles, CA 90210",
        "kyc_status": "PENDING",
        "date_created": "2021-03-22"
    },
    "CUST003": {
        "customer_id": "CUST003",
        "name": "Michael Brown",
        "email": "michael.brown@email.com", 
        "phone": "+1-555-0789",
        "address": "789 Pine St, Chicago, IL 60601",
        "kyc_status": "VERIFIED",
        "date_created": "2019-07-10"
    }
}

MOCK_IDENTIFIERS = {
    # Account numbers
    "ACC123456789": "CUST001",
    "ACC987654321": "CUST002", 
    "ACC555666777": "CUST003",
    # Card numbers (last 4 digits for security)
    "****1234": "CUST001",
    "****5678": "CUST002",
    "****9012": "CUST003",
    # SWIFT/BIC codes (for international transfers)
    "CHASUS33": "CUST001",  # Chase Bank
    "BOFAUS3N": "CUST002",  # Bank of America
    "CITIUS33": "CUST003"   # Citibank
    # Note: US banks do not use IBAN codes - they use routing numbers + account numbers
}

MOCK_PRODUCTS = {
    "CUST001": [
        {
            "product_id": "CHK001", 
            "type": "checking_account", 
            "status": "active", 
            "balance": 2500.00,
            "swift_code": "CHASUS33",
            "bic_code": "CHASUS33",
            "bank_name": "Chase Bank",
            "routing_number": "021000021",
            "account_number": "ACC123456789"
        },
        {
            "product_id": "CC001", 
            "type": "credit_card", 
            "status": "active", 
            "limit": 5000.00
        },
        {
            "product_id": "SAV001", 
            "type": "savings_account", 
            "status": "active", 
            "balance": 15000.00,
            "swift_code": "CHASUS33",
            "bic_code": "CHASUS33",
            "bank_name": "Chase Bank",
            "routing_number": "021000021",
            "account_number": "SAV123456789"
        }
    ],
    "CUST002": [
        {
            "product_id": "CHK002", 
            "type": "checking_account", 
            "status": "active", 
            "balance": 1200.00,
            "swift_code": "BOFAUS3N",
            "bic_code": "BOFAUS3N",
            "bank_name": "Bank of America",
            "routing_number": "026009593",
            "account_number": "ACC987654321"
        },
        {
            "product_id": "LON001", 
            "type": "personal_loan", 
            "status": "active", 
            "principal": 10000.00
        }
    ],
    "CUST003": [
        {
            "product_id": "CHK003", 
            "type": "checking_account", 
            "status": "frozen", 
            "balance": 3200.00,
            "swift_code": "CITIUS33",
            "bic_code": "CITIUS33",
            "bank_name": "Citibank",
            "routing_number": "021000089",
            "account_number": "ACC555666777"
        },
        {
            "product_id": "CC003", 
            "type": "credit_card", 
            "status": "active", 
            "limit": 10000.00
        },
        {
            "product_id": "SAV003", 
            "type": "savings_account", 
            "status": "active", 
            "balance": 25000.00,
            "swift_code": "CITIUS33",
            "bic_code": "CITIUS33",
            "bank_name": "Citibank",
            "routing_number": "021000089",
            "account_number": "SAV555666777"
        },
        {
            "product_id": "MTG001", 
            "type": "mortgage", 
            "status": "active", 
            "principal": 250000.00
        }
    ]
}

# Account status tracking
ACCOUNT_STATUS = {
    "CHK001": "active",
    "CHK002": "active", 
    "CHK003": "frozen",
    "CC001": "active",
    "CC003": "active",
    "SAV001": "active",
    "SAV003": "active",
    "LON001": "active",
    "MTG001": "active"
}

# -----------------------------------------------------------------------------
# Customer Account Lookup Tool Functions
# -----------------------------------------------------------------------------
def search_customer(identifier: str) -> Dict[str, Any]:
    """Search for customer by account number, card number, or SWIFT/BIC code
    Note: US banks do not use IBAN codes - use routing number + account number instead"""
    customer_id = MOCK_IDENTIFIERS.get(identifier)
    if not customer_id:
        return {
            "success": False,
            "error": "Customer not found",
            "identifier": identifier,
            "note": "US banks do not use IBAN codes. Use account number, card number, or SWIFT/BIC code."
        }
    
    return {
        "success": True,
        "customer_id": customer_id,
        "identifier": identifier,
        "timestamp": datetime.now().isoformat()
    }

def get_customer_profile(customer_id: str) -> Dict[str, Any]:
    """Get customer profile information"""
    customer = MOCK_CUSTOMERS.get(customer_id)
    if not customer:
        return {
            "success": False,
            "error": "Customer not found",
            "customer_id": customer_id
        }
    
    return {
        "success": True,
        **customer,
        "timestamp": datetime.now().isoformat()
    }

def get_active_products(customer_id: str) -> Dict[str, Any]:
    """Get list of active products for customer"""
    products = MOCK_PRODUCTS.get(customer_id, [])
    if not products:
        return {
            "success": False,
            "error": "No products found for customer",
            "customer_id": customer_id
        }
    
    return {
        "success": True,
        "customer_id": customer_id,
        "products": products,
        "total_products": len(products),
        "timestamp": datetime.now().isoformat()
    }

def get_banking_details(account_id: str) -> Dict[str, Any]:
    """Get banking details including SWIFT/BIC codes for an account
    US banks use routing numbers + account numbers, not IBAN codes"""
    # Find the account across all customers
    for customer_id, products in MOCK_PRODUCTS.items():
        for product in products:
            if product["product_id"] == account_id:
                if product["type"] in ["checking_account", "savings_account"]:
                    banking_details = {
                        "account_id": account_id,
                        "customer_id": customer_id,
                        "account_type": product["type"],
                        "status": product["status"],
                        "swift_code": product.get("swift_code"),
                        "bic_code": product.get("bic_code"),
                        "bank_name": product.get("bank_name"),
                        "routing_number": product.get("routing_number"),
                        "account_number": product.get("account_number"),
                        "balance": product.get("balance", 0.00),
                        "iban": None,  # US banks do not use IBAN codes
                        "iban_note": "US banks do not use IBAN codes. Use routing number + account number for domestic transfers, SWIFT code for international."
                    }
                    return {
                        "success": True,
                        "banking_details": banking_details,
                        "timestamp": datetime.now().isoformat()
                    }
                else:
                    return {
                        "success": False,
                        "error": "Account type does not support international transfers",
                        "account_id": account_id,
                        "account_type": product["type"]
                    }
    
    return {
        "success": False,
        "error": "Account not found",
        "account_id": account_id
    }

def search_by_swift_bic(swift_bic_code: str) -> Dict[str, Any]:
    """Search for accounts by SWIFT or BIC code"""
    matching_accounts = []
    
    for customer_id, products in MOCK_PRODUCTS.items():
        customer_info = MOCK_CUSTOMERS.get(customer_id, {})
        for product in products:
            if (product.get("swift_code") == swift_bic_code or 
                product.get("bic_code") == swift_bic_code):
                account_info = {
                    "account_id": product["product_id"],
                    "customer_id": customer_id,
                    "customer_name": customer_info.get("name", "Unknown"),
                    "account_type": product["type"],
                    "status": product["status"],
                    "swift_code": product.get("swift_code"),
                    "bic_code": product.get("bic_code"),
                    "bank_name": product.get("bank_name"),
                    "routing_number": product.get("routing_number")
                }
                matching_accounts.append(account_info)
    
    if not matching_accounts:
        return {
            "success": False,
            "error": "No accounts found for SWIFT/BIC code",
            "swift_bic_code": swift_bic_code
        }
    
    return {
        "success": True,
        "swift_bic_code": swift_bic_code,
        "matching_accounts": matching_accounts,
        "total_accounts": len(matching_accounts),
        "timestamp": datetime.now().isoformat()
    }

def get_iban_info(account_id: str) -> Dict[str, Any]:
    """Handle IBAN requests for US accounts - explains why IBAN is not applicable"""
    # Check if account exists first
    account_found = False
    for customer_id, products in MOCK_PRODUCTS.items():
        for product in products:
            if product["product_id"] == account_id:
                account_found = True
                break
        if account_found:
            break
    
    if not account_found:
        return {
            "success": False,
            "error": "Account not found",
            "account_id": account_id
        }
    
    return {
        "success": False,
        "error": "IBAN not applicable for US bank accounts",
        "account_id": account_id,
        "explanation": "US banks do not use IBAN (International Bank Account Number) codes. Instead, US banks use:",
        "alternatives": {
            "domestic_transfers": "Routing number + Account number",
            "international_transfers": "SWIFT/BIC code + Routing number + Account number",
            "wire_transfers": "SWIFT code + Bank name + Account details"
        },
        "note": "IBAN is primarily used by European banks and some other international banks, but not by US financial institutions.",
        "timestamp": datetime.now().isoformat()
    }

# -----------------------------------------------------------------------------
# Account Action Management Tool Functions  
# -----------------------------------------------------------------------------
def freeze_account(account_id: str) -> Dict[str, Any]:
    """Freeze a customer account"""
    if account_id not in ACCOUNT_STATUS:
        return {
            "success": False,
            "error": "Account not found",
            "account_id": account_id
        }
    
    ACCOUNT_STATUS[account_id] = "frozen"
    
    # Update the product status in mock data
    for customer_id, products in MOCK_PRODUCTS.items():
        for product in products:
            if product["product_id"] == account_id:
                product["status"] = "frozen"
                break
    
    return {
        "success": True,
        "account_id": account_id,
        "action": "freeze",
        "new_status": "frozen",
        "timestamp": datetime.now().isoformat(),
        "reference_id": f"FRZ-{uuid.uuid4().hex[:8].upper()}"
    }

def unfreeze_account(account_id: str) -> Dict[str, Any]:
    """Unfreeze a customer account"""
    if account_id not in ACCOUNT_STATUS:
        return {
            "success": False,
            "error": "Account not found", 
            "account_id": account_id
        }
    
    ACCOUNT_STATUS[account_id] = "active"
    
    # Update the product status in mock data
    for customer_id, products in MOCK_PRODUCTS.items():
        for product in products:
            if product["product_id"] == account_id:
                product["status"] = "active"
                break
    
    return {
        "success": True,
        "account_id": account_id,
        "action": "unfreeze",
        "new_status": "active",
        "timestamp": datetime.now().isoformat(),
        "reference_id": f"UFZ-{uuid.uuid4().hex[:8].upper()}"
    }

def reset_password(customer_id: str) -> Dict[str, Any]:
    """Reset customer password"""
    customer = MOCK_CUSTOMERS.get(customer_id)
    if not customer:
        return {
            "success": False,
            "error": "Customer not found",
            "customer_id": customer_id
        }
    
    # Generate temporary password
    temp_password = f"TEMP-{uuid.uuid4().hex[:8].upper()}"
    
    return {
        "success": True,
        "customer_id": customer_id,
        "action": "password_reset",
        "temporary_password": temp_password,
        "expires_in_hours": 24,
        "timestamp": datetime.now().isoformat(),
        "reference_id": f"PWD-{uuid.uuid4().hex[:8].upper()}"
    }

def update_address(customer_id: str, new_address: str) -> Dict[str, Any]:
    """Update customer address"""
    customer = MOCK_CUSTOMERS.get(customer_id)
    if not customer:
        return {
            "success": False,
            "error": "Customer not found",
            "customer_id": customer_id
        }
    
    old_address = customer["address"]
    customer["address"] = new_address
    
    return {
        "success": True,
        "customer_id": customer_id,
        "action": "address_update",
        "old_address": old_address,
        "new_address": new_address,
        "timestamp": datetime.now().isoformat(),
        "reference_id": f"ADR-{uuid.uuid4().hex[:8].upper()}"
    }

# -----------------------------------------------------------------------------
# MCP Tool Registry
# -----------------------------------------------------------------------------
ToolFn = Callable[[Dict[str, Any]], Dict[str, Any]]
TOOL_REGISTRY: Dict[str, Tuple[ToolFn, Dict[str, Any]]] = {
    "search_customer": (
        lambda args: search_customer(args.get("identifier", "")),
        {
            "type": "object",
            "properties": {
                "identifier": {
                    "type": "string", 
                    "description": "Customer identifier: account number, card number, or SWIFT/BIC code (US banks do not use IBAN)"
                }
            },
            "required": ["identifier"]
        }
    ),
    "get_customer_profile": (
        lambda args: get_customer_profile(args.get("customer_id", "")),
        {
            "type": "object",
            "properties": {
                "customer_id": {
                    "type": "string",
                    "description": "Unique customer identifier"
                }
            },
            "required": ["customer_id"]
        }
    ),
    "get_active_products": (
        lambda args: get_active_products(args.get("customer_id", "")),
        {
            "type": "object", 
            "properties": {
                "customer_id": {
                    "type": "string",
                    "description": "Unique customer identifier"
                }
            },
            "required": ["customer_id"]
        }
    ),
    "freeze_account": (
        lambda args: freeze_account(args.get("account_id", "")),
        {
            "type": "object",
            "properties": {
                "account_id": {
                    "type": "string",
                    "description": "Account/product identifier to freeze"
                }
            },
            "required": ["account_id"]
        }
    ),
    "unfreeze_account": (
        lambda args: unfreeze_account(args.get("account_id", "")),
        {
            "type": "object",
            "properties": {
                "account_id": {
                    "type": "string", 
                    "description": "Account/product identifier to unfreeze"
                }
            },
            "required": ["account_id"]
        }
    ),
    "reset_password": (
        lambda args: reset_password(args.get("customer_id", "")),
        {
            "type": "object",
            "properties": {
                "customer_id": {
                    "type": "string",
                    "description": "Customer identifier for password reset"
                }
            },
            "required": ["customer_id"]
        }
    ),
    "update_address": (
        lambda args: update_address(args.get("customer_id", ""), args.get("new_address", "")),
        {
            "type": "object",
            "properties": {
                "customer_id": {
                    "type": "string",
                    "description": "Customer identifier"
                },
                "new_address": {
                    "type": "string",
                    "description": "New address for the customer"
                }
            },
            "required": ["customer_id", "new_address"]
        }
    ),
    "get_banking_details": (
        lambda args: get_banking_details(args.get("account_id", "")),
        {
            "type": "object",
            "properties": {
                "account_id": {
                    "type": "string",
                    "description": "Account identifier to get banking details for"
                }
            },
            "required": ["account_id"]
        }
    ),
    "search_by_swift_bic": (
        lambda args: search_by_swift_bic(args.get("swift_bic_code", "")),
        {
            "type": "object",
            "properties": {
                "swift_bic_code": {
                    "type": "string",
                    "description": "SWIFT or BIC code to search for"
                }
            },
            "required": ["swift_bic_code"]
        }
    ),
    "get_iban_info": (
        lambda args: get_iban_info(args.get("account_id", "")),
        {
            "type": "object",
            "properties": {
                "account_id": {
                    "type": "string",
                    "description": "Account identifier to check for IBAN (will explain why IBAN is not applicable for US accounts)"
                }
            },
            "required": ["account_id"]
        }
    )
}

def tools_list_result(cursor: Optional[str] = None):
    tools = []
    for name, (_, schema) in TOOL_REGISTRY.items():
        tool_info = {
            "name": name,
            "title": name.replace("_", " ").title(),
            "description": f"{name.replace('_', ' ').title()} - Customer account management tool",
            "inputSchema": schema
        }
        tools.append(tool_info)
    
    return {"tools": tools, "nextCursor": None}

def mcp_tool_success(out: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "content": [{"type": "text", "text": json.dumps(out, indent=2)}],
        "structuredContent": out,
        "isError": False
    }

def mcp_tool_error(msg: str, details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return {
        "content": [{"type": "text", "text": msg}],
        "structuredContent": {"error": msg, **(details or {})},
        "isError": True
    }

def tools_call_result(name: Optional[str], arguments: Dict[str, Any]):
    if name not in TOOL_REGISTRY:
        log.warning("tools/call unknown tool=%s args=%s", name, _short(arguments))
        return mcp_tool_error(f"Unknown tool: {name}")
    
    impl, _ = TOOL_REGISTRY[name]
    log.info("tools/call name=%s args=%s", name, _short(arguments))
    
    try:
        result = impl(arguments or {})
        log.info("tools/call result name=%s result=%s", name, _short(result))
        return mcp_tool_success(result)
    except Exception as e:
        log.exception("tools/call failed name=%s args=%s", name, _short(arguments))
        return mcp_tool_error("Tool execution failed", {"error": str(e)})

# -----------------------------------------------------------------------------
# JSON-RPC Method Handler
# -----------------------------------------------------------------------------
def handle_method(method: str, params: Dict[str, Any], id_) -> Optional[Dict[str, Any]]:
    try:
        if method == "initialize":
            log.info("rpc initialize id=%s params=%s", id_, _short(params))
            client_version = params.get("protocolVersion") or MCP_PROTOCOL_VERSION
            return jrpc_result(id_, {
                "protocolVersion": client_version,
                "capabilities": {"tools": {"listChanged": True}},
                "serverInfo": {
                    "name": "account-support-mcp-server", 
                    "version": "1.0.0",
                    "description": "Customer Account Support MCP Server"
                }
            })

        if method == "notifications/initialized":
            log.info("rpc notification: %s params=%s (no response)", method, _short(params))
            return None

        if method == "ping":
            log.info("rpc ping id=%s", id_)
            return jrpc_result(id_, {})

        if method == "tools/list":
            log.info("rpc tools/list id=%s", id_)
            result = tools_list_result(params.get("cursor"))
            log.info("rpc tools/list result=%s", _short(result))
            return jrpc_result(id_, result)

        if method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            log.info("rpc tools/call id=%s name=%s args=%s", id_, tool_name, _short(arguments))
            result = tools_call_result(tool_name, arguments)
            return jrpc_result(id_, result)

        log.warning("rpc method not found id=%s method=%s", id_, method)
        return jrpc_error(id_, -32601, "Method not found", {"method": method})

    except HTTPException as http:
        log.warning("rpc http-exception id=%s method=%s detail=%s", id_, method, http.detail)
        return jrpc_error(id_, -32602, http.detail)
    except Exception:
        log.exception("rpc internal-error id=%s method=%s", id_, method)
        return jrpc_error(id_, -32603, "Internal error")

# -----------------------------------------------------------------------------
# API Endpoints
# -----------------------------------------------------------------------------
@app.get("/healthz")
def health():
    return {
        "ok": True, 
        "sessions": len(SESSIONS),
        "tools": list(TOOL_REGISTRY.keys()),
        "customers": len(MOCK_CUSTOMERS)
    }

@app.post("/notify-tools-refresh/{session_id}")
async def notify_tools_refresh(session_id: str):
    q = SESSIONS.get(session_id)
    if not q:
        raise HTTPException(404, "Unknown session")
    note = {"jsonrpc": "2.0", "method": "tools/list_changed"}
    await q.put(("message", json.dumps(note)))
    log.info("sent tools/list_changed to session=%s", session_id)
    return {"ok": True}

# -----------------------------------------------------------------------------
# SSE Stream Endpoint
# -----------------------------------------------------------------------------
@app.get("/sse")
async def sse_stream(request: Request, origin: Optional[str] = Header(None)):
    check_origin(origin)
    session_id = str(uuid.uuid4())
    queue: asyncio.Queue = asyncio.Queue(maxsize=SESSION_QUEUE_MAX)
    SESSIONS[session_id] = queue
    base = external_base_url(request)
    inbox_abs = urljoin(base, f"inbox/{session_id}")
    await queue.put(("endpoint", inbox_abs))
    log.info("SSE connected session=%s endpoint=%s origin=%s", session_id, inbox_abs, origin)

    async def event_generator():
        try:
            while True:
                event, data = await queue.get()
                log.debug("SSE emit session=%s event=%s data=%s", session_id, event, _short(data, 300))
                yield {"event": event, "data": data}
        finally:
            SESSIONS.pop(session_id, None)
            log.info("SSE closed session=%s", session_id)

    return EventSourceResponse(event_generator(), ping=SSE_PING_SECONDS)

# -----------------------------------------------------------------------------
# Inbox Endpoint
# -----------------------------------------------------------------------------
@app.post("/inbox/{session_id}")
async def inbox(session_id: str, request: Request, origin: Optional[str] = Header(None)):
    check_origin(origin)
    if session_id not in SESSIONS:
        raise HTTPException(status_code=404, detail="Unknown session")

    try:
        body = await request.json()
    except Exception:
        log.warning("inbox parse-error session=%s", session_id)
        return JSONResponse(jrpc_error(None, -32700, "Parse error"), status_code=400)

    if not isinstance(body, dict):
        log.warning("inbox invalid-request (not dict) session=%s body=%s", session_id, _short(body))
        return JSONResponse(jrpc_error(None, -32600, "Invalid Request"), status_code=400)

    msg_id = body.get("id")
    method = body.get("method")
    params = body.get("params", {})
    is_notification = msg_id is None

    log.info("inbox recv session=%s id=%s method=%s params=%s", session_id, msg_id, method, _short(params))

    response = handle_method(method, params, msg_id)

    if is_notification or response is None:
        return Response(status_code=204)

    try:
        payload = json.dumps(response)
        await SESSIONS[session_id].put(("message", payload))
        log.info("inbox ack->sse session=%s id=%s method=%s result=%s", session_id, msg_id, method, _short(response, 600))
    except asyncio.QueueFull:
        log.warning("inbox queue-full session=%s dropping one message", session_id)
        try:
            _ = SESSIONS[session_id].get_nowait()
        except Exception:
            pass
        await SESSIONS[session_id].put(("message", json.dumps(response)))

    return Response(status_code=204)

# -----------------------------------------------------------------------------
# Main Entry Point
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8200)