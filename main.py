"""
FinGraph 财经图集爬虫主程序
"""

import logging
import yaml
from pathlib import Path

from crawler.zsxq_client import ZsxqClient
from crawler.parser import ArticleParser
from crawler.storage import Storage

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def load_config(config_path: str = "config/config.yaml") -> dict:
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def crawl(config: dict, max_pages: int = None, since_date: str = None):
    """
    执行爬取任务

    Args:
        config: 配置字典
        max_pages: 最大翻页数（None 表示爬取所有）
        since_date: 只爬取该日期之后的文章 (YYYY-MM-DD)
    """
    client = ZsxqClient(
        access_token=config["zsxq"]["access_token"],
        request_interval=config["crawler"]["request_interval"],
    )
    parser = ArticleParser()
    storage = Storage(
        db_path=config["storage"]["db_path"],
        articles_dir=config["storage"]["articles_dir"],
        images_dir=config["storage"]["images_dir"],
    )

    group_id = config["zsxq"]["group_id"]
    page_size = config["crawler"]["page_size"]
    download_images = config["crawler"]["download_images"]

    # 如果没指定起始日期，默认只爬取数据库中最新日期之后的内容
    if not since_date:
        since_date = storage.get_latest_article_date()

    end_time = None
    page = 0
    total_new = 0
    stop = False
    consecutive_failures = 0

    logger.info(f"开始爬取，since_date={since_date or '全部'}, max_pages={max_pages or '不限'}")

    while not stop:
        page += 1
        if max_pages and page > max_pages:
            break

        logger.info(f"正在获取第 {page} 页主题列表...")
        try:
            topics, next_end_time = client.get_topics(group_id, count=page_size, end_time=end_time)
        except Exception as e:
            consecutive_failures += 1
            logger.warning(f"第 {page} 页获取失败 ({consecutive_failures}/3): {e}")
            if consecutive_failures >= 3:
                logger.error("连续 3 页失败，停止爬取")
                break
            # 跳过这一页，用当前 end_time 继续尝试下一页
            continue

        consecutive_failures = 0

        if not topics:
            logger.info("没有更多主题了")
            break

        for topic in topics:
            # 只处理包含文章的主题（财经图集以文章形式发布）
            talk = topic.get("talk", {})
            article = talk.get("article")
            if not article:
                continue

            article_id = article["article_id"]
            topic_id = str(topic.get("topic_id", ""))
            title = article.get("title", "")

            # 检查是否为 FinGraph 每日财经图集
            if "FinGraph" not in title and "财经图集" not in title:
                continue

            # 检查是否已存在
            if storage.article_exists(article_id):
                logger.debug(f"已存在，跳过: {title}")
                continue

            # 检查日期范围
            create_time = topic.get("create_time", "")
            article_date = create_time[:10] if create_time else ""
            if since_date and article_date and article_date < since_date:
                logger.info(f"已到达起始日期 {since_date}，停止爬取")
                stop = True
                break

            # 获取文章 HTML
            logger.info(f"正在爬取: {title}")
            try:
                html = client.get_article_html(article_id)
            except Exception as e:
                logger.error(f"获取文章失败 {article_id}: {e}")
                continue

            # 解析文章
            try:
                digest = parser.parse(html)
            except Exception as e:
                logger.error(f"解析文章失败 {article_id}: {e}")
                continue

            # 下载图片
            local_images_map = {}
            if download_images:
                for item in digest.items:
                    for img_url in item.image_urls:
                        try:
                            img_data = client.download_image(img_url)
                            local_path = storage.save_image(img_url, img_data, article_id)
                            local_images_map[img_url] = local_path
                        except Exception as e:
                            logger.warning(f"下载图片失败: {img_url}: {e}")

            # 存储
            storage.save_digest(article_id, topic_id, digest, local_images_map)
            total_new += 1
            logger.info(f"已保存: {title} ({len(digest.items)} 条图表)")

        end_time = next_end_time

    logger.info(f"爬取完成，新增 {total_new} 篇文章")
    return total_new


def main():
    import argparse

    parser = argparse.ArgumentParser(description="FinGraph 财经图集爬虫")
    parser.add_argument("--config", default="config/config.yaml", help="配置文件路径")
    parser.add_argument("--pages", type=int, default=None, help="最大翻页数")
    parser.add_argument("--since", type=str, default=None, help="起始日期 (YYYY-MM-DD)")
    parser.add_argument("--all", action="store_true", help="爬取所有历史数据")
    args = parser.parse_args()

    config = load_config(args.config)

    since_date = args.since
    if args.all:
        since_date = ""  # 空字符串表示不限制

    crawl(config, max_pages=args.pages, since_date=since_date)


if __name__ == "__main__":
    main()
