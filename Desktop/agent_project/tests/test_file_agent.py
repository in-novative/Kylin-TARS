"""FileAgent自动化测试用例（覆盖正常/异常场景）"""
import os
import sys
import shutil

# 关键：将项目根目录+src目录加入Python路径，解决模块导入问题
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, SRC_DIR)

# 正确导入src目录下的FileAgentLogic
from file_agent_logic import FileAgentLogic

def test_search_file():
    """测试search_file接口：正常场景+所有异常场景"""
    agent = FileAgentLogic()
    test_search_path = "/home/user1/Desktop"
    test_keyword = "test"

    # 1. 正常场景：递归搜索桌面的test文件
    res_normal = agent.search_file(
        search_path=test_search_path,
        keyword=test_keyword,
        recursive=True
    )
    assert res_normal["status"] == "success", f"正常场景（递归搜索）测试失败：{res_normal['msg']}"
    print(f"✅ 正常场景1（递归搜索）：{res_normal['msg']}")

    # 2. 正常场景：非递归搜索
    res_normal2 = agent.search_file(
        search_path=test_search_path,
        keyword=test_keyword,
        recursive=False
    )
    assert res_normal2["status"] == "success", f"正常场景（非递归搜索）测试失败：{res_normal2['msg']}"
    print(f"✅ 正常场景2（非递归搜索）：{res_normal2['msg']}")

    # 3. 异常场景1：搜索路径不存在
    res_error1 = agent.search_file(
        search_path="/home/user1/Desktop/non_exist_dir",
        keyword=test_keyword
    )
    assert res_error1["status"] == "error", "异常场景1（路径不存在）测试失败"
    print(f"✅ 异常场景1（路径不存在）：{res_error1['msg']}")

    # 4. 异常场景2：搜索关键词为空
    res_error2 = agent.search_file(
        search_path=test_search_path,
        keyword=""
    )
    assert res_error2["status"] == "error", "异常场景2（关键词为空）测试失败"
    print(f"✅ 异常场景2（关键词为空）：{res_error2['msg']}")

    # 5. 异常场景3：搜索路径非字符串（类型错误）
    try:
        agent.search_file(search_path=123, keyword=test_keyword)
    except Exception as e:
        print(f"✅ 异常场景3（路径类型错误）：拦截成功，错误信息：{str(e)}")

def test_move_to_trash():
    """测试move_to_trash接口：正常场景+所有异常场景"""
    agent = FileAgentLogic()
    # 创建测试文件（确保存在）
    test_file_path = "/home/user1/Desktop/test_trash_file.txt"
    with open(test_file_path, "w", encoding="utf-8") as f:
        f.write("FileAgent测试文件")
    assert os.path.exists(test_file_path), "测试文件创建失败，请检查权限"

    # 1. 正常场景：移至回收站
    res_normal = agent.move_to_trash(file_path=test_file_path)
    assert res_normal["status"] == "success", f"正常场景（移至回收站）测试失败：{res_normal['msg']}"
    assert not os.path.exists(test_file_path), "文件未被移至回收站"
    print(f"✅ 正常场景（移至回收站）：{res_normal['msg']}")

    # 2. 异常场景1：文件不存在
    res_error1 = agent.move_to_trash(file_path="/home/user1/Desktop/non_exist_file.txt")
    assert res_error1["status"] == "error", "异常场景1（文件不存在）测试失败"
    print(f"✅ 异常场景1（文件不存在）：{res_error1['msg']}")

    # 3. 异常场景2：文件路径为空字符串
    res_error2 = agent.move_to_trash(file_path="")
    assert res_error2["status"] == "error", "异常场景2（路径为空）测试失败"
    print(f"✅ 异常场景2（路径为空）：{res_error2['msg']}")

    # 4. 异常场景3：路径为目录（非文件）
    test_dir_path = "/home/user1/Desktop/test_trash_dir"
    os.makedirs(test_dir_path, exist_ok=True)
    res_error3 = agent.move_to_trash(file_path=test_dir_path)
    assert res_error3["status"] == "success", "异常场景3（目录处理）测试失败"
    assert not os.path.exists(test_dir_path), "目录未被移至回收站"
    print(f"✅ 异常场景3（目录处理）：{res_error3['msg']}")

    # 清理：恢复测试文件（可选）
    trash_dir = os.path.expanduser("~/.local/share/Trash/files/")
    for item in os.listdir(trash_dir):
        if "test_trash" in item:
            src = os.path.join(trash_dir, item)
            dst = os.path.join("/home/user1/Desktop", item)
            shutil.move(src, dst)
    print(f"✅ 测试文件已恢复至桌面")

if __name__ == "__main__":
    print("===== 开始测试FileAgent接口 =====")
    # 执行文件搜索测试
    test_search_file()
    print("\n")
    # 执行移至回收站测试
    test_move_to_trash()
    print("\n🎉 FileAgent所有自动化测试用例执行完成！")
