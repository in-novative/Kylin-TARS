#!/usr/bin/env python3
# agent_registry.py
import sqlite3
import json
import time
from typing import Dict, Optional

DB_FILE = "agent_registry.db"

def _get_conn():
    """获取SQLite数据库连接"""
    return sqlite3.connect(DB_FILE, check_same_thread=False)

def InitDb():
    """初始化智能体注册表（仅首次执行有效）"""
    sql = """
    CREATE TABLE IF NOT EXISTS agents(
        name        TEXT PRIMARY KEY,
        service     TEXT NOT NULL,
        path        TEXT NOT NULL,
        interface   TEXT NOT NULL,
        capabilities TEXT NOT NULL,  -- JSON 列表
        last_seen   REAL NOT NULL
    );
    """
    with _get_conn() as conn:
        conn.execute(sql)
        print("Database initialize successfully")

def UpsertAgent(name: str, service: str, path: str,
                 interface: str, caps: list, last: Optional[float]=None):
    """新增/更新智能体注册信息(UPSERT)"""
    with _get_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO agents VALUES(?,?,?,?,?,?)",
            (name, service, path, interface, json.dumps(caps), last or time.time())
        )

def RemoveAgent(name: str):
    """删除指定名称的智能体注册信息"""
    with _get_conn() as conn:
        conn.execute("DELETE FROM agents WHERE name=?", (name,))

def ListAgents():
    """查询所有已注册的智能体信息"""
    with _get_conn() as conn:
        rows = conn.execute("SELECT * FROM agents").fetchall()
    return [dict(zip(
        ["name","service","path","interface","capabilities","last_seen"], row))
        for row in rows]

def AgentByName(name: str):
    """根据名称查询单个智能体的注册信息"""
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM agents WHERE name=?", (name,)).fetchone()
    return dict(zip(
        ["name","service","path","interface","capabilities","last_seen"], row)) if row else None