#!/usr/bin/env python3
"""
System-2 可解释推理模板 - openKylin GUI Agent

本模块实现强制 JSON 格式的 System Prompt，用于：
1. 将用户指令转换为标准化推理链
2. 实现任务分解、智能体选择、风险评估
3. 确保输出格式稳定，便于 Master Agent 解析

依赖：
- vLLM API 服务（需先启动）
- json5（容错JSON解析）

作者：GUI Agent Team
日期：2024-12
"""

import requests
import base64
import json
import re
from pathlib import Path
from typing import Optional, Dict, Any, Union
from datetime import datetime

# 尝试导入json5用于容错解析，如果没有则使用标准json
try:
    import json5
    HAS_JSON5 = True
except ImportError:
    HAS_JSON5 = False
    print("警告: json5未安装，将使用标准json解析。建议安装: pip install json5")

# ============================================================
# API 配置
# ============================================================
API_BASE = "http://localhost:8000"
MODEL_NAME = "/data1/models/UI-TARS-1.5-7B"

# ============================================================
# System-2 核心 Prompt 模板
# ============================================================

# Master Agent 任务分解模板（纯推理，不涉及GUI操作）
SYSTEM2_MASTER_PROMPT = """你是openKylin桌面的中央调度智能体(Master Agent)，必须严格按照以下规则处理用户任务：

## 你的职责
1. **任务分解**：将用户任务拆分为2-4个可执行子步骤（每个步骤对应具体操作）
2. **智能体选择**：根据子步骤类型选择对应子智能体，并说明选择理由
3. **风险评估**：识别最可能的执行风险
4. **回退策略**：针对风险给出回退方案

## 可用的子智能体
- **FileAgent**: 文件操作（搜索、移动、复制、删除文件/目录）
- **SettingsAgent**: 系统设置（壁纸、音量、亮度、网络、蓝牙等）
- **AppAgent**: 应用操作（打开、关闭应用程序）
- **BrowserAgent**: 浏览器操作（打开网页、搜索）
- **TerminalAgent**: 终端命令执行

## 输出格式要求
必须返回JSON格式，字段如下（不可增减字段，不可修改格式）：
```json
{
    "thought_chain": {
        "task_understanding": "对用户任务的理解",
        "task_decomposition": "1. 步骤一；2. 步骤二；3. 步骤三",
        "agent_selection": [
            {"step": 1, "agent": "AgentName", "reason": "选择理由"},
            {"step": 2, "agent": "AgentName", "reason": "选择理由"}
        ],
        "risk_assessment": "核心风险描述",
        "fallback_plan": "风险回退方案"
    },
    "execution_plan": [
        {"step": 1, "action": "具体操作描述", "agent": "AgentName"},
        {"step": 2, "action": "具体操作描述", "agent": "AgentName"}
    ],
    "milestone_markers": ["milestone_1", "milestone_2", "milestone_3"]
}
```

## 示例
用户任务："把下载目录的png文件设置为壁纸"

输出：
```json
{
    "thought_chain": {
        "task_understanding": "用户希望从下载目录找到PNG图片并设置为桌面壁纸",
        "task_decomposition": "1. 搜索~/Downloads目录下的png文件；2. 选择合适的图片；3. 调用系统设置更换壁纸；4. 验证壁纸是否生效",
        "agent_selection": [
            {"step": 1, "agent": "FileAgent", "reason": "需要文件搜索功能"},
            {"step": 2, "agent": "FileAgent", "reason": "需要文件选择功能"},
            {"step": 3, "agent": "SettingsAgent", "reason": "需要系统设置功能"},
            {"step": 4, "agent": "SettingsAgent", "reason": "需要验证系统状态"}
        ],
        "risk_assessment": "~/Downloads目录可能没有png文件",
        "fallback_plan": "如果没有png文件，提示用户上传图片或搜索其他格式"
    },
    "execution_plan": [
        {"step": 1, "action": "在~/Downloads目录搜索*.png文件", "agent": "FileAgent"},
        {"step": 2, "action": "获取搜索结果的第一个png文件路径", "agent": "FileAgent"},
        {"step": 3, "action": "打开系统设置-外观-壁纸，设置选中的图片", "agent": "SettingsAgent"},
        {"step": 4, "action": "检查桌面壁纸是否已更新", "agent": "SettingsAgent"}
    ],
    "milestone_markers": ["search_complete", "file_selected", "wallpaper_set", "verification_done"]
}
```

请严格按照上述格式输出JSON，不要输出其他内容。
"""

