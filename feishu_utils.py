"""
飞书工具模块：发送群聊消息和更新文档
"""
import os
import re
import requests
import datetime
from typing import Optional, List
from loguru import logger
from paper import ArxivPaper


def get_tenant_access_token(app_id: str, app_secret: str) -> str:
    """获取飞书 tenant_access_token"""
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    payload = {
        "app_id": app_id,
        "app_secret": app_secret
    }
    try:
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != 0:
            raise Exception(f"获取 token 失败: {data.get('msg')}")
        return data["tenant_access_token"]
    except Exception as e:
        logger.error(f"获取飞书 token 失败: {e}")
        raise


def build_paper_summary(p: ArxivPaper) -> dict:
    """构建单篇论文的摘要信息（用于消息展示）"""
    author_list = [a.name for a in p.authors]
    num_authors = len(author_list)
    
    if num_authors <= 3:
        authors = ', '.join(author_list)
    else:
        authors = ', '.join(author_list[:2] + ['...'] + author_list[-1:])
    
    # 处理关键词
    try:
        kws = getattr(p, "keywords", None)
        if isinstance(kws, list) and len(kws) > 0:
            keywords_str = ', '.join(kws[:4])  # 最多4个
        else:
            keywords_str = "N/A"
    except Exception:
        keywords_str = "N/A"
    
    # 处理评分（星星）
    score = p.score if p.score else 0
    stars = "⭐" * min(5, int(score / 2)) if score > 6 else ""
    
    return {
        "title": p.title,
        "authors": authors,
        "keywords": keywords_str,
        "score": score,
        "stars": stars,
        "arxiv_id": p.arxiv_id,
        "tldr": p.tldr,
        "pdf_url": p.pdf_url,
        "code_url": p.code_url,
        "affiliations": p.affiliations or []
    }


def build_feishu_interactive_message(
    papers: List[ArxivPaper],
    date_str: Optional[str] = None,
    doc_url: Optional[str] = None,
) -> dict:
    """
    构建飞书 interactive 卡片：精简摘要（Top 3）+ 查看详情按钮
    采用官方推荐的简单 card 结构：若仍有问题，可从 API Explorer 进一步微调。
    """
    if date_str is None:
        date_str = datetime.datetime.now().strftime("%Y年%m月%d日")

    title = f"Daily arXiv - {date_str}"

    if len(papers) == 0:
        summary_md = "今天没有新论文，好好休息吧！😊"
    else:
        lines = [
            f"📚 **{title}**",
            "",
            f"今日推荐 {len(papers)} 篇论文，下面是前 3 篇简要信息：",
            "",
        ]
        for idx, p in enumerate(papers[:3], 1):
            info = build_paper_summary(p)
            one = [
                f"{idx}. **{info['title']}** {info['stars']}",
                f"   关键词: {info['keywords']}",
                f"   [arXiv 链接](https://arxiv.org/abs/{info['arxiv_id']})",
                "",
            ]
            lines.extend(one)
        if doc_url:
            lines.append(f"[👉 查看全部详情（飞书文档）]({doc_url})")
        summary_md = "\n".join(lines).strip()

    elements: list[dict] = [
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": summary_md,
            },
        }
    ]

    # /im/v1/messages 对 interactive 的要求是：
    # msg_type="interactive"，content 为 JSON 字符串形式的 card 对象
    import json
    card_obj = {
        "config": {"wide_screen_mode": True},
        "header": {
            "title": {"tag": "plain_text", "content": title},
            "template": "blue",
        },
        "elements": elements,
    }

    return {
        "msg_type": "interactive",
        "content": json.dumps(card_obj, ensure_ascii=False),
    }


