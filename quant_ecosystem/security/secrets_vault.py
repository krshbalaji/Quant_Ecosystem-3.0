class SecretsVault:

    def __init__(self):
        self._secrets = {}

    def store(
        self,
        key,
        value,
    ):
        self._secrets[key] = value

    def fetch(
        self,
        key,
    ):
        return self._secrets.get(key)

    def clear(self):
        self._secrets.clear()


secrets_vault = SecretsVault()