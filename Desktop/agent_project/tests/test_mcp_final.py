"""最终版MCP集成测试脚本（验证所有Agent的MCP接口）"""
import sys
import os
# 把项目根目录加入Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 直接导入MCP模块
import src.file_agent_mcp as file_agent_mcp
import src.settings_agent_mcp as settings_agent_mcp

def test_file_agent_mcp():
    """测试FileAgent的MCP接口"""
    print("=== 测试FileAgent MCP接口 ===")
    
    # 1. 测试search_file接口
    print("\n1. 测试 file_agent.search_file")
    search_request = {
        "search_path": "/home/user1/Desktop",
        "keyword": "test",
        "recursive": True
    }
    search_result = file_agent_mcp.handle_search_file(search_request)
    print(f"   状态：{search_result['status']}")
    print(f"   信息：{search_result['msg']}")
    assert search_result["status"] == "success", f"搜索接口测试失败：{search_result['msg']}"
    
    # 2. 测试move_to_trash接口
    print("\n2. 测试 file_agent.move_to_trash")
    # 先创建测试文件
    test_file = "/home/user1/Desktop/test_mcp_final.txt"
    with open(test_file, "w", encoding="utf-8") as f:
        f.write("最终MCP测试文件")
    trash_request = {"file_path": test_file}
    trash_result = file_agent_mcp.handle_move_to_trash(trash_request)
    print(f"   状态：{trash_result['status']}")
    print(f"   信息：{trash_result['msg']}")
    assert trash_result["status"] == "success", f"移至回收站接口测试失败：{trash_result['msg']}"
    
    print("\n✅ FileAgent MCP接口测试通过！")

def test_settings_agent_mcp():
    """测试SettingsAgent的MCP接口"""
    print("\n=== 测试SettingsAgent MCP接口 ===")
    
    # 1. 测试change_wallpaper接口
    print("\n1. 测试 settings_agent.change_wallpaper")
    wallpaper_request = {
        "wallpaper_path": "/home/user1/Desktop/test_wallpaper.jpg",
        "scale": "fill"
    }
    wallpaper_result = settings_agent_mcp.handle_change_wallpaper(wallpaper_request)
    print(f"   状态：{wallpaper_result['status']}")
    print(f"   信息：{wallpaper_result['msg']}")
    assert wallpaper_result["status"] == "success", f"壁纸修改接口测试失败：{wallpaper_result['msg']}"
    
    # 2. 测试adjust_volume接口
    print("\n2. 测试 settings_agent.adjust_volume")
    volume_request = {
        "volume": 50,
        "device": "@DEFAULT_SINK@"
    }
    volume_result = settings_agent_mcp.handle_adjust_volume(volume_request)
    print(f"   状态：{volume_result['status']}")
    print(f"   信息：{volume_result['msg']}")
    assert volume_result["status"] == "success", f"音量调整接口测试失败：{volume_result['msg']}"
    
    print("\n✅ SettingsAgent MCP接口测试通过！")

def test_mcp_server_start():
    """测试MCP Server启动"""
    print("\n=== 测试MCP Server启动 ===")
    # 测试FileAgent的MCP Server启动
    file_agent_mcp.mcp_server.start()
    # 测试SettingsAgent的MCP Server启动
    settings_agent_mcp.mcp_server.start()
    print("\n✅ MCP Server启动测试通过！")

if __name__ == "__main__":
    print("===== 开始最终版MCP集成测试 =====")
    try:
        # 执行所有测试
        test_file_agent_mcp()
        test_settings_agent_mcp()
        test_mcp_server_start()
        print("\n🎉 所有MCP接口集成测试通过！Day 2任务已全部完成！")
    except Exception as e:
        print(f"\n❌ 测试失败：{str(e)}")
        sys.exit(1)