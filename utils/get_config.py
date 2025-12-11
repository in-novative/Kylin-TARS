import json
import os
from typing import List

def get_master_config():
    BASE_DIR = os.path.dirname(os.path.dirname(__file__))
    CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = json.load(f)
    MASTERAGENT = next((i.get("content", []) for i in config if i.get("item") == "MasterAgent"), None)
    assert (MASTERAGENT is not None), "can't find MasterAgent, please check config.json"
    return MASTERAGENT

def get_childen_config() -> List:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = json.load(f)
    CHILDENAGENTS = next((i.get("content", []) for i in config if i.get("item") == "ChildAgent"), None)
    assert (CHILDENAGENTS is not None), "can't find ChildenAgents, please check config.json"
    return CHILDENAGENTS

def get_child_config(agent_name):
    CHILDENAGENTS = get_childen_config()
    TARGETAGENT = next((agent for agent in CHILDENAGENTS if agent.get("name") == agent_name), None)
    assert (TARGETAGENT is not None), f"can't find {agent_name} in ChildenAgents, please check config.json"