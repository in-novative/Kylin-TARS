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
    蓝牙管理（开启/关闭/连接已配对设备）- 修复DBus错误
    
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
        
        # 首先获取蓝牙适配器路径
        manager = dbus.Interface(
            bus.get_object(bluez_service, "/"),
            "org.freedesktop.DBus.ObjectManager"
        )
        objects = manager.GetManagedObjects()
        
        # 查找蓝牙适配器
        adapter_path = None
        for path, interfaces in objects.items():
            if "org.bluez.Adapter1" in interfaces:
                adapter_path = path
                break
        
        if not adapter_path:
            # 如果没有找到适配器，尝试使用hci0路径
            adapter_path = "/org/bluez/hci0"
        
        if action == "status":
            # 查询蓝牙状态
            try:
                # 获取适配器属性
                adapter_obj = bus.get_object(bluez_service, adapter_path)
                adapter_props = dbus.Interface(adapter_obj, "org.freedesktop.DBus.Properties")
                
                # 使用正确的接口名称和方法
                powered = adapter_props.Get("org.bluez.Adapter1", "Powered")
                discoverable = adapter_props.Get("org.bluez.Adapter1", "Discoverable")
                
                # 获取已配对设备列表
                paired_devices = []
                try:
                    for path, interfaces in objects.items():
                        if "org.bluez.Device1" in interfaces:
                            device_props = interfaces["org.bluez.Device1"]
                            if device_props.get("Paired", False):
                                # 获取设备属性
                                device_obj = bus.get_object(bluez_service, path)
                                device_props_iface = dbus.Interface(device_obj, "org.freedesktop.DBus.Properties")
                                
                                name = device_props_iface.Get("org.bluez.Device1", "Name")
                                address = device_props_iface.Get("org.bluez.Device1", "Address")
                                connected = device_props_iface.Get("org.bluez.Device1", "Connected")
                                
                                paired_devices.append({
                                    "name": str(name),
                                    "address": str(address),
                                    "connected": bool(connected)
                                })
                except Exception as e:
                    print(f"获取配对设备信息时出错: {e}")
                    # 使用回退方法
                    for path, interfaces in objects.items():
                        if "org.bluez.Device1" in interfaces:
                            device_props = interfaces["org.bluez.Device1"]
                            if device_props.get("Paired", False):
                                paired_devices.append({
                                    "name": str(device_props.get("Name", "Unknown")),
                                    "address": str(device_props.get("Address", "Unknown")),
                                    "connected": bool(device_props.get("Connected", False))
                                })
                
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
                return {"status": "error", "msg": f"查询蓝牙状态失败（DBus）：{e}", "data": None}
            
        elif action == "enable":
            # 开启蓝牙
            try:
                adapter_obj = bus.get_object(bluez_service, adapter_path)
                adapter = dbus.Interface(adapter_obj, "org.bluez.Adapter1")
                adapter_props = dbus.Interface(adapter_obj, "org.freedesktop.DBus.Properties")
                
                # 使用正确的接口和方法设置属性
                adapter_props.Set("org.bluez.Adapter1", "Powered", dbus.Boolean(True))
                
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
                except Exception as rfkill_error:
                    return {"status": "error", "msg": f"开启蓝牙失败：DBus: {e}, rfkill: {rfkill_error}", "data": None}
            
        elif action == "disable":
            # 关闭蓝牙
            try:
                adapter_obj = bus.get_object(bluez_service, adapter_path)
                adapter_props = dbus.Interface(adapter_obj, "org.freedesktop.DBus.Properties")
                
                # 使用正确的接口和方法设置属性
                adapter_props.Set("org.bluez.Adapter1", "Powered", dbus.Boolean(False))
                
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
                except Exception as rfkill_error:
                    return {"status": "error", "msg": f"关闭蓝牙失败：DBus: {e}, rfkill: {rfkill_error}", "data": None}
            
        elif action == "connect":
            # 连接已配对设备
            if not device_name:
                return {"status": "error", "msg": "连接设备需要指定设备名称或地址", "data": None}
            
            try:
                device_path = None
                device_address = None
                
                # 搜索设备
                for path, interfaces in objects.items():
                    if "org.bluez.Device1" in interfaces:
                        try:
                            device_obj = bus.get_object(bluez_service, path)
                            device_props = dbus.Interface(device_obj, "org.freedesktop.DBus.Properties")
                            
                            name = str(device_props.Get("org.bluez.Device1", "Name"))
                            address = str(device_props.Get("org.bluez.Device1", "Address"))
                            alias = str(device_props.Get("org.bluez.Device1", "Alias"))
                            
                            # 匹配名称或地址
                            if (name.lower() == device_name.lower() or 
                                address.lower() == device_name.lower() or
                                alias.lower() == device_name.lower()):
                                device_path = path
                                device_address = address
                                break
                        except:
                            continue
                
                if not device_path:
                    return {"status": "error", "msg": f"未找到设备：{device_name}，请先配对设备", "data": None}
                
                # 连接设备
                device_obj = bus.get_object(bluez_service, device_path)
                device = dbus.Interface(device_obj, "org.bluez.Device1")
                device.Connect()
                
                return {
                    "status": "success",
                    "msg": f"已连接到设备：{device_name}",
                    "data": {"device_name": device_name, "address": device_address, "connected": True}
                }
            except dbus.exceptions.DBusException as e:
                error_msg = str(e)
                if "Already connected" in error_msg:
                    return {
                        "status": "success",
                        "msg": f"设备 {device_name} 已连接",
                        "data": {"device_name": device_name, "connected": True}
                    }
                elif "Connection attempt without pairing" in error_msg:
                    return {"status": "error", "msg": f"设备 {device_name} 未配对，请先配对", "data": None}
                else:
                    return {"status": "error", "msg": f"连接设备失败：{error_msg}", "data": None}
            
        else:
            return {"status": "error", "msg": f"不支持的操作：{action}，支持的操作：enable/disable/connect/status", "data": None}
            
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"蓝牙操作异常详情：{error_details}")
        return {"status": "error", "msg": f"蓝牙操作失败：{str(e)}", "data": None}

