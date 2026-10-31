from flask import Flask, render_template_string, request
import urllib.request
import json
import os
import sqlite3

app = Flask(__name__)

TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

# Initialize SQLite Database with safe connection context management
def init_db():
    with sqlite3.connect('shopper.db', timeout=10.0) as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS wallets (user_id TEXT PRIMARY KEY, balance REAL)''')
        c.execute('''CREATE TABLE IF NOT EXISTS orders (order_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, product_name TEXT, status TEXT, details TEXT)''')
        conn.commit()

init_db()

def search_tavily(query, time_range="w"):
    url = "https://api.tavily.com/search"
    payload = {
        "api_key": TAVILY_API_KEY.strip(), 
        "query": query, 
        "max_results": 3, 
        "include_images": True,
        "time_range": time_range
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req) as response:
            res = json.loads(response.read().decode())
            results = res.get("results", [])
            images = res.get("images", [])
            for i, r in enumerate(results):
                if i < len(images):
                    r['image_url'] = images[i]
                else:
                    r['image_url'] = ""
            return results
    except Exception as e:
        print(f"Tavily Error: {e}")
        return []

def ask_groq(prompt):
    url = "https://api.groq.com/openai/v1/chat/completions"
    payload = {
        "model": "openai/gpt-oss-20b",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, 
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {GROQ_API_KEY.strip()}",
            "User-Agent": "Mozilla/5.0"
        }
    )
    try:
        with urllib.request.urlopen(req) as response:
            res_data = json.loads(response.read().decode())
            return res_data["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"Groq Debug Error: {e}")
        return f"AI request failed: {e}"

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Shopper — AI Autonomous Shopping Agent</title>
    <style>
        :root {
            --bg-body: #F4F8F3;
            --sidebar-bg: #DCE8D8;
            --sidebar-active: #C2D6BC;
            --card-bg: #FFFFFF;
            --green-dark: #2D4A27;
            --green-primary: #386641;
            --green-button: #285430;
            --alert-bg: #EAF4E6;
            --alert-border: #A3C293;
            --text-main: #2C352D;
            --text-muted: #556B53;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background: var(--bg-body);
            margin: 0;
            padding: 0;
            color: var(--text-main);
            display: flex;
            height: 100vh;
            overflow: hidden;
        }

        .sidebar {
            width: 82px;
            background: var(--sidebar-bg);
            display: flex;
            flex-direction: column;
            align-items: center;
            padding-top: 24px;
            padding-bottom: 24px;
            gap: 22px;
            flex-shrink: 0;
            border-right: 1px solid rgba(0, 0, 0, 0.04);
        }

        .nav-item {
            background: none;
            border: none;
            cursor: pointer;
            color: var(--text-muted);
            font-size: 11px;
            font-weight: 500;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 5px;
            padding: 8px 4px;
            border-radius: 12px;
            width: 66px;
            text-align: center;
            transition: all 0.2s ease;
        }

        .nav-item.active {
            background: var(--sidebar-active);
            color: var(--green-dark);
            font-weight: 600;
        }

        .nav-item span.icon {
            font-size: 20px;
            line-height: 1;
        }

        .main-content {
            flex: 1;
            padding: 24px 20px;
            overflow-y: auto;
            box-sizing: border-box;
            background: var(--bg-body);
        }

        .header {
            text-align: center;
            margin-bottom: 20px;
        }

        .logo-bags {
            font-size: 28px;
            margin-bottom: 2px;
        }

        .header h1 {
            color: var(--green-primary);
            margin: 0 0 4px 0;
            font-size: 26px;
            font-weight: 700;
            letter-spacing: -0.5px;
        }

        .header p {
            color: var(--text-muted);
            font-size: 12px;
            margin: 0;
            font-weight: 400;
        }

        .ai-notification {
            background: var(--alert-bg);
            border: 1.5px solid var(--alert-border);
            padding: 12px 14px;
            border-radius: 14px;
            margin-bottom: 22px;
            font-size: 12px;
            display: flex;
            align-items: flex-start;
            gap: 10px;
            line-height: 1.4;
            color: #2F3E2E;
        }

        .ai-notification span {
            font-size: 16px;
            flex-shrink: 0;
        }

        .form-group {
            margin-bottom: 16px;
        }

        label {
            display: block;
            font-weight: 600;
            margin-bottom: 8px;
            font-size: 13.5px;
            color: var(--text-main);
        }

        input[type="text"], input[type="number"] {
            width: 100%;
            padding: 14px 16px;
            border: 1.5px solid #C5D4BF;
            border-radius: 14px;
            box-sizing: border-box;
            font-size: 13.5px;
            outline: none;
            background: #FFFFFF;
            color: #333;
            box-shadow: inset 0 1px 3px rgba(0,0,0,0.02);
        }

        input[type="text"]:focus, input[type="number"]:focus {
            border-color: var(--green-primary);
        }

        button.bag-btn {
            background: var(--green-button);
            color: white;
            border: none;
            padding: 16px;
            width: 100%;
            border-radius: 20px;
            font-size: 15px;
            font-weight: 600;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
            box-shadow: 0 4px 14px rgba(40, 84, 48, 0.25);
            margin-top: 12px;
            transition: background 0.2s;
        }

        button.bag-btn:hover {
            background: #1f4226;
        }

        .tab-pane {
            display: none;
        }

        .tab-pane.active {
            display: block;
        }

        .sub-tabs {
            display: flex;
            gap: 10px;
            margin-bottom: 16px;
        }

        .sub-tab-btn {
            flex: 1;
            padding: 10px;
            background: #E2ECE0;
            border: none;
            border-radius: 10px;
            font-weight: 600;
            font-size: 12.5px;
            cursor: pointer;
            color: var(--green-dark);
        }

        .sub-tab-btn.active {
            background: var(--green-primary);
            color: white;
        }

        .sub-pane {
            display: none;
        }

        .sub-pane.active {
            display: block;
        }

        .result-card {
            margin-top: 20px;
            background: var(--alert-bg);
            padding: 16px;
            border-radius: 14px;
            border: 1.5px solid var(--alert-border);
        }

        .result-card h3 {
            margin-top: 0;
            color: var(--green-dark);
            font-size: 14px;
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .ai-output {
            white-space: pre-wrap;
            line-height: 1.5;
            font-size: 12.5px;
            color: #2F3E2E;
            margin-bottom: 14px;
        }

        .product-grid {
            display: grid;
            grid-template-columns: 1fr;
            gap: 12px;
            margin-top: 12px;
        }

        .card-item {
            background: #FFFFFF;
            padding: 12px;
            border-radius: 12px;
            border-left: 4px solid var(--green-primary);
            box-shadow: 0 2px 6px rgba(0,0,0,0.02);
            display: flex;
            gap: 12px;
            align-items: center;
        }

        .card-item img {
            width: 60px;
            height: 60px;
            object-fit: cover;
            border-radius: 8px;
            background: #eee;
            flex-shrink: 0;
        }

        .card-item h4 {
            margin: 0 0 4px 0;
            color: var(--green-dark);
            font-size: 13px;
        }

        .card-item p {
            margin: 0;
            font-size: 11px;
            color: var(--text-muted);
        }

        .paypal-btn {
            display: inline-block;
            background: #0070BA;
            color: white;
            padding: 6px 12px;
            border-radius: 6px;
            font-size: 11px;
            font-weight: 600;
            text-decoration: none;
            margin-top: 6px;
        }
        .paypal-btn:hover {
            background: #005ea6;
        }
    </style>
</head>
<body>
    <div class="sidebar">
        <button class="nav-item active" onclick="switchTab(event, 'searchTab')">
            <span class="icon">🛍️</span>
            Shopper
        </button>
        <button class="nav-item" onclick="switchTab(event, 'walletTab')">
            <span class="icon">💳</span>
            Wallet
        </button>
        <button class="nav-item" onclick="switchTab(event, 'recommendTab')">
            <span class="icon">✨</span>
            Recomms
        </button>
        <button class="nav-item" onclick="switchTab(event, 'promosTab')">
            <span class="icon">⚡</span>
            Promos
        </button>
        <button class="nav-item" onclick="switchTab(event, 'newsTab')">
            <span class="icon">📰</span>
            News
        </button>
        <button class="nav-item" onclick="switchTab(event, 'settingsTab')" style="margin-top: auto;">
            <span class="icon">⚙️</span>
            Settings
        </button>
    </div>

    <div class="main-content">
        <div class="header">
            <div class="logo-bags">🛍️</div>
            <h1>Shopper</h1>
            <p>Your Intelligent Autonomous Shopping Assistant</p>
        </div>

        <div class="ai-notification">
            <span>💡</span>
            <div>
                <strong>Shopper AI Alert:</strong> Prices for top requested items dropped by ~5% today. Best time to buy!
            </div>
        </div>

        <div id="searchTab" class="tab-pane active">
            <form method="POST">
                <div class="form-group">
                    <label for="query">What are you looking for today?</label>
                    <input type="text" id="query" name="query" value="{{ query if query else 'power bank under 20000 Naira' }}" required>
                </div>
                <button type="submit" class="bag-btn">
                    <span>👜</span> Ask Shopper AI
                </button>
            </form>

            {% if result %}
                <div class="result-card">
                    <h3>🤖 AI Product Evaluation</h3>
                    <div class="ai-output">{{ result }}</div>

                    <div class="sub-tabs">
                        <button class="sub-tab-btn active" onclick="switchSubTab(event, 'recentsPane')">⏳ Recents (Past Week)</button>
                        <button class="sub-tab-btn" onclick="switchSubTab(event, 'olderPane')">📦 Older (Past 3 Months)</button>
                    </div>

                    <div id="recentsPane" class="sub-pane active">
                        <p style="font-size: 11.5px; color: var(--text-muted); margin-top:0;">Deals from the past 7 days:</p>
                        {% if recent_results %}
                            <div class="product-grid">
                                {% for r in recent_results %}
                                    <div class="card-item">
                                        {% if r.get('image_url') %}<img src="{{ r.get('image_url') }}" alt="Product">{% endif %}
                                        <div>
                                            <h4>{{ r.get('title') }}</h4>
                                            <p><a href="{{ r.get('url') }}" target="_blank" style="color: var(--green-primary); text-decoration: none;">View Store →</a></p>
                                            <form action="/checkout" method="POST" style="margin-top:4px;">
                                                <input type="hidden" name="product_name" value="{{ r.get('title') }}">
                                                <button type="submit" class="paypal-btn" style="border:none; cursor:pointer;">Checkout with PayPal</button>
                                            </form>
                                        </div>
                                    </div>
                                {% endfor %}
                            </div>
                        {% else %}
                            <p style="font-size: 12px;">No recent listings found.</p>
                        {% endif %}
                    </div>

                    <div id="olderPane" class="sub-pane">
                        <p style="font-size: 11.5px; color: var(--text-muted); margin-top:0;">Listings from the past 3 months:</p>
                        {% if older_results %}
                            <div class="product-grid">
                                {% for r in older_results %}
                                    <div class="card-item">
                                        {% if r.get('image_url') %}<img src="{{ r.get('image_url') }}" alt="Product">{% endif %}
                                        <div>
                                            <h4>{{ r.get('title') }}</h4>
                                            <p><a href="{{ r.get('url') }}" target="_blank" style="color: var(--green-primary); text-decoration: none;">View Store →</a></p>
                                            <form action="/checkout" method="POST" style="margin-top:4px;">
                                                <input type="hidden" name="product_name" value="{{ r.get('title') }}">
                                                <button type="submit" class="paypal-btn" style="border:none; cursor:pointer;">Checkout with PayPal</button>
                                            </form>
                                        </div>
                                    </div>
                                {% endfor %}
                            </div>
                        {% else %}
                            <p style="font-size: 12px;">No older listings found.</p>
                        {% endif %}
                    </div>
                </div>
            {% endif %}

            {% if checkout_msg %}
                <div class="result-card" style="border-left-color: #0070BA; background: #E6F0FA;">
                    <h3 style="color: #0070BA;">🛍️ Autonomous Purchase Status</h3>
                    <div class="ai-output">{{ checkout_msg }}</div>
                </div>
            {% endif %}
        </div>

        <div id="walletTab" class="tab-pane">
            <h3 style="color: var(--green-dark); font-size: 15px; margin-top:0;">💳 Account Wallet</h3>
            <div class="card-item" style="flex-direction: column; align-items: flex-start;">
                <h4>Current Balance</h4>
                <p style="font-size: 18px; font-weight: bold; color: var(--green-primary); margin: 6px 0;">₦{{ "%.2f"|format(balance) }}</p>
                <form action="/fund" method="POST" style="width: 100%; margin-top: 10px;">
                    <div class="form-group" style="margin-bottom: 8px;">
                        <input type="number" name="amount" placeholder="Enter amount to fund" required min="1" step="any">
                    </div>
                    <button type="submit" class="paypal-btn" style="width: 100%; padding: 10px; font-size: 13px;">Fund Account via PayPal</button>
                </form>
            </div>
        </div>

        <div id="recommendTab" class="tab-pane">
            <h3 style="color: var(--green-dark); font-size: 15px; margin-top:0;">Curated For You</h3>
            <div class="card-item">
                <div>
                    <h4>Poolee Energize20 (20000mAh)</h4>
                    <p><strong>₦18,000</strong> • 22.5W Fast Charging.</p>
                </div>
            </div>
        </div>

        <div id="promosTab" class="tab-pane">
            <h3 style="color: var(--green-dark); font-size: 15px; margin-top:0;">🔥 Live Web Promos</h3>
            <div class="card-item" style="border-left-color: #D97706;">
                <div>
                    <h4>Jumia Tech Week Flash Sale</h4>
                    <p>Up to 25% off selected mobile accessories.</p>
                </div>
            </div>
        </div>

        <div id="newsTab" class="tab-pane">
            <h3 style="color: var(--green-dark); font-size: 15px; margin-top:0;">📰 Shopping & Tech News</h3>
            <div class="card-item" style="border-left-color: #4A5568;">
                <div>
                    <h4>How to Spot Fake Power Banks</h4>
                    <p>Industry experts share safety tips on checking true capacity.</p>
                </div>
            </div>
        </div>

        <div id="settingsTab" class="tab-pane">
            <h3 style="color: var(--green-dark); font-size: 15px; margin-top:0;">⚙️ App Settings</h3>
            <div class="card-item">
                <div>
                    <h4>API Configuration</h4>
                    <p>Tavily & Groq AI keys active via environment variables.</p>
                </div>
            </div>
        </div>
    </div>

    <script>
        function switchTab(evt, tabName) {
            let panes = document.getElementsByClassName("tab-pane");
            for (let p of panes) { p.classList.remove("active"); }

            let items = document.getElementsByClassName("nav-item");
            for (let i of items) { i.classList.remove("active"); }

            document.getElementById(tabName).classList.add("active");
            evt.currentTarget.classList.add("active");
        }

        function switchSubTab(evt, paneName) {
            let panes = document.getElementsByClassName("sub-pane");
            for (let p of panes) { p.classList.remove("active"); }

            let btns = document.getElementsByClassName("sub-tab-btn");
            for (let b of btns) { b.classList.remove("active"); }

            document.getElementById(paneName).classList.add("active");
            evt.currentTarget.classList.add("active");
        }
    </script>
</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def home():
    result = None
    query = ""
    recent_results = []
    older_results = []
    checkout_msg = None
    
    user_id = "default_user"
    with sqlite3.connect('shopper.db') as conn:
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO wallets 
