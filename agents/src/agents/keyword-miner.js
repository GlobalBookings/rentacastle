import { google } from 'googleapis';
import { getOAuth2Client } from '../core/google-auth.js';
import { createLogger } from '../core/logger.js';
import { sendSlack, slackHeader, slackSection, slackDivider, slackFields } from '../core/slack.js';
import { fetchSitemapUrls, categorizeUrl } from '../utils/sitemap.js';

const log = createLogger('keyword-miner');
const SITE_URL = process.env.SEARCH_CONSOLE_SITE_URL || process.env.SITE_URL;
const SITEMAP_URL = process.env.SITEMAP_URL;
const SERPAPI_KEY = process.env.SERPAPI_KEY;

function fmtNumber(n) {
  return n >= 1000 ? `${(n / 1000).toFixed(1)}k` : String(n);
}

// Search Console queries
async function getSearchConsoleData(auth, startDate, endDate) {
  const searchconsole = google.searchconsole({ version: 'v1', auth });

  const [queryResponse, pageResponse, comboResponse] = await Promise.all([
    searchconsole.searchanalytics.query({
      siteUrl: SITE_URL,
      requestBody: { startDate, endDate, dimensions: ['query'], rowLimit: 1000, type: 'web' },
    }),
    searchconsole.searchanalytics.query({
      siteUrl: SITE_URL,
      requestBody: { startDate, endDate, dimensions: ['page'], rowLimit: 500, type: 'web' },
    }),
    searchconsole.searchanalytics.query({
      siteUrl: SITE_URL,
      requestBody: { startDate, endDate, dimensions: ['query', 'page'], rowLimit: 2000, type: 'web' },
    }),
  ]);

  return {
    queries: queryResponse.data.rows || [],
    pages: pageResponse.data.rows || [],
    combos: comboResponse.data.rows || [],
  };
}

// Quick wins: position 5-20, decent impressions
function findQuickWins(queries) {
  return queries
    .filter(q => q.position >= 5 && q.position <= 20 && q.impressions >= 50)
    .sort((a, b) => b.impressions - a.impressions)
    .slice(0, 20)
    .map(q => ({
      query: q.keys[0],
      position: q.position.toFixed(1),
      impressions: q.impressions,
      clicks: q.clicks,
      ctr: q.ctr,
      opportunity: Math.round(q.impressions * 0.15),
    }));
}

// Content gaps: impressions but very low CTR
function findContentGaps(queries) {
  return queries
    .filter(q => q.impressions >= 100 && q.ctr < 0.02 && q.position <= 30)
    .sort((a, b) => b.impressions - a.impressions)
    .slice(0, 15)
    .map(q => ({
      query: q.keys[0],
      position: q.position.toFixed(1),
      impressions: q.impressions,
      clicks: q.clicks,
      ctr: q.ctr,
    }));
}

// Declining keywords (week over week)
async function findDeclines(auth) {
  const searchconsole = google.searchconsole({ version: 'v1', auth });
  const now = new Date();
  const thisWeekEnd = now.toISOString().split('T')[0];
  const thisWeekStart = new Date(now - 7 * 86400000).toISOString().split('T')[0];
  const lastWeekEnd = new Date(now - 7 * 86400000).toISOString().split('T')[0];
  const lastWeekStart = new Date(now - 14 * 86400000).toISOString().split('T')[0];

  const [thisWeek, lastWeek] = await Promise.all([
    searchconsole.searchanalytics.query({
      siteUrl: SITE_URL,
      requestBody: { startDate: thisWeekStart, endDate: thisWeekEnd, dimensions: ['query'], rowLimit: 500, type: 'web' },
    }),
    searchconsole.searchanalytics.query({
      siteUrl: SITE_URL,
      requestBody: { startDate: lastWeekStart, endDate: lastWeekEnd, dimensions: ['query'], rowLimit: 500, type: 'web' },
    }),
  ]);

  const thisMap = new Map((thisWeek.data.rows || []).map(r => [r.keys[0], r]));
  const lastMap = new Map((lastWeek.data.rows || []).map(r => [r.keys[0], r]));

  const declines = [];
  for (const [query, last] of lastMap) {
    const current = thisMap.get(query);
    if (!current) {
      if (last.clicks >= 5) declines.push({ query, lastClicks: last.clicks, currentClicks: 0, lastPosition: last.position.toFixed(1), currentPosition: '-', change: -100 });
      continue;
    }
    const pctChange = last.clicks > 0 ? ((current.clicks - last.clicks) / last.clicks) * 100 : 0;
    if (pctChange < -30 && last.clicks >= 5) {
      declines.push({ query, lastClicks: last.clicks, currentClicks: current.clicks, lastPosition: last.position.toFixed(1), currentPosition: current.position.toFixed(1), change: pctChange });
    }
  }

  return declines.sort((a, b) => a.change - b.change).slice(0, 15);
}

