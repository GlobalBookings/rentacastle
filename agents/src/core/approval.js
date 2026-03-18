import express from 'express';
import { createLogger } from './logger.js';
import { sendSlack, slackSection, slackDivider } from './slack.js';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const log = createLogger('approval');
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PENDING_DIR = path.join(__dirname, '..', '..', 'data', 'pending');
const PORT = parseInt(process.env.APPROVAL_PORT || '3100');
const TIMEOUT_MS = 12 * 60 * 60 * 1000;

if (!fs.existsSync(PENDING_DIR)) fs.mkdirSync(PENDING_DIR, { recursive: true });

const pendingCallbacks = new Map();

export async function requestApproval(proposalId, summary, actions, onApprove) {
  const proposal = {
    id: proposalId,
    created: new Date().toISOString(),
    summary,
    actions,
    status: 'pending',
  };

  fs.writeFileSync(
    path.join(PENDING_DIR, `${proposalId}.json`),
    JSON.stringify(proposal, null, 2)
  );

  pendingCallbacks.set(proposalId, {
    onApprove,
    timer: setTimeout(() => expireProposal(proposalId), TIMEOUT_MS),
  });

  const blocks = [
    ...summary,
    slackDivider(),
    {
      type: 'actions',
      block_id: `approval_${proposalId}`,
      elements: [
        {
          type: 'button',
          text: { type: 'plain_text', text: 'Approve', emoji: true },
          style: 'primary',
          action_id: 'approve',
          value: proposalId,
        },
        {
          type: 'button',
          text: { type: 'plain_text', text: 'Reject', emoji: true },
          style: 'danger',
          action_id: 'reject',
          value: proposalId,
        },
      ],
    },
  ];

  await sendSlack(blocks, `Agent awaiting approval: ${proposalId}`);
  log.info(`Approval requested: ${proposalId} (${actions.length} actions)`);
}

function expireProposal(proposalId) {
  const entry = pendingCallbacks.get(proposalId);
  if (entry) {
    pendingCallbacks.delete(proposalId);
    updateProposalFile(proposalId, 'expired');
    log.info(`Proposal ${proposalId} expired`);
  }
}

function updateProposalFile(proposalId, status) {
  const filePath = path.join(PENDING_DIR, `${proposalId}.json`);
  if (fs.existsSync(filePath)) {
    const data = JSON.parse(fs.readFileSync(filePath, 'utf8'));
    data.status = status;
    data.resolved = new Date().toISOString();
    fs.writeFileSync(filePath, JSON.stringify(data, null, 2));
  }
}

let serverStarted = false;

export function startApprovalServer() {
  if (serverStarted) return;
  serverStarted = true;

  const app = express();
  app.use(express.urlencoded({ extended: true }));
  app.use(express.json());

  app.get('/health', (req, res) => {
    res.json({ status: 'ok', pending: pendingCallbacks.size });
  });

  app.post('/slack/actions', async (req, res) => {
    try {
      const payload = JSON.parse(req.body.payload);
      const action = payload.actions?.[0];
      if (!action) { res.sendStatus(200); return; }

      const proposalId = action.value;
      const actionId = action.action_id;
      const user = payload.user?.name || 'unknown';

      const entry = pendingCallbacks.get(proposalId);
      if (!entry) {
        res.json({ response_type: 'ephemeral', text: `Proposal already processed.` });
        return;
      }

      clearTimeout(entry.timer);
      pendingCallbacks.delete(proposalId);

      if (actionId === 'approve') {
        updateProposalFile(proposalId, 'approved');
        res.json({ response_type: 'in_channel', text: `Approved by ${user}. Executing...` });
        try {
          await entry.onApprove();
          updateProposalFile(proposalId, 'executed');
        } catch (err) {
          updateProposalFile(proposalId, 'failed');
        }
      } else {
        updateProposalFile(proposalId, 'rejected');
        res.json({ response_type: 'in_channel', text: `Rejected by ${user}.` });
      }
    } catch (err) {
      res.sendStatus(200);
    }
  });

  const triggerHandlers = {};
  app.post('/trigger/:agent', async (req, res) => {
    const agent = req.params.agent;
    const handler = triggerHandlers[agent];
    if (!handler) { res.status(404).json({ error: `Unknown agent: ${agent}` }); return; }
    res.json({ status: 'triggered', agent });
    try { await handler(); } catch (err) { log.error(`Triggered ${agent} failed: ${err.message}`); }
  });

  app.listen(PORT, () => {
    log.info(`Approval server listening on port ${PORT}`);
  });

  return {
    registerTrigger: (name, fn) => { triggerHandlers[name] = fn; },
  };
}
