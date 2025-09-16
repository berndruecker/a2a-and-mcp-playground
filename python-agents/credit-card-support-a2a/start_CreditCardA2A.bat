@echo off
echo Starting Credit Card Loss A2A...

uvicorn credit_card_loss_agent:app --reload --host 0.0.0.0 --port 8000