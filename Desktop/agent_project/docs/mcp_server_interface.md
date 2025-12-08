+ ### **1. `Ping`**

  - **功能**：用于健康检查，返回服务器的当前状态和时间戳。

  - **输入参数**：无

  - **返回值**：

    - 成功：

      ```json
      {
        "status": "ok",
        "timestamp": <当前时间戳>,
        "service": "MCP Master Agent"
      }
      ```

    - 失败：无（通常不会失败）

  ### **2. `ToolsList`**

  - **功能**：列出所有可用的工具，包括本地工具和子代理（child agents）的工具。

  - **输入参数**：无

  - **返回值**：

    - 成功：

      ```json
      {
        "success": true,
        "tools": [
          {
            "name": "<工具名称>",
            "description": "<工具描述>",
            "parameters": <工具参数定义>,
            "examples": <工具使用示例>,
            "agent": "<子代理名称（如果有）>"
          },
          ...
        ],
        "total": <工具总数>
      }
      ```

    - 失败：

      ```json
      {
        "success": false,
        "error": "<错误信息>"
      }
      ```

  ### **3. `ToolsCall`**

  - **功能**：调用指定的工具，并传递参数。

  - **输入参数**：

    - `tool_name`：工具名称（字符串）
    - `parameters_json`：工具调用的参数（JSON 格式的字符串）

  - **返回值**：

    - 成功：

      ```json
      {
        "success": true,
        "result": <工具返回的结果>
      }
      ```

    - 失败：

      ```json
      {
        "success": false,
        "error": "<错误信息>"
      }
      ```

      

  ### **4. `AgentRegister`**

  - **功能**：注册一个子代理（child agent），子代理提供其服务信息和工具列表。

  - **输入参数**：

    - `agent_info_json`：子代理的信息（JSON 格式的字符串），包含以下字段：
      - `name`：子代理的名称
      - `service`：子代理的服务名称
      - `path`：子代理的 DBus 路径
      - `interface`：子代理的 DBus 接口名称
      - `tools`：子代理提供的工具列表

  - **返回值**：

    - 成功：

      ```json
      {
        "success": true,
        "message": "Agent '<代理名称>' registered successfully"
      }
      ```

    - 失败：

      ```json
      {
        "success": false,
        "error": "<错误信息>"
      }
      ```

  ### **5. `AgentUnregister`**

  - **功能**：注销一个子代理。

  - **输入参数**：

    - `agent_name`：子代理的名称（字符串）

  - **返回值**：

    - 成功：

      ```json
      {
        "success": true,
        "message": "Agent '<代理名称>' unregistered successfully"
      }
      ```

    - 失败：

      ```json
      {
        "success": false,
        "error": "<错误信息>"
      }
      ```

  ### **6. `AgentsList`**

  - **功能**：列出所有已注册的子代理及其状态。

  - **输入参数**：无

  - **返回值**：

    - 成功：

      ```json
      {
        "success": true,
        "agents": [
          {
            "name": "<子代理名称>",
            "service": "<服务名称>",
            "path": "<DBus 路径>",
            "interface": "<DBus 接口名称>",
            "tools_count": <工具数量>,
            "last_seen": <最后通信时间戳>,
            "is_alive": <是否在线（布尔值）>
          },
          ...
        ],
        "total": <子代理总数>
      }
      ```

    - 失败：

      ```json
      {
        "success": false,
        "error": "<错误信息>"
      }
      ```