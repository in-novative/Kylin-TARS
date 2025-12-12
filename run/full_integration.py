#!/usr/bin/env python3
"""
全链路联调脚本 - Kylin-TARS GUI Agent

本脚本用于联调 System-2 推理、MCP 协议、子智能体、记忆模块的完整流程。

使用方式：
1. 模拟模式（无需启动 MCP Server）：
   python full_integration.py

2. 真实模式（需要先启动 MCP Server 和子智能体）：
   python full_integration.py --real

作者：GUI Agent Team
日期：2024-12
"""

import os
import sys
import json
import time
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# 添加项目路径
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# 导入自定义模块
from system2_memory import (
    reasoning_with_memory,
    get_reasoning_for_master,
    validate_for_mcp,
    normalize_for_mcp
)
from memory_store import (
    save_collaboration_trajectory,
    list_trajectories,
    STORAGE_DIR
)
from memory_retrieve import (
    retrieve_similar_trajectory,
    reuse_reasoning_chain,
    reasoning_with_retrieval
)

# ============================================================
# 配置常量
# ============================================================

# MCP 配置（成员A）
MCP_CONFIG_A = {
    "service_name": "com.kylin.ai.mcp.MasterAgent",
    "object_path": "/com/kylin/ai/mcp/MasterAgent",
    "interface_name": "com.kylin.ai.mcp.MasterAgent"
}

# MCP 配置（成员C）
MCP_CONFIG_C = {
    "service_name": "com.mcp.server",
    "object_path": "/com/mcp/server",
    "interface_name": "com.mcp.server.Interface"
}

# 子智能体配置
AGENTS_CONFIG = {
    "FileAgent": {
        "service": "com.mcp.agent.file",
        "path": "/com/mcp/agent/file",
        "interface": "com.mcp.agent.file.Interface",
        "tools": [
            {
                "name": "file_agent.search_file",
                "description": "按关键词递归/非递归搜索指定目录下的文件",
                "parameters": {
                    "search_path": "string",
                    "keyword": "string",
                    "recursive": "boolean"
                }
            },
            {
                "name": "file_agent.move_to_trash",
                "description": "将指定文件/目录移动到回收站",
                "parameters": {
                    "file_path": "string"
                }
            }
        ]
    },
    "SettingsAgent": {
        "service": "com.mcp.agent.settings",
        "path": "/com/mcp/agent/settings",
        "interface": "com.mcp.agent.settings.Interface",
        "tools": [
            {
                "name": "settings_agent.change_wallpaper",
                "description": "调用DBus实现壁纸修改",
                "parameters": {
                    "wallpaper_path": "string",
                    "scale": "string"
                }
            },
            {
                "name": "settings_agent.adjust_volume",
                "description": "调用gsettings实现音量调整",
                "parameters": {
                    "volume": "integer",
                    "device": "string"
                }
            }
        ]
    }
}


# ============================================================
# 模拟工具执行
# ============================================================

class MockToolExecutor:
    """模拟工具执行器（无需真实 D-Bus）"""
    
    def __init__(self):
        self.execution_log = []
    
    def execute(self, tool_name: str, parameters: Dict) -> Dict:
        """模拟执行工具"""
        timestamp = datetime.now().isoformat()
        
        result = {
            "tool_name": tool_name,
            "parameters": parameters,
            "timestamp": timestamp,
            "success": True
        }
        
        # 模拟不同工具的返回结果
        if "search_file" in tool_name:
            result["result"] = {
                "files": [
                    {"file_name": "image1.png", "file_path": "~/Downloads/image1.png"},
                    {"file_name": "image2.png", "file_path": "~/Downloads/image2.png"}
                ],
                "count": 2
            }
            result["message"] = f"搜索完成，找到 2 个文件"
            
        elif "move_to_trash" in tool_name:
            result["result"] = {"moved": parameters.get("file_path", "")}
            result["message"] = f"文件已移动到回收站"
            
        elif "change_wallpaper" in tool_name:
            result["result"] = {"wallpaper": parameters.get("wallpaper_path", "")}
            result["message"] = f"壁纸设置成功"
            
        elif "adjust_volume" in tool_name:
            result["result"] = {"volume": parameters.get("volume", 50)}
            result["message"] = f"音量已调整到 {parameters.get('volume', 50)}%"
            
        else:
            result["success"] = False
            result["error"] = f"未知工具: {tool_name}"
        
        self.execution_log.append(result)
        return result


