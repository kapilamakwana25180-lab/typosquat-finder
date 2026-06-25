"""
app.py
Flask web app for the Typosquatting Domain Finder.

Run with:
    python3 app.py

Then open http://127.0.0.1:5000 in your browser.
"""

from flask import Flask, render_template, request
from generator import generate_variants
from checker import check_domains_parallel
import re

app = Flask(__name__)

DOMAIN_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9\-\.]{1,253}\.[a-zA-Z]{2,}$")


@app.route("/", methods=["GET", "POST"])
def index():
    error = None
    results = None
    target_domain = None
    stats = None

    if request.method == "POST":
        target_domain = request.form.get("domain", "").strip().lower()

        if not target_domain or not DOMAIN_PATTERN.match(target_domain):
            error = "Please enter a valid domain, e.g. example.com"
        else:
            variants = generate_variants(target_domain)
            raw_results = check_domains_parallel(variants)
            # Sort: live (registered) domains first, riskiest first
            risk_order = {"HIGH": 0, "MEDIUM": 1, "LOW-MEDIUM": 2, "NOT": 3}

            def sort_key(r):
                tag = r["risk"].split()[0]
                return (not r["live"], risk_order.get(tag, 4), r["domain"])

            raw_results.sort(key=sort_key)
            results = raw_results

            live_count = sum(1 for r in results if r["live"])
            high_count = sum(1 for r in results if r["risk"].startswith("HIGH"))
            medium_count = sum(1 for r in results if r["risk"].startswith("MEDIUM"))
            established_count = sum(1 for r in results if r["risk"].startswith("LOW-MEDIUM"))
            unregistered_count = sum(1 for r in results if r["risk"].startswith("Not"))

            total = len(results) or 1  # avoid divide-by-zero
            stats = {
                "total": len(results),
                "live": live_count,
                "high_risk": high_count,
                "medium_risk": medium_count,
                "established": established_count,
                "unregistered": unregistered_count,
            }

    return render_template(
        "index.html",
        error=error,
        results=results,
        target_domain=target_domain,
        stats=stats,
    )


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    debug_mode = os.environ.get("FLASK_DEBUG", "true").lower() == "true"
    app.run(debug=debug_mode, host="0.0.0.0", port=port)
