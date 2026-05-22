"""
知识星球 API 客户端
负责与知识星球 API 交互，获取主题列表和文章内容
"""

import time
import requests
from urllib.parse import quote


class ZsxqClient:
    BASE_URL = "https://api.zsxq.com/v2"
    ARTICLE_URL = "https://articles.zsxq.com/inline_form/id_{article_id}.html"

    def __init__(self, access_token: str, request_interval: float = 2.0):
        self.session = requests.Session()
        self.session.headers.update({
            "Cookie": f"zsxq_access_token={access_token}; abtest_env=beta",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://wx.zsxq.com/",
            "Origin": "https://wx.zsxq.com",
        })
        self.request_interval = request_interval
        self._last_request_time = 0

    def _throttle(self):
        """请求限流"""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.request_interval:
            time.sleep(self.request_interval - elapsed)
        self._last_request_time = time.time()

    def _get(self, url: str, params: dict = None) -> dict:
        """发送 GET 请求"""
        self._throttle()
        resp = self.session.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()
        if not data.get("succeeded"):
            raise Exception(f"API error: {data.get('code')} - {data.get('error', 'unknown')}")
        return data.get("resp_data", {})

    def get_topics(self, group_id: str, count: int = 20, end_time: str = None) -> tuple:
        """
        获取星球主题列表
        返回 (topics_list, next_end_time)
        """
        params = {"scope": "all", "count": count}
        if end_time:
            params["end_time"] = end_time

        url = f"{self.BASE_URL}/groups/{group_id}/topics"
        data = self._get(url, params)
        topics = data.get("topics", [])
        next_end_time = topics[-1]["create_time"] if topics else None
        return topics, next_end_time

    def get_article_html(self, article_id: str) -> str:
        """获取文章的完整 HTML 内容"""
        self._throttle()
        url = self.ARTICLE_URL.format(article_id=article_id)
        resp = self.session.get(url)
        resp.raise_for_status()
        return resp.text

    def download_image(self, image_url: str) -> bytes:
        """下载图片，返回二进制内容"""
        self._throttle()
        resp = self.session.get(image_url, timeout=30)
        resp.raise_for_status()
        return resp.content