# GUI操作执行模板（带图像输入）
SYSTEM2_GUI_PROMPT = """你是一个GUI操作智能体，负责在openKylin桌面上执行具体的GUI操作。

## 输出格式
```
Thought: <分析当前界面状态和下一步操作>
Action: <具体操作指令>
```

## Action Space（可用操作）
- click(start_box='(x,y)')  # 点击指定坐标
- left_double(start_box='(x,y)')  # 双击
- right_single(start_box='(x,y)')  # 右键单击
- drag(start_box='(x1,y1)', end_box='(x2,y2)')  # 拖拽
- hotkey(key='ctrl c')  # 快捷键，用空格分隔，最多3个键
- type(content='xxx')  # 输入文本，用\\n表示回车提交
- scroll(start_box='(x,y)', direction='down')  # 滚动，方向: up/down/left/right
- wait()  # 等待5秒
- finished(content='任务完成描述')  # 任务完成

## 注意事项
- Thought部分用中文描述
- 先分析界面，再决定操作
- 坐标格式必须是 (x,y)
- 一次只执行一个操作

## 当前任务
{instruction}
"""

# 组合推理模板（任务分解 + GUI操作）
# 注意：JSON中的大括号需要双写 {{ }} 来转义，避免与 .format() 冲突
SYSTEM2_COMBINED_PROMPT = """你是openKylin桌面的GUI智能体，需要完成以下任务。

## 输出格式
必须返回JSON格式：
```json
{{
    "thought_chain": {{
        "current_state": "当前界面状态描述",
        "task_analysis": "任务分析",
        "next_step": "下一步操作计划",
        "reasoning": "操作理由"
    }},
    "action": {{
        "type": "操作类型(click/type/hotkey/scroll/drag/wait/finished)",
        "params": {{
            "坐标或其他参数"
        }}
    }},
    "confidence": 0.95,
    "milestone": "当前里程碑标识"
}}
```

## Action Types
- click: {{"start_box": "(x,y)"}}
- left_double: {{"start_box": "(x,y)"}}
- right_single: {{"start_box": "(x,y)"}}
- drag: {{"start_box": "(x1,y1)", "end_box": "(x2,y2)"}}
- hotkey: {{"key": "ctrl c"}}
- type: {{"content": "输入内容"}}
- scroll: {{"start_box": "(x,y)", "direction": "down"}}
- wait: {{}}
- finished: {{"content": "完成描述"}}

## 当前任务
{instruction}

请分析当前界面并给出下一步操作。
"""


# ============================================================
# 辅助函数
# ============================================================

def parse_json_response(response_text: str) -> Optional[Dict]:
    """
    从模型响应中解析JSON
    
    Args:
        response_text: 模型原始输出
        
    Returns:
        解析后的字典，失败返回None
    """
    # 尝试提取JSON块
    json_patterns = [
        r'```json\s*([\s\S]*?)\s*```',  # ```json ... ```
        r'```\s*([\s\S]*?)\s*```',       # ``` ... ```
        r'\{[\s\S]*\}',                   # 直接的JSON对象
    ]
    
    json_str = None
    for pattern in json_patterns:
        match = re.search(pattern, response_text)
        if match:
            json_str = match.group(1) if '```' in pattern else match.group(0)
            break
    
    if not json_str:
        json_str = response_text.strip()
    
    # 清理JSON字符串
    json_str = json_str.strip()
    if json_str.startswith('```'):
        json_str = re.sub(r'^```\w*\n?', '', json_str)
        json_str = re.sub(r'\n?```$', '', json_str)
    
    # 尝试解析
    try:
        if HAS_JSON5:
            return json5.loads(json_str)
        else:
            return json.loads(json_str)
    except Exception as e:
        # 尝试修复常见问题
        try:
            # 移除末尾多余的逗号
            json_str = re.sub(r',\s*}', '}', json_str)
            json_str = re.sub(r',\s*]', ']', json_str)
            if HAS_JSON5:
                return json5.loads(json_str)
            else:
                return json.loads(json_str)
        except:
            return None


