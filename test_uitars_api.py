#!/usr/bin/env python3
"""
UI-TARS-1.5-7B vLLM API 测试脚本
支持纯文本测试和图像+文本测试
"""

import requests
import base64
import json
import re
import math
from pathlib import Path
from PIL import Image
import matplotlib.pyplot as plt

# API配置
API_BASE = "http://localhost:8000"
MODEL_NAME = "/data1/models/UI-TARS-1.5-7B"

# ============================================================
# UI-TARS 官方坐标转换参数和函数
# ============================================================
IMAGE_FACTOR = 28
MIN_PIXELS = 100 * 28 * 28
MAX_PIXELS = 16384 * 28 * 28
MAX_RATIO = 200


def round_by_factor(number: int, factor: int) -> int:
    """Returns the closest integer to 'number' that is divisible by 'factor'."""
    return round(number / factor) * factor


def ceil_by_factor(number: int, factor: int) -> int:
    """Returns the smallest integer >= 'number' that is divisible by 'factor'."""
    return math.ceil(number / factor) * factor


def floor_by_factor(number: int, factor: int) -> int:
    """Returns the largest integer <= 'number' that is divisible by 'factor'."""
    return math.floor(number / factor) * factor


def smart_resize(
    height: int, 
    width: int, 
    factor: int = IMAGE_FACTOR, 
    min_pixels: int = MIN_PIXELS, 
    max_pixels: int = MAX_PIXELS
) -> tuple:
    """
    Rescales the image so that:
    1. Both dimensions are divisible by 'factor'.
    2. Total pixels within ['min_pixels', 'max_pixels'].
    3. Aspect ratio maintained as closely as possible.
    """
    if max(height, width) / min(height, width) > MAX_RATIO:
        raise ValueError(
            f"absolute aspect ratio must be smaller than {MAX_RATIO}, "
            f"got {max(height, width) / min(height, width)}"
        )
    h_bar = max(factor, round_by_factor(height, factor))
    w_bar = max(factor, round_by_factor(width, factor))
    if h_bar * w_bar > max_pixels:
        beta = math.sqrt((height * width) / max_pixels)
        h_bar = floor_by_factor(height / beta, factor)
        w_bar = floor_by_factor(width / beta, factor)
    elif h_bar * w_bar < min_pixels:
        beta = math.sqrt(min_pixels / (height * width))
        h_bar = ceil_by_factor(height * beta, factor)
        w_bar = ceil_by_factor(width * beta, factor)
    return h_bar, w_bar


def parse_coordinate(model_response: str) -> tuple:
    """
    从模型输出中解析坐标
    支持格式: click(start_box='(x,y)') 或 click(start_box="(x,y)")
    返回: (x, y) 或 None
    """
    # 匹配 start_box='(x,y)' 或 start_box="(x,y)" 格式
    pattern = r"start_box=['\"]?\((\d+),\s*(\d+)\)['\"]?"
    match = re.search(pattern, model_response)
    if match:
        x = int(match.group(1))
        y = int(match.group(2))
        return (x, y)
    return None


def convert_coordinate(
    model_coord: tuple, 
    original_width: int, 
    original_height: int
) -> tuple:
    """
    将模型输出的坐标转换为原始图像的实际坐标
    
    Args:
        model_coord: 模型输出的坐标 (x, y)
        original_width: 原始图像宽度
        original_height: 原始图像高度
    
    Returns:
        实际坐标 (x, y)
    """
    model_x, model_y = model_coord
    
    # 计算模型处理时的图像尺寸
    new_height, new_width = smart_resize(original_height, original_width)
    
    # 转换坐标
    actual_x = int(model_x / new_width * original_width)
    actual_y = int(model_y / new_height * original_height)
    
    return (actual_x, actual_y)


def visualize_coordinate(
    image_path: str, 
    coordinate: tuple, 
    output_path: str = None
) -> str:
    """
    在图像上标记坐标点并保存
    
    Args:
        image_path: 原始图像路径
        coordinate: 要标记的坐标 (x, y)
        output_path: 输出图像路径，默认在原图同目录下生成
    
    Returns:
        输出图像路径
    """
    img = Image.open(image_path)
    
    # 生成输出路径
    if output_path is None:
        path = Path(image_path)
        output_path = str(path.parent / f"{path.stem}_marked{path.suffix}")
    
    # 绘制图像和坐标点
    plt.figure(figsize=(12, 8))
    plt.imshow(img)
    plt.scatter([coordinate[0]], [coordinate[1]], c='red', s=20, marker='x', linewidths=3)
    plt.scatter([coordinate[0]], [coordinate[1]], c='red', s=50, facecolors='none', edgecolors='red', linewidths=2)
    plt.title(f'GUI Grounding Result - Coordinate: {coordinate}', fontsize=14)
    plt.axis('off')
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    return output_path


