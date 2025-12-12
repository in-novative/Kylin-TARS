"""FileAgent MCP接口骨架文件（仅定义接口规范，无业务逻辑）"""
from typing import List, Dict, Optional

class FileAgentSkeleton:
    """FileAgent接口契约定义"""
    
    def search_file(
        self,
        search_path: str,
        keyword: str,
        recursive: bool = True
    ) -> Dict[str, str]:
        """
        文件搜索接口（契约定义）
        :param search_path: 搜索根路径（必填，str）
        :param keyword: 搜索关键词（必填，str）
        :param recursive: 是否递归搜索（可选，bool，默认True）
        :return: 标准化返回字典，包含status/msg/data字段
        """
        pass  # 仅占位，无业务逻辑
    
    def move_to_trash(
        self,
        file_path: str
    ) -> Dict[str, str]:
        """
        文件移至回收站接口（契约定义）
        :param file_path: 文件绝对路径（必填，str）
        :return: 标准化返回字典，包含status/msg字段
        """
        pass  # 仅占位，无业务逻辑