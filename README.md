# My treasure trove

简洁、可快速浏览的 AI 动态看板。每小时尝试更新；每条动态都标注原始来源、原文链接和可用的发布时间。内容只摘要，不替代原文。

<!-- DASHBOARD:START -->
正在等待首次自动更新。可在仓库的 **Actions → Update dashboard → Run workflow** 手动触发。
<!-- DASHBOARD:END -->

## 来源与口径

- **AI 资讯**：来自下方列出的公开 RSS 源；链接直达原文。显示 RSS 提供的发布时间，若源未提供则明确标为未知。
- **Mac 本地 AI、GitHub 热门项目、Agent / Skills**：通过 GitHub Search API 搜索公开仓库。展示仓库链接、Stars（抓取时数值）、创建/最近推送时间；每项都链接到仓库，并列出 API 查询来源。
- “热门”是**最近 30 天有推送的搜索结果中按 Stars 排序**，不是 GitHub 官方 Trending 榜单，也不代表质量背书。
- 所有时间均为 UTC。抓取时间与源提供的发布时间分开标注；数据源或 API 失败时会显示错误，不会伪装成完整更新。
- 自动化定义见 [更新工作流](.github/workflows/update.yml) 和 [抓取脚本](scripts/fetch_data.py)。

## 数据源

- [Hugging Face Blog RSS](https://huggingface.co/blog/feed.xml)
- [OpenAI News RSS](https://openai.com/news/rss.xml)
- [GitHub REST API — Search repositories](https://docs.github.com/en/rest/search/search#search-repositories)
