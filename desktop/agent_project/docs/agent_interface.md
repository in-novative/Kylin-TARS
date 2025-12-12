# 智能体接口文档（Day 2+Day5）

## FileAgent
### 1. search_file
- 功能：按关键词递归/非递归搜索文件
- 入参：search_path(str)、keyword(str)、recursive(bool, 默认True)
- 出参：status(success/error)、msg(描述)、data(文件列表)

### 2. move_to_trash
- 功能：将文件/目录移至Linux回收站
- 入参：file_path(str)
- 出参：status(success/error)、msg(描述)、data(路径信息)


## SettingsAgent
### 1. change_wallpaper
- 功能：修改Linux桌面壁纸（依赖feh）
- 入参：wallpaper_path(str)、scale(str, 默认fill)
- 出参：status(success/error)、msg(描述)、data(壁纸信息)

### 2. adjust_volume
- 功能：调整系统音量（依赖pactl）
- 入参：volume(int, 0-100)、device(str, 默认@DEFAULT_SINK@)
- 出参：status(success/error)、msg(描述)、data(音量信息)


## Gradio界面访问说明
### 1. 运行方式
在项目根目录下，激活虚拟环境后执行：
```bash
# 激活虚拟环境（已激活可跳过）
source agent_env/bin/activate
# 启动Gradio界面
python src/gradio_ui.py