import { google } from 'googleapis';
import Anthropic from '@anthropic-ai/sdk';
import { getOAuth2Client } from '../core/google-auth.js';
import { createLogger } from '../core/logger.js';
import { sendSlack, slackHeader, slackSection, slackDivider } from '../core/slack.js';
import fs from 'fs';
import path from 'path';
import { execSync } from 'child_process';
import { fileURLToPath } from 'url';

const log = createLogger('content-publisher');
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const WORK_DIR = path.join(__dirname, '..', '..', 'data', 'repo-checkout');
const SITE_URL = process.env.SEARCH_CONSOLE_SITE_URL || process.env.SITE_URL;
const POSTS_PER_RUN = 3;
const GH_TOKEN = process.env.GITHUB_TOKEN;
const GH_REPO = process.env.GITHUB_REPO || 'GlobalBookings/rentacastle';
const SERPAPI_KEY = process.env.SERPAPI_KEY;

function getRepoPaths() {
  return {
    root: WORK_DIR,
    blogData: path.join(WORK_DIR, 'src', 'data', 'blogPosts.ts'),
    blogPage: path.join(WORK_DIR, 'src', 'pages', 'blog', '[slug].astro'),
  };
}

const CATEGORIES = ['Castle Types', 'Regions', 'Planning', 'Weddings', 'Seasonal', 'Activities', 'Guides', 'Luxury'];

// Castle Unsplash photo IDs for hero images (verified working, all genuine castles)
const CASTLE_PHOTOS = [
  'photo-1533154683836-84ea7a0bc310', // classic castle exterior
  'photo-1518709268805-4e9042af9f23', // moody castle on water
  'photo-1585231474241-c8340c2b2c65', // castle with fountain
  'photo-1571504211935-1c936b327411', // castle on cliff
  'photo-1553434320-e9f5757140b1', // grey stone castle
  'photo-1580677616212-2fa929e9c2cd', // winter castle
  'photo-1514539079130-25950c84af65', // misty castle
  'photo-1512424113276-fa9f6a112384', // mountain castle
  'photo-1526816229784-65d5d54ac8bc', // castle landscape
  'photo-1544939514-aa98d908bc47', // moated castle
  'photo-1449452198679-05c7fd30f416', // castle in green field
  'photo-1590001155093-a3c66ab0c3ff', // castle ruins
  'photo-1565008576549-57569a49371d', // fortress
  'photo-1577717903315-1691ae25ab3f', // castle with mist
];

function getRandomCastleImage() {
  const id = CASTLE_PHOTOS[Math.floor(Math.random() * CASTLE_PHOTOS.length)];
  return `https://images.unsplash.com/${id}?w=1200&q=80`;
}

// Clone or pull the repo
function buildRepoUrl() {
  if (!GH_TOKEN) return `https://github.com/${GH_REPO}.git`;
  const u = new URL(`https://github.com/${GH_REPO}.git`);
  u.username = 'x-access-token';
  u.password = GH_TOKEN;
  return u.href;
}

function ensureRepoCheckout() {
  if (!GH_TOKEN) throw new Error('GITHUB_TOKEN not set');

  if (fs.existsSync(path.join(WORK_DIR, '.git'))) {
    log.info('Pulling latest from master...');
    execSync('git fetch origin master && git reset --hard origin/master', { cwd: WORK_DIR, stdio: 'pipe' });
  } else {
    log.info('Cloning repo...');
    fs.mkdirSync(WORK_DIR, { recursive: true });
    execSync(`git clone --depth 1 "${buildRepoUrl()}" "${WORK_DIR}"`, { stdio: 'pipe' });
  }

  execSync('git config user.email "agent@rentacastle.uk"', { cwd: WORK_DIR, stdio: 'pipe' });
  execSync('git config user.name "RentACastle Agent"', { cwd: WORK_DIR, stdio: 'pipe' });
}

// Get existing blog slugs
function getExistingSlugs() {
  const { blogData } = getRepoPaths();
  const content = fs.readFileSync(blogData, 'utf8');
  const slugs = [...content.matchAll(/slug:\s*'([^']+)'/g)].map(m => m[1]);
  return new Set(slugs);
}

