@echo off
echo Starting Account Management MCP Server...

SET EXTERNAL_BASE_URL=http://host.docker.internal:8200/
python account_management_mcp.py