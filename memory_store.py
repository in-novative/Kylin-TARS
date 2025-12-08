#!/usr/bin/env python3
"""
记忆模块 - 协作轨迹存储与检索

本模块实现 GUI Agent 的记忆功能：
1. 存储协作轨迹（任务 + 推理链 + 执行结果 + 截图路径）
2. 按时间/关键词检索历史轨迹
3. 支持相似任务的推理链复用

作者：GUI Agent Team
日期：2024-12
"""

import json
import os
import time
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any

# ============================================================
# 存储配置
# ============================================================

# 存储模式配置
# - "project": 存储在项目目录内（便于版本控制和项目迁移）
# - "system": 存储在用户配置目录（数据持久化，多项目共享）
STORAGE_MODE = os.environ.get("MEMORY_STORAGE_MODE", "project")  # 默认改为项目内

# 项目根目录（自动检测当前文件所在目录）
PROJECT_ROOT = Path(__file__).parent.absolute()

# 根据模式选择存储目录
if STORAGE_MODE == "project":
    # 存储在项目内的 data/memory 目录
    STORAGE_DIR = str(PROJECT_ROOT / "data" / "collaboration_memory")
else:
    # 存储在用户配置目录（XDG规范）
    STORAGE_DIR = os.path.expanduser("~/.config/kylin-gui-agent/collaboration_memory")

# 确保存储目录存在
os.makedirs(STORAGE_DIR, exist_ok=True)

# 打印当前存储位置（仅首次导入时）
print(f"📁 记忆存储位置: {STORAGE_DIR}")


# ============================================================
# 辅助函数
# ============================================================

def generate_task_hash(task: str) -> str:
    """
    生成任务唯一标识（MD5哈希前8位）
    
    Args:
        task: 用户任务描述
        
    Returns:
        8位哈希字符串
    """
    return hashlib.md5(task.encode('utf-8')).hexdigest()[:8]


def validate_screenshot_paths(paths: List[str]) -> List[str]:
    """
    验证截图路径，只保留存在的文件
    
    Args:
        paths: 截图路径列表
        
    Returns:
        有效的截图路径列表
    """
    if not paths:
        return []
    return [p for p in paths if os.path.exists(p)]


# ============================================================
# 核心存储函数
# ============================================================

def save_collaboration_trajectory(
    task: str,
    reasoning_chain: Any,
    execution_result: str = "",
    screenshot_paths: Optional[List[str]] = None,
    gui_action: Optional[Dict] = None,
    success: bool = True,
    metadata: Optional[Dict] = None
) -> str:
    """
    保存协作轨迹到本地JSON文件
    
    Args:
        task: 用户原始任务
        reasoning_chain: System-2生成的推理链（字典或JSON字符串）
        execution_result: 子智能体执行结果描述
        screenshot_paths: 执行过程的截图路径列表
        gui_action: GUI操作记录
        success: 执行是否成功
        metadata: 额外元数据
        
    Returns:
        保存的文件路径
    """
    # 处理推理链格式
    if isinstance(reasoning_chain, str):
        try:
            reasoning_chain = json.loads(reasoning_chain)
        except json.JSONDecodeError:
            reasoning_chain = {"raw": reasoning_chain}
    
    # 验证截图路径
    valid_screenshots = validate_screenshot_paths(screenshot_paths or [])
    
    # 提取关键信息用于检索
    keywords = extract_keywords(task)
    agents_involved = extract_agents(reasoning_chain)
    
    # 构建轨迹数据结构
    trajectory = {
        # 基本信息
        "task": task,
        "task_hash": generate_task_hash(task),
        "keywords": keywords,
        
        # 推理链
        "reasoning_chain": reasoning_chain,
        
        # 执行信息
        "execution_result": execution_result,
        "gui_action": gui_action,
        "agents_involved": agents_involved,
        "success": success,
        
        # 截图
        "screenshot_paths": valid_screenshots,
        "screenshot_count": len(valid_screenshots),
        
        # 时间戳
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "timestamp_unix": int(time.time()),
        
        # 元数据
        "metadata": metadata or {}
    }
    
    # 生成文件名（时间戳_任务哈希.json）
    filename = f"{trajectory['timestamp_unix']}_{trajectory['task_hash']}.json"
    file_path = os.path.join(STORAGE_DIR, filename)
    
    # 保存到JSON文件
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(trajectory, f, ensure_ascii=False, indent=2)
    
    print(f"✓ 协作轨迹已保存: {file_path}")
    return file_path