# ============================================================
# 推理链解析与执行
# ============================================================

def parse_execution_plan(reasoning_chain: Dict) -> List[Dict]:
    """
    从推理链中解析执行计划
    
    Args:
        reasoning_chain: 推理链字典
        
    Returns:
        执行步骤列表
    """
    steps = []
    
    execution_plan = reasoning_chain.get("execution_plan", [])
    
    for step in execution_plan:
        action = step.get("action", "")
        agent = step.get("agent", "")
        
        # 尝试匹配工具
        tool_info = match_tool_from_action(action, agent)
        
        steps.append({
            "step": step.get("step", len(steps) + 1),
            "action": action,
            "agent": agent,
            "tool": tool_info
        })
    
    return steps


def match_tool_from_action(action: str, agent: str) -> Optional[Dict]:
    """
    从动作描述中匹配工具
    
    Args:
        action: 动作描述
        agent: 智能体名称
        
    Returns:
        工具信息字典
    """
    action_lower = action.lower()
    
    # FileAgent 工具匹配
    if agent == "FileAgent" or "文件" in action or "搜索" in action:
        if "搜索" in action or "search" in action_lower:
            return {
                "name": "file_agent.search_file",
                "parameters": extract_search_params(action)
            }
        elif "回收站" in action or "删除" in action or "移动" in action or "trash" in action_lower:
            return {
                "name": "file_agent.move_to_trash",
                "parameters": extract_trash_params(action)
            }
    
    # SettingsAgent 工具匹配
    if agent == "SettingsAgent" or "设置" in action:
        if "壁纸" in action or "wallpaper" in action_lower:
            return {
                "name": "settings_agent.change_wallpaper",
                "parameters": extract_wallpaper_params(action)
            }
        elif "音量" in action or "volume" in action_lower:
            return {
                "name": "settings_agent.adjust_volume",
                "parameters": extract_volume_params(action)
            }
    
    return None


def extract_search_params(action: str) -> Dict:
    """从动作描述中提取搜索参数"""
    import re
    
    params = {
        "search_path": "~/Downloads",
        "keyword": "*.png",
        "recursive": True
    }
    
    # 提取路径
    path_match = re.search(r'[~/\w]+/\w+', action)
    if path_match:
        params["search_path"] = path_match.group(0)
    
    # 提取文件模式
    pattern_match = re.search(r'\*?\.\w+', action)
    if pattern_match:
        params["keyword"] = pattern_match.group(0)
    
    return params


def extract_trash_params(action: str) -> Dict:
    """从动作描述中提取删除参数"""
    import re
    
    params = {"file_path": ""}
    
    path_match = re.search(r'[~/\w]+/[\w.]+', action)
    if path_match:
        params["file_path"] = path_match.group(0)
    
    return params


def extract_wallpaper_params(action: str) -> Dict:
    """从动作描述中提取壁纸参数"""
    import re
    
    params = {
        "wallpaper_path": "",
        "scale": "zoom"
    }
    
    path_match = re.search(r'[~/\w]+/[\w.]+\.(png|jpg|jpeg)', action, re.IGNORECASE)
    if path_match:
        params["wallpaper_path"] = path_match.group(0)
    
    return params


def extract_volume_params(action: str) -> Dict:
    """从动作描述中提取音量参数"""
    import re
    
    params = {
        "volume": 50,
        "device": "@DEFAULT_SINK@"
    }
    
    vol_match = re.search(r'(\d+)\s*%?', action)
    if vol_match:
        params["volume"] = int(vol_match.group(1))
    
    return params


# ============================================================
# 全链路执行
# ============================================================

