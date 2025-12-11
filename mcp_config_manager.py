#!/usr/bin/env python3
"""
MCP配置管理模块

功能：
1. MCP配置加载/保存
2. 角色权限分级
3. 配置自动备份/恢复

作者：GUI Agent Team
"""

import json
import os
import shutil
from datetime import datetime
from typing import Dict, List, Optional
from enum import Enum


class PermissionLevel(Enum):
    """权限级别"""
    ADMIN = "admin"  # 管理员：所有权限
    NORMAL = "normal"  # 普通用户：正常操作
    READONLY = "readonly"  # 只读：仅查询
    GUEST = "guest"  # 访客：受限操作


# 配置目录
CONFIG_DIR = os.path.expanduser("~/.config/kylin-gui-agent/mcp_config")
BACKUP_DIR = os.path.expanduser("~/.config/kylin-gui-agent/mcp_config/backups")
os.makedirs(CONFIG_DIR, exist_ok=True)
os.makedirs(BACKUP_DIR, exist_ok=True)

CONFIG_FILE = os.path.join(CONFIG_DIR, "mcp_config.json")


class MCPConfigManager:
    """MCP配置管理器"""
    
    def __init__(self):
        """初始化配置管理器"""
        self.config: Dict = self._load_config()
        self._ensure_default_config()
    
    def _ensure_default_config(self):
        """确保默认配置存在"""
        if "agents" not in self.config:
            self.config["agents"] = {}
        if "permissions" not in self.config:
            self.config["permissions"] = {}
        if "settings" not in self.config:
            self.config["settings"] = {
                "auto_backup": True,
                "backup_interval_hours": 24,
                "max_backups": 10
            }
    
    def _load_config(self) -> Dict:
        """加载配置"""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                pass
        return {}
    
    def save_config(self):
        """保存配置"""
        # 自动备份
        if self.config.get("settings", {}).get("auto_backup", True):
            self.backup_config()
        
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)
    
    def backup_config(self) -> str:
        """备份配置"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = os.path.join(BACKUP_DIR, f"mcp_config_{timestamp}.json")
        
        shutil.copy2(CONFIG_FILE if os.path.exists(CONFIG_FILE) else "", backup_file)
        
        # 清理旧备份
        self._cleanup_old_backups()
        
        return backup_file
    
    def _cleanup_old_backups(self):
        """清理旧备份"""
        max_backups = self.config.get("settings", {}).get("max_backups", 10)
        backups = sorted([f for f in os.listdir(BACKUP_DIR) if f.endswith(".json")])
        
        if len(backups) > max_backups:
            for old_backup in backups[:-max_backups]:
                os.remove(os.path.join(BACKUP_DIR, old_backup))
    
    def restore_config(self, backup_file: str) -> bool:
        """恢复配置"""
        try:
            if os.path.exists(backup_file):
                shutil.copy2(backup_file, CONFIG_FILE)
                self.config = self._load_config()
                return True
        except:
            pass
        return False
    
    def list_backups(self) -> List[Dict]:
        """列出所有备份"""
        backups = []
        for f in os.listdir(BACKUP_DIR):
            if f.endswith(".json"):
                file_path = os.path.join(BACKUP_DIR, f)
                mtime = os.path.getmtime(file_path)
                backups.append({
                    "file": f,
                    "path": file_path,
                    "timestamp": datetime.fromtimestamp(mtime).isoformat(),
                    "size": os.path.getsize(file_path)
                })
        
        backups.sort(key=lambda x: x["timestamp"], reverse=True)
        return backups
    
    def set_agent_permission(self, agent_name: str, permission: PermissionLevel):
        """设置智能体权限"""
        if "permissions" not in self.config:
            self.config["permissions"] = {}
        self.config["permissions"][agent_name] = permission.value
        self.save_config()
    
    def get_agent_permission(self, agent_name: str) -> PermissionLevel:
        """获取智能体权限"""
        permission_str = self.config.get("permissions", {}).get(agent_name, PermissionLevel.NORMAL.value)
        return PermissionLevel(permission_str)
    
    def check_permission(self, agent_name: str, action: str) -> bool:
        """
        检查权限
        
        Args:
            agent_name: 智能体名称
            action: 操作（read/write/admin）
        
        Returns:
            是否有权限
        """
        permission = self.get_agent_permission(agent_name)
        
        if permission == PermissionLevel.ADMIN:
            return True
        elif permission == PermissionLevel.NORMAL:
            return action in ["read", "write"]
        elif permission == PermissionLevel.READONLY:
            return action == "read"
        else:  # GUEST
            return False
    
    def update_agent_config(self, agent_name: str, config: Dict):
        """更新智能体配置"""
        if "agents" not in self.config:
            self.config["agents"] = {}
        self.config["agents"][agent_name] = config
        self.save_config()
    
    def get_agent_config(self, agent_name: str) -> Dict:
        """获取智能体配置"""
        return self.config.get("agents", {}).get(agent_name, {})
    
    def get_all_config(self) -> Dict:
        """获取所有配置"""
        return self.config.copy()


# ============================================================
# 全局实例
# ============================================================

_config_manager: Optional[MCPConfigManager] = None


def get_config_manager() -> MCPConfigManager:
    """获取配置管理器实例（单例）"""
    global _config_manager
    if _config_manager is None:
        _config_manager = MCPConfigManager()
    return _config_manager


# ============================================================
# 测试
# ============================================================

if __name__ == "__main__":
    print("=== 测试MCP配置管理 ===\n")
    
    manager = get_config_manager()
    
    # 测试权限设置
    print("--- 权限设置测试 ---")
    manager.set_agent_permission("FileAgent", PermissionLevel.NORMAL)
    manager.set_agent_permission("SettingsAgent", PermissionLevel.ADMIN)
    
    print(f"FileAgent权限: {manager.get_agent_permission('FileAgent').value}")
    print(f"SettingsAgent权限: {manager.get_agent_permission('SettingsAgent').value}")
    
    # 测试权限检查
    print("\n--- 权限检查测试 ---")
    print(f"FileAgent read: {manager.check_permission('FileAgent', 'read')}")
    print(f"FileAgent write: {manager.check_permission('FileAgent', 'write')}")
    print(f"FileAgent admin: {manager.check_permission('FileAgent', 'admin')}")
    
    # 测试备份
    print("\n--- 备份测试 ---")
    backup_file = manager.backup_config()
    print(f"备份文件: {backup_file}")
    
    backups = manager.list_backups()
    print(f"备份数量: {len(backups)}")
    
    print("\n=== 测试完成 ===")

