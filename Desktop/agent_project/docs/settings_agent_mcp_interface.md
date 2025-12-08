# SettingsAgent MCP接口规范文档
## 文档说明
本文档定义SettingsAgent的MCP接口规范，包含接口功能、入参出参、调用示例、环境依赖等核心信息，适配Ubuntu 20.04+/GNOME桌面环境（兼容VMware/VirtualBox虚拟机）。

## 一、核心能力
SettingsAgent聚焦Ubuntu系统设置操作，提供标准化MCP接口，核心能力：
1. 桌面壁纸修改（基于feh工具，解决虚拟机gsettings权限问题）；
2. 系统音量调整（基于amixer命令，无图形化会话依赖）。

## 二、接口详细规范
### 2.1 接口1：change_wallpaper（修改桌面壁纸）
#### 功能描述
修改Ubuntu桌面壁纸，支持5种缩放方式，自动校验文件合法性，兼容虚拟机环境。
#### 入参规范
| 参数名         | 数据类型 | 是否必填 | 默认值 | 取值范围/说明                                                                 |
|----------------|----------|----------|--------|------------------------------------------------------------------------------|
| wallpaper_path | str      | 是       | -      | 壁纸文件绝对路径；支持格式：.jpg/.jpeg/.png/.gif/.bmp                        |
| scale          | str      | 否       | fill   | 缩放方式：fill（填充）、stretch（拉伸）、center（居中）、tile（平铺）、zoom（缩放） |

#### 出参规范
| 字段名  | 数据类型 | 说明                                                                 |
|---------|----------|----------------------------------------------------------------------|
| status  | str      | 调用状态：success（成功）、error（失败）|
| msg     | str      | 结果描述：成功返回壁纸路径+缩放方式；失败返回具体错误原因（如文件不存在、入参非法） |

#### 调用示例
- 成功返回示例：
```json
{
  "status": "success",
  "msg": "壁纸修改成功！路径：/home/user1/Desktop/test_wallpaper.jpg，缩放方式：fill（feh命令：feh --bg-fill /home/user1/Desktop/test_wallpaper.jpg）"
}
- 失败返回示例（文件不存在）：：
```json
{
  "status": "error",
  "msg": "壁纸文件不存在：/home/user1/Desktop/non_exist.jpg"
}
