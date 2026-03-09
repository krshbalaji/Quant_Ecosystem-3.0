from quant_ecosystem.infra.telegram_services import send_message


def send_menu():

    text = """
📊 <b>Quant Ecosystem Control Center</b>

1️⃣ /status
2️⃣ /research
3️⃣ /strategies
4️⃣ /capital
5️⃣ /regime
6️⃣ /pause
7️⃣ /resume
"""

    send_message(text)