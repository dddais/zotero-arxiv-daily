"""
飞书群聊 ID 获取工具

使用方法：
1. 在文件开头填入你的 FEISHU_APP_ID 和 FEISHU_APP_SECRET
2. 运行: python get_feishu_chat_id.py
3. 在输出中找到目标群聊的 Chat ID
"""
import os
import sys

# ========== 配置区域 ==========
# 请在这里填入你的飞书应用凭证
FEISHU_APP_ID = os.getenv("FEISHU_APP_ID", "cli_a9c27578bfb8dcd5")  # 替换为你的 App ID
FEISHU_APP_SECRET = os.getenv("FEISHU_APP_SECRET", "zWePqI6WS7JX1vmjmazs1EgR1ekXNRL7")  # 替换为你的 App Secret
# ==============================

def get_chat_list():
    """获取飞书群聊列表"""
    try:
        import lark_oapi as lark
        from lark_oapi.api.im.v1 import ListChatRequest
    except ImportError:
        print("❌ 错误: 未安装 lark-oapi")
        print("请运行: pip install lark-oapi")
        sys.exit(1)
    
    # 创建客户端
    client = lark.Client.builder() \
        .app_id(FEISHU_APP_ID) \
        .app_secret(FEISHU_APP_SECRET) \
        .log_level(lark.LogLevel.INFO) \
        .build()
    
    print("🔍 正在获取群聊列表...\n")
    
    # 获取群聊列表
    request = ListChatRequest.builder() \
        .page_size(50) \
        .build()
    
    try:
        response = client.im.v1.chat.list(request)
        
        if not response.success():
            print(f"❌ 获取失败: {response.msg}")
            print(f"   错误码: {response.code}")
            if response.code == 99991663:
                print("   💡 提示: 可能是权限不足，请检查应用是否添加了 'im:chat' 权限")
            elif response.code == 99991661:
                print("   💡 提示: App ID 或 App Secret 错误")
            return
        
        if not response.data or not response.data.items:
            print("⚠️  未找到任何群聊")
            print("   💡 提示: 确保应用已加入目标群聊")
            return
        
        print("=" * 60)
        print("📋 群聊列表")
        print("=" * 60)
        
        for idx, chat in enumerate(response.data.items, 1):
            # 新版 SDK 返回的 ListChat item 可能没有 chat_type 属性，这里用 getattr 兜底
            chat_type_raw = getattr(chat, "chat_type", None)
            if chat_type_raw is None:
                chat_type = "未知类型"
            elif str(chat_type_raw) == "2":
                chat_type = "群聊"
            elif str(chat_type_raw) == "1":
                chat_type = "单聊"
            else:
                chat_type = f"类型{chat_type_raw}"

            print(f"\n[{idx}] {getattr(chat, 'name', '(未命名)')}")
            print(f"    类型: {chat_type}")
            print(f"    Chat ID: {getattr(chat, 'chat_id', '(无 chat_id)')}")
            desc = getattr(chat, "description", None)
            if desc:
                print(f"    描述: {desc}")
            print("-" * 60)
        
        print(f"\n✅ 共找到 {len(response.data.items)} 个群聊")
        print("\n💡 提示: 复制目标群聊的 Chat ID，填入配置文件的 FEISHU_CHAT_ID")
        
    except Exception as e:
        print(f"❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # 检查配置
    if FEISHU_APP_ID.startswith("cli_") and len(FEISHU_APP_ID) > 10:
        if FEISHU_APP_SECRET and len(FEISHU_APP_SECRET) > 20:
            get_chat_list()
        else:
            print("❌ 错误: FEISHU_APP_SECRET 未配置或格式不正确")
            print("   请在文件开头填入你的 App Secret，或设置环境变量 FEISHU_APP_SECRET")
    else:
        print("❌ 错误: FEISHU_APP_ID 未配置或格式不正确")
        print("   请在文件开头填入你的 App ID，或设置环境变量 FEISHU_APP_ID")
        print("\n💡 提示: App ID 格式通常为 cli_xxx...")

