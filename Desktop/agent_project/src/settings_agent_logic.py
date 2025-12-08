"""SettingsAgent核心逻辑（修复缩放模式警告）"""
import subprocess
import os
from typing import Dict

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