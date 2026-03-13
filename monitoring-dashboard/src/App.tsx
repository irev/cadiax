import { useEffect, useState } from "react";

type NavKey =
  | "overview"
  | "runtime"
  | "routing"
  | "channels"
  | "identity"
  | "privacy"
  | "events";

type DashboardPayload = {
  status: Record<string, any>;
  metrics: Record<string, any>;
  jobs: Record<string, any>;
  events: Record<string, any>;
  proactive: Record<string, any>;
  email: Record<string, any>;
  whatsapp: Record<string, any>;
  identity: Record<string, any>;
  privacy: Record<string, any>;
  fetchedAt: string;
};

const navItems: Array<{ key: NavKey; label: string; kicker: string }> = [
  { key: "overview", label: "Overview", kicker: "System pulse" },
  { key: "runtime", label: "Runtime", kicker: "Jobs and scheduler" },
  { key: "routing", label: "Routing", kicker: "Cost and intent flow" },
  { key: "channels", label: "Channels", kicker: "Email and WhatsApp" },
  { key: "identity", label: "Identity", kicker: "Sessions and continuity" },
  { key: "privacy", label: "Privacy", kicker: "Consent and retention" },
  { key: "events", label: "Events", kicker: "Automation trail" },
];

function App() {
  const [active, setActive] = useState<NavKey>("overview");
  const [data, setData] = useState<DashboardPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      try {
        const response = await fetch("/api/dashboard", { cache: "no-store" });
        if (!response.ok) {
          throw new Error(`Dashboard API returned ${response.status}`);
        }
        const payload = (await response.json()) as DashboardPayload;
        if (!cancelled) {
          setData(payload);
          setError("");
          setLoading(false);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Unknown dashboard error");
          setLoading(false);
        }
      }
    };

    void load();
    const timer = window.setInterval(() => void load(), 15000);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, []);

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <p className="eyebrow">Cadiax</p>
          <h1>Monitoring</h1>
          <p className="lede">Optional local operations dashboard with a separate web runtime.</p>
        </div>
        <nav className="nav">
          {navItems.map((item) => (
            <button
              key={item.key}
              type="button"
              className={item.key === active ? "nav-item active" : "nav-item"}
              onClick={() => setActive(item.key)}
            >
              <span className="nav-kicker">{item.kicker}</span>
              <span className="nav-label">{item.label}</span>
            </button>
          ))}
        </nav>
        <div className="sidebar-footer">
          <div className="status-pill">
            <span className="dot" />
            {data?.status?.overall?.status ?? "loading"}
          </div>
          <p>{data?.fetchedAt ? `Last sync ${new Date(data.fetchedAt).toLocaleTimeString()}` : "Waiting for first sync"}</p>
        </div>
      </aside>

      <main className="content">
        <header className="header">
          <div>
            <p className="eyebrow">Runtime telemetry</p>
            <h2>Autonomous operations dashboard</h2>
          </div>
          <div className="hero-metrics">
            <MetricCard label="Health" value={data?.status?.overall?.status ?? "-"} accent="emerald" />
            <MetricCard label="Routes" value={String(data?.status?.routing?.routes_total ?? 0)} accent="amber" />
            <MetricCard label="Alerts" value={String(data?.status?.issues?.length ?? 0)} accent="scarlet" />
          </div>
        </header>

        {loading ? <section className="panel">Loading dashboard data...</section> : null}
        {error ? <section className="panel error">{error}</section> : null}
        {!loading && !error && data ? <SectionRenderer active={active} data={data} /> : null}
      </main>
    </div>
  );
}

