#!/usr/bin/env python3
"""
MediaAgent 核心逻辑 - 媒体控制智能体

功能：
1. 播放音频/视频文件
2. 媒体控制（播放/暂停/停止/全屏）
3. 截图当前播放帧

作者：GUI Agent Team
"""

import os
import subprocess
import time
import dbus
from typing import Dict, Optional
from datetime import datetime


class MediaAgentLogic:
    """媒体控制智能体核心逻辑"""
    
    def __init__(self):
        self.screenshot_dir = os.path.expanduser("~/.config/kylin-gui-agent/screenshots")
        os.makedirs(self.screenshot_dir, exist_ok=True)
        self.media_player = "totem"  # 麒麟系统默认媒体播放器
    
    def capture_screenshot(self, prefix: str = "media") -> Optional[str]:
        """截取屏幕"""
        timestamp = int(time.time())
        screenshot_path = os.path.join(self.screenshot_dir, f"{prefix}_{timestamp}.png")
        
        try:
            subprocess.run(["scrot", "-d", "1", screenshot_path], check=True, capture_output=True)
            return screenshot_path
        except:
            try:
                subprocess.run(["gnome-screenshot", "-f", screenshot_path], check=True, capture_output=True)
                return screenshot_path
            except:
                return None
    
    def make_response(self, status: str, msg: str, data: Dict = None, screenshot: str = None) -> Dict:
        """生成标准响应"""
        return {
            "status": status,
            "msg": msg,
            "data": data or {},
            "screenshot_path": screenshot,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    
    # ==================== 播放媒体 ====================
    
    def play_media(self, media_path: str) -> Dict:
        """
        播放媒体文件（音频/视频）
        
        Args:
            media_path: 媒体文件路径（支持本地文件）
        """
        try:
            # 检查文件是否存在
            if not os.path.exists(media_path):
                return self.make_response("error", f"媒体文件不存在: {media_path}")
            
            # 检查文件权限
            if not os.access(media_path, os.R_OK):
                return self.make_response("error", f"无权限读取文件: {media_path}")
            
            # 使用totem播放器播放
            # 方法1: 使用gio launch（推荐）
            try:
                subprocess.Popen(
                    ["gio", "open", media_path],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True
                )
                time.sleep(2)  # 等待播放器启动
                
                screenshot = self.capture_screenshot("media_playing")
                
                return self.make_response(
                    "success",
                    f"媒体文件已开始播放: {os.path.basename(media_path)}",
                    {
                        "media_path": media_path,
                        "media_name": os.path.basename(media_path),
                        "player": self.media_player,
                        "playing": True
                    },
                    screenshot
                )
            except FileNotFoundError:
                # 方法2: 直接使用totem命令
                subprocess.Popen(
                    [self.media_player, media_path],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True
                )
                time.sleep(2)
                
                screenshot = self.capture_screenshot("media_playing")
                
                return self.make_response(
                    "success",
                    f"媒体文件已开始播放: {os.path.basename(media_path)}",
                    {
                        "media_path": media_path,
                        "media_name": os.path.basename(media_path),
                        "player": self.media_player,
                        "playing": True
                    },
                    screenshot
                )
                
        except Exception as e:
            return self.make_response("error", f"播放媒体失败: {e}")
    
    # ==================== 媒体控制 ====================
    
    def media_control(self, action: str) -> Dict:
        """
        控制媒体播放状态
        
        Args:
            action: 操作类型（play/pause/stop/fullscreen/next/previous）
        """
        try:
            # 使用DBus控制totem播放器
            bus = dbus.SessionBus()
            
            # totem的DBus接口
            totem_service = "org.gnome.Totem"
            totem_path = "/org/gnome/Totem"
            totem_interface = "org.gnome.Totem"
            
            if not bus.name_has_owner(totem_service):
                return self.make_response("error", "媒体播放器未运行，请先播放媒体文件")
            
            try:
                totem_proxy = bus.get_object(totem_service, totem_path)
                totem_interface_obj = dbus.Interface(totem_proxy, totem_interface)
                
                action_map = {
                    "play": "Play",
                    "pause": "Pause",
                    "stop": "Stop",
                    "next": "Next",
                    "previous": "Previous",
                }
                
                if action == "fullscreen":
                    # 全屏操作
                    totem_interface_obj.set_fullscreen(True)
                    control_action = "fullscreen"
                elif action in action_map:
                    # 其他控制操作
                    method_name = action_map[action]
                    getattr(totem_interface_obj, method_name)()
                    control_action = action
                else:
                    return self.make_response("error", f"不支持的操作: {action}")
                
                time.sleep(0.5)
                screenshot = self.capture_screenshot(f"media_{control_action}")
                
                return self.make_response(
                    "success",
                    f"媒体控制成功: {action}",
                    {
                        "action": control_action,
                        "status": "success"
                    },
                    screenshot
                )
                
            except dbus.exceptions.DBusException as e:
                # DBus调用失败，尝试使用键盘快捷键
                return self._control_via_hotkey(action)
                
        except Exception as e:
            return self.make_response("error", f"媒体控制失败: {e}")
    
    def _control_via_hotkey(self, action: str) -> Dict:
        """使用键盘快捷键控制媒体（备用方案）"""
        try:
            hotkey_map = {
                "play": "space",
                "pause": "space",
                "stop": "Escape",
                "fullscreen": "f",
            }
            
            if action not in hotkey_map:
                return self.make_response("error", f"不支持的操作: {action}")
            
            # 使用xdotool发送按键
            subprocess.run(
                ["xdotool", "key", hotkey_map[action]],
                check=True,
                capture_output=True,
                timeout=2
            )
            
            time.sleep(0.5)
            screenshot = self.capture_screenshot(f"media_{action}")
            
            return self.make_response(
                "success",
                f"媒体控制成功（快捷键）: {action}",
                {
                    "action": action,
                    "method": "hotkey"
                },
                screenshot
            )
            
        except Exception as e:
            return self.make_response("error", f"快捷键控制失败: {e}")
    
    # ==================== 截图播放帧 ====================
    
    def capture_media_frame(self) -> Dict:
        """
        截图当前播放帧
        
        Returns:
            截图路径
        """
        try:
            screenshot = self.capture_screenshot("media_frame")
            
            if screenshot:
                return self.make_response(
                    "success",
                    "播放帧截图成功",
                    {
                        "screenshot_path": screenshot,
                        "timestamp": datetime.now().isoformat()
                    },
                    screenshot
                )
            else:
                return self.make_response("error", "截图失败，请确保媒体播放器正在运行")
                
        except Exception as e:
            return self.make_response("error", f"截图播放帧失败: {e}")


# ============================================================
# 测试
# ============================================================

if __name__ == "__main__":
    agent = MediaAgentLogic()
    
    print("=== 测试 MediaAgent ===\n")
    
    # 测试播放媒体（需要提供实际文件路径）
    print("1. 播放媒体:")
    print("   提示: 需要提供实际的媒体文件路径进行测试")
    
    # 测试媒体控制
    print("\n2. 媒体控制:")
    result = agent.media_control("pause")
    print(f"   {result['msg']}")
    
    # 测试截图
    print("\n3. 截图播放帧:")
    result = agent.capture_media_frame()
    print(f"   {result['msg']}")
    
    print("\n=== 测试完成 ===")

