# RentACastle — Comprehensive SEO Audit Report

**Date:** 2026-03-18  
**Site:** https://rentacastle.uk  
**Auditor:** Automated SEO Audit

---

## 1. Meta Tags (BaseLayout.astro)

- [OK] **Title tag pattern** — Dynamic `{title} | RentACastle` for all pages; homepage uses `RentACastle - Rent a Castle Anywhere in the UK`. (line 21-23, `src/layouts/BaseLayout.astro`)
- [OK] **Meta description** — Passed as prop with sensible default fallback (line 18-19). Every page type passes a custom description.
- [OK] **Canonical URL** — Generated automatically from `Astro.url.pathname` with configurable override via `canonicalUrl` prop (line 27).
- [OK] **Open Graph tags** — Full set: `og:type`, `og:title`, `og:description`, `og:image`, `og:url`, `og:site_name` (lines 37-43).
- [OK] **Twitter Card** — `summary_large_image` with title, description, and image (lines 46-49).
- [OK] **article:modified_time** — Conditionally rendered when `lastUpdated` prop is passed (line 35).
- [ISSUE] **og:type is always "website"** — Blog posts should use `og:type="article"`. Currently hardcoded to `"website"` for all page types (line 38, `src/layouts/BaseLayout.astro`).
- [MISSING] **og:locale** — No `og:locale` tag (should be `en_GB` for a UK site).
- [MISSING] **Twitter @site / @creator** — No Twitter handle specified in twitter card meta tags.

---

## 2. Schema.org Structured Data

### Present:
- [OK] **WebSite schema** — On homepage (`src/pages/index.astro`, line 63). Includes name, url, publisher.
- [OK] **Organization schema** — On homepage (`src/pages/index.astro`, line 63). Includes name, url, logo.
- [OK] **LodgingBusiness schema** — On every castle detail page (`src/pages/castles/[slug].astro`, line 48). Includes name, description, image, address, priceRange, numberOfRooms, amenityFeature, geo coordinates, and aggregateRating (when reviewScore exists).
- [OK] **BreadcrumbList schema** — On every page that uses the Breadcrumbs component (`src/components/Breadcrumbs.astro`, line 62). Properly structured with position, name, and item.
- [OK] **FAQPage schema** — On FAQ page (`src/pages/faq.astro`, line 70). All 10 FAQs included as Question/Answer pairs.
- [OK] **Article schema** — On blog post pages (`src/pages/blog/[slug].astro`, line 70). Includes headline, description, image, datePublished, author, publisher.

### Missing:
- [MISSING] **BlogPosting schema** — Blog posts use `@type: "Article"` instead of `"BlogPosting"` (line 60, `src/pages/blog/[slug].astro`). `BlogPosting` is a more specific subtype and preferred for blog content.
- [MISSING] **AggregateRating on standalone pages** — Only present within LodgingBusiness on castle detail pages (conditional). No site-wide aggregate rating schema.
- [MISSING] **dateModified in Article schema** — The Article schema on blog posts includes `datePublished` but no `dateModified` (line 60-69, `src/pages/blog/[slug].astro`).
- [MISSING] **mainEntityOfPage in Article** — The Article schema should include `mainEntityOfPage` for the canonical URL.

---

## 3. Sitemap

- [OK] **Sitemap integration** — `@astrojs/sitemap` is configured in `astro.config.mjs` (line 4).
- [OK] **sitemap-index.xml exists** — Found at `dist/sitemap-index.xml`.
- [OK] **sitemap-0.xml exists** — Found at `dist/sitemap-0.xml` (8,013 bytes).
- [OK] **Sitemap link in HTML head** — `<link rel="sitemap" href="/sitemap-index.xml" />` in BaseLayout (line 53).

---

## 4. Robots.txt

- [OK] **robots.txt exists** — Located at `public/robots.txt`.
- [OK] **Content is correct** — `User-agent: *`, `Allow: /`, `Sitemap: https://rentacastle.uk/sitemap-index.xml`.

---

## 5. Internal Linking

