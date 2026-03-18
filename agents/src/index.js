import 'dotenv/config';
import { schedule, listJobs } from './core/scheduler.js';
import { createLogger } from './core/logger.js';
import { sendSlack, slackHeader, slackSection } from './core/slack.js';
import { startApprovalServer } from './core/approval.js';
import { run as runContent } from './agents/content-publisher.js';
import { run as runKeywords } from './agents/keyword-miner.js';
import { run as runInternalLinker } from './agents/internal-linker.js';

const log = createLogger('main');

log.info('RentACastle Agent System starting...');

const { registerTrigger } = startApprovalServer();

registerTrigger('content-publisher', runContent);
registerTrigger('keyword-miner', runKeywords);
registerTrigger('internal-linker', runInternalLinker);

// Schedule agents (UK Time = Europe/London)
schedule('Content Publisher', '0 12 * * *', runContent);      // 12:00 PM daily
schedule('Keyword Miner',     '0 9 * * 1',  runKeywords);     // 9:00 AM Monday
schedule('Internal Linker',   '0 13 * * 4', runInternalLinker); // 1:00 PM Thursday

const jobs = listJobs();
log.info(`${jobs.length} agents scheduled:`);
jobs.forEach(j => log.info(`  ${j.name} -> ${j.schedule}`));

await sendSlack([
  slackHeader('RentACastle Agents Online'),
  slackSection(
    jobs.map(j => `* *${j.name}* -> \`${j.schedule}\``).join('\n') +
    '\n\n_Approval server running. Proposals expire after 12 hours._'
  ),
], 'Agent system started');

log.info('Agent system running. Press Ctrl+C to stop.');
