#!/usr/bin/env python3
"""
记忆检索模块 - 高效检索与推理链复用

本模块实现记忆的高效检索功能：
1. 模糊匹配检索（基于 fuzzywuzzy）
2. 多策略匹配（精确/模糊/关键词）
3. 推理链智能复用
4. 检索性能优化

作者：GUI Agent Team
日期：2024-12
"""

import json
import time
from datetime import datetime
from typing import Optional, Dict, List, Tuple, Any

# 导入记忆存储模块
from memory_store import (
    list_trajectories,
    search_trajectories,
    extract_keywords,
    STORAGE_DIR
)

# 尝试导入 fuzzywuzzy（模糊匹配库）
try:
    from fuzzywuzzy import fuzz
    HAS_FUZZYWUZZY = True
except ImportError:
    HAS_FUZZYWUZZY = False
    print("提示: fuzzywuzzy 未安装，将使用基础匹配。")
    print("安装命令: pip install fuzzywuzzy python-Levenshtein")

# 尝试导入麒麟AI框架（语义检索）
HAS_KYLIN_AI = False
KYLIN_EMBED_MODEL = None
try:
    # 检查是否有麒麟AI框架的embedding接口
    import subprocess
    result = subprocess.run(["which", "kylin-llm-embed"], capture_output=True, timeout=2)
    if result.returncode == 0:
        HAS_KYLIN_AI = True
        print("✓ 检测到麒麟AI框架，将启用语义检索")
except:
    pass

# 如果没有麒麟AI框架，尝试使用其他embedding库（如sentence-transformers）
if not HAS_KYLIN_AI:
    try:
        import sentence_transformers
        HAS_SENTENCE_TRANSFORMERS = True
        # 使用轻量级中文模型
        try:
            KYLIN_EMBED_MODEL = sentence_transformers.SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
            print("✓ 使用 sentence-transformers 进行语义检索")
        except:
            HAS_SENTENCE_TRANSFORMERS = False
    except ImportError:
        HAS_SENTENCE_TRANSFORMERS = False
        print("提示: 未检测到语义检索库，将使用关键词检索")


# ============================================================
# 相似度计算函数
# ============================================================

def calculate_text_similarity(text1: str, text2: str, method: str = "token_sort") -> int:
    """
    计算两段文本的相似度
    
    Args:
        text1: 文本1
        text2: 文本2
        method: 匹配方法 (token_sort/partial/simple)
        
    Returns:
        相似度分数 (0-100)
    """
    if not text1 or not text2:
        return 0
    
    text1 = text1.lower().strip()
    text2 = text2.lower().strip()
    
    if HAS_FUZZYWUZZY:
        if method == "token_sort":
            # 分词排序后匹配（对词序不敏感）
            return fuzz.token_sort_ratio(text1, text2)
        elif method == "partial":
            # 部分匹配（适合长文本包含短文本的情况）
            return fuzz.partial_ratio(text1, text2)
        elif method == "token_set":
            # 集合匹配（去重后比较）
            return fuzz.token_set_ratio(text1, text2)
        else:
            # 简单匹配
            return fuzz.ratio(text1, text2)
    else:
        # 基础匹配：基于关键词重叠
        words1 = set(text1.split())
        words2 = set(text2.split())
        if not words1 or not words2:
            return 0
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        return int(intersection / union * 100) if union > 0 else 0


def calculate_keyword_similarity(keywords1: List[str], keywords2: List[str]) -> int:
    """
    计算关键词列表的相似度（Jaccard 相似度）
    
    Args:
        keywords1: 关键词列表1
        keywords2: 关键词列表2
        
    Returns:
        相似度分数 (0-100)
    """
    if not keywords1 or not keywords2:
        return 0
    
    set1 = set(k.lower() for k in keywords1)
    set2 = set(k.lower() for k in keywords2)
    
    intersection = len(set1 & set2)
    union = len(set1 | set2)
    
    return int(intersection / union * 100) if union > 0 else 0


def calculate_combined_similarity(
    task1: str,
    task2: str,
    keywords1: List[str],
    keywords2: List[str],
    weights: Tuple[float, float, float] = (0.5, 0.3, 0.2)
) -> int:
    """
    计算综合相似度（结合多种匹配策略）
    
    Args:
        task1: 任务描述1
        task2: 任务描述2
        keywords1: 关键词列表1
        keywords2: 关键词列表2
        weights: (文本相似度, 部分匹配, 关键词相似度) 权重
        
    Returns:
        综合相似度分数 (0-100)
    """
    w1, w2, w3 = weights
    
    # 文本相似度（分词排序）
    text_sim = calculate_text_similarity(task1, task2, "token_sort")
    
    # 部分匹配相似度
    partial_sim = calculate_text_similarity(task1, task2, "partial")
    
    # 关键词相似度
    keyword_sim = calculate_keyword_similarity(keywords1, keywords2)
    
    # 加权综合
    combined = int(w1 * text_sim + w2 * partial_sim + w3 * keyword_sim)
    
    return min(combined, 100)