- [OK] **Castle-type pages link to individual castles** — All castle-type pages (e.g., `wedding-castles.astro`, line 35-50) link to `/castles/{slug}` for each filtered castle.
- [OK] **Region pages link to individual castles** — `regions/[slug].astro` (line 41-49) links to `/castles/{slug}` for each regional castle.
- [OK] **Castle detail pages cross-link** — `castles/[slug].astro` links to related castles in the same region (line 338-356), region pages (line 301-305), and blog posts (line 315-328).
- [OK] **FAQ has rich internal links** — FAQ answers contain links to `/guides/*`, `/castles`, `/castle-types/*` throughout.
- [OK] **Header mega-menus** — Excellent internal linking via mega menus with links to all regions, castle types, and guides (`src/components/Header.astro`).
- [OK] **Footer** — Links to castles, regions, castle types, blog, guides, FAQ (`src/components/Footer.astro`).
- [ISSUE] **Blog post content lacks internal links** — Blog post template (`src/pages/blog/[slug].astro`) has identical hardcoded body content for ALL posts (lines 99-136). The only internal link in the body is a generic `href="/castles"` (line 147). No links to specific castles, regions, or other blog posts within the article body.
- [ISSUE] **Blog posts have templated content** — Every single blog post renders the exact same article body text regardless of the post data. Only the title, description, date, category, and image vary. This is a critical content quality and internal linking problem. (See Section 11.)

---

## 6. Page Titles

| Page | Title | Length | Assessment |
|------|-------|--------|------------|
| `index.astro` | `RentACastle - Rent a Castle Anywhere in the UK` | 48 chars | [OK] Unique, keyword-rich, under 60 |
| `castles/index.astro` | `Castle Rentals UK - Browse All Castles \| RentACastle` | 53 chars | [OK] But note: title is passed to BaseLayout which appends `\| RentACastle` again, resulting in `Castle Rentals UK - Browse All Castles \| RentACastle \| RentACastle` (double brand name) |
| `regions/[slug].astro` | `{region.name} Castle Rentals - Castles to Rent in {region.name} \| RentACastle` | ~75 chars (Scotland) | [ISSUE] Double brand — BaseLayout appends `\| RentACastle` again. Also **exceeds 60 chars** for all regions. |
| `castle-types/wedding-castles.astro` | `Wedding Castle Venues \| RentACastle` | 36 chars | [OK] Unique, keyword-rich, under 60 |
| `blog/[slug].astro` | `{post.title} \| RentACastle` | Varies (e.g., 57 chars for "Best Castles to Rent in Scotland for 2026") | [OK] Dynamic per post, generally under 60 |
| `faq.astro` | `Frequently Asked Questions \| RentACastle` | 42 chars | [OK] Under 60 |

- [ISSUE] **Double `| RentACastle` on castles/index.astro** — The title prop already includes `| RentACastle`, and BaseLayout appends it again (line 8, `castles/index.astro`; line 22, `BaseLayout.astro`).
- [ISSUE] **Double `| RentACastle` on regions/[slug].astro** — Same problem: title prop already includes `| RentACastle` (line 22, `regions/[slug].astro`).
- [ISSUE] **Castle detail title also doubles** — `castles/[slug].astro` line 35: `${castle.name} | Castle Rental in ${castle.region} | RentACastle` becomes `{castle.name} | Castle Rental in {castle.region} | RentACastle | RentACastle`.

---

## 7. Heading Structure

### Homepage (`index.astro`):
- [OK] **Single H1** — `Rent a Castle in the United Kingdom` (line 109)
- [OK] **H2s** — Explore by Type, Explore by Region, Own a Historic Property?, Plan Your Castle Stay, Your Castle Awaits
- [OK] **H3s** — Category titles, region names, guide titles (properly nested under H2s)

### Castle Detail (`castles/[slug].astro`):
- [OK] **Single H1** — `{castle.name}` (line 69)
- [OK] **H2s** — Overview, Amenities, Castle History, Key Features, Location & Nearby Attractions, Castle Guides & Tips, Nearby Castles
- [OK] **H3s** — Quick Facts, Plan Your Stay, More Castles in {region} (sidebar)

### Blog Post (`blog/[slug].astro`):
- [OK] **Single H1** — `{post.title}` (line 88)
- [OK] **H2s** — What Makes This Special, Key Things to Know, Making the Most of Your Castle Stay, You Might Also Like
- [OK] **H3** — Ready to Book Your Castle Stay? (CTA), related post titles

---

## 8. Image Alt Text

