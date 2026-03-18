const LEVELS = { debug: 0, info: 1, warn: 2, error: 3 };
const MIN_LEVEL = LEVELS[process.env.LOG_LEVEL || 'info'];

function fmt(level, agent, msg) {
  const ts = new Date().toISOString();
  return `[${ts}] [${level.toUpperCase()}] [${agent}] ${msg}`;
}

export function createLogger(agent) {
  return {
    debug: (msg) => LEVELS.debug >= MIN_LEVEL && console.log(fmt('debug', agent, msg)),
    info:  (msg) => LEVELS.info  >= MIN_LEVEL && console.log(fmt('info',  agent, msg)),
    warn:  (msg) => LEVELS.warn  >= MIN_LEVEL && console.warn(fmt('warn',  agent, msg)),
    error: (msg) => LEVELS.error >= MIN_LEVEL && console.error(fmt('error', agent, msg)),
  };
}
