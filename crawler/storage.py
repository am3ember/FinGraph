"""
数据存储模块
使用 SQLite 存储结构化数据，文件系统存储图片
"""

import os
import json
import sqlite3
import hashlib
from datetime import datetime
from pathlib import Path


class Storage:
    def __init__(self, db_path: str, articles_dir: str, images_dir: str):
        self.db_path = db_path
        self.articles_dir = Path(articles_dir)
        self.images_dir = Path(images_dir)

        self.articles_dir.mkdir(parents=True, exist_ok=True)
        self.images_dir.mkdir(parents=True, exist_ok=True)

        self._init_db()

    def _init_db(self):
        """初始化数据库表"""
        conn = self._get_conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS articles (
                article_id TEXT PRIMARY KEY,
                topic_id TEXT,
                title TEXT,
                date TEXT,
                period TEXT,
                headlines TEXT,
                create_time TEXT,
                crawl_time TEXT
            );

            CREATE TABLE IF NOT EXISTS chart_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                article_id TEXT,
                item_index INTEGER,
                category TEXT,
                text TEXT,
                source TEXT,
                image_urls TEXT,
                local_images TEXT,
                FOREIGN KEY (article_id) REFERENCES articles(article_id)
            );

            CREATE INDEX IF NOT EXISTS idx_articles_date ON articles(date);
            CREATE INDEX IF NOT EXISTS idx_items_category ON chart_items(category);
            CREATE INDEX IF NOT EXISTS idx_items_article ON chart_items(article_id);
        """)
        conn.commit()
        conn.close()

    def _get_conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def article_exists(self, article_id: str) -> bool:
        """检查文章是否已爬取"""
        conn = self._get_conn()
        cur = conn.execute("SELECT 1 FROM articles WHERE article_id = ?", (article_id,))
        exists = cur.fetchone() is not None
        conn.close()
        return exists

    def save_digest(self, article_id: str, topic_id: str, digest, local_images_map: dict = None):
        """
        保存解析后的每日图集数据
        local_images_map: {image_url: local_path}
        """
        conn = self._get_conn()
        try:
            # 保存文章元数据
            conn.execute("""
                INSERT OR REPLACE INTO articles
                (article_id, topic_id, title, date, period, headlines, create_time, crawl_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                article_id,
                topic_id,
                digest.title,
                digest.date,
                digest.period,
                json.dumps(digest.headlines, ensure_ascii=False),
                digest.date,
                datetime.now().isoformat(),
            ))

            # 保存图文条目
            conn.execute("DELETE FROM chart_items WHERE article_id = ?", (article_id,))
            for item in digest.items:
                local_images = []
                if local_images_map:
                    local_images = [local_images_map.get(url, "") for url in item.image_urls]

                conn.execute("""
                    INSERT INTO chart_items
                    (article_id, item_index, category, text, source, image_urls, local_images)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    article_id,
                    item.index,
                    item.category,
                    item.text,
                    item.source,
                    json.dumps(item.image_urls, ensure_ascii=False),
                    json.dumps(local_images, ensure_ascii=False),
                ))

            conn.commit()
        finally:
            conn.close()

        # 保存原始 HTML
        html_path = self.articles_dir / f"{article_id}.html"
        html_path.write_text(digest.raw_html, encoding="utf-8")

    def save_image(self, image_url: str, image_data: bytes, article_id: str) -> str:
        """
        保存图片到本地，返回相对路径
        """
        # 用 URL hash 作为文件名，保留扩展名
        url_hash = hashlib.md5(image_url.encode()).hexdigest()[:12]
        ext = ".jpg"  # 知识星球图片默认 jpg

        article_dir = self.images_dir / article_id
        article_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{url_hash}{ext}"
        filepath = article_dir / filename
        filepath.write_bytes(image_data)

        return str(filepath.relative_to(self.images_dir.parent.parent))

    def get_latest_article_date(self) -> str:
        """获取数据库中最新文章的日期"""
        conn = self._get_conn()
        cur = conn.execute("SELECT MAX(date) FROM articles")
        row = cur.fetchone()
        conn.close()
        return row[0] if row and row[0] else ""