function SectionRenderer({ active, data }: { active: NavKey; data: DashboardPayload }) {
  if (active === "overview") {
    return (
      <section className="grid two-up">
        <Panel title="System Overview">
          <KeyValue label="Overall" value={data.status.overall.status} />
          <KeyValue label="Runtime" value={data.status.runtime.status} />
          <KeyValue label="Scheduler" value={data.status.scheduler.status} />
          <KeyValue label="Dashboard access" value={data.status.dashboard?.access_mode ?? "local"} />
        </Panel>
        <Panel title="Operator Focus">
          <KeyValue label="Queued jobs" value={String(data.status.runtime.queued_jobs)} />
          <KeyValue label="Policy denied" value={String(data.status.policy.policy_denied_count)} />
          <KeyValue label="Heuristic route rate" value={data.status.routing.heuristic_rate} />
          <KeyValue label="AI route rate" value={data.status.routing.ai_route_rate} />
        </Panel>
      </section>
    );
  }

  if (active === "runtime") {
    return (
      <section className="grid two-up">
        <Panel title="Job Runtime">
          <KeyValue label="Queued" value={String(data.status.runtime.queued_jobs)} />
          <KeyValue label="Leased" value={String(data.status.runtime.leased_jobs)} />
          <KeyValue label="Done" value={String(data.status.runtime.done_jobs)} />
          <KeyValue label="Failed" value={String(data.status.runtime.failed_jobs)} />
        </Panel>
        <Panel title="Scheduler Pulse">
          <KeyValue label="Last status" value={data.status.scheduler.last_status || "-"} />
          <KeyValue label="Last run at" value={data.status.scheduler.last_run_at || "-"} />
          <KeyValue label="Heartbeat mode" value={data.status.scheduler.last_heartbeat_mode || "-"} />
          <KeyValue label="Processed" value={String(data.status.scheduler.last_processed)} />
        </Panel>
      </section>
    );
  }

  if (active === "routing") {
    return (
      <section className="grid two-up">
        <Panel title="Route Distribution">
          <KeyValue label="Builtin" value={String(data.status.routing.builtin_routes_total)} />
          <KeyValue label="Direct skill" value={String(data.status.routing.direct_skill_routes_total)} />
          <KeyValue label="Heuristic" value={String(data.status.routing.heuristic_routes_total)} />
          <KeyValue label="AI" value={String(data.status.routing.ai_routes_total)} />
        </Panel>
        <Panel title="Provider Load">
          <KeyValue label="AI requests" value={String(data.metrics.summary.ai_requests_total)} />
          <KeyValue label="AI tokens" value={String(data.metrics.summary.ai_total_tokens)} />
          <KeyValue label="Latency samples" value={String(data.metrics.summary.provider_latency_samples)} />
          <KeyValue label="Errors" value={String(data.metrics.summary.errors_total)} />
        </Panel>
      </section>
    );
  }

  if (active === "channels") {
    return (
      <section className="grid two-up">
        <Panel title="Email">
          <KeyValue label="Messages" value={String(data.email.email.message_count)} />
          <KeyValue label="Inbound" value={String(data.email.email.inbound_count)} />
          <KeyValue label="Outbound" value={String(data.email.email.outbound_count)} />
          <KeyValue label="Latest subject" value={String(data.email.email.latest_message?.subject || "-")} />
        </Panel>
        <Panel title="WhatsApp">
          <KeyValue label="Messages" value={String(data.whatsapp.whatsapp.message_count)} />
          <KeyValue label="Inbound" value={String(data.whatsapp.whatsapp.inbound_count)} />
          <KeyValue label="Outbound" value={String(data.whatsapp.whatsapp.outbound_count)} />
          <KeyValue label="Latest phone" value={String(data.whatsapp.whatsapp.latest_message?.phone_number || "-")} />
        </Panel>
      </section>
    );
  }

  if (active === "identity") {
    return (
      <section className="grid two-up">
        <Panel title="Identity Continuity">
          <KeyValue label="Identity count" value={String(data.identity.identity.identity_count)} />
          <KeyValue label="Session count" value={String(data.identity.identity.session_count)} />
          <KeyValue label="Filtered scope" value={String(data.status.scope_filter?.agent_scope || "default")} />
          <KeyValue label="Visible sessions" value={String(data.status.scope_filter?.visible_sessions || 0)} />
        </Panel>
        <Panel title="Proactive Layer">
          <KeyValue label="Insight count" value={String(data.proactive.proactive.insight_count ?? data.status.personality.proactive_insight_count ?? 0)} />
          <KeyValue label="Notifications" value={String(data.status.notifications.notification_count)} />
          <KeyValue label="Identity total" value={String(data.status.storage.identity_count)} />
          <KeyValue label="Session total" value={String(data.status.storage.session_count)} />
        </Panel>
      </section>
    );
  }

  if (active === "privacy") {
    return (
      <section className="grid two-up">
        <Panel title="Privacy Controls">
          <KeyValue label="Quiet hours" value={data.privacy.privacy_controls.quiet_hours_enabled ? "enabled" : "disabled"} />
          <KeyValue label="Consent required" value={data.privacy.privacy_controls.consent_required_for_proactive ? "yes" : "no"} />
          <KeyValue label="Proactive enabled" value={data.privacy.privacy_controls.proactive_assistance_enabled ? "yes" : "no"} />
          <KeyValue label="Retention days" value={String(data.privacy.privacy_controls.memory_retention_days)} />
        </Panel>
        <Panel title="Retention Scope">
          <KeyValue label="Memory entries" value={String(data.privacy.privacy_controls.memory_entry_count)} />
          <KeyValue label="Notifications" value={String(data.privacy.privacy_controls.notification_count)} />
          <KeyValue label="Email" value={String(data.privacy.privacy_controls.email_count)} />
          <KeyValue label="WhatsApp" value={String(data.privacy.privacy_controls.whatsapp_count)} />
        </Panel>
      </section>
    );
  }

  return (
    <section className="grid single">
      <Panel title="Event Stream">
        <div className="event-list">
          {(data.events.events ?? []).slice(0, 12).map((event: any, index: number) => (
            <article key={event.id ?? index} className="event-item">
              <p className="event-topic">{event.topic || "event"}</p>
              <p className="event-text">{event.event_type || event.type || "-"}</p>
            </article>
          ))}
        </div>
      </Panel>
    </section>
  );
}

function MetricCard({ label, value, accent }: { label: string; value: string; accent: string }) {
  return (
    <div className={`metric-card ${accent}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="panel">
      <header className="panel-header">
        <h3>{title}</h3>
      </header>
      <div className="panel-body">{children}</div>
    </section>
  );
}

function KeyValue({ label, value }: { label: string; value: string }) {
  return (
    <div className="kv">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

export default App;
