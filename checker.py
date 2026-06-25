"""
checker.py
Checks whether generated domain variants are actually registered/live,
and pulls basic WHOIS info to help assess risk.
"""

import socket
import concurrent.futures
from datetime import datetime, timezone

try:
    import whois
except ImportError:
    whois = None


def is_domain_live(domain: str, timeout: float = 2.0) -> bool:
    try:
        socket.setdefaulttimeout(timeout)
        socket.gethostbyname(domain)
        return True
    except (socket.gaierror, socket.timeout, UnicodeError, OSError):
        return False


def get_whois_info(domain: str) -> dict:
    info = {"registrar": None, "creation_date": None, "age_days": None}
    if whois is None:
        info["error"] = "python-whois not installed."
        return info

    try:
        w = whois.whois(domain)
        creation = w.creation_date
        if isinstance(creation, list):
            creation = creation[0]

        info["registrar"] = w.registrar
        if creation:
            info["creation_date"] = str(creation)
            now = datetime.now(timezone.utc)
            if creation.tzinfo is None:
                creation = creation.replace(tzinfo=timezone.utc)
            info["age_days"] = (now - creation).days
    except (Exception, UnicodeError) as e:
        info["error"] = str(e)

    return info


def risk_score(live: bool, age_days) -> str:
    if not live:
        return "Not registered (low risk)"
    if age_days is not None and age_days < 90:
        return "HIGH RISK - registered, live, and very recently created"
    if age_days is not None and age_days < 365:
        return "MEDIUM RISK - registered, live, less than 1 year old"
    return "LOW-MEDIUM RISK - registered and live, but established"


def check_domain(domain: str) -> dict:
    live = is_domain_live(domain)
    whois_info = get_whois_info(domain) if live else {"registrar": None, "creation_date": None, "age_days": None}
    score = risk_score(live, whois_info.get("age_days"))

    return {
        "domain": domain,
        "live": live,
        "registrar": whois_info.get("registrar"),
        "creation_date": whois_info.get("creation_date"),
        "age_days": whois_info.get("age_days"),
        "risk": score,
    }


def check_domains_parallel(domains: list, max_workers: int = 10) -> list:
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(check_domain, d): d for d in domains}
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())
    return results


if __name__ == "__main__":
    test_domains = ["google.com", "thisdomaindoesnotexist12345.com"]
    for d in test_domains:
        print(check_domain(d))
