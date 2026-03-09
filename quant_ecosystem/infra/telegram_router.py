from quant_ecosystem.infra.telegram_services import send_message
from quant_ecosystem.system_status import system_status


def handle_command(cmd):

    if cmd == "/status":
        send_message(system_status())

    elif cmd == "/regime":
        from quant_ecosystem.intelligence.regime_ai import current_regime
        send_message(f"Current Regime: {current_regime()}")

    elif cmd == "/research":
        send_message("Research loop active")

    elif cmd == "/pause":
        send_message("Trading paused")

    elif cmd == "/resume":
        send_message("Trading resumed")

    else:
        send_message("Unknown command")