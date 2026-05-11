# 开局一下 MVP

Cloudflare Worker + static assets MVP for a younger Bazi/Qimen question tool.

## Stack

- Static HTML/CSS/ES modules under `public/`.
- Cloudflare Worker API under `src/worker.js`.
- Strict Zi Ping four-pillar calculation via `lunar-javascript`.
- Optional DeepSeek V4 explanation layer through Worker secrets.
- AdSense publisher placeholder already set to `pub-8433474721209734`.

## Local Preview

```bash
cd tool-sites/baziqimen
npm install
npm run dev
```

Open the local Worker URL that Wrangler prints, usually:

```text
http://127.0.0.1:8787/
```

## DeepSeek

Set the API key as a Cloudflare secret:

```bash
cd tool-sites/baziqimen
npx wrangler secret put DEEPSEEK_API_KEY
```

Optional variables are in `wrangler.toml`:

```text
DEEPSEEK_MODEL = "deepseek-v4-flash"
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_THINKING = "disabled"
```

Use `deepseek-v4-pro` if you want stronger but slower explanations.

## Deploy

```bash
cd tool-sites/baziqimen
npm run check
npm run deploy
```

Recommended domain: `kaijuyixia.com`. If unavailable, use `kaijuyixia.cn`, `qimenkai.com`, or `askqimen.com`, then replace canonical URLs, contact email, robots, and sitemap.

## AdSense Checklist

- Verify `https://kaijuyixia.com/ads.txt`.
- Keep ads away from form buttons and result controls.
- Do not promise certain outcomes.
- Keep the disclaimer and privacy pages linked from the footer.
