#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单壁纸更换测试脚本（参考openKylin_agents实现方式）
适配麒麟操作系统（UKUI桌面环境）

使用方法：
    python3 test_wallpaper_simple.py /path/to/wallpaper.png
"""

import os
import sys
import subprocess
import time
import signal
import xml.etree.ElementTree as ET
from pathlib import Path


def get_desktop_environment():
    """
    获取当前桌面环境
    返回：小写的桌面环境标识（如ukui、gnome、mate）
    """
    desktop_env = os.environ.get('XDG_CURRENT_DESKTOP', '').lower()
    if 'ukui' in desktop_env:
        return 'ukui'
    elif 'gnome' in desktop_env:
        return 'gnome'
    elif 'mate' in desktop_env:
        return 'mate'
    else:
        return desktop_env if desktop_env else 'unknown'


def validate_wallpaper_file(wallpaper_path):
    """
    验证壁纸文件的有效性
    :param wallpaper_path: 壁纸文件路径
    :return: (是否有效, 绝对路径, 提示信息)
    """
    # 转换为绝对路径
    abs_path = Path(wallpaper_path).absolute()
    
    # 检查文件是否存在
    if not abs_path.exists():
        return False, None, f"错误：壁纸文件不存在 → {abs_path}"
    
    # 检查是否是文件
    if not abs_path.is_file():
        return False, None, f"错误：不是有效文件 → {abs_path}"
    
    # 检查文件格式
    supported_formats = ('.jpg', '.jpeg', '.png', '.bmp', '.gif')
    if abs_path.suffix.lower() not in supported_formats:
        return False, None, (
            f"错误：不支持的文件格式 → {abs_path.suffix}\n"
            f"支持格式：{supported_formats}"
        )
    
    return True, str(abs_path), f"文件验证通过 → {abs_path}"


def update_wallpaper_xml(wallpaper_abs_path, scale="zoom"):
    """
    更新UKUI的wallpaper.xml配置文件
    :param wallpaper_abs_path: 壁纸绝对路径
    :param scale: 缩放模式（zoom, scaled, stretched等）
    :return: (是否成功, 提示信息)
    """
    wallpaper_xml = os.path.expanduser("~/.config/ukui/wallpaper.xml")
    
    try:
        # 确保目录存在
        os.makedirs(os.path.dirname(wallpaper_xml), exist_ok=True)
        
        # 读取或创建XML文件
        if os.path.exists(wallpaper_xml):
            tree = ET.parse(wallpaper_xml)
            root = tree.getroot()
        else:
            root = ET.Element("wallpapers")
            tree = ET.ElementTree(root)
        
        # 查找目标壁纸
        target_wp = None
        all_wallpapers = list(root.findall('wallpaper'))
        
        for wp in all_wallpapers:
            filename_elem = wp.find('filename')
            if filename_elem is not None:
                filename_text = filename_elem.text or ""
                if wallpaper_abs_path == filename_text or wallpaper_abs_path in filename_text:
                    target_wp = wp
                    break
        
        # 如果没找到，创建新条目
        if target_wp is None:
            target_wp = ET.SubElement(root, 'wallpaper')
            target_wp.set('deleted', 'false')
            ET.SubElement(target_wp, 'artist').text = '(none)'
            ET.SubElement(target_wp, '_name').text = os.path.splitext(os.path.basename(wallpaper_abs_path))[0]
            ET.SubElement(target_wp, 'filename').text = wallpaper_abs_path
            ET.SubElement(target_wp, 'options').text = scale
            ET.SubElement(target_wp, 'pcolor').text = '#000000'
            ET.SubElement(target_wp, 'scolor').text = '#000000'
            ET.SubElement(target_wp, 'shade_type').text = 'solid'
        else:
            # 更新现有条目
            filename_elem = target_wp.find('filename')
            if filename_elem is not None:
                filename_elem.text = wallpaper_abs_path
            options_elem = target_wp.find('options')
            if options_elem is not None:
                options_elem.text = scale
        
        # 关键：将目标壁纸移到第一个位置
        all_wallpapers_after = list(root.findall('wallpaper'))
        if len(all_wallpapers_after) > 0 and all_wallpapers_after[0] != target_wp:
            root.remove(target_wp)
            root.insert(0, target_wp)
        
        # 保存XML文件
        tree.write(wallpaper_xml, encoding='UTF-8', xml_declaration=True)
        return True, "wallpaper.xml已更新，目标壁纸设为第一个"
        
    except Exception as e:
        return False, f"更新wallpaper.xml失败: {e}"


def refresh_ukui_desktop():
    """
    刷新UKUI桌面环境（多种方法）
    :return: 执行的刷新方法列表
    """
    refresh_methods = []
    env = os.environ.copy()
    env['DISPLAY'] = os.environ.get('DISPLAY', ':0')
    
    # 方法1: 重启ukui-settings-daemon
    try:
        result = subprocess.run(
            ['pgrep', '-f', 'ukui-settings-daemon'],
            stdout=subprocess.PIPE,
            text=True,
            timeout=2
        )
        if result.returncode == 0:
            pids = [pid.strip() for pid in result.stdout.strip().split('\n') if pid.strip()]
            for pid in pids:
                try:
                    os.kill(int(pid), signal.SIGHUP)
                except:
                    pass
            if pids:
                refresh_methods.append("重启ukui-settings-daemon")
                time.sleep(1)
    except:
        pass
    
    # 方法2: 切换active状态
    try:
        active_result = subprocess.run(
            ["gsettings", "get", "org.ukui.SettingsDaemon.plugins.background", "active"],
            capture_output=True,
            text=True,
            timeout=2,
            env=env
        )
        if active_result.returncode == 0:
            current_active = active_result.stdout.strip()
            new_active = "false" if current_active == "true" else "true"
            subprocess.run(
                ["gsettings", "set", "org.ukui.SettingsDaemon.plugins.background", "active", new_active],
                capture_output=True,
                timeout=2,
                env=env
            )
            time.sleep(0.3)
            subprocess.run(
                ["gsettings", "set", "org.ukui.SettingsDaemon.plugins.background", "active", "true"],
                capture_output=True,
                timeout=2,
                env=env
            )
            refresh_methods.append("切换active状态")
    except:
        pass
    
    # 方法3: 刷新ukui-session
    try:
        result = subprocess.run(
            ['pgrep', '-f', 'ukui-session'],
            stdout=subprocess.PIPE,
            text=True,
            timeout=2
        )
        if result.returncode == 0:
            pids = [pid.strip() for pid in result.stdout.strip().split('\n') if pid.strip()]
            for pid in pids:
                try:
                    os.kill(int(pid), signal.SIGHUP)
                except:
                    pass
            if pids:
                refresh_methods.append("刷新ukui-session")
                time.sleep(0.5)
    except:
        pass
    
    # 方法4: 强制重启peony-qt-desktop（使用TERM信号，systemd会自动重启）
    # 这是关键步骤，只有完全重启peony-qt-desktop才能让桌面真正刷新
    try:
        result = subprocess.run(
            ['pgrep', '-f', 'peony-qt-desktop'],
            stdout=subprocess.PIPE,
            text=True,
            timeout=2
        )
        if result.returncode == 0:
            pids = [pid.strip() for pid in result.stdout.strip().split('\n') if pid.strip()]
            original_pids = set(pids)
            
            # 发送TERM信号，让进程优雅退出（systemd会自动重启）
            for pid in pids:
                try:
                    os.kill(int(pid), signal.SIGTERM)  # SIGTERM = 15，比HUP更有效
                except:
                    pass
            
            if pids:
                refresh_methods.append("强制重启peony-qt-desktop")
                # 等待进程退出和重启（增加等待时间，确保完全重启）
                time.sleep(3)
                
                # 验证进程是否已重启（PID应该改变）
                result2 = subprocess.run(
                    ['pgrep', '-f', 'peony-qt-desktop'],
                    stdout=subprocess.PIPE,
                    text=True,
                    timeout=2
                )
                if result2.returncode == 0:
                    new_pids = set([pid.strip() for pid in result2.stdout.strip().split('\n') if pid.strip()])
                    if new_pids != original_pids:
                        print(f"  ✓ peony-qt-desktop已重启 (旧PID: {original_pids}, 新PID: {new_pids})")
                        # 再等待1秒，确保新进程完全加载配置
                        time.sleep(1)
                    else:
                        print(f"  ⚠️  peony-qt-desktop可能未重启 (PID未变)")
                else:
                    print(f"  ⚠️  重启后未找到peony-qt-desktop进程（可能正在重启中）")
                    time.sleep(2)  # 再等待2秒
    except Exception as e:
        print(f"  ⚠️  重启peony-qt-desktop失败: {e}")
        pass
    
    return refresh_methods


def change_wallpaper_ukui(wallpaper_abs_path):
    """
    更换UKUI桌面壁纸（完整实现，包括wallpaper.xml和刷新机制）
    :param wallpaper_abs_path: 壁纸绝对路径
    """
    import urllib.parse
    
    # 步骤1: 更新wallpaper.xml
    print("  正在更新wallpaper.xml...")
    xml_success, xml_msg = update_wallpaper_xml(wallpaper_abs_path, "zoom")
    if xml_success:
        print(f"  ✓ {xml_msg}")
    else:
        print(f"  ⚠️  {xml_msg}")
    
    # 步骤2: 设置多个gsettings schema
    encoded_path = urllib.parse.quote(wallpaper_abs_path, safe='')
    file_uri = f"file://{encoded_path}"
    
    env = os.environ.copy()
    env['DISPLAY'] = os.environ.get('DISPLAY', ':0')
    
    # UKUI可能的schema列表
    ukui_schemas = [
        # 标准GNOME壁纸设置（必须）
        ("org.gnome.desktop.background", "picture-uri", file_uri),
        # UKUI锁屏壁纸
        ("org.ukui.screensaver", "background", wallpaper_abs_path),
        # UKUI屏保图片
        ("org.ukui.screensaver-default", "background-path", wallpaper_abs_path),
        # MATE桌面环境（如果支持）
        ("org.mate.background", "picture-filename", wallpaper_abs_path),
    ]
    
    success_count = 0
    for schema, key, value in ukui_schemas:
        try:
            # 检查schema是否存在
            check_result = subprocess.run(
                ["gsettings", "list-keys", schema],
                capture_output=True,
                text=True,
                timeout=2,
                env=env
            )
            if check_result.returncode == 0 and key in check_result.stdout:
                # Schema存在且包含key，尝试设置
                subprocess.run(
                    ["gsettings", "set", schema, key, value],
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=5,
                    env=env
                )
                print(f"  ✓ 成功设置schema: {schema}.{key}")
                success_count += 1
        except:
            pass
    
    if success_count == 0:
        return False, "错误：未找到可用的UKUI壁纸配置项"
    
    # 步骤3: 刷新桌面环境
    print("\n【刷新步骤】正在刷新桌面...")
    refresh_methods = refresh_ukui_desktop()
    if refresh_methods:
        print(f"  ✓ 已执行刷新方法: {', '.join(refresh_methods)}")
    else:
        print("  ⚠️  未找到可用的刷新方法")
    
    return True, f"UKUI壁纸更换成功（使用 org.gnome.desktop.background, org.ukui.screensaver, org.ukui.screensaver-default，已更新wallpaper.xml）"


def change_wallpaper_gnome(wallpaper_abs_path):
    """
    更换GNOME桌面壁纸（参考openKylin_agents的简单实现方式）
    :param wallpaper_abs_path: 壁纸绝对路径
    """
    import urllib.parse
    # GNOME需要使用file://协议前缀
    encoded_path = urllib.parse.quote(wallpaper_abs_path, safe='')
    wallpaper_uri = f"file://{encoded_path}"
    
    cmd = [
        'gsettings', 'set',
        'org.gnome.desktop.background',
        'picture-uri',
        wallpaper_uri
    ]
    
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10,
            check=True
        )
        return True, "GNOME壁纸更换成功"
    except subprocess.CalledProcessError as e:
        return False, f"GNOME壁纸更换失败：{e.stderr.strip()}"
    except Exception as e:
        return False, f"未知错误：{str(e)}"


def change_wallpaper_mate(wallpaper_abs_path):
    """
    更换MATE桌面壁纸（openKylin_agents的原始实现方式）
    :param wallpaper_abs_path: 壁纸绝对路径
    """
    cmd = [
        'gsettings', 'set',
        'org.mate.background',
        'picture-filename',
        wallpaper_abs_path
    ]
    
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10,
            check=True
        )
        return True, "MATE壁纸更换成功"
    except subprocess.CalledProcessError as e:
        return False, f"MATE壁纸更换失败：{e.stderr.strip()}"
    except Exception as e:
        return False, f"未知错误：{str(e)}"


def main():
    """主函数"""
    print("=" * 60)
    print("壁纸更换测试脚本（参考openKylin_agents实现）")
    print("=" * 60)
    
    # 检查命令行参数
    if len(sys.argv) != 2:
        print("\n使用方法：")
        print(f"  python3 {sys.argv[0]} <壁纸文件路径>")
        print("\n示例：")
        print(f"  python3 {sys.argv[0]} /home/user/Pictures/wallpaper.png")
        print(f"  python3 {sys.argv[0]} ~/Desktop/test.jpg")
        print("\n支持的格式：jpg, jpeg, png, bmp, gif")
        print("=" * 60)
        sys.exit(1)
    
    wallpaper_path = sys.argv[1]
    
    # 1. 验证壁纸文件
    print("\n【步骤 1/3】验证壁纸文件...")
    valid, abs_path, validate_msg = validate_wallpaper_file(wallpaper_path)
    print(f"  {validate_msg}")
    
    if not valid:
        print("\n❌ 文件验证失败，退出")
        sys.exit(1)
    
    # 2. 检测桌面环境
    print("\n【步骤 2/3】检测桌面环境...")
    desktop_env = get_desktop_environment()
    print(f"  检测到桌面环境：{desktop_env}")
    
    if desktop_env == 'unknown':
        print("  ⚠️  警告：无法识别桌面环境，将尝试UKUI方式...")
        desktop_env = 'ukui'
    
    # 3. 更换壁纸
    print("\n【步骤 3/3】开始更换壁纸...")
    print(f"  壁纸路径：{abs_path}")
    print(f"  桌面环境：{desktop_env}")
    
    success = False
    result_msg = ""
    
    if desktop_env == 'ukui':
        success, result_msg = change_wallpaper_ukui(abs_path)
    elif desktop_env == 'gnome':
        success, result_msg = change_wallpaper_gnome(abs_path)
    elif desktop_env == 'mate':
        success, result_msg = change_wallpaper_mate(abs_path)
    else:
        # 未知环境，尝试所有方式
        print("  尝试UKUI方式...")
        success, result_msg = change_wallpaper_ukui(abs_path)
        if not success:
            print("  尝试GNOME方式...")
            success, result_msg = change_wallpaper_gnome(abs_path)
        if not success:
            print("  尝试MATE方式...")
            success, result_msg = change_wallpaper_mate(abs_path)
    
    # 输出结果
    print("\n" + "=" * 60)
    if success:
        print("✅ 壁纸更换成功！")
        print(f"  {result_msg}")
        print("\n提示：如果桌面壁纸没有立即更新，请尝试：")
        print("  1. 手动刷新桌面（按F5或右键刷新）")
        print("  2. 检查wallpaper.xml第一个条目是否正确：")
        print("     head -5 ~/.config/ukui/wallpaper.xml")
        print("  3. 检查gsettings设置是否生效：")
        print("     gsettings get org.gnome.desktop.background picture-uri")
        print("  4. 如果仍未更新，尝试重启ukui-settings-daemon：")
        print("     killall -HUP ukui-settings-daemon")
    else:
        print("❌ 壁纸更换失败！")
        print(f"  {result_msg}")
        print("\n排查建议：")
        print("  1. 检查gsettings是否可用：gsettings --version")
        print("  2. 检查桌面环境：echo $XDG_CURRENT_DESKTOP")
        print("  3. 尝试手动设置：")
        print("     gsettings set org.gnome.desktop.background picture-uri 'file:///path/to/image.png'")
    print("=" * 60)
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n程序被用户中断")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n程序异常：{str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

