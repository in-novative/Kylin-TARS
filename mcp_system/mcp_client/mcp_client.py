#!/usr/bin/env python3
# mcp_client.py
import dbus
import json
import time
import logging
from agent_registry import InitDb, UpsertAgent, ListAgents

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - MCP Client - %(levelname)s - %(message)s")
log = logging.getLogger("MCP Client")

CANDIDATE_AGENTS = [
    {
        "name"      : "FileAgent",
        "service"   : "com.kylin.ai.mcp.FileAgent",
        "path"      : "/com/kylin/ai/mcp/FileAgent",
        "interface" : "com.kylin.ai.mcp.FileAgent",
    },
]

def PingAgent(service: str, path: str, iface: str) -> bool:
    """Check if Agent is accessible"""
    try:
        bus = dbus.SessionBus()
        proxy = bus.get_object(service, path)
        interface = dbus.Interface(proxy, iface)
        ret = interface.Ping()
        return json.loads(ret).get("status") == "ok"
    except Exception as e:
        log.debug("Ping %s failed: %s", service, e)
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

            upsert_agent(name=name,
                         service=ag["service"],
                         path=ag["path"],
                         interface=ag["interface"],
                         caps=caps)
            discovered += 1
            details.append({"name": name, "status": "registered", "caps": caps})
            log.info("%s discovered & registered (%d caps).", name, len(caps))
        else:
            details.append({"name": name, "status": "offline"})
            log.warning("%s not responding.", name)
    return {"discovered": discovered, "details": details}

def PrintRegistry():
    for ag in ListAgents():
        log.info("Agent: %s | service: %s | caps: %s",
                 ag["name"], ag["service"], json.loads(ag["capabilities"]))

def main():
    InitDb()
    log.info("MCP Client start scanning...")
    DiscoverFileAgent()
    PrintRegistry()

if __name__ == "__main__":
    main()