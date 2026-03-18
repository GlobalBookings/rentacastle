import cron from 'node-cron';
import { createLogger } from './logger.js';

const log = createLogger('scheduler');
const jobs = [];

export function schedule(name, cronExpr, fn) {
  const task = cron.schedule(cronExpr, async () => {
    log.info(`Running ${name}...`);
    const start = Date.now();
    try {
      await fn();
      log.info(`${name} completed in ${((Date.now() - start) / 1000).toFixed(1)}s`);
    } catch (err) {
      log.error(`${name} failed: ${err.message}`);
    }
  }, { timezone: 'Europe/London' });

  jobs.push({ name, cronExpr, task });
  log.info(`Scheduled ${name} → ${cronExpr} (UK Time)`);
  return task;
}

export function listJobs() {
  return jobs.map(j => ({ name: j.name, schedule: j.cronExpr }));
}
