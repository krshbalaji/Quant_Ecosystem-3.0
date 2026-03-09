from quant_ecosystem.core.system_state import SystemState


def system_status():
    try:
        state = SystemState.get_state()

        return f"""
SYSTEM STATUS

Mode: {state.get('mode', 'unknown')}
Strategies Active: {state.get('active_strategies', 0)}
Capital Allocated: {state.get('capital_allocated', 0)}
Research Loop: {state.get('research_running', False)}
"""
    except Exception as e:
        return f"System status unavailable: {e}"