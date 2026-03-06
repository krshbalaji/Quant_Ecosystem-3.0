"""
PATCH: quant_ecosystem/controller/autonomous_controller.py
FIX:   Constructor now accepts config=None, **kwargs.
"""


class AutonomousController:
    """
    Top-level autonomous decision controller.
    Receives signals from engines and issues execution instructions.
    """

    def __init__(self, config=None, **kwargs):
        self.config = config
        self._mode = (config or {}).get("mode", "PAPER")

    def dispatch(self, signal):
        """Route signal to execution layer (stub)."""
        print(f"[AutonomousController] Dispatching signal in {self._mode} mode.")

    def status(self) -> dict:
        return {"mode": self._mode, "active": True}
