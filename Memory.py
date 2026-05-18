import json
import os

Mem_file = "agent_memory.json"

def load_memory():
    if os.path.exists(Mem_file):
        try:
            with open(Mem_file, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading memory file, starting fresh: {e}")
    return {}
def save_memory(data):
    try:
        with open(Mem_file, "w") as f:
            json.dump(data, f, indent =4)
    except Exception as e:
        print(f"Error saving memory to disk: {e}")