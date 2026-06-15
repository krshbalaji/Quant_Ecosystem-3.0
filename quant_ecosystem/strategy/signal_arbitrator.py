from collections import defaultdict


class SignalArbitrator:

    def _group_by_symbol(
        self,
        signals,
    ):
        grouped = defaultdict(list)

        for signal in signals:
            symbol = signal.get("symbol")

            if symbol:
                grouped[symbol].append(signal)

        return grouped

    def priority_resolution(
        self,
        signals,
    ):
        if not signals:
            return []

        grouped = self._group_by_symbol(signals)

        resolved = []

        for _, items in grouped.items():
            winner = sorted(
                items,
                key=lambda x: x.get(
                    "priority",
                    9999,
                )
            )[0]

            resolved.append(winner)

        return resolved

    def confidence_weighted(
        self,
        signals,
    ):
        if not signals:
            return []

        grouped = self._group_by_symbol(signals)
        resolved = []

        for _, items in grouped.items():
            buy_score = 0.0
            sell_score = 0.0
            best = None
            best_conf = -1

            for signal in items:
                conf = float(
                    signal.get(
                        "confidence",
                        0.0,
                    )
                )

                side = str(
                    signal.get("side", "")
                ).upper()

                if conf > best_conf:
                    best_conf = conf
                    best = signal

                if side == "BUY":
                    buy_score += conf

                elif side == "SELL":
                    sell_score += conf

            if best is None:
                continue

            best_dict = dict(best)

            if buy_score == sell_score:
                resolved.append(best_dict)

            elif buy_score > sell_score:
                resolved.append(
                    {
                        **best_dict,
                        "side": "BUY",
                    }
                )

            else:
                resolved.append(
                    {
                        **best_dict,
                        "side": "SELL",
                    }
                )

        return resolved

    def consensus(
        self,
        signals,
    ):
        if not signals:
            return []

        grouped = self._group_by_symbol(signals)
        resolved = []

        for _, items in grouped.items():
            sides = [
                str(
                    x.get("side", "")
                ).upper()
                for x in items
            ]

            if len(set(sides)) == 1:
                resolved.append(items[0])

        return resolved

    def veto(
        self,
        signals,
    ):
        if not signals:
            return []

        grouped = self._group_by_symbol(signals)
        resolved = []

        for _, items in grouped.items():
            vetoed = any(
                bool(x.get("veto", False))
                for x in items
            )

            if vetoed:
                continue

            resolved.extend(items[:1])

        return resolved

    def hedge_aware(
        self,
        signals,
    ):
        if not signals:
            return []

        directional = []
        hedges = []

        for signal in signals:
            trade_type = str(
                signal.get(
                    "trade_type",
                    ""
                )
            ).upper()

            if "HEDGE" in trade_type:
                hedges.append(signal)
            else:
                directional.append(signal)

        resolved = self.priority_resolution(
            directional
        )

        resolved.extend(hedges)

        return resolved


signal_arbitrator = SignalArbitrator()