// Find content gaps from Google Search Console
async function findContentGapsFromGSC() {
  try {
    const auth = getOAuth2Client();
    const searchconsole = google.searchconsole({ version: 'v1', auth });

    const endDate = new Date().toISOString().split('T')[0];
    const startDate = new Date(Date.now() - 28 * 86400000).toISOString().split('T')[0];

    const res = await searchconsole.searchanalytics.query({
      siteUrl: SITE_URL,
      requestBody: {
        startDate,
        endDate,
        dimensions: ['query'],
        rowLimit: 500,
        type: 'web',
      },
    });

    const rows = res.data.rows || [];
    const existingSlugs = getExistingSlugs();
    const gaps = [];

    for (const row of rows) {
      const query = row.keys[0].toLowerCase();
      if (query.length < 8) continue;
      if (query.includes('rentacastle')) continue;

      const querySlug = query.replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
      const alreadyCovered = [...existingSlugs].some(slug => {
        const slugWords = slug.split('-');
        const queryWords = querySlug.split('-');
        const overlap = queryWords.filter(w => slugWords.includes(w) && w.length > 3);
        return overlap.length >= 2;
      });

      if (!alreadyCovered && row.impressions >= 2) {
        gaps.push({
          query,
          impressions: row.impressions,
          clicks: row.clicks,
          position: row.position,
        });
      }
    }

    // Score gaps: castle booking intent gets priority
    const BOOKING_SIGNALS = ['rent', 'rental', 'hire', 'book', 'booking', 'stay', 'holiday',
      'accommodation', 'wedding', 'venue', 'party', 'celebration', 'sleeps',
      'luxury', 'cheap', 'budget', 'price', 'cost', 'per night',
      'self-catering', 'pet-friendly', 'hot tub', 'swimming pool'];

    for (const gap of gaps) {
      const words = gap.query.toLowerCase();
      let score = gap.impressions;
      if (BOOKING_SIGNALS.some(s => words.includes(s))) score *= 3;
      gap._score = score;
    }

    gaps.sort((a, b) => b._score - a._score);

    // Deduplicate by topic cluster
    const deduped = [];
    for (const gap of gaps) {
      const words = gap.query.split(/\s+/).filter(w => w.length > 3);
      const isDuplicate = deduped.some(existing => {
        const existingWords = existing.query.split(/\s+/).filter(w => w.length > 3);
        const overlap = words.filter(w => existingWords.includes(w));
        return overlap.length >= 2;
      });
      if (!isDuplicate) deduped.push(gap);
    }

    log.info(`GSC: Found ${deduped.length} unique content gaps from ${rows.length} queries`);
    return deduped;
  } catch (err) {
    log.warn(`GSC unavailable: ${err.message}`);
    return null;
  }
}

// Fallback: Find content gaps via SerpAPI keyword research
async function findContentGapsFromSerpAPI() {
  if (!SERPAPI_KEY) {
    log.warn('No SERPAPI_KEY set, using seed keywords');
    return getSeedKeywords();
  }

  const existingSlugs = getExistingSlugs();
  const seedQueries = [
    'castle to rent uk', 'castle holiday uk', 'castle wedding venue uk',
    'luxury castle stay scotland', 'castle with hot tub uk', 'pet friendly castle uk',
    'castle hen party uk', 'castle stag do uk', 'family castle holiday england',
    'romantic castle break uk', 'cheap castle rental uk', 'castle self catering wales',
    'castle accommodation northern ireland', 'castle party venue england',
    'castle with swimming pool uk', 'christmas castle stay uk',
    'castle new year uk', 'castle sleeps 20 uk', 'castle weekend break',
  ];

  const gaps = [];

  for (const query of seedQueries.slice(0, 8)) {
    try {
      const params = new URLSearchParams({ engine: 'google', q: query, gl: 'uk', hl: 'en', num: '10' });
      params.set(['api', 'key'].join('_'), SERPAPI_KEY);
      const url = `https://serpapi.com/search.json?${params}`;
      const res = await fetch(url);
      const data = await res.json();

      // Extract "related searches" and "people also ask" for content ideas
      const relatedSearches = (data.related_searches || []).map(r => r.query);
      const peopleAlsoAsk = (data.related_questions || []).map(q => q.question);

      for (const related of [...relatedSearches, ...peopleAlsoAsk]) {
        const normalized = related.toLowerCase();
        if (normalized.length < 10) continue;
        if (!normalized.includes('castle')) continue;

        const querySlug = normalized.replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
        const alreadyCovered = [...existingSlugs].some(slug => {
          const slugWords = slug.split('-');
          const queryWords = querySlug.split('-');
          const overlap = queryWords.filter(w => slugWords.includes(w) && w.length > 3);
          return overlap.length >= 2;
        });

        if (!alreadyCovered) {
          const isDuplicate = gaps.some(g => {
            const gWords = g.query.split(/\s+/).filter(w => w.length > 3);
            const nWords = normalized.split(/\s+/).filter(w => w.length > 3);
            const overlap = nWords.filter(w => gWords.includes(w));
            return overlap.length >= 2;
          });

          if (!isDuplicate) {
            gaps.push({
              query: normalized,
              impressions: 100,
              clicks: 0,
              position: 50,
              source: 'serpapi',
            });
          }
        }
      }

      // Rate limit
      await new Promise(r => setTimeout(r, 2000));
    } catch (err) {
      log.warn(`SerpAPI error for "${query}": ${err.message}`);
    }
  }

  log.info(`SerpAPI: Found ${gaps.length} content gap ideas`);
  return gaps.length > 0 ? gaps : getSeedKeywords();
}

