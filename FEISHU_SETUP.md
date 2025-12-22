# 飞书开放平台配置详细指南

本指南将帮助你完成飞书开放平台的所有配置步骤，以便将 arXiv 论文推荐发送到飞书群聊和文档。

---

## 📋 目录

1. [创建飞书应用](#1-创建飞书应用)
2. [配置应用权限](#2-配置应用权限)
3. [获取应用凭证](#3-获取应用凭证)
4. [获取群聊 ID](#4-获取群聊-id)
5. [创建并获取文档 Token](#5-创建并获取文档-token)
6. [配置到项目](#6-配置到项目)
7. [测试验证](#7-测试验证)

---

## 1. 创建飞书应用

### 步骤 1.1：登录飞书开放平台

1. 访问 [飞书开放平台](https://open.feishu.cn/)
2. 使用你的飞书账号登录（需要管理员权限或创建应用的权限）

### 步骤 1.2：创建企业自建应用

1. 登录后，点击右上角 **"创建企业自建应用"** 或进入 **"应用管理"** → **"创建应用"**
2. 填写应用基本信息：
   - **应用名称**：例如 `arXiv Daily Bot` 或 `论文推荐机器人`
   - **应用描述**：例如 `每日自动推荐 arXiv 论文到飞书群聊和文档`
   - **应用图标**：可选，上传一个图标
3. 点击 **"创建"**

### 步骤 1.3：记录应用凭证

创建成功后，你会看到应用的 **基本信息** 页面，记录以下信息：

- **App ID**：格式如 `cli_a8fa799ad079500e`（这就是 `FEISHU_APP_ID`）
- **App Secret**：点击 **"查看"** 按钮查看，格式如 `8qQ7TxoBnIBTJkbLjYd84bXhkQY0IMvt`（这就是 `FEISHU_APP_SECRET`）

⚠️ **重要**：App Secret 只显示一次，请立即保存！

---

## 2. 配置应用权限

### 步骤 2.1：进入权限管理

在应用详情页面，点击左侧菜单 **"权限管理"**

### 步骤 2.2：添加所需权限

点击 **"添加权限"**，搜索并添加以下权限：

#### 必需权限列表：

1. **`im:message`** - 发送单聊、群聊消息
   - 权限范围：`发送单聊消息`、`发送群聊消息`
   
2. **`im:chat`** - 获取群聊信息
   - 权限范围：`获取群聊信息`、`获取与发送单聊、群组消息`

3. **`docx:document`** - 查看、编辑和管理云空间中所有文档
   - 权限范围：`查看、编辑和管理云空间中所有文档`
   
4. **`docx:document:readonly`** - 查看云空间中所有文档（如果只需要读取）
   - 权限范围：`查看云空间中所有文档`

### 步骤 2.3：申请权限

添加权限后，点击 **"申请权限"** 或 **"提交申请"**

⚠️ **注意**：
- 某些权限可能需要管理员审批
- 如果是个人开发者或测试环境，通常可以立即通过
- 企业环境可能需要等待管理员审批

---

## 3. 获取应用凭证

### 步骤 3.1：查看 App ID

在应用详情页面的 **"基本信息"** 中，可以看到 **App ID**

### 步骤 3.2：查看 App Secret

1. 在 **"基本信息"** 页面，找到 **"App Secret"**
2. 点击 **"查看"** 按钮
3. 可能需要验证身份（输入密码或扫码）
4. **立即复制并保存** App Secret（只显示一次！）

### 步骤 3.3：记录凭证

现在你有了：
- ✅ `FEISHU_APP_ID` = `cli_xxx...`
- ✅ `FEISHU_APP_SECRET` = `xxx...`

---

## 4. 获取群聊 ID

### 方法一：通过飞书 API 获取（推荐）

#### 步骤 4.1：安装飞书 SDK（如果还没有）

```bash
pip install lark-oapi
```

#### 步骤 4.2：创建临时脚本获取群聊列表

创建一个文件 `get_chat_id.py`：

```python
import lark_oapi as lark
import os

# 替换为你的 App ID 和 App Secret
APP_ID = "cli_a8fa799ad079500e"
APP_SECRET = "8qQ7TxoBnIBTJkbLjYd84bXhkQY0IMvt"

client = lark.Client.builder() \
    .app_id(APP_ID) \
    .app_secret(APP_SECRET) \
    .log_level(lark.LogLevel.INFO) \
    .build()

# 获取群聊列表
from lark_oapi.api.im.v1 import *

request = ListChatRequest.builder() \
    .page_size(50) \
    .build()

response = client.im.v1.chat.list(request)

if response.success():
    print("\n=== 群聊列表 ===")
    for chat in response.data.items:
        print(f"群聊名称: {chat.name}")
        print(f"群聊 ID: {chat.chat_id}")
        print(f"群聊类型: {chat.chat_type}")
        print("-" * 50)
else:
    print(f"获取失败: {response.msg}")
```

运行脚本：

```bash
python get_chat_id.py
```

#### 步骤 4.3：找到目标群聊

在输出中找到你要发送消息的群聊，记录其 **Chat ID**（格式如 `oc_xxx...`）

### 方法二：通过飞书网页端获取

1. 打开飞书网页版或客户端
2. 进入目标群聊
3. 查看浏览器地址栏或群聊设置
4. 群聊 ID 通常在 URL 中，格式如 `oc_xxx...`

### 方法三：使用飞书 API 工具

访问 [飞书 API 调试工具](https://open.feishu.cn/api-explorer)，使用 `GET /open-apis/im/v1/chats` 接口获取群聊列表。

---

## 5. 创建并获取文档 Token

### 步骤 5.1：创建飞书文档

1. 在飞书中创建一个新文档（可以是空白文档）
2. 给文档起个名字，例如 `Daily arXiv 推荐历史`

### 步骤 5.2：获取文档 Token

#### 方法一：从文档 URL 获取（最简单）

1. 打开文档，查看浏览器地址栏
2. URL 格式通常为：`https://xxx.feishu.cn/docx/doccnxxxxxxxxxxxxx`
3. **文档 Token** 就是 `docx/` 后面的部分：`doccnxxxxxxxxxxxxx`

例如：
```
https://xxx.feishu.cn/docx/doccnABC123XYZ456
```
文档 Token = `doccnABC123XYZ456`

#### 方法二：通过 API 获取

如果你有文档的完整 URL，也可以使用 API 获取文档信息。

### 步骤 5.3：确保应用有文档权限

确保你的应用已经添加了 `docx:document` 权限（见步骤 2.2）

---

## 6. 配置到项目

### 方式一：使用环境变量（推荐）

创建或编辑 `.env` 文件（在项目根目录）：

```env
# 飞书配置
FEISHU_APP_ID=cli_a8fa799ad079500e
FEISHU_APP_SECRET=8qQ7TxoBnIBTJkbLjYd84bXhkQY0IMvt
FEISHU_CHAT_ID=oc_xxxxxxxxxxxxx
FEISHU_DOC_TOKEN=doccnxxxxxxxxxxxxx
FEISHU_HISTORY_FILE=history.md

# 其他现有配置...
ZOTERO_ID=xxx
ZOTERO_KEY=xxx
# ...
```

### 方式二：使用命令行参数

```bash
python main.py \
  --feishu_app_id=cli_a8fa799ad079500e \
  --feishu_app_secret=8qQ7TxoBnIBTJkbLjYd84bXhkQY0IMvt \
  --feishu_chat_id=oc_xxxxxxxxxxxxx \
  --feishu_doc_token=doccnxxxxxxxxxxxxx \
  --feishu_history_file=history.md \
  # ... 其他参数
```

### 方式三：在 GitHub Actions 中配置

如果你使用 GitHub Actions，在仓库的 **Settings** → **Secrets and variables** → **Actions** 中添加：

- `FEISHU_APP_ID`
- `FEISHU_APP_SECRET`
- `FEISHU_CHAT_ID`
- `FEISHU_DOC_TOKEN`
- `FEISHU_HISTORY_FILE`（可选）

---

## 7. 测试验证

### 步骤 7.1：确保机器人已加入群聊

1. 在飞书中打开目标群聊
2. 点击群聊设置 → **群成员**
3. 点击 **添加成员** → 搜索你的应用名称
4. 将应用添加进群聊

### 步骤 7.2：运行测试

使用 `--debug` 模式测试（只处理 5 篇论文）：

```bash
python main.py \
  --debug \
  --feishu_app_id=你的APP_ID \
  --feishu_app_secret=你的APP_SECRET \
  --feishu_chat_id=你的群聊ID \
  --feishu_doc_token=你的文档TOKEN \
  --feishu_history_file=history.md \
  # ... 其他必需参数（zotero_id, arxiv_query 等）
```

### 步骤 7.3：检查结果

1. **检查群聊消息**：
   - 打开目标群聊
   - 应该看到一条卡片消息，显示论文摘要
   - 点击 **"📖 点击展开查看全部论文详情"** 应该能看到详细信息

2. **检查本地文件**：
   - 查看项目目录下是否生成了 `history.md` 文件
   - 文件内容应该是 Markdown 格式的论文列表

3. **检查飞书文档**（如果安装了 lark_oapi）：
   - 打开飞书文档
   - 应该看到新的论文内容被添加到文档开头

### 步骤 7.4：常见问题排查

#### 问题 1：提示 "获取 token 失败"

- ✅ 检查 `FEISHU_APP_ID` 和 `FEISHU_APP_SECRET` 是否正确
- ✅ 确认应用状态为"已启用"
- ✅ 检查网络连接

#### 问题 2：提示 "发送消息失败" 或 "权限不足"

- ✅ 确认应用已添加 `im:message` 权限
- ✅ 确认权限已通过审批
- ✅ 确认机器人已加入目标群聊
- ✅ 检查 `FEISHU_CHAT_ID` 是否正确

#### 问题 3：文档更新失败

- ✅ 确认应用已添加 `docx:document` 权限
- ✅ 检查 `FEISHU_DOC_TOKEN` 是否正确
- ✅ 如果未安装 `lark_oapi`，这是正常的，会保存到本地文件
- ✅ 安装 `lark_oapi`：`pip install lark-oapi`

#### 问题 4：消息格式显示异常

- ✅ 检查飞书客户端是否为最新版本
- ✅ 某些旧版飞书客户端可能不支持 `interactive` 卡片，会降级显示

---

## 📝 配置检查清单

在开始使用前，确认以下所有项：

- [ ] ✅ 已创建飞书应用
- [ ] ✅ 已记录 `App ID` 和 `App Secret`
- [ ] ✅ 已添加 `im:message` 权限
- [ ] ✅ 已添加 `im:chat` 权限
- [ ] ✅ 已添加 `docx:document` 权限
- [ ] ✅ 权限已通过审批
- [ ] ✅ 已获取群聊 ID（`oc_xxx...`）
- [ ] ✅ 已创建文档并获取文档 Token（`doccnxxx...`）
- [ ] ✅ 已将机器人添加进目标群聊
- [ ] ✅ 已在项目配置中填写所有飞书相关参数
- [ ] ✅ 已运行测试并验证功能正常

---

## 🔗 相关链接

- [飞书开放平台](https://open.feishu.cn/)
- [飞书 API 文档](https://open.feishu.cn/document/)
- [飞书 API 调试工具](https://open.feishu.cn/api-explorer)
- [lark-oapi Python SDK](https://github.com/larksuite/oapi-sdk-python)

---

## 💡 提示

1. **安全性**：
   - 不要将 `App Secret` 提交到公开仓库
   - 使用环境变量或 GitHub Secrets 存储敏感信息

2. **权限审批**：
   - 企业环境可能需要管理员审批权限
   - 个人开发者通常可以立即使用

3. **文档更新**：
   - 如果自动更新失败，可以手动将 `history.md` 导入飞书文档
   - 飞书文档支持直接粘贴 Markdown 内容

4. **测试建议**：
   - 先用 `--debug` 模式测试
   - 确认功能正常后再启用定时任务

---

如有问题，请检查日志输出或参考飞书开放平台文档。

