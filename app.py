"""
Shopper — AI Shopping Assistant
--------------------------------
Run:
    pip install flask
    # Optional live search + AI:
    # Set TAVILY_API_KEY and GROQ_API_KEY in your environment.
    python app.py

Open http://127.0.0.1:5000

IMPORTANT:
- Wallet funding is a local demo balance only. It does not charge a card or PayPal.
- Checkout creates a demo order record only. It does not purchase from a merchant.
- Add a real payment provider and verify payment server-side before accepting money.
"""

from flask import Flask, render_template_string, request, redirect, url_for, flash
import json
import os
import sqlite3
import urllib.error
import urllib.request

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
<title>Shopper — AI Shopping Assistant</title>
<style>
:root {
  --bg:#f4f8f3; --side:#dce8d8; --active:#c2d6bc; --card:#fff;
  --dark:#2d4a27; --green:#386641; --button:#285430;
  --alert:#eaf4e6; --border:#a3c293; --text:#2c352d; --muted:#556b53;
}
*{box-sizing:border-box}
body{margin:0;min-height:100vh;background:var(--bg);color:var(--text);
  font-family:system-ui,-apple-system,"Segoe UI",Roboto,Arial,sans-serif}
.app{display:flex;min-height:100vh}
.sidebar{width:90px;background:var(--side);padding:18px 10px;display:flex;
  flex-direction:column;align-items:center;gap:12px;flex-shrink:0}
.nav-item{width:70px;border:0;background:transparent;color:var(--muted);
  padding:10px 4px;border-radius:12px;cursor:pointer;font-size:11px}
.nav-item .ico{display:block;font-size:21px;margin-bottom:4px}
.nav-item.active{background:var(--active);color:var(--dark);font-weight:700}
.nav-bottom{margin-top:auto}
main{flex:1;max-width:1050px;margin:0 auto;padding:25px 22px 50px;width:100%}
.header{text-align:center;margin-bottom:20px}
.logo{font-size:29px}.header h1{margin:0;color:var(--green);font-size:27px}
.header p{margin:4px 0;color:var(--muted);font-size:13px}
.notice{background:var(--alert);border:1px solid var(--border);border-radius:14px;
  padding:13px 15px;margin-bottom:20px;font-size:13px}
.panel{display:none}.panel.active{display:block}
label{display:block;font-size:14px;font-weight:650;margin-bottom:8px}
input[type=text],input[type=number]{width:100%;padding:13px 14px;border:1px solid #c5d4bf;
  border-radius:12px;font-size:15px;background:white}
button.primary{width:100%;border:0;border-radius:14px;background:var(--button);
  color:white;padding:14px;font-size:15px;font-weight:700;cursor:pointer;margin-top:12px}
button.primary:hover{filter:brightness(.93)}
.card{background:white;border:1px solid #e4eadf;border-left:4px solid var(--green);
  border-radius:13px;padding:14px;margin:12px 0;display:flex;gap:12px;align-items:center}
.card img{width:64px;height:64px;object-fit:cover;border-radius:9px;background:#eee}
.card h3,.card h4{margin:0 0 5px;color:var(--dark);font-size:14px}
.card p{margin:0;color:var(--muted);font-size:12px}
.result{margin-top:18px;padding:16px;background:var(--alert);border:1px solid var(--border);
  border-radius:14px}
.output{white-space:pre-wrap;line-height:1.55;font-size:13px}
.subtabs{display:flex;gap:8px;margin:15px 0}
.subtabs button{flex:1;border:0;border-radius:9px;padding:10px;background:#e2ece0;
  color:var(--dark);font-weight:650;cursor:pointer}
.subtabs button.active{background:var(--green);color:white}
.subpane{display:none}.subpane.active{display:block}
.product-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:10px}
.product{align-items:flex-start}
a{color:var(--green);font-weight:650;text-decoration:none}
a:hover{text-decoration:underline}
.small-btn{display:inline-block;margin-top:8px;background:#285430;color:white;
  border:0;border-radius:7px;padding:7px 10px;font-size:12px;cursor:pointer}
