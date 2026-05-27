class FragmentationEngine:

    def fragment(
        self,
        qty,
        brokers,
    ):
        brokers = list(brokers)

        if not brokers:
            return [qty]

        if qty < 5000:
            return [qty]

        parts = len(brokers)
        base = qty // parts
        rem = qty % parts

        chunks = []

        for i in range(parts):
            chunk = base

            if i == 0:
                chunk += rem

            chunks.append(chunk)

        return chunks