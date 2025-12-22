"""
飞书文档 Token 获取工具

使用方法：
1. 在文件开头填入你的 FEISHU_APP_ID 和 FEISHU_APP_SECRET
2. 运行: python get_feishu_doc_token.py
3. 在输出中找到目标文档的 Token
"""
import os
import sys
import re

# ========== 配置区域 ==========
# 请在这里填入你的飞书应用凭证
FEISHU_APP_ID = os.getenv("FEISHU_APP_ID", "cli_a8fa799ad079500e")  # 替换为你的 App ID
FEISHU_APP_SECRET = os.getenv("FEISHU_APP_SECRET", "8qQ7TxoBnIBTJkbLjYd84bXhkQY0IMvt")  # 替换为你的 App Secret
# ==============================

def get_doc_token_from_url():
    """从 URL 提取文档 Token（最简单的方法）"""
    print("=" * 60)
    print("方法一：从文档 URL 获取 Token（推荐）")
    print("=" * 60)
    print("\n1. 在飞书中打开你的文档")
    print("2. 查看浏览器地址栏")
    print("3. URL 格式通常为: https://xxx.feishu.cn/docx/doccnxxxxxxxxxxxxx")
    print("4. 文档 Token 就是 docx/ 后面的部分\n")
    
    url = input("请输入文档的完整 URL（或直接回车跳过）: ").strip()
    
    if url:
        # 提取 token
        match = re.search(r'/docx/(doccn[a-zA-Z0-9]+)', url)
        if match:
            token = match.group(1)
            print(f"\n✅ 文档 Token: {token}")
            print(f"\n💡 请将此 Token 填入配置文件的 FEISHU_DOC_TOKEN")
            return token
        else:
            print("❌ 无法从 URL 中提取 Token，请检查 URL 格式")
    else:
        print("⏭️  跳过方法一\n")
    
    return None


def get_doc_list():
    """通过 API 获取文档列表"""
    try:
        import lark_oapi as lark
        from lark_oapi.api.drive.v1 import ListFileRequest
    except ImportError:
        print("❌ 错误: 未安装 lark-oapi")
        print("请运行: pip install lark-oapi")
        return None
    
    print("=" * 60)
    print("方法二：通过 API 获取文档列表")
    print("=" * 60)
    
    # 创建客户端
    client = lark.Client.builder() \
        .app_id(FEISHU_APP_ID) \
        .app_secret(FEISHU_APP_SECRET) \
        .log_level(lark.LogLevel.INFO) \
        .build()
    
    print("\n🔍 正在获取文档列表...\n")
    
    try:
        # 获取文档列表（需要 drive:file 权限）
        request = ListFileRequest.builder() \
            .folder_token("root") \
            .page_size(50) \
            .build()
        
        response = client.drive.v1.file.list(request)
        
        if not response.success():
            print(f"❌ 获取失败: {response.msg}")
            print(f"   错误码: {response.code}")
            if response.code == 99991663:
                print("   💡 提示: 可能是权限不足，请检查应用是否添加了 'drive:file' 权限")
            return None
        
        if not response.data or not response.data.files:
            print("⚠️  未找到任何文档")
            return None
        
        print("=" * 60)
        print("📋 文档列表")
        print("=" * 60)
        
        docx_files = [f for f in response.data.files if f.type == "docx"]
        
        if not docx_files:
            print("\n⚠️  未找到 docx 格式的文档")
            return None
        
        for idx, file in enumerate(docx_files, 1):
            print(f"\n[{idx}] {file.name}")
            print(f"   文档 Token: {file.token}")
            print("-" * 60)
        
        print(f"\n✅ 共找到 {len(docx_files)} 个文档")
        print("\n💡 提示: 复制目标文档的 Token，填入配置文件的 FEISHU_DOC_TOKEN")
        
        return docx_files[0].token if docx_files else None
        
    except Exception as e:
        print(f"❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    print("\n" + "=" * 60)
    print("📄 飞书文档 Token 获取工具")
    print("=" * 60 + "\n")
    
    # 检查配置
    if not FEISHU_APP_ID.startswith("cli_") or len(FEISHU_APP_ID) <= 10:
        print("❌ 错误: FEISHU_APP_ID 未配置或格式不正确")
        print("   请在文件开头填入你的 App ID，或设置环境变量 FEISHU_APP_ID")
        return
    
    # 方法一：从 URL 获取（最简单）
    token = get_doc_token_from_url()
    
    if token:
        print(f"\n✅ 成功获取文档 Token: {token}")
        return
    
    # 方法二：通过 API 获取
    print("\n")
    token = get_doc_list()
    
    if not token:
        print("\n" + "=" * 60)
        print("💡 其他方法")
        print("=" * 60)
        print("\n如果以上方法都无法获取，可以：")
        print("1. 在飞书中打开文档")
        print("2. 点击右上角 '...' → '复制链接'")
        print("3. 从链接中提取 docx/ 后面的部分")
        print("4. 或者查看文档设置中的文档 ID")


if __name__ == "__main__":
    main()

