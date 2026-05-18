import json
import os

config_file = "soul.json"

def load_agent_config():
    #load agent id config if it exists
    if os.path.exists(config_file):
        with open(config_file, "r", encoding = "utf-8") as f:
            return json.load(f)
    return None
def save_agent_config(id_data):
    #save agent id to disk
    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(id_data, f, indent = 4)