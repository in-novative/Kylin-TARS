#!/usr/bin/env python3
# mcp_client.py
import os
import dbus
import json
import time
import logging
from mcp_client.agent_registry import InitDb, ListAgents, UpsertAgent

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - MCP Client - %(levelname)s - %(message)s")
logger = logging.getLogger("MCP Client")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")

with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    config = json.load(f)

for i in config:
    if i.get("item")=="ChildAgent":
        CANDIDATE_AGENTS = i.get("content", [])
        break
if CANDIDATE_AGENTS is None:
    logger.warning("can't find any ChildAgent, please check config.json")

def PingAgent(service: str, path: str, iface: str) -> bool:
    """Check if Agent is accessible"""
    try:
        bus = dbus.SessionBus()
        proxy = bus.get_object(service, path)
        interface = dbus.Interface(proxy, iface)
        ret = interface.Ping()
        return json.loads(ret).get("status") == "ok"
    except Exception as e:
        logger.debug("Ping %s failed: %s", service, e)
        return False

def DiscoverAgents(candidates: list[dict]) -> dict:
    """Universal Agent discover method,scan accroding to CANDIDATE_AGENTS list"""
    discovered = 0
    details = []
    for ag in candidates:
        name = ag["name"]
        if PingAgent(ag["service"], ag["path"], ag["interface"]):
            # pull Agent
            bus = dbus.SessionBus()
            proxy = bus.get_object(ag["service"], ag["path"])
            iface = dbus.Interface(proxy, ag["interface"])
            tools = json.loads(iface.ToolsList())["tools"]
            caps = [t["name"] for t in tools]

            UpsertAgent(name=name,
                         service=ag["service"],
                         path=ag["path"],
                         interface=ag["interface"],
                         caps=caps)
            discovered += 1
            details.append({"name": name, "status": "registered", "caps": caps})
            logger.info("%s discovered & registered (%d caps).", name, len(caps))
        else:
            details.append({"name": name, "status": "offline"})
            logger.warning("%s not responding.", name)
    return {"discovered": discovered, "details": details}

def PrintRegistry():
    for ag in ListAgents():
        logger.info("Agent: %s | service: %s | caps: %s",
                 ag["name"], ag["service"], json.loads(ag["capabilities"]))


def main():
    InitDb()
    logger.info("MCP Client start scanning...")
    DiscoverAgents(CANDIDATE_AGENTS)
    PrintRegistry()

if __name__ == "__main__":
    main()