# Precision Trader (QE3 LT)

## Setup
- Python 3.10+
- `pip install -r requirements.txt`

## Env
Create `.env`:
TELEGRAM_TOKEN=...
TELEGRAM_CHAT_ID=...

## Run
python strategy_loop.py

## Notes
- Paper broker by default
- Smart auto fallback optional
- Capital & risk configured in `capital_allocator.py`