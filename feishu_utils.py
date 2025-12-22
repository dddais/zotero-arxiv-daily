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
    if not app_id or not app_secret:
        raise ValueError("app_id or app_secret not found")
    
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
            f"今日推荐 {len(papers)} 篇论文，下面是前 3 篇精简信息：",
            "",
        ]
        for idx, p in enumerate(papers[:3], 1):
            info = build_paper_summary(p)
            # TLDR 做 1 行截断，避免群里太长
            tldr_short = info["tldr"].replace("\n", " ")
            if len(tldr_short) > 120:
                tldr_short = tldr_short[:117] + "..."
            # 每篇只保留一个链接（arXiv），避免信息过载
            one = [
                f"{idx}. **{info['title']}** {info['stars']}",
                f"   作者: {info['authors']}",
                f"   关键词: {info['keywords']}",
                f"   TLDR: {tldr_short}",
                f"   [arXiv](https://arxiv.org/abs/{info['arxiv_id']})",
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


def build_docx_blocks_for_papers(
    papers: List[ArxivPaper],
    date_str: str,
):
    """
    参考邮件样式，为 Docx 文档构建一组 Block：
    - 顶部：日期 + 总数
    - 每篇：标题（加粗+星级）/ 作者 / 机构 / 关键词 / TLDR / 链接 + 分隔线
    """
    try:
        import lark_oapi as lark  # noqa: F401
        from lark_oapi.api.docx.v1 import (
            Block,
            Text,
            TextElement,
            TextRun,
            TextStyle,
            TextElementStyle,
        )
    except Exception as e:
        # 理论上不会走到这里，因为上层已导入；保险兜底
        logger.error(f"❌ 导入 lark_oapi SDK 失败: {e}")
        import traceback
        logger.error(f"详细错误信息: {traceback.format_exc()}")
        return []

    blocks: List[Block] = []
    
    logger.debug(f"开始构造 Docx 块，papers 数量: {len(papers)}")

    # 顶部标题：日期（一级标题）
    title_elements = [
        TextElement.builder()
        .text_run(
            TextRun.builder()
            .content(f"Daily arXiv - {date_str}")
            .text_element_style(
                TextElementStyle.builder()
                .bold(True)
                .build()
            )
            .build()
        )
        .build()
    ]
    # 一级标题：使用 heading1 字段（block_type=3）
    # 根据飞书文档，heading1 的结构和 text 类似，但字段名不同
    blocks.append(
        Block.builder()
        .block_type(3)
        .heading1(
            Text.builder()
            .elements(title_elements)
            .style(TextStyle.builder().align(1).build())  # align=1 表示左对齐
            .build()
        )
        .build()
    )

    # 顶部第二行：总数
    summary_elements = [
        TextElement.builder()
        .text_run(
            TextRun.builder()
            .content(f"共推荐 {len(papers)} 篇论文")
            .build()
        )
        .build()
    ]
    blocks.append(
        Block.builder()
        .block_type(2)
        .text(
            Text.builder()
            .style(TextStyle.builder().build())
            .elements(summary_elements)
            .build()
        )
        .build()
    )

    # 空行
    def _blank_block():
        return (
            Block.builder()
            .block_type(2)
            .text(
                Text.builder()
                .style(TextStyle.builder().build())
                .elements([
                    TextElement.builder()
                    .text_run(TextRun.builder().content("").build())
                    .build()
                ])
                .build()
            )
            .build()
        )

    blocks.append(_blank_block())

    for idx, p in enumerate(papers, 1):
        info = build_paper_summary(p)

        # 标题行：序号 + 标题 + 星级（二级标题，加粗）
        title_line = f"{idx}. {info['title']} {info['stars']}"
        title_el = TextElement.builder().text_run(
            TextRun.builder()
            .content(title_line)
            .text_element_style(
                TextElementStyle.builder()
                .bold(True)
                .build()
            )
            .build()
        ).build()
        # 二级标题：使用 heading2 字段（block_type=4）
        blocks.append(
            Block.builder()
            .block_type(4)
            .heading2(
                Text.builder()
                .elements([title_el])
                .style(TextStyle.builder().build())
                .build()
            )
            .build()
        )

        # 作者（引用块，block_type=15）
        author_line = f"作者: {info['authors']}"
        author_el = TextElement.builder().text_run(
            TextRun.builder().content(author_line).build()
        ).build()
        blocks.append(
            Block.builder()
            .block_type(15)
            .quote(
                Text.builder()
                .elements([author_el])
                .style(TextStyle.builder().align(1).build())  # align=1 表示左对齐
                .build()
            )
            .build()
        )

        # 机构（最多 3 个，引用块）
        if info["affiliations"]:
            affil_list = info["affiliations"][:3]
            if len(info["affiliations"]) > 3:
                affil_list.append("...")
            affil_line = "机构: " + ", ".join(affil_list)
            affil_el = TextElement.builder().text_run(
                TextRun.builder().content(affil_line).build()
            ).build()
            blocks.append(
                Block.builder()
                .block_type(15)
                .quote(
                    Text.builder()
                    .elements([affil_el])
                    .style(TextStyle.builder().align(1).build())
                    .build()
                )
                .build()
            )

        # 关键词（引用块）
        kw_line = f"关键词: {info['keywords']}"
        kw_el = TextElement.builder().text_run(
            TextRun.builder().content(kw_line).build()
        ).build()
        blocks.append(
            Block.builder()
            .block_type(15)
            .quote(
                Text.builder()
                .elements([kw_el])
                .style(TextStyle.builder().align(1).build())
                .build()
            )
            .build()
        )

        # TLDR
        tldr_line = f"TLDR: {info['tldr']}"
        tldr_el = TextElement.builder().text_run(
            TextRun.builder().content(tldr_line).build()
        ).build()
        blocks.append(
            Block.builder()
            .block_type(2)
            .text(
                Text.builder()
                .style(TextStyle.builder().build())
                .elements([tldr_el])
                .build()
            )
            .build()
        )

        # 链接行：只保留一个链接（arXiv 页面）
        link_line = f"链接: https://arxiv.org/abs/{info['arxiv_id']}"
        link_el = TextElement.builder().text_run(
            TextRun.builder().content(link_line).build()
        ).build()
        blocks.append(
            Block.builder()
            .block_type(2)
            .text(
                Text.builder()
                .style(TextStyle.builder().build())
                .elements([link_el])
                .build()
            )
            .build()
        )

        # 分隔线 + 空行
        sep_el = TextElement.builder().text_run(
            TextRun.builder().content("────────────────────────────────").build()
        ).build()
        blocks.append(
            Block.builder()
            .block_type(2)
            .text(
                Text.builder()
                .style(TextStyle.builder().build())
                .elements([sep_el])
                .build()
            )
            .build()
        )
        blocks.append(_blank_block())

    logger.debug(f"构造完成，blocks 数量: {len(blocks)}")
    return blocks


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

        # 1. 不再维护本地 Markdown 文件，直接构造 Docx Block 结构
        # 2. 使用 Docx SDK 追加更新飞书 Docx 文档内容（docx/v1），使用应用级别的 tenant_access_token
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
                TextElementStyle,
            )

            # 检查 app_id 和 app_secret 是否提供
            if not app_id or not app_secret:
                logger.warning("⚠️  未提供 FEISHU_APP_ID 或 FEISHU_APP_SECRET，无法更新飞书文档")
                return True

            # 使用应用的 tenant_access_token（与发送消息的方式一致）
            tenant_token = get_tenant_access_token(app_id, app_secret)

            # 使用 SDK client
            client = lark.Client.builder() \
                .log_level(lark.LogLevel.INFO) \
                .build()

            # 构造块列表：参考邮件样式，但以 Docx 文本块的形式表达
            blocks: List[Block] = build_docx_blocks_for_papers(papers, date_str)

            # 检查 blocks 是否为空，API 要求 children 数组至少有一个元素
            if not blocks or len(blocks) == 0:
                logger.warning(f"⚠️  构造的 Docx 块列表为空（papers数量: {len(papers)}），跳过文档更新")
                return True
            
            logger.info(f"📝 准备插入 {len(blocks)} 个块到飞书文档")
            
            # 飞书 API 限制：children 数组最多 50 个元素，需要分批插入
            MAX_BLOCKS_PER_BATCH = 50
            total_batches = (len(blocks) + MAX_BLOCKS_PER_BATCH - 1) // MAX_BLOCKS_PER_BATCH
            logger.info(f"📦 将分 {total_batches} 批插入（每批最多 {MAX_BLOCKS_PER_BATCH} 个块）")
            
            # 使用 tenant_access_token（应用级别 token）
            option = lark.RequestOption.builder() \
                .tenant_access_token(tenant_token) \
                .build()
            
            # 分批插入，倒序插入以确保顺序正确（最后一批先插入，第1批最后插入）
            # 这样第1批会在最前面，保持正确的顺序
            for batch_idx in range(total_batches - 1, -1, -1):  # 从最后一批开始倒序
                start_idx = batch_idx * MAX_BLOCKS_PER_BATCH
                end_idx = min(start_idx + MAX_BLOCKS_PER_BATCH, len(blocks))
                batch_blocks = blocks[start_idx:end_idx]
                
                logger.debug(f"📤 插入第 {batch_idx + 1}/{total_batches} 批（块 {start_idx + 1}-{end_idx}，共 {len(batch_blocks)} 个）")
                
                request = CreateDocumentBlockChildrenRequest.builder() \
                    .document_id(doc_token) \
                    .block_id(doc_token) \
                    .document_revision_id(-1) \
                    .request_body(
                        CreateDocumentBlockChildrenRequestBody.builder()
                        .children(batch_blocks)
                        .index(0)  # 每次都插入到文档最前面
                        .build()
                    ) \
                    .build()
                
                response = client.docx.v1.document_block_children.create(request, option)
                
                if not response.success():
                    error_detail = ""
                    try:
                        if hasattr(response, 'raw') and response.raw:
                            import json
                            error_detail = f" | 响应详情: {json.dumps(json.loads(response.raw.content), indent=2, ensure_ascii=False)}"
                    except Exception:
                        pass
                    logger.warning(
                        f"⚠️  飞书 Docx 文档 API 返回错误（第 {batch_idx + 1} 批）: {response.code} {response.msg} | log_id: {response.get_log_id()}{error_detail}"
                    )
                    return True
                
                logger.debug(f"✅ 第 {batch_idx + 1}/{total_batches} 批插入成功")

            logger.success(f"✅ 飞书 Docx 文档更新成功（共 {len(blocks)} 个块，分 {total_batches} 批插入）")
            return True

        except Exception as e:
            logger.warning(f"⚠️  飞书 Docx 文档自动更新失败: {e}")
            import traceback
            logger.debug(f"详细错误信息: {traceback.format_exc()}")
            return True
        
    except Exception as e:
        logger.error(f"更新飞书文档时出错: {e}")
        return False

