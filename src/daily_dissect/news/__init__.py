"""资讯线：抓取 RSS，只留最近 24 小时，单个源失败不影响其他源。"""

from daily_dissect.news.collect import NewsFetchResult, collect_news
from daily_dissect.news.models import NewsItem, SourceFailure
from daily_dissect.news.parse import NEWS_WITHIN_HOURS, filter_recent, parse_feed

__all__ = [
    "NEWS_WITHIN_HOURS",
    "NewsFetchResult",
    "NewsItem",
    "SourceFailure",
    "collect_news",
    "filter_recent",
    "parse_feed",
]