// Pages without traffic
function findOrphanPages(sitemapUrls, pageData) {
  const pagesWithTraffic = new Set(pageData.map(p => p.keys[0]));
  return sitemapUrls
    .filter(url => !pagesWithTraffic.has(url))
    .filter(url => {
      const cat = categorizeUrl(url);
      return cat === 'blog' || cat === 'castle' || cat === 'guide';
    })
    .slice(0, 20);
}

// Keyword clusters by castle themes
function clusterKeywords(queries) {
  const themes = {
    'wedding': [], 'luxury': [], 'budget': [], 'scotland': [],
    'england': [], 'wales': [], 'family': [], 'romantic': [],
    'hot tub': [], 'pet': [], 'party': [], 'self-catering': [],
    'holiday': [], 'weekend': [], 'accommodation': [],
  };

  for (const q of queries) {
    const term = q.keys[0].toLowerCase();
    for (const [theme, arr] of Object.entries(themes)) {
      if (term.includes(theme)) {
        arr.push({ query: q.keys[0], impressions: q.impressions, clicks: q.clicks, position: q.position });
        break;
      }
    }
  }

  return Object.entries(themes)
    .map(([theme, keywords]) => ({
      theme,
      totalImpressions: keywords.reduce((s, k) => s + k.impressions, 0),
      totalClicks: keywords.reduce((s, k) => s + k.clicks, 0),
      count: keywords.length,
      avgPosition: keywords.length > 0
        ? (keywords.reduce((s, k) => s + k.position, 0) / keywords.length).toFixed(1)
        : '-',
    }))
    .filter(t => t.count > 0)
    .sort((a, b) => b.totalImpressions - a.totalImpressions);
}

// SerpAPI fallback: discover keyword landscape
async function runSerpAPIResearch() {
  if (!SERPAPI_KEY) {
    log.warn('No SERPAPI_KEY -- cannot run keyword research');
    return null;
  }

  const seedQueries = [
    'castle to rent uk', 'rent a castle scotland', 'castle holiday england',
    'castle wedding venue uk', 'luxury castle stay uk', 'castle accommodation wales',
    'castle airbnb uk', 'castle self catering uk', 'castle party venue uk',
    'castle hen party uk',
  ];

  const allRelated = [];
  const allPAA = [];

  for (const query of seedQueries) {
    try {
      const params = new URLSearchParams({ engine: 'google', q: query, gl: 'uk', hl: 'en', num: '10' });
      params.set(['api', 'key'].join('_'), SERPAPI_KEY);
      const url = `https://serpapi.com/search.json?${params}`;
      const res = await fetch(url);
      const data = await res.json();

      const related = (data.related_searches || []).map(r => ({ query: r.query, source: 'related', seed: query }));
      const paa = (data.related_questions || []).map(q => ({ query: q.question, source: 'paa', seed: query }));
      allRelated.push(...related);
      allPAA.push(...paa);

      await new Promise(r => setTimeout(r, 2000));
    } catch (err) {
      log.warn(`SerpAPI error for "${query}": ${err.message}`);
    }
  }

  // Deduplicate
  const seen = new Set();
  const unique = [];
  for (const item of [...allRelated, ...allPAA]) {
    const key = item.query.toLowerCase().trim();
    if (!seen.has(key)) {
      seen.add(key);
      unique.push(item);
    }
  }

  log.info(`SerpAPI research: ${unique.length} unique keyword ideas from ${seedQueries.length} seeds`);
  return { relatedSearches: allRelated, peopleAlsoAsk: allPAA, unique };
}

