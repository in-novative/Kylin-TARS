#!/usr/bin/env python3
"""
System-2 推理与记忆整合模块

本模块实现「推理链生成→自动存储→智能复用」全流程：
1. 生成推理链并自动存储到记忆
2. 支持相似任务的推理链复用
3. 提供 Master Agent 标准化调用接口
4. 格式校验确保 MCP 协议兼容

作者：GUI Agent Team
日期：2024-12
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any, Tuple

# 导入推理模块
from system2_prompt import (
    generate_master_reasoning,
    generate_gui_action,
    execute_reasoning_pipeline,
    create_fallback_chain,
    call_vllm_api,
    API_BASE
)

# 导入记忆模块
from memory_store import (
    save_collaboration_trajectory,
    list_trajectories,
    search_trajectories,
    find_similar_task,
    get_memory_stats,
    STORAGE_DIR
)

# 尝试导入高级检索模块
try:
    from memory_retrieve import (
        retrieve_similar_trajectory,
        reuse_reasoning_chain,
        calculate_combined_similarity
    )
    HAS_ADVANCED_RETRIEVE = True
except ImportError:
    HAS_ADVANCED_RETRIEVE = False

# ============================================================
# MCP 格式校验
# ============================================================

# MCP 协议要求的核心字段
MCP_REQUIRED_FIELDS = {
    "thought_chain": {
        "task_decomposition": "任务分解步骤",
        "agent_selection": "智能体选择列表",
    },
    "execution_plan": "执行计划列表",
    "milestone_markers": "里程碑标记列表"
}


def validate_for_mcp(reasoning_chain: Dict) -> Tuple[bool, str]:
    """
    校验推理链是否符合 MCP 调用要求
    
    Args:
        reasoning_chain: 推理链字典
        
    Returns:
        (is_valid, message)
    """
    errors = []
    
    # 检查 thought_chain
    if "thought_chain" not in reasoning_chain:
        errors.append("缺失 thought_chain")
    else:
        tc = reasoning_chain["thought_chain"]
        if "task_decomposition" not in tc or not tc["task_decomposition"]:
            errors.append("缺失或为空: thought_chain.task_decomposition")
        if "agent_selection" not in tc:
            errors.append("缺失: thought_chain.agent_selection")
    
    # 检查 execution_plan
    if "execution_plan" not in reasoning_chain:
        errors.append("缺失 execution_plan")
    elif not reasoning_chain["execution_plan"]:
        errors.append("execution_plan 为空")
    
    # 检查 milestone_markers
    if "milestone_markers" not in reasoning_chain:
        errors.append("缺失 milestone_markers")
    elif not reasoning_chain["milestone_markers"]:
        errors.append("milestone_markers 为空")
    
    if errors:
        return False, "; ".join(errors)
    
    return True, "格式符合 MCP 要求"


def normalize_for_mcp(reasoning_chain: Dict) -> Dict:
    """
    标准化推理链格式，确保符合 MCP 要求
    
    Args:
        reasoning_chain: 原始推理链
        
    Returns:
        标准化后的推理链
    """
    normalized = reasoning_chain.copy()
    
    # 确保 thought_chain 存在
    if "thought_chain" not in normalized:
        normalized["thought_chain"] = {}
    
    tc = normalized["thought_chain"]
    
    # 确保必要字段存在
    if "task_decomposition" not in tc:
        tc["task_decomposition"] = "待分解"
    
    if "agent_selection" not in tc:
        tc["agent_selection"] = []
    
    if "risk_assessment" not in tc:
        tc["risk_assessment"] = "未评估"
    
    if "fallback_plan" not in tc:
        tc["fallback_plan"] = "重试或手动干预"
    
    # 确保 execution_plan 存在
    if "execution_plan" not in normalized:
        normalized["execution_plan"] = []
    
    # 确保 milestone_markers 存在
    if "milestone_markers" not in normalized:
        normalized["milestone_markers"] = ["start", "execute", "complete"]
    
    return normalized


# ============================================================
# 推理链复用
# ============================================================

def try_reuse_reasoning(
    user_task: str,
    similarity_threshold: float = 0.6,
    verbose: bool = True
) -> Optional[Dict]:
    """
    尝试复用相似任务的推理链
    
    Args:
        user_task: 当前用户任务
        similarity_threshold: 相似度阈值 (0-1 或 0-100)
        verbose: 是否打印详细信息
        
    Returns:
        复用的推理链（如果找到），否则 None
    """
    # 使用高级检索模块（如果可用）
    if HAS_ADVANCED_RETRIEVE:
        # 将阈值转换为 0-100 范围
        threshold_100 = int(similarity_threshold * 100) if similarity_threshold <= 1 else int(similarity_threshold)
        reused = reuse_reasoning_chain(user_task, threshold=threshold_100, verbose=verbose)
        if reused:
            return reused
        return None
    
    # 回退到基础检索
    similar = find_similar_task(user_task, threshold=similarity_threshold)
    
    if similar:
        if verbose:
            print(f"\n✓ 找到可复用的历史推理链")
            print(f"  历史任务: {similar['task'][:50]}...")
            print(f"  执行结果: {similar.get('execution_result', 'N/A')[:50]}...")
        
        # 返回历史推理链，并标记为复用
        reused_chain = similar.get("reasoning_chain", {}).copy()
        reused_chain["_reused_from"] = {
            "task": similar["task"],
            "task_hash": similar.get("task_hash"),
            "timestamp": similar.get("timestamp"),
            "success": similar.get("success", False)
        }
        return reused_chain
    
    return None


# ============================================================
# 核心整合函数
# ============================================================

def reasoning_with_memory(
    user_task: str,
    screenshot_path: Optional[str] = None,
    execution_result: str = "",
    screenshot_paths: Optional[List[str]] = None,
    success: bool = True,
    enable_reuse: bool = True,
    reuse_threshold: float = 0.6,
    verbose: bool = True
) -> Tuple[Dict, str]:
    """
    一站式流程：推理链复用检查 → 生成推理链 → 自动存储到记忆
    
    Args:
        user_task: 用户任务描述
        screenshot_path: 当前截图路径（用于 GUI 操作生成）
        execution_result: 子智能体执行结果（可选，调用子智能体后补充）
        screenshot_paths: 执行过程的截图路径列表
        success: 执行是否成功
        enable_reuse: 是否启用推理链复用
        reuse_threshold: 复用相似度阈值
        verbose: 是否打印详细信息
        
    Returns:
        (reasoning_chain, trajectory_path)
    """
    if verbose:
        print("\n" + "=" * 70)
        print("System-2 推理与记忆整合流程")
        print("=" * 70)
        print(f"用户任务: {user_task}")
    
    reasoning_chain = None
    reused = False
    
    # Step 1: 尝试复用历史推理链
    if enable_reuse:
        if verbose:
            print("\n--- Step 1: 检查推理链复用 ---")
        reasoning_chain = try_reuse_reasoning(
            user_task, 
            similarity_threshold=reuse_threshold,
            verbose=verbose
        )
        if reasoning_chain:
            reused = True
    
    # Step 2: 生成新推理链（如果没有复用）
    if reasoning_chain is None:
        if verbose:
            print("\n--- Step 2: 生成新推理链 ---")
        reasoning_chain = generate_master_reasoning(
            user_task=user_task,
            verbose=verbose
        )
    
    # Step 3: MCP 格式校验和标准化
    if verbose:
        print("\n--- Step 3: MCP 格式校验 ---")
    
    is_valid, msg = validate_for_mcp(reasoning_chain)
    if not is_valid:
        if verbose:
            print(f"⚠️ 格式不符合 MCP 要求: {msg}")
            print("  正在标准化...")
        reasoning_chain = normalize_for_mcp(reasoning_chain)
    else:
        if verbose:
            print(f"✓ {msg}")
    
    # Step 4: 生成 GUI 操作（如果提供了截图）
    gui_action = None
    if screenshot_path and Path(screenshot_path).exists():
        if verbose:
            print("\n--- Step 4: 生成 GUI 操作 ---")
        
        # 获取第一步操作作为指令
        first_step = ""
        if "execution_plan" in reasoning_chain and reasoning_chain["execution_plan"]:
            first_step = reasoning_chain["execution_plan"][0].get("action", "")
        
        instruction = f"{user_task}\n当前步骤: {first_step}" if first_step else user_task
        
        gui_action = generate_gui_action(
            instruction=instruction,
            screenshot_path=screenshot_path,
            verbose=verbose
        )
    
    # Step 5: 存储到记忆
    if verbose:
        print("\n--- Step 5: 存储到记忆 ---")
    
    # 准备截图路径列表
    all_screenshots = screenshot_paths or []
    if screenshot_path and screenshot_path not in all_screenshots:
        all_screenshots.insert(0, screenshot_path)
    
    # 设置默认执行结果
    if not execution_result:
        if reused:
            execution_result = "推理链已从历史记录复用，等待子智能体执行"
        else:
            execution_result = "推理链已生成，等待子智能体执行"
    
    trajectory_path = save_collaboration_trajectory(
        task=user_task,
        reasoning_chain=reasoning_chain,
        execution_result=execution_result,
        screenshot_paths=all_screenshots,
        gui_action=gui_action,
        success=success,
        metadata={
            "source": "system2_memory",
            "reused": reused,
            "mcp_validated": True
        }
    )
    
    # 输出摘要
    if verbose:
        print("\n" + "=" * 70)
        print("流程完成摘要")
        print("=" * 70)
        print(f"  推理链复用: {'是' if reused else '否'}")
        print(f"  MCP 格式: 已校验")
        print(f"  GUI 操作: {'已生成' if gui_action else '无'}")
        print(f"  轨迹存储: {trajectory_path}")
    
    return reasoning_chain, trajectory_path


# ============================================================
# Master Agent 调用接口
# ============================================================

def get_reasoning_for_master(
    user_task: str,
    enable_reuse: bool = True,
    verbose: bool = False
) -> Dict:
    """
    Master Agent 调用接口：返回标准化的推理链字典
    
    Args:
        user_task: 用户任务描述
        enable_reuse: 是否启用推理链复用
        verbose: 是否打印详细信息
        
    Returns:
        符合 MCP 格式的推理链字典
    """
    reasoning_chain, _ = reasoning_with_memory(
        user_task=user_task,
        enable_reuse=enable_reuse,
        verbose=verbose
    )
    
    # 清理内部字段
    clean_chain = {k: v for k, v in reasoning_chain.items() if not k.startswith("_")}
    
    return clean_chain


def get_next_action_for_master(
    user_task: str,
    screenshot_path: str,
    action_history: Optional[List[str]] = None,
    verbose: bool = False
) -> Dict:
    """
    Master Agent 调用接口：获取下一步 GUI 操作
    
    Args:
        user_task: 用户任务描述
        screenshot_path: 当前截图路径
        action_history: 历史操作记录
        verbose: 是否打印详细信息
        
    Returns:
        GUI 操作字典
    """
    gui_action = generate_gui_action(
        instruction=user_task,
        screenshot_path=screenshot_path,
        action_history=action_history,
        verbose=verbose
    )
    
    # 清理内部字段
    clean_action = {k: v for k, v in gui_action.items() if not k.startswith("_")}
    
    return clean_action


def update_trajectory_result(
    task_hash: str,
    execution_result: str,
    success: bool,
    screenshot_paths: Optional[List[str]] = None
) -> bool:
    """
    更新轨迹的执行结果（子智能体执行完成后调用）
    
    Args:
        task_hash: 任务哈希
        execution_result: 执行结果描述
        success: 是否成功
        screenshot_paths: 执行后的截图路径
        
    Returns:
        是否更新成功
    """
    import os
    
    # 查找轨迹文件
    trajectory_files = [f for f in os.listdir(STORAGE_DIR) if f.endswith(".json")]
    
    for file in trajectory_files:
        if task_hash in file:
            file_path = os.path.join(STORAGE_DIR, file)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    trajectory = json.load(f)
                
                # 更新字段
                trajectory["execution_result"] = execution_result
                trajectory["success"] = success
                if screenshot_paths:
                    trajectory["screenshot_paths"].extend(screenshot_paths)
                    trajectory["screenshot_count"] = len(trajectory["screenshot_paths"])
                trajectory["metadata"]["updated_at"] = datetime.now().isoformat()
                
                # 保存
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(trajectory, f, ensure_ascii=False, indent=2)
                
                print(f"✓ 轨迹已更新: {file_path}")
                return True
            except Exception as e:
                print(f"更新轨迹失败: {e}")
                return False
    
    print(f"未找到任务哈希为 {task_hash} 的轨迹")
    return False


# ============================================================
# 批量处理
# ============================================================

def batch_reasoning(
    tasks: List[str],
    verbose: bool = True
) -> List[Dict]:
    """
    批量生成推理链
    
    Args:
        tasks: 任务列表
        verbose: 是否打印详细信息
        
    Returns:
        推理链列表
    """
    results = []
    
    for i, task in enumerate(tasks, 1):
        if verbose:
            print(f"\n\n{'#' * 70}")
            print(f"# 批量任务 {i}/{len(tasks)}: {task[:50]}...")
            print(f"{'#' * 70}")
        
        reasoning_chain, trajectory_path = reasoning_with_memory(
            user_task=task,
            verbose=verbose
        )
        
        results.append({
            "task": task,
            "reasoning_chain": reasoning_chain,
            "trajectory_path": trajectory_path
        })
    
    return results


# ============================================================
# 状态查询
# ============================================================

def get_system_status() -> Dict:
    """
    获取系统状态（用于 Gradio 界面展示）
    
    Returns:
        系统状态字典
    """
    import requests
    
    status = {
        "api_available": False,
        "api_base": API_BASE,
        "memory_stats": get_memory_stats(),
        "timestamp": datetime.now().isoformat()
    }
    
    # 检查 API 状态
    try:
        response = requests.get(f"{API_BASE}/health", timeout=5)
        status["api_available"] = response.status_code == 200
    except:
        pass
    
    return status


# ============================================================
# 测试函数
# ============================================================

def test_api_health():
    """检查 API 服务状态"""
    import requests
    
    print("=" * 60)
    print("检查 vLLM API 服务状态")
    print("=" * 60)
    
    try:
        response = requests.get(f"{API_BASE}/health", timeout=10)
        if response.status_code == 200:
            print("✓ API 服务正常")
            return True
        else:
            print(f"✗ API 服务异常: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ 无法连接 API 服务: {e}")
        return False


def test_system2_memory():
    """测试 System-2 与记忆整合功能"""
    print("\n" + "🚀 System-2 与记忆整合测试 🚀".center(60))
    print("=" * 60)
    
    # 检查 API 状态
    if not test_api_health():
        print("\n❌ API 服务未就绪，请先启动 vLLM 服务")
        return
    
    # 测试任务列表
    test_tasks = [
        "搜索~/Downloads目录的png文件并设置为壁纸",
        "把系统音量调到50%",
        "将下载目录的tmp文件移动到回收站",
    ]
    
    # 测试截图路径
    test_screenshot = "/data1/cyx/anything/麒麟OS桌面.png"
    
    print("\n" + "=" * 60)
    print("测试1: 完整推理+存储流程")
    print("=" * 60)
    
    # 测试第一个任务（带截图）
    reasoning_chain, trajectory_path = reasoning_with_memory(
        user_task=test_tasks[0],
        screenshot_path=test_screenshot if Path(test_screenshot).exists() else None,
        execution_result="测试执行：成功搜索到png文件",
        success=True,
        enable_reuse=False,  # 第一次不启用复用
        verbose=True
    )
    
    print("\n推理链摘要:")
    tc = reasoning_chain.get("thought_chain", {})
    print(f"  任务分解: {tc.get('task_decomposition', 'N/A')[:80]}...")
    print(f"  风险评估: {tc.get('risk_assessment', 'N/A')}")
    
    print("\n" + "=" * 60)
    print("测试2: 推理链复用")
    print("=" * 60)
    
    # 测试相似任务的复用
    similar_task = "搜索下载目录的jpg文件设置为壁纸"
    reasoning_chain2, _ = reasoning_with_memory(
        user_task=similar_task,
        enable_reuse=True,
        reuse_threshold=0.5,
        verbose=True
    )
    
    if reasoning_chain2.get("_reused_from"):
        print(f"\n✓ 成功复用历史推理链!")
    else:
        print(f"\n⚠️ 未找到可复用的推理链，生成了新的")
    
    print("\n" + "=" * 60)
    print("测试3: Master Agent 接口")
    print("=" * 60)
    
    master_reasoning = get_reasoning_for_master(
        user_task=test_tasks[1],
        enable_reuse=True,
        verbose=False
    )
    
    print(f"返回类型: {type(master_reasoning)}")
    print(f"核心字段: {list(master_reasoning.keys())}")
    
    # MCP 格式校验
    is_valid, msg = validate_for_mcp(master_reasoning)
    print(f"MCP 格式校验: {'✓ ' + msg if is_valid else '✗ ' + msg}")
    
    print("\n" + "=" * 60)
    print("测试4: 系统状态")
    print("=" * 60)
    
    status = get_system_status()
    print(f"API 可用: {status['api_available']}")
    print(f"记忆统计:")
    print(f"  总轨迹数: {status['memory_stats']['total_trajectories']}")
    print(f"  成功率: {status['memory_stats']['success_rate']:.1%}")
    
    print("\n" + "=" * 60)
    print("✓ 所有测试完成!")
    print("=" * 60)


if __name__ == "__main__":
    test_system2_memory()

