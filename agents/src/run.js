import 'dotenv/config';
import { createLogger } from './core/logger.js';

const log = createLogger('runner');
const agent = process.argv[2];

if (!agent) {
  console.log('Usage: node src/run.js <agent-name>');
  console.log('  content-publisher  — Generate blog posts from content gaps');
  console.log('  keyword-miner      — Find keyword opportunities');
  console.log('  internal-linker    — Add cross-links between blog posts');
  console.log('  test               — Verify configuration');
  process.exit(1);
}

if (agent === 'test') {
  log.info('Testing agent configuration...');

  const checks = [
    ['ANTHROPIC_API_KEY', process.env.ANTHROPIC_API_KEY],
    ['GITHUB_TOKEN', process.env.GITHUB_TOKEN],
    ['GITHUB_REPO', process.env.GITHUB_REPO],
    ['SERPAPI_KEY', process.env.SERPAPI_KEY],
    ['GOOGLE_CLIENT_ID', process.env.GOOGLE_CLIENT_ID],
    ['GOOGLE_CLIENT_SECRET', process.env.GOOGLE_CLIENT_SECRET],
    ['GOOGLE_REFRESH_TOKEN', process.env.GOOGLE_REFRESH_TOKEN],
    ['SEARCH_CONSOLE_SITE_URL', process.env.SEARCH_CONSOLE_SITE_URL],
    ['SLACK_WEBHOOK_URL', process.env.SLACK_WEBHOOK_URL],
    ['SITE_URL', process.env.SITE_URL],
    ['SITEMAP_URL', process.env.SITEMAP_URL],
  ];

  let allGood = true;
  for (const [name, value] of checks) {
    const icon = value ? 'OK' : 'MISSING';
    if (!value) allGood = false;
    console.log(`  ${value ? '+' : '-'} ${name}: ${icon}`);
  }

  if (allGood) {
    log.info('All credentials configured.');
    const { sendSlack, slackSection } = await import('./core/slack.js');
    await sendSlack([slackSection('RentACastle Agent test -- all systems go!')], 'Agent test');
  } else {
    log.warn('Some credentials are missing. See .env.example for required values.');
  }

  process.exit(0);
}

const agents = {
  'content-publisher': () => import('./agents/content-publisher.js'),
  'keyword-miner': () => import('./agents/keyword-miner.js'),
  'internal-linker': () => import('./agents/internal-linker.js'),
};

const loader = agents[agent];
if (!loader) {
  log.error(`Unknown agent: ${agent}`);
  log.info(`Available: ${Object.keys(agents).join(', ')}`);
  process.exit(1);
}

try {
  log.info(`Running ${agent}...`);
  const start = Date.now();
  const mod = await loader();
  const result = await mod.run();
  const elapsed = ((Date.now() - start) / 1000).toFixed(1);
  log.info(`${agent} completed in ${elapsed}s`);
  if (result) log.info(`Result: ${JSON.stringify(result)}`);
} catch (err) {
  log.error(`${agent} failed: ${err.message}`);
  console.error(err.stack);
  process.exit(1);
}