def validate_reasoning_chain(chain: Dict) -> tuple:
    """
    验证推理链格式是否正确
    
    Args:
        chain: 解析后的推理链字典
        
    Returns:
        (is_valid, error_message)
    """
    required_fields = ["thought_chain"]
    thought_chain_fields = ["task_decomposition"]
    
    # 检查顶层字段
    for field in required_fields:
        if field not in chain:
            return False, f"缺失顶层字段: {field}"
    
    # 检查thought_chain字段
    if "thought_chain" in chain:
        for field in thought_chain_fields:
            if field not in chain["thought_chain"]:
                return False, f"thought_chain缺失字段: {field}"
    
    return True, "格式正确"


def create_fallback_chain(user_task: str) -> Dict:
    """
    创建兜底推理链（当模型输出格式错误时使用）
    
    Args:
        user_task: 用户任务描述
        
    Returns:
        兜底推理链字典
    """
    return {
        "thought_chain": {
            "task_understanding": f"执行用户任务: {user_task}",
            "task_decomposition": f"1. 分析任务需求；2. 执行{user_task}核心操作；3. 验证执行结果",
            "agent_selection": [
                {"step": 1, "agent": "DefaultAgent", "reason": "默认处理"},
                {"step": 2, "agent": "DefaultAgent", "reason": "执行核心操作"},
                {"step": 3, "agent": "DefaultAgent", "reason": "验证结果"}
            ],
            "risk_assessment": "可能存在操作失败风险",
            "fallback_plan": "重试1次后提示用户手动操作"
        },
        "execution_plan": [
            {"step": 1, "action": "分析任务", "agent": "DefaultAgent"},
            {"step": 2, "action": user_task, "agent": "DefaultAgent"},
            {"step": 3, "action": "验证结果", "agent": "DefaultAgent"}
        ],
        "milestone_markers": ["analyze", "execute", "verify"],
        "_is_fallback": True
    }


# ============================================================
# 核心API调用函数
# ============================================================

def call_vllm_api(
    messages: list,
    max_tokens: int = 1024,
    temperature: float = 0.05,
    timeout: int = 120
) -> Optional[str]:
    """
    调用vLLM API
    
    Args:
        messages: 消息列表
        max_tokens: 最大生成token数
        temperature: 温度参数
        timeout: 超时时间
        
    Returns:
        模型响应文本，失败返回None
    """
    url = f"{API_BASE}/v1/chat/completions"
    
    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    
    try:
        response = requests.post(url, json=payload, timeout=timeout)
        response.raise_for_status()
        result = response.json()
        return result['choices'][0]['message']['content']
    except Exception as e:
        print(f"API调用失败: {e}")
        return None


def encode_image(image_path: str) -> Optional[str]:
    """
    将图片编码为base64
    
    Args:
        image_path: 图片路径
        
    Returns:
        base64编码字符串
    """
    try:
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    except Exception as e:
        print(f"图片编码失败: {e}")
        return None


# ============================================================
# 推理链生成函数
# ============================================================

