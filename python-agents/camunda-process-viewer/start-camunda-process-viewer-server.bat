@echo off
echo Starting Camunda Process Viewer Server
echo.
echo This will start a server on port 3001 that forwards requests to Camunda on port 8088
echo and serves the process viewer HTML file.
echo.
echo Make sure Camunda is running on port 8088!
echo.
echo ...
python camunda-process-viewer-server.py
