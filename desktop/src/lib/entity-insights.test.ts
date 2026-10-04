import assert from "node:assert/strict";
import test from "node:test";
import { summarizeEntity } from "./entity-insights.ts";

test("missing or malformed collection is unknown, never a zero observation", () => {
  for (const payload of [null, {}, { obligation: null, contract_count: false }, { obligation: true, contract_count: [] }]) {
    const summary = summarizeEntity(payload);
    assert.equal(summary.obligation, "—");
    assert.equal(summary.contracts, "—");
    assert.equal(summary.hosts, "—");
    assert.equal(summary.cves, "—");
  }
  const partial = summarizeEntity({ osint: { shodan_ip: { queried: true }, service_risk: { queried: true } } });
  assert.equal(partial.hosts, "—");
  assert.equal(partial.services, "—");
});

test("successful zero and failed default zero remain distinct", () => {
  const empty = summarizeEntity({ obligation: 0, contract_ids: [], osint: {
    shodan_ip: { queried: true, ips_enriched: 0, hosts: [], aggregate: { total_vulns: 0 } },
    service_risk: { queried: true, total_services: 0 },
  } });
  assert.equal(empty.obligation, "$0");
  assert.equal(empty.contracts, "0");
  assert.equal(empty.hosts, "0");
  assert.equal(empty.cves, "0");
  assert.equal(empty.services, "0");
  const failed = summarizeEntity({ osint: { shodan_ip: { queried: false, error: "HTTP 503", ips_enriched: 0, hosts: [] } } });
  assert.equal(failed.hosts, "—");
  assert.equal(failed.cves, "—");
  assert.equal(failed.sources.filter((source) => source.state === "error").length, 1);
});

test("an empty IP lookup does not erase hosts in the legacy collection", () => {
  const summary = summarizeEntity({ shodan: { queried: true, total_hosts: 4 }, osint: { shodan_ip: { queried: true, ips_enriched: 0, hosts: [] } } });
  assert.equal(summary.hosts, "4");
});

test("recorded CVEs include host-only IDs and are not limited to CVSS-scored subset", () => {
  const summary = summarizeEntity({ shodan: { queried: true, vulns: [{ cve: "CVE-2024-1234" }] }, osint: {
    shodan_ip: { queried: true, hosts: [{ vulns: ["CVE-2024-1234", "CVE-2024-5678", "CVE-2024-9012"] }], aggregate: { total_vulns: 3 } },
    nvd_cvss: { queried: true, total_cves: 8, scored_cves: 1, scores: { "CVE-2024-1234": {} } },
  } });
  assert.equal(summary.cves, "8");
  const hostOnly = summarizeEntity({ osint: { shodan_ip: { queried: true, hosts: [{ vulns: ["CVE-2024-1234", "CVE-2024-1234", "CVE-2024-5678"] }] } } });
  assert.equal(hostOnly.cves, "2");
});

test("a scoring outage retains NVD inventory without claiming successful collection", () => {
  const summary = summarizeEntity({ osint: { nvd_cvss: { queried: true, total_cves: 40, scored_cves: 0, error: "All 40 CVE lookups failed", query_time: "2026-10-01T12:00:00Z" } } });
  assert.equal(summary.cves, "40");
  assert.equal(summary.latestEvidence, "");
  assert.equal(summary.sources.filter((source) => source.state === "error").length, 1);
});

test("invalidated history cannot create a current domain mismatch or freshness", () => {
  const summary = summarizeEntity({ osint: {
    domain_discovery: { queried: true, domain: "new.example", query_time: "2026-01-01T12:00:00Z" },
    dns: { queried: false, _invalidated_by: "ai_research_sync", domain: "old.example", query_time: "2026-09-01T12:00:00Z" },
    web: { queried: true, domain: "https://www.new.example/", query_time: "2026-02-01T12:00:00Z" },
  } });
  assert.equal(summary.domainMismatch, false);
  assert.equal(summary.latestEvidence, "2026-02-01");
  assert.equal(summary.sources.find((source) => source.observedAt === "2026-09-01")?.state, "stale");
  const mismatch = summarizeEntity({ osint: { domain_discovery: { domain: "new.example" }, dns: { queried: true, domain: "new.example" }, web: { queried: true, domain: "different.example" } } });
  assert.equal(mismatch.domainMismatch, true);
});

test("collector no-result sentinels are empty; missing identifiers are not outages", () => {
  const summary = summarizeEntity({ shodan: { queried: false, error: "no_searchable_identifier" }, osint: {
    domain_discovery: { queried: true, error: "no_domain_found" },
    onprem_network: { queried: true, error: "no_ips_found", on_prem_count: 0, cloud_count: 0 },
  } });
  assert.equal(summary.sources.filter((source) => source.state === "empty").length, 2);
  assert.equal(summary.sources.filter((source) => source.state === "error").length, 0);
  assert.equal(summary.collectedCount, 2);
});

test("facility metadata retains operator without fabricating a contractor assessment", () => {
  const summary = summarizeEntity({ type: "Feature", properties: { type: "data_center", tags: { name: "Site A", operator: "Example Operator", "addr:city": "Austin", "addr:state": "TX" } } });
  assert.equal(summary.operator, "Example Operator");
  assert.equal(summary.category, "data center");
  assert.equal(summary.location, "Austin, TX");
  assert.equal(summary.hosts, "—");
  assert.equal(summary.obligation, "—");
  assert.equal(summary.sourceCount, 0);
});