def generate_master_reasoning(
    user_task: str,
    max_retries: int = 3,
    verbose: bool = True
) -> Dict:
    """
    生成Master Agent推理链（任务分解、智能体选择）
    
    Args:
        user_task: 用户任务描述
        max_retries: 最大重试次数
        verbose: 是否打印详细信息
        
    Returns:
        推理链字典
    """
    if verbose:
        print(f"\n{'='*60}")
        print(f"生成Master推理链")
        print(f"用户任务: {user_task}")
        print(f"{'='*60}")
    
    messages = [
        {"role": "system", "content": SYSTEM2_MASTER_PROMPT},
        {"role": "user", "content": f"用户任务：{user_task}\n\n请严格按照JSON格式输出推理链："}
    ]
    
    for retry in range(max_retries):
        if verbose:
            print(f"\n第 {retry + 1} 次尝试...")
        
        # 调用API
        raw_output = call_vllm_api(
            messages=messages,
            max_tokens=1024,
            temperature=0.05
        )
        
        if raw_output is None:
            print(f"API调用失败，重试中...")
            continue
        
        if verbose:
            print(f"模型原始输出:\n{raw_output[:500]}...")
        
        # 解析JSON
        reasoning_chain = parse_json_response(raw_output)
        
        if reasoning_chain is None:
            print(f"JSON解析失败，重试中...")
            continue
        
        # 验证格式
        is_valid, error_msg = validate_reasoning_chain(reasoning_chain)
        
        if is_valid:
            if verbose:
                print(f"\n✓ 推理链生成成功!")
            reasoning_chain["_raw_output"] = raw_output
            reasoning_chain["_retry_count"] = retry + 1
            return reasoning_chain
        else:
            print(f"格式验证失败: {error_msg}，重试中...")
    
    # 所有重试失败，返回兜底推理链
    print(f"\n⚠️ 所有重试失败，使用兜底推理链")
    return create_fallback_chain(user_task)


def generate_gui_action(
    instruction: str,
    screenshot_path: Optional[str] = None,
    action_history: Optional[list] = None,
    max_retries: int = 3,
    verbose: bool = True
) -> Dict:
    """
    生成GUI操作（结合截图分析）
    
    Args:
        instruction: 操作指令
        screenshot_path: 截图路径（可选）
        action_history: 历史操作记录（可选）
        max_retries: 最大重试次数
        verbose: 是否打印详细信息
        
    Returns:
        操作指令字典
    """
    if verbose:
        print(f"\n{'='*60}")
        print(f"生成GUI操作")
        print(f"指令: {instruction}")
        if screenshot_path:
            print(f"截图: {screenshot_path}")
        print(f"{'='*60}")
    
    # 构建prompt
    prompt = SYSTEM2_COMBINED_PROMPT.format(instruction=instruction)
    
    # 添加历史操作
    if action_history:
        history_text = "\n## 历史操作\n"
        for i, action in enumerate(action_history[-5:], 1):  # 只保留最近5个
            history_text += f"{i}. {action}\n"
        prompt += history_text
    
    # 构建消息
    if screenshot_path and Path(screenshot_path).exists():
        image_data = encode_image(screenshot_path)
        if image_data:
            ext = Path(screenshot_path).suffix.lower()
            mime_type = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}.get(ext, "image/png")
            
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{mime_type};base64,{image_data}"}
                        },
                        {"type": "text", "text": prompt}
                    ]
                }
            ]
        else:
            messages = [{"role": "user", "content": prompt}]
    else:
        messages = [{"role": "user", "content": prompt}]
    
    for retry in range(max_retries):
        if verbose:
            print(f"\n第 {retry + 1} 次尝试...")
        
        raw_output = call_vllm_api(
            messages=messages,
            max_tokens=512,
            temperature=0.1
        )
        
        if raw_output is None:
            continue
        
        if verbose:
            print(f"模型原始输出:\n{raw_output}")
        
        # 解析JSON
        action_result = parse_json_response(raw_output)
        
        if action_result and "action" in action_result:
            if verbose:
                print(f"\n✓ GUI操作生成成功!")
            action_result["_raw_output"] = raw_output
            return action_result
        
        # 尝试解析Thought/Action格式
        thought_match = re.search(r'Thought:\s*(.+?)(?=Action:|$)', raw_output, re.DOTALL)
        action_match = re.search(r'Action:\s*(.+?)(?=Thought:|$)', raw_output, re.DOTALL)
        
        if action_match:
            action_text = action_match.group(1).strip()
            thought_text = thought_match.group(1).strip() if thought_match else ""
            
            # 解析action
            action_result = {
                "thought_chain": {
                    "current_state": thought_text,
                    "reasoning": thought_text
                },
                "action": parse_action_text(action_text),
                "_raw_output": raw_output
            }
            
            if action_result["action"]:
                if verbose:
                    print(f"\n✓ GUI操作生成成功 (Thought/Action格式)!")
                return action_result
    
    # 返回等待操作
    return {
        "thought_chain": {
            "current_state": "无法识别当前状态",
            "reasoning": "生成失败，执行等待"
        },
        "action": {"type": "wait", "params": {}},
        "_is_fallback": True
    }


