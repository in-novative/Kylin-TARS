# FileAgent 说明文档
## 功能简介
- 基础能力：文件编码检测/读取/转换（支持GBK/UTF-8/GB2312等）
- MCP接口：search_file（文件搜索）、move_to_trash（文件移至回收站）

## 环境要求
- Python 3.10+
- 依赖包：chardet（编码检测）、shutil/os（内置库，无需额外安装）
- 运行环境：Ubuntu虚拟机（回收站路径适配Ubuntu）

## 快速运行
1. 激活虚拟环境：source agent_env/bin/activate
2. 运行核心逻辑测试：python src/file_agent_logic.py
3. MCP对接：修改src/file_agent_mcp.py中的MCP框架代码，执行python src/file_agent_mcp.py

## 后续对接
- 等待团队MCP Server开发完成后，替换src/file_agent_mcp.py中的模板代码即可完成接口注册

等团队的 MCP Server 开发完成后，你只需要：
替换模板中的 MCP 框架代码：把MCPServer/MCPRequest/MCPResponse替换为团队实际的类；
调整接口注册逻辑：按团队 MCP 框架的文档，修改register_handler和start的实现；
无需改核心逻辑：file_agent_logic.py里的search_file/move_to_trash完全不用动。

# SettingsAgent MCP接口规范文档
## 1. 功能简介
SettingsAgent 主要负责Ubuntu系统设置类操作，提供标准化MCP接口，支持桌面壁纸修改、系统音量调整，所有接口均适配Ubuntu 20.04+/GNOME桌面环境，兼容虚拟机场景。

## 2. 接口列表
### 2.1 change_wallpaper（修改桌面壁纸）
#### 功能描述
修改Ubuntu桌面壁纸，支持多种缩放方式，基于feh工具实现（虚拟机兼容性优于gsettings）。
#### 入参说明
| 参数名         | 类型    | 是否必填 | 默认值 | 说明                                                                 |
|----------------|---------|----------|--------|----------------------------------------------------------------------|
| wallpaper_path | str     | 是       | -      | 壁纸文件绝对路径（支持.jpg/.jpeg/.png/.gif/.bmp格式）|
| scale          | str     | 否       | fill   | 缩放方式，可选值：fill（填充）、stretch（拉伸）、center（居中）、tile（平铺）、zoom（缩放） |

#### 出参说明
| 字段名  | 类型    | 说明                                                                 |
|---------|---------|----------------------------------------------------------------------|
| status  | str     | 接口调用状态，success（成功）/error（失败）|
| msg     | str     | 结果描述（成功：返回壁纸路径+缩放方式；失败：返回具体错误原因）|

#### 调用示例
- 成功返回：
```json
{
  "status": "success",
  "msg": "壁纸修改成功！路径：/home/user1/Desktop/test_wallpaper.jpg，缩放方式：fill（feh命令：feh --bg-fill /home/user1/Desktop/test_wallpaper.jpg）"
}