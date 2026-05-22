"""
文章 HTML 解析器
从 FinGraph 每日财经图集的 HTML 内容中提取结构化数据
"""

import re
from dataclasses import dataclass, field
from bs4 import BeautifulSoup
from urllib.parse import urlparse


@dataclass
class ChartItem:
    """单条图文数据"""
    index: int  # 序号
    text: str  # 文字描述
    image_urls: list = field(default_factory=list)  # 图片 URL 列表
    source: str = ""  # 数据来源
    category: str = ""  # 分类：中国/美国/欧洲/全球 等


@dataclass
class DailyDigest:
    """每日财经图集解析结果"""
    title: str
    date: str  # YYYY-MM-DD
    period: str  # "早" or "晚"
    headlines: list = field(default_factory=list)  # 标题列表
    items: list = field(default_factory=list)  # ChartItem 列表
    raw_html: str = ""


class ArticleParser:
    # 分类关键词
    CATEGORY_MARKERS = ["中国", "美国", "欧洲", "英国", "日本", "韩国", "全球", "其他"]

    def parse(self, html: str) -> DailyDigest:
        """解析文章 HTML，提取结构化数据"""
        soup = BeautifulSoup(html, "html.parser")
        content_div = soup.find("div", class_="ql-editor")
        if not content_div:
            content_div = soup.find("div", class_="content")
        if not content_div:
            raise ValueError("无法找到文章内容区域")

        # 提取标题
        title_tag = soup.find("div", class_="title")
        title = title_tag.get_text(strip=True) if title_tag else ""

        # 解析日期和时段
        date, period = self._parse_title_date(title)

        # 遍历内容提取结构化数据
        digest = DailyDigest(
            title=title,
            date=date,
            period=period,
            raw_html=html,
        )

        self._extract_content(content_div, digest)
        return digest

    def _parse_title_date(self, title: str) -> tuple:
        """从标题中提取日期和时段"""
        # 匹配 "2026年05月22日（晚）"
        match = re.search(r"(\d{4})年(\d{2})月(\d{2})日[（(](早|晚)[）)]", title)
        if match:
            date = f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
            period = match.group(4)
            return date, period
        return "", ""

    def _extract_content(self, content_div, digest: DailyDigest):
        """从内容 div 中提取 headlines 和 chart items"""
        current_category = ""
        current_item_text = []
        current_item_images = []
        current_item_index = 0
        in_headline = False
        headline_done = False

        elements = content_div.find_all(["h1", "p"])

        for el in elements:
            text = el.get_text(strip=True)

            # 检测 h1 标签作为分类
            if el.name == "h1":
                # 保存上一个 item
                if current_item_text and headline_done:
                    self._save_item(digest, current_item_index, current_item_text,
                                    current_item_images, current_category)
                    current_item_text = []
                    current_item_images = []

                if text == "Headline":
                    in_headline = True
                    continue
                elif text in self.CATEGORY_MARKERS:
                    in_headline = False
                    headline_done = True
                    current_category = text
                    current_item_index = 0
                    continue

            # 提取 headline 条目
            if in_headline and text and text != "Headline":
                digest.headlines.append(text)
                continue

            # 跳过空行
            if not text and not el.find("img"):
                continue

            if not headline_done:
                continue

            # 检测序号开头的段落 → 新条目
            num_match = re.match(r"^(\d+)[.、．]", text)
            if num_match:
                # 保存上一个 item
                if current_item_text:
                    self._save_item(digest, current_item_index, current_item_text,
                                    current_item_images, current_category)
                    current_item_images = []

                current_item_index = int(num_match.group(1))
                current_item_text = [text]
                continue

            # 图片
            img_tag = el.find("img")
            if img_tag and img_tag.get("src"):
                current_item_images.append(img_tag["src"])
                continue

            # 来源标注
            if text.startswith("来源：") or text.startswith("来源:"):
                if current_item_text:
                    source = text.replace("来源：", "").replace("来源:", "").strip()
                    # 会在 save_item 时附加
                    current_item_text.append(f"[来源: {source}]")
                continue

            # 普通文本，附加到当前条目
            if current_item_text:
                current_item_text.append(text)

        # 保存最后一个 item
        if current_item_text:
            self._save_item(digest, current_item_index, current_item_text,
                            current_item_images, current_category)

    def _save_item(self, digest: DailyDigest, index: int, texts: list,
                   images: list, category: str):
        """保存一个 chart item"""
        # 提取来源
        source = ""
        clean_texts = []
        for t in texts:
            if t.startswith("[来源:"):
                source = t[5:-1].strip()
            else:
                clean_texts.append(t)

        item = ChartItem(
            index=index,
            text="\n".join(clean_texts),
            image_urls=images,
            source=source,
            category=category,
        )
        digest.items.append(item)