def build_feishu_post_message(papers: List[ArxivPaper], date_str: Optional[str] = None) -> dict:
    """
    构建飞书 post 类型的富文本消息（支持折叠效果）
    每条论文先显示摘要，详细信息在折叠区域
    """
    if date_str is None:
        date_str = datetime.datetime.now().strftime('%Y年%m月%d日')
    
    if len(papers) == 0:
        return {
            "msg_type": "post",
            "content": {
                "post": {
                    "zh_cn": {
                        "title": f"📚 Daily arXiv - {date_str}",
                        "content": [
                            [
                                {
                                    "tag": "text",
                                    "text": "今天没有新论文，好好休息吧！😊"
                                }
                            ]
                        ]
                    }
                }
            }
        }
    
    # 构建消息内容
    content = []
    
    # 标题行
    content.append([
        {
            "tag": "text",
            "text": f"📚 Daily arXiv - {date_str}\n",
            "style": [
                {"bold": True},
                {"font_size": "large"}
            ]
        }
    ])
    
    content.append([
        {
            "tag": "text",
            "text": f"共推荐 {len(papers)} 篇论文\n\n",
            "style": [{"font_size": "medium"}]
        }
    ])
    
    # 每篇论文
    for idx, p in enumerate(papers, 1):
        paper_info = build_paper_summary(p)
        
        # 论文标题（可点击展开）
        content.append([
            {
                "tag": "text",
                "text": f"{idx}. ",
                "style": [{"bold": True}]
            },
            {
                "tag": "a",
                "text": paper_info["title"],
                "href": f"https://arxiv.org/abs/{paper_info['arxiv_id']}"
            },
            {
                "tag": "text",
                "text": f" {paper_info['stars']}\n",
            }
        ])
        
        # 摘要信息（作者、关键词）
        content.append([
            {
                "tag": "text",
                "text": f"   作者: {paper_info['authors']}\n",
                "style": [{"font_size": "small"}]
            }
        ])
        
        content.append([
            {
                "tag": "text",
                "text": f"   关键词: {paper_info['keywords']}\n",
                "style": [{"font_size": "small"}]
            }
        ])
        
        # 详细信息（TLDR）- 使用分隔线
        content.append([
            {
                "tag": "text",
                "text": f"   TLDR: {paper_info['tldr']}\n",
                "style": [{"font_size": "small"}]
            }
        ])
        
        # 链接
        links_text = f"   📄 PDF: {paper_info['pdf_url']}"
        if paper_info['code_url']:
            links_text += f" | 💻 Code: {paper_info['code_url']}"
        links_text += "\n"
        
        content.append([
            {
                "tag": "text",
                "text": links_text,
                "style": [{"font_size": "small"}]
            }
        ])
        
        # 分隔线（除了最后一篇）
        if idx < len(papers):
            content.append([
                {
                    "tag": "text",
                    "text": "─" * 30 + "\n",
                    "style": [{"font_size": "small"}]
                }
            ])
    
    return {
        "msg_type": "post",
        "content": {
            "post": {
                "zh_cn": {
                    "title": f"📚 Daily arXiv - {date_str}",
                    "content": content
                }
            }
        }
    }


def send_feishu_group_message(
    papers: List[ArxivPaper],
    app_id: str,
    app_secret: str,
    chat_id: str,
    date_str: Optional[str] = None,
    doc_url: Optional[str] = None,
) -> bool:
    """
    发送飞书群聊消息
    
    Args:
        papers: 论文列表
        app_id: 飞书应用 ID
        app_secret: 飞书应用 Secret
        chat_id: 群聊 ID
        date_str: 日期字符串（可选）
    
    Returns:
        bool: 是否发送成功
    """
    try:
        token = get_tenant_access_token(app_id, app_secret)
        url = "https://open.feishu.cn/open-apis/im/v1/messages"
        
        # 构建消息（卡片概要 + 查看详情按钮）
        message = build_feishu_interactive_message(papers, date_str, doc_url)
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        params = {
            "receive_id_type": "chat_id"
        }
        
        payload = {
            "receive_id": chat_id,
            **message
        }

        resp = requests.post(url, headers=headers, params=params, json=payload, timeout=30)
        try:
            resp.raise_for_status()
        except Exception as http_e:
            logger.error(f"发送飞书消息 HTTP错误: {http_e}, 响应: {resp.text}")
            return False

        data = resp.json()
        
        if data.get("code") != 0:
            logger.error(f"发送飞书消息失败: {data.get('code')} {data.get('msg')} | 响应: {data}")
            return False
        
        logger.success(f"✅ 飞书群聊消息发送成功 (共 {len(papers)} 篇论文)")
        return True
        
    except Exception as e:
        logger.error(f"发送飞书消息时出错: {e}")
        return False


def build_markdown_for_doc(papers: List[ArxivPaper], date_str: Optional[str] = None) -> str:
    """
    构建用于飞书文档的 Markdown 内容
    """
    if date_str is None:
        date_str = datetime.datetime.now().strftime('%Y年%m月%d日')
    
    if len(papers) == 0:
        return f"## {date_str}\n\n今天没有新论文，好好休息吧！😊\n\n---\n\n"
    
    md_lines = [f"## {date_str}\n"]
    md_lines.append(f"**共推荐 {len(papers)} 篇论文**\n\n")
    
    for idx, p in enumerate(papers, 1):
        paper_info = build_paper_summary(p)
        
        md_lines.append(f"### {idx}. {paper_info['title']} {paper_info['stars']}\n")
        md_lines.append(f"**作者:** {paper_info['authors']}\n\n")
        
        if paper_info['affiliations']:
            affil_str = ', '.join(paper_info['affiliations'][:3])
            if len(paper_info['affiliations']) > 3:
                affil_str += ', ...'
            md_lines.append(f"**机构:** {affil_str}\n\n")
        
        md_lines.append(f"**关键词:** {paper_info['keywords']}\n\n")
        md_lines.append(f"**TLDR:** {paper_info['tldr']}\n\n")
        md_lines.append(f"**链接:** [arXiv](https://arxiv.org/abs/{paper_info['arxiv_id']}) | [PDF]({paper_info['pdf_url']})")
        
        if paper_info['code_url']:
            md_lines.append(f" | [Code]({paper_info['code_url']})")
        
        md_lines.append("\n\n---\n\n")
    
    return ''.join(md_lines)