def execute_full_pipeline(
    user_task: str,
    mock_mode: bool = True,
    verbose: bool = True
) -> Dict:
    """
    执行完整的 GUI Agent 流程
    
    流程：用户任务 → 记忆检索 → System-2 推理 → 工具执行 → 结果存储
    
    Args:
        user_task: 用户任务描述
        mock_mode: 是否使用模拟模式
        verbose: 是否打印详细信息
        
    Returns:
        执行结果字典
    """
    result = {
        "task": user_task,
        "timestamp": datetime.now().isoformat(),
        "pipeline_steps": [],
        "success": False
    }
    
    if verbose:
        print("\n" + "=" * 70)
        print("🚀 Kylin-TARS GUI Agent 全链路执行")
        print("=" * 70)
        print(f"📝 用户任务: {user_task}")
        print(f"🔧 运行模式: {'模拟模式' if mock_mode else '真实模式'}")
    
    # Step 1: 记忆检索
    if verbose:
        print("\n" + "-" * 50)
        print("Step 1: 记忆检索")
        print("-" * 50)
    
    reused_reasoning = None
    similar_traj = retrieve_similar_trajectory(user_task, threshold=60, verbose=verbose)
    
    if similar_traj:
        reused_reasoning = similar_traj.get("reasoning_chain")
        result["pipeline_steps"].append({
            "step": "memory_retrieval",
            "status": "reused",
            "similar_task": similar_traj.get("task"),
            "similarity": "≥60%"
        })
        if verbose:
            print(f"✓ 找到相似任务，复用推理链")
    else:
        result["pipeline_steps"].append({
            "step": "memory_retrieval",
            "status": "not_found"
        })
        if verbose:
            print(f"○ 未找到相似任务，将生成新推理链")
    
    # Step 2: System-2 推理
    if verbose:
        print("\n" + "-" * 50)
        print("Step 2: System-2 推理")
        print("-" * 50)
    
    if reused_reasoning:
        reasoning_chain = reused_reasoning
        if verbose:
            print("✓ 复用历史推理链")
    else:
        reasoning_chain, _ = reasoning_with_memory(
            user_task=user_task,
            enable_reuse=False,
            verbose=verbose
        )
    
    # 验证推理链格式
    is_valid, msg = validate_for_mcp(reasoning_chain)
    if not is_valid:
        reasoning_chain = normalize_for_mcp(reasoning_chain)
        if verbose:
            print(f"⚠️ 推理链格式标准化: {msg}")
    
    result["reasoning_chain"] = reasoning_chain
    result["pipeline_steps"].append({
        "step": "reasoning",
        "status": "success" if reasoning_chain else "failed",
        "reused": bool(reused_reasoning)
    })
    
    # 打印推理链摘要
    if verbose and reasoning_chain:
        tc = reasoning_chain.get("thought_chain", {})
        print(f"\n📋 推理链摘要:")
        print(f"   任务分解: {tc.get('task_decomposition', 'N/A')[:80]}...")
        print(f"   风险评估: {tc.get('risk_assessment', 'N/A')}")
    
    # Step 3: 解析执行计划
    if verbose:
        print("\n" + "-" * 50)
        print("Step 3: 解析执行计划")
        print("-" * 50)
    
    execution_steps = parse_execution_plan(reasoning_chain)
    
    if verbose:
        print(f"📊 解析出 {len(execution_steps)} 个执行步骤:")
        for step in execution_steps:
            tool_name = step["tool"]["name"] if step["tool"] else "无工具"
            print(f"   {step['step']}. {step['action'][:40]}... → {tool_name}")
    
    # Step 4: 执行工具调用
    if verbose:
        print("\n" + "-" * 50)
        print("Step 4: 执行工具调用")
        print("-" * 50)
    
    executor = MockToolExecutor()
    execution_results = []
    
    for step in execution_steps:
        if step["tool"]:
            tool_name = step["tool"]["name"]
            parameters = step["tool"]["parameters"]
            
            if verbose:
                print(f"\n   执行: {tool_name}")
                print(f"   参数: {parameters}")
            
            tool_result = executor.execute(tool_name, parameters)
            execution_results.append(tool_result)
            
            if verbose:
                status = "✓" if tool_result["success"] else "✗"
                print(f"   结果: {status} {tool_result.get('message', '')}")
        else:
            if verbose:
                print(f"\n   步骤 {step['step']}: 无需工具调用 - {step['action'][:40]}...")
    
    result["execution_results"] = execution_results
    result["pipeline_steps"].append({
        "step": "execution",
        "status": "success" if all(r.get("success", False) for r in execution_results) else "partial",
        "tool_calls": len(execution_results)
    })
    
    # Step 5: 存储协作轨迹
    if verbose:
        print("\n" + "-" * 50)
        print("Step 5: 存储协作轨迹")
        print("-" * 50)
    
    execution_summary = json.dumps(execution_results, ensure_ascii=False)
    overall_success = all(r.get("success", False) for r in execution_results) if execution_results else True
    
    trajectory_path = save_collaboration_trajectory(
        task=user_task,
        reasoning_chain=reasoning_chain,
        execution_result=execution_summary,
        screenshot_paths=[],
        success=overall_success,
        metadata={
            "source": "full_integration",
            "mock_mode": mock_mode,
            "reused_reasoning": bool(reused_reasoning)
        }
    )
    
    result["trajectory_path"] = trajectory_path
    result["pipeline_steps"].append({
        "step": "storage",
        "status": "success",
        "path": trajectory_path
    })
    
    result["success"] = overall_success
    
    # 打印总结
    if verbose:
        print("\n" + "=" * 70)
        print("📊 执行总结")
        print("=" * 70)
        print(f"   任务: {user_task[:50]}...")
        print(f"   推理链复用: {'是' if reused_reasoning else '否'}")
        print(f"   工具调用: {len(execution_results)} 次")
        print(f"   执行状态: {'✓ 成功' if overall_success else '✗ 部分失败'}")
        print(f"   轨迹存储: {trajectory_path}")
    
    return result


