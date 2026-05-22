# FinGraph 财经图集爬虫

从知识星球"财经图集"专栏自动爬取每日财经图文数据，为构建全球经济动向仪表盘提供数据源。

## 数据内容

FinGraph 每日发布早/晚两期财经图集，每期包含 20-30 条图文数据，覆盖：
- 中国：工业、贸易、财政、房地产、货币政策等
- 美国：就业、通胀、利率、科技股等
- 欧洲/日本/韩国/全球：GDP、PMI、零售、汇率等

## 项目结构

```
FinGraph/
├── main.py                  # 爬虫主程序入口
├── crawler/
│   ├── zsxq_client.py       # 知识星球 API 客户端
│   ├── parser.py            # 文章 HTML 解析器
│   └── storage.py           # SQLite + 文件存储
├── config/
│   ├── config.example.yaml  # 配置模板
│   └── config.yaml          # 实际配置（不提交）
├── data/                    # 数据目录（不提交）
│   ├── articles/            # 原始 HTML
│   ├── images/              # 下载的图表图片
│   └── fingraph.db          # SQLite 数据库
└── requirements.txt
```

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 配置
cp config/config.example.yaml config/config.yaml
# 编辑 config.yaml，填入你的 zsxq_access_token

# 爬取今日数据
python main.py --since 2026-05-22

# 爬取最近 1 页（约 3-4 天）
python main.py --pages 1

# 爬取所有可获取的历史数据（约 4 个月）
python main.py --all
```

## 获取 access_token

1. 浏览器打开 https://wx.zsxq.com 并登录
2. F12 → Network → 找任意 `api.zsxq.com` 请求
3. 复制 Cookie 中 `zsxq_access_token` 的值

> Token 有效期约 1-3 个月，过期需重新获取。

## 数据库结构

**articles 表**：文章元数据（日期、标题、时段）

**chart_items 表**：每条图文数据（分类、文字描述、图片 URL、本地图片路径、数据来源）

```sql
-- 查询某天的所有中国相关数据
SELECT item_index, text, source FROM chart_items
WHERE article_id IN (SELECT article_id FROM articles WHERE date = '2026-05-22')
AND category = '中国';
```

## 定时爬取（Linux crontab）

```bash
# 每天 9:30 和 21:30 执行
30 9,21 * * * cd /path/to/FinGraph && python3 main.py >> logs/crawl.log 2>&1
```

## 后续规划

- [ ] 全球经济动向仪表盘（基于爬取的图文数据）
- [ ] 关键指标提取与时序数据库
- [ ] Token 过期自动检测与通知
