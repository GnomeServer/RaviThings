<script lang="ts">
  import { RISKY_PORTS } from "../../ui/src/risk";
  import AtlasIcon from "./AtlasIcon.svelte";

  type Factor = { text: string; level: string };
  type Risk = { score: number; severity: string; factors: Factor[] } | null;
  type Rec = Record<string, unknown>;
  type Service = { port: number; name: string; danger: string; reason: string };

  let {
    payload,
    risk,
    onCve,
    onPort,
  }: {
    payload: Rec | null;
    risk: Risk;
    onCve: (id: string) => void;
    onPort: (port: number) => void;
  } = $props();

  let copiedIp = $state("");
  let copyNote = $state("");

  const DANGER_ORDER: Record<string, number> = { critical: 0, high: 1, medium: 2 };
  const PORTS: Record<number, { name: string; danger: "critical" | "high" | "medium"; reason: string }> = {
    3389: { name: "RDP", danger: "critical", reason: "Remote Desktop — BlueKeep, brute force, lateral movement" },
    445: { name: "SMB", danger: "critical", reason: "Server Message Block — EternalBlue, WannaCry, ransomware vector" },
    1433: { name: "MSSQL", danger: "critical", reason: "Microsoft SQL Server — default credentials, SQL injection pivot" },
    3306: { name: "MySQL", danger: "critical", reason: "MySQL — often has weak/no auth when exposed" },
    5432: { name: "PostgreSQL", danger: "critical", reason: "PostgreSQL — database exfiltration risk" },
    27017: { name: "MongoDB", danger: "critical", reason: "MongoDB — frequently left without authentication" },
    6379: { name: "Redis", danger: "critical", reason: "Redis — no auth by default, RCE via SLAVEOF" },
    9200: { name: "Elasticsearch", danger: "critical", reason: "Elasticsearch — unauthenticated data access by default" },
    5900: { name: "VNC", danger: "critical", reason: "VNC — remote framebuffer, weak auth common" },
    2375: { name: "Docker API", danger: "critical", reason: "Docker daemon — unauthenticated container escape" },
    21: { name: "FTP", danger: "high", reason: "FTP — cleartext credentials, anonymous access" },
    23: { name: "Telnet", danger: "high", reason: "Telnet — cleartext everything, default credentials on IoT" },
    25: { name: "SMTP", danger: "high", reason: "SMTP — open relay testing, email spoofing" },
    110: { name: "POP3", danger: "high", reason: "POP3 — cleartext email retrieval" },
    143: { name: "IMAP", danger: "high", reason: "IMAP — cleartext email access" },
    161: { name: "SNMP", danger: "high", reason: "SNMP — community strings leak configs and credentials" },
    389: { name: "LDAP", danger: "high", reason: "LDAP — directory enumeration, credential harvesting" },
    11211: { name: "Memcached", danger: "high", reason: "Memcached — DDoS amplification, data exfiltration" },
    8080: { name: "HTTP-Proxy", danger: "medium", reason: "HTTP proxy — often dev servers, admin panels" },
    8443: { name: "HTTPS-Alt", danger: "medium", reason: "HTTPS alt — management interfaces" },
  };

  function rec(value: unknown): Rec | null {
    return value && typeof value === "object" && !Array.isArray(value) ? (value as Rec) : null;
  }
  function arr(value: unknown): unknown[] {
    return Array.isArray(value) ? value : [];
  }
  function strings(value: unknown): string[] {
    return arr(value).map((item) => (typeof item === "string" ? item : "")).filter(Boolean);
  }
  function text(value: unknown): string {
    if (value === undefined || value === null || value === "") return "not collected";
    return String(value);
  }
  function finite(value: unknown): number | null {
    return typeof value === "number" && Number.isFinite(value) ? value : null;
  }
  function money(value: unknown): string {
    if (value === undefined || value === null || value === "") return "not collected";
    const n = typeof value === "number" ? value : Number(value);
    if (!Number.isFinite(n)) return "not collected";
    if (n === 0) return "$0";
    const abs = Math.abs(n);
    const sign = n < 0 ? "-" : "";
    if (abs >= 1e9) return `${sign}$${(abs / 1e9).toFixed(1)}B`;
    if (abs >= 1e6) return `${sign}$${(abs / 1e6).toFixed(1)}M`;
    if (abs >= 1e3) return `${sign}$${(abs / 1e3).toFixed(0)}K`;
    return `${sign}$${abs.toFixed(0)}`;
  }
  function coords(lat: unknown, lon: unknown): string {
    const a = finite(lat);
    const b = finite(lon);
    if (a === null || b === null) return "not collected";
    return `${a.toFixed(4)}, ${b.toFixed(4)}`;
  }
  function cleanRole(value: unknown): string {
    if (typeof value !== "string") return "";
    const clean = value
      .replace(/^Supports Department of Energy through work described as:\s*/i, "")
      .replace(/IGF::[\s\S]*?::IGF\s*/g, "")
      .replace(/TAS::[\s\S]*?::TAS\s*/g, "")
      .trim();
    if (!clean) return "";
    return clean.length > 400 ? `${clean.slice(0, 400)}…` : clean;
  }
  function present(value: unknown): boolean {
    return value !== undefined && value !== null && value !== "";
  }
  function severityRole(value: string): string {
    const key = value.toLowerCase();
    if (key === "critical" || key === "high" || key === "medium" || key === "low") return key;
    return "unknown";
  }
  function factorRole(value: string): string {
    if (value === "bad" || value === "warn" || value === "ok") return value;
    return "unknown";
  }

  const osint = $derived(rec(payload?.osint));
  const shodan = $derived(rec(payload?.shodan));
  const ai = $derived(rec(osint?.ai_research));
  const onprem = $derived(rec(osint?.onprem_network));
  const serviceRisk = $derived(rec(osint?.service_risk));
  const domainDiscovery = $derived(rec(osint?.domain_discovery));
  const domainVerify = $derived(rec(osint?.domain_verify));
  const dns = $derived(rec(osint?.dns));
  const web = $derived(rec(osint?.web));
  const shodanIp = $derived(rec(osint?.shodan_ip));
  const nvd = $derived(rec(osint?.nvd_cvss));
  const roleLine = $derived(cleanRole(payload?.role));
  const showAi = $derived(ai?.queried === true);
  const aiError = $derived(typeof ai?.error === "string" && ai.error ? ai.error : "");
  const aiSources = $derived(arr(ai?.sources).slice(0, 6).map((item) => {
    const row = rec(item);
    if (!row) return "";
    return typeof row.title === "string" && row.title ? row.title : typeof row.url === "string" ? row.url : "";
  }).filter(Boolean));
  const awardAgencies = $derived(strings(payload?.awarding_agencies));
  const fundAgencies = $derived(strings(payload?.funding_agencies));
  const contractIds = $derived(strings(payload?.contract_ids));
  const people = $derived(strings(payload?.personnel));
  const hosts = $derived(arr(shodanIp?.hosts).map(rec).filter((item): item is Rec => item !== null));
  const findings = $derived(arr(rec(shodanIp?.aggregate)?.critical_findings));
  const nvdSummary = $derived(rec(nvd?.summary));
  const showInfra = $derived(Boolean(domainDiscovery || domainVerify || dns || web));
  const showOnprem = $derived(
    onprem?.queried === true && (finite(onprem.on_prem_count) ?? 0) + (finite(onprem.cloud_count) ?? 0) > 0,
  );
  const showShodan = $derived(shodan?.queried === true);
  const headers = $derived(rec(web?.security_headers));
  const tech = $derived.by(() => {
    const set = new Set<string>();
    for (const item of [...arr(dns?.technologies_detected), ...arr(web?.technologies_detected)]) {
      if (typeof item === "string" && item) set.add(item);
    }
    return [...set].sort();
  });
  const flags = $derived.by(() => {
    if (!payload) return [] as string[];
    const pairs: [string, string][] = [
      ["small_business", "Small Business"],
      ["woman_owned", "Woman-Owned"],
      ["veteran_owned", "Veteran-Owned"],
      ["minority_owned", "Minority-Owned"],
      ["for_profit", "For-Profit"],
      ["nonprofit", "Nonprofit"],
    ];
    return pairs.filter(([key]) => payload[key] === true).map(([, label]) => label);
  });
  const services = $derived.by(() => {
    const stored = arr(serviceRisk?.dangerous_services);
    const parsed: Service[] = [];
    if (stored.length) {
      for (const item of stored) {
        const row = rec(item);
        if (!row || !Number.isFinite(Number(row.port))) continue;
        parsed.push({
          port: Number(row.port),
          name: text(row.name),
          danger: String(row.danger ?? ""),
          reason: text(row.reason),
        });
      }
    } else {
      const ports = new Set<number>();
      for (const item of [...arr(shodan?.top_ports), ...arr(shodan?.sample_hosts)]) {
        const port = Number(rec(item)?.port);
        if (Number.isFinite(port)) ports.add(port);
      }
      for (const port of ports) {
        const spec = PORTS[port];
        if (spec) parsed.push({ port, ...spec });
      }
    }
    parsed.sort((a, b) => (DANGER_ORDER[a.danger] ?? 9) - (DANGER_ORDER[b.danger] ?? 9));
    return parsed;
  });
  const cves = $derived(
    arr(shodan?.vulns)
      .map((item) => rec(item)?.cve)
      .filter((item): item is string => typeof item === "string" && item.length > 0)
      .slice(0, 12),
  );
  const topPorts = $derived(
    arr(shodan?.top_ports)
      .map((item) => {
        const row = rec(item);
        if (!row || !Number.isFinite(Number(row.port))) return "";
        return `${row.port} (${row.count ?? 0})`;
      })
      .filter(Boolean),
  );
  const nvdScores = $derived.by(() => {
    const scores = rec(nvd?.scores);
    if (!scores) return [] as { id: string; rest: string }[];
    return Object.keys(scores).slice(0, 12).map((key) => {
      const row = rec(scores[key]);
      if (!row) return { id: key, rest: "" };
      const bits: string[] = [];
      if (present(row.base_score)) bits.push(String(row.base_score));
      if (typeof row.severity === "string" && row.severity) bits.push(row.severity);
      return { id: key, rest: bits.length ? ` ${bits.join(" ")}` : "" };
    });
  });
  const onCount = $derived(finite(onprem?.on_prem_count) ?? 0);
  const cloudCount = $derived(finite(onprem?.cloud_count) ?? 0);
  const onPct = $derived(
    finite(onprem?.on_prem_percentage) ?? (onCount + cloudCount > 0 ? Math.round((onCount / (onCount + cloudCount)) * 100) : 0),
  );
  const tokens = $derived(
    arr(dns?.verification_tokens)
      .map((item) => rec(item)?.service)
      .filter((item): item is string => typeof item === "string" && item.length > 0),
  );
  const shownContractIds = $derived(contractIds.slice(0, 40));
  const shownPeople = $derived(people.slice(0, 20));

  function shownIp(value: unknown): string {
    if (typeof value === "string" && value.trim()) return value;
    const row = rec(value);
    if (row && typeof row.ip === "string" && row.ip.trim()) return row.ip;
    return "";
  }
  function copyIp(ip: string) {
    try {
      const clipboard = navigator.clipboard;
      const write = clipboard && typeof clipboard.writeText === "function" ? clipboard.writeText.bind(clipboard) : null;
      if (!write) {
        copiedIp = ip;
        copyNote = "Copy failed";
        return;
      }
      void write(ip).then(
        () => {
          copiedIp = ip;
          copyNote = "Copied";
        },
        () => {
          copiedIp = ip;
          copyNote = "Copy failed";
        },
      );
    } catch {
      copiedIp = ip;
      copyNote = "Copy failed";
    }
  }
  function mission(p: Rec | null): string {
    if (!p) return "not collected";
    const name = text(p.name);
    const category = text(p.category);
    const city = text(p.city);
    const state = text(p.state);
    const dba = typeof p.dba === "string" && p.dba && p.dba !== p.name ? p.dba : "";
    const parent = typeof p.parent === "string" && p.parent && p.parent !== p.name ? p.parent : "";
    let line = dba ? `Operating as ${dba}, ${name} is a ${category} contractor` : `${name} is a ${category} contractor`;
    if (parent) line += ` (subsidiary of ${parent})`;
    line += ` located in ${city}, ${state}.`;
    if (typeof p.naics === "string" && p.naics) line += ` Primary work: ${p.naics}.`;
    if (typeof p.psc === "string" && p.psc) line += ` Product/service: ${p.psc}.`;
    const obligation = finite(p.obligation);
    if (obligation !== null && obligation > 0) line += ` Federal obligation: ${money(obligation)}.`;
    const contracts = arr(p.contract_ids);
    if (contracts.length) line += ` ${contracts.length} contracts on record.`;
    if (typeof p.award_types === "string" && p.award_types) line += ` Award: ${p.award_types}.`;
    if (typeof p.pricing_types === "string" && p.pricing_types) line += ` Pricing: ${p.pricing_types}.`;
    if (present(p.performance_start) || present(p.performance_end)) {
      line += ` Period: ${text(p.performance_start)} to ${text(p.performance_end)}.`;
    }
    const funding = strings(p.funding_agencies);
    if (funding.length) line += ` Funded by: ${funding.join(", ")}.`;
    return line;
  }

  function serviceLine(item: unknown): string {
    const row = rec(item);
    if (!row) return text(item);
    const product = typeof row.product === "string" ? row.product : "";
    const version = typeof row.version === "string" ? row.version : "";
    return `${row.port ?? ""}/${row.transport ?? ""} ${product} ${version}`.replace(/\s+/g, " ").trim();
  }
  function hostnames(host: Rec): string {
    const names = strings(host.hostnames);
    return names.length ? names.join(", ") : "not collected";
  }
  function hostServiceCount(host: Rec): number {
    return arr(host.services).length;
  }
