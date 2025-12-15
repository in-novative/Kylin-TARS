#!/usr/bin/env python3
"""
协作全链路日志追溯模块

功能：
1. 记录决策日志（推理链生成）
2. 记录调度日志（MCP调用工具前）
3. 记录执行日志（工具执行后）
4. 记录广播日志（状态变更）
5. 支持按log_id/agent/status筛选

作者：GUI Agent Team
"""

import json
import os
import uuid
import time
from datetime import datetime
from typing import Dict, List, Optional
from enum import Enum


class LogType(Enum):
    """日志类型"""
    DECISION = "decision"  # 决策日志（推理链生成）
    SCHEDULE = "schedule"  # 调度日志（MCP调用工具前）
    EXECUTION = "execution"  # 执行日志（工具执行后）
    BROADCAST = "broadcast"  # 广播日志（状态变更）


# 日志存储目录
LOG_DIR = os.path.expanduser("~/.config/kylin-gui-agent/collaboration_logs")
os.makedirs(LOG_DIR, exist_ok=True)

# 日志文件（按日期）
def get_log_file_path() -> str:
    """获取今天的日志文件路径"""
    today = datetime.now().strftime("%Y%m%d")
    return os.path.join(LOG_DIR, f"collaboration_log_{today}.json")


def load_logs() -> List[Dict]:
    """加载日志文件"""
    log_file = get_log_file_path()
    if not os.path.exists(log_file):
        return []
    
    try:
        with open(log_file, "r", encoding="utf-8") as f:
            logs = json.load(f)
            return logs if isinstance(logs, list) else []
    except:
        return []


def save_logs(logs: List[Dict]):
    """保存日志文件"""
    log_file = get_log_file_path()
    with open(log_file, "w", encoding="utf-8") as f:
        json.dump(logs, f, ensure_ascii=False, indent=2)


def create_log_entry(
    log_type: LogType,
    task: str,
    step: int = 1,
    agent: Optional[str] = None,
    tool: Optional[str] = None,
    parameters: Optional[Dict] = None,
    status: str = "success",
    related_log_id: Optional[str] = None,
    metadata: Optional[Dict] = None
) -> Dict:
    """
    创建日志条目
    
    Args:
        log_type: 日志类型
        task: 用户任务
        step: 步骤编号
        agent: 智能体名称
        tool: 工具名称
        parameters: 工具参数
        status: 状态（success/error/pending）
        related_log_id: 关联的日志ID
        metadata: 额外元数据
    
    Returns:
        日志条目字典
    """
    log_id = str(uuid.uuid4())[:8]
    
    return {
        "log_id": log_id,
        "log_type": log_type.value,
        "task": task,
        "step": step,
        "agent": agent,
        "tool": tool,
        "parameters": parameters or {},
        "status": status,
        "timestamp": datetime.now().isoformat(),
        "timestamp_unix": int(time.time()),
        "related_log_id": related_log_id,
        "metadata": metadata or {}
    }


def log_decision(
    task: str,
    reasoning_chain: Dict,
    metadata: Optional[Dict] = None
) -> str:
    """
    记录决策日志（推理链生成）
    
    Returns:
        log_id
    """
    logs = load_logs()
    
    log_entry = create_log_entry(
        log_type=LogType.DECISION,
        task=task,
        step=0,
        metadata={
            "reasoning_chain": reasoning_chain,
            **(metadata or {})
        }
    )
    
    logs.append(log_entry)
    save_logs(logs)
    
    return log_entry["log_id"]


def log_schedule(
    task: str,
    step: int,
    agent: str,
    tool: str,
    parameters: Dict,
    related_log_id: Optional[str] = None
) -> str:
    """
    记录调度日志（MCP调用工具前）
    
    Returns:
        log_id
    """
    logs = load_logs()
    
    log_entry = create_log_entry(
        log_type=LogType.SCHEDULE,
        task=task,
        step=step,
        agent=agent,
        tool=tool,
        parameters=parameters,
        status="pending",
        related_log_id=related_log_id
    )
    
    logs.append(log_entry)
    save_logs(logs)
    
    return log_entry["log_id"]


def log_execution(
    task: str,
    step: int,
    agent: str,
    tool: str,
    status: str,
    result: Optional[Dict] = None,
    related_log_id: Optional[str] = None,
    error: Optional[str] = None
) -> str:
    """
    记录执行日志（工具执行后）
    
    Returns:
        log_id
    """
    logs = load_logs()
    
    log_entry = create_log_entry(
        log_type=LogType.EXECUTION,
        task=task,
        step=step,
        agent=agent,
        tool=tool,
        status=status,
        related_log_id=related_log_id,
        metadata={
            "result": result,
            "error": error
        }
    )
    
    logs.append(log_entry)
    save_logs(logs)
    
    return log_entry["log_id"]


def log_broadcast(
    agent_name: str,
    instance_id: str,
    old_status: str,
    new_status: str,
    metadata: Optional[Dict] = None
) -> str:
    """
    记录广播日志（状态变更）
    
    Returns:
        log_id
    """
    logs = load_logs()
    
    log_entry = create_log_entry(
        log_type=LogType.BROADCAST,
        task=f"状态变更: {agent_name}",
        step=0,
        agent=agent_name,
        status="success",
        metadata={
            "instance_id": instance_id,
            "old_status": old_status,
            "new_status": new_status,
            **(metadata or {})
        }
    )
    
    logs.append(log_entry)
    save_logs(logs)
    
    return log_entry["log_id"]


