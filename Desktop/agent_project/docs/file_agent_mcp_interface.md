# FileAgent MCP接口规范
| 接口名         | 入参（参数名/类型/必填）| 出参（字段名/类型/说明）| 异常返回示例                                                                 |
|----------------|---------------------------------------------|-------------------------------------------------|----------------------------------------------------------------------------------|
| search_file    | - search_path：str（必填）：搜索根路径<br>- keyword：str（必填）：文件名关键词<br>- recursive：bool（可选，默认True）：是否递归搜索 | - status：str：success/error<br>- msg：str：提示信息<br>- data：list：匹配文件列表（file_name/file_path/file_size/modify_time） | `{"status":"error","msg":"搜索路径不存在","data":[]}` |
| move_to_trash  | - file_path：str（必填）：文件lujing | - status：str：success/error<br>- msg：str：提示信息 | `{"status":"error","msg":"文件不存在"}` |