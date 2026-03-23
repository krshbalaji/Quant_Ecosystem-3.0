class MultiSymbolIntelligence:

    def __init__(self):

        self.symbol_clusters = {

            "trend": ["NIFTY", "BANKNIFTY"],
            "mean": ["RELIANCE", "INFY"],
            "volatile": ["CRYPTO", "MIDCAP"]
        }

    def suggest_symbols(self, regime):

        return self.symbol_clusters.get(regime, ["NIFTY"])