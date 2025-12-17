# run_KL.sh 使用说明

## 问题分析

### 原 `run.sh` 服务突然中断的可能原因：

1. **`set -e` 导致立即退出**
   - 原脚本使用了 `set -e`，任何命令返回非零退出码都会立即终止脚本
   - 如果 MCP Server 启动失败，脚本会立即退出

2. **MCP Server 启动失败**
   - MCP Server 启动检查过于严格（3秒后检查进程）
   - 如果启动时间超过3秒，会被误判为失败

3. **缺少错误日志**
   - 没有详细的错误输出，难以诊断问题
   - 错误信息被隐藏，无法定位问题

4. **环境变量传递问题**
   - 在 `dbus-run-session` 中环境变量可能没有正确传递
   - 特别是图形界面相关的环境变量（DISPLAY, WAYLAND_DISPLAY）

5. **Python 模块导入错误**
   - 缺少必要的 Python 模块（如 dbus, gradio）
   - PyGObject 路径配置不正确

---

## run_KL.sh 改进点

### ✅ 1. 更健壮的错误处理

- **移除了 `set -e`**：改为手动错误处理，不会因为小错误就退出
- **添加了错误陷阱**：捕获错误并记录到日志文件
- **优雅的清理机制**：退出时自动清理所有进程

### ✅ 2. 详细的环境检查

在启动前检查：
- ✅ 图形界面环境（DISPLAY/WAYLAND_DISPLAY）
- ✅ Python 解释器版本
- ✅ 必要的 Python 模块（dbus, gradio）
- ✅ DBus 可用性
- ✅ 所有必要文件是否存在

### ✅ 3. 完整的日志记录

- **启动日志文件**：`logs/startup_YYYYMMDD_HHMMSS.log`
- **所有输出都记录到日志**：包括错误信息
- **进程 PID 记录**：方便调试和监控

### ✅ 4. 更长的等待时间

- **MCP Server 等待时间**：从 3 秒增加到 5 秒
- **子智能体等待时间**：从 1 秒增加到 2 秒
- **更宽松的失败检查**：子智能体启动失败不会阻止主程序继续

### ✅ 5. 环境变量完整传递

确保以下环境变量在 `dbus-run-session` 中正确传递：
- `PYTHONPATH`
- `GI_TYPELIB_PATH`
- `LD_LIBRARY_PATH`
- `UITARS_API_BASE`
- `VLLM_API_BASE`
- `DISPLAY`
- `WAYLAND_DISPLAY`

### ✅ 6. 进程状态监控

- 每个服务启动后检查进程状态
- 记录进程 PID，方便后续监控和清理
- 启动失败时给出警告但不阻止继续执行（除了 MCP Server）

---

## 使用方法

### 1. 赋予执行权限

```bash
chmod +x run_KL.sh
```

### 2. 运行脚本

```bash
./run_KL.sh
```

### 3. 查看日志

如果遇到问题，查看日志文件：

```bash
# 查看最新的启动日志
ls -lt logs/startup_*.log | head -1 | xargs cat

# 或者查看所有日志
tail -f logs/startup_*.log
```

---

## 常见问题排查

### 问题1：MCP Server 启动失败

**症状**：脚本在启动 MCP Server 后立即退出

**排查步骤**：
1. 查看日志文件：`logs/startup_*.log`
2. 检查 Python 模块是否安装：
   ```bash
   python3 -c "import dbus; import gradio"
   ```
3. 检查 MCP Server 文件是否存在：
   ```bash
   ls -l mcp_system/mcp_server/mcp_server.py
   ```
4. 手动运行 MCP Server 查看错误：
   ```bash
   python3 mcp_system/mcp_server/mcp_server.py
   ```

### 问题2：Gradio UI 无法启动

**症状**：所有智能体启动成功，但 Gradio UI 无法访问

**排查步骤**：
1. 检查端口是否被占用：
   ```bash
   netstat -tlnp | grep 7870
   ```
2. 检查防火墙设置
3. 查看 Gradio 错误日志：
   ```bash
   tail -50 logs/startup_*.log | grep -i error
   ```

### 问题3：图形界面功能不可用

**症状**：媒体控制、截图等功能报错

**排查步骤**：
1. 检查图形界面环境：
   ```bash
   echo $DISPLAY
   echo $WAYLAND_DISPLAY
   ```
2. 检查 DBus Session Bus：
   ```bash
   dbus-run-session -- echo "DBus available"
   ```
3. 检查截图工具：
   ```bash
   which gnome-screenshot scrot grim
   ```

### 问题4：Python 模块导入错误

**症状**：提示缺少 Python 模块

**解决方法**：
```bash
# 安装必要的模块
pip install dbus-python gradio

# 或者使用系统包管理器（Kylin 系统）
sudo apt-get install python3-dbus python3-gi
```

---

## 与原 run.sh 的对比

| 特性 | run.sh | run_KL.sh |
|------|--------|-----------|
| 错误处理 | `set -e`（严格） | 手动处理（灵活） |
| 环境检查 | 无 | 完整检查 |
| 日志记录 | 无 | 详细日志 |
| 等待时间 | 3秒（MCP） | 5秒（MCP） |
| 进程监控 | 仅检查 MCP | 检查所有进程 |
| 错误恢复 | 立即退出 | 继续执行（子智能体） |
| 清理机制 | 简单 | 完整清理 |

---

## 建议

1. **首次使用**：先运行 `run_KL.sh` 查看环境检查结果
2. **遇到问题**：查看日志文件 `logs/startup_*.log`
3. **调试模式**：可以手动运行各个组件，定位问题
4. **生产环境**：建议使用 systemd 服务管理，而不是直接运行脚本

---

## 联系支持

如果问题仍然存在，请提供：
1. 完整的日志文件：`logs/startup_*.log`
2. 环境信息：`python3 --version`, `uname -a`
3. 错误信息：终端输出的完整错误信息

