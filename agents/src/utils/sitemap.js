import { createLogger } from '../core/logger.js';

const log = createLogger('sitemap');

export async function fetchSitemapUrls(sitemapIndexUrl) {
  log.info(`Fetching sitemap index: ${sitemapIndexUrl}`);
  const res = await fetch(sitemapIndexUrl);
  const xml = await res.text();

  const sitemapUrls = [...xml.matchAll(/<loc>([^<]+)<\/loc>/g)].map(m => m[1]);
  log.info(`Found ${sitemapUrls.length} child sitemap(s)`);

  const allUrls = [];
  for (const url of sitemapUrls) {
    const childRes = await fetch(url);
    const childXml = await childRes.text();
    const pageUrls = [...childXml.matchAll(/<loc>([^<]+)<\/loc>/g)].map(m => m[1]);
    allUrls.push(...pageUrls);
  }

  log.info(`Total pages in sitemap: ${allUrls.length}`);
  return allUrls;
}

export function categorizeUrl(url) {
  const path = new URL(url).pathname;
  if (path.startsWith('/blog/')) return 'blog';
  if (path.startsWith('/castles/') && path !== '/castles/') return 'castle';
  if (path.startsWith('/regions/')) return 'region';
  if (path.startsWith('/castle-types/')) return 'castle-type';
  if (path.startsWith('/guides/')) return 'guide';
  return 'page';
}
