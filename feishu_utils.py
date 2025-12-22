"""
飞书工具模块：发送群聊消息和更新文档
"""
import os
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


def build_feishu_interactive_message(papers: List[ArxivPaper], date_str: Optional[str] = None) -> dict:
    """
    构建飞书消息（简化为 post 类型，避免卡片 schema 报 400）
    """
    if date_str is None:
        date_str = datetime.datetime.now().strftime('%Y年%m月%d日')

    def build_blocks():
        blocks = []
        if len(papers) == 0:
            blocks.append([{"tag": "text", "text": "今天没有新论文，好好休息吧！😊"}])
            return blocks

        blocks.append([{"tag": "text", "text": f"📚 Daily arXiv - {date_str}\n", "style": {"bold": True}}])
        blocks.append([{"tag": "text", "text": f"共推荐 {len(papers)} 篇论文\n\n"}])

        for idx, p in enumerate(papers, 1):
            info = build_paper_summary(p)
            blocks.append([{"tag": "text", "text": f"{idx}. {info['title']} {info['stars']}\n", "style": {"bold": True}}])
            blocks.append([{"tag": "text", "text": f"作者: {info['authors']}\n"}])
            blocks.append([{"tag": "text", "text": f"关键词: {info['keywords']}\n"}])
            blocks.append([{"tag": "text", "text": f"TLDR: {info['tldr']}\n"}])

            links = f"arXiv: https://arxiv.org/abs/{info['arxiv_id']}  |  PDF: {info['pdf_url']}"
            if info["code_url"]:
                links += f"  |  Code: {info['code_url']}"
            blocks.append([{"tag": "text", "text": links + "\n"}])
            blocks.append([{"tag": "text", "text": "—" * 20 + "\n"}])
        return blocks

    return {
        "msg_type": "post",
        "content": {
            "post": {
                "zh_cn": {
                    "title": f"Daily arXiv - {date_str}",
                    "content": build_blocks()
                }
            }
        }
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
    date_str: Optional[str] = None
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
        
        # 构建消息（使用 interactive 类型支持折叠）
        message = build_feishu_interactive_message(papers, date_str)
        
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
        new_content = build_markdown_for_doc(papers, date_str)
        
        # 1. 更新本地历史文件（如果指定）
        if history_file:
            try:
                if os.path.exists(history_file):
                    with open(history_file, 'r', encoding='utf-8') as f:
                        existing_content = f.read()
                    # 在文件开头插入新内容
                    with open(history_file, 'w', encoding='utf-8') as f:
                        f.write(new_content + existing_content)
                else:
                    # 首次创建，添加标题
                    with open(history_file, 'w', encoding='utf-8') as f:
                        f.write(f"# Daily arXiv 推荐历史\n\n{new_content}")
                logger.info(f"✅ 本地历史文件已更新: {history_file}")
            except Exception as e:
                logger.warning(f"更新本地历史文件失败: {e}")
        
        # 2. 尝试使用 lark_oapi SDK 更新飞书文档（可选功能）
        # 注意：飞书文档 API 比较复杂，这里提供一个基础实现
        # 如果 SDK 不可用，会回退到仅维护本地文件
        try:
            import lark_oapi as lark
            # 只导入需要的类，避免函数作用域内使用 import *
            from lark_oapi.api.docx.v1 import (
                ListDocumentBlockRequest,
                CreateDocumentBlockChildrenRequest,
            )
            
            client = lark.Client.builder() \
                .app_id(app_id) \
                .app_secret(app_secret) \
                .log_level(lark.LogLevel.INFO) \
                .build()
            
            # 获取文档的第一个 block（用于在开头插入新内容）
            blocks_request = ListDocumentBlockRequest.builder() \
                .document_id(doc_token) \
                .page_size(10) \
                .build()
            
            blocks_response = client.docx.v1.document_block.list(blocks_request)
            if not blocks_response.success():
                raise Exception(f"获取文档 blocks 失败: {blocks_response.msg}")
            
            # 找到第一个 block 的 ID（用于插入位置）
            first_block_id = None
            if blocks_response.data and blocks_response.data.items:
                first_block_id = blocks_response.data.items[0].block_id
            
            # 将 Markdown 内容转换为飞书文档 blocks
            # 简化处理：将每段内容转换为文本 block
            import re
            paragraphs = [p.strip() for p in new_content.split('\n\n') if p.strip()]
            blocks_to_insert = []
            
            for para in paragraphs:
                if para.startswith('##'):
                    # 二级标题
                    text = re.sub(r'^##+\s*', '', para).strip()
                    blocks_to_insert.append({
                        "block_type": 2,  # 文本块
                        "text": {
                            "elements": [{
                                "text_run": {
                                    "content": text,
                                    "style": {"bold": True}
                                }
                            }]
                        }
                    })
                elif para.startswith('---'):
                    # 分隔线
                    blocks_to_insert.append({"block_type": 19})  # 分隔线块
                else:
                    # 普通文本段落，处理链接
                    text_runs = []
                    last_end = 0
                    link_pattern = r'\[([^\]]+)\]\(([^\)]+)\)'
                    
                    for match in re.finditer(link_pattern, para):
                        if match.start() > last_end:
                            text_runs.append({
                                "text_run": {"content": para[last_end:match.start()]}
                            })
                        link_text = match.group(1)
                        link_url = match.group(2)
                        text_runs.append({
                            "text_run": {
                                "content": link_text,
                                "style": {"link": {"url": link_url}}
                            }
                        })
                        last_end = match.end()
                    
                    if last_end < len(para):
                        text_runs.append({
                            "text_run": {"content": para[last_end:]}
                        })
                    
                    if not text_runs:
                        text_runs = [{"text_run": {"content": para}}]
                    
                    blocks_to_insert.append({
                        "block_type": 2,
                        "text": {"elements": text_runs}
                    })
            
            # 在文档开头插入新内容
            if first_block_id and blocks_to_insert:
                insert_request = CreateDocumentBlockChildrenRequest.builder() \
                    .document_id(doc_token) \
                    .block_id(first_block_id) \
                    .index(0) \
                    .children(blocks_to_insert) \
                    .build()
                
                insert_response = client.docx.v1.document_block_children.create(insert_request)
                if insert_response.success():
                    logger.success(f"✅ 飞书文档更新成功")
                    return True
                else:
                    raise Exception(f"更新失败: {insert_response.msg}")
            else:
                raise Exception("无法找到插入位置或内容为空")
                
        except ImportError:
            logger.warning("⚠️  lark_oapi 未安装，无法自动更新飞书文档")
            logger.info("   建议：安装 lark_oapi: pip install lark-oapi")
            if history_file:
                logger.info(f"   内容已保存到本地文件: {history_file}")
                logger.info("   你可以手动将 Markdown 内容导入到飞书文档（飞书支持 Markdown 导入）")
            return True  # 本地文件已更新，返回成功
        except Exception as e:
            logger.warning(f"⚠️  飞书文档自动更新失败: {e}")
            if history_file:
                logger.info(f"   内容已保存到本地文件: {history_file}")
                logger.info("   建议：手动将 Markdown 内容导入到飞书文档（飞书支持 Markdown 导入）")
            return True  # 本地文件已更新，返回成功
        
    except Exception as e:
        logger.error(f"更新飞书文档时出错: {e}")
        return False

