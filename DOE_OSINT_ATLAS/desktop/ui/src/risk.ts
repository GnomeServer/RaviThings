/** Port of computeRiskScore / RISKY_PORTS from frontend/static/contractor-map.html. */

export const RISKY_PORTS = new Set([
  21, 23, 25, 110, 143, 445, 1433, 1521, 3306, 3389, 5432, 5900, 6379, 8080, 8443, 9200, 11211, 27017,
]);


export type RiskFactor = { text: string; level: "bad" | "warn" | "ok" };
export type RiskResult = { score: number; severity: string; factors: RiskFactor[] };

type Rec = Record<string, unknown>;

function obj(v: unknown): Rec {
  return v && typeof v === "object" && !Array.isArray(v) ? (v as Rec) : {};
}

function arr(v: unknown): Rec[] {
  return Array.isArray(v) ? (v as Rec[]) : [];
}

export function computeRiskScore(c: Rec): RiskResult {
  let score = 0;
  const factors: RiskFactor[] = [];

  const s = obj(c.shodan);
  const o = obj(c.osint);
  const dns = obj(o.dns);
  const web = obj(o.web);
  const ct = obj(o.ct);
  const sip = obj(o.shodan_ip);
  const sipAgg = obj(sip.aggregate);

  const exposedHosts = (sip.ips_enriched as number) || (s.total_hosts as number) || 0;
  if (exposedHosts > 0) {
    const hostScore = Math.min(exposedHosts / 20, 1) * 20;
    score += hostScore;
    if (exposedHosts > 5) factors.push({ text: `${exposedHosts} exposed hosts`, level: "bad" });
    else factors.push({ text: `${exposedHosts} exposed host(s)`, level: "warn" });
  }

  const critFindings = arr(sipAgg.critical_findings);
  if (critFindings.length > 0) {
    score += Math.min(critFindings.length * 5, 15);
    const svcNames = [...new Set(critFindings.map((f) => String(f.service ?? "")))].join(", ");
    factors.push({ text: `${critFindings.length} critical exposures (${svcNames})`, level: "bad" });
  }

  const vulnCount = arr(s.vulns).length;
  const nvd = obj(o.nvd_cvss);
  const nvdSummary = obj(nvd.summary);
  const hasCVSS = Number(nvd.scored_cves) > 0;

  if (vulnCount > 0) {
    if (hasCVSS) {
      const weightedScore =
        ((Number(nvdSummary.critical) || 0) * 4 +
          (Number(nvdSummary.high) || 0) * 3 +
          (Number(nvdSummary.medium) || 0) * 2 +
          (Number(nvdSummary.low) || 0)) /
        (Number(nvd.scored_cves) * 4);
      score += weightedScore * 30;
      if (Number(nvdSummary.critical) > 0) {
        factors.push({ text: `${nvdSummary.critical} CRITICAL CVEs (CVSS 9.0+)`, level: "bad" });
      } else if (Number(nvdSummary.high) > 0) {
        factors.push({ text: `${nvdSummary.high} HIGH CVEs (CVSS 7.0+)`, level: "bad" });
      } else {
        factors.push({ text: `${vulnCount} CVEs (scored)`, level: "warn" });
      }
    } else {
      score += Math.min(vulnCount / 15, 1) * 30;
      if (vulnCount >= 5) factors.push({ text: `${vulnCount} known CVEs`, level: "bad" });
      else factors.push({ text: `${vulnCount} CVEs`, level: "warn" });
    }
  }

  const sr = obj(o.service_risk);
  const dangerSummary = obj(sr.danger_summary);
  const criticalSvcs = Number(dangerSummary.critical) || 0;
  const highSvcs = Number(dangerSummary.high) || 0;

  if (criticalSvcs > 0 || highSvcs > 0) {
    score += Math.min((criticalSvcs * 3 + highSvcs * 1.5) / 8, 1) * 15;
    if (criticalSvcs > 0) factors.push({ text: `${criticalSvcs} critical services exposed`, level: "bad" });
    else factors.push({ text: `${highSvcs} high-risk services`, level: "warn" });
  } else {
    const riskyPortCount = arr(s.top_ports).filter((p) => RISKY_PORTS.has(Number(p.port))).length;
    if (riskyPortCount > 0) {
      score += Math.min(riskyPortCount / 5, 1) * 15;
      factors.push({ text: `${riskyPortCount} risky ports`, level: "bad" });
    }
  }

  const dmarc = dns.dmarc_policy as string | undefined;
  if (!dmarc || dmarc === "not_set" || dmarc === "none") {
    score += 10;
    factors.push({ text: dmarc === "none" ? "DMARC=none" : "No DMARC", level: "bad" });
  } else if (dmarc === "quarantine") {
    score += 3;
    factors.push({ text: "DMARC=quarantine", level: "warn" });
  } else if (dmarc === "reject") {
    factors.push({ text: "DMARC=reject", level: "ok" });
  }

  const webSec = web.security_score;
  if (typeof webSec === "number") {
    score += Math.max(0, (100 - webSec) / 100) * 10;
    if (webSec < 30) factors.push({ text: `Sec headers: ${webSec}/100`, level: "bad" });
    else if (webSec < 60) factors.push({ text: `Sec headers: ${webSec}/100`, level: "warn" });
  } else if (dns.queried) {
    score += 5;
  }

  const subCount = arr(ct.subdomains).length;
  if (subCount > 10) {
    score += Math.min((subCount - 10) / 40, 1) * 10;
    factors.push({ text: `${subCount} subdomains exposed`, level: "warn" });
  }

  const sampleHosts = arr(s.sample_hosts);
  const hasExpiredSSL = sampleHosts.some((h) => {
    if (!h.ssl_expires) return false;
    return new Date(String(h.ssl_expires)) < new Date();
  });
  if (hasExpiredSSL) {
    score += 5;
    factors.push({ text: "Expired SSL cert", level: "bad" });
  }

  score = Math.min(Math.round(score), 100);
  let severity: string;
  if (score >= 70) severity = "critical";
  else if (score >= 40) severity = "high";
  else if (score >= 15) severity = "medium";
  else severity = "low";

  return { score, severity, factors };
}
