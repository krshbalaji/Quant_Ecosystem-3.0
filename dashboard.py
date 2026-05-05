def dashboard():

    text = """
🧠 SDE QUANT SYSTEM

Status: LIVE
Mode: READY
"""

    buttons = {
        "inline_keyboard": [
            [{"text": "📊 TRADE PANEL", "callback_data": "panel"}],
            [{"text": "⚡ STRIKE NOW", "callback_data": "strike"}],
            [{"text": "🧠 AI MODE", "callback_data": "ai"}],
            [{"text": "⚙ SETTINGS", "callback_data": "settings"}]
        ]
    }

    return text, buttons