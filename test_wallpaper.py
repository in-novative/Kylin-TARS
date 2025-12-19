#!/usr/bin/env python3
"""
壁纸更换功能测试脚本

用于测试SettingsAgent的壁纸更换功能是否正常工作
"""

import sys
import os

# 添加项目路径
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "desktop", "agent_project", "src"))

from settings_agent_logic import SettingsAgentLogic

def test_wallpaper_change(wallpaper_path: str, scale: str = "zoom"):
    """测试壁纸更换功能"""
    print("=" * 70)
    print("壁纸更换功能测试")
    print("=" * 70)
    print(f"测试文件: {wallpaper_path}")
    print(f"缩放模式: {scale}")
    print()
    
    # 检查文件是否存在
    if not os.path.exists(wallpaper_path):
        print(f"❌ 错误: 文件不存在 - {wallpaper_path}")
        return False
    
    print(f"✓ 文件存在: {wallpaper_path}")
    print(f"  文件大小: {os.path.getsize(wallpaper_path)} 字节")
    print()
    
    # 检查文件格式
    supported_formats = ['.jpg', '.jpeg', '.png', '.bmp', '.svg']
    file_ext = os.path.splitext(wallpaper_path)[1].lower()
    if file_ext not in supported_formats:
        print(f"⚠️  警告: 文件格式可能不支持 - {file_ext}")
        print(f"  支持的格式: {', '.join(supported_formats)}")
    else:
        print(f"✓ 文件格式支持: {file_ext}")
    print()
    
    # 检查环境变量
    print("环境检查:")
    display = os.environ.get("DISPLAY")
    if display:
        print(f"✓ DISPLAY: {display}")
    else:
        print("⚠️  DISPLAY 未设置")
    print()
    
    # 检查必要工具
    print("工具检查:")
    tools = {
        "gsettings": "gsettings",
        "gdbus": "gdbus",
        "dbus-send": "dbus-send"
    }
    
    import subprocess
    for tool_name, tool_cmd in tools.items():
        try:
            result = subprocess.run(
                ["which", tool_cmd],
                capture_output=True,
                timeout=2
            )
            if result.returncode == 0:
                print(f"✓ {tool_name}: {result.stdout.decode().strip()}")
            else:
                print(f"✗ {tool_name}: 未找到")
        except:
            print(f"✗ {tool_name}: 检查失败")
    print()
    
    # 测试壁纸更换
    print("开始测试壁纸更换...")
    print("-" * 70)
    
    try:
        agent = SettingsAgentLogic()
        result = agent.change_wallpaper(wallpaper_path, scale)
        
        print("\n测试结果:")
        print("-" * 70)
        print(f"状态: {result['status']}")
        print(f"消息: {result['msg']}")
        
        if result.get('data'):
            print("\n详细信息:")
            for key, value in result['data'].items():
                print(f"  {key}: {value}")
        
        if result['status'] == 'success':
            print("\n✓ 壁纸更换成功！")
            
            # 验证设置
            print("\n验证设置...")
            try:
                verify_result = subprocess.run(
                    ["gsettings", "get", "org.gnome.desktop.background", "picture-uri"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if verify_result.returncode == 0:
                    current_uri = verify_result.stdout.strip().strip("'\"")
                    print(f"当前壁纸URI: {current_uri}")
                    
                    # 检查缩放模式
                    scale_result = subprocess.run(
                        ["gsettings", "get", "org.gnome.desktop.background", "picture-options"],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if scale_result.returncode == 0:
                        current_scale = scale_result.stdout.strip().strip("'\"")
                        print(f"当前缩放模式: {current_scale}")
            except Exception as e:
                print(f"⚠️  验证失败: {e}")
            
            return True
        else:
            print("\n✗ 壁纸更换失败！")
            if result.get('data'):
                print("\n错误详情:")
                for key, value in result['data'].items():
                    if key == 'error_trace':
                        print(f"\n{key}:")
                        print(value)
                    else:
                        print(f"  {key}: {value}")
            return False
            
    except Exception as e:
        import traceback
        print(f"\n✗ 测试异常: {str(e)}")
        print("\n异常堆栈:")
        print(traceback.format_exc())
        return False

if __name__ == "__main__":
    # 默认测试文件
    default_wallpaper = "/data/usershare/Kylin-TARS/桌面测试.png"
    
    if len(sys.argv) > 1:
        wallpaper_path = sys.argv[1]
    else:
        wallpaper_path = default_wallpaper
    
    scale = sys.argv[2] if len(sys.argv) > 2 else "zoom"
    
    success = test_wallpaper_change(wallpaper_path, scale)
    
    print("\n" + "=" * 70)
    if success:
        print("测试完成: ✓ 成功")
    else:
        print("测试完成: ✗ 失败")
    print("=" * 70)
    
    sys.exit(0 if success else 1)

