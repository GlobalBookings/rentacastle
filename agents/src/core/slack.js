const WEBHOOK_URL = process.env.SLACK_WEBHOOK_URL;

export async function sendSlack(blocks, fallbackText = 'RentACastle Agent Alert') {
  if (!WEBHOOK_URL) {
    console.log(`[SLACK-DRY-RUN] ${fallbackText}`);
    if (Array.isArray(blocks)) {
      blocks.forEach(b => {
        if (b.type === 'section' && b.text) console.log(`  ${b.text.text}`);
      });
    }
    return;
  }

  const payload = {
    text: fallbackText,
    blocks: Array.isArray(blocks) ? blocks : undefined,
  };

  const res = await fetch(WEBHOOK_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    console.error(`Slack webhook failed: ${res.status} ${await res.text()}`);
  }
}

export function slackHeader(text) {
  return { type: 'header', text: { type: 'plain_text', text, emoji: true } };
}

export function slackSection(markdown) {
  return { type: 'section', text: { type: 'mrkdwn', text: markdown } };
}

export function slackDivider() {
  return { type: 'divider' };
}

export function slackFields(pairs) {
  return {
    type: 'section',
    fields: pairs.map(([label, value]) => ({
      type: 'mrkdwn',
      text: `*${label}*\n${value}`,
    })),
  };
}
