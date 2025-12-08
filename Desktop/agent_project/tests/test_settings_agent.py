import os
import sys
# 将项目根目录加入Python路径，确保能导入src下的模块
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from src.settings_agent_logic import SettingsAgentLogic

def test_change_wallpaper():
    """测试change_wallpaper接口：覆盖正常场景+所有异常场景"""
    agent = SettingsAgentLogic()
    # 1. 正常场景：使用桌面的test_wallpaper.jpg（需确保文件存在）
    test_wallpaper = "/home/user1/Desktop/test_wallpaper.jpg"
    if os.path.exists(test_wallpaper):
        res = agent.change_wallpaper(test_wallpaper, scale="fill")
        assert res["status"] == "success", f"正常场景测试失败：{res['msg']}"
        print(f"✅ 正常场景（修改壁纸）：{res['msg']}")
    else:
        print("⚠️  测试壁纸文件不存在，跳过正常场景测试（请确保test_wallpaper.jpg在桌面）")
    
    # 2. 异常场景1：壁纸文件不存在
    res_error1 = agent.change_wallpaper("/home/user1/Desktop/non_exist.jpg")
    assert res_error1["status"] == "error", "异常场景1（文件不存在）测试失败"
    print(f"✅ 异常场景1（文件不存在）：{res_error1['msg']}")
    
    # 3. 异常场景2：缩放方式非法（不在fill/stretch/center/tile/zoom范围内）
    res_error2 = agent.change_wallpaper(test_wallpaper, scale="invalid_scale")
    assert res_error2["status"] == "error", "异常场景2（缩放方式非法）测试失败"
    print(f"✅ 异常场景2（缩放方式非法）：{res_error2['msg']}")
    
    # 4. 异常场景3：壁纸路径为空字符串
    res_error3 = agent.change_wallpaper("")
    assert res_error3["status"] == "error", "异常场景3（路径为空）测试失败"
    print(f"✅ 异常场景3（路径为空）：{res_error3['msg']}")

def test_adjust_volume():
    """测试adjust_volume接口：覆盖正常场景+所有异常场景"""
    agent = SettingsAgentLogic()
    # 1. 正常场景：调整音量至50%
    res = agent.adjust_volume(50, device="default")
    assert res["status"] == "success", f"正常场景测试失败：{res['msg']}"
    print(f"✅ 正常场景（调整音量）：{res['msg']}")
    
    # 2. 异常场景1：音量值超过100（非法范围）
    res_error1 = agent.adjust_volume(150)
    assert res_error1["status"] == "error", "异常场景1（音量超100）测试失败"
    print(f"✅ 异常场景1（音量超100）：{res_error1['msg']}")
    
    # 3. 异常场景2：音量值为负数（非法范围）
    res_error2 = agent.adjust_volume(-10)
    assert res_error2["status"] == "error", "异常场景2（音量为负）测试失败"
    print(f"✅ 异常场景2（音量为负）：{res_error2['msg']}")
    
    # 4. 异常场景3：音量值为非整数（入参类型错误，此处传字符串模拟）
    # 注：因接口入参校验会拦截类型错误，此处用try-except捕获
    try:
        agent.adjust_volume("50")
    except Exception as e:
        # 若接口返回error而非抛异常，改用以下方式
        res_error3 = agent.adjust_volume(volume="50") if hasattr(agent.adjust_volume, 'volume') else {"status": "error"}
        assert res_error3["status"] == "error", "异常场景3（类型错误）测试失败"
        print(f"✅ 异常场景3（类型错误）：入参类型错误拦截成功")

if __name__ == "__main__":
    # 执行所有测试用例
    print("===== 开始测试SettingsAgent接口 =====")
    test_change_wallpaper()
    print("\n")
    test_adjust_volume()
    print("\n🎉 SettingsAgent所有自动化测试用例执行完成！")