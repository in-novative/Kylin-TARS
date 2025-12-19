"""SettingsAgent核心逻辑（修复缩放模式警告）"""
import subprocess
import os
import dbus
import time
import urllib.parse
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
            if not os.path.exists(wallpaper_path) or not wallpaper_path.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.svg')):
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
            # 确保使用绝对路径，并进行URL编码
            abs_wallpaper_path = os.path.abspath(wallpaper_path)
            
            # UKUI特殊处理：将壁纸复制到UKUI的壁纸目录（如果不存在）
            desktop_env = os.environ.get("XDG_CURRENT_DESKTOP", "").upper()
            if "UKUI" in desktop_env:
                try:
                    ukui_wallpaper_dir = os.path.expanduser("~/.local/share/ukui-control-center/wallpaperData")
                    os.makedirs(ukui_wallpaper_dir, exist_ok=True)
                    
                    # 生成壁纸文件名（基于原文件名）
                    wallpaper_basename = os.path.basename(abs_wallpaper_path)
                    ukui_wallpaper_path = os.path.join(ukui_wallpaper_dir, wallpaper_basename)
                    
                    # 如果文件不在UKUI目录中，复制一份
                    if not os.path.exists(ukui_wallpaper_path):
                        import shutil
                        shutil.copy2(abs_wallpaper_path, ukui_wallpaper_path)
                        print(f"已将壁纸复制到UKUI目录: {ukui_wallpaper_path}")
                    
                    # 更新UKUI的wallpaper.xml配置文件
                    try:
                        wallpaper_xml = os.path.expanduser("~/.config/ukui/wallpaper.xml")
                        if os.path.exists(wallpaper_xml):
                            import xml.etree.ElementTree as ET
                            tree = ET.parse(wallpaper_xml)
                            root = tree.getroot()
                            
                            # 检查是否已存在
                            exists = False
                            for wp in root.findall('wallpaper'):
                                if wp.find('filename') is not None and abs_wallpaper_path in wp.find('filename').text:
                                    exists = True
                                    break
                            
                            # 如果不存在，添加新条目
                            if not exists:
                                wp = ET.SubElement(root, 'wallpaper')
                                wp.set('deleted', 'false')
                                ET.SubElement(wp, 'artist').text = '(none)'
                                ET.SubElement(wp, '_name').text = os.path.splitext(wallpaper_basename)[0]
                                ET.SubElement(wp, 'filename').text = abs_wallpaper_path
                                ET.SubElement(wp, 'options').text = scale
                                ET.SubElement(wp, 'pcolor').text = '#000000'
                                ET.SubElement(wp, 'scolor').text = '#000000'
                                ET.SubElement(wp, 'shade_type').text = 'solid'
                                tree.write(wallpaper_xml, encoding='UTF-8', xml_declaration=True)
                                print(f"已更新UKUI wallpaper.xml配置文件")
                    except Exception as e:
                        print(f"更新UKUI wallpaper.xml失败: {e}")
                except Exception as e:
                    print(f"UKUI特殊处理失败: {e}")
            
            # gsettings 需要 file:// URI 格式，路径需要 URL 编码
            encoded_path = urllib.parse.quote(abs_wallpaper_path, safe='')
            file_uri = f"file://{encoded_path}"
            
            # 确保环境变量正确传递（特别是 DISPLAY）
            env = os.environ.copy()
            # 如果没有 DISPLAY，尝试设置
            if not env.get("DISPLAY"):
                # 检查 X11 socket
                if os.path.exists("/tmp/.X11-unix/X0"):
                    env["DISPLAY"] = ":0"
                elif os.path.exists("/tmp/.X11-unix/X1"):
                    env["DISPLAY"] = ":1"
                else:
                    # 尝试从 systemd 获取
                    try:
                        result = subprocess.run(
                            ["loginctl", "show-session", "-p", "Display"],
                            capture_output=True,
                            text=True,
                            timeout=2
                        )
                        if result.returncode == 0 and result.stdout.strip():
                            display = result.stdout.strip().split("=")[-1]
                            if display:
                                env["DISPLAY"] = display
                    except:
                        pass
            
            # 设置壁纸URI
            result1 = subprocess.run(
                [
                    "gsettings", "set",
                    "org.gnome.desktop.background",
                    "picture-uri",
                    file_uri
                ],
                check=True,
                capture_output=True,
                text=True,
                timeout=10,
                env=env
            )
            
            # 设置缩放模式
            result2 = subprocess.run(
                [
                    "gsettings", "set",
                    "org.gnome.desktop.background",
                    "picture-options",
                    scale
                ],
                check=True,
                capture_output=True,
                text=True,
                timeout=10,
                env=env
            )
            
            # 验证设置是否成功
            verify_result = subprocess.run(
                ["gsettings", "get", "org.gnome.desktop.background", "picture-uri"],
                capture_output=True,
                text=True,
                check=True,
                timeout=5,
                env=env
            )
            current_uri = verify_result.stdout.strip().strip("'\"")
            
            # 强制刷新桌面环境（多种方法）
            # 方法1: 通过 gsettings 触发刷新（先设置为空再设置回目标值）
            try:
                subprocess.run(
                    ["gsettings", "set", "org.gnome.desktop.background", "picture-uri", "''"],
                    capture_output=True,
                    timeout=2,
                    env=env
                )
                time.sleep(0.3)
                subprocess.run(
                    ["gsettings", "set", "org.gnome.desktop.background", "picture-uri", file_uri],
                    capture_output=True,
                    timeout=2,
                    env=env
                )
                time.sleep(0.3)
            except:
                pass
            
            # 方法2: 检测桌面环境并尝试相应的刷新方法
            desktop_env = os.environ.get("XDG_CURRENT_DESKTOP", "").upper()
            
            # UKUI桌面环境特殊处理
            if "UKUI" in desktop_env:
                try:
                    # UKUI方法1: 通过UKUI SettingsDaemon刷新
                    subprocess.run(
                        [
                            "dbus-send",
                            "--session",
                            "--type=method_call",
                            "--dest=org.ukui.SettingsDaemon.plugins.background",
                            "/org/ukui/SettingsDaemon/plugins/background",
                            "org.ukui.SettingsDaemon.plugins.background.Refresh"
                        ],
                        capture_output=True,
                        timeout=3,
                        env=env
                    )
                except:
                    pass
                
                try:
                    # UKUI方法2: 同时设置UKUI的background schema
                    subprocess.run(
                        ["gsettings", "set", "org.ukui.SettingsDaemon.plugins.background", "picture-uri", file_uri],
                        capture_output=True,
                        timeout=2,
                        env=env
                    )
                except:
                    pass
            
            # GNOME Shell刷新方法（如果存在）
            refresh_js = f"""
            const Gio = imports.gi.Gio;
            const settings = new Gio.Settings({{ schema: 'org.gnome.desktop.background' }});
            settings.set_string('picture-uri', '{file_uri}');
            settings.set_string('picture-options', '{scale}');
            """
            try:
                result = subprocess.run(
                    [
                        "gdbus", "call",
                        "--session",
                        "--dest", "org.gnome.Shell",
                        "--object-path", "/org/gnome/Shell",
                        "--method", "org.gnome.Shell.Eval",
                        refresh_js.strip()
                    ],
                    capture_output=True,
                    timeout=5,
                    env=env
                )
                if result.returncode == 0:
                    time.sleep(0.5)  # 等待刷新完成
            except:
                pass
            
            # 方法3: 通过 dbus-send 发送刷新信号（GNOME Shell）
            try:
                subprocess.run(
                    [
                        "dbus-send",
                        "--session",
                        "--type=method_call",
                        "--dest=org.gnome.Shell",
                        "/org/gnome/Shell",
                        "org.gnome.Shell.Eval",
                        f"string:{refresh_js.strip()}"
                    ],
                    capture_output=True,
                    timeout=5,
                    env=env
                )
                time.sleep(0.5)
            except:
                pass
            
            # 方法4: 使用gsettings触发桌面刷新（通过修改其他属性触发）
            try:
                # 修改颜色渐变触发刷新
                subprocess.run(
                    ["gsettings", "set", "org.gnome.desktop.background", "color-shading-type", "solid"],
                    capture_output=True,
                    timeout=2,
                    env=env
                )
                time.sleep(0.2)
                subprocess.run(
                    ["gsettings", "set", "org.gnome.desktop.background", "picture-uri", file_uri],
                    capture_output=True,
                    timeout=2,
                    env=env
                )
            except:
                pass
            
            # 方法5: 发送D-Bus信号通知桌面环境刷新（通用方法）
            try:
                # 发送SettingsChanged信号
                subprocess.run(
                    [
                        "dbus-send",
                        "--session",
                        "--type=signal",
                        "/org/gnome/desktop/background",
                        "org.gtk.SettingsChanged",
                        "string:org.gnome.desktop.background",
                        "string:picture-uri"
                    ],
                    capture_output=True,
                    timeout=2,
                    env=env
                )
            except:
                pass
            
            # 方法6: UKUI特殊处理 - 尝试使用feh设置壁纸（如果可用）
            if "UKUI" in desktop_env:
                try:
                    # 检查feh是否可用
                    feh_check = subprocess.run(
                        ["which", "feh"],
                        capture_output=True,
                        timeout=1
                    )
                    if feh_check.returncode == 0:
                        # 使用feh设置壁纸（feh兼容性更好）
                        subprocess.run(
                            ["feh", "--bg-scale", abs_wallpaper_path],
                            capture_output=True,
                            timeout=3,
                            env=env
                        )
                        time.sleep(0.5)
                except:
                    pass
                
                # UKUI方法7: 强制刷新 - 多次设置并发送信号
                try:
                    # 再次设置确保生效
                    subprocess.run(
                        ["gsettings", "set", "org.gnome.desktop.background", "picture-uri", "''"],
                        capture_output=True,
                        timeout=2,
                        env=env
                    )
                    time.sleep(0.2)
                    subprocess.run(
                        ["gsettings", "set", "org.gnome.desktop.background", "picture-uri", file_uri],
                        capture_output=True,
                        timeout=2,
                        env=env
                    )
                    time.sleep(0.3)
                    
                    # 发送HUP信号给ukui-session（通知刷新）
                    ps_result = subprocess.run(
                        ["pgrep", "-f", "ukui-session"],
                        capture_output=True,
                        text=True,
                        timeout=2
                    )
                    if ps_result.returncode == 0:
                        pids = ps_result.stdout.strip().split('\n')
                        for pid in pids:
                            if pid.strip():
                                try:
                                    os.kill(int(pid.strip()), 1)  # SIGHUP = 1
                                except:
                                    pass
                    
                    # 也尝试发送信号给ukui-control-center-session
                    ps_result2 = subprocess.run(
                        ["pgrep", "-f", "ukui-control-center-session"],
                        capture_output=True,
                        text=True,
                        timeout=2
                    )
                    if ps_result2.returncode == 0:
                        pids = ps_result2.stdout.strip().split('\n')
                        for pid in pids:
                            if pid.strip():
                                try:
                                    os.kill(int(pid.strip()), 1)  # SIGHUP = 1
                                except:
                                    pass
                except Exception as e:
                    print(f"UKUI刷新信号发送失败: {e}")
            
            # 等待桌面环境刷新（重要：给足够的时间让壁纸生效）
            # UKUI可能需要更长的刷新时间
            refresh_wait_time = 3 if "UKUI" in desktop_env else 1
            time.sleep(refresh_wait_time)
            
            # 最终验证：检查设置是否真的生效
            final_check = subprocess.run(
                ["gsettings", "get", "org.gnome.desktop.background", "picture-uri"],
                capture_output=True,
                text=True,
                check=False,
                timeout=5,
                env=env
            )
            final_uri = final_check.stdout.strip().strip("'\"")
            
            # 检查URI是否匹配（忽略大小写和编码差异）
            uri_match = file_uri.lower() in final_uri.lower() or final_uri.lower() in file_uri.lower()
            
            # UKUI桌面环境特殊提示
            desktop_env = os.environ.get("XDG_CURRENT_DESKTOP", "").upper()
            ukui_note = ""
            if "UKUI" in desktop_env:
                ukui_note = "（注意：UKUI桌面环境可能需要手动刷新桌面或重启桌面组件才能看到效果）"
            
            if uri_match:
                return {
                    "status": "success",
                    "msg": f"壁纸修改成功（gsettings方案）：{abs_wallpaper_path}{ukui_note}",
                    "data": {
                        "wallpaper_path": abs_wallpaper_path,
                        "scale": scale,
                        "uri": final_uri,
                        "display": env.get("DISPLAY", "未设置"),
                        "desktop_env": desktop_env,
                        "note": ukui_note if ukui_note else None
                    }
                }
            else:
                return {
                    "status": "warning",
                    "msg": f"壁纸设置完成，但验证URI不匹配（可能是编码问题）{ukui_note}。设置的URI: {file_uri[:50]}... 当前URI: {final_uri[:50]}...",
                    "data": {
                        "expected_uri": file_uri,
                        "actual_uri": final_uri,
                        "display": env.get("DISPLAY", "未设置"),
                        "desktop_env": desktop_env,
                        "note": "如果桌面未更新，请尝试手动刷新桌面或重启桌面环境"
                    }
                }
        except subprocess.CalledProcessError as e:
            stderr_msg = e.stderr.strip() if e.stderr else ""
            stdout_msg = e.stdout.strip() if e.stdout else ""
            error_details = f"命令执行失败 (返回码: {e.returncode})"
            if stderr_msg:
                error_details += f"\n标准错误: {stderr_msg}"
            if stdout_msg:
                error_details += f"\n标准输出: {stdout_msg}"
            if not stderr_msg and not stdout_msg:
                error_details += f"\n错误信息: {str(e)}"
            return {
                "status": "error",
                "msg": f"壁纸修改失败：{error_details}",
                "data": {
                    "command": str(e.cmd) if hasattr(e, 'cmd') else "未知",
                    "returncode": e.returncode,
                    "display": env.get("DISPLAY", "未设置") if 'env' in locals() else "未设置"
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
                    "error_trace": error_trace,
                    "display": env.get("DISPLAY", "未设置") if 'env' in locals() else "未设置"
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
                                errors.append(f"{cmd[0]}: {result.stderr.decode() if result.stderr else result.stdout.decode()}")
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
                    error_msg = e.stderr.decode() if e.stderr else str(e)
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