def extract_keywords(task: str) -> List[str]:
    """
    从任务描述中提取关键词
    
    Args:
        task: 用户任务描述
        
    Returns:
        关键词列表
    """
    # 常见操作关键词
    action_keywords = [
        "搜索", "查找", "设置", "更换", "调整", "移动", "删除", "复制",
        "打开", "关闭", "安装", "卸载", "下载", "上传", "创建", "修改"
    ]
    
    # 常见对象关键词
    object_keywords = [
        "文件", "目录", "文件夹", "壁纸", "音量", "亮度", "网络", "蓝牙",
        "浏览器", "终端", "应用", "程序", "图片", "文档", "视频", "音乐"
    ]
    
    keywords = []
    
    # 提取操作关键词
    for kw in action_keywords:
        if kw in task:
            keywords.append(kw)
    
    # 提取对象关键词
    for kw in object_keywords:
        if kw in task:
            keywords.append(kw)
    
    # 提取路径（如 ~/Downloads）
    import re
    paths = re.findall(r'[~/\w]+/\w+', task)
    keywords.extend(paths)
    
    # 提取文件扩展名（如 .png, .tmp）
    extensions = re.findall(r'\.\w+', task)
    keywords.extend(extensions)
    
    return list(set(keywords))  # 去重


def extract_agents(reasoning_chain: Dict) -> List[str]:
    """
    从推理链中提取涉及的智能体
    
    Args:
        reasoning_chain: 推理链字典
        
    Returns:
        智能体名称列表
    """
    agents = set()
    
    # 从 thought_chain.agent_selection 提取
    if "thought_chain" in reasoning_chain:
        tc = reasoning_chain["thought_chain"]
        if "agent_selection" in tc:
            for item in tc["agent_selection"]:
                if isinstance(item, dict) and "agent" in item:
                    agents.add(item["agent"])
    
    # 从 execution_plan 提取
    if "execution_plan" in reasoning_chain:
        for step in reasoning_chain["execution_plan"]:
            if isinstance(step, dict) and "agent" in step:
                agents.add(step["agent"])
    
    return list(agents)


# ============================================================
# 检索函数
# ============================================================

def list_trajectories(limit: int = 10, success_only: bool = False) -> List[Dict]:
    """
    列出最近的协作轨迹（按时间倒序）
    
    Args:
        limit: 返回条数
        success_only: 是否只返回成功的轨迹
        
    Returns:
        轨迹列表
    """
    # 获取所有轨迹文件
    trajectory_files = [f for f in os.listdir(STORAGE_DIR) if f.endswith(".json")]
    
    # 按时间戳倒序排序
    trajectory_files.sort(reverse=True, key=lambda x: int(x.split("_")[0]))
    
    # 读取轨迹
    trajectories = []
    for file in trajectory_files:
        if len(trajectories) >= limit:
            break
            
        file_path = os.path.join(STORAGE_DIR, file)
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                traj = json.load(f)
                if success_only and not traj.get("success", False):
                    continue
                trajectories.append(traj)
        except Exception as e:
            print(f"读取轨迹失败 {file}: {e}")
    
    return trajectories


def search_trajectories(
    keyword: str = None,
    agent: str = None,
    limit: int = 10
) -> List[Dict]:
    """
    搜索协作轨迹
    
    Args:
        keyword: 关键词（匹配任务描述或关键词列表）
        agent: 智能体名称（匹配涉及的智能体）
        limit: 返回条数
        
    Returns:
        匹配的轨迹列表
    """
    all_trajectories = list_trajectories(limit=1000)  # 获取所有轨迹
    
    matched = []
    for traj in all_trajectories:
        if len(matched) >= limit:
            break
        
        # 关键词匹配
        if keyword:
            task_match = keyword.lower() in traj.get("task", "").lower()
            keywords_match = keyword.lower() in " ".join(traj.get("keywords", [])).lower()
            if not (task_match or keywords_match):
                continue
        
        # 智能体匹配
        if agent:
            if agent not in traj.get("agents_involved", []):
                continue
        
        matched.append(traj)
    
    return matched


