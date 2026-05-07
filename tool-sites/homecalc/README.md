# HomeCalc Tools MVP

Static Cloudflare Pages MVP for a home improvement calculator site.

## Local Preview

Open:

```text
tool-sites/homecalc/public/index.html
```

or serve it locally:

```bash
cd tool-sites/homecalc
python3 -m http.server 8788 --directory public
```

## Deploy With Wrangler

```bash
cd tool-sites/homecalc
npm install -g wrangler
wrangler login
wrangler pages project create homecalc-xyz
wrangler pages deploy public --project-name=homecalc-xyz
```

## Before Ads

Replace the placeholder publisher ID in:

- `public/ads.txt`
- page `<head>` comments if you enable AdSense code

Also replace `homecalc.xyz` and `contact@homecalc.xyz` if you launch with a different domain.

Use the SOP in `docs/2026-05-05-cloudflare-tool-site-sop.md` before submitting the site for review.