def test_text_only():
    """测试纯文本对话"""
    print("=" * 50)
    print("测试1: 纯文本对话")
    print("=" * 50)
    
    url = f"{API_BASE}/v1/chat/completions"
    
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {
                "role": "user",
                "content": "你好，请介绍一下你自己。"
            }
        ],
        "max_tokens": 512,
        "temperature": 0.7
    }
    
    try:
        response = requests.post(url, json=payload, timeout=60)
        response.raise_for_status()
        result = response.json()
        
        print(f"状态: 成功 ✓")
        print(f"回复: {result['choices'][0]['message']['content']}")
        print(f"Token使用: {result.get('usage', 'N/A')}")
        return True
    except Exception as e:
        print(f"状态: 失败 ✗")
        print(f"错误: {e}")
        return False


def test_image_url():
    """测试图像URL输入"""
    print("\n" + "=" * 50)
    print("测试2: 图像URL + 文本")
    print("=" * 50)
    
    url = f"{API_BASE}/v1/chat/completions"
    
    # 使用一个公开的测试图片URL
    image_url = "https://upload.wikimedia.org/wikipedia/commons/thumb/4/47/PNG_transparency_demonstration_1.png/300px-PNG_transparency_demonstration_1.png"
    
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": image_url
                        }
                    },
                    {
                        "type": "text",
                        "text": "请描述这张图片中的内容。"
                    }
                ]
            }
        ],
        "max_tokens": 512,
        "temperature": 0.7
    }
    
    try:
        response = requests.post(url, json=payload, timeout=120)
        response.raise_for_status()
        result = response.json()
        
        print(f"状态: 成功 ✓")
        print(f"回复: {result['choices'][0]['message']['content']}")
        return True
    except Exception as e:
        print(f"状态: 失败 ✗")
        print(f"错误: {e}")
        return False


def test_image_base64(image_path: str = None):
    """测试Base64图像输入"""
    print("\n" + "=" * 50)
    print("测试3: Base64图像 + 文本")
    print("=" * 50)
    
    # 如果没有提供图片路径，创建一个简单的测试图片
    if image_path is None or not Path(image_path).exists():
        print("提示: 未提供图片路径，跳过此测试")
        print("使用方法: test_image_base64('/path/to/your/image.png')")
        return None
    
    url = f"{API_BASE}/v1/chat/completions"
    
    # 读取并编码图片
    with open(image_path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode("utf-8")
    
    # 根据文件扩展名确定MIME类型
    ext = Path(image_path).suffix.lower()
    mime_types = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif", ".webp": "image/webp"}
    mime_type = mime_types.get(ext, "image/png")
    
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{image_data}"
                        }
                    },
                    {
                        "type": "text",
                        "text": "请详细描述这张图片中的内容，包括你看到的所有元素。"
                    }
                ]
            }
        ],
        "max_tokens": 1024,
        "temperature": 0.7
    }
    
    try:
        response = requests.post(url, json=payload, timeout=120)
        response.raise_for_status()
        result = response.json()
        
        print(f"状态: 成功 ✓")
        print(f"回复: {result['choices'][0]['message']['content']}")
        return True
    except Exception as e:
        print(f"状态: 失败 ✗")
        print(f"错误: {e}")
        return False


