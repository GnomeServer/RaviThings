"""DNS intelligence gathering for DOE contractor domain enrichment.

Resolves A, MX, NS, TXT, DMARC, and CNAME records for a given domain,
then infers mail providers, DNS providers, CDN, hosting, and third-party
service integrations from the raw record data.

Requires: dnspython >= 2.8.0
Usage:
    from osint.dns_intel import enrich_dns
    result = enrich_dns("example-contractor.com")
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

import dns.exception
import dns.resolver

# ---------------------------------------------------------------------------
# Provider detection mappings
# ---------------------------------------------------------------------------

MAIL_PROVIDERS: list[tuple[str, str]] = [
    ("google.com", "Google Workspace"),
    ("googlemail.com", "Google Workspace"),
    ("outlook.com", "Microsoft 365"),
    ("protection.outlook.com", "Microsoft 365"),
    ("pphosted.com", "Proofpoint"),
    ("mimecast.com", "Mimecast"),
    ("barracuda.com", "Barracuda"),
    ("messagelabs.com", "Symantec/Broadcom"),
    ("fireeyecloud.com", "Trellix (FireEye)"),
    ("emailsrvr.com", "Rackspace"),
    ("secureserver.net", "GoDaddy"),
    ("zoho.com", "Zoho Mail"),
    ("yahoodns.net", "Yahoo Mail"),
    ("exclaimer.net", "Exclaimer"),
    ("protonmail.ch", "ProtonMail"),
    ("tutanota.de", "Tutanota"),
    ("forcepoint.com", "Forcepoint"),
]

DNS_PROVIDERS: list[tuple[str, str]] = [
    ("cloudflare.com", "Cloudflare"),
    ("awsdns", "AWS Route53"),
    ("googledomains.com", "Google Cloud DNS"),
    ("google.com", "Google Cloud DNS"),
    ("azure-dns.com", "Azure DNS"),
    ("azure-dns.net", "Azure DNS"),
    ("azure-dns.org", "Azure DNS"),
    ("azure-dns.info", "Azure DNS"),
    ("domaincontrol.com", "GoDaddy"),
    ("registrar-servers.com", "Namecheap"),
    ("digitalocean.com", "DigitalOcean"),
    ("linode.com", "Linode (Akamai)"),
    ("dynect.net", "Oracle Dyn"),
    ("ultradns.com", "Neustar UltraDNS"),
    ("ultradns.net", "Neustar UltraDNS"),
    ("ultradns.org", "Neustar UltraDNS"),
    ("nsone.net", "NS1 (IBM)"),
    ("name-services.com", "Enom"),
    ("he.net", "Hurricane Electric"),
    ("dnsmadeeasy.com", "DNS Made Easy"),
    ("worldnic.com", "Network Solutions"),
    ("hover.com", "Hover"),
]

CDN_SIGNATURES: list[tuple[str, str]] = [
    ("cloudflare", "Cloudflare"),
    ("cloudfront.net", "AWS CloudFront"),
    ("akamai", "Akamai"),
    ("edgekey.net", "Akamai"),
    ("edgesuite.net", "Akamai"),
    ("akamaiedge.net", "Akamai"),
    ("fastly", "Fastly"),
    ("azureedge.net", "Azure CDN"),
    ("azurefd.net", "Azure Front Door"),
    ("trafficmanager.net", "Azure Traffic Manager"),
    ("netlify", "Netlify"),
    ("vercel", "Vercel"),
    ("herokuapp.com", "Heroku"),
    ("pantheon.io", "Pantheon"),
    ("wpengine.com", "WP Engine"),
    ("squarespace.com", "Squarespace"),
    ("shopify.com", "Shopify"),
    ("incapdns.net", "Imperva/Incapsula"),
    ("sucuri.net", "Sucuri"),
    ("stackpathdns.com", "StackPath"),
    ("github.io", "GitHub Pages"),
    ("googleapis.com", "Google Cloud"),
    ("googlehosted.com", "Google Cloud"),
]

HOSTING_SIGNATURES: list[tuple[str, str]] = [
    ("amazonaws.com", "AWS"),
    ("cloudfront.net", "AWS"),
    ("awsdns", "AWS"),
    ("azure", "Microsoft Azure"),
    ("googleusercontent.com", "Google Cloud"),
    ("bc.googleusercontent.com", "Google Cloud"),
    ("1e100.net", "Google Cloud"),
    ("digitalocean", "DigitalOcean"),
    ("linode", "Linode (Akamai)"),
    ("vultr", "Vultr"),
    ("hetzner", "Hetzner"),
    ("ovh.net", "OVHcloud"),
    ("rackspace", "Rackspace"),
    ("softlayer", "IBM Cloud"),
    ("oracle", "Oracle Cloud"),
]

VERIFICATION_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("Google", re.compile(r"google-site-verification=(\S+)")),
    ("Microsoft", re.compile(r"(MS=\S+)")),
    ("Atlassian", re.compile(r"(atlassian-domain-verification=\S+)")),
    ("DocuSign", re.compile(r"(docusign=\S+)")),
    ("Facebook", re.compile(r"(facebook-domain-verification=\S+)")),
    ("Zoom", re.compile(r"(zoom-domain-verification=\S+)")),
    ("Slack", re.compile(r"(slack-domain-verification=\S+)")),
    ("Adobe", re.compile(r"(adobe-idp-site-verification=\S+)")),
    ("Salesforce", re.compile(r"(salesforce-allowed-domains=\S+)")),
    ("HubSpot", re.compile(r"(hubspot-developer-verification=\S+)")),
    ("Dropbox", re.compile(r"(dropbox-domain-verification=\S+)")),
    ("Cisco Webex", re.compile(r"(webexdomainverification\.\S+)")),
    ("Citrix", re.compile(r"(citrix-verification-code=\S+)")),
    ("Sophos", re.compile(r"(sophos-domain-verification=\S+)")),
    ("GlobalSign", re.compile(r"(globalsign-domain-verification=\S+)")),
    ("Apple", re.compile(r"(apple-domain-verification=\S+)")),
    ("Stripe", re.compile(r"(stripe-verification=\S+)")),
    ("Dynatrace", re.compile(r"(dynatrace-site-verification=\S+)")),
    ("Sendinblue", re.compile(r"(sendinblue-code:\S+)")),
    ("Mailchimp", re.compile(r"(mailchimp-domain-verification=\S+)")),
]

# ---------------------------------------------------------------------------
# Internal resolver configuration
# ---------------------------------------------------------------------------

_RESOLVER_TIMEOUT = 5  # seconds per query
_RESOLVER_LIFETIME = 10  # total seconds for all retries


def _make_resolver() -> dns.resolver.Resolver:
    """Create a configured DNS resolver instance."""
    resolver = dns.resolver.Resolver()
    resolver.timeout = _RESOLVER_TIMEOUT
    resolver.lifetime = _RESOLVER_LIFETIME
    return resolver


# ---------------------------------------------------------------------------
# Record-type resolution helpers
# ---------------------------------------------------------------------------

def _resolve_a(resolver: dns.resolver.Resolver, domain: str) -> list[str]:
    """Resolve A records and return list of IPv4 addresses."""
    answer = resolver.resolve(domain, "A")
    return sorted(str(rdata) for rdata in answer)


def _resolve_mx(
    resolver: dns.resolver.Resolver, domain: str,
) -> tuple[list[dict[str, Any]], str]:
    """Resolve MX records and identify the mail provider.

    Returns:
        Tuple of (mx_record_list, mail_provider_name).
    """
    answer = resolver.resolve(domain, "MX")
    records: list[dict[str, Any]] = []
    for rdata in answer:
        exchange = str(rdata.exchange).rstrip(".")
        records.append({"priority": rdata.preference, "exchange": exchange})
    records.sort(key=lambda r: r["priority"])

    # Detect mail provider from exchanges
    provider = _identify_mail_provider(records)
    return records, provider


def _identify_mail_provider(mx_records: list[dict[str, Any]]) -> str:
    """Match MX exchanges against known mail provider signatures."""
    for rec in mx_records:
        exchange_lower = rec["exchange"].lower()
        for signature, name in MAIL_PROVIDERS:
            if signature in exchange_lower:
                return name
    # If MX records exist but no known provider matched, it is likely on-prem.
    if mx_records:
        return "On-premise"
    return "Unknown"


def _resolve_ns(
    resolver: dns.resolver.Resolver, domain: str,
) -> tuple[list[str], str]:
    """Resolve NS records and identify the DNS hosting provider.

    Returns:
        Tuple of (nameserver_list, dns_provider_name).
    """
    answer = resolver.resolve(domain, "NS")
    nameservers = sorted(str(rdata).rstrip(".") for rdata in answer)

    provider = _identify_dns_provider(nameservers)
    return nameservers, provider


def _identify_dns_provider(nameservers: list[str]) -> str:
    """Match nameservers against known DNS provider signatures."""
    for ns in nameservers:
        ns_lower = ns.lower()
        for signature, name in DNS_PROVIDERS:
            if signature in ns_lower:
                return name
    return "Unknown"


def _resolve_txt(
    resolver: dns.resolver.Resolver, domain: str,
) -> tuple[list[str], list[str], list[dict[str, str]]]:
    """Resolve TXT records, extract SPF includes and verification tokens.

    Returns:
        Tuple of (raw_txt_records, spf_includes, verification_tokens).
    """
    answer = resolver.resolve(domain, "TXT")
    raw_records: list[str] = []
    spf_includes: list[str] = []
    verification_tokens: list[dict[str, str]] = []

    for rdata in answer:
        # TXT rdata may contain multiple strings concatenated; join them.
        text = str(rdata).strip('"')
        raw_records.append(text)

        # Parse SPF record
        if text.lower().startswith("v=spf1"):
            spf_includes.extend(_parse_spf_includes(text))

        # Detect verification tokens
        for service, pattern in VERIFICATION_PATTERNS:
            match = pattern.search(text)
            if match:
                verification_tokens.append({
                    "service": service,
                    "token": match.group(0),
                })

    return raw_records, spf_includes, verification_tokens


def _parse_spf_includes(spf_text: str) -> list[str]:
    """Extract all 'include:' values from an SPF record string."""
    return re.findall(r"include:(\S+)", spf_text)


def _resolve_dmarc(resolver: dns.resolver.Resolver, domain: str) -> str:
    """Resolve the _dmarc TXT record and extract the policy value.

    Returns one of: 'none', 'quarantine', 'reject', or 'not_set'.
    """
    dmarc_domain = f"_dmarc.{domain}"
    answer = resolver.resolve(dmarc_domain, "TXT")
    for rdata in answer:
        text = str(rdata).strip('"')
        if "v=dmarc1" in text.lower():
            policy_match = re.search(r";\s*p\s*=\s*(\w+)", text, re.IGNORECASE)
            if policy_match:
                policy = policy_match.group(1).lower()
                if policy in ("none", "quarantine", "reject"):
                    return policy
    return "not_set"


def _resolve_www_cname(
    resolver: dns.resolver.Resolver, domain: str,
) -> tuple[str, str]:
    """Resolve the CNAME for www.<domain> and detect CDN/hosting.

    Returns:
        Tuple of (cdn_name, hosting_provider_name).
    """
    www_domain = f"www.{domain}"
    answer = resolver.resolve(www_domain, "CNAME")
    cname_target = str(list(answer)[0]).rstrip(".")
    cname_lower = cname_target.lower()

    cdn = _identify_cdn(cname_lower)
    hosting = _identify_hosting(cname_lower)

    return cdn, hosting


def _identify_cdn(cname_lower: str) -> str:
    """Match a CNAME target against known CDN signatures."""
    for signature, name in CDN_SIGNATURES:
        if signature in cname_lower:
            return name
    return "Unknown"


def _identify_hosting(cname_lower: str) -> str:
    """Match a CNAME target against known hosting provider signatures."""
    for signature, name in HOSTING_SIGNATURES:
        if signature in cname_lower:
            return name
    return "Unknown"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def enrich_dns(domain: str) -> dict[str, Any]:
    """Perform comprehensive DNS intelligence gathering for a domain.

    Resolves A, MX, NS, TXT, DMARC, and www CNAME records independently,
    so a failure in one record type does not block the others.  Infers mail
    provider, DNS provider, CDN, hosting, verification tokens, and
    aggregated technology fingerprints from the raw DNS data.

    Args:
        domain: The target domain name (e.g. ``"contractor.energy.gov"``).

    Returns:
        A dictionary containing all resolved records, inferred providers,
        detected technologies, and any per-record-type errors.  The
        top-level ``error`` key is ``None`` unless a catastrophic failure
        occurred that prevented *all* lookups.
    """
    domain = domain.strip().lower().rstrip(".")
    resolver = _make_resolver()

    result: dict[str, Any] = {
        "queried": True,
        "query_time": datetime.now(timezone.utc).isoformat(),
        "domain": domain,
        "a_records": [],
        "mx_records": [],
        "mail_provider": "Unknown",
        "ns_records": [],
        "dns_provider": "Unknown",
        "txt_records": [],
        "spf_includes": [],
        "verification_tokens": [],
        "dmarc_policy": "not_set",
        "cdn": "Unknown",
        "hosting_provider": "Unknown",
        "technologies_detected": [],
        "error": None,
    }

    _dns_errors: list[str] = []

    # --- A records ---
    try:
        result["a_records"] = _resolve_a(resolver, domain)
    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer,
            dns.resolver.NoNameservers, dns.exception.Timeout) as exc:
        _dns_errors.append(f"A: {type(exc).__name__}")

    # --- MX records ---
    try:
        mx_records, mail_provider = _resolve_mx(resolver, domain)
        result["mx_records"] = mx_records
        result["mail_provider"] = mail_provider
    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer,
            dns.resolver.NoNameservers, dns.exception.Timeout) as exc:
        _dns_errors.append(f"MX: {type(exc).__name__}")

    # --- NS records ---
    try:
        ns_records, dns_provider = _resolve_ns(resolver, domain)
        result["ns_records"] = ns_records
        result["dns_provider"] = dns_provider
    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer,
            dns.resolver.NoNameservers, dns.exception.Timeout) as exc:
        _dns_errors.append(f"NS: {type(exc).__name__}")

    # --- TXT records ---
    try:
        txt_records, spf_includes, tokens = _resolve_txt(resolver, domain)
        result["txt_records"] = txt_records
        result["spf_includes"] = spf_includes
        result["verification_tokens"] = tokens
    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer,
            dns.resolver.NoNameservers, dns.exception.Timeout) as exc:
        _dns_errors.append(f"TXT: {type(exc).__name__}")

    # --- DMARC policy ---
    try:
        result["dmarc_policy"] = _resolve_dmarc(resolver, domain)
    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer,
            dns.resolver.NoNameservers, dns.exception.Timeout) as exc:
        _dns_errors.append(f"DMARC: {type(exc).__name__}")

    # --- www CNAME (CDN / hosting detection) ---
    try:
        cdn, hosting = _resolve_www_cname(resolver, domain)
        result["cdn"] = cdn
        result["hosting_provider"] = hosting
    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer,
            dns.resolver.NoNameservers, dns.exception.Timeout) as exc:
        _dns_errors.append(f"CNAME: {type(exc).__name__}")

    # If A records were resolved, try to infer hosting from IPs / CNAME
    # when the www CNAME lookup didn't yield a result.
    if result["hosting_provider"] == "Unknown" and result["a_records"]:
        result["hosting_provider"] = _infer_hosting_from_context(result)

    # Aggregate all detected technologies into a single list
    result["technologies_detected"] = _aggregate_technologies(result)

    # Set top-level error only if every single lookup failed
    if _dns_errors and len(_dns_errors) == 6:
        result["error"] = "; ".join(_dns_errors)
    elif _dns_errors:
        # Partial failures are informational, not blocking
        result["error"] = None

    return result


# ---------------------------------------------------------------------------
# Technology aggregation
# ---------------------------------------------------------------------------

def _infer_hosting_from_context(result: dict[str, Any]) -> str:
    """Best-effort hosting inference from A-record IPs and other signals."""
    # Fall back to checking SPF includes for well-known providers
    for include in result.get("spf_includes", []):
        include_lower = include.lower()
        for sig, name in HOSTING_SIGNATURES:
            if sig in include_lower:
                return name
    return "Unknown"


def _aggregate_technologies(result: dict[str, Any]) -> list[str]:
    """Compile a de-duplicated, sorted list of all technologies detected."""
    techs: set[str] = set()

    if result["mail_provider"] != "Unknown":
        techs.add(result["mail_provider"])
    if result["dns_provider"] != "Unknown":
        techs.add(result["dns_provider"])
    if result["cdn"] != "Unknown":
        techs.add(result["cdn"])
    if result["hosting_provider"] != "Unknown":
        techs.add(result["hosting_provider"])
    if result["dmarc_policy"] != "not_set":
        techs.add("DMARC")
    if result["spf_includes"]:
        techs.add("SPF")

    # Derive service names from SPF includes
    for include in result["spf_includes"]:
        include_lower = include.lower()
        if "google" in include_lower:
            techs.add("Google Workspace")
        elif "outlook" in include_lower or "microsoft" in include_lower:
            techs.add("Microsoft 365")
        elif "sendgrid" in include_lower:
            techs.add("SendGrid")
        elif "mailchimp" in include_lower or "mandrillapp" in include_lower:
            techs.add("Mailchimp")
        elif "amazonses" in include_lower:
            techs.add("Amazon SES")
        elif "zendesk" in include_lower:
            techs.add("Zendesk")
        elif "salesforce" in include_lower:
            techs.add("Salesforce")
        elif "hubspot" in include_lower:
            techs.add("HubSpot")
        elif "freshdesk" in include_lower:
            techs.add("Freshdesk")
        elif "mimecast" in include_lower:
            techs.add("Mimecast")

    # Derive from verification tokens
    for token in result["verification_tokens"]:
        techs.add(token["service"])

    return sorted(techs)
