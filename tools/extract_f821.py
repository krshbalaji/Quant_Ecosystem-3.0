import json

with open("ruff_execution.json", encoding="utf-8") as f:
    data = json.load(f)

for item in data:
    if item.get("code") == "F821":
        filename = item["filename"]
        line = item["location"]["row"]
        message = item["message"]

        print(f"{filename} | line {line} | {message}")