def parse_action_text(action_text: str) -> Optional[Dict]:
    """
    解析Action文本为结构化字典
    
    Args:
        action_text: 如 "click(start_box='(100,200)')"
        
    Returns:
        {"type": "click", "params": {"start_box": "(100,200)"}}
    """
    # 匹配函数调用格式
    match = re.match(r'(\w+)\((.*)\)', action_text.strip())
    if not match:
        return None
    
    action_type = match.group(1)
    params_str = match.group(2)
    
    # 解析参数
    params = {}
    param_patterns = [
        r"(\w+)='([^']*)'",  # key='value'
        r'(\w+)="([^"]*)"',  # key="value"
        r"(\w+)=(\([^)]+\))",  # key=(x,y)
    ]
    
    for pattern in param_patterns:
        for m in re.finditer(pattern, params_str):
            params[m.group(1)] = m.group(2)
    
    return {"type": action_type, "params": params}


# ============================================================
# 完整推理流程
# ============================================================

def execute_reasoning_pipeline(
    user_task: str,
    screenshot_path: Optional[str] = None,
    verbose: bool = True
) -> Dict:
    """
    执行完整的推理流程
    
    Args:
        user_task: 用户任务
        screenshot_path: 当前截图路径
        verbose: 是否打印详细信息
        
    Returns:
        包含推理链和操作的完整结果
    """
    result = {
        "user_task": user_task,
        "timestamp": datetime.now().isoformat(),
        "screenshot": screenshot_path,
        "master_reasoning": None,
        "gui_action": None,
        "success": False
    }
    
    # Step 1: 生成Master推理链
    print("\n" + "="*70)
    print("Step 1: 生成Master推理链（任务分解）")
    print("="*70)
    
    master_reasoning = generate_master_reasoning(user_task, verbose=verbose)
    result["master_reasoning"] = master_reasoning
    
    if master_reasoning.get("_is_fallback"):
        print("⚠️ 使用了兜底推理链")
    else:
        print("✓ Master推理链生成成功")
    
    # Step 2: 如果有截图，生成GUI操作
    if screenshot_path and Path(screenshot_path).exists():
        print("\n" + "="*70)
        print("Step 2: 生成GUI操作（基于截图）")
        print("="*70)
        
        # 从推理链获取第一步操作
        first_step = ""
        if "execution_plan" in master_reasoning and master_reasoning["execution_plan"]:
            first_step = master_reasoning["execution_plan"][0].get("action", "")
        
        instruction = f"{user_task}\n当前步骤: {first_step}" if first_step else user_task
        
        gui_action = generate_gui_action(
            instruction=instruction,
            screenshot_path=screenshot_path,
            verbose=verbose
        )
        result["gui_action"] = gui_action
        
        if gui_action.get("_is_fallback"):
            print("⚠️ 使用了兜底操作")
        else:
            print("✓ GUI操作生成成功")
    
    result["success"] = not (
        master_reasoning.get("_is_fallback") or 
        (result["gui_action"] and result["gui_action"].get("_is_fallback"))
    )
    
    return result


# ============================================================
# 保存推理链示例
# ============================================================

