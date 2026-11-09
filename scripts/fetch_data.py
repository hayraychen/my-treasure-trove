#!/usr/bin/env python3
"""Fetch public RSS/GitHub data and replace the dashboard block in README."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import html
import json
import os
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
README = os.path.join(ROOT, "README.md")
START = "<!-- DASHBOARD:START -->"
END = "<!-- DASHBOARD:END -->"
USER_AGENT = "my-treasure-trove-dashboard/1.0 (GitHub Actions)"
RSS_FEEDS = [
    ("Hugging Face Blog", "https://huggingface.co/blog/feed.xml"),
    ("OpenAI News", "https://openai.com/news/rss.xml"),
]


def fetch(url: str, headers: dict[str, str] | None = None) -> bytes:
    request_headers = {"User-Agent": USER_AGENT, "Accept": "application/json, application/atom+xml, application/rss+xml, application/xml, text/xml"}
    if headers:
        request_headers.update(headers)
    request = urllib.request.Request(url, headers=request_headers)
    with urllib.request.urlopen(request, timeout=25) as response:
        return response.read()


def clean_text(value: str) -> str:
    value = re.sub(r"<[^>]*>", " ", value or "")
    value = html.unescape(value)
    return re.sub(r"\s+", " ", value).strip()


def parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    value = value.strip()
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        try:
            parsed = parsedate_to_datetime(value)
        except (TypeError, ValueError, OverflowError):
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def date_text(value: datetime | None) -> str:
    return value.strftime("%Y-%m-%d %H:%M UTC") if value else "源未提供/无法解析"


def rss_items(feed_name: str, feed_url: str) -> tuple[list[dict], str | None]:
    try:
        root = ET.fromstring(fetch(feed_url))
        items = []
        for entry in root.iter():
            tag = entry.tag.rsplit("}", 1)[-1].lower()
            if tag not in ("item", "entry"):
                continue
            fields = {}
            for child in list(entry):
                key = child.tag.rsplit("}", 1)[-1].lower()
                if key == "link":
                    link = child.attrib.get("href") or (child.text or "").strip()
                    if link:
                        fields["link"] = link
                else:
                    fields[key] = " ".join(child.itertext()).strip()
            title = clean_text(fields.get("title", ""))
            link = fields.get("link", "")
            if not title or not link:
                continue
            raw_date = fields.get("published") or fields.get("pubdate") or fields.get("updated") or fields.get("date")
            summary = clean_text(fields.get("summary") or fields.get("description") or fields.get("content", ""))
            items.append({"title": title, "url": link, "date": parse_date(raw_date), "summary": summary[:260], "source": feed_name})
        items.sort(key=lambda item: item["date"] or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
        return items[:5], None
    except Exception as exc:
        return [], f"{feed_name}: {type(exc).__name__}: {exc}"


def github_repositories(label: str, query_text: str, since: str, token: str | None) -> tuple[list[dict], str, str | None]:
    query = f"{query_text} pushed:>={since}"
    params = urllib.parse.urlencode({"q": query, "sort": "stars", "order": "desc", "per_page": 5})
    api_url = f"https://api.github.com/search/repositories?{params}"
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        data = json.loads(fetch(api_url, headers).decode("utf-8"))
        repos = []
        for item in data.get("items", []):
            repos.append({
                "name": item.get("full_name", "unknown"),
                "url": item.get("html_url", ""),
                "description": clean_text(item.get("description") or "")[:220],
                "stars": item.get("stargazers_count", 0),
                "created": parse_date(item.get("created_at")),
                "pushed": parse_date(item.get("pushed_at")),
            })
        return repos, api_url, None
    except Exception as exc:
        return [], api_url, f"{label}: {type(exc).__name__}: {exc}"


def render() -> str:
    now = datetime.now(timezone.utc)
    since = (now - timedelta(days=30)).date().isoformat()
    token = os.environ.get("GITHUB_TOKEN")
    sections: list[str] = [f"**抓取时间：{date_text(now)}**  ·  GitHub 项目搜索窗口：最近 30 天（自 {since} 起）"]
    errors: list[str] = []

    sections.append("\n### Mac 电脑跑 AI\n")
    mac_results, mac_api, error = github_repositories("Mac 本地 AI", "macOS LLM", since, token)
    if error:
        errors.append(error)
    if mac_results:
        for repo in mac_results:
            sections.append(f"- [{repo['name']}]({repo['url']}) — {repo['description'] or '仓库未提供简介'} · ⭐ {repo['stars']:,}（抓取时） · 最近推送：{date_text(repo['pushed'])} · 创建：{date_text(repo['created'])}")
    else:
        sections.append("- 本次未取得结果；详见下方数据源状态。")
    sections.append(f"\n来源查询：[GitHub Search API]({mac_api})")

    sections.append("\n### 最新 AI 资讯\n")
    all_news: list[dict] = []
    for feed_name, feed_url in RSS_FEEDS:
        items, error = rss_items(feed_name, feed_url)
        if error:
            errors.append(error)
        for item in items:
            item["feed_url"] = feed_url
        all_news.extend(items)
    all_news.sort(key=lambda item: item["date"] or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    if all_news:
        for item in all_news[:8]:
            summary = f" — {item['summary']}" if item["summary"] else ""
            sections.append(f"- [{item['title']}]({item['url']}) — {item['source']} · 发布：{date_text(item['date'])}{summary}")
    else:
        sections.append("- 本次未取得资讯；详见下方数据源状态。")
    sections.append("\nRSS 来源：[Hugging Face Blog](https://huggingface.co/blog/feed.xml) · [OpenAI News](https://openai.com/news/rss.xml)")

    sections.append("\n### GitHub 热门开源项目\n")
    trend_results, trend_api, error = github_repositories("GitHub 热门项目", "AI LLM", since, token)
    if error:
        errors.append(error)
    if trend_results:
        for repo in trend_results:
            sections.append(f"- [{repo['name']}]({repo['url']}) — {repo['description'] or '仓库未提供简介'} · ⭐ {repo['stars']:,}（抓取时） · 最近推送：{date_text(repo['pushed'])}")
    else:
        sections.append("- 本次未取得结果；详见下方数据源状态。")
    sections.append(f"\n来源查询：[GitHub Search API]({trend_api})")

    sections.append("\n### 热门 Agent / Skills\n")
    agent_results, agent_api, error = github_repositories("Agent / Skills", 'agent skills', since, token)
    if error:
        errors.append(error)
    if agent_results:
        for repo in agent_results:
            sections.append(f"- [{repo['name']}]({repo['url']}) — {repo['description'] or '仓库未提供简介'} · ⭐ {repo['stars']:,}（抓取时） · 最近推送：{date_text(repo['pushed'])}")
    else:
        sections.append("- 本次未取得结果；详见下方数据源状态。")
    sections.append(f"\n来源查询：[GitHub Search API]({agent_api})")

    sections.append("\n### 数据源状态\n")
    if errors:
        sections.extend(f"- ⚠️ {clean_text(error)}" for error in errors)
    else:
        sections.append("- 本次配置的数据源均成功响应。")
    sections.append("- RSS 条目链接为原文；GitHub 项目链接为仓库。Stars 和时间为本次抓取到的 API 值，不是实时承诺。")
    return "\n".join(sections)


def main() -> None:
    with open(README, "r", encoding="utf-8") as file:
        content = file.read()
    if START not in content or END not in content:
        raise SystemExit("README dashboard markers not found")
    before, remainder = content.split(START, 1)
    _, after = remainder.split(END, 1)
    updated = before + START + "\n" + render() + "\n" + END + after
    with open(README, "w", encoding="utf-8") as file:
        file.write(updated)


if __name__ == "__main__":
    main()
