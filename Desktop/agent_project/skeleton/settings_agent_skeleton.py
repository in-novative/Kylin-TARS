"""SettingsAgent MCP接口骨架文件（仅定义接口规范，无业务逻辑）"""
from typing import Dict, Optional

class SettingsAgentSkeleton:
    """SettingsAgent接口契约定义"""
    
    def change_wallpaper(
        self,
        wallpaper_path: str,
        scale: str = "fill"
    ) -> Dict[str, str]:
        """
        修改桌面壁纸接口（契约定义）
        :param wallpaper_path: 壁纸文件绝对路径（必填，str）
        :param scale: 缩放方式（可选，str，默认fill，支持fill/stretch/center/tile/zoom）
        :return: 标准化返回字典，包含status/msg字段
        """
        pass  # 仅占位，无业务逻辑
    
    def adjust_volume(
        self,
        volume: int,
        device: str = "default"
    ) -> Dict[str, str]:
        """
        调整系统音量接口（契约定义）
        :param volume: 音量值（必填，int，0-100）
        :param device: 音频设备（可选，str，默认default）
        :return: 标准化返回字典，包含status/msg字段
        """
        pass  # 仅占位，无业务逻辑