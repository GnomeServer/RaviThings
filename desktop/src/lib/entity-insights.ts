type RecordValue = Record<string, unknown>;
export type EvidenceSource = {
  label: string;
  state: "collected" | "empty" | "error" | "missing" | "stale";
  detail: string;
  observedAt: string;
};
export type EntitySummary = {
  category: string;
  location: string;
  address: string;
  operator: string;
  domain: string;
  obligation: string;
  contracts: string;
  hosts: string;
  cves: string;
  services: string;
  sources: EvidenceSource[];
  collectedCount: number;
  sourceCount: number;
  latestEvidence: string;
  domainMismatch: boolean;
};

function record(value: unknown): RecordValue | null {
  return value !== null && typeof value === "object" && !Array.isArray(value) ? value as RecordValue : null;
}
function string(value: unknown): string {
  return typeof value === "string" ? value.trim() : "";
}
function number(value: unknown): number | null {
  if (typeof value !== "number" && (typeof value !== "string" || !value.trim())) return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}
function count(value: unknown): number | null {
  const parsed = number(value);
  return parsed !== null && parsed >= 0 && Number.isInteger(parsed) ? parsed : null;
}
function arrayCount(value: unknown): number | null {
  return Array.isArray(value) ? value.length : null;
}
function displayCount(value: number | null): string {
  return value === null ? "—" : value.toLocaleString("en-US");
}
function money(value: unknown): string {
  const amount = number(value);
  if (amount === null) return "—";
  const abs = Math.abs(amount);
  const sign = amount < 0 ? "−" : "";
  for (const [size, unit] of [[1e9, "B"], [1e6, "M"], [1e3, "K"]] as const) {
    if (abs >= size) return `${sign}$${(abs / size).toFixed(1)}${unit}`;
  }
  return `${sign}$${abs.toFixed(0)}`;
}
function noResults(source: RecordValue | null): boolean {
  return /^(no_results|no results|no_domain_found|no_ips_found)$/i.test(string(source?.error));
}
function collected(source: RecordValue | null): boolean {
  return !!source && !source._invalidated_by && (noResults(source) || (source.queried === true && !source.error));
}
function observed(source: RecordValue | null): string {
  const time = string(source?.query_time);
  return /^\d{4}-\d{2}-\d{2}(T|$)/.test(time) && Number.isFinite(Date.parse(time)) ? time.slice(0, 10) : "";
}
function sourceRecord(label: string, source: RecordValue | null, detail: string, empty = false): EvidenceSource {
  if (source?._invalidated_by) return { label, state: "stale", detail: "Invalidated after domain change; collection must be refreshed", observedAt: observed(source) };
  if (source?.error === "no_searchable_identifier") return { label, state: "missing", detail: "No searchable identifier", observedAt: "" };
  if (noResults(source)) return { label, state: "empty", detail: source?.error === "no_ips_found" ? "No IPs found" : source?.error === "no_domain_found" ? "No domain found" : "No results returned", observedAt: observed(source) };
  if (source?.error) return { label, state: "error", detail: [detail, string(source.error) || "Collection failed"].filter(Boolean).join(" · "), observedAt: observed(source) };
  if (!source || source.queried !== true) return { label, state: "missing", detail: "Not collected", observedAt: "" };
  return { label, state: empty ? "empty" : "collected", detail: detail || "No observation details recorded", observedAt: observed(source) };
}
function countedDetail(value: number | null, unit: string): string {
  return value === null ? "" : `${displayCount(value)} ${unit}`;
}
function normalizeDomain(value: unknown): string {
  return string(value).toLowerCase().replace(/^https?:\/\//, "").split("/")[0].replace(/^www\./, "").replace(/\.$/, "");
}

/** Recorded evidence only. Missing, failed and successfully empty observations stay distinct. */
export function summarizeEntity(payload: RecordValue | null): EntitySummary {
  const unknown: EntitySummary = {
    category: "", location: "", address: "", operator: "", domain: "", obligation: "—", contracts: "—", hosts: "—", cves: "—", services: "—",
    sources: [], collectedCount: 0, sourceCount: 0, latestEvidence: "", domainMismatch: false,
  };
  if (!payload) return unknown;
  const properties = record(payload.properties);
  if (payload.type === "Feature" || properties) {
    const tags = record(properties?.tags) ?? {};
    const props = properties ?? {};
    const facilityType = string(props.type) || string(tags.man_made) || string(tags.waterway) || string(tags.power) || string(tags.building);
    const city = string(props["addr:city"]) || string(tags["addr:city"]);
    const state = string(props["addr:state"]) || string(tags["addr:state"]);
    return {
      ...unknown,
      category: (facilityType || "Facility").replaceAll("_", " "),
      location: [city, state].filter(Boolean).join(", "),
      address: string(props["addr:full"]) || string(tags["addr:full"]),
      operator: string(props.operator) || string(tags.operator),
    };
  }

  const osint = record(payload.osint);
  const discovery = record(osint?.domain_discovery);
  const verification = record(osint?.domain_verify);
  const dns = record(osint?.dns);
  const web = record(osint?.web);
  const ct = record(osint?.ct);
  const ip = record(osint?.shodan_ip);
  const legacy = record(payload.shodan);
  const nvd = record(osint?.nvd_cvss);
  const services = record(osint?.service_risk);
  const network = record(osint?.onprem_network);
  const aggregate = record(ip?.aggregate);
  const domain = string(discovery?.domain) || string(record(osint?.ai_research)?.current_domain) || string(verification?.domain) || string(dns?.domain) || string(web?.domain);
  const identity = normalizeDomain(domain);
  const recordedHosts = [
    collected(ip) ? count(ip?.ips_enriched) ?? arrayCount(ip?.hosts) : null,
    collected(legacy) ? count(legacy?.total_hosts) ?? (noResults(legacy) ? 0 : null) : null,
  ].filter((value): value is number => value !== null);
  const hostCount = recordedHosts.length ? Math.max(...recordedHosts) : null;
  const serviceCount = collected(services) ? count(services?.total_services) : collected(ip) ? count(aggregate?.total_services) : null;

  // NVD scored_cves is only the scored subset. Never substitute it for the recorded CVE inventory.
  const cveIds = new Set<string>();
  const addCve = (value: unknown) => {
    const id = string(value).toUpperCase();
    if (/^CVE-\d{4}-\d{4,}$/.test(id)) cveIds.add(id);
  };
  if (Array.isArray(legacy?.vulns)) for (const item of legacy.vulns) addCve(typeof item === "string" ? item : record(item)?.cve);
  if (Array.isArray(ip?.hosts)) for (const host of ip.hosts) {
    const vulns = record(host)?.vulns;
    if (Array.isArray(vulns)) for (const id of vulns) addCve(id);
  }
  const scores = record(nvd?.scores);
  if (scores) for (const id of Object.keys(scores)) addCve(id);
  const cveCounts = [
    nvd?.queried === true && !nvd._invalidated_by ? count(nvd.total_cves) : null,
    collected(ip) ? count(aggregate?.total_vulns) : null,
    collected(legacy) && Array.isArray(legacy?.vulns) ? legacy.vulns.length : null,
  ].filter((value): value is number => value !== null);
  if (cveIds.size) cveCounts.push(cveIds.size);
  const cveCount = cveCounts.length ? Math.max(...cveCounts) : null;
  const ctCount = count(ct?.subdomain_count) ?? arrayCount(ct?.unique_subdomains);
  const onpremCount = count(network?.on_prem_count);
  const cloudCount = count(network?.cloud_count);
  const nvdCount = count(nvd?.total_cves);
  const ipCount = count(ip?.ips_enriched) ?? arrayCount(ip?.hosts);
  const legacyCount = count(legacy?.total_hosts);
  const asn = record(osint?.asn);
  const sources: EvidenceSource[] = [
    sourceRecord("Domain discovery", discovery, string(discovery?.domain)),
    sourceRecord("Domain verification", verification, [string(verification?.domain), string(verification?.verdict)].filter(Boolean).join(" · ")),
    sourceRecord("DNS", dns, string(dns?.domain)),
    sourceRecord("Web presence", web, [string(web?.domain), string(web?.server)].filter(Boolean).join(" · ")),
    sourceRecord("Certificate transparency", ct, countedDetail(ctCount, "subdomains"), ctCount === 0),
    sourceRecord("ASN host discovery", asn, countedDetail(arrayCount(asn?.hosts), "hosts returned"), arrayCount(asn?.hosts) === 0),
    sourceRecord("Shodan IP lookup", ip, countedDetail(ipCount, "hosts"), ipCount === 0),
    sourceRecord("Legacy Shodan", legacy, countedDetail(legacyCount, "hosts"), legacyCount === 0),
    sourceRecord("On-prem / cloud", network, onpremCount !== null || cloudCount !== null ? `${displayCount(onpremCount)} on-prem · ${displayCount(cloudCount)} cloud` : "", onpremCount === 0 && cloudCount === 0),
    sourceRecord("Service risk", services, countedDetail(count(services?.total_services), "services assessed"), count(services?.total_services) === 0),
    sourceRecord("NVD", nvd, nvdCount !== null ? `${displayCount(nvdCount)} recorded CVEs · ${displayCount(count(nvd?.scored_cves))} scored` : "", nvdCount === 0),
  ];
  let latestEvidence = "";
  let collectedCount = 0;
  for (const source of sources) {
    if (source.state === "collected" || source.state === "empty") {
      collectedCount += 1;
      if (source.observedAt > latestEvidence) latestEvidence = source.observedAt;
    }
  }
  return {
    category: string(payload.category),
    location: [string(payload.city), string(payload.state)].filter(Boolean).join(", "),
    address: string(payload.address), operator: "", domain,
    obligation: money(payload.obligation),
    contracts: displayCount(count(payload.contract_count) ?? arrayCount(payload.contract_ids)),
    hosts: displayCount(hostCount), cves: displayCount(cveCount), services: displayCount(serviceCount),
    sources, collectedCount, sourceCount: sources.length, latestEvidence,
    domainMismatch: !!identity && [dns, web].some((source) => {
      if (source?.queried !== true || source._invalidated_by) return false;
      const observedDomain = normalizeDomain(source?.domain);
      return !!observedDomain && observedDomain !== identity;
    }),
  };
}