def markdown_to_docx_paragraphs(md: str) -> List[str]:
    """
    将用于邮件/本地历史的 Markdown 文本，转换为适合 Docx 文档的纯文本段落列表。
    - 去掉标题符号(#)
    - 去掉粗体符号(**)
    - 将 Markdown 链接 [text](url) 转换为 "text (url)"
    - 将分隔线 --- 转成一行长横线
    """
    # 去掉行首的 # 级标题
    text = re.sub(r'^[#]{1,6}\s*', '', md, flags=re.MULTILINE)
    # 去掉粗体标记 **
    text = text.replace('**', '')
    # 转换链接 [text](url) -> text (url)
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'\1 (\2)', text)
    # 将分隔线 --- 转为一行横线
    text = re.sub(r'^-{3,}\s*$', '--------------------', text, flags=re.MULTILINE)

    # 按空行拆成段落
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    return paragraphs


def update_feishu_document(
    papers: List[ArxivPaper],
    app_id: str,
    app_secret: str,
    doc_token: str,
    history_file: Optional[str] = None
) -> bool:
    """
    更新飞书文档（通过维护本地 Markdown 文件，然后同步到飞书）
    
    Args:
        papers: 论文列表
        app_id: 飞书应用 ID
        app_secret: 飞书应用 Secret
        doc_token: 飞书文档 token
        history_file: 本地历史文件路径（如 history.md），如果为 None 则不维护本地文件
    
    Returns:
        bool: 是否更新成功
    """
    try:
        date_str = datetime.datetime.now().strftime('%Y年%m月%d日')
        md_content = build_markdown_for_doc(papers, date_str)
        docx_paragraphs = markdown_to_docx_paragraphs(md_content)
        
        # 1. 更新本地历史文件（如果指定，保留完整 Markdown）
        if history_file:
            try:
                if os.path.exists(history_file):
                    with open(history_file, 'r', encoding='utf-8') as f:
                        existing_content = f.read()
                    # 在文件开头插入新内容
                    with open(history_file, 'w', encoding='utf-8') as f:
                        f.write(md_content + existing_content)
                else:
                    # 首次创建，添加标题
                    with open(history_file, 'w', encoding='utf-8') as f:
                        f.write(f"# Daily arXiv 推荐历史\n\n{md_content}")
                logger.info(f"✅ 本地历史文件已更新: {history_file}")
            except Exception as e:
                logger.warning(f"更新本地历史文件失败: {e}")
        
        # 2. 使用 Docx SDK 追加更新飞书 Docx 文档内容（docx/v1），以用户身份调用
        try:
            import lark_oapi as lark
            from lark_oapi.api.docx.v1 import (
                CreateDocumentBlockChildrenRequest,
                CreateDocumentBlockChildrenRequestBody,
                Block,
                Text,
                TextElement,
                TextRun,
                TextStyle,
            )

            user_access_token = os.getenv("FEISHU_USER_ACCESS_TOKEN")
            if not user_access_token:
                logger.warning("⚠️  未配置 FEISHU_USER_ACCESS_TOKEN，无法自动更新 Docx 文档，只更新本地 Markdown。")
                return True

            # 使用 SDK client，按官方示例启用 set_token
            client = lark.Client.builder() \
                .enable_set_token(True) \
                .log_level(lark.LogLevel.INFO) \
                .build()

            # 构造块列表：block_type=2 表示段落块，使用 Text 结构承载文本
            blocks: List[Block] = []
            for para in docx_paragraphs:
                block = Block.builder() \
                    .block_type(2) \
                    .text(
                        Text.builder()
                        .style(TextStyle.builder().build())
                        .elements([
                            TextElement.builder()
                            .text_run(
                                TextRun.builder()
                                .content(para)
                                .build()
                            )
                            .build()
                        ])
                        .build()
                    ) \
                    .build()
                blocks.append(block)

            request = CreateDocumentBlockChildrenRequest.builder() \
                .document_id(doc_token) \
                .block_id(doc_token) \
                .document_revision_id(-1) \
                .request_body(
                    CreateDocumentBlockChildrenRequestBody.builder()
                    .children(blocks)
                    .index(0)
                    .build()
                ) \
                .build()

            option = lark.RequestOption.builder() \
                .user_access_token(user_access_token) \
                .build()

            response = client.docx.v1.document_block_children.create(request, option)

            if not response.success():
                logger.warning(
                    f"⚠️  飞书 Docx 文档 API 返回错误: {response.code} {response.msg} | log_id: {response.get_log_id()}"
                )
                return True

            logger.success("✅ 飞书 Docx 文档更新成功（追加模式，Docx SDK）")
            return True

        except Exception as e:
            logger.warning(f"⚠️  飞书 Docx 文档自动更新失败: {e}")
            if history_file:
                logger.info(f"   内容已保存到本地文件: {history_file}")
                logger.info("   建议：手动将 Markdown 内容导入到飞书文档（飞书支持 Markdown 导入），或检查 FEISHU_USER_ACCESS_TOKEN 是否有效")
            return True
        
    except Exception as e:
        logger.error(f"更新飞书文档时出错: {e}")
        return False

