# RentACastle Project Memory

## Project Overview
- **Site:** rentacastle.uk -- UK castle rental aggregator with affiliate/partnership revenue model
- **Domain:** rentacastle.uk (NOT .co.uk)
- **GitHub:** GlobalBookings/rentacastle (master branch)
- **Tech:** Astro 5.17.1 static site + sitemap integration
- **Hosting:** DigitalOcean App Platform (auto-deploy from GitHub master)
- **Analytics:** Google Analytics G-17XC2TGN5Q (in BaseLayout.astro)
- **Build:** `npx astro build` -> 108 pages, output to `dist/`

## Architecture (modeled on BanffBound)
```
rentacastle/
├── astro.config.mjs          # site: rentacastle.uk, static output, sitemap
├── src/
│   ├── layouts/BaseLayout.astro   # Meta, OG, GA tag, imports Header/Footer/global.css
│   ├── styles/global.css          # Premium luxury design system
│   ├── components/
│   │   ├── Header.astro           # Fixed header, mega-menu (Regions/Types/Plan), mobile overlay
│   │   ├── Footer.astro           # Dark bg, 4-column, external heritage links
│   │   └── Breadcrumbs.astro      # BreadcrumbList schema.org
│   ├── data/
│   │   ├── castles.ts             # 56 castles (23 curated + 33 scraped), Castle interface
│   │   └── blogPosts.ts           # 18 blog posts, BlogPost interface
│   └── pages/
│       ├── index.astro            # Hero slideshow, stats, categories, regions, blog
│       ├── castles/
│       │   ├── index.astro        # Castle directory grid
│       │   └── [slug].astro       # Castle detail (gallery, booking strip, schema)
│       ├── regions/
│       │   ├── index.astro        # Region overview
│       │   ├── [slug].astro       # Dynamic region pages (Scotland/England/Wales/NI)
│       │   └── 8 sub-regions      # scottish-highlands, lake-district, cornwall, yorkshire,
│       │                          # cotswolds, pembrokeshire, norfolk, northumberland
│       ├── castle-types/          # 10 filter pages
│       │   ├── wedding-castles, luxury-castles, budget-friendly-castles
│       │   ├── pet-friendly-castles, castles-with-hot-tubs, family-castles
│       │   ├── romantic-castles, historic-castles, castles-for-parties
│       │   └── self-catering-castles
│       ├── guides/                # 6 guide pages
│       │   ├── how-to-rent-a-castle, packing-list, best-time-to-visit
│       │   ├── castle-wedding-guide, group-booking-guide, castle-etiquette
│       ├── blog/
│       │   ├── index.astro        # Blog listing
│       │   └── [slug].astro       # Blog detail (content stored as Record<string,string>)
│       ├── faq.astro              # 10 questions, FAQ schema markup
│       └── partners.astro         # List Your Castle CTA
├── scripts/
│   ├── scrape_castles.py          # SerpAPI scraper (292 listings from 41 queries)
│   ├── normalize.py               # Clean/normalize scraped data
│   ├── deduplicate.py             # Fuzzy dedup
│   ├── enrich.py                  # Add details per castle
│   ├── export_to_site.py          # Convert to TypeScript
│   ├── run_pipeline.py            # Orchestrate full pipeline
│   └── verify_images.py           # Check all Unsplash URLs return HTTP 200
└── agents/                        # SEO automation system
    ├── package.json               # ESM, node-cron, anthropic, googleapis, express
    ├── app-spec.yaml              # DigitalOcean App Platform worker spec
    ├── docker-compose.yml         # Docker deployment
    ├── Dockerfile                 # Node 20 slim
    ├── deploy.sh                  # Droplet deployment script
    ├── .env                       # API keys (gitignored)
    ├── .env.example               # Template
    └── src/
        ├── index.js               # Main entry: schedules all agents, starts approval server
        ├── run.js                 # CLI runner: `node src/run.js <agent-name>`
        ├── core/
        │   ├── logger.js          # Leveled logger [timestamp] [LEVEL] [agent]
        │   ├── scheduler.js       # node-cron, Europe/London timezone
        │   ├── slack.js           # Webhook + Block Kit helpers, dry-run fallback
        │   ├── google-auth.js     # OAuth2 client with refresh token
        │   └── approval.js        # Express server :3100, Slack interactive buttons
        ├── agents/
        │   ├── content-publisher.js  # Auto-generates 3 blog posts/run via Claude
        │   ├── keyword-miner.js     # GSC or SerpAPI keyword research
        │   └── internal-linker.js   # Cross-links under-linked blog posts
        └── utils/
            └── sitemap.js         # Fetch/parse sitemap-index.xml

```