def save_reasoning_examples(results: list, output_path: str = None):
    """
    保存推理链示例到文件
    
    Args:
        results: 推理结果列表
        output_path: 输出文件路径
    """
    if output_path is None:
        output_path = Path(__file__).parent / "reasoning_examples.json"
    
    # 清理不需要保存的字段
    clean_results = []
    for r in results:
        clean_r = {
            "user_task": r["user_task"],
            "timestamp": r["timestamp"],
            "success": r["success"]
        }
        
        if r["master_reasoning"]:
            mr = r["master_reasoning"].copy()
            mr.pop("_raw_output", None)
            clean_r["master_reasoning"] = mr
        
        if r["gui_action"]:
            ga = r["gui_action"].copy()
            ga.pop("_raw_output", None)
            clean_r["gui_action"] = ga
        
        clean_results.append(clean_r)
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(clean_results, f, indent=2, ensure_ascii=False)
    
    print(f"\n推理链示例已保存到: {output_path}")


# ============================================================
# 测试函数
# ============================================================

def test_api_health():
    """检查API服务状态"""
    print("="*60)
    print("检查vLLM API服务状态")
    print("="*60)
    
    try:
        response = requests.get(f"{API_BASE}/health", timeout=10)
        if response.status_code == 200:
            print("✓ API服务正常")
            return True
        else:
            print(f"✗ API服务异常: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ 无法连接API服务: {e}")
        return False


def main():
    """主测试函数"""
    print("\n" + "🚀 System-2 可解释推理模板测试 🚀".center(60))
    print("="*60)
    
    # 检查API状态
    if not test_api_health():
        print("\n❌ API服务未就绪，请先启动vLLM服务")
        print("启动命令示例:")
        print("  python -m vllm.entrypoints.openai.api_server \\")
        print("    --model /data1/models/UI-TARS-1.5-7B \\")
        print("    --trust-remote-code --dtype bfloat16 \\")
        print("    --max-model-len 8192 --port 8000")
        return
    
    # 测试任务列表
    test_tasks = [
        "搜索~/Downloads目录的png文件并设置为壁纸",
        "将下载目录的tmp文件移动到回收站",
        "把系统音量调到50%",
        "打开Firefox浏览器并搜索天气预报",
        "设置默认浏览器为Firefox"
    ]
    
    # 测试截图路径（如果存在）
    test_screenshot = "/data1/cyx/anything/麒麟OS桌面.png"
    
    # 收集测试结果
    all_results = []
    success_count = 0
    
    print("\n" + "="*60)
    print(f"开始测试 {len(test_tasks)} 个任务")
    print("="*60)
    
    for i, task in enumerate(test_tasks, 1):
        print(f"\n\n{'#'*70}")
        print(f"# 测试任务 {i}/{len(test_tasks)}: {task}")
        print(f"{'#'*70}")
        
        # 只对第一个任务使用截图
        screenshot = test_screenshot if i == 1 and Path(test_screenshot).exists() else None
        
        result = execute_reasoning_pipeline(
            user_task=task,
            screenshot_path=screenshot,
            verbose=True
        )
        
        all_results.append(result)
        
        if result["success"]:
            success_count += 1
        
        # 打印推理链摘要
        if result["master_reasoning"]:
            print("\n--- 推理链摘要 ---")
            tc = result["master_reasoning"].get("thought_chain", {})
            print(f"任务分解: {tc.get('task_decomposition', 'N/A')[:100]}...")
            print(f"风险评估: {tc.get('risk_assessment', 'N/A')}")
    
    # 打印测试总结
    print("\n\n" + "="*70)
    print("测试结果总结")
    print("="*70)
    print(f"总任务数: {len(test_tasks)}")
    print(f"成功数量: {success_count}")
    print(f"成功率: {success_count/len(test_tasks)*100:.1f}%")
    
    for i, result in enumerate(all_results, 1):
        status = "✓" if result["success"] else "✗"
        fallback = " (fallback)" if result["master_reasoning"].get("_is_fallback") else ""
        print(f"  {i}. {result['user_task'][:40]}... {status}{fallback}")
    
    # 保存成功的推理链示例
    successful_results = [r for r in all_results if r["success"]]
    if successful_results:
        save_reasoning_examples(successful_results[:3])
    
    print("\n测试完成！")


if __name__ == "__main__":
    main()

