import { createLogger } from '../core/logger.js';
import { sendSlack, slackHeader, slackSection, slackDivider } from '../core/slack.js';
import fs from 'fs';
import path from 'path';
import { execSync } from 'child_process';
import { fileURLToPath } from 'url';

const log = createLogger('internal-linker');
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const WORK_DIR = path.join(__dirname, '..', '..', 'data', 'repo-checkout');
const GH_TOKEN = process.env.GITHUB_TOKEN;
const GH_REPO = process.env.GITHUB_REPO || 'GlobalBookings/rentacastle';

const MAX_LINKS_PER_POST = 3;
const MAX_LINKS_PER_RUN = 15;
const MIN_INBOUND_THRESHOLD = 2;

const RELATED_CATEGORIES = {
  'Castle Types': ['Guides', 'Planning', 'Regions'],
  'Regions': ['Castle Types', 'Guides', 'Seasonal'],
  'Planning': ['Castle Types', 'Guides', 'Luxury'],
  'Weddings': ['Planning', 'Luxury', 'Regions'],
  'Seasonal': ['Planning', 'Regions', 'Activities'],
  'Activities': ['Planning', 'Castle Types', 'Seasonal'],
  'Guides': ['Planning', 'Castle Types', 'Regions'],
  'Luxury': ['Weddings', 'Castle Types', 'Regions'],
};

function getRepoPaths() {
  return {
    root: WORK_DIR,
    blogData: path.join(WORK_DIR, 'src', 'data', 'blogPosts.ts'),
    blogPage: path.join(WORK_DIR, 'src', 'pages', 'blog', '[slug].astro'),
  };
}

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

function parseBlogPosts() {
  const { blogData } = getRepoPaths();
  const content = fs.readFileSync(blogData, 'utf8');
  const posts = [];
  const entryRegex = /\{\s*slug:\s*'([^']+)',\s*title:\s*'([^']*(?:\\.[^']*)*)',\s*description:\s*'([^']*(?:\\.[^']*)*)',\s*date:\s*'([^']+)',\s*category:\s*'([^']+)'/g;
  let match;

  while ((match = entryRegex.exec(content)) !== null) {
    posts.push({
      slug: match[1],
      title: match[2].replace(/\\'/g, "'"),
      description: match[3].replace(/\\'/g, "'"),
      date: match[4],
      category: match[5],
    });
  }

  log.info(`Parsed ${posts.length} blog posts from blogPosts.ts`);
  return posts;
}

function parseSlugContent() {
  const { blogPage } = getRepoPaths();
  const raw = fs.readFileSync(blogPage, 'utf8');
  const contentMap = {};
  const slugBlockRegex = /'([^']+)':\s*`([\s\S]*?)`(?:\s*,|\s*\})/g;
  let match;

  while ((match = slugBlockRegex.exec(raw)) !== null) {
    contentMap[match[1]] = match[2];
  }

  log.info(`Parsed ${Object.keys(contentMap).length} content blocks from [slug].astro`);
  return { raw, contentMap };
}

function extractInternalLinks(html) {
  const links = [];
  const linkRegex = /href="(\/blog\/[^"]+|\/castles[^"]*|\/regions[^"]*|\/castle-types[^"]*|\/guides[^"]*)"/g;
  let match;
  while ((match = linkRegex.exec(html)) !== null) {
    links.push(match[1]);
  }
  return links;
}

