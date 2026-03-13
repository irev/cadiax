import express from "express";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const projectRoot = path.resolve(__dirname, "..", "..");
const clientRoot = path.resolve(projectRoot, "dist", "client");

const host = process.env.OTONOMASSIST_DASHBOARD_HOST || "127.0.0.1";
const port = Number(process.env.OTONOMASSIST_DASHBOARD_PORT || 8795);
const adminApiUrl = (process.env.OTONOMASSIST_DASHBOARD_ADMIN_API_URL || "http://127.0.0.1:8787").replace(/\/$/, "");
const adminToken = process.env.OTONOMASSIST_DASHBOARD_ADMIN_TOKEN || "";

const app = express();

async function proxyJson(route: string) {
  const headers: Record<string, string> = {
    Accept: "application/json",
  };
  if (adminToken.trim()) {
    headers["X-Cadiax-Token"] = adminToken.trim();
  }
  const response = await fetch(`${adminApiUrl}${route}`, {
    headers,
    cache: "no-store",
  });
  if (!response.ok) {
    const body = await response.text();
    throw new Error(`Admin API ${route} returned ${response.status}: ${body}`);
  }
  return response.json();
}

app.get("/api/dashboard", async (_request, response) => {
  try {
    const status = await proxyJson("/status");
    const metrics = await proxyJson("/metrics");
    const jobs = await proxyJson("/jobs");
    const events = await proxyJson("/events?limit=15");
    const proactive = await proxyJson("/proactive");
    const email = await proxyJson("/email");
    const whatsapp = await proxyJson("/whatsapp");
    const identity = await proxyJson("/identity");
    const privacy = await proxyJson("/privacy");
    response.json({
      status,
      metrics,
      jobs,
      events,
      proactive,
      email,
      whatsapp,
      identity,
      privacy,
      fetchedAt: new Date().toISOString(),
    });
  } catch (error) {
    response.status(502).json({
      error: error instanceof Error ? error.message : "Unknown dashboard proxy error",
      adminApiUrl,
    });
  }
});

app.use(express.static(clientRoot));

app.get(/.*/, (_request, response) => {
  response.sendFile(path.join(clientRoot, "index.html"));
});

app.listen(port, host, () => {
  console.log(`Cadiax dashboard listening on http://${host}:${port}`);
});
