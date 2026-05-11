## 2026-04-23
- Documented the stable backtest v2 design for SSQ
- Added an implementation plan focused on tune/validate backtesting and portfolio-based scoring
- Created initial `.pm` project metadata for future maintenance
- Ran smoke validation for portfolio scoring, tune/validate backtesting, config coverage, deterministic ticket generation, and Flask rendering
- Updated project metadata to reflect stable backtest v2 implementation and validation status
- Changed parameter ranking to maximize validation expected value lower-confidence-bound (EV-LCB) instead of coverage-oriented score
- Added UI metrics for validation EV, risk-adjusted EV, per-ticket EV, and standard error

## 2026-05-05
- Added Cloudflare deployment, advertising monetization, and viral growth planning documentation
- Linked the commercialization plan from README
- Updated project metadata to reflect growth-planning phase and compliance-sensitive next actions
- Added a reusable Cloudflare tool-site SOP covering topic selection, AdSense setup, Cloudflare Pages deployment, analytics, launch checks, and operations
- Created the HomeCalc Tools Cloudflare Pages MVP with three calculators, six guide pages, legal pages, SEO files, ad placeholders, and Wrangler deploy metadata
- Added a China-mainland-focused SOP for AdSense registration, wire-transfer bank collection, Spaceship nameserver handoff, Cloudflare Pages deployment, and post-launch payment operations

## 2026-05-08
- Created the 开局一下 second tool-site MVP under `tool-sites/baziqimen`
- Implemented a Cloudflare Worker API with strict Zi Ping four-pillar calculation via `lunar-javascript`
- Added optional DeepSeek V4 JSON explanation support through Worker secrets
- Built the young-audience Chinese UI with public/lunar birth input, true solar time toggle, province/city/district selector, question textarea, structured result cards, pillars, element balance, Qimen grid, action items, and result-card download/copy controls
- Added true solar time and lunar/solar converter helper tools, six guide pages, legal pages, AdSense script, `ads.txt`, `robots.txt`, `sitemap.xml`, headers, redirects, README, and smoke test
- Added the Obsidian project card `工具站工厂/05 开局一下 二号工具站进度.md` and linked it from the tool-site dashboard
