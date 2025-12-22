"""SettingsAgent核心逻辑（直接使用test_wallpaper_simple.py的实现）"""
import subprocess
import os
import dbus
import time
import signal
import urllib.parse
import shutil
import sys
import importlib.util
from typing import Dict, Optional

# 导入test_wallpaper_simple模块
def _load_wallpaper_module():
    """动态加载test_wallpaper_simple.py模块"""
    # 从当前文件位置推断项目根目录
    current_file_dir = os.path.dirname(os.path.abspath(__file__))
    # 向上三级到达项目根目录: desktop/agent_project/src -> 项目根目录
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_file_dir)))
    script_path = os.path.join(project_root, "test_wallpaper_simple.py")
    
    # 如果不在预期位置，尝试其他路径
    if not os.path.exists(script_path):
        script_path = os.path.join(os.getcwd(), "test_wallpaper_simple.py")
    if not os.path.exists(script_path):
        script_path = "/home/ok/桌面/Kylin-TARS/test_wallpaper_simple.py"
    
    if not os.path.exists(script_path):
        raise FileNotFoundError(f"找不到test_wallpaper_simple.py脚本: {script_path}")
    
    # 动态导入脚本模块
    spec = importlib.util.spec_from_file_location("test_wallpaper_simple", script_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"无法加载test_wallpaper_simple.py模块: {script_path}")
    
    wallpaper_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(wallpaper_module)
    return wallpaper_module

# 全局加载壁纸模块
_wallpaper_module = None
try:
    _wallpaper_module = _load_wallpaper_module()
except Exception as e:
    print(f"警告: 无法加载test_wallpaper_simple.py模块: {e}")