# ============================================================
# 核心检索函数
# ============================================================

def semantic_retrieve(
    user_task: str,
    threshold: float = 0.6,
    limit: int = 50,
    success_only: bool = True,
    verbose: bool = True
) -> List[Tuple[Dict, float]]:
    """
    语义检索（使用向量相似度）
    
    Args:
        user_task: 用户任务描述
        threshold: 相似度阈值（0-1）
        limit: 最多检索的轨迹数量
        success_only: 是否只检索成功的轨迹
        verbose: 是否打印详细信息
    
    Returns:
        [(轨迹, 相似度), ...] 列表，按相似度降序
    """
    if not HAS_KYLIN_AI and not HAS_SENTENCE_TRANSFORMERS:
        if verbose:
            print("⚠️ 语义检索不可用，回退到关键词检索")
        # 回退到关键词检索
        return [(t, s/100.0) for t, s in retrieve_top_k_trajectories(user_task, k=3, limit=limit, success_only=success_only)]
    
    trajectories = list_trajectories(limit=limit, success_only=success_only)
    if not trajectories:
        return []
    
    # 将用户任务转换为向量
    try:
        if HAS_KYLIN_AI:
            # 使用麒麟AI框架
            import subprocess
            result = subprocess.run(
                ["kylin-llm-embed", "--text", user_task],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                query_vector = json.loads(result.stdout)
            else:
                return []
        else:
            # 使用sentence-transformers
            query_vector = KYLIN_EMBED_MODEL.encode(user_task).tolist()
    except Exception as e:
        if verbose:
            print(f"⚠️ 向量化失败: {e}，回退到关键词检索")
        return [(t, s/100.0) for t, s in retrieve_top_k_trajectories(user_task, k=3, limit=limit, success_only=success_only)]
    
    # 计算与历史轨迹的相似度
    scored_trajectories = []
    for traj in trajectories:
        history_task = traj.get("task", "")
        if not history_task:
            continue
        
        try:
            if HAS_KYLIN_AI:
                result = subprocess.run(
                    ["kylin-llm-embed", "--text", history_task],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    history_vector = json.loads(result.stdout)
                else:
                    continue
            else:
                history_vector = KYLIN_EMBED_MODEL.encode(history_task).tolist()
            
            # 计算余弦相似度
            import numpy as np
            query_np = np.array(query_vector)
            history_np = np.array(history_vector)
            similarity = np.dot(query_np, history_np) / (np.linalg.norm(query_np) * np.linalg.norm(history_np))
            
            if similarity >= threshold:
                scored_trajectories.append((traj, float(similarity)))
        except Exception as e:
            if verbose:
                print(f"⚠️ 计算相似度失败: {e}")
            continue
    
    # 按相似度降序排序
    scored_trajectories.sort(key=lambda x: x[1], reverse=True)
    
    if verbose:
        print(f"语义检索找到 {len(scored_trajectories)} 条相似轨迹（阈值≥{threshold:.0%}）")
    
    return scored_trajectories[:3]  # 返回前3个


def retrieve_similar_trajectory(
    user_task: str,
    threshold: int = 70,
    limit: int = 50,
    success_only: bool = True,
    verbose: bool = True,
    use_semantic: bool = False
) -> Optional[Dict]:
    """
    检索最相似的历史轨迹
    
    Args:
        user_task: 用户当前任务
        threshold: 匹配阈值 (0-100)
        limit: 最多检索的轨迹数量
        success_only: 是否只检索成功的轨迹
        verbose: 是否打印详细信息
        
    Returns:
        最相似的轨迹字典，无匹配返回 None
    """
    start_time = time.time()
    
    if verbose:
        print(f"\n{'='*60}")
        print(f"检索相似轨迹")
        print(f"{'='*60}")
        print(f"当前任务: {user_task}")
        print(f"匹配阈值: {threshold}")
        print(f"检索模式: {'语义检索' if use_semantic else '关键词检索'}")
    
    # 如果启用语义检索且可用
    if use_semantic and (HAS_KYLIN_AI or HAS_SENTENCE_TRANSFORMERS):
        semantic_results = semantic_retrieve(
            user_task=user_task,
            threshold=threshold/100.0,
            limit=limit,
            success_only=success_only,
            verbose=verbose
        )
        if semantic_results:
            best_match, best_score = semantic_results[0]
            if verbose:
                print(f"\n✓ 语义检索找到匹配轨迹（相似度: {best_score:.2%}）")
            return best_match
    
    # 获取历史轨迹（关键词检索）
    trajectories = list_trajectories(limit=limit, success_only=success_only)
    
    if not trajectories:
        if verbose:
            print("⚠️ 无历史协作轨迹")
        return None
    
    if verbose:
        print(f"检索范围: 最近 {len(trajectories)} 条轨迹")
    
    # 提取当前任务的关键词
    current_keywords = extract_keywords(user_task)
    
    # 遍历计算相似度
    best_match = None
    best_score = 0
    match_details = []
    
    for traj in trajectories:
        history_task = traj.get("task", "")
        history_keywords = traj.get("keywords", [])
        
        if not history_task:
            continue
        
        # 计算综合相似度
        score = calculate_combined_similarity(
            user_task, history_task,
            current_keywords, history_keywords
        )
        
        match_details.append({
            "task": history_task[:40] + "..." if len(history_task) > 40 else history_task,
            "score": score
        })
        
        if score > best_score:
            best_score = score
            best_match = traj
    
    elapsed = time.time() - start_time
    
    # 打印匹配详情
    if verbose:
        print(f"\n--- 匹配结果（耗时: {elapsed:.3f}s）---")
        # 按相似度排序，显示前5个
        sorted_matches = sorted(match_details, key=lambda x: x["score"], reverse=True)[:5]
        for m in sorted_matches:
            indicator = "✓" if m["score"] >= threshold else " "
            print(f"  {indicator} [{m['score']:3d}] {m['task']}")
    
    # 检查是否达到阈值
    if best_match and best_score >= threshold:
        if verbose:
            print(f"\n✓ 找到匹配轨迹（相似度: {best_score}）")
        return best_match
    else:
        if verbose:
            print(f"\n⚠️ 未找到相似度 ≥ {threshold} 的轨迹")
        return None


def retrieve_top_k_trajectories(
    user_task: str,
    k: int = 5,
    limit: int = 50,
    success_only: bool = True
) -> List[Tuple[Dict, int]]:
    """
    检索 Top-K 相似轨迹
    
    Args:
        user_task: 用户当前任务
        k: 返回数量
        limit: 最多检索的轨迹数量
        success_only: 是否只检索成功的轨迹
        
    Returns:
        [(轨迹, 相似度), ...] 列表，按相似度降序
    """
    trajectories = list_trajectories(limit=limit, success_only=success_only)
    
    if not trajectories:
        return []
    
    current_keywords = extract_keywords(user_task)
    
    scored_trajectories = []
    for traj in trajectories:
        history_task = traj.get("task", "")
        history_keywords = traj.get("keywords", [])
        
        if not history_task:
            continue
        
        score = calculate_combined_similarity(
            user_task, history_task,
            current_keywords, history_keywords
        )
        scored_trajectories.append((traj, score))
    
    # 按相似度降序排序
    scored_trajectories.sort(key=lambda x: x[1], reverse=True)
    
    return scored_trajectories[:k]


# ============================================================
# 推理链复用函数
# ============================================================

def reuse_reasoning_chain(
    user_task: str,
    threshold: int = 70,
    verbose: bool = True
) -> Optional[Dict]:
    """
    复用相似轨迹的推理链
    
    Args:
        user_task: 用户当前任务
        threshold: 匹配阈值
        verbose: 是否打印详细信息
        
    Returns:
        复用的推理链字典，无匹配返回 None
    """
    similar_traj = retrieve_similar_trajectory(
        user_task=user_task,
        threshold=threshold,
        verbose=verbose
    )
    
    if not similar_traj:
        return None
    
    # 提取历史推理链
    history_reasoning = similar_traj.get("reasoning_chain", {})
    
    if not history_reasoning:
        if verbose:
            print("⚠️ 匹配的轨迹无有效推理链")
        return None
    
    # 添加复用标记
    reused_reasoning = history_reasoning.copy()
    reused_reasoning["_reused"] = True
    reused_reasoning["_reused_from"] = {
        "task": similar_traj.get("task"),
        "task_hash": similar_traj.get("task_hash"),
        "timestamp": similar_traj.get("timestamp"),
        "success": similar_traj.get("success")
    }
    
    if verbose:
        print(f"\n--- 复用的推理链 ---")
        tc = history_reasoning.get("thought_chain", {})
        print(f"任务分解: {tc.get('task_decomposition', 'N/A')[:80]}...")
    
    return reused_reasoning


# ============================================================
# 检索优先的推理流程
# ============================================================

def reasoning_with_retrieval(
    user_task: str,
    threshold: int = 70,
    verbose: bool = True
) -> Tuple[Dict, str]:
    """
    检索优先：先查历史轨迹，无匹配再生成新推理链
    
    Args:
        user_task: 用户任务
        threshold: 匹配阈值
        verbose: 是否打印详细信息
        
    Returns:
        (推理链, 状态) 状态为 "reused" 或 "generated"
    """
    # 1. 尝试检索复用
    reused_reasoning = reuse_reasoning_chain(
        user_task=user_task,
        threshold=threshold,
        verbose=verbose
    )
    
    if reused_reasoning:
        return reused_reasoning, "reused"
    
    # 2. 无匹配，调用 system2_memory 生成新推理链
    if verbose:
        print("\n--- 生成新推理链 ---")
    
    try:
        from system2_memory import reasoning_with_memory
        
        reasoning_chain, _ = reasoning_with_memory(
            user_task=user_task,
            enable_reuse=False,  # 已经检索过了，不需要再检索
            verbose=verbose
        )
        return reasoning_chain, "generated"
    except Exception as e:
        if verbose:
            print(f"⚠️ 生成推理链失败: {e}")
        # 返回基础兜底推理链
        return {
            "thought_chain": {
                "task_decomposition": f"执行: {user_task}",
                "agent_selection": [{"step": 1, "agent": "DefaultAgent", "reason": "默认处理"}],
                "risk_assessment": "未知风险",
                "fallback_plan": "手动干预"
            },
            "execution_plan": [{"step": 1, "action": user_task, "agent": "DefaultAgent"}],
            "milestone_markers": ["start", "execute", "complete"],
            "_is_fallback": True
        }, "fallback"


# ============================================================
# 检索统计
# ============================================================

def get_retrieval_stats() -> Dict:
    """
    获取检索统计信息
    
    Returns:
        统计信息字典
    """
    trajectories = list_trajectories(limit=1000)
    
    stats = {
        "total_trajectories": len(trajectories),
        "success_trajectories": sum(1 for t in trajectories if t.get("success")),
        "agents_distribution": {},
        "keywords_frequency": {},
        "recent_tasks": []
    }
    
    for traj in trajectories:
        # 智能体分布
        for agent in traj.get("agents_involved", []):
            stats["agents_distribution"][agent] = stats["agents_distribution"].get(agent, 0) + 1
        
        # 关键词频率
        for kw in traj.get("keywords", []):
            stats["keywords_frequency"][kw] = stats["keywords_frequency"].get(kw, 0) + 1
    
    # 最近任务
    stats["recent_tasks"] = [
        {"task": t.get("task", "")[:50], "timestamp": t.get("timestamp")}
        for t in trajectories[:5]
    ]
    
    # 关键词按频率排序
    stats["top_keywords"] = sorted(
        stats["keywords_frequency"].items(),
        key=lambda x: x[1],
        reverse=True
    )[:10]
    
    return stats


# ============================================================
# 测试函数
# ============================================================

def test_retrieval():
    """测试记忆检索功能"""
    print("\n" + "🔍 记忆检索模块测试 🔍".center(60))
    print("=" * 60)
    
    # 检查是否有历史轨迹
    trajectories = list_trajectories(limit=10)
    if not trajectories:
        print("⚠️ 无历史轨迹，请先运行 system2_memory.py 生成测试数据")
        return
    
    print(f"✓ 检测到 {len(trajectories)} 条历史轨迹")
    
    # 测试用例
    test_cases = [
        {
            "name": "完全匹配",
            "task": trajectories[0].get("task", "测试任务"),
            "expected": "high"
        },
        {
            "name": "相似任务",
            "task": "搜索下载目录的jpg文件设置为壁纸",
            "expected": "medium"
        },
        {
            "name": "不匹配任务",
            "task": "查看系统内存使用情况并生成报告",
            "expected": "low"
        }
    ]
    
    results = []
    
    for i, case in enumerate(test_cases, 1):
        print(f"\n\n{'#' * 60}")
        print(f"# 测试 {i}: {case['name']}")
        print(f"# 任务: {case['task'][:50]}...")
        print(f"{'#' * 60}")
        
        # 检索
        reasoning, status = reasoning_with_retrieval(
            user_task=case["task"],
            threshold=60,
            verbose=True
        )
        
        results.append({
            "name": case["name"],
            "task": case["task"],
            "status": status,
            "reused": status == "reused"
        })
    
    # 打印测试总结
    print("\n\n" + "=" * 60)
    print("测试结果总结")
    print("=" * 60)
    
    for r in results:
        status_icon = "✓" if r["reused"] else "○"
        print(f"  {status_icon} {r['name']}: {r['status']}")
    
    # 检索统计
    print("\n" + "=" * 60)
    print("检索统计")
    print("=" * 60)
    
    stats = get_retrieval_stats()
    print(f"  总轨迹数: {stats['total_trajectories']}")
    print(f"  成功轨迹: {stats['success_trajectories']}")
    print(f"  智能体分布: {stats['agents_distribution']}")
    print(f"  热门关键词: {stats['top_keywords'][:5]}")
    
    print("\n" + "=" * 60)
    print("✓ 检索测试完成!")
    print("=" * 60)


if __name__ == "__main__":
    test_retrieval()

