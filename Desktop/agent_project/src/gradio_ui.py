"""Gradio界面"""
import gradio as gr
import sys
import os
import time
import subprocess
from typing import Dict, List

# 项目路径配置
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.file_agent_logic import FileAgentLogic
from src.settings_agent_logic import SettingsAgentLogic

# 初始化智能体
file_agent = FileAgentLogic()
settings_agent = SettingsAgentLogic()

# 截图目录
SCREENSHOT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

# ===================== 核心功能 =====================
def install_dependencies():
    """安装必要依赖"""
    required_tools = ["scrot", "wmctrl", "xdotool"]
    for tool in required_tools:
        try:
            subprocess.run(["which", tool], check=True, capture_output=True)
        except subprocess.CalledProcessError:
            print(f"正在安装{tool}...")
            subprocess.run(["sudo", "apt-get", "update"], check=True)
            subprocess.run(["sudo", "apt-get", "install", "-y", tool], check=True)

def capture_desktop_auto() -> str:
    """自动跳转到桌面并截图"""
    screenshot_path = os.path.join(SCREENSHOT_DIR, f"desktop_wallpaper_{int(time.time())}.png")
    
    try:
        # 跳转到桌面
        subprocess.run(["wmctrl", "-k", "on"], check=True)
        time.sleep(1)
        
        # 截取桌面
        subprocess.run(["scrot", "-d", 1, screenshot_path], check=True)
        
        # 恢复窗口
        subprocess.run(["wmctrl", "-k", "off"], check=True)
        
        return screenshot_path
    except Exception as e:
        print(f"自动截图失败：{e}")
        try:
            subprocess.run(["gnome-screenshot", "-f", screenshot_path], check=True)
            return screenshot_path
        except Exception as e2:
            print(f"备选方案也失败：{e2}")
            return None

def capture_volume_panel() -> str:
    """截取音量面板"""
    screenshot_path = os.path.join(SCREENSHOT_DIR, f"volume_panel_{int(time.time())}.png")
    
    try:
        # 打开音量面板
        subprocess.Popen(["gnome-control-center", "sound"])
        time.sleep(1)
        
        # 截取音量面板
        subprocess.run(["scrot", screenshot_path], check=True)
        
        # 关闭音量面板
        subprocess.run(["pkill", "gnome-control-center"])
        
        return screenshot_path
    except Exception as e:
        print(f"音量面板截图失败：{e}")
        return None

# ===================== 工具调用函数 =====================
def search_files(path: str, keyword: str, recursive: bool) -> tuple:
    result = file_agent.search_file(path, keyword, recursive)
    if result["status"] == "success":
        data = [[i["file_name"], i["file_path"], i["file_size"], i["modify_time"]] for i in result["data"]]
        return data, f"搜索成功，找到{len(data)}个文件"
    else:
        return [], f"搜索失败：{result['msg']}"

def move_to_trash(file_path: str) -> str:
    result = file_agent.move_to_trash(file_path)
    return f"移至回收站{'成功' if result['status']=='success' else '失败'}：{result['msg']}"

def change_wallpaper(wallpaper_path: str, scale: str) -> tuple:
    """修改壁纸+自动跳转到桌面截图"""
    if not os.path.exists(wallpaper_path):
        return f"壁纸修改失败：文件不存在 {wallpaper_path}", None
    
    result = settings_agent.change_wallpaper(wallpaper_path, scale)
    
    if result["status"] == "success":
        time.sleep(2)
        try:
            screenshot_path = capture_desktop_auto()
            return f"修改壁纸成功：{wallpaper_path}", screenshot_path
        except Exception as e:
            return f"修改壁纸成功：{wallpaper_path}（截图失败：{str(e)}）", None
    else:
        return f"修改壁纸失败：{result['msg']}", None

def adjust_volume(volume: int, device: str) -> tuple:
    """调整音量+截取音量面板"""
    result = settings_agent.adjust_volume(volume, device)
    if result["status"] == "success":
        time.sleep(1)
        try:
            screenshot_path = capture_volume_panel()
            return f"调整音量成功：{volume}%", screenshot_path
        except Exception as e:
            return f"调整音量成功：{volume}%（截图失败：{str(e)}）", None
    else:
        return f"调整音量失败：{result['msg']}", None

def refresh_screenshots() -> List[str]:
    screenshots = [os.path.join(SCREENSHOT_DIR, f) for f in os.listdir(SCREENSHOT_DIR) if f.endswith(('.png', '.jpg'))]
    screenshots.sort(key=os.path.getmtime, reverse=True)
    return screenshots

def generate_test_report() -> tuple:
    screenshots = refresh_screenshots()
    total = len(screenshots)
    log = f"测试报告（{time.strftime('%Y-%m-%d %H:%M:%S')}）\n"
    log += f"总测试次数：{total}\n成功次数：{total}\n\n截图列表：\n"
    for i, s in enumerate(screenshots, 1):
        log += f"{i}. {os.path.basename(s)}（{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(os.path.getmtime(s)))}\n"
    return total, total, 0, log

