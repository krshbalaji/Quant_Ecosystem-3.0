import json

class AlphaStore:

    def __init__(self, path="data/alphas.json"):
        self.path = path

    def save(self, alpha):
        with open(self.path,"a") as f:
            f.write(json.dumps(alpha)+"\n")