def test_gui_grounding(image_path: str = None, instruction: str = None):
    """
    测试GUI定位能力 (UI-TARS的核心能力)
    这是UI-TARS模型的特色功能：给定屏幕截图和指令，返回点击坐标
    
    Args:
        image_path: 截图路径
        instruction: 定位指令，默认为"请找到搜索框的位置"
    
    Returns:
        dict: 包含模型输出、坐标信息、可视化图像路径
    """
    print("\n" + "=" * 50)
    print("测试4: GUI元素定位 (UI-TARS核心能力)")
    print("=" * 50)
    
    if image_path is None or not Path(image_path).exists():
        print("提示: 需要提供GUI截图路径来测试定位能力")
        print("使用方法: test_gui_grounding('/path/to/screenshot.png')")
        return None
    
    # 默认指令
    if instruction is None:
        instruction = "请找到调整文件视图大小按钮的位置"
    
    url = f"{API_BASE}/v1/chat/completions"
    
    # 读取图片信息
    img = Image.open(image_path)
    original_width, original_height = img.size
    print(f"原始图像尺寸: {original_width} x {original_height}")
    
    # 计算模型处理尺寸
    resized_height, resized_width = smart_resize(original_height, original_width)
    print(f"模型处理尺寸: {resized_width} x {resized_height}")
    
    # 读取并编码图片
    with open(image_path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode("utf-8")
    
    ext = Path(image_path).suffix.lower()
    mime_types = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}
    mime_type = mime_types.get(ext, "image/png")
    
    # 构造prompt
    prompt_text = f"{instruction}，并给出点击坐标，请按照这样的格式输出Thought: xxx\nAction: click(start_box='(x,y)')"
    
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{image_data}"
                        }
                    },
                    {
                        "type": "text",
                        "text": prompt_text
                    }
                ]
            }
        ],
        "max_tokens": 1024,
        "temperature": 0.1  # GUI任务用低温度更精确
    }
    
    try:
        response = requests.post(url, json=payload, timeout=120)
        response.raise_for_status()
        result = response.json()
        
        model_response = result['choices'][0]['message']['content']
        print(f"\n状态: 成功 ✓")
        print(f"模型原始输出:\n{model_response}")
        
        # 解析坐标
        model_coord = parse_coordinate(model_response)
        
        if model_coord:
            print(f"\n--- 坐标解析结果 ---")
            print(f"模型输出坐标 (相对于{resized_width}x{resized_height}): {model_coord}")
            
            # 转换为实际坐标
            actual_coord = convert_coordinate(model_coord, original_width, original_height)
            print(f"实际图像坐标 (相对于{original_width}x{original_height}): {actual_coord}")
            
            # 可视化
            output_path = visualize_coordinate(image_path, actual_coord)
            print(f"\n--- 可视化结果 ---")
            print(f"已保存标记图像: {output_path}")
            
            return {
                "success": True,
                "model_response": model_response,
                "model_coordinate": model_coord,
                "actual_coordinate": actual_coord,
                "original_size": (original_width, original_height),
                "resized_size": (resized_width, resized_height),
                "visualization_path": output_path
            }
        else:
            print(f"\n⚠️ 无法从模型输出中解析坐标")
            return {
                "success": False,
                "model_response": model_response,
                "error": "无法解析坐标"
            }
            
    except Exception as e:
        print(f"状态: 失败 ✗")
        print(f"错误: {e}")
        return None


def test_health():
    """检查服务健康状态"""
    print("=" * 50)
    print("检查服务状态")
    print("=" * 50)
    
    try:
        response = requests.get(f"{API_BASE}/health", timeout=10)
        print(f"健康检查: {'正常 ✓' if response.status_code == 200 else '异常 ✗'}")
        
        # 获取模型信息
        models_response = requests.get(f"{API_BASE}/v1/models", timeout=10)
        if models_response.status_code == 200:
            models = models_response.json()
            print(f"已加载模型: {[m['id'] for m in models.get('data', [])]}")
        
        return response.status_code == 200
    except Exception as e:
        print(f"服务不可用: {e}")
        return False


def main():
    """运行所有测试"""
    print("\n" + "🚀 UI-TARS-1.5-7B API 测试开始 🚀".center(50))
    print("\n")
    
    # 检查服务状态
    if not test_health():
        print("\n❌ 服务未就绪，请确保vLLM服务正在运行")
        return
    
    print()
    
    # 运行测试
    results = []
    
    # 测试1: 纯文本
    results.append(("纯文本对话", test_text_only()))
    
    # 测试2: 图像URL
    results.append(("图像URL", test_image_url()))
    
    # 测试3: Base64图像 (可选，需要提供图片)
    # results.append(("Base64图像", test_image_base64("/path/to/image.png")))
    
    # 测试4: GUI定位 (可选，需要提供截图)
    gui_result = test_gui_grounding("/data1/cyx/anything/麒麟OS桌面.png")
    gui_success = gui_result.get("success", False) if isinstance(gui_result, dict) else bool(gui_result)
    results.append(("GUI定位", gui_success if gui_result else None))
    
    # 打印测试结果汇总
    print("\n" + "=" * 50)
    print("测试结果汇总")
    print("=" * 50)
    for name, result in results:
        status = "✓ 通过" if result else ("⏭ 跳过" if result is None else "✗ 失败")
        print(f"  {name}: {status}")
    
    # 如果GUI定位成功，打印详细信息
    if gui_result and gui_result.get("success"):
        print("\n" + "=" * 50)
        print("GUI定位详细结果")
        print("=" * 50)
        print(f"  实际坐标: {gui_result['actual_coordinate']}")
        print(f"  可视化图像: {gui_result['visualization_path']}")
    
    print("\n测试完成！")


if __name__ == "__main__":
    main()

