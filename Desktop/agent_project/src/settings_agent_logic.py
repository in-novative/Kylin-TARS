"""SettingsAgent核心逻辑（修复缩放模式警告）"""
import subprocess
import os
import dbus
from typing import Dict, Optional

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
        """调用DBus修改桌面壁纸（修复缩放模式）"""
        try:
            # 1. 验证壁纸文件存在
            if not os.path.exists(wallpaper_path):
                return {"status": "error", "msg": f"壁纸文件不存在：{wallpaper_path}", "data": None}

            # 2. 验证并标准化缩放模式
            if scale not in self.supported_wallpaper_scales:
                print(f"警告：无效的缩放模式 '{scale}'，使用默认值 'zoom'")
                scale = "zoom"  # 使用默认值

            # 3. 首选方案：使用org.gnome.Shell DBus服务
            try:
                escaped_path = wallpaper_path.replace("'", "\\'")
                js_command = f"""
                const Gio = imports.gi.Gio;
                const settings = new Gio.Settings({{ schema: 'org.gnome.desktop.background' }});
                settings.set_string('picture-uri', 'file://{escaped_path}');
                settings.set_string('picture-options', '{scale}');
                """
                
                result = subprocess.run(
                    [
                        "gdbus", "call",
                        "--session",
                        "--dest", "org.gnome.Shell",
                        "--object-path", "/org/gnome/Shell",
                        "--method", "org.gnome.Shell.Eval",
                        js_command.strip()
                    ],
                    capture_output=True,
                    text=True
                )
                
                if "true" in result.stdout:
                    return {
                        "status": "success",
                        "msg": f"壁纸修改成功（DBus方案）：{wallpaper_path}",
                        "data": {"wallpaper_path": wallpaper_path, "scale": scale}
                    }
            except Exception as e:
                print(f"DBus方案失败，尝试备选方案：{e}")

            # 4. 备选方案：直接使用gsettings命令
            subprocess.run(
                [
                    "gsettings", "set",
                    "org.gnome.desktop.background",
                    "picture-uri",
                    f"file://{wallpaper_path}"
                ],
                check=True,
                capture_output=True,
                text=True
            )
            
            subprocess.run(
                [
                    "gsettings", "set",
                    "org.gnome.desktop.background",
                    "picture-options",
                    scale
                ],
                check=True,
                capture_output=True,
                text=True
            )
            
            return {
                "status": "success",
                "msg": f"壁纸修改成功（gsettings备选方案）：{wallpaper_path}",
                "data": {"wallpaper_path": wallpaper_path, "scale": scale}
            }
        except subprocess.CalledProcessError as e:
            stderr_msg = e.stderr.strip() if e.stderr else str(e)
            return {"status": "error", "msg": f"壁纸修改失败：{stderr_msg}", "data": None}
        except Exception as e:
            return {"status": "error", "msg": f"未知错误：{str(e)}", "data": None}

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
        蓝牙管理（开启/关闭/连接已配对设备）
        
        Args:
            action: 操作类型（enable/disable/connect/status）
            device_name: 设备名称（连接时必需）
        
        Returns:
            操作结果字典
        """
        try:
            # 使用BlueZ DBus接口
            bus = dbus.SystemBus()
            bluez_service = "org.bluez"
            
            if action == "status":
                # 查询蓝牙状态
                try:
                    adapter_path = "/org/bluez/hci0"
                    adapter_interface = "org.bluez.Adapter1"
                    
                    adapter_proxy = bus.get_object(bluez_service, adapter_path)
                    adapter_props = dbus.Interface(adapter_proxy, "org.freedesktop.DBus.Properties")
                    
                    powered = adapter_props.Get(adapter_interface, "Powered")
                    discoverable = adapter_props.Get(adapter_interface, "Discoverable")
                    
                    # 获取已配对设备列表
                    paired_devices = []
                    try:
                        manager = dbus.Interface(adapter_proxy, "org.freedesktop.DBus.ObjectManager")
                        objects = manager.GetManagedObjects()
                        
                        for path, interfaces in objects.items():
                            if "org.bluez.Device1" in interfaces:
                                device_props = interfaces["org.bluez.Device1"]
                                if device_props.get("Paired", False):
                                    paired_devices.append({
                                        "name": device_props.get("Name", "Unknown"),
                                        "address": device_props.get("Address", "Unknown"),
                                        "connected": device_props.get("Connected", False)
                                    })
                    except:
                        pass
                    
                    return {
                        "status": "success",
                        "msg": "蓝牙状态查询成功",
                        "data": {
                            "powered": bool(powered),
                            "discoverable": bool(discoverable),
                            "paired_devices": paired_devices,
                            "paired_count": len(paired_devices)
                        }
                    }
                except dbus.exceptions.DBusException as e:
                    return {"status": "error", "msg": f"查询蓝牙状态失败：{e}", "data": None}
            
            elif action == "enable":
                # 开启蓝牙
                try:
                    adapter_path = "/org/bluez/hci0"
                    adapter_interface = "org.bluez.Adapter1"
                    
                    adapter_proxy = bus.get_object(bluez_service, adapter_path)
                    adapter = dbus.Interface(adapter_proxy, adapter_interface)
                    
                    adapter.Set("Powered", dbus.Boolean(True))
                    
                    return {
                        "status": "success",
                        "msg": "蓝牙已开启",
                        "data": {"powered": True}
                    }
                except dbus.exceptions.DBusException as e:
                    # 备选方案：使用rfkill命令
                    try:
                        subprocess.run(["rfkill", "unblock", "bluetooth"], check=True, capture_output=True)
                        subprocess.run(["hciconfig", "hci0", "up"], check=True, capture_output=True)
                        return {
                            "status": "success",
                            "msg": "蓝牙已开启（使用rfkill）",
                            "data": {"powered": True}
                        }
                    except:
                        return {"status": "error", "msg": f"开启蓝牙失败：{e}", "data": None}
            
            elif action == "disable":
                # 关闭蓝牙
                try:
                    adapter_path = "/org/bluez/hci0"
                    adapter_interface = "org.bluez.Adapter1"
                    
                    adapter_proxy = bus.get_object(bluez_service, adapter_path)
                    adapter = dbus.Interface(adapter_proxy, adapter_interface)
                    
                    adapter.Set("Powered", dbus.Boolean(False))
                    
                    return {
                        "status": "success",
                        "msg": "蓝牙已关闭",
                        "data": {"powered": False}
                    }
                except dbus.exceptions.DBusException as e:
                    # 备选方案：使用rfkill命令
                    try:
                        subprocess.run(["rfkill", "block", "bluetooth"], check=True, capture_output=True)
                        return {
                            "status": "success",
                            "msg": "蓝牙已关闭（使用rfkill）",
                            "data": {"powered": False}
                        }
                    except:
                        return {"status": "error", "msg": f"关闭蓝牙失败：{e}", "data": None}
            
            elif action == "connect":
                # 连接已配对设备
                if not device_name:
                    return {"status": "error", "msg": "连接设备需要指定设备名称", "data": None}
                
                try:
                    adapter_path = "/org/bluez/hci0"
                    manager = dbus.Interface(bus.get_object(bluez_service, adapter_path), "org.freedesktop.DBus.ObjectManager")
                    objects = manager.GetManagedObjects()
                    
                    device_path = None
                    for path, interfaces in objects.items():
                        if "org.bluez.Device1" in interfaces:
                            device_props = interfaces["org.bluez.Device1"]
                            if device_props.get("Name", "") == device_name or device_props.get("Alias", "") == device_name:
                                device_path = path
                                break
                    
                    if not device_path:
                        return {"status": "error", "msg": f"未找到设备：{device_name}，请先配对设备", "data": None}
                    
                    device_proxy = bus.get_object(bluez_service, device_path)
                    device = dbus.Interface(device_proxy, "org.bluez.Device1")
                    device.Connect()
                    
                    return {
                        "status": "success",
                        "msg": f"已连接到设备：{device_name}",
                        "data": {"device_name": device_name, "connected": True}
                    }
                except dbus.exceptions.DBusException as e:
                    return {"status": "error", "msg": f"连接设备失败：{e}", "data": None}
            
            else:
                return {"status": "error", "msg": f"不支持的操作：{action}，支持的操作：enable/disable/connect/status", "data": None}
                
        except Exception as e:
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