class SettingsAgentLogic:
    def __init__(self):
        """初始化SettingsAgent"""
        # 定义GNOME支持的壁纸缩放模式
        self.supported_wallpaper_scales = [
            "none",          # 不缩放
            "wallpaper",     # 平铺
            "centered",      # 居中
            "scaled",        # 缩放以适应
            "stretched",     # 拉伸
            "zoom",          # 缩放并裁剪
            "spanned"        # 跨越多个显示器
        ]


    def change_wallpaper(self, wallpaper_path: str, scale: str = "zoom") -> Dict:
        """
        更换桌面壁纸（直接调用test_wallpaper_simple.py中的函数）
        :param wallpaper_path: 壁纸文件路径
        :param scale: 缩放模式（zoom, scaled, stretched等）- 注意：test_wallpaper_simple.py目前固定使用zoom
        :return: 执行结果字典
        """
        try:
            # 检查模块是否已加载
            if _wallpaper_module is None:
                    return {
                    "status": "error",
                    "msg": "无法加载test_wallpaper_simple.py模块，请检查文件是否存在",
                    "data": None
                }
            
            # 1. 验证壁纸文件
            abs_wallpaper_path = os.path.abspath(wallpaper_path)
            valid, abs_path, validate_msg = _wallpaper_module.validate_wallpaper_file(abs_wallpaper_path)
            if not valid:
                return {
                    "status": "error",
                    "msg": f"壁纸文件验证失败: {validate_msg}",
                    "data": None
                }
            
            print(f"正在使用test_wallpaper_simple.py设置壁纸: {abs_path}")
            print(f"DISPLAY环境变量: {os.environ.get('DISPLAY', '未设置')}")
            
            # 2. 检测桌面环境
            desktop_env = _wallpaper_module.get_desktop_environment()
            if desktop_env == 'unknown':
                desktop_env = 'ukui'  # 默认使用UKUI
            
            print(f"检测到桌面环境: {desktop_env}")
            
            # 3. 调用对应的壁纸更换函数（直接使用test_wallpaper_simple.py中的函数）
            success = False
            result_msg = ""
            
            if desktop_env == 'ukui':
                success, result_msg = _wallpaper_module.change_wallpaper_ukui(abs_path)
            elif desktop_env == 'gnome':
                success, result_msg = _wallpaper_module.change_wallpaper_gnome(abs_path)
            elif desktop_env == 'mate':
                success, result_msg = _wallpaper_module.change_wallpaper_mate(abs_path)
            else:
                # 未知环境，尝试UKUI方式
                success, result_msg = _wallpaper_module.change_wallpaper_ukui(abs_path)
            
            # 4. 验证壁纸是否真的更新成功
            wallpaper_updated = False
            final_uri = ""
            try:
                verify_result = subprocess.run(
                    ["gsettings", "get", "org.gnome.desktop.background", "picture-uri"],
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=5
                )
                final_uri = verify_result.stdout.strip().strip("'\"")
                encoded_path = urllib.parse.quote(abs_path, safe='')
                expected_uri = f"file://{encoded_path}"
                uri_match = expected_uri.lower() in final_uri.lower() or final_uri.lower() in expected_uri.lower()
                wallpaper_updated = uri_match
                print(f"壁纸更新验证: {'成功' if wallpaper_updated else '失败'}")
                print(f"  期望URI: {expected_uri}")
                print(f"  实际URI: {final_uri}")
            except Exception as e:
                print(f"壁纸验证失败: {e}")
                wallpaper_updated = False
            
            # 5. 返回结果
            desktop_env_upper = os.environ.get("XDG_CURRENT_DESKTOP", "").upper()
            is_ukui = "UKUI" in desktop_env_upper
            
            if success and wallpaper_updated:
                result_msg_final = f"UKUI壁纸更换成功（使用test_wallpaper_simple.py）" if is_ukui else f"壁纸更换成功（使用test_wallpaper_simple.py）"
                return {
                    "status": "success",
                    "msg": result_msg_final,
                    "data": {
                        "wallpaper_path": abs_path,
                        "scale": scale,
                        "uri": final_uri,
                        "display": os.environ.get("DISPLAY", "未设置"),
                        "desktop_env": desktop_env_upper,
                        "uri_match": True,
                        "result_msg": result_msg
                    }
                }
            elif success:
                # 函数返回成功，但验证失败，可能是桌面刷新延迟
                result_msg_final = f"UKUI壁纸设置命令执行成功，但桌面可能未刷新。请尝试手动刷新桌面（按F5或右键刷新）" if is_ukui else f"壁纸设置命令执行成功，但桌面可能未刷新"
                return {
                    "status": "warning",
                    "msg": result_msg_final,
                    "data": {
                        "wallpaper_path": abs_path,
                        "scale": scale,
                        "uri": final_uri,
                        "display": os.environ.get("DISPLAY", "未设置"),
                        "desktop_env": desktop_env_upper,
                        "uri_match": False,
                        "result_msg": result_msg,
                        "suggestion": "如果桌面未更新，请尝试：1) 手动刷新桌面（按F5或右键刷新）；2) 检查wallpaper.xml：head -5 ~/.config/ukui/wallpaper.xml；3) 重启ukui-settings-daemon：killall -HUP ukui-settings-daemon"
                    }
                }
            else:
                # 函数执行失败
                return {
                    "status": "error",
                    "msg": f"壁纸更换失败: {result_msg}",
                    "data": {
                        "wallpaper_path": abs_path,
                        "desktop_env": desktop_env_upper,
                        "result_msg": result_msg
                    }
                }
                
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            return {
                "status": "error",
                "msg": f"壁纸修改失败：未知错误 - {str(e)}",
                "data": {
                    "error_type": type(e).__name__,
                    "error_trace": error_trace
                }
            }

    def adjust_volume(self, volume: int, device: str = "@DEFAULT_SINK@") -> Dict:
        """调用gsettings调整系统音量"""
        try:
            if not (0 <= volume <= 100):
                return {"status": "error", "msg": "音量值必须在0-100之间", "data": None}

            # 使用pactl命令调整音量（最可靠）
            subprocess.run(
                [
                    "pactl", "set-sink-volume",
                    device,
                    f"{volume}%"
                ],
                check=True,
                capture_output=True,
                text=True
            )
            
            # 获取实际音量
            result = subprocess.run(
                ["pactl", "get-sink-volume", device],
                capture_output=True,
                text=True,
                check=True
            )
            actual_volume = int(result.stdout.split("/")[1].strip().replace("%", ""))
            
            return {
                "status": "success",
                "msg": f"音量调整成功（目标：{volume}%，实际：{actual_volume}%）",
                "data": {"target_volume": volume, "actual_volume": actual_volume, "device": device}
            }
        except subprocess.CalledProcessError as e:
            stderr_msg = e.stderr.strip() if e.stderr else str(e)
            return {"status": "error", "msg": f"音量调整失败：{stderr_msg}", "data": None}
        except Exception as e:
            return {"status": "error", "msg": f"未知错误：{str(e)}", "data": None}
    
    def bluetooth_manage(self, action: str, device_name: Optional[str] = None) -> Dict:
        """
        蓝牙管理（开启/关闭/连接已配对设备）- 优先使用bluetoothctl命令行工具

        Args:
            action: 操作类型（enable/disable/connect/status）
            device_name: 设备名称或MAC地址（连接时必需）

        Returns:
            操作结果字典
        """
        # 首先检查是否有蓝牙硬件/服务
        has_bluetooth = False
        try:
            # 检查蓝牙服务是否存在
            result = subprocess.run(
                ["systemctl", "list-unit-files", "bluetooth.service"],
                capture_output=True,
                text=True,
                check=False,
                timeout=3
            )
            if "bluetooth.service" in result.stdout:
                # 检查是否有蓝牙适配器
                hci_result = subprocess.run(
                    ["hciconfig"],
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=3
                )
                if hci_result.returncode == 0 and "hci" in hci_result.stdout:
                    has_bluetooth = True
        except:
            pass
        
        if not has_bluetooth:
            return {
                "status": "error",
                "msg": "未检测到蓝牙硬件或蓝牙服务不可用（虚拟机可能没有蓝牙适配器）",
                "data": None
            }
        
        # 优先使用命令行工具（bluetoothctl），兼容性更好
        try:
            if action == "status":
                # 查询蓝牙状态
                bluetooth_status = {}
                
                # 检查蓝牙服务状态
                try:
                    result = subprocess.run(
                        ["systemctl", "is-active", "bluetooth"],
                        capture_output=True,
                        text=True,
                        check=False,
                        timeout=3
                    )
                    bluetooth_status["service_active"] = result.stdout.strip() == "active"
                except:
                    bluetooth_status["service_active"] = False
                
                # 检查蓝牙适配器状态（使用bluetoothctl）
                powered = False
                try:
                    result = subprocess.run(
                        ["bluetoothctl", "show"],
                        capture_output=True,
                        text=True,
                        check=False,
                        timeout=5
                    )
                    if result.returncode == 0:
                        powered = "Powered: yes" in result.stdout
                except:
                    pass
                
                # 获取已配对设备
                paired_devices = []
                try:
                    result = subprocess.run(
                        ["bluetoothctl", "paired-devices"],
                        capture_output=True,
                        text=True,
                        check=False,  # 改为check=False，避免在没有配对设备时报错
                        timeout=5
                    )
                    
                    # 如果命令成功执行（即使没有配对设备）
                    if result.returncode == 0:
                        for line in result.stdout.strip().split('\n'):
                            if line.strip():
                                parts = line.split()
                                if len(parts) >= 2:
                                    address = parts[1]
                                    name = ' '.join(parts[2:]) if len(parts) > 2 else address
                                    
                                    # 检查连接状态
                                    connected = False
                                    try:
                                        conn_result = subprocess.run(
                                            ["bluetoothctl", "info", address],
                                            capture_output=True,
                                            text=True,
                                            check=False,
                                            timeout=3
                                        )
                                        if conn_result.returncode == 0:
                                            connected = "Connected: yes" in conn_result.stdout
                                    except:
                                        pass
                                    
                                    paired_devices.append({
                                        "name": name,
                                        "address": address,
                                        "connected": connected
                                    })
                except Exception as e:
                    print(f"获取配对设备失败: {e}")
                
                return {
                    "status": "success",
                    "msg": "蓝牙状态查询成功",
                    "data": {
                        "powered": powered,
                        "service_active": bluetooth_status.get("service_active", False),
                        "paired_devices": paired_devices,
                        "paired_count": len(paired_devices)
                    }
                }
            
            elif action == "enable":
                # 开启蓝牙
                commands = [
                    ["systemctl", "start", "bluetooth"],
                    ["bluetoothctl", "power", "on"]
                ]
                
                success_count = 0
                errors = []
                
                for cmd in commands:
                    try:
                        subprocess.run(cmd, check=True, capture_output=True, timeout=5)
                        success_count += 1
                    except Exception as e:
                        errors.append(f"{cmd[0]}: {str(e)}")
                
                if success_count > 0:
                    return {
                        "status": "success",
                        "msg": f"蓝牙已开启（成功执行 {success_count}/{len(commands)} 个命令）",
                        "data": {"powered": True}
                    }
                else:
                    return {"status": "error", "msg": f"开启蓝牙失败：{'; '.join(errors)}", "data": None}
            
            elif action == "disable":
                # 关闭蓝牙
                commands = [
                    ["bluetoothctl", "power", "off"]
                ]
                
                success_count = 0
                errors = []
                
                for cmd in commands:
                    try:
                        result = subprocess.run(cmd, check=False, capture_output=True, text=True, timeout=5)
                        if result.returncode == 0:
                            success_count += 1
                        else:
                            # 检查是否是"Already off"的情况
                            if "already off" in result.stderr.lower() or "already off" in result.stdout.lower():
                                success_count += 1  # 已经关闭也算成功
                            else:
                                errors.append(f"{cmd[0]}: {result.stderr if result.stderr else result.stdout}")
                    except Exception as e:
                        errors.append(f"{cmd[0]}: {str(e)}")
                
                if success_count > 0:
                    return {
                        "status": "success",
                        "msg": f"蓝牙已关闭（成功执行 {success_count}/{len(commands)} 个命令）",
                        "data": {"powered": False}
                    }
                else:
                    return {"status": "error", "msg": f"关闭蓝牙失败：{'; '.join(errors) if errors else '未知错误'}", "data": None}
            
            elif action == "connect":
                # 连接设备
                if not device_name:
                    return {"status": "error", "msg": "连接设备需要指定设备名称或地址", "data": None}
                
                # 如果是设备名称，尝试获取地址
                device_address = device_name
                
                # 检查是否是MAC地址格式
                import re
                if not re.match(r'^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$', device_name):
                    # 尝试通过名称查找地址
                    try:
                        result = subprocess.run(
                            ["bluetoothctl", "paired-devices"],
                            capture_output=True,
                            text=True,
                            check=True,
                            timeout=5
                        )
                        
                        for line in result.stdout.strip().split('\n'):
                            if device_name.lower() in line.lower():
                                parts = line.split()
                                if len(parts) >= 2:
                                    device_address = parts[1]
                                    break
                    except:
                        return {"status": "error", "msg": f"无法找到设备 {device_name} 的地址", "data": None}
                
                # 连接设备
                try:
                    # 先确保蓝牙已开启
                    subprocess.run(["bluetoothctl", "power", "on"], check=False, capture_output=True, timeout=3)
                    time.sleep(1)  # 等待蓝牙启动
                    
                    # 连接设备
                    result = subprocess.run(
                        ["bluetoothctl", "connect", device_address],
                        capture_output=True,
                        text=True,
                        check=True,
                        timeout=10
                    )
                    
                    if "Connection successful" in result.stdout or "successful" in result.stdout.lower():
                        return {
                            "status": "success",
                            "msg": f"已连接到设备 {device_name} ({device_address})",
                            "data": {"device_name": device_name, "address": device_address, "connected": True}
                        }
                    else:
                        return {"status": "error", "msg": f"连接失败：{result.stdout}", "data": None}
                        
                except subprocess.TimeoutExpired:
                    return {"status": "error", "msg": f"连接超时：设备 {device_name} 可能不可用", "data": None}
                except subprocess.CalledProcessError as e:
                    error_msg = e.stderr if e.stderr else str(e)
                    if "Already connected" in error_msg or "already connected" in error_msg.lower():
                        return {
                            "status": "success",
                            "msg": f"设备 {device_name} 已连接",
                            "data": {"device_name": device_name, "connected": True}
                        }
                    return {"status": "error", "msg": f"连接失败：{error_msg}", "data": None}
            
            else:
                return {"status": "error", "msg": f"不支持的操作：{action}，支持的操作：enable/disable/connect/status", "data": None}

        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"蓝牙操作异常详情：{error_details}")
            return {"status": "error", "msg": f"蓝牙操作失败：{str(e)}", "data": None}
    
    def get_volume(self) -> Dict:
        """获取当前音量"""
        try:
            result = subprocess.run(
                ["pactl", "get-sink-volume", "@DEFAULT_SINK@"],
                capture_output=True,
                text=True,
                check=True
            )
            volume_str = result.stdout.split("/")[1].strip().replace("%", "")
            volume = int(volume_str)
            
            return {
                "status": "success",
                "msg": f"当前音量：{volume}%",
                "data": {"volume": volume}
            }
        except Exception as e:
            return {"status": "error", "msg": f"获取音量失败：{str(e)}", "data": None}