</script>

<div class="atlas-exposure">
  <section class="sc-panel atlas-exposure__summary" aria-labelledby="exposure-summary-title">
    <h3 id="exposure-summary-title" class="sc-label">Exposure summary</h3>
    <div class="sc-kpis">
      <div class="sc-kpi">
        <p class="sc-kpi__label">Exposure score</p>
        {#if risk}
          <p class="sc-kpi__value sc-kpi__value--mono" data-severity={severityRole(risk.severity)}>{risk.score}</p>
          <p class="sc-kpi__sub" data-severity={severityRole(risk.severity)}>{risk.severity}</p>
        {:else}
          <p class="sc-kpi__value">Not available</p>
        {/if}
      </div>
    </div>
    {#if risk}
      <ul class="atlas-factors">
        {#each risk.factors as factor}
          <li data-level={factorRole(factor.level)}>{factor.text}</li>
        {/each}
      </ul>
    {/if}
    {#if services.length}
      <h4 class="sc-label">Dangerous services</h4>
      <ul class="atlas-rows">
        {#each services as svc}
          <li>
            <p>
              <button type="button" class="sc-mono atlas-action" data-severity={severityRole(svc.danger)} onclick={() => onPort(svc.port)}>{svc.port}</button>
              {svc.name}
              <span data-severity={severityRole(svc.danger)}>{svc.danger}</span>
            </p>
            <p class="atlas-note">{svc.reason}</p>
          </li>
        {/each}
      </ul>
    {/if}
    {#if findings.length}
      <h4 class="sc-label">Critical host findings</h4>
      <ul class="atlas-rows">
        {#each findings as finding}
          {@const row = rec(finding)}
          {@const ip = row ? shownIp(row.ip) : ""}
          {@const port = row ? Number(row.port) : Number.NaN}
          <li class="sc-mono">
            {#if row}
              {#if ip}
                <button type="button" class="atlas-action" onclick={() => copyIp(ip)}>
                  <AtlasIcon name="copy" />
                  {ip}
                </button>
              {:else}
                {text(row.ip)}
              {/if}:{#if RISKY_PORTS.has(port)}<button type="button" class="atlas-action" onclick={() => onPort(port)}>{text(row.port)}</button>{:else}{text(row.port)}{/if} {text(row.service)}
            {:else}
              {text(finding)}
            {/if}
          </li>
        {/each}
      </ul>
    {/if}
    {#if nvdSummary}
      <h4 class="sc-label">NVD</h4>
      <p class="sc-mono">{Object.entries(nvdSummary).map(([key, value]) => `${key} ${value ?? "not collected"}`).join(" · ")}</p>
      <ul class="atlas-rows">
        {#each nvdScores as line}
          <li class="sc-mono"><button type="button" class="atlas-action" onclick={() => onCve(line.id)}>{line.id}</button>{line.rest}</li>
        {/each}
      </ul>
    {/if}
  </section>

  <article class="sc-dossier atlas-brief" data-sc-theme="sand" aria-labelledby="atlas-brief-title">
    <h3 id="atlas-brief-title" class="sc-label">Intelligence brief</h3>
    <p class="atlas-brief__meta">Mission and role from the catalog. Queried AI research, when present, is separate from collected network evidence.</p>
    <p class="atlas-brief__prose">{mission(payload)}</p>
    {#if roleLine}<p class="atlas-brief__meta">{roleLine}</p>{/if}
    {#if showAi && ai}
      <h4 class="atlas-brief__meta">Queried AI research</h4>
      {#if aiError}
        <p class="atlas-brief__error" role="alert">{aiError}</p>
      {:else}
        <p class="atlas-brief__meta">{text(ai.company_status)}{present(ai.parent_company) ? ` · ${ai.parent_company}` : ""}{present(ai.acquisition_year) ? ` (${ai.acquisition_year})` : ""}</p>
        <p class="sc-mono atlas-brief__meta">domain {text(ai.current_domain)}{present(ai.previous_domain) ? ` was ${ai.previous_domain}` : ""} · conf {text(ai.domain_confidence)} · {ai.domain_validated === true ? "validated" : ai.domain_validated === false ? "unvalidated" : "not collected"}</p>
        {#if present(ai.brief)}<p class="atlas-brief__prose">{ai.brief}</p>{/if}
        {#if present(ai.company_status_detail)}<p class="atlas-brief__prose">{ai.company_status_detail}</p>{/if}
        {#each aiSources as title}
          <p class="atlas-brief__meta">{title}</p>
        {/each}
      {/if}
    {/if}
  </article>

  <section class="atlas-network" aria-labelledby="network-evidence-title">
    <h3 id="network-evidence-title" class="sc-label">Network evidence</h3>
    {#if showOnprem && onprem}
      <details class="atlas-disclosure sc-panel" open>
        <summary>On-prem and cloud</summary>
        <div class="atlas-disclosure__body">
          <p class="sc-mono">{onCount} on-prem ({onPct}%) · {cloudCount} cloud ({100 - onPct}%)</p>
          <p>ISP {text(onprem.inferred_isp)}</p>
          {#each arr(onprem.on_prem_ips).slice(0, 15) as ip}
            {@const label = shownIp(ip)}
            <p class="sc-mono">
              {#if label}
                <button type="button" class="atlas-action" onclick={() => copyIp(label)}>
                  <AtlasIcon name="copy" />
                  {label}
                </button>
              {:else}
                {text(ip)}
              {/if}
            </p>
          {/each}
          {#each arr(onprem.cloud_ips).slice(0, 8) as ip}
            {@const label = shownIp(ip)}
            {@const row = rec(ip)}
            <p class="sc-mono">
              {#if label}
                <button type="button" class="atlas-action" onclick={() => copyIp(label)}>
                  <AtlasIcon name="copy" />
                  {label}
                </button>
              {:else}
                {text(ip)}
              {/if}
              {#if row && typeof row.provider === "string" && row.provider} {row.provider}{/if}
            </p>
          {/each}
        </div>
      </details>
    {/if}
    {#if showInfra}
      <details class="atlas-disclosure sc-panel" open>
        <summary>Infrastructure</summary>
        <div class="atlas-disclosure__body">
          {#if domainDiscovery}<p class="sc-mono">{text(domainDiscovery.domain)}</p>{/if}
          {#if domainVerify}
            <p>{text(domainVerify.verdict)} {present(domainVerify.confidence) ? `${domainVerify.confidence}%` : "not collected"}</p>
            {#if domainVerify.is_parking === true}<p>Domain appears parked</p>{/if}
            {#if domainVerify.is_redirect_away === true}<p>Redirects to a different domain</p>{/if}
          {/if}
          {#if dns}
            {#if present(dns.mail_provider) && dns.mail_provider !== "Unknown"}<p>Mail {dns.mail_provider}</p>{/if}
            {#if present(dns.dns_provider) && dns.dns_provider !== "Unknown"}<p>DNS {dns.dns_provider}</p>{/if}
            {#if present(dns.cdn) && dns.cdn !== "Unknown" && dns.cdn !== "None"}<p>CDN {dns.cdn}</p>{/if}
            {#if present(dns.dmarc_policy)}<p>DMARC {dns.dmarc_policy}</p>{/if}
            {#if tokens.length}<div class="atlas-tags">{#each tokens as token}<span class="sc-chip">{token}</span>{/each}</div>{/if}
            {#if strings(dns.spf_includes).length}<p class="sc-mono">{strings(dns.spf_includes).join(", ")}</p>{/if}
          {/if}
          {#if web}
            {#if present(web.server)}<p class="sc-mono">{web.server}</p>{/if}
            {#if present(web.cdn_detected) && web.cdn_detected !== "None"}<p>CDN {web.cdn_detected}</p>{/if}
            {#if present(web.cms)}<p>CMS {web.cms}</p>{/if}
            {#if present(web.powered_by)}<p>{web.powered_by}</p>{/if}
            {#if strings(web.js_frameworks).length}<div class="atlas-tags">{#each strings(web.js_frameworks) as fw}<span class="sc-chip">{fw}</span>{/each}</div>{/if}
            {#if present(web.security_score) || headers}
              <p class="sc-mono">headers {text(web.security_score)}{headers ? ` HSTS ${headers.hsts ? "yes" : "no"} CSP ${headers.csp ? "yes" : "no"} X-Frame ${headers.x_frame ? "yes" : "no"} X-Content-Type ${headers.x_content_type ? "yes" : "no"}` : ""}</p>
            {/if}
          {/if}
          {#if tech.length}<div class="atlas-tags">{#each tech as item}<span class="sc-chip">{item}</span>{/each}</div>{/if}
        </div>
      </details>
    {/if}
    {#if hosts.length}
      <p class="sc-mono">{hosts.length} hosts · {findings.length} critical</p>
      {#each hosts as host, index (`${shownIp(host.ip)}:${index}`)}
        {@const ip = shownIp(host.ip)}
        {@const names = hostnames(host)}
        <details class="atlas-disclosure sc-panel">
          <summary>
            <span class="sc-mono">{ip || text(host.ip)}</span>
            <span>{hostServiceCount(host)} services</span>
            <span>{names}</span>
          </summary>
          <div class="atlas-disclosure__body">
            <p class="sc-mono">
              {#if ip}
                <button type="button" class="atlas-action" onclick={() => copyIp(ip)}>
                  <AtlasIcon name="copy" />
                  {ip}
                </button>
              {:else}
                {text(host.ip)}
              {/if}
              {present(host.org) ? host.org : ""} {present(host.os) ? host.os : ""}
            </p>
            <p class="atlas-note">{names}</p>
            {#each arr(host.services).slice(0, 10) as svc}
              <p class="sc-mono">{serviceLine(svc)}</p>
            {/each}
            {#if strings(host.vulns).length}
              <p class="sc-mono">{strings(host.vulns).slice(0, 8).join(" ")}</p>
            {/if}
          </div>
        </details>
      {/each}
    {/if}
    {#if showShodan && shodan}
      <details class="atlas-disclosure sc-panel">
        <summary>Legacy Shodan</summary>
        <div class="atlas-disclosure__body">
          <p class="sc-mono">{text(shodan.total_hosts)} hosts</p>
          {#if cves.length}
            <p class="sc-mono">{#each cves as id}<button type="button" class="atlas-action" onclick={() => onCve(id)}>{id}</button> {/each}</p>
          {/if}
          {#if topPorts.length}<p class="sc-mono">{topPorts.join(", ")}</p>{/if}
        </div>
      </details>
    {/if}
  </section>

  <details class="atlas-disclosure sc-panel">
    <summary>Contract profile</summary>
    <div class="atlas-disclosure__body">
      <h4 class="sc-label">Financial summary</h4>
      <p>Obligation <span class="sc-mono">{money(payload?.obligation)}</span></p>
      <p>Max award <span class="sc-mono">{money(payload?.max_award)}</span></p>
      <p>Contracts <span class="sc-mono">{text(payload?.contract_count)}</span></p>
      <p>Records <span class="sc-mono">{text(payload?.record_count)}</span></p>
      <h4 class="sc-label">Location</h4>
      <p>{text(payload?.address)}</p>
      <p class="sc-mono">{coords(payload?.lat, payload?.lon)}</p>
      <h4 class="sc-label">Classification</h4>
      <p>{text(payload?.naics)}</p>
      <p class="sc-mono">{text(payload?.naics_code)}</p>
      <p>{text(payload?.psc)}</p>
      <p class="sc-mono">{text(payload?.award_types)}</p>
      <p class="sc-mono">{text(payload?.pricing_types)}</p>
      <h4 class="sc-label">Business profile</h4>
      <p>{text(payload?.business_size)}</p>
      {#if flags.length}
        <div class="atlas-tags">{#each flags as flag}<span class="sc-chip">{flag}</span>{/each}</div>
      {/if}
      <h4 class="sc-label">Performance period</h4>
      <p class="sc-mono">{text(payload?.fiscal_years)}</p>
      <p class="sc-mono">{text(payload?.performance_start)} → {text(payload?.performance_end)}</p>
      {#if awardAgencies.length || fundAgencies.length}
        <h4 class="sc-label">Agencies</h4>
        {#if awardAgencies.length}<p>Awarding: {awardAgencies.join(", ")}</p>{/if}
        {#if fundAgencies.length}<p>Funding: {fundAgencies.join(", ")}</p>{/if}
      {/if}
      {#if contractIds.length}
        <h4 class="sc-label">Contract IDs</h4>
        <div class="atlas-tags">
          {#each shownContractIds as id}<span class="sc-mono">{id}</span>{/each}
        </div>
        {#if contractIds.length > 40}<p class="atlas-note">+{contractIds.length - 40} more</p>{/if}
      {/if}
      {#if people.length}
        <h4 class="sc-label">Key personnel</h4>
        {#each shownPeople as person}<p>{person}</p>{/each}
        {#if people.length > 20}<p class="atlas-note">+{people.length - 20} more</p>{/if}
      {/if}
      <h4 class="sc-label">Identifiers</h4>
      <p>UEI <span class="sc-mono">{text(payload?.uei)}</span></p>
      <p>CAGE <span class="sc-mono">{text(payload?.cage)}</span></p>
      <p>Phone <span class="sc-mono">{text(payload?.phone)}</span></p>
      <p>Email <span class="sc-mono">{text(payload?.email)}</span></p>
      <p>URL <span class="sc-mono">{text(payload?.url)}</span></p>
    </div>
  </details>

  <p class="atlas-copy-status" role="status">{#if copyNote}{copyNote}{#if copiedIp} {copiedIp}{/if}{/if}</p>
</div>

<style>
  .atlas-exposure {
    display: flex;
    flex-direction: column;
    gap: 12px;
    min-width: 0;
    overflow-wrap: anywhere;
    color: var(--sc-ink);
    font-family: var(--sc-font-ui);
    font-size: 13px;
    line-height: 1.5;
  }

  .atlas-exposure .sc-label,
  .atlas-exposure .sc-kpi__label,
  .atlas-exposure .sc-kpi__sub,
  .atlas-exposure .sc-chip {
    font-size: 13px;
  }

  .atlas-exposure :global(.sc-mono),
  .atlas-exposure .sc-mono {
    font-size: 12px;
    line-height: 1.45;
    overflow-wrap: anywhere;
  }

  .atlas-exposure__summary,
  .atlas-network {
    display: flex;
    flex-direction: column;
    gap: 8px;
    min-width: 0;
  }

  .atlas-factors,
  .atlas-rows {
    margin: 0;
    padding: 0;
    list-style: none;
  }

  .atlas-factors li,
  .atlas-rows li,
  .atlas-exposure p {
    margin: 0;
    overflow-wrap: anywhere;
  }

  .atlas-note {
    color: var(--sc-ink-2);
  }

  .atlas-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    min-width: 0;
  }

  .atlas-tags :global(.sc-chip) {
    height: auto;
    min-height: 22px;
    white-space: normal;
    overflow-wrap: anywhere;
  }

  .atlas-action {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    min-height: 34px;
    padding: 0 2px;
    border: 0;
    background: transparent;
    color: inherit;
    font: inherit;
    text-align: left;
    overflow-wrap: anywhere;
  }

  .atlas-action:focus-visible,
  .atlas-disclosure > summary:focus-visible {
    outline: 2px solid var(--sc-gold);
    outline-offset: 2px;
  }

  .atlas-exposure [data-severity="critical"],
  .atlas-exposure [data-level="bad"] {
    color: var(--sc-signal);
  }

  .atlas-exposure [data-severity="high"],
  .atlas-exposure [data-level="warn"] {
    color: var(--sc-gold);
  }

  .atlas-exposure [data-severity="medium"] {
    color: var(--sc-ink-2);
  }

  .atlas-exposure [data-severity="low"],
  .atlas-exposure [data-severity="unknown"],
  .atlas-exposure [data-level="unknown"] {
    color: var(--sc-ink-3);
  }

  .atlas-exposure [data-level="ok"] {
    color: var(--sc-olive);
  }

  .atlas-brief {
    padding: 16px;
    box-shadow: none;
    font-family: var(--sc-font-ui);
    font-size: 13px;
    line-height: 1.5;
  }

  .atlas-brief :global(.sc-label),
  .atlas-brief__meta {
    font-family: var(--sc-font-ui);
    font-size: 13px;
    line-height: 1.5;
    color: var(--sc-paper-muted);
  }

  .atlas-brief :global(.sc-label) {
    font-family: var(--sc-font-mono);
    color: var(--sc-paper-head);
  }

  .atlas-brief__prose {
    margin: 8px 0 0;
    font-family: var(--sc-font-doc);
    font-size: 16px;
    line-height: 1.6;
    color: var(--sc-paper-ink);
  }

  .atlas-brief__error {
    margin: 8px 0 0;
    color: var(--sc-signal);
  }

  .atlas-brief :global(a:not([class])) {
    color: var(--sc-paper-accent);
  }

  .atlas-brief .sc-mono {
    color: var(--sc-paper-ink);
  }

  .atlas-disclosure {
    padding: 0;
    min-width: 0;
  }

  .atlas-disclosure > summary {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    align-items: baseline;
    min-height: 34px;
    padding: 8px 12px;
    cursor: pointer;
    font-size: 13px;
    line-height: 1.4;
  }

  .atlas-disclosure__body {
    display: flex;
    flex-direction: column;
    gap: 6px;
    min-width: 0;
    padding: 0 12px 12px;
  }

  .atlas-copy-status {
    min-height: 1.25em;
    margin: 0;
    color: var(--sc-ink-2);
    font-size: 13px;
  }

  @media (pointer: coarse) {
    .atlas-action,
    .atlas-disclosure > summary {
      min-height: 44px;
    }
  }
</style>
