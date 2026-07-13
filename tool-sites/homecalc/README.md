# HomeCalc Tools

Static Cloudflare Pages site for home improvement calculators and planning guides.

The public site includes calculators for:

- paint
- tile
- flooring
- drywall
- wallpaper
- concrete
- mulch
- deck boards
- baseboard trim
- curtains

It also includes a guide library covering measurement, material waste, primer, finish, grout, wallpaper repeat, drywall finishing, project supplies, and budget planning.

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

Verify the AdSense publisher ID before each review or launch pass:

- `public/ads.txt`
- page `<head>` AdSense script tags

Also replace `homecalc.xyz` and `contact@homecalc.xyz` if you launch with a different domain.

Before submitting the site for ad review, run local link checks, verify `sitemap.xml`, and use the SOP in `docs/2026-05-05-cloudflare-tool-site-sop.md`.
