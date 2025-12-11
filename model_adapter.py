#!/usr/bin/env python3
"""
模型适配层 - 支持Qwen2.5系列模型

功能：
1. 统一模型加载接口（支持Qwen2.5-0.5B/1.5B/3B/7B/14B）
2. 自动检测可用模型并切换
3. 支持vLLM加速（可选）
4. 模型健康检查

作者：GUI Agent Team
"""

import os
import json
import requests
import time
from typing import Optional, Dict, List, Tuple
from enum import Enum


class ModelType(Enum):
    """模型类型"""
    QWEN2_5_0_5B = "Qwen2.5-0.5B"
    QWEN2_5_1_5B = "Qwen2.5-1.5B"
    QWEN2_5_3B = "Qwen2.5-3B"
    QWEN2_5_7B = "Qwen2.5-7B"
    QWEN2_5_14B = "Qwen2.5-14B"
    UI_TARS_7B = "UI-TARS-1.5-7B"  # 默认模型


class ModelAdapter:
    """模型适配器"""
    
    def __init__(self, api_base: str = None):
        """
        初始化模型适配器
        
        Args:
            api_base: vLLM API服务地址，如果为None则从环境变量VLLM_API_BASE读取，默认http://localhost:8000
        """
        if api_base is None:
            api_base = os.getenv("VLLM_API_BASE", "http://localhost:8000")
        self.api_base = api_base
        self.current_model: Optional[str] = None
        self.model_config: Dict[str, Dict] = {}
        self.available_models: List[str] = []
        self.model_health: Dict[str, bool] = {}
        
        # 加载模型配置
        self._load_model_config()
        
        # 检测可用模型
        self._detect_available_models()
    
    def _load_model_config(self):
        """加载模型配置"""
        # 默认模型配置（优先级从高到低）
        self.model_config = {
            "UI-TARS-1.5-7B": {
                "path": "/data1/models/UI-TARS-1.5-7B",
                "type": ModelType.UI_TARS_7B,
                "priority": 1,
                "max_tokens": 2048,
                "temperature": 0.7
            },
            "Qwen2.5-14B": {
                "path": "/data1/models/Qwen2.5-14B",
                "type": ModelType.QWEN2_5_14B,
                "priority": 2,
                "max_tokens": 2048,
                "temperature": 0.7
            },
            "Qwen2.5-7B": {
                "path": "/data1/models/Qwen2.5-7B",
                "type": ModelType.QWEN2_5_7B,
                "priority": 3,
                "max_tokens": 2048,
                "temperature": 0.7
            },
            "Qwen2.5-3B": {
                "path": "/data1/models/Qwen2.5-3B",
                "type": ModelType.QWEN2_5_3B,
                "priority": 4,
                "max_tokens": 2048,
                "temperature": 0.7
            },
            "Qwen2.5-1.5B": {
                "path": "/data1/models/Qwen2.5-1.5B",
                "type": ModelType.QWEN2_5_1_5B,
                "priority": 5,
                "max_tokens": 2048,
                "temperature": 0.7
            },
            "Qwen2.5-0.5B": {
                "path": "/data1/models/Qwen2.5-0.5B",
                "type": ModelType.QWEN2_5_0_5B,
                "priority": 6,
                "max_tokens": 2048,
                "temperature": 0.7
            }
        }
        
        # 尝试从配置文件加载
        config_file = os.path.expanduser("~/.config/kylin-gui-agent/model_config.json")
        if os.path.exists(config_file):
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    custom_config = json.load(f)
                    # 合并自定义配置
                    for model_name, config in custom_config.items():
                        if model_name in self.model_config:
                            self.model_config[model_name].update(config)
            except:
                pass
    
    def _detect_available_models(self):
        """检测可用模型（检查模型路径是否存在）"""
        self.available_models = []
        
        for model_name, config in self.model_config.items():
            model_path = config.get("path", "")
            if model_path and os.path.exists(model_path):
                self.available_models.append(model_name)
                self.model_health[model_name] = True
            else:
                self.model_health[model_name] = False
        
        # 按优先级排序
        self.available_models.sort(
            key=lambda x: self.model_config.get(x, {}).get("priority", 999)
        )
    
    def _check_model_health(self, model_name: str) -> bool:
        """
        检查模型健康状态（通过API ping）
        
        Args:
            model_name: 模型名称
        
        Returns:
            是否健康
        """
        try:
            # 尝试调用API健康检查
            response = requests.get(
                f"{self.api_base}/health",
                timeout=2
            )
            if response.status_code == 200:
                # 检查模型是否已加载
                models_response = requests.get(
                    f"{self.api_base}/v1/models",
                    timeout=2
                )
                if models_response.status_code == 200:
                    models_data = models_response.json()
                    loaded_models = [m.get("id", "") for m in models_data.get("data", [])]
                    model_path = self.model_config.get(model_name, {}).get("path", "")
                    # 检查模型路径是否匹配
                    for loaded_model in loaded_models:
                        if model_path in loaded_model or model_name in loaded_model:
                            return True
        except:
            pass
        
        return False
    
    def auto_switch_model(self) -> Optional[str]:
        """
        自动切换模型（选择第一个可用的健康模型）
        
        Returns:
            选中的模型名称，无可用模型返回None
        """
        # 检查当前模型是否健康
        if self.current_model and self._check_model_health(self.current_model):
            return self.current_model
        
        # 遍历可用模型，选择第一个健康的
        for model_name in self.available_models:
            if self._check_model_health(model_name):
                self.current_model = model_name
                print(f"✓ 自动切换到模型: {model_name}")
                return model_name
        
        # 如果都不可用，选择第一个可用模型（即使API不可用）
        if self.available_models:
            self.current_model = self.available_models[0]
            print(f"⚠️ 使用模型（API未检查）: {self.current_model}")
            return self.current_model
        
        return None
    
    def switch_model(self, model_name: str) -> bool:
        """
        手动切换模型
        
        Args:
            model_name: 模型名称
        
        Returns:
            是否切换成功
        """
        if model_name not in self.available_models:
            print(f"✗ 模型不可用: {model_name}")
            return False
        
        # 检查健康状态
        if not self._check_model_health(model_name):
            print(f"⚠️ 模型健康检查失败: {model_name}，但仍将使用")
        
        self.current_model = model_name
        print(f"✓ 切换到模型: {model_name}")
        return True
    
    def get_current_model(self) -> Optional[str]:
        """获取当前模型"""
        return self.current_model
    
    def get_model_config(self, model_name: Optional[str] = None) -> Dict:
        """
        获取模型配置
        
        Args:
            model_name: 模型名称，None则返回当前模型配置
        
        Returns:
            模型配置字典
        """
        model_name = model_name or self.current_model
        if not model_name:
            return {}
        
        return self.model_config.get(model_name, {})
    
    def generate(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        model_name: Optional[str] = None
    ) -> Optional[str]:
        """
        生成文本（调用vLLM API）
        
        Args:
            prompt: 输入提示
            max_tokens: 最大生成token数
            temperature: 温度参数
            model_name: 指定模型名称（可选）
        
        Returns:
            生成的文本，失败返回None
        """
        # 选择模型
        target_model = model_name or self.current_model
        if not target_model:
            target_model = self.auto_switch_model()
            if not target_model:
                print("✗ 无可用模型")
                return None
        
        # 获取模型配置
        config = self.get_model_config(target_model)
        max_tokens = max_tokens or config.get("max_tokens", 2048)
        temperature = temperature if temperature is not None else config.get("temperature", 0.7)
        
        # 调用API
        try:
            response = requests.post(
                f"{self.api_base}/v1/completions",
                json={
                    "model": target_model,
                    "prompt": prompt,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "stop": ["\n\n"]
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                choices = result.get("choices", [])
                if choices:
                    return choices[0].get("text", "")
            else:
                print(f"✗ API调用失败: {response.status_code}")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"✗ API请求失败: {e}")
            # 尝试切换到其他模型
            if not model_name:  # 只有自动选择时才切换
                for alt_model in self.available_models:
                    if alt_model != target_model:
                        print(f"尝试切换到: {alt_model}")
                        if self.switch_model(alt_model):
                            return self.generate(prompt, max_tokens, temperature, alt_model)
            return None
    
    def list_available_models(self) -> List[Dict]:
        """
        列出所有可用模型
        
        Returns:
            模型信息列表
        """
        models = []
        for model_name in self.available_models:
            config = self.get_model_config(model_name)
            models.append({
                "name": model_name,
                "path": config.get("path", ""),
                "type": config.get("type", "").value if isinstance(config.get("type"), ModelType) else "",
                "priority": config.get("priority", 999),
                "is_current": model_name == self.current_model,
                "is_healthy": self._check_model_health(model_name) if model_name in self.available_models else False
            })
        
        return models


# ============================================================
# 全局实例
# ============================================================

_model_adapter: Optional[ModelAdapter] = None


def get_model_adapter(api_base: str = None) -> ModelAdapter:
    """
    获取模型适配器实例（单例）
    
    Args:
        api_base: API服务地址，如果为None则从环境变量VLLM_API_BASE读取，默认http://localhost:8000
    
    Returns:
        ModelAdapter实例
    """
    global _model_adapter
    if _model_adapter is None:
        if api_base is None:
            api_base = os.getenv("VLLM_API_BASE", "http://localhost:8000")
        _model_adapter = ModelAdapter(api_base=api_base)
        # 自动切换模型
        _model_adapter.auto_switch_model()
    return _model_adapter


# ============================================================
# 测试
# ============================================================

if __name__ == "__main__":
    print("=== 测试模型适配层 ===\n")
    
    adapter = get_model_adapter()
    
    print("可用模型:")
    models = adapter.list_available_models()
    for model in models:
        status = "✓" if model["is_healthy"] else "✗"
        current = " [当前]" if model["is_current"] else ""
        print(f"  {status} {model['name']}{current}")
        print(f"    路径: {model['path']}")
        print(f"    优先级: {model['priority']}")
    
    print(f"\n当前模型: {adapter.get_current_model()}")
    
    # 测试生成
    print("\n--- 测试生成 ---")
    test_prompt = "你好，请介绍一下你自己。"
    result = adapter.generate(test_prompt, max_tokens=100)
    if result:
        print(f"生成结果: {result[:100]}...")
    else:
        print("生成失败")