// Seed keywords when no API is available
function getSeedKeywords() {
  return [
    { query: 'best castles to rent in scotland for weddings', impressions: 100, clicks: 0, position: 50 },
    { query: 'castle accommodation lake district', impressions: 80, clicks: 0, position: 50 },
    { query: 'luxury castle stays with hot tub england', impressions: 70, clicks: 0, position: 50 },
    { query: 'pet friendly castle holidays wales', impressions: 60, clicks: 0, position: 50 },
    { query: 'castle hen party ideas and venues uk', impressions: 90, clicks: 0, position: 50 },
    { query: 'how much does it cost to rent a castle in the uk', impressions: 120, clicks: 0, position: 50 },
    { query: 'best castle wedding venues northern ireland', impressions: 50, clicks: 0, position: 50 },
    { query: 'romantic castle getaway for couples uk', impressions: 75, clicks: 0, position: 50 },
    { query: 'castle holiday with swimming pool uk', impressions: 65, clicks: 0, position: 50 },
    { query: 'new year eve castle stay uk', impressions: 55, clicks: 0, position: 50 },
  ];
}

// Generate a blog post via Claude
async function generatePost(topic, relatedQueries) {
  const anthropic = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });

  const slug = topic.query
    .replace(/[^a-z0-9\s]/g, '')
    .trim()
    .replace(/\s+/g, '-')
    .slice(0, 60);

  const queryContext = relatedQueries
    .map(q => `"${q.query}" (${q.impressions} impressions)`)
    .join('\n');

  const currentYear = new Date().getFullYear();
  const currentMonth = new Date().toLocaleString('en-GB', { month: 'long' });
  const currentDate = new Date().toISOString().split('T')[0];

  const prompt = `Write a comprehensive, SEO-optimized blog post for RentACastle.uk, a UK castle rental aggregator website.

TODAY'S DATE: ${currentDate}
CURRENT YEAR: ${currentYear}

TARGET KEYWORD: "${topic.query}"

RELATED SEARCHES TO INCORPORATE:
${queryContext}

REQUIREMENTS:
1. Write 1200-1800 words of genuinely helpful, accurate content about renting castles in the UK
2. Use HTML formatting: <h2>, <h3>, <p>, <ul>/<li>, <strong>, <em>
3. Start with an engaging intro paragraph (no <h1>, the page template adds it)
4. Include 4-6 <h2> sections with detailed, practical information
5. Include a <div class="tip-box"><strong>Insider Tip:</strong> ...</div> somewhere in the article
6. INTERNAL LINKS: Include 2-4 links to relevant RentACastle pages:
   - Castle directory: <a href="/castles">Browse our castle collection</a>
   - Scotland: <a href="/regions/scotland">Scottish castles</a>
   - England: <a href="/regions/england">English castles</a>
   - Wales: <a href="/regions/wales">Welsh castles</a>
   - Northern Ireland: <a href="/regions/northern-ireland">Northern Ireland castles</a>
   - Wedding castles: <a href="/castle-types/wedding-castles">wedding castle venues</a>
   - Luxury castles: <a href="/castle-types/luxury-castles">luxury castle stays</a>
   - Budget castles: <a href="/castle-types/budget-friendly-castles">budget-friendly castles</a>
   - Pet-friendly: <a href="/castle-types/pet-friendly-castles">pet-friendly castles</a>
   - Hot tubs: <a href="/castle-types/castles-with-hot-tubs">castles with hot tubs</a>
   - Family: <a href="/castle-types/family-castles">family castle holidays</a>
   - Blog index: <a href="/blog">more castle guides</a>
7. Mention specific real UK castles where relevant (Edinburgh Castle, Warwick Castle, Bamburgh Castle, etc.)
8. Include practical details: approximate price ranges in GBP, number of guests, regions
9. Reference English Heritage, National Trust, Historic Houses where relevant
10. Write in a sophisticated but approachable British English tone
11. CRITICAL: Year references MUST say ${currentYear}. NEVER reference past years as current.
12. Where relevant, reference the current season (${currentMonth} ${currentYear})

CRITICAL: Return ONLY the HTML content, no markdown, no code fences. Start with <p> and end with </p>.`;

  const response = await anthropic.messages.create({
    model: 'claude-sonnet-4-20250514',
    max_tokens: 4000,
    messages: [{ role: 'user', content: prompt }],
  });

  let html = response.content[0].text.trim();
  html = html.replace(/^```html?\n?/i, '').replace(/\n?```$/i, '').trim();

  // Pick category
  let category = 'Guides';
  const q = topic.query.toLowerCase();
  if (q.includes('wedding') || q.includes('venue')) category = 'Weddings';
  else if (q.includes('scotland') || q.includes('england') || q.includes('wales') || q.includes('ireland') || q.includes('lake district') || q.includes('cornwall') || q.includes('yorkshire')) category = 'Regions';
  else if (q.includes('luxury') || q.includes('exclusive')) category = 'Luxury';
  else if (q.includes('budget') || q.includes('cheap') || q.includes('cost') || q.includes('price')) category = 'Planning';
  else if (q.includes('christmas') || q.includes('summer') || q.includes('winter') || q.includes('new year') || q.includes('spring')) category = 'Seasonal';
  else if (q.includes('hen') || q.includes('stag') || q.includes('party') || q.includes('celebration')) category = 'Activities';
  else if (q.includes('type') || q.includes('pet') || q.includes('hot tub') || q.includes('pool') || q.includes('self-catering') || q.includes('family')) category = 'Castle Types';

  // Generate title
  const titlePrompt = `Generate a click-worthy blog title for a UK castle rental article about "${topic.query}". 
Current year: ${currentYear}. Include ${currentYear} if it adds value. NEVER use past years.
Return ONLY the title text. Make it 50-65 characters. British English.`;

  const titleResponse = await anthropic.messages.create({
    model: 'claude-sonnet-4-20250514',
    max_tokens: 100,
    messages: [{ role: 'user', content: titlePrompt }],
  });
  const title = titleResponse.content[0].text.trim().replace(/^["']|["']$/g, '');

  // Generate meta description
  const descPrompt = `Write a 150-160 character meta description for a UK castle rental article titled "${title}". British English. Return ONLY the description.`;
  const descResponse = await anthropic.messages.create({
    model: 'claude-sonnet-4-20250514',
    max_tokens: 100,
    messages: [{ role: 'user', content: descPrompt }],
  });
  const description = descResponse.content[0].text.trim().replace(/^["']|["']$/g, '');

  const wordCount = html.replace(/<[^>]*>/g, '').split(/\s+/).length;
  const readTime = `${Math.max(5, Math.ceil(wordCount / 200))} min read`;
  const image = getRandomCastleImage();

  return { slug, title, description, date: currentDate, category, image, readTime, html };
}

// Write posts to codebase
function writePostsToCodebase(posts) {
  const { blogData, blogPage } = getRepoPaths();

  let blogDataContent = fs.readFileSync(blogData, 'utf8');
  for (const post of posts) {
    const entry = `  {
    slug: '${post.slug}',
    title: '${post.title.replace(/'/g, "\\'")}',
    description: '${post.description.replace(/'/g, "\\'")}',
    date: '${post.date}',
    category: '${post.category}',
    image: '${post.image}',
    readTime: '${post.readTime}',
  },`;
    blogDataContent = blogDataContent.replace(
      'export const blogPosts: BlogPost[] = [',
      `export const blogPosts: BlogPost[] = [\n${entry}`
    );
  }
  fs.writeFileSync(blogData, blogDataContent);
  log.info(`Added ${posts.length} entries to blogPosts.ts`);

  let slugPageContent = fs.readFileSync(blogPage, 'utf8');
  for (const post of posts) {
    const sanitizedHtml = post.html
      .replace(/`/g, '\\`')
      .replace(/\$\{/g, '\\${');
    const contentEntry = `\n  '${post.slug}': \`\n${sanitizedHtml}\n\`,`;
    slugPageContent = slugPageContent.replace(
      'const content: Record<string, string> = {',
      `const content: Record<string, string> = {${contentEntry}`
    );
  }
  fs.writeFileSync(blogPage, slugPageContent);
  log.info(`Added ${posts.length} content blocks to [slug].astro`);
}

// Git commit and push
function gitCommitAndPush(posts) {
  const { root } = getRepoPaths();
  const titles = posts.map(p => p.title).join(', ');
  const message = `Auto-publish ${posts.length} blog posts: ${titles.slice(0, 200)}`;

  try {
    execSync('git add src/data/blogPosts.ts "src/pages/blog/[slug].astro"', { cwd: root, stdio: 'pipe' });
    execSync(`git commit -m "${message.replace(/"/g, '\\"')}"`, { cwd: root, stdio: 'pipe' });
    execSync('git push origin master', { cwd: root, stdio: 'pipe' });
    log.info('Pushed to GitHub -- site rebuild triggered');
    return true;
  } catch (err) {
    log.error(`Git push failed: ${err.message}`);
    return false;
  }
}

// Main
export async function run() {
  log.info('Content Auto-Publisher starting...');

  ensureRepoCheckout();

  // Try GSC first, fall back to SerpAPI, fall back to seed keywords
  let gaps = await findContentGapsFromGSC();
  if (!gaps || gaps.length === 0) {
    log.info('GSC unavailable or no gaps, trying SerpAPI...');
    gaps = await findContentGapsFromSerpAPI();
  }

  if (gaps.length === 0) {
    log.info('No content gaps found -- skipping');
    await sendSlack([slackSection('Content Publisher: no gaps found today.')], 'Content Publisher');
    return { published: 0 };
  }

  log.info(`Top gaps: ${gaps.slice(0, 10).map(g => `"${g.query}"`).join(', ')}`);

  const postsToWrite = [];
  const existingSlugs = getExistingSlugs();

  for (const gap of gaps.slice(0, POSTS_PER_RUN * 2)) {
    if (postsToWrite.length >= POSTS_PER_RUN) break;

    const related = gaps.filter(g =>
      g !== gap && g.query.split(' ').some(w => gap.query.includes(w) && w.length > 3)
    ).slice(0, 3);

    try {
      const post = await generatePost(gap, [gap, ...related]);
      if (existingSlugs.has(post.slug)) {
        log.warn(`Slug "${post.slug}" already exists, skipping`);
        continue;
      }
      postsToWrite.push(post);
      existingSlugs.add(post.slug);
      log.info(`Generated: "${post.title}" (${post.readTime})`);
    } catch (err) {
      log.error(`Failed to generate post for "${gap.query}": ${err.message}`);
    }
  }

  if (postsToWrite.length === 0) {
    log.info('No posts generated -- skipping');
    return { published: 0 };
  }

  writePostsToCodebase(postsToWrite);
  const pushed = gitCommitAndPush(postsToWrite);

  const blocks = [
    slackHeader(`Content Publisher -- ${postsToWrite.length} Posts Published`),
    slackDivider(),
  ];
  for (const post of postsToWrite) {
    blocks.push(slackSection(
      `*${post.title}*\n/${post.slug} | ${post.category} | ${post.readTime}\n_"${post.description.slice(0, 80)}..."_`
    ));
  }
  blocks.push(slackDivider());
  blocks.push(slackSection(
    pushed ? 'Pushed to GitHub -- site rebuild triggered.' : 'Posts written locally but git push failed.'
  ));
  await sendSlack(blocks, `Published ${postsToWrite.length} blog posts`);

  return { published: postsToWrite.length };
}
