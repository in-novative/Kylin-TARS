#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
麒麟(Kylin)操作系统更换桌面壁纸Python程序
支持环境：UKUI（主流）、GNOME桌面
使用要求：壁纸文件为绝对路径，支持jpg/png/bmp/gif格式
"""

import os
import sys
import subprocess
from pathlib import Path


def get_desktop_environment():
    """
    获取当前桌面环境
    返回：小写的桌面环境标识（如ukui、gnome）
    """
    desktop_env = os.environ.get('XDG_CURRENT_DESKTOP', '').lower()
    # 兼容不同的标识格式（如UKUI可能返回UKUI/ukui）
    if 'ukui' in desktop_env:
        return 'ukui'
    elif 'gnome' in desktop_env:
        return 'gnome'
    else:
        return desktop_env


def validate_wallpaper_file(wallpaper_path):
    """
    验证壁纸文件的有效性
    :param wallpaper_path: 壁纸文件路径（建议绝对路径）
    :return: (是否有效, 提示信息)
    """
    # 转换为绝对路径
    abs_path = Path(wallpaper_path).absolute()
    
    # 检查文件是否存在
    if not abs_path.exists():
        return False, f"错误：壁纸文件不存在 → {abs_path}"
    
    # 检查是否是文件
    if not abs_path.is_file():
        return False, f"错误：不是有效文件 → {abs_path}"
    
    # 检查文件格式
    supported_formats = ('.jpg', '.jpeg', '.png', '.bmp', '.gif')
    if abs_path.suffix.lower() not in supported_formats:
        return False, (
            f"错误：不支持的文件格式 → {abs_path.suffix}\n"
            f"支持格式：{supported_formats}"
        )
    
    return True, f"文件验证通过 → {abs_path}"


def execute_command(cmd):
    """
    执行系统命令并捕获输出
    :param cmd: 命令列表（如['gsettings', 'set', ...]）
    :return: (是否成功, 输出/错误信息)
    """
    try:
        # 执行命令，捕获stdout和stderr
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding='utf-8',
            check=True
        )
        return True, f"命令执行成功：{' '.join(cmd)}\n输出：{result.stdout.strip()}"
    except subprocess.CalledProcessError as e:
        return False, (
            f"命令执行失败：{' '.join(cmd)}\n"
            f"错误码：{e.returncode}\n"
            f"错误信息：{e.stderr.strip()}"
        )
    except Exception as e:
        return False, f"未知错误：{str(e)}"


def change_ukui_wallpaper(wallpaper_abs_path):
    """
    更换UKUI桌面壁纸
    :param wallpaper_abs_path: 壁纸绝对路径
    """
    # UKUI不同版本的schema可能不同，优先尝试主流版本
    schemas = [
        # 主流UKUI版本（如麒麟V10）
        'org.ukui.control-center.personalization',
        # 兼容旧版本
        'org.ukui.desktop.background'
    ]
    
    for schema in schemas:
        cmd = [
            'gsettings',
            'set',
            schema,
            'wallpaper-path',
            wallpaper_abs_path
        ]
        success, msg = execute_command(cmd)
        if success:
            return True, f"UKUI壁纸更换成功\n{msg}"
        # 若schema不存在，尝试下一个
        if 'No such schema' in msg:
            continue
        else:
            return False, f"UKUI壁纸更换失败\n{msg}"
    
    return False, "错误：未找到可用的UKUI壁纸配置项"


def change_gnome_wallpaper(wallpaper_abs_path):
    """
    更换GNOME桌面壁纸
    :param wallpaper_abs_path: 壁纸绝对路径
    """
    # GNOME需要使用file://协议前缀
    wallpaper_uri = f"file://{wallpaper_abs_path}"
    
    # 设置普通模式壁纸
    cmd_light = [
        'gsettings',
        'set',
        'org.gnome.desktop.background',
        'picture-uri',
        wallpaper_uri
    ]
    success_light, msg_light = execute_command(cmd_light)
    
    # 设置深色模式壁纸（可选，增强兼容性）
    cmd_dark = [
        'gsettings',
        'set',
        'org.gnome.desktop.background',
        'picture-uri-dark',
        wallpaper_uri
    ]
    success_dark, msg_dark = execute_command(cmd_dark)
    
    if success_light:
        return True, (
            f"GNOME壁纸更换成功\n"
            f"普通模式：{msg_light}\n"
            f"深色模式：{msg_dark if success_dark else '深色模式配置忽略（非必需）'}"
        )
    else:
        return False, f"GNOME壁纸更换失败\n{msg_light}"


def main():
    """主函数"""
    # 检查命令行参数
    if len(sys.argv) != 2:
        print("="*50)
        print("使用方法：")
        print(f"  python3 {sys.argv[0]} 壁纸文件绝对路径")
        print("示例：")
        print(f"  python3 {sys.argv[0]} /home/user/Pictures/wallpaper.png")
        print("="*50)
        sys.exit(1)
    
    # 获取用户输入的壁纸路径
    wallpaper_path = sys.argv[1]
    
    # 1. 验证壁纸文件
    valid, validate_msg = validate_wallpaper_file(wallpaper_path)
    print(f"【1/3】文件验证：{validate_msg}")
    if not valid:
        sys.exit(1)
    wallpaper_abs_path = str(Path(wallpaper_path).absolute())
    
    # 2. 获取桌面环境
    desktop_env = get_desktop_environment()
    print(f"【2/3】检测到桌面环境：{desktop_env}")
    if desktop_env not in ['ukui', 'gnome']:
        print(f"警告：未适配的桌面环境 → {desktop_env}，尝试用UKUI方式兼容...")
        desktop_env = 'ukui'  # 降级到UKUI兼容模式
    
    # 3. 更换壁纸
    print("【3/3】开始更换壁纸...")
    if desktop_env == 'ukui':
        success, result_msg = change_ukui_wallpaper(wallpaper_abs_path)
    elif desktop_env == 'gnome':
        success, result_msg = change_gnome_wallpaper(wallpaper_abs_path)
    else:
        success = False
        result_msg = f"不支持的桌面环境：{desktop_env}"
    
    # 输出结果
    print("="*50)
    if success:
        print("✅ 壁纸更换成功！")
        print(result_msg)
    else:
        print("❌ 壁纸更换失败！")
        print(result_msg)
        sys.exit(1)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n程序被用户中断")
        sys.exit(0)
    except Exception as e:
        print(f"\n程序异常：{str(e)}")
        sys.exit(1)
