"""
LLM 客户端
调用 DeepSeek API 进行文本分析和情绪打分
"""

import json
import requests


class LLMClient:
    BASE_URL = "https://api.deepseek.com/v1"

    def __init__(self, api_key: str, model: str = "deepseek-chat"):
        self.api_key = api_key
        self.model = model
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        })

    def chat(self, messages: list, temperature: float = 0.3, max_tokens: int = 1024) -> str:
        """
        发送聊天请求，返回模型回复文本
        """
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        resp = self.session.post(f"{self.BASE_URL}/chat/completions", json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]

    def score_article_item(self, text: str, region: str = "中国") -> dict:
        """
        对单条图文数据进行指标分类和情绪打分

        返回格式:
        {
            "indices": [
                {"name": "指数名称", "score": 分值, "type": "structural/event", "reason": "理由"}
            ],
            "locations": ["省份或城市名"]
        }
        """
        system_prompt = self._build_system_prompt(region)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text},
        ]
        reply = self.chat(messages, temperature=0.1)
        return self._parse_response(reply)

    def _build_system_prompt(self, region: str) -> str:
        if region == "中国":
            return CHINA_SCORING_PROMPT
        # 后续扩展其他区域
        return CHINA_SCORING_PROMPT

    def _parse_response(self, reply: str) -> dict:
        """解析模型 JSON 回复，带容错"""
        # 尝试提取 JSON 块
        reply = reply.strip()
        if "```json" in reply:
            reply = reply.split("```json")[1].split("```")[0].strip()
        elif "```" in reply:
            reply = reply.split("```")[1].split("```")[0].strip()

        try:
            return json.loads(reply)
        except json.JSONDecodeError:
            # 尝试找到第一个 { 和最后一个 }
            start = reply.find("{")
            end = reply.rfind("}") + 1
            if start >= 0 and end > start:
                try:
                    return json.loads(reply[start:end])
                except json.JSONDecodeError:
                    pass
            return {"indices": [], "locations": [], "error": "JSON parse failed", "raw": reply}


CHINA_SCORING_PROMPT = """你是一个宏观经济分析师。请根据用户提供的财经图文数据，完成指标分类、情绪打分和地理标注。

【任务】

1. 判断该条数据属于以下中国区域指数中的哪些（可多选，也可不选）：
   - 中国经济动能指数：PMI、工业增加值、GDP、产能利用率等反映实体经济扩张/收缩的数据
   - 中国贸易景气指数：进出口、关税、贸易顺差/逆差、出口订单、全球市场份额等
   - 中国房地产指数：房价、房贷利率、销售面积、新开工、土地出让、保交楼、开发商等
   - 中国资本市场情绪：A股、港股、ETF资金流、国家队、IPO、北向资金、市场情绪等
   - 中国产业升级指数：AI、半导体、新能源车、光伏、稀土、高端制造、研发、科技企业等
   - 中国财政脉冲指数：财政收支、专项债、地方债、基建投资、税收、养老金、城投等

2. 对命中的每个指数，给出情绪分值：
   - +2: 强正面（远超预期、重大利好、创纪录积极表现、重大政策转向利好）
   - +1: 温和正面（好于预期、改善、扩张、温和利好政策）
   - 0: 中性（符合预期、持平、无明确方向、纯分析无结论）
   - -1: 温和负面（不及预期、放缓、恶化、温和利空）
   - -2: 强负面（远差于预期、暴跌、崩盘、危机、重大政策利空）

3. 判断信号类型：
   - structural（结构性）：满足以下任一——政策制度变更、趋势拐点确认（连续多期方向逆转）、经济结构比例显著变化、不可逆事件
   - event（事件性）：满足以下任一——单期数据波动、市场短期反应、一次性孤立事件、预期内的常规操作

4. 提取数据中明确提及的中国省份或城市名称（如有）

【输出格式】严格输出JSON，不要有其他文字：
{
  "indices": [
    {"name": "指数名称", "score": 分值, "type": "structural或event", "reason": "一句话理由"}
  ],
  "locations": ["省份或城市名"]
}

如果该条数据不属于以上任何指数，输出：
{"indices": [], "locations": []}
"""
