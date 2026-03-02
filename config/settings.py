from config.env_loader import Env

class Settings:

    CAPITAL = Env.CAPITAL

    MAX_RISK_PER_TRADE = 0.01

    MAX_DRAWDOWN = 0.15

    MAX_TRADES_PER_DAY = 50

    PAPER_MODE = not Env.LIVE_TRADING