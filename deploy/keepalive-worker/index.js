// Cloudflare Worker (free plan) that pings the Hugging Face Space on a cron
// schedule so the free CPU Space never hits its ~48h inactivity sleep.
export default {
  async scheduled(_event, env, ctx) {
    ctx.waitUntil(ping(env));
  },
  // Visiting the worker URL triggers a manual ping (handy for testing).
  async fetch(_request, env) {
    return Response.json(await ping(env));
  },
};

async function ping(env) {
  const url = `${env.SPACE_URL.replace(/\/$/, "")}/api/health`;
  try {
    const r = await fetch(url, { headers: { "user-agent": "leakfusion-keepalive" } });
    return { url, status: r.status };
  } catch (e) {
    return { url, error: String(e) };
  }
}
