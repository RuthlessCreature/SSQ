# HomeCalc Tools

Static Cloudflare Pages site for transparent interior material takeoffs.

## Active library

The search-facing site is deliberately limited to four maintained calculators and four worked planning records:

- paint
- tile
- flooring
- drywall

Each active calculator exposes the product-specific assumptions that affect the purchase quantity. The accompanying records use clearly marked illustrative scenarios to show raw measurements, allowances, package rounding, and scope limits. Older URLs are retained for link continuity but marked `noindex,follow` until they are independently rewritten or retired.

## Local preview

```powershell
cd tool-sites/homecalc
py -3 -m http.server 8788 --directory public
```

Then open `http://127.0.0.1:8788/`.

## Deploy with Wrangler

```powershell
cd tool-sites/homecalc
npx wrangler pages deploy public --project-name=homecalc-xyz
```

## Review checklist

Before a search or ad-quality review, verify that:

- `public/sitemap.xml` contains only pages in the active library.
- Unmaintained legacy pages carry `noindex,follow` and are absent from the main navigation.
- Calculator results use the exact product coverage, carton coverage, or sheet dimensions provided by the reader.
- Every active record labels constructed examples as illustrative and links to `/methodology/`.
- `public/ads.txt`, contact information, privacy terms, and the disclaimer remain reachable.

The site currently does not load ad units. Reintroduce an AdSense script or units only after approval and only on pages that continue to meet the editorial standard.
