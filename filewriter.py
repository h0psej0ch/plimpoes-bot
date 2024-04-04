import json

with open("data.json", 'w') as f:
    data = {"data": {}}
    json.dump(data, f)