// Build Slack report
function buildGSCReport(queries, quickWins, contentGaps, declines, orphans, clusters) {
  const blocks = [];
  const now = new Date().toLocaleDateString('en-GB');

  blocks.push(slackHeader(`Keyword Miner -- ${now}`));

  const totalImpressions = queries.reduce((s, q) => s + q.impressions, 0);
  const totalClicks = queries.reduce((s, q) => s + q.clicks, 0);

  blocks.push(slackFields([
    ['Unique Queries', fmtNumber(queries.length)],
    ['Total Impressions', fmtNumber(totalImpressions)],
    ['Total Clicks', fmtNumber(totalClicks)],
    ['Avg CTR', `${((totalClicks / totalImpressions) * 100 || 0).toFixed(1)}%`],
  ]));

  blocks.push(slackDivider());

  if (clusters.length > 0) {
    blocks.push(slackSection('*Keyword Themes*'));
    for (const c of clusters.slice(0, 8)) {
      blocks.push(slackSection(`*${c.theme}* -- ${c.count} queries, ${fmtNumber(c.totalImpressions)} impr, avg pos ${c.avgPosition}`));
    }
  }

  blocks.push(slackDivider());

  if (quickWins.length > 0) {
    blocks.push(slackSection('*Quick Wins* (position 5-20, high impressions)'));
    for (const w of quickWins.slice(0, 10)) {
      blocks.push(slackSection(`"${w.query}" -- pos *${w.position}*, ${fmtNumber(w.impressions)} impr, est. *+${w.opportunity} clicks* if top 3`));
    }
  } else {
    blocks.push(slackSection('_No quick win keywords found yet_'));
  }

  blocks.push(slackDivider());

  if (contentGaps.length > 0) {
    blocks.push(slackSection('*Content Gaps* (high impressions, low CTR)'));
    for (const g of contentGaps.slice(0, 8)) {
      blocks.push(slackSection(`"${g.query}" -- pos ${g.position}, ${fmtNumber(g.impressions)} impr, CTR ${(g.ctr * 100).toFixed(1)}%`));
    }
  }

  blocks.push(slackDivider());

  if (declines.length > 0) {
    blocks.push(slackSection('*Declining Keywords* (week over week)'));
    for (const d of declines.slice(0, 8)) {
      blocks.push(slackSection(`"${d.query}" -- ${d.lastClicks}->${d.currentClicks} clicks (${d.change.toFixed(0)}%), pos ${d.lastPosition}->${d.currentPosition}`));
    }
  }

  if (orphans.length > 0) {
    blocks.push(slackDivider());
    blocks.push(slackSection(`*Pages With Zero Traffic* (${orphans.length} found)`));
    for (const url of orphans.slice(0, 8)) {
      blocks.push(slackSection(`\`${new URL(url).pathname}\``));
    }
  }

  blocks.push(slackDivider());
  blocks.push(slackSection('_Keyword Miner -- RentACastle_'));

  return blocks;
}

function buildSerpAPIReport(research) {
  const blocks = [];
  const now = new Date().toLocaleDateString('en-GB');

  blocks.push(slackHeader(`Keyword Research (SerpAPI) -- ${now}`));
  blocks.push(slackFields([
    ['Related Searches', String(research.relatedSearches.length)],
    ['People Also Ask', String(research.peopleAlsoAsk.length)],
    ['Unique Ideas', String(research.unique.length)],
  ]));

  blocks.push(slackDivider());
  blocks.push(slackSection('*Top Keyword Ideas (castle-related):*'));

  const castleKeywords = research.unique.filter(k => k.query.toLowerCase().includes('castle')).slice(0, 15);
  for (const k of castleKeywords) {
    blocks.push(slackSection(`"${k.query}" _(${k.source} from "${k.seed}")_`));
  }

  blocks.push(slackDivider());
  blocks.push(slackSection('_Keyword Miner -- RentACastle_'));

  return blocks;
}

// Main
export async function run() {
  log.info('Starting Keyword Miner...');

  // Try GSC first
  let gscData = null;
  try {
    const auth = getOAuth2Client();
    const endDate = new Date().toISOString().split('T')[0];
    const startDate = new Date(Date.now() - 28 * 86400000).toISOString().split('T')[0];

    log.info(`Querying Search Console: ${startDate} to ${endDate}`);
    gscData = await getSearchConsoleData(auth, startDate, endDate);
    log.info(`Got ${gscData.queries.length} queries, ${gscData.pages.length} pages`);
  } catch (err) {
    log.warn(`GSC unavailable: ${err.message}`);
  }

  if (gscData && gscData.queries.length > 0) {
    const quickWins = findQuickWins(gscData.queries);
    const contentGaps = findContentGaps(gscData.queries);
    const declines = await findDeclines(getOAuth2Client()).catch(() => []);
    const clusters = clusterKeywords(gscData.queries);

    let orphans = [];
    if (SITEMAP_URL) {
      try {
        const sitemapUrls = await fetchSitemapUrls(SITEMAP_URL);
        orphans = findOrphanPages(sitemapUrls, gscData.pages);
      } catch (e) {
        log.warn(`Sitemap fetch failed: ${e.message}`);
      }
    }

    const report = buildGSCReport(gscData.queries, quickWins, contentGaps, declines, orphans, clusters);
    await sendSlack(report, 'Keyword Miner Report');

    return { source: 'gsc', totalQueries: gscData.queries.length, quickWins: quickWins.length, contentGaps: contentGaps.length };
  }

  // Fallback to SerpAPI
  log.info('Falling back to SerpAPI research...');
  const research = await runSerpAPIResearch();

  if (research) {
    const report = buildSerpAPIReport(research);
    await sendSlack(report, 'Keyword Research Report');
    return { source: 'serpapi', keywordIdeas: research.unique.length };
  }

  log.warn('No keyword data available (no GSC, no SerpAPI)');
  await sendSlack([slackSection('Keyword Miner: no data sources available. Configure GSC or SERPAPI_KEY.')], 'Keyword Miner');
  return { source: 'none' };
}