.muted{color:var(--muted);font-size:13px}
.balance{font-size:24px;font-weight:750;color:var(--green);margin:8px 0 16px}
.flash{padding:11px 13px;border-radius:10px;background:#fff4d8;margin-bottom:12px;font-size:13px}
@media(max-width:600px){.sidebar{width:68px;padding:12px 5px}.nav-item{width:58px;font-size:10px}
  main{padding:18px 13px 35px}.header h1{font-size:24px}}
</style>
</head>
<body>
<div class="app">
<nav class="sidebar" aria-label="Main navigation">
  <button class="nav-item active" data-tab="search"><span class="ico">🛍️</span>Shopper</button>
  <button class="nav-item" data-tab="wallet"><span class="ico">💳</span>Wallet</button>
  <button class="nav-item" data-tab="recommend"><span class="ico">✨</span>Recomms</button>
  <button class="nav-item" data-tab="promos"><span class="ico">⚡</span>Promos</button>
  <button class="nav-item" data-tab="news"><span class="ico">📰</span>News</button>
  <button class="nav-item nav-bottom" data-tab="settings"><span class="ico">⚙️</span>Settings</button>
</nav>

<main>
<header class="header">
  <div class="logo">🛍️</div><h1>Shopper</h1>
  <p>Your Intelligent Shopping Assistant</p>
</header>

<div class="notice">💡 <strong>Shopper AI:</strong> Search products, compare available listings,
and review an AI-generated recommendation before deciding what to buy.</div>

{% with messages = get_flashed_messages() %}
  {% for message in messages %}<div class="flash">{{ message }}</div>{% endfor %}
{% endwith %}

<section id="search" class="panel active">
  <form method="post" action="{{ url_for('home') }}">
    <label for="query">What are you looking for today?</label>
    <input id="query" type="text" name="query"
      value="{{ query or 'power bank under 20000 Naira' }}" required maxlength="300">
    <button class="primary" type="submit">👜 Ask Shopper AI</button>
  </form>

  {% if result %}
  <div class="result">
    <h3>🤖 AI Product Evaluation</h3>
    <div class="output">{{ result }}</div>
    <div class="subtabs">
      <button class="active" data-subtab="recent">Recent (7 days)</button>
      <button data-subtab="older">Older (3 months)</button>
    </div>
    <div id="recent" class="subpane active">
      <p class="muted">Listings from the past 7 days:</p>
      {% if recent_results %}
      <div class="product-grid">
      {% for item in recent_results %}
        <article class="card product">
          {% if item.image_url %}<img src="{{ item.image_url }}" alt="Product image" loading="lazy">{% endif %}
          <div><h4>{{ item.title }}</h4>
            <p>{{ item.content[:180] if item.content else '' }}</p>
            {% if item.url %}<p><a href="{{ item.url }}" target="_blank" rel="noopener noreferrer">View store →</a></p>{% endif %}
            <form method="post" action="{{ url_for('checkout') }}">
              <input type="hidden" name="product_name" value="{{ item.title }}">
              <button class="small-btn" type="submit">Create demo order</button>
            </form>
          </div>
        </article>
      {% endfor %}
      </div>
      {% else %}<p class="muted">No recent listings found.</p>{% endif %}
    </div>
    <div id="older" class="subpane">
      <p class="muted">Listings from the past 3 months:</p>
      {% if older_results %}
      <div class="product-grid">
      {% for item in older_results %}
        <article class="card product">
          {% if item.image_url %}<img src="{{ item.image_url }}" alt="Product image" loading="lazy">{% endif %}
          <div><h4>{{ item.title }}</h4>
            <p>{{ item.content[:180] if item.content else '' }}</p>
            {% if item.url %}<p><a href="{{ item.url }}" target="_blank" rel="noopener noreferrer">View store →</a></p>{% endif %}
            <form method="post" action="{{ url_for('checkout') }}">
              <input type="hidden" name="product_name" value="{{ item.title }}">
              <button class="small-btn" type="submit">Create demo order</button>
            </form>
          </div>
        </article>
      {% endfor %}
      </div>
      {% else %}<p class="muted">No older listings found.</p>{% endif %}
    </div>
  </div>
  {% endif %}
  {% if checkout_msg %}<div class="result"><h3>Order status</h3><div class="output">{{ checkout_msg }}</div></div>{% endif %}
</section>

<section id="wallet" class="panel">
  <h3>💳 Account Wallet</h3>
  <div class="card" style="display:block">
    <h4>Demo balance</h4><div class="balance">₦{{ "%.2f"|format(balance) }}</div>
    <p class="muted">This is a local demonstration balance, not real money.</p>
    <form method="post" action="{{ url_for('fund') }}">
      <label for="amount">Add demo funds (₦)</label>
      <input id="amount" type="number" name="amount" min="1" max="100000000" step="0.01" required placeholder="Enter amount">
      <button class="primary" type="submit">Add demo funds</button>
    </form>
  </div>
</section>

<section id="recommend" class="panel">
  <h3>✨ Curated For You</h3>
  <div class="card"><div><h4>Poolee Energize20 (20,000mAh)</h4>
    <p><strong>₦18,000</strong> · 22.5W fast charging (sample recommendation; verify price and availability).</p></div></div>
</section>

<section id="promos" class="panel">
  <h3>⚡ Live Web Promos</h3>
  <div class="card"><div><h4>Promotions</h4>
    <p>Search results may contain current offers. Confirm terms and prices on the merchant's website.</p></div></div>
</section>

<section id="news" class="panel">
  <h3>📰 Shopping &amp; Tech News</h3>
  <div class="card"><div><h4>How to Spot Fake Power Banks</h4>
    <p>Check independent reviews, warranty details, seller reputation, and credible capacity testing.</p></div></div>
</section>

<section id="settings" class="panel">
  <h3>⚙️ App Settings</h3>
  <div class="card"><div><h4>API Configuration</h4>
    <p>Tavily search: {{ 'configured' if tavily_ready else 'not configured' }} ·
       Groq AI: {{ 'configured' if groq_ready else 'not configured' }}</p>
    <p class="muted">Set TAVILY_API_KEY and GROQ_API_KEY as environment variables, then restart the app.</p>
  </div></div>
  <p class="muted">Payment actions are demo-only. No PayPal transaction or merchant purchase is performed.</p>
</section>
</main>
</div>
<script>
document.querySelectorAll('.nav-item').forEach(button => {
  button.addEventListener('click', () => {
    document.querySelectorAll('.nav-item').forEach(x => x.classList.remove('active'));
    document.querySelectorAll('.panel').forEach(x => x.classList.remove('active'));
    button.classList.add('active');
    document.getElementById(button.dataset.tab).classList.add('active');
  });
});
document.querySelectorAll('[data-subtab]').forEach(button => {
  button.addEventListener('click', () => {
    document.querySelectorAll('[data-subtab]').forEach(x => x.classList.remove('active'));
    document.querySelectorAll('.subpane').forEach(x => x.classList.remove('active'));
    button.classList.add('active');
    document.getElementById(button.dataset.subtab).classList.add('active');
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
    request_headers = {"Content-Type": "application/json", "User-Agent": "ShopperApp/1.0"}
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
            "environment variables. Search listings may still appear if Tavily is configured."
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


@app.route("/", methods=["GET", "POST"])
def home():
    result = None
    query = ""
    recent_results = []
    older_results = []
    checkout_msg = None

    if request.method == "POST":
        query = request.form.get("query", "").strip()
        if not query:
            flash("Please enter a product to search for.")
        else:
            recent_results = search_tavily(query, time_range="week")
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

    return render_template_string(
        HTML,
        result=result,
        recent_results=recent_results,
        older_results=older_results,
        query=query,
        balance=get_balance(),
        checkout_msg=checkout_msg,
        tavily_ready=bool(TAVILY_API_KEY),
        groq_ready=bool(GROQ_API_KEY),
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
