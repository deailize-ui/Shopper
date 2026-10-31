"""
SHOPPER — AI Shopping Assistant
Single-file Flask application combining the supplied Shopper Green frontend design
with the supplied Flask/SQLite/Tavily/Groq backend.

Install:
    pip install flask
Optional environment variables:
    FLASK_SECRET_KEY
    SHOPPER_DB_PATH
    TAVILY_API_KEY
    GROQ_API_KEY

Run:
    python app.py

Open:
    http://127.0.0.1:5000

Important:
- Wallet funding is a local demo balance only; it does not charge a card or PayPal.
- Checkout creates a demo order record only; it does not purchase from a merchant.
- Configure a real payment provider and verify payments server-side before accepting money.
"""

from flask import Flask, render_template_string, request, redirect, url_for, flash
import json
import os
import sqlite3
import urllib.error
import urllib.request
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "change-this-development-secret")

DB_PATH = os.environ.get("SHOPPER_DB_PATH", "shopper.db")
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "").strip()
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "").strip()

HTML = r"""
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Shopper — Your AI Shopping Assistant</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600;9..144,700&family=Manrope:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
:root{
 --bg:#f4f8f3;--forest:#2d4a27;--green:#386641;--primary:#386641;
 --coffee:#896b4b;--card:#fff;--ink:#263428;--muted:#758273;
 --line:#e4eadf;--soft:#e8f0e5;--shadow:0 12px 34px rgba(45,74,39,.08);
 --lift:0 16px 38px rgba(45,74,39,.14);
}
*{box-sizing:border-box}
body{margin:0;min-height:100vh;background:var(--bg);color:var(--ink);font-family:Manrope,system-ui,sans-serif}
button,input{font:inherit}
.app{min-height:100vh}
.sidebar{position:fixed;inset:0 auto 0 0;z-index:10;width:80px;background:var(--forest);display:flex;flex-direction:column;align-items:center;gap:9px;padding:20px 10px}
.brand-mark{width:42px;height:42px;border-radius:15px;background:#d8e6d2;color:var(--forest);display:grid;place-items:center;font-size:22px;margin-bottom:18px}
.nav-item{position:relative;width:48px;height:48px;border:0;border-radius:14px;background:transparent;color:rgba(255,255,255,.67);cursor:pointer;display:grid;place-items:center;transition:.2s}
.nav-item:hover{background:rgba(255,255,255,.12);color:white;transform:translateY(-1px)}
.nav-item.active{background:#d5e5cf;color:var(--forest);box-shadow:0 8px 20px rgba(0,0,0,.12)}
.nav-item .ico{font-size:20px;line-height:1}
.nav-item .tip{position:absolute;left:58px;top:50%;transform:translateY(-50%);background:#243d20;color:#fff;padding:7px 10px;border-radius:8px;font-size:11px;white-space:nowrap;opacity:0;pointer-events:none;transition:.15s}
.nav-item:hover .tip{opacity:1}
.nav-bottom{margin-top:auto}
main{margin-left:80px;padding:42px 6vw 64px;min-height:100vh}
.main-inner{max-width:1050px;margin:0 auto}
.panel{display:none;animation:fade .25s ease}.panel.active{display:block}
@keyframes fade{from{opacity:0;transform:translateY(7px)}to{opacity:1;transform:none}}
.hero{padding:30px 0 12px;max-width:790px}
.eyebrow{margin:0 0 10px;color:var(--coffee);font-size:12px;font-weight:800;letter-spacing:.17em;text-transform:uppercase}
h1,h2,h3,h4,p{margin-top:0}
h1{font:600 clamp(35px,5vw,60px)/1.12 Fraunces,Georgia,serif;color:var(--forest);letter-spacing:-.035em;margin-bottom:12px}
h2{font:600 30px Fraunces,Georgia,serif;color:var(--forest);margin-bottom:8px}
h3{font-size:17px;color:var(--forest);margin-bottom:14px}
.subtitle{font-size:14px;color:var(--muted);line-height:1.7}
.search-form{margin-top:28px;display:flex;align-items:center;gap:9px;background:white;padding:9px;border-radius:18px;box-shadow:var(--shadow);border:1px solid rgba(45,74,39,.04);transition:.2s}
.search-form:focus-within{box-shadow:var(--lift)}
.search-form input{flex:1;min-width:0;border:0;outline:0;background:transparent;padding:13px 12px;color:var(--ink);font-size:15px}
.search-form input::placeholder{color:#9ba698}
.primary{border:0;border-radius:13px;background:var(--green);color:white;padding:13px 19px;font-size:13px;font-weight:800;cursor:pointer;transition:.2s}
.primary:hover{background:var(--forest);transform:translateY(-1px)}
.notice{margin:20px 0;padding:13px 16px;border:1px solid #d8e5d2;background:#edf4e9;border-radius:13px;color:#496147;font-size:12px;line-height:1.6}
.result{margin-top:25px;background:#fff;border:1px solid var(--line);border-radius:20px;padding:22px;box-shadow:var(--shadow)}
.output{white-space:pre-wrap;line-height:1.75;font-size:13px;color:#4d5c4d}
.subtabs{display:flex;gap:8px;margin:20px 0 14px;border-bottom:1px solid var(--line);padding-bottom:10px}
.subtabs button{border:0;border-radius:10px;padding:9px 14px;background:transparent;color:var(--muted);font-size:12px;font-weight:800;cursor:pointer}
.subtabs button.active{background:var(--soft);color:var(--forest)}
.subpane{display:none}.subpane.active{display:block}
.product-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(235px,1fr));gap:13px}
.product-card,.card{background:#fff;border:1px solid var(--line);border-radius:17px;padding:16px;box-shadow:0 7px 22px rgba(45,74,39,.045)}
.product-card{display:flex;gap:13px;align-items:flex-start}
.product-card img{width:76px;height:76px;object-fit:cover;border-radius:12px;background:#edf1eb}
.product-card h4,.card h4{margin:0 0 7px;font-size:14px;color:var(--forest)}
.product-card p,.card p{font-size:12px;color:var(--muted);line-height:1.6;margin:0 0 7px}
a{color:var(--green);font-weight:800;text-decoration:none}a:hover{text-decoration:underline}
.small-btn{border:0;border-radius:9px;background:var(--forest);color:#fff;padding:8px 11px;font-size:11px;font-weight:800;cursor:pointer;margin-top:7px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:15px;margin-top:20px}
.card{padding:20px}
.card .symbol{font-size:25px;margin-bottom:12px}
.balance{font:600 36px Fraunces,Georgia,serif;color:var(--green);margin:12px 0}
label{display:block;font-size:12px;font-weight:800;color:var(--forest);margin:15px 0 8px}
input[type=number]{width:100%;border:1px solid #d7e1d2;background:white;border-radius:11px;padding:13px;outline:0}
input:focus{border-color:var(--green)}
.flash{padding:12px 15px;border-radius:12px;background:#fff2d7;color:#76541c;font-size:12px;margin:0 0 14px}
.empty{padding:28px;text-align:center;border:1px dashed #cbd9c5;border-radius:16px;color:var(--muted);font-size:13px;background:rgba(255,255,255,.45)}
.setting-row{display:flex;justify-content:space-between;gap:20px;padding:13px 0;border-bottom:1px solid var(--line);font-size:13px}
.status{font-size:11px;border-radius:99px;background:#edf4e9;color:var(--green);padding:5px 9px;font-weight:800}
@media(max-width:650px){
 .sidebar{width:64px;padding:15px 7px;gap:7px}.brand-mark{width:39px;height:39px}
 .nav-item{width:46px;height:46px}main{margin-left:64px;padding:25px 17px 45px}
 .search-form{align-items:stretch;flex-wrap:wrap}.search-form input{flex-basis:100%;padding:10px}
 .search-form .primary{width:100%}.result{padding:16px}.product-card{padding:12px}
}
</style>
</head>
<body>
<div class="app">
<nav class="sidebar" aria-label="Main navigation">
 <div class="brand-mark">🍃</div>
 <button class="nav-item active" data-tab="search" aria-label="Shopper"><span class="ico">🛍</span><span class="tip">Shopper</span></button>
 <button class="nav-item" data-tab="wallet" aria-label="Wallet"><span class="ico">▣</span><span class="tip">Wallet</span></button>
 <button class="nav-item" data-tab="recommend" aria-label="Recommendations"><span class="ico">✦</span><span class="tip">Recommendations</span></button>
 <button class="nav-item" data-tab="promos" aria-label="Promos"><span class="ico">⚡</span><span class="tip">Promos</span></button>
 <button class="nav-item" data-tab="news" aria-label="News"><span class="ico">▤</span><span class="tip">News</span></button>
 <button class="nav-item nav-bottom" data-tab="settings" aria-label="Settings"><span class="ico">⚙</span><span class="tip">Settings</span></button>
</nav>
<main><div class="main-inner">
{% with messages = get_flashed_messages() %}
 {% for message in messages %}<div class="flash">{{ message }}</div>{% endfor %}
{% endwith %}

<section id="search" class="panel active">
 <div class="hero">
  <p class="eyebrow">{{ greeting }}</p>
  <h1>What are we shopping for today?</h1>
  <p class="subtitle">Tell Shopper what you need. We'll search available listings, compare the evidence and help you make a smarter choice.</p>
  <form class="search-form" method="post" action="{{ url_for('home') }}">
   <input type="text" name="query" value="{{ query }}" placeholder="Try “power bank under ₦20,000”" maxlength="300" required aria-label="Product search">
   <button class="primary" type="submit">✦ <span>Ask Shopper</span></button>
  </form>
 </div>
 <div class="notice">🌿 <strong>Shopper AI</strong> · Search product listings and review an AI-generated evaluation before deciding what to buy. Always verify price, stock and seller details with the store.</div>
 {% if result %}
 <div class="result">
  <h3>✦ Shopper's evaluation</h3>
  <div class="output">{{ result }}</div>
  <div class="subtabs">
   <button type="button" class="active" data-subtab="recent">Recents · Past 7 days</button>
   <button type="button" data-subtab="older">Older · Past 3 months</button>
  </div>
  <div id="recent" class="subpane active">
   {% if recent_results %}<div class="product-grid">
   {% for item in recent_results %}
    <article class="product-card">
     {% if item.image_url %}<img src="{{ item.image_url }}" alt="Product image" loading="lazy">{% endif %}
     <div><h4>{{ item.title }}</h4><p>{{ item.content[:180] if item.content else '' }}</p>
      {% if item.url %}<p><a href="{{ item.url }}" target="_blank" rel="noopener noreferrer">View store ↗</a></p>{% endif %}
      <form method="post" action="{{ url_for('checkout') }}"><input type="hidden" name="product_name" value="{{ item.title }}"><button class="small-btn" type="submit">Create demo order</button></form>
     </div>
    </article>
   {% endfor %}</div>{% else %}<div class="empty">No recent listings were returned. Check your search connection or try another query.</div>{% endif %}
  </div>
  <div id="older" class="subpane">
   {% if older_results %}<div class="product-grid">
   {% for item in older_results %}
    <article class="product-card">
     {% if item.image_url %}<img src="{{ item.image_url }}" alt="Product image" loading="lazy">{% endif %}
     <div><h4>{{ item.title }}</h4><p>{{ item.content[:180] if item.content else '' }}</p>
      {% if item.url %}<p><a href="{{ item.url }}" target="_blank" rel="noopener noreferrer">View store ↗</a></p>{% endif %}
      <form method="post" action="{{ url_for('checkout') }}"><input type="hidden" name="product_name" value="{{ item.title }}"><button class="small-btn" type="submit">Create demo order</button></form>
     </div>
    </article>
   {% endfor %}</div>{% else %}<div class="empty">No older listings were returned.</div>{% endif %}
  </div>
 </div>
 {% else %}
 <div class="cards">
  <div class="card"><div class="symbol">⌕</div><h4>Search what you need</h4><p>Describe a product, preferred features or your budget in natural language.</p></div>
  <div class="card"><div class="symbol">◈</div><h4>Compare the evidence</h4><p>Shopper reviews available search results and highlights missing information.</p></div>
  <div class="card"><div class="symbol">✓</div><h4>Choose with confidence</h4><p>Open the merchant listing to verify current prices, availability and terms.</p></div>
 </div>
 {% endif %}
</section>

<section id="wallet" class="panel">
 <p class="eyebrow">Your account</p><h2>Wallet</h2><p class="subtitle">Manage your Shopper demo balance.</p>
 <div class="cards">
  <div class="card"><div class="symbol">▣</div><p>Available demo balance</p><div class="balance">₦{{ "%.2f"|format(balance) }}</div><span class="status">Local demo only</span></div>
  <div class="card"><h3>Add funds</h3><p>This form updates a local demonstration balance. It does not charge a card, bank account or PayPal.</p>
   <form method="post" action="{{ url_for('fund') }}"><label for="amount">Amount in naira (₦)</label><input id="amount" type="number" name="amount" min="1" max="100000000" step="0.01" required placeholder="Enter amount"><button class="primary" type="submit" style="width:100%;margin-top:13px">Add demo funds</button></form>
  </div>
 </div>
</section>

<section id="recommend" class="panel">
 <p class="eyebrow">Picked for your needs</p><h2>Recommendations</h2><p class="subtitle">Recommendations will be based on your searches as product data becomes available.</p>
 <div class="empty">No personalized recommendations yet. Search for a product to get started.</div>
</section>

<section id="promos" class="panel">
 <p class="eyebrow">Offers and savings</p><h2>Promos</h2><p class="subtitle">Discover possible deals in product search results.</p>
 <div class="empty">Search results may include offers. Confirm promotion dates, eligibility and final prices on the merchant's website.</div>
</section>

<section id="news" class="panel">
 <p class="eyebrow">Shopping insights</p><h2>News</h2>
 <div class="cards"><div class="card"><div class="symbol">◉</div><h4>How to spot fake power banks</h4><p>Check independent reviews, warranty details, seller reputation and credible capacity testing before buying.</p></div></div>
</section>

<section id="settings" class="panel">
 <p class="eyebrow">Preferences and connections</p><h2>Settings</h2><p class="subtitle">Check the service connections used by Shopper.</p>
 <div class="card">
  <div class="setting-row"><span>Tavily product search</span><span class="status">{{ 'Connected' if tavily_ready else 'Not configured' }}</span></div>
  <div class="setting-row"><span>Groq AI evaluation</span><span class="status">{{ 'Connected' if groq_ready else 'Not configured' }}</span></div>
  <p style="margin-top:15px">Set <code>TAVILY_API_KEY</code> and <code>GROQ_API_KEY</code> as environment variables, then restart the app.</p>
  <p>Payment actions are currently demo-only. No PayPal transaction or merchant purchase is performed.</p>
 </div>
</section>
</div></main>
</div>
<script>
document.querySelectorAll('.nav-item').forEach(button => {
 button.addEventListener('click', () => {
  document.querySelectorAll('.nav-item').forEach(x => x.classList.remove('active'));
  document.querySelectorAll('.panel').forEach(x => x.classList.remove('active'));
  button.classList.add('active');
  const panel = document.getElementById(button.dataset.tab);
  if (panel) panel.classList.add('active');
 });
});
document.querySelectorAll('[data-subtab]').forEach(button => {
 button.addEventListener('click', () => {
  document.querySelectorAll('[data-subtab]').forEach(x => x.classList.remove('active'));
  document.querySelectorAll('.subpane').forEach(x => x.classList.remove('active'));
  button.classList.add('active');
  const pane = document.getElementById(button.dataset.subtab);
  if (pane) pane.classList.add('active');
 });
});
</script>
</body>
</html>
"""