function buildLinkMap(contentMap) {
  const outbound = {};
  const inbound = {};

  for (const slug of Object.keys(contentMap)) {
    outbound[slug] = extractInternalLinks(contentMap[slug]);
    if (!inbound[slug]) inbound[slug] = [];
  }

  for (const [sourceSlug, links] of Object.entries(outbound)) {
    for (const link of links) {
      const blogMatch = link.match(/^\/blog\/([^/?#]+)/);
      if (blogMatch) {
        const targetSlug = blogMatch[1];
        if (!inbound[targetSlug]) inbound[targetSlug] = [];
        inbound[targetSlug].push(sourceSlug);
      }
    }
  }

  return { outbound, inbound };
}

function getSignificantWords(text) {
  const stopWords = new Set(['about', 'their', 'there', 'these', 'those', 'which', 'where',
    'would', 'could', 'should', 'being', 'after', 'before', 'under', 'above',
    'between', 'through', 'during', 'other', 'every', 'while', 'castle', 'castles']);
  return text
    .toLowerCase()
    .replace(/[^a-z0-9\s]/g, ' ')
    .split(/\s+/)
    .filter(w => w.length > 4 && !stopWords.has(w));
}

function calculateRelevance(postA, postB) {
  let score = 0;

  const slugWordsA = getSignificantWords(postA.slug.replace(/-/g, ' '));
  const slugWordsB = getSignificantWords(postB.slug.replace(/-/g, ' '));
  score += slugWordsA.filter(w => slugWordsB.includes(w)).length * 3;

  const titleWordsA = getSignificantWords(postA.title);
  const titleWordsB = getSignificantWords(postB.title);
  score += titleWordsA.filter(w => titleWordsB.includes(w)).length * 2;

  if (postA.category === postB.category) score += 2;

  const related = RELATED_CATEGORIES[postA.category] || [];
  if (related.includes(postB.category)) score += 1;

  return score;
}

function insertLinkIntoHTML(html, targetSlug, anchorText) {
  const targetWords = getSignificantWords(targetSlug.replace(/-/g, ' '));
  const paragraphs = html.match(/<p>[\s\S]*?<\/p>/g) || [];

  let bestParagraph = null;
  let bestScore = 0;
  let bestPhrase = null;

  for (const para of paragraphs) {
    if (para.includes(`/blog/${targetSlug}`)) continue;
    const plainText = para.replace(/<[^>]*>/g, '');
    if (plainText.length < 80) continue;

    const paraWords = getSignificantWords(plainText);
    const overlapScore = targetWords.filter(w => paraWords.includes(w)).length;

    if (overlapScore > bestScore) {
      bestScore = overlapScore;
      bestParagraph = para;
      bestPhrase = findLinkablePhrase(plainText, targetWords, anchorText);
    }
  }

  if (!bestParagraph && paragraphs.length >= 3) {
    const middleStart = Math.floor(paragraphs.length / 3);
    const middleEnd = Math.floor((paragraphs.length * 2) / 3);
    for (let i = middleStart; i <= middleEnd; i++) {
      if (!paragraphs[i]) continue;
      const plainText = paragraphs[i].replace(/<[^>]*>/g, '');
      if (plainText.length >= 100) {
        bestParagraph = paragraphs[i];
        break;
      }
    }
  }

  if (!bestParagraph) return null;

  const linkTag = `<a href="/blog/${targetSlug}">${anchorText}</a>`;
  let modifiedPara;

  if (bestPhrase && bestParagraph.includes(bestPhrase)) {
    modifiedPara = bestParagraph.replace(bestPhrase, linkTag);
  } else {
    const sentence = ` For more, see our guide on ${linkTag}.`;
    modifiedPara = bestParagraph.replace('</p>', `${sentence}</p>`);
  }

  const newHTML = html.replace(bestParagraph, modifiedPara);
  return newHTML === html ? null : newHTML;
}

function findLinkablePhrase(text, targetWords, anchorText) {
  if (text.includes(anchorText)) return anchorText;

  const anchorWords = getSignificantWords(anchorText);
  if (anchorWords.length >= 2) {
    const shortAnchor = anchorWords.slice(0, 3).join(' ');
    const idx = text.toLowerCase().indexOf(shortAnchor);
    if (idx >= 0) return text.substring(idx, idx + shortAnchor.length);
  }

  for (const word of targetWords) {
    const regex = new RegExp(`\\b(${word}\\w*)\\b`, 'i');
    const match = text.match(regex);
    if (match) return match[0];
  }

  return null;
}

function generateAnchorText(post) {
  let anchor = post.title;
  anchor = anchor.replace(/\s*:?\s*\d{4}('s)?\s*/g, ' ');
  anchor = anchor.replace(/\b(Your|Ultimate|Complete|Epic|Guide|Adventure)\b\s*/gi, '');
  anchor = anchor.trim().replace(/\s+/g, ' ').replace(/^[\s:]+|[\s:]+$/g, '');
  if (anchor.length > 55) anchor = anchor.substring(0, 50).replace(/\s\S*$/, '').trim();
  if (anchor.length < 5) anchor = post.title.substring(0, 50);
  return anchor;
}

export async function run() {
  log.info('Internal Link Optimiser starting...');

  ensureRepoCheckout();

  const posts = parseBlogPosts();
  if (posts.length === 0) {
    log.warn('No blog posts found');
    return { linksAdded: 0, postsModified: 0 };
  }

  const { raw: astroFileContent, contentMap } = parseSlugContent();
  const { outbound, inbound } = buildLinkMap(contentMap);

  const underLinked = posts.filter(p => {
    const inboundCount = (inbound[p.slug] || []).length;
    return inboundCount < MIN_INBOUND_THRESHOLD && contentMap[p.slug];
  });

  log.info(`Found ${underLinked.length} under-linked posts (< ${MIN_INBOUND_THRESHOLD} inbound links)`);

  if (underLinked.length === 0) {
    await sendSlack([slackSection('Internal Linker: all blog posts have sufficient cross-links.')], 'Internal Linker');
    return { linksAdded: 0, postsModified: 0 };
  }

  const linkPlan = [];
  let totalLinksPlanned = 0;
  const existingLinks = new Set();
  for (const [slug, links] of Object.entries(outbound)) {
    for (const link of links) existingLinks.add(`${slug}->${link}`);
  }

  for (const targetPost of underLinked) {
    if (totalLinksPlanned >= MAX_LINKS_PER_RUN) break;

    const candidates = posts
      .filter(p => p.slug !== targetPost.slug && contentMap[p.slug])
      .map(p => ({ post: p, relevance: calculateRelevance(targetPost, p) }))
      .filter(c => c.relevance > 0)
      .sort((a, b) => b.relevance - a.relevance)
      .slice(0, 3);

    for (const candidate of candidates) {
      if (totalLinksPlanned >= MAX_LINKS_PER_RUN) break;
      const sourceSlug = candidate.post.slug;
      const linkKey = `${sourceSlug}->/blog/${targetPost.slug}`;
      if (existingLinks.has(linkKey)) continue;

      const linksFromSource = linkPlan.filter(l => l.sourceSlug === sourceSlug).length;
      if (linksFromSource >= MAX_LINKS_PER_POST) continue;

      linkPlan.push({
        sourceSlug,
        targetSlug: targetPost.slug,
        anchorText: generateAnchorText(targetPost),
        relevanceScore: candidate.relevance,
      });
      existingLinks.add(linkKey);
      totalLinksPlanned++;
    }
  }

  log.info(`Planned ${linkPlan.length} new internal links`);

  if (linkPlan.length === 0) {
    await sendSlack([slackSection('Internal Linker: no suitable cross-link opportunities found.')], 'Internal Linker');
    return { linksAdded: 0, postsModified: 0 };
  }

  const modifiedSlugs = new Set();
  const appliedLinks = [];
  const modifiedContentMap = { ...contentMap };

  for (const link of linkPlan) {
    const currentHTML = modifiedContentMap[link.sourceSlug];
    if (!currentHTML) continue;
    if (currentHTML.includes(`/blog/${link.targetSlug}`)) continue;

    const newHTML = insertLinkIntoHTML(currentHTML, link.targetSlug, link.anchorText);
    if (newHTML) {
      modifiedContentMap[link.sourceSlug] = newHTML;
      modifiedSlugs.add(link.sourceSlug);
      appliedLinks.push(link);
      log.info(`Added link: ${link.sourceSlug} -> ${link.targetSlug}`);
    }
  }

  if (appliedLinks.length === 0) {
    await sendSlack([slackSection('Internal Linker: found under-linked posts but could not find natural insertion points.')], 'Internal Linker');
    return { linksAdded: 0, postsModified: 0 };
  }

  const { blogPage } = getRepoPaths();
  let updatedAstroContent = astroFileContent;
  for (const slug of modifiedSlugs) {
    updatedAstroContent = updatedAstroContent.replace(contentMap[slug], modifiedContentMap[slug]);
  }
  fs.writeFileSync(blogPage, updatedAstroContent);

  const { root } = getRepoPaths();
  let pushed = false;
  try {
    execSync('git add "src/pages/blog/[slug].astro"', { cwd: root, stdio: 'pipe' });
    execSync(`git commit -m "Auto-add ${appliedLinks.length} internal links"`, { cwd: root, stdio: 'pipe' });
    execSync('git push origin master', { cwd: root, stdio: 'pipe' });
    pushed = true;
  } catch (err) {
    log.error(`Git push failed: ${err.message}`);
  }

  const blocks = [
    slackHeader(`Internal Linker -- ${appliedLinks.length} Links Added`),
    slackDivider(),
  ];
  for (const link of appliedLinks) {
    blocks.push(slackSection(`*${link.sourceSlug}* -> /blog/${link.targetSlug}\n_Anchor: "${link.anchorText}"_ (relevance: ${link.relevanceScore})`));
  }
  blocks.push(slackDivider());
  blocks.push(slackSection(
    `*Summary:* ${appliedLinks.length} links across ${modifiedSlugs.size} posts\n` +
    (pushed ? 'Pushed to GitHub.' : 'Git push failed -- manual push needed.')
  ));
  await sendSlack(blocks, `Internal Linker: ${appliedLinks.length} links added`);

  return { linksAdded: appliedLinks.length, postsModified: modifiedSlugs.size };
}