- [OK] **Most images have descriptive alt text** — Castle images use `alt={castle.name}`, blog images use `alt={post.title}`, region images use `alt={`Castles in ${region.name}`}`, hero images have descriptive text like "Majestic Scottish castle on a loch at sunset".
- [OK] **Gallery images** — Castle detail page uses `alt={`${castle.name} - View ${i + 2}`}` for gallery thumbnails (line 60, `castles/[slug].astro`).
- [ISSUE] **Two decorative images have empty alt="" but need review** — `src/pages/index.astro` lines 210 and 254 have `alt=""` on background CTA images. These are decorative, so empty alt is technically correct, but the images are large section backgrounds that could benefit from descriptive alt text for accessibility.
- [ISSUE] **Guide card images on homepage missing width/height** — `src/pages/index.astro` line 234: `<img src={post.image} alt={post.title} loading="lazy" />` — missing `width` and `height` attributes, which causes layout shift (CLS).
- [ISSUE] **Castle detail hero main image missing loading/size attributes** — `castles/[slug].astro` line 57: `<img src={galleryImages[0]} alt={castle.name} />` — no `width`, `height`, `fetchpriority`, or `loading` attributes on the LCP image.

---

## 9. Core Web Vitals

### Lazy Loading:
- [OK] **Lazy loading widely used** — `loading="lazy"` found on 30+ images across all page types for below-fold content.
- [OK] **Hero/LCP images use eager loading** — `loading="eager"` + `fetchpriority="high"` on hero images across castle-type pages, region pages, castles index (20+ instances).
- [ISSUE] **Castle detail page hero has no loading strategy** — `castles/[slug].astro` line 57: main hero image lacks `loading="eager"`, `fetchpriority="high"`, `width`, and `height`.

### Font Strategy:
- [ISSUE] **Google Fonts loaded via @import (render-blocking)** — `src/styles/global.css` line 8 uses `@import url('https://fonts.googleapis.com/css2?family=...')`. This is render-blocking and adds latency. Should use `<link rel="preconnect">` + `<link rel="stylesheet">` in the `<head>` or self-host fonts.
- [OK] **font-display:swap** — Included in the Google Fonts URL parameter (`&display=swap`).
- [ISSUE] **Three font families loaded** — Playfair Display (11 weights), Cormorant Garamond (5 weights), Inter (5 weights). That's 21 font variations — excessive and impacts LCP. Cormorant Garamond appears unused in CSS variables.

### CSS:
- [OK] **Single global CSS file** — `src/styles/global.css` imported in BaseLayout. Page-specific styles are scoped in `<style>` tags (Astro best practice).
- [ISSUE] **No `<link rel="preconnect">` for external resources** — No preconnect hints for `fonts.googleapis.com`, `fonts.gstatic.com`, or `images.unsplash.com` in the `<head>`.

---

## 10. Technical SEO

### Trailing Slashes:
- [ISSUE] **No trailingSlash config** — `astro.config.mjs` does not set `trailingSlash`. Astro defaults to `"ignore"`, which can lead to duplicate content with both `/castles` and `/castles/` resolving. Header links use trailing slashes (`/regions/scotland/`), while some page links don't (`/castles`, `/partners`). This inconsistency should be resolved.

### 404 Page:
- [MISSING] **No 404 page** — `src/pages/404.astro` does not exist. Users hitting invalid URLs will see Astro's default or the hosting platform's generic 404.

### Canonical URLs:
- [OK] **Canonical URLs present** — Auto-generated in BaseLayout (line 27) using `Astro.url.pathname` resolved against `https://rentacastle.uk`.

### Hreflang:
- [OK] **Not needed** — UK-only English site. No hreflang required.

### Mobile Viewport:
- [OK] **Viewport meta tag present** — `<meta name="viewport" content="width=device-width, initial-scale=1.0" />` (line 33, `BaseLayout.astro`).

### Favicon:
- [OK] **Favicon present** — `public/favicon.svg` exists. Referenced in BaseLayout as `<link rel="icon" type="image/svg+xml" href="/favicon.svg" />` (line 52).
- [ISSUE] **Only SVG favicon** — No PNG fallback (`favicon.ico`, `apple-touch-icon.png`) for older browsers and Apple devices.

### Language:
- [OK] **lang="en" on html tag** — Set in BaseLayout (line 31).

### Accessibility:
- [OK] **Skip to content link** — `<a href="#main-content" class="skip-link">Skip to main content</a>` (line 60, BaseLayout).
- [OK] **ARIA labels on navigation** — Header nav has `aria-label="Main navigation"`, breadcrumbs have `aria-label="Breadcrumb"`.