def find_similar_task(task: str, threshold: float = 0.5) -> Optional[Dict]:
    """
    查找相似任务的历史轨迹（用于推理链复用）
    
    Args:
        task: 当前任务描述
        threshold: 相似度阈值（0-1）
        
    Returns:
        最相似的轨迹，无匹配返回None
    """
    current_keywords = set(extract_keywords(task))
    if not current_keywords:
        return None
    
    all_trajectories = list_trajectories(limit=100, success_only=True)
    
    best_match = None
    best_score = 0
    
    for traj in all_trajectories:
        traj_keywords = set(traj.get("keywords", []))
        if not traj_keywords:
            continue
        
        # 计算Jaccard相似度
        intersection = len(current_keywords & traj_keywords)
        union = len(current_keywords | traj_keywords)
        similarity = intersection / union if union > 0 else 0
        
        if similarity > best_score and similarity >= threshold:
            best_score = similarity
            best_match = traj
    
    if best_match:
        print(f"✓ 找到相似任务 (相似度: {best_score:.2f}): {best_match['task'][:50]}...")
    
    return best_match


def get_trajectory_by_hash(task_hash: str) -> Optional[Dict]:
    """
    根据任务哈希获取轨迹
    
    Args:
        task_hash: 任务哈希值
        
    Returns:
        轨迹字典
    """
    trajectory_files = [f for f in os.listdir(STORAGE_DIR) if f.endswith(".json")]
    
    for file in trajectory_files:
        if task_hash in file:
            file_path = os.path.join(STORAGE_DIR, file)
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
    
    return None


# ============================================================
# 统计函数
# ============================================================

def get_memory_stats() -> Dict:
    """
    获取记忆模块统计信息
    
    Returns:
        统计信息字典
    """
    trajectory_files = [f for f in os.listdir(STORAGE_DIR) if f.endswith(".json")]
    
    total_count = len(trajectory_files)
    success_count = 0
    agent_counts = {}
    
    for file in trajectory_files:
        file_path = os.path.join(STORAGE_DIR, file)
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                traj = json.load(f)
                if traj.get("success", False):
                    success_count += 1
                for agent in traj.get("agents_involved", []):
                    agent_counts[agent] = agent_counts.get(agent, 0) + 1
        except:
            pass
    
    return {
        "total_trajectories": total_count,
        "success_count": success_count,
        "success_rate": success_count / total_count if total_count > 0 else 0,
        "agent_usage": agent_counts,
        "storage_dir": STORAGE_DIR
    }


def clear_old_trajectories(days: int = 30) -> int:
    """
    清理指定天数之前的轨迹
    
    Args:
        days: 保留最近N天的轨迹
        
    Returns:
        删除的文件数量
    """
    cutoff_time = int(time.time()) - (days * 24 * 60 * 60)
    trajectory_files = [f for f in os.listdir(STORAGE_DIR) if f.endswith(".json")]
    
    deleted_count = 0
    for file in trajectory_files:
        try:
            timestamp = int(file.split("_")[0])
            if timestamp < cutoff_time:
                os.remove(os.path.join(STORAGE_DIR, file))
                deleted_count += 1
        except:
            pass
    
    if deleted_count > 0:
        print(f"已清理 {deleted_count} 条过期轨迹")
    
    return deleted_count


# ============================================================
# 与 System-2 集成
# ============================================================

def save_from_reasoning_result(result: Dict, execution_result: str = "") -> str:
    """
    从 system2_prompt.py 的 execute_reasoning_pipeline 结果保存轨迹
    
    Args:
        result: execute_reasoning_pipeline 的返回值
        execution_result: 执行结果描述
        
    Returns:
        保存的文件路径
    """
    return save_collaboration_trajectory(
        task=result.get("user_task", ""),
        reasoning_chain=result.get("master_reasoning", {}),
        execution_result=execution_result,
        screenshot_paths=[result.get("screenshot")] if result.get("screenshot") else [],
        gui_action=result.get("gui_action"),
        success=result.get("success", False),
        metadata={
            "source": "system2_prompt",
            "original_timestamp": result.get("timestamp")
        }
    )


# ============================================================
# 测试函数
# ============================================================