## Design System
- **Palette:** Royal purple-black primary (#1a1423), antique gold accent (#c4a265), warm ivory bg (#faf9f7)
- **Typography:** Cormorant Garamond (headings) + Playfair Display (display) + Inter (body)
- **Cards:** 16px radius, 1px border, soft shadows, 3/2 aspect ratio, translateY(-6px) hover
- **Buttons:** border-radius 0 (square), uppercase, 0.08em letter-spacing
- **Header:** Fixed, transparent-to-white on scroll, mega-menu dropdowns
- **Footer:** Dark (#0f0a14), gold border-top, 4 columns

## Castle Data (56 total)
- **Interface fields:** slug, name, region, county, type, priceRange, avgPrice, sleeps, bedrooms, bathrooms, bookingUrl, image, description, highlights, nearbyAttractions, overview, amenities, weddingSuitable, petFriendly, selfCatering, hasHotTub, hasPool, hasWifi, parkingSpaces, yearBuilt, lastRenovated, reviewScore, reviewLabel, reviewCount, history, lat, lng, images, bookingPlatform
- **Regions:** Scotland (23), England (26), Wales (5), Northern Ireland (3)
- **Sources:** 23 hand-curated with rich content + 33 from SerpAPI scraping pipeline
- **All 56 castles have real booking URLs** (official sites, Airbnb, Sykes Cottages, Coolstays, Oliver's Travels, etc.)

## Blog Posts (18 total)
- Categories: Castle Types, Regions, Planning, Weddings, Seasonal, Activities, Guides, Luxury
- Content stored inline in [slug].astro as `const content: Record<string, string> = { 'slug': `html` }`
- Topics: wedding guide, budget castles, pet-friendly, hen parties, romantic breaks, hot tubs, Christmas, Wales, family, castle vs hotel, wedding venues, packing list, history, cheapest, NYE, large groups, summer

## Images
- All from Unsplash (free, no attribution required)
- 62 unique URLs, all verified HTTP 200
- Verified castle photo IDs (no Disney, no hotels, no modern houses):
  - photo-1533154683836-84ea7a0bc310 (classic exterior)
  - photo-1518709268805-4e9042af9f23 (castle reflection)
  - photo-1585231474241-c8340c2b2c65 (castle fountain)
  - photo-1571504211935-1c936b327411 (cliff castle)
  - photo-1553434320-e9f5757140b1 (grey stone)
  - photo-1580677616212-2fa929e9c2cd (winter castle)
  - photo-1514539079130-25950c84af65 (misty castle)
  - photo-1512424113276-fa9f6a112384 (mountain castle)
  - photo-1526816229784-65d5d54ac8bc (castle landscape)
  - photo-1544939514-aa98d908bc47 (moated castle)
  - photo-1486272812091-a9bf3c6376c5 (castle interior)
  - photo-1449452198679-05c7fd30f416 (green field)

## SEO Features
- Schema.org: LodgingBusiness (castle pages), BreadcrumbList, WebSite+Organization (homepage), FAQ schema
- Sitemap auto-generated via @astrojs/sitemap
- 108 indexable pages
- Internal linking across regions, castle types, guides, blog
- Meta descriptions and Open Graph tags on all pages

## Agent System
- **content-publisher:** Daily 12pm UK. Finds content gaps (GSC -> SerpAPI fallback -> seed keywords). Generates 3 posts via Claude sonnet. Writes to blogPosts.ts + [slug].astro. Commits and pushes.
- **keyword-miner:** Monday 9am UK. Queries GSC for quick wins (pos 5-20), content gaps (high impr low CTR), declines, clusters. Falls back to SerpAPI research. Reports to Slack.
- **internal-linker:** Thursday 1pm UK. Parses all blog content, builds link graph, finds under-linked posts (<2 inbound), inserts contextual links by topic relevance. Max 15 links/run, 3/post.
- **Run individually:** `cd agents && npm run content|keywords|links`
- **Run all on schedule:** `cd agents && npm start`
- **Approval server:** Express on :3100, Slack interactive buttons for approve/reject

## API Keys (in agents/.env, gitignored)
- ANTHROPIC_API_KEY: configured (sk-ant-api03-rs2B...)
- SERPAPI_KEY: configured (76613601d506...)
- GITHUB_TOKEN: configured (user added)
- GOOGLE_CLIENT_ID/SECRET/REFRESH_TOKEN: not yet configured
- SLACK_WEBHOOK_URL: not yet configured
- GA4_PROPERTY_ID: not yet configured
- RESEND_API_KEY: not yet configured

## Deployment
- **Static site:** DigitalOcean App Platform, auto-deploys from GitHub master
- **Agents:** App Platform worker component (agents/app-spec.yaml), London region, 1x apps-s-1vcpu-0.5gb
- **Secrets** (ANTHROPIC_API_KEY, GITHUB_TOKEN, SERPAPI_KEY, SLACK_WEBHOOK_URL) set via DO dashboard

## Scraping Pipeline (scripts/)
- Uses SerpAPI for Google search results (avoids blocks)
- 41 castle-rental queries -> 292 raw listings -> normalize -> deduplicate -> 33 genuine castles exported
- Pipeline: scrape_castles.py -> normalize.py -> deduplicate.py -> enrich.py -> export_to_site.py
- Orchestrated by run_pipeline.py

## Git History
```
15cc136 Fix app-spec dockerfile path for App Platform deployment
de1e00f Add SEO agent system
1008ce5 Fix all booking URLs + 3 broken images
4052678 Add 25 missing pages + replace all non-castle imagery
7d88178 Premium luxury redesign + merge 33 scraped castles (56 total)
968a568 Add castle scraping pipeline (SerpAPI + normalize + dedupe + export)
4fed9a5 Add Google Analytics tag (G-17XC2TGN5Q)
10656ce Update domain to rentacastle.uk across all files
b03bfba Initial build: RentACastle UK castle rental directory
```

## What's Still Needed
- [ ] Deploy agents to DigitalOcean App Platform (app-spec.yaml ready)
- [ ] Google Search Console verification + OAuth setup for keyword-miner
- [ ] Slack webhook for agent reports
- [ ] Content velocity: run content-publisher to start generating posts
- [ ] GA4 property ID for analytics agent (future)
- [ ] Resend API key for email outreach agent (future)
- [ ] Additional agents from BanffBound to port: rank-tracker, content-refresher, blogger-outreach, journalist-pitcher, infographic-generator
- [ ] More castles: re-run scraping pipeline periodically to add new listings
- [ ] Castle owner partnerships: partners.astro page exists, needs outreach
