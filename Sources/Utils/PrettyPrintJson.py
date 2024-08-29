import json

def pretty_print_json(data):
    print(json.dumps(data, indent=4, ensure_ascii=False))