def query_logs(
    log_id: Optional[str] = None,
    agent: Optional[str] = None,
    status: Optional[str] = None,
    log_type: Optional[str] = None,
    task: Optional[str] = None,
    limit: int = 100
) -> List[Dict]:
    """
    查询日志
    
    Args:
        log_id: 日志ID
        agent: 智能体名称
        status: 状态
        log_type: 日志类型
        task: 任务关键词
        limit: 返回条数
    
    Returns:
        匹配的日志列表
    """
    logs = load_logs()
    
    filtered_logs = []
    for log in logs:
        if log_id and log.get("log_id") != log_id:
            continue
        if agent and log.get("agent") != agent:
            continue
        if status and log.get("status") != status:
            continue
        if log_type and log.get("log_type") != log_type:
            continue
        if task and task.lower() not in log.get("task", "").lower():
            continue
        
        filtered_logs.append(log)
    
    # 按时间倒序
    filtered_logs.sort(key=lambda x: x.get("timestamp_unix", 0), reverse=True)
    
    return filtered_logs[:limit]


def get_log_chain(log_id: str) -> List[Dict]:
    """
    获取日志链（通过related_log_id关联）
    
    Args:
        log_id: 起始日志ID
    
    Returns:
        日志链列表（按时间顺序）
    """
    logs = load_logs()
    
    # 构建日志字典（log_id -> log）
    log_dict = {log["log_id"]: log for log in logs}
    
    # 查找起始日志
    if log_id not in log_dict:
        return []
    
    chain = []
    current_log_id = log_id
    
    # 向前查找（related_log_id指向的日志）
    visited = set()
    while current_log_id and current_log_id not in visited:
        visited.add(current_log_id)
        if current_log_id in log_dict:
            chain.insert(0, log_dict[current_log_id])
            current_log_id = log_dict[current_log_id].get("related_log_id")
        else:
            break
    
    # 向后查找（related_log_id指向当前日志的日志）
    current_log_id = log_id
    visited = set()
    while current_log_id:
        visited.add(current_log_id)
        # 查找所有related_log_id指向当前日志的日志
        next_logs = [log for log in logs 
                     if log.get("related_log_id") == current_log_id 
                     and log["log_id"] not in visited]
        
        if next_logs:
            # 按时间排序
            next_logs.sort(key=lambda x: x.get("timestamp_unix", 0))
            for next_log in next_logs:
                chain.append(next_log)
                current_log_id = next_log["log_id"]
        else:
            break
    
    return chain


def get_log_statistics() -> Dict:
    """获取日志统计信息"""
    logs = load_logs()
    
    stats = {
        "total_logs": len(logs),
        "by_type": {},
        "by_status": {},
        "by_agent": {},
        "recent_logs": []
    }
    
    for log in logs:
        # 按类型统计
        log_type = log.get("log_type", "unknown")
        stats["by_type"][log_type] = stats["by_type"].get(log_type, 0) + 1
        
        # 按状态统计
        status = log.get("status", "unknown")
        stats["by_status"][status] = stats["by_status"].get(status, 0) + 1
        
        # 按智能体统计
        agent = log.get("agent", "unknown")
        stats["by_agent"][agent] = stats["by_agent"].get(agent, 0) + 1
    
    # 最近日志
    stats["recent_logs"] = sorted(logs, key=lambda x: x.get("timestamp_unix", 0), reverse=True)[:10]
    
    return stats


# ============================================================
# 测试
# ============================================================

if __name__ == "__main__":
    print("=== 测试协作日志模块 ===\n")
    
    # 测试决策日志
    decision_id = log_decision(
        task="搜索下载目录的png文件并设置为壁纸",
        reasoning_chain={"thought_chain": {"task_decomposition": "1. 搜索文件；2. 设置壁纸"}}
    )
    print(f"✓ 决策日志: {decision_id}")
    
    # 测试调度日志
    schedule_id = log_schedule(
        task="搜索下载目录的png文件并设置为壁纸",
        step=1,
        agent="FileAgent",
        tool="file_agent.search_file",
        parameters={"path": "~/Downloads", "keyword": ".png"},
        related_log_id=decision_id
    )
    print(f"✓ 调度日志: {schedule_id}")
    
    # 测试执行日志
    execution_id = log_execution(
        task="搜索下载目录的png文件并设置为壁纸",
        step=1,
        agent="FileAgent",
        tool="file_agent.search_file",
        status="success",
        result={"files_found": 2},
        related_log_id=schedule_id
    )
    print(f"✓ 执行日志: {execution_id}")
    
    # 测试广播日志
    broadcast_id = log_broadcast(
        agent_name="FileAgent",
        instance_id="file_agent_123",
        old_status="online",
        new_status="busy"
    )
    print(f"✓ 广播日志: {broadcast_id}")
    
    # 测试日志链查询
    print("\n--- 日志链查询 ---")
    chain = get_log_chain(decision_id)
    print(f"日志链长度: {len(chain)}")
    for log in chain:
        print(f"  [{log['log_type']}] {log.get('agent', 'N/A')} - {log.get('tool', 'N/A')} ({log['status']})")
    
    # 测试统计
    print("\n--- 日志统计 ---")
    stats = get_log_statistics()
    print(f"总日志数: {stats['total_logs']}")
    print(f"按类型: {stats['by_type']}")
    print(f"按状态: {stats['by_status']}")
    print(f"按智能体: {stats['by_agent']}")
    
    print("\n=== 测试完成 ===")