def test_memory_store():
    """测试记忆存储功能"""
    print("=" * 60)
    print("记忆模块测试")
    print("=" * 60)
    
    # 测试数据
    test_cases = [
        {
            "task": "搜索~/Downloads目录的png文件并设置为壁纸",
            "reasoning_chain": {
                "thought_chain": {
                    "task_understanding": "用户希望从下载目录找到PNG图片并设置为桌面壁纸",
                    "task_decomposition": "1. 搜索~/Downloads目录下的png文件；2. 选择图片；3. 设置壁纸",
                    "agent_selection": [
                        {"step": 1, "agent": "FileAgent", "reason": "需要文件搜索功能"},
                        {"step": 2, "agent": "SettingsAgent", "reason": "需要系统设置功能"}
                    ],
                    "risk_assessment": "~/Downloads目录可能没有png文件",
                    "fallback_plan": "如果没有png文件，提示用户上传图片"
                },
                "execution_plan": [
                    {"step": 1, "action": "搜索png文件", "agent": "FileAgent"},
                    {"step": 2, "action": "设置壁纸", "agent": "SettingsAgent"}
                ],
                "milestone_markers": ["search_complete", "wallpaper_set"]
            },
            "execution_result": "成功搜索到2个png文件，壁纸设置完成",
            "success": True
        },
        {
            "task": "把系统音量调到50%",
            "reasoning_chain": {
                "thought_chain": {
                    "task_understanding": "用户希望将系统音量调整到50%",
                    "task_decomposition": "1. 打开系统设置；2. 调整音量",
                    "agent_selection": [
                        {"step": 1, "agent": "SettingsAgent", "reason": "需要系统设置功能"}
                    ],
                    "risk_assessment": "可能找不到音量控制选项",
                    "fallback_plan": "使用终端命令调整音量"
                },
                "execution_plan": [
                    {"step": 1, "action": "打开系统设置", "agent": "SettingsAgent"},
                    {"step": 2, "action": "调整音量到50%", "agent": "SettingsAgent"}
                ],
                "milestone_markers": ["settings_opened", "volume_set"]
            },
            "execution_result": "音量已调整到50%",
            "success": True
        },
        {
            "task": "将下载目录的tmp文件移动到回收站",
            "reasoning_chain": {
                "thought_chain": {
                    "task_understanding": "用户需要删除tmp文件",
                    "task_decomposition": "1. 搜索tmp文件；2. 移动到回收站",
                    "agent_selection": [
                        {"step": 1, "agent": "FileAgent", "reason": "需要文件操作功能"}
                    ],
                    "risk_assessment": "文件可能不存在",
                    "fallback_plan": "提示用户检查文件名"
                },
                "execution_plan": [
                    {"step": 1, "action": "搜索tmp文件", "agent": "FileAgent"},
                    {"step": 2, "action": "移动到回收站", "agent": "FileAgent"}
                ],
                "milestone_markers": ["search_complete", "file_moved"]
            },
            "execution_result": "文件已移动到回收站",
            "success": True
        }
    ]
    
    # 保存测试轨迹
    print("\n--- 保存测试轨迹 ---")
    saved_paths = []
    for i, case in enumerate(test_cases, 1):
        print(f"\n测试 {i}: {case['task'][:40]}...")
        path = save_collaboration_trajectory(
            task=case["task"],
            reasoning_chain=case["reasoning_chain"],
            execution_result=case["execution_result"],
            success=case["success"]
        )
        saved_paths.append(path)
        time.sleep(1)  # 确保时间戳不同
    
    # 测试列表功能
    print("\n--- 列出最近轨迹 ---")
    recent = list_trajectories(limit=3)
    for traj in recent:
        print(f"  • {traj['task'][:40]}... [{traj['timestamp']}]")
    
    # 测试搜索功能
    print("\n--- 关键词搜索测试 ---")
    results = search_trajectories(keyword="壁纸", limit=5)
    print(f"搜索 '壁纸': 找到 {len(results)} 条记录")
    for r in results:
        print(f"  • {r['task'][:50]}...")
    
    # 测试智能体搜索
    print("\n--- 智能体搜索测试 ---")
    results = search_trajectories(agent="FileAgent", limit=5)
    print(f"搜索 FileAgent: 找到 {len(results)} 条记录")
    
    # 测试相似任务查找
    print("\n--- 相似任务查找测试 ---")
    similar = find_similar_task("搜索下载目录的jpg文件并设置为壁纸")
    if similar:
        print(f"  匹配任务: {similar['task'][:50]}...")
    
    # 显示统计信息
    print("\n--- 记忆统计 ---")
    stats = get_memory_stats()
    print(f"  总轨迹数: {stats['total_trajectories']}")
    print(f"  成功数量: {stats['success_count']}")
    print(f"  成功率: {stats['success_rate']:.1%}")
    print(f"  智能体使用: {stats['agent_usage']}")
    print(f"  存储目录: {stats['storage_dir']}")
    
    print("\n" + "=" * 60)
    print("✓ 记忆模块测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    test_memory_store()

