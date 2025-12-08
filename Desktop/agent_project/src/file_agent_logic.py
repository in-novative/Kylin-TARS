import os
import shutil
from pathlib import Path  
from datetime import datetime

class FileAgentLogic:
    def search_file(self, search_path: str, keyword: str, recursive: bool = True) -> dict:
        """search_file接口核心逻辑"""
        # 1. 入参校验（修正语法）
        if not isinstance(search_path, str) or not search_path:
            return {"status": "error", "msg": "入参错误：search_path必须是非空字符串", "data": []}
        if not isinstance(keyword, str) or not keyword:
            return {"status": "error", "msg": "入参错误：keyword必须是非空字符串", "data": []}
        if not isinstance(recursive, bool):
            return {"status": "error", "msg": "入参错误：recursive必须是布尔值", "data": []}

        # 2. 校验路径是否存在
        if not os.path.exists(search_path):
            return {"status": "error", "msg": f"搜索路径不存在：{search_path}", "data": []}

        # 3. 执行搜索逻辑（修正walk_func的写法）
        matched_files = []
        try:
            # 递归/非递归搜索
            if recursive:
                # 递归：遍历所有子目录
                walk_func = os.walk(search_path)
            else:
                # 非递归：仅遍历当前目录
                root = search_path
                dirs = [d for d in os.listdir(search_path) if os.path.isdir(os.path.join(search_path, d))]
                files = [f for f in os.listdir(search_path) if os.path.isfile(os.path.join(search_path, f))]
                walk_func = [(root, dirs, files)]  # 模拟os.walk的返回格式

            # 遍历目录，匹配关键词
            for root, dirs, files in walk_func:
                for file in files:
                    if keyword in file:
                        file_path = os.path.join(root, file)
                        # 收集文件信息（修正字典格式）
                        matched_files.append({
                            "file_name": file,
                            "file_path": file_path,
                            "file_size": os.path.getsize(file_path),  # 字节
                            "modify_time": datetime.fromtimestamp(os.path.getmtime(file_path)).strftime("%Y-%m-%d %H:%M:%S")
                        })

            # 返回成功结果
            return {
                "status": "success",
                "msg": f"找到{len(matched_files)}个匹配文件",
                "data": matched_files
            }

        except Exception as e:
            return {"status": "error", "msg": f"搜索失败：{str(e)}", "data": []}
    
    def move_to_trash(self, file_path: str) -> dict:
        """move_to_trash接口核心逻辑"""
        # 1. 入参校验
        if not isinstance(file_path, str) or not file_path:
            return {"status": "error", "msg": "入参错误：file_path必须是非空字符串", "data": []}
        file_abs_path = os.path.abspath(file_path)
        if not os.path.exists(file_abs_path):
            return {"status": "error", "msg": f"文件不存在：{file_abs_path}", "data": []}

        # 2. 配置Ubuntu回收站路径
        trash_dir = os.path.expanduser("~/.local/share/Trash/files/")
        os.makedirs(trash_dir, exist_ok=True)  # 确保回收站目录存在

        # 3. 处理重复文件名（避免覆盖）
        file_name = os.path.basename(file_abs_path)
        target_path = os.path.join(trash_dir, file_name)
        counter = 1
        while os.path.exists(target_path):
            name, ext = os.path.splitext(file_name)
            target_path = os.path.join(trash_dir, f"{name}_{counter}{ext}")
            counter += 1

        # 4. 执行移动操作
        try:
            shutil.move(file_abs_path, target_path)
            return {
                "status": "success",
                "msg": f"已移至回收站：{target_path}",
                "data": [{"original_path": file_abs_path, "trash_path": target_path}]
            }
        except Exception as e:
            return {"status": "error", "msg": f"移动失败：{str(e)}", "data": []}

if __name__ == "__main__":
    agent = FileAgentLogic()
    
    # 测试search_file
    print("=== 测试search_file接口 ===")
    res1 = agent.search_file("/home/user1/Desktop", "test", recursive=True)
    print(res1)
    
    # 测试move_to_trash（先创建测试文件）
    print("\n=== 测试move_to_trash接口 ===")
    test_file = "/home/user1/Desktop/test_trash.txt"
    # 确保文件编码为utf-8（兼容中文）
    with open(test_file, "w", encoding="utf-8") as f:
        f.write("MCP接口测试文件")
    res2 = agent.move_to_trash(test_file)
    print(res2)