def bluetooth_manage_cli(self, action: str, device_name: Optional[str] = None) -> Dict:
    """
    蓝牙管理（使用命令行工具）- 兼容性更好的版本
    
    Args:
        action: 操作类型（enable/disable/connect/disconnect/status/pair/list）
        device_name: 设备名称或MAC地址
    
    Returns:
        操作结果字典
    """
    try:
        if action == "status":
            # 检查蓝牙服务状态
            bluetooth_status = {}
            
            # 检查蓝牙适配器状态
            try:
                result = subprocess.run(
                    ["rfkill", "list", "bluetooth"],
                    capture_output=True,
                    text=True,
                    check=True
                )
                if "Soft blocked: no" in result.stdout and "Hard blocked: no" in result.stdout:
                    bluetooth_status["rfkill_unblocked"] = True
                else:
                    bluetooth_status["rfkill_unblocked"] = False
            except:
                bluetooth_status["rfkill_unblocked"] = False
            
            # 检查蓝牙服务
            try:
                result = subprocess.run(
                    ["systemctl", "is-active", "bluetooth"],
                    capture_output=True,
                    text=True,
                    check=False
                )
                bluetooth_status["service_active"] = result.stdout.strip() == "active"
            except:
                bluetooth_status["service_active"] = False
            
            # 检查蓝牙适配器
            try:
                result = subprocess.run(
                    ["hciconfig", "hci0"],
                    capture_output=True,
                    text=True,
                    check=False
                )
                bluetooth_status["adapter_available"] = "UP" in result.stdout
            except:
                bluetooth_status["adapter_available"] = False
            
            # 获取已配对设备
            paired_devices = []
            try:
                result = subprocess.run(
                    ["bluetoothctl", "paired-devices"],
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=5
                )
                
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
                                    check=True,
                                    timeout=3
                                )
                                connected = "Connected: yes" in conn_result.stdout
                            except:
                                pass
                            
                            paired_devices.append({
                                "name": name,
                                "address": address,
                                "connected": connected
                            })
            except:
                pass
            
            # 综合状态
            powered = bluetooth_status.get("rfkill_unblocked", False) and bluetooth_status.get("adapter_available", False)
            
            return {
                "status": "success",
                "msg": "蓝牙状态查询成功",
                "data": {
                    "powered": powered,
                    "service_active": bluetooth_status.get("service_active", False),
                    "rfkill_unblocked": bluetooth_status.get("rfkill_unblocked", False),
                    "adapter_available": bluetooth_status.get("adapter_available", False),
                    "paired_devices": paired_devices,
                    "paired_count": len(paired_devices)
                }
            }
        
        elif action == "enable":
            # 开启蓝牙
            commands = [
                ["rfkill", "unblock", "bluetooth"],
                ["systemctl", "start", "bluetooth"],
                ["systemctl", "enable", "bluetooth"],
                ["hciconfig", "hci0", "up"]
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
                    "msg": f"蓝牙已开启（成功执行 {success_count}/4 个命令）",
                    "data": {"powered": True, "errors": errors if errors else None}
                }
            else:
                return {"status": "error", "msg": f"开启蓝牙失败：{'; '.join(errors)}", "data": None}
        
        elif action == "disable":
            # 关闭蓝牙
            commands = [
                ["bluetoothctl", "power", "off"],
                ["hciconfig", "hci0", "down"],
                ["rfkill", "block", "bluetooth"]
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
                    "msg": f"蓝牙已关闭（成功执行 {success_count}/3 个命令）",
                    "data": {"powered": False, "errors": errors if errors else None}
                }
            else:
                return {"status": "error", "msg": f"关闭蓝牙失败：{'; '.join(errors)}", "data": None}
        
        elif action == "connect":
            # 连接设备
            if not device_name:
                return {"status": "error", "msg": "需要指定设备地址或名称", "data": None}
            
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
                subprocess.run(["bluetoothctl", "power", "on"], check=False, capture_output=True)
                
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
                return {"status": "error", "msg": f"连接失败：{e.stderr}", "data": None}
        
        elif action == "list":
            # 扫描并列出可用设备
            try:
                # 开始扫描
                subprocess.run(["bluetoothctl", "scan", "on"], check=False, capture_output=True)
                time.sleep(3)  # 等待扫描结果
                subprocess.run(["bluetoothctl", "scan", "off"], check=False, capture_output=True)
                
                # 获取设备列表
                result = subprocess.run(
                    ["bluetoothctl", "devices"],
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=5
                )
                
                devices = []
                for line in result.stdout.strip().split('\n'):
                    if line.strip():
                        parts = line.split()
                        if len(parts) >= 3:
                            address = parts[1]
                            name = ' '.join(parts[2:])
                            devices.append({"name": name, "address": address})
                
                return {
                    "status": "success",
                    "msg": f"找到 {len(devices)} 个设备",
                    "data": {"devices": devices, "count": len(devices)}
                }
            except Exception as e:
                return {"status": "error", "msg": f"扫描设备失败：{str(e)}", "data": None}
        
        else:
            return {"status": "error", "msg": f"不支持的操作：{action}，支持的操作：enable/disable/connect/list/status", "data": None}
            
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"蓝牙CLI操作异常：{error_details}")
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