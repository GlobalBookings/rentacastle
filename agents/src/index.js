import 'dotenv/config';
import http from 'http';
import { schedule, listJobs } from './core/scheduler.js';
import { createLogger } from './core/logger.js';
import { sendSlack, slackHeader, slackSection } from './core/slack.js';

const log = createLogger('main');
const PORT = parseInt(process.env.PORT || '8080');

log.info('RentACastle Agent System starting...');

// Health check server (keeps container alive for DO App Platform)
const server = http.createServer((req, res) => {
  if (req.url === '/health' || req.url === '/') {
    const jobs = listJobs();
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ status: 'ok', agents: jobs.length, uptime: process.uptime() }));
  } else {
    res.writeHead(404);
    res.end();
  }
});

server.listen(PORT, () => {
  log.info(`Health check server listening on port ${PORT}`);
});

// Lazy-load agents to avoid crashing on missing deps
async function loadAgent(name) {
  try {
    const mod = await import(`./agents/${name}.js`);
    return mod.run;
  } catch (err) {
    log.error(`Failed to load agent ${name}: ${err.message}`);
    return async () => { log.error(`Agent ${name} not available`); };
  }
}

const runContent = await loadAgent('content-publisher');
const runKeywords = await loadAgent('keyword-miner');
const runInternalLinker = await loadAgent('internal-linker');

// Schedule agents (UK Time = Europe/London)
schedule('Content Publisher', '0 12 * * *', runContent);       // 12:00 PM daily
schedule('Keyword Miner',     '0 9 * * 1',  runKeywords);      // 9:00 AM Monday
schedule('Internal Linker',   '0 13 * * 4', runInternalLinker); // 1:00 PM Thursday

const jobs = listJobs();
log.info(`${jobs.length} agents scheduled:`);
jobs.forEach(j => log.info(`  ${j.name} -> ${j.schedule}`));

await sendSlack([
  slackHeader('RentACastle Agents Online'),
  slackSection(
    jobs.map(j => `* *${j.name}* -> \`${j.schedule}\``).join('\n')
  ),
], 'Agent system started').catch(() => {});

log.info('Agent system running. Press Ctrl+C to stop.');

// Keep process alive
process.on('uncaughtException', (err) => {
  log.error(`Uncaught exception: ${err.message}`);
});
process.on('unhandledRejection', (err) => {
  log.error(`Unhandled rejection: ${err}`);
});