def db_connect():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with db_connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS wallets (
                user_id TEXT PRIMARY KEY,
                balance REAL NOT NULL DEFAULT 0
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                order_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                product_name TEXT NOT NULL,
                status TEXT NOT NULL,
                details TEXT
            )
        """)
        conn.execute(
            "INSERT OR IGNORE INTO wallets (user_id, balance) VALUES (?, ?)",
            ("default_user", 0.0),
        )


def post_json(url, payload, headers=None, timeout=25):
    data = json.dumps(payload).encode("utf-8")
    request_headers = {
        "Content-Type": "application/json",
        "User-Agent": "ShopperApp/1.0",
    }
    if headers:
        request_headers.update(headers)
    req = urllib.request.Request(url, data=data, headers=request_headers, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def search_tavily(query, time_range="week"):
    if not TAVILY_API_KEY:
        return []
    try:
        data = post_json(
            "https://api.tavily.com/search",
            {
                "api_key": TAVILY_API_KEY,
                "query": query,
                "max_results": 5,
                "include_images": True,
                "time_range": time_range,
            },
        )
        results = data.get("results", [])
        images = data.get("images", []) or []
        for index, item in enumerate(results):
            item["image_url"] = images[index] if index < len(images) else ""
        return results
    except (urllib.error.URLError, TimeoutError, ValueError, KeyError) as exc:
        app.logger.warning("Tavily search failed: %s", exc)
        return []


def ask_groq(prompt):
    if not GROQ_API_KEY:
        return (
            "AI recommendations are not configured yet. Add GROQ_API_KEY to your "
            "environment variables. Product listings may still appear if Tavily is configured."
        )
    try:
        data = post_json(
            "https://api.groq.com/openai/v1/chat/completions",
            {
                "model": "openai/gpt-oss-20b",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
            },
            headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
        )
        return data["choices"][0]["message"]["content"]
    except (urllib.error.URLError, TimeoutError, ValueError, KeyError, IndexError) as exc:
        app.logger.warning("Groq request failed: %s", exc)
        return "The AI request could not be completed. Check your API key and connection."


def get_balance(user_id="default_user"):
    with db_connect() as conn:
        row = conn.execute(
            "SELECT balance FROM wallets WHERE user_id = ?", (user_id,)
        ).fetchone()
        return float(row["balance"]) if row else 0.0


def greeting_for_now():
    hour = datetime.now().hour
    if hour < 12:
        return "Good morning"
    if hour < 17:
        return "Good afternoon"
    return "Good evening"


@app.route("/", methods=["GET", "POST"])
def home():
    result = None
    query = ""
    recent_results = []
    older_results = []

    if request.method == "POST":
        query = request.form.get("query", "").strip()[:300]
        if not query:
            flash("Please enter a product to search for.")
        else:
            recent_results = search_tavily(query, time_range="week")
            # Tavily supports month; the UI describes the broader archive as three months.
            older_results = search_tavily(query, time_range="month")
            context = "\n\n".join(
                f"Title: {item.get('title', '')}\n"
                f"Link: {item.get('url', '')}\n"
                f"Content: {item.get('content', '')}"
                for item in recent_results
            )
            prompt = (
                f"The shopper is looking for: {query}\n\n"
                f"Search results:\n{context or 'No web results were returned.'}\n\n"
                "Compare the available evidence, identify the strongest option, "
                "mention any price only if the results provide one, and point out "
                "missing information. Keep the response under 120 words."
            )
            result = ask_groq(prompt)
            if not TAVILY_API_KEY:
                flash("Tavily is not configured. Add TAVILY_API_KEY to enable live product search.")
    return render_template_string(
        HTML,
        result=result,
        recent_results=recent_results,
        older_results=older_results,
        query=query,
        balance=get_balance(),
        tavily_ready=bool(TAVILY_API_KEY),
        groq_ready=bool(GROQ_API_KEY),
        greeting=greeting_for_now(),
    )


@app.route("/fund", methods=["POST"])
def fund():
    try:
        amount = float(request.form.get("amount", "0"))
    except (TypeError, ValueError):
        amount = 0

    if amount <= 0 or amount > 100_000_000:
        flash("Enter a valid demo amount.")
    else:
        with db_connect() as conn:
            conn.execute(
                "UPDATE wallets SET balance = balance + ? WHERE user_id = ?",
                (amount, "default_user"),
            )
        flash(f"Added ₦{amount:,.2f} to your demo wallet. No real payment was made.")
    return redirect(url_for("home"))


@app.route("/checkout", methods=["POST"])
def checkout():
    product_name = request.form.get("product_name", "").strip()[:250]
    if not product_name:
        flash("Product name is missing.")
    else:
        with db_connect() as conn:
            cursor = conn.execute(
                """INSERT INTO orders (user_id, product_name, status, details)
                   VALUES (?, ?, ?, ?)""",
                (
                    "default_user",
                    product_name,
                    "demo_order_created",
                    "Demo only: no payment and no merchant purchase occurred.",
                ),
            )
            order_id = cursor.lastrowid
        flash(
            f"Demo order #{order_id} created for “{product_name}”. "
            "No payment was taken and no merchant purchase was made."
        )
    return redirect(url_for("home"))


@app.route("/health")
def health():
    return {"status": "ok"}


init_db()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=False)