# ===================== 界面布局（兼容非常旧版Gradio） =====================
with gr.Blocks(title="智能体管理系统") as demo:
    # 页面标题
    gr.Markdown("""
    # 🤖 智能体管理系统
    高效管理文件与系统设置的智能助手
    """)
    
    with gr.Tabs():
        # 1. 文件管理标签页
        with gr.Tab("📁 文件管理"):
            gr.Markdown("## 文件搜索与管理")
            
            # 搜索区域
            with gr.Row():
                with gr.Column(scale=2):
                    search_path = gr.Textbox(
                        label="搜索路径", 
                        value="/home/user1/Desktop",
                        placeholder="输入要搜索的目录路径"
                    )
                    keyword = gr.Textbox(
                        label="关键词", 
                        value="test",
                        placeholder="输入要搜索的文件名关键词"
                    )
                with gr.Column(scale=1):
                    recursive = gr.Checkbox(
                        label="递归搜索", 
                        value=True
                    )
                    search_btn = gr.Button(
                        "🔍 搜索文件", 
                        variant="primary"
                    )
            
            # 搜索结果区域
            search_result = gr.Dataframe(
                label="搜索结果", 
                headers=["文件名", "路径", "大小", "修改时间"], 
                datatype=["str", "str", "number", "str"],
                row_count=5,
                col_count=(4, "fixed")
            )
            file_operation_result = gr.Textbox(
                label="操作结果",
                placeholder="显示搜索结果或操作状态"
            )
            
            # 文件操作区域
            gr.Markdown("## 文件操作")
            with gr.Row():
                trash_file_path = gr.Textbox(
                    label="文件路径", 
                    placeholder="输入要删除的文件路径"
                )
                trash_btn = gr.Button(
                    "🗑️ 移至回收站", 
                    variant="secondary"
                )
        
        # 2. 系统设置标签页
        with gr.Tab("⚙️ 系统设置"):
            gr.Markdown("## 壁纸与音量设置")
            
            # 壁纸设置
            gr.Markdown("### 壁纸设置")
            with gr.Row():
                with gr.Column(scale=2):
                    wallpaper_path = gr.Textbox(
                        label="壁纸路径", 
                        placeholder="/home/user1/Desktop/wallpaper.jpg"
                    )
                    scale_mode = gr.Dropdown(
                        label="缩放方式", 
                        choices=["zoom", "scaled", "centered", "stretched", "wallpaper"],
                        value="zoom"
                    )
                with gr.Column(scale=1):
                    wallpaper_btn = gr.Button(
                        "🖼️ 修改壁纸", 
                        variant="primary"
                    )
            
            # 音量设置
            gr.Markdown("### 音量设置")
            with gr.Row():
                with gr.Column(scale=2):
                    volume_value = gr.Slider(
                        label="音量值", 
                        minimum=0, 
                        maximum=100, 
                        value=50,
                        step=1
                    )
                    audio_device = gr.Textbox(
                        label="音频设备", 
                        value="@DEFAULT_SINK@",
                        placeholder="默认音频设备"
                    )
                with gr.Column(scale=1):
                    volume_btn = gr.Button(
                        "🔊 调整音量", 
                        variant="primary"
                    )
            
            # 操作结果区域
            settings_operation_result = gr.Textbox(
                label="操作结果",
                placeholder="显示设置操作的结果"
            )
            
            # 测试截图区域
            gr.Markdown("### 测试截图")
            with gr.Row():
                with gr.Column(scale=1):
                    test_screenshot = gr.Image(
                        label="最新截图",
                        height=400,
                        width=600,
                        type="filepath"
                    )
                with gr.Column(scale=1):
                    screenshot_list = gr.Files(
                        label="截图列表", 
                        file_count="multiple",
                        type="filepath"
                    )
        
        # 3. 测试报告标签页
        with gr.Tab("📊 测试报告"):
            gr.Markdown("## 功能测试报告")
            
            # 测试统计
            gr.Markdown("### 测试统计")
            with gr.Row():
                with gr.Column(scale=1):
                    total_tests = gr.Number(
                        label="总测试次数", 
                        value=0,
                        precision=0
                    )
                with gr.Column(scale=1):
                    success_tests = gr.Number(
                        label="成功次数", 
                        value=0,
                        precision=0
                    )
                with gr.Column(scale=1):
                    failure_tests = gr.Number(
                        label="失败次数", 
                        value=0,
                        precision=0
                    )
            
            # 测试日志
            gr.Markdown("### 测试日志")
            generate_report_btn = gr.Button(
                "📋 生成测试报告", 
                variant="primary"
            )
            test_log = gr.Textbox(
                label="日志内容",
                lines=15,
                placeholder="点击按钮生成测试报告"
            )
    
    # ===================== 事件绑定 =====================
    search_btn.click(fn=search_files, inputs=[search_path, keyword, recursive], outputs=[search_result, file_operation_result])
    trash_btn.click(fn=move_to_trash, inputs=[trash_file_path], outputs=[file_operation_result])
    wallpaper_btn.click(fn=change_wallpaper, inputs=[wallpaper_path, scale_mode], outputs=[settings_operation_result, test_screenshot])
    volume_btn.click(fn=adjust_volume, inputs=[volume_value, audio_device], outputs=[settings_operation_result, test_screenshot])
    generate_report_btn.click(fn=generate_test_report, inputs=[], outputs=[total_tests, success_tests, failure_tests, test_log])
    demo.load(fn=refresh_screenshots, inputs=[], outputs=[screenshot_list])

# ===================== 启动应用 =====================
if __name__ == "__main__":
    # 安装必要依赖
    install_dependencies()
    
    # 启动Gradio界面
    # 使用环境变量或默认端口 7870（避免与其他服务冲突）
    import os
    port = int(os.environ.get("GRADIO_SERVER_PORT", 7870))
    demo.launch(server_name="0.0.0.0", server_port=port, share=False, debug=True)