### Google Analytics:
- [OK] **GA4 configured** — `G-17XC2TGN5Q` tag present (lines 56-62, BaseLayout.astro).
- [ISSUE] **GA loaded with `is:inline` and no consent management** — No cookie consent/GDPR banner detected. For UK sites, this is a legal requirement under UK GDPR/PECR.

---

## 11. Content Quality

### Homepage:
- [OK] **Rich homepage content** — The homepage has substantial text across hero, stats, categories (6), regions (4), partners CTA, guides (4), and bottom CTA. Estimated 300-400 words of visible text plus dynamic castle/region data.

### Castle Descriptions:
- [OK] **Castle descriptions are unique** — Each castle in `src/data/castles.ts` has a unique `description`, `overview`, and `history` field. The first castle (Barcaldine) has a ~300-word overview. Amberley Castle has ~350 words. These are clearly individually written.
- [OK] **Extensive castle data** — 3,069 lines of castle data with 55+ castles, each having unique descriptions, highlights, amenities, nearby attractions, and reviews.

### Blog Post Content:
- [ISSUE] **CRITICAL: All blog posts share identical body content** — `src/pages/blog/[slug].astro` (lines 99-136) renders the same hardcoded paragraphs for every blog post regardless of the post's unique title/topic. The only unique parts are the title, description lead paragraph, date, and category. Every post says "Castle stays have become one of the most popular..." followed by identical generic content. This is devastating for SEO — Google will likely see these as thin/duplicate content.
- [ISSUE] **Blog word count is very low** — The templated body content is approximately 200 words of generic text. Combined with the unique description (~40 words), each blog post has roughly 240 words total. Google generally expects 1,000+ words for informational content to rank.

---

## 12. External Links / Rel Attributes

### Booking URLs:
- [OK] **Booking links have proper rel attributes** — `castles/[slug].astro` uses `rel="noopener sponsored"` on both booking link locations (line 96 and line 276). This correctly signals to Google that these are sponsored/affiliate links.
- [OK] **Booking links open in new tab** — `target="_blank"` is used on both booking CTAs.

### Footer External Links:
- [OK] **External links use rel="noopener noreferrer"** — Footer component (`Footer.astro`) applies `rel="noopener noreferrer"` on external links to English Heritage, Historic Houses, National Trust, and Visit Britain. However:
- [ISSUE] **Footer external links use `rel="noopener noreferrer"` but not `rel="noopener nofollow"`** — These are editorial links (not sponsored), so `nofollow` is technically not required. But `noreferrer` strips referrer information which prevents these sites from seeing RentACastle as a traffic source — this is counterproductive for partnership/link-building. Consider using just `rel="noopener"` instead.

---

## Summary of Issues

### Critical (Fix Immediately):
1. **All blog posts have identical templated content** — `src/pages/blog/[slug].astro` lines 99-136. Every post renders the same ~200 words regardless of topic. This will be seen as thin/duplicate content by Google.
2. **Double `| RentACastle` in title tags** — `castles/index.astro` (line 8), `regions/[slug].astro` (line 22), `castles/[slug].astro` (line 35) all pass titles that already include `| RentACastle`, causing BaseLayout to double it.
3. **Missing 404 page** — No `src/pages/404.astro` exists.

### High Priority:
4. **Google Fonts loaded via render-blocking @import** — `src/styles/global.css` line 8.
5. **Three font families with 21 weight variations** — Cormorant Garamond appears unused.
6. **No preconnect hints** for fonts.googleapis.com, fonts.gstatic.com, images.unsplash.com.
7. **Castle detail hero image missing perf attributes** — `castles/[slug].astro` line 57 (no loading, fetchpriority, width, height).
8. **No trailing slash config** — Mixed usage across the site.

### Medium Priority:
9. **og:type always "website"** — Blog posts should use "article" (BaseLayout line 38).
10. **Missing og:locale** — Should be `en_GB`.
11. **Article schema should be BlogPosting** — `blog/[slug].astro` line 60.
12. **Article schema missing dateModified and mainEntityOfPage** — `blog/[slug].astro` lines 60-69.
13. **No PNG/ICO favicon fallback** — Only SVG favicon provided.
14. **No Twitter @site/@creator handle** in meta tags.
15. **Guide card images on homepage missing width/height** — `index.astro` line 234.
16. **No GDPR cookie consent** — GA4 runs without consent management.

### Low Priority:
17. **Footer external links use noreferrer** — Strips referrer, counterproductive for partnerships.
18. **Two decorative images have empty alt** — Technically correct but could be more descriptive.
