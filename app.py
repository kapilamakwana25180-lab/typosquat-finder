"""
app.py
Flask web app for the Typosquatting Domain Finder.

Run with:
    python3 app.py

Then open http://127.0.0.1:5000 in your browser.
"""

from flask import Flask, render_template, request, redirect, url_for
from generator import generate_variants
from checker import check_domains_parallel
import re
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)

DOMAIN_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9\-\.]{1,253}\.[a-zA-Z]{2,}$")
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reviews.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            rating INTEGER NOT NULL,
            comment TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


init_db()


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
        active_page="scanner",
    )


@app.route("/reviews", methods=["GET", "POST"])
def reviews():
    error = None
    success = None

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        rating = request.form.get("rating", "").strip()
        comment = request.form.get("comment", "").strip()

        if not name or len(name) > 60:
            error = "Please enter your name (max 60 characters)."
        elif rating not in {"1", "2", "3", "4", "5"}:
            error = "Please select a star rating."
        elif not comment or len(comment) > 500:
            error = "Please enter a comment (max 500 characters)."
        else:
            conn = get_db()
            conn.execute(
                "INSERT INTO reviews (name, rating, comment, created_at) VALUES (?, ?, ?, ?)",
                (name, int(rating), comment, datetime.utcnow().strftime("%Y-%m-%d %H:%M")),
            )
            conn.commit()
            conn.close()
            return redirect(url_for("reviews", submitted="1"))

    conn = get_db()
    rows = conn.execute("SELECT * FROM reviews ORDER BY id DESC").fetchall()
    conn.close()

    all_reviews = [dict(r) for r in rows]
    avg_rating = round(sum(r["rating"] for r in all_reviews) / len(all_reviews), 1) if all_reviews else None

    if request.args.get("submitted") == "1":
        success = "Thanks! Your review has been posted below."

    return render_template(
        "reviews.html",
        reviews=all_reviews,
        avg_rating=avg_rating,
        error=error,
        success=success,
        active_page="reviews",
    )


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    debug_mode = os.environ.get("FLASK_DEBUG", "true").lower() == "true"
    app.run(debug=debug_mode, host="0.0.0.0", port=port)