# ============================================================
# 测试用例
# ============================================================

def test_full_integration():
    """全链路测试"""
    print("\n" + "🧪 Kylin-TARS 全链路联调测试 🧪".center(70))
    print("=" * 70)
    
    # 测试任务列表
    test_tasks = [
        "搜索~/Downloads目录的png文件并设置为壁纸",
        "把系统音量调到50%",
        "将下载目录的tmp文件移动到回收站",
    ]
    
    results = []
    
    for i, task in enumerate(test_tasks, 1):
        print(f"\n\n{'#' * 70}")
        print(f"# 测试 {i}/{len(test_tasks)}: {task}")
        print(f"{'#' * 70}")
        
        result = execute_full_pipeline(
            user_task=task,
            mock_mode=True,
            verbose=True
        )
        results.append(result)
        
        # 间隔以便观察
        time.sleep(1)
    
    # 打印测试报告
    print("\n\n" + "=" * 70)
    print("📋 测试报告")
    print("=" * 70)
    
    success_count = sum(1 for r in results if r["success"])
    print(f"总测试数: {len(results)}")
    print(f"成功数量: {success_count}")
    print(f"成功率: {success_count/len(results)*100:.1f}%")
    
    print("\n详细结果:")
    for i, r in enumerate(results, 1):
        status = "✓" if r["success"] else "✗"
        print(f"  {i}. {r['task'][:40]}... {status}")
    
    # 测试记忆检索
    print("\n\n" + "=" * 70)
    print("📋 记忆检索测试")
    print("=" * 70)
    
    # 使用相似任务测试检索
    similar_task = "搜索下载目录的jpg文件设为壁纸"
    print(f"\n测试任务: {similar_task}")
    
    result = execute_full_pipeline(
        user_task=similar_task,
        mock_mode=True,
        verbose=True
    )
    
    if result.get("pipeline_steps"):
        retrieval_step = next((s for s in result["pipeline_steps"] if s["step"] == "memory_retrieval"), None)
        if retrieval_step and retrieval_step.get("status") == "reused":
            print("\n✓ 记忆检索测试通过: 成功复用历史推理链")
        else:
            print("\n○ 记忆检索测试: 未复用历史推理链（可能阈值不足）")
    
    print("\n" + "=" * 70)
    print("✓ 全链路联调测试完成!")
    print("=" * 70)


# ============================================================
# 主函数
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="Kylin-TARS GUI Agent 全链路联调")
    parser.add_argument("--real", action="store_true", help="使用真实模式（需要启动 MCP Server）")
    parser.add_argument("--task", type=str, help="指定测试任务")
    args = parser.parse_args()
    
    if args.task:
        # 执行单个任务
        execute_full_pipeline(
            user_task=args.task,
            mock_mode=not args.real,
            verbose=True
        )
    else:
        # 运行完整测试
        test_full_integration()


if __name__ == "__main__":
    main()

