"""
SHOPPER — AI Shopping Assistant
Single-file Flask application using Tavily marketplace-first search and Groq AI evaluation.

Install: pip install flask
Environment: FLASK_SECRET_KEY, SHOPPER_DB_PATH, TAVILY_API_KEY, GROQ_API_KEY
Run: python app.py

Product cards open the seller's original page and, when found or submitted, a
PayPal-hosted payment link. Payments go directly to the seller; Shopper never
collects or holds the money.
"""

from flask import Flask, render_template_string, request, redirect, url_for, flash
import json
import os
import sqlite3
import socket
import ipaddress
import re
import unicodedata
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
import urllib.error
import urllib.request
from urllib.parse import urlparse, urljoin
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "change-this-development-secret")

DB_PATH = os.environ.get("SHOPPER_DB_PATH", "shopper.db")
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "").strip()
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "").strip()
FALLBACK_IMAGE = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='420' height='300' viewBox='0 0 420 300'%3E%3Crect width='420' height='300' rx='24' fill='%23e8f0e5'/%3E%3Ccircle cx='210' cy='130' r='42' fill='%23386641' opacity='.2'/%3E%3Cpath d='M185 130h50m-25-25v50' stroke='%23386641' stroke-width='9' stroke-linecap='round'/%3E%3Ctext x='210' y='220' text-anchor='middle' font-family='Arial' font-size='22' font-weight='700' fill='%232d4a27'%3EShopper%3C/text%3E%3C/svg%3E"

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
.nav-item .ico{display:flex;align-items:center;justify-content:center;line-height:1}.nav-item .ico svg{width:24px;height:24px;display:block}.brand-mark{display:grid;place-items:center}.brand-mark svg{width:25px;height:25px;display:block}
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
.item-price{font-weight:900;color:var(--forest);font-size:14px;margin:5px 0}.source-tag{display:inline-block;background:#edf4e9;color:#386641;border-radius:99px;padding:4px 8px;font-size:10px;font-weight:900;margin-bottom:6px}.seller-listing{border:1px solid #d9e7d3;background:#fbfdf9;border-radius:15px;padding:14px;margin:10px 0}.seller-listing .price{font-weight:900;color:var(--forest);font-size:15px}.sell-page{max-width:760px;margin:20px auto;background:#fff;border:1px solid var(--line);border-radius:20px;padding:24px;box-shadow:var(--shadow)}.sell-page input,.sell-page textarea{width:100%;border:1px solid #d7e1d2;background:#fff;border-radius:11px;padding:13px;outline:0;font:inherit;font-size:13px}.sell-page textarea{min-height:115px;resize:vertical}.sell-page .field{margin:14px 0}.sell-page .hint{font-size:11px;color:var(--muted);line-height:1.5}.paypal-btn{display:inline-block;border:0;border-radius:9px;background:#ffc439;color:#17345b;padding:8px 11px;font-size:11px;font-weight:900;text-decoration:none;margin:7px 5px 0 0}.small-btn{border:0;border-radius:9px;background:var(--forest);color:#fff;padding:8px 11px;font-size:11px;font-weight:800;cursor:pointer;margin-top:7px}
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
 <div class="brand-mark"><svg class="lucide lucide-leaf" aria-hidden="true" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 4.18 2 8 0 5.5-4.78 10-10 10Z"></path><path d="M2 21c0-3 1.85-5.36 5.08-6C9.5 14.52 12 13 13 12"></path></svg></div>
 <button class="nav-item active" data-tab="search" aria-label="Shopper"><span class="ico"><svg class="lucide lucide-search" aria-hidden="true" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m21 21-4.34-4.34"></path><circle cx="11" cy="11" r="8"></circle></svg></span><span class="tip">Shopper</span></button>
 <a class="nav-item" href="{{ url_for('sell_product') }}" aria-label="Sell a product"><span class="ico">＋</span><span class="tip">Sell a product</span></a>
 <button class="nav-item" data-tab="wallet" aria-label="Wallet"><span class="ico"><svg class="lucide lucide-wallet" aria-hidden="true" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 7V4a1 1 0 0 0-1-1H5a2 2 0 0 0 0 4h15a1 1 0 0 1 1 1v4h-3a2 2 0 0 0 0 4h3a1 1 0 0 0 1-1v-2a1 1 0 0 0-1-1"></path><path d="M3 5v14a2 2 0 0 0 2 2h15a1 1 0 0 0 1-1v-4"></path></svg></span><span class="tip">Wallet</span></button>
 <button class="nav-item" data-tab="recommend" aria-label="Recommendations"><span class="ico"><svg class="lucide lucide-sparkles" aria-hidden="true" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11.017 2.814a1 1 0 0 1 1.966 0l1.051 5.558a2 2 0 0 0 1.594 1.594l5.558 1.051a1 1 0 0 1 0 1.966l-5.558 1.051a2 2 0 0 0-1.594 1.594l-1.051 5.558a1 1 0 0 1-1.966 0l-1.051-5.558a2 2 0 0 0-1.594-1.594l-5.558-1.051a1 1 0 0 1 0-1.966l5.558-1.051a2 2 0 0 0 1.594-1.594z"></path><path d="M20 2v4"></path><path d="M22 4h-4"></path><circle cx="4" cy="20" r="2"></circle></svg></span><span class="tip">Recommendations</span></button>
 <button class="nav-item" data-tab="promos" aria-label="Promos"><span class="ico"><svg class="lucide lucide-tag" aria-hidden="true" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12.586 2.586A2 2 0 0 0 11.172 2H4a2 2 0 0 0-2 2v7.172a2 2 0 0 0 .586 1.414l8.704 8.704a2.426 2.426 0 0 0 3.42 0l6.58-6.58a2.426 2.426 0 0 0 0-3.42z"></path><circle cx="7.5" cy="7.5" r=".5" fill="currentColor"></circle></svg></span><span class="tip">Promos</span></button>
 <button class="nav-item" data-tab="news" aria-label="News"><span class="ico"><svg class="lucide lucide-newspaper" aria-hidden="true" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 18h-5"></path><path d="M18 14h-8"></path><path d="M4 22h16a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2H8a2 2 0 0 0-2 2v16a2 2 0 0 1-4 0v-9a2 2 0 0 1 2-2h2"></path><rect height="4" rx="1" width="8" x="10" y="6"></rect></svg></span><span class="tip">News</span></button>
 <button class="nav-item nav-bottom" data-tab="settings" aria-label="Settings"><span class="ico"><svg class="lucide lucide-settings" aria-hidden="true" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9.671 4.136a2.34 2.34 0 0 1 4.659 0 2.34 2.34 0 0 0 3.319 1.915 2.34 2.34 0 0 1 2.33 4.033 2.34 2.34 0 0 0 0 3.831 2.34 2.34 0 0 1-2.33 4.033 2.34 2.34 0 0 0-3.319 1.915 2.34 2.34 0 0 1-4.659 0 2.34 2.34 0 0 0-3.32-1.915 2.34 2.34 0 0 1-2.33-4.033 2.34 2.34 0 0 0 0-3.831A2.34 2.34 0 0 1 6.35 6.051a2.34 2.34 0 0 0 3.319-1.915"></path><circle cx="12" cy="12" r="3"></circle></svg></span><span class="tip">Settings</span></button>
</nav>
<main><div class="main-inner">
{% with messages = get_flashed_messages() %}
 {% for message in messages %}<div class="flash">{{ message }}</div>{% endfor %}
{% endwith %}

<section id="search" class="panel active">
 <div class="hero">
  <p class="eyebrow">{{ greeting }}</p>
  <h1>What are we shopping for today?</h1>
  <p class="subtitle">Tell Shopper what you need. Results are split 50% across Jumia, Temu and other online stores, and 50% across social media listings. We filter for the product type and your stated budget.</p>
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
  {% if seller_listings %}
  <div style="margin:22px 0"><h3>Products listed directly on Shopper</h3><div class="product-grid">
   {% for item in seller_listings %}
    <article class="product-card"><img src="{{ fallback_image }}" alt="Product image"><div><h4>{{ item.title }}</h4><p>{{ item.description }}</p><p class="price">{{ item.price }}</p><p><a class="small-btn" href="{{ item.product_url }}" target="_blank" rel="noopener noreferrer">View product ↗</a></p><p><a class="paypal-btn" href="{{ item.paypal_url }}" target="_blank" rel="noopener noreferrer">Pay with PayPal ↗</a></p></div></article>
   {% endfor %}</div></div>
  {% endif %}
  <div id="recent" class="subpane active">
   {% if recent_results %}<div class="product-grid">
   {% for item in recent_results %}
    <article class="product-card">
     <img src="{{ item.image_url or fallback_image }}" alt="Product image" loading="lazy" onerror="this.onerror=null;this.src='{{ fallback_image }}'">
     <div><h4>{{ item.title }}</h4><p><span class="source-tag">{{ item.source_group or item.marketplace or 'Online store' }}</span></p>{% if item.display_price %}<p class="item-price">{{ item.display_price }}</p>{% else %}<p class="hint">Price not verified — check seller page</p>{% endif %}<p>{{ item.content[:180] if item.content else '' }}</p>
      {% if item.url %}<p><a class="small-btn" href="{{ item.url }}" target="_blank" rel="noopener noreferrer">Buy from Seller ↗</a></p>{% endif %}
      {% if item.paypal_url %}<p><a class="paypal-btn" href="{{ item.paypal_url }}" target="_blank" rel="noopener noreferrer">Pay with PayPal ↗</a></p>{% endif %}
     </div>
    </article>
   {% endfor %}</div>{% else %}<div class="empty">No listing with an extracted within-budget price was found. Check the alternatives below or try another search phrase.</div>{% endif %}
   {% if over_budget_results %}<div style="margin-top:24px"><h3>Above your budget — alternatives</h3><p class="muted">These listings appear relevant, but their extracted naira price is higher than your budget.</p><div class="product-grid">{% for item in over_budget_results %}<article class="product-card"><img src="{{ item.image_url or fallback_image }}" alt="Product image" loading="lazy" onerror="this.onerror=null;this.src='{{ fallback_image }}'"><div><h4>{{ item.title }}</h4><p><span class="source-tag">{{ item.source_group }}</span></p><p class="item-price">{{ item.display_price }} · Above budget</p><p>{{ item.content[:180] if item.content else '' }}</p><p><a class="small-btn" href="{{ item.url }}" target="_blank" rel="noopener noreferrer">View seller ↗</a></p>{% if item.paypal_url %}<p><a class="paypal-btn" href="{{ item.paypal_url }}" target="_blank" rel="noopener noreferrer">Pay with PayPal ↗</a></p>{% endif %}</div></article>{% endfor %}</div></div>{% endif %}
   {% if unpriced_results %}<div style="margin-top:24px"><h3>Other relevant listings — price not confirmed in naira</h3><p class="muted">Some listings do not show a usable price, or show a different currency. Open the seller page to confirm the current naira price. They are not confirmed to be within your budget.</p><div class="product-grid">{% for item in unpriced_results %}<article class="product-card"><img src="{{ item.image_url or fallback_image }}" alt="Product image" loading="lazy" onerror="this.onerror=null;this.src='{{ fallback_image }}'"><div><h4>{{ item.title }}</h4><p><span class="source-tag">{{ item.source_group }}</span></p><p class="hint">{% if item.budget_status == 'foreign_currency' %}{{ item.display_price }} · not compared with NGN budget{% else %}Price not verified{% endif %}</p><p>{{ item.content[:180] if item.content else '' }}</p><p><a class="small-btn" href="{{ item.url }}" target="_blank" rel="noopener noreferrer">View seller ↗</a></p></div></article>{% endfor %}</div></div>{% endif %}
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
 <p class="eyebrow">Your account</p><h2>Wallet</h2><p class="subtitle">Shopper wallet payments are not enabled yet. For now, buy directly from the seller using the link on each product.</p>
 <div class="cards">
  <div class="card"><div class="symbol">▣</div><h3>Wallet coming later</h3><p>Direct seller checkout links are active. Shopper's own balance and one-tap payments will be added after a supported marketplace payment provider is connected.</p><span class="status">Not accepting funds</span></div>
 </div>
</section>

<section id="recommend" class="panel">
 <p class="eyebrow">Picked for your needs</p><h2>Recommendations</h2><p class="subtitle">Recommendations will be based on your searches as product data becomes available.</p>
 <div class="empty">No personalized recommendations yet. Search for a product to get started.</div>
</section>

<section id="promos" class="panel">
 <p class="eyebrow">Offers and savings</p><h2>Find live promos</h2>
 <p class="subtitle">Tell Shopper what you want deals on. We'll search the web for promotions and show matching offers.</p>
 <form class="search-form" method="post" action="{{ url_for('promos') }}">
  <input type="text" name="promo_query" value="{{ promo_query }}" placeholder="e.g. phone discounts, laptops, fashion deals" maxlength="250" required aria-label="What promotions are you looking for?">
  <button class="primary" type="submit">⚡ Find promos</button>
 </form>
 {% if promo_error %}<div class="notice">{{ promo_error }}</div>{% endif %}
 {% if promo_results %}
  <div class="result"><h3>Promotions matching “{{ promo_query }}”</h3><div class="product-grid">
  {% for item in promo_results %}
   <article class="product-card"><img src="{{ item.image_url or fallback_image }}" alt="Promotion image" loading="lazy" onerror="this.onerror=null;this.src='{{ fallback_image }}'">
    <div><h4>{{ item.title }}</h4><p>{{ item.content[:210] if item.content else 'Open the merchant page to review this offer.' }}</p>
     {% if item.url %}<p><a href="{{ item.url }}" target="_blank" rel="noopener noreferrer">View promotion ↗</a></p>{% endif %}
    </div>
   </article>
  {% endfor %}</div><p class="muted" style="margin-top:15px">Confirm current price, expiry date, stock and eligibility on the merchant's page.</p></div>
 {% elif promo_searched %}<div class="empty">No matching promotions were returned. Try a broader search or check that Tavily is configured.</div>
 {% else %}<div class="empty">Enter a product or category above and tap <strong>Find promos</strong> to search for offers.</div>{% endif %}
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
  <p style="margin-top:15px">Shopper checks public seller pages for PayPal checkout links and also accepts seller-submitted links. Only PayPal-hosted payment URLs are accepted.</p>
  <p>Set <code>TAVILY_API_KEY</code> and <code>GROQ_API_KEY</code> as environment variables, then restart the app.</p>
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
        conn.execute("""
            CREATE TABLE IF NOT EXISTS seller_paypal_links (
                product_url TEXT PRIMARY KEY,
                product_name TEXT NOT NULL,
                paypal_url TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS seller_products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                product_url TEXT NOT NULL,
                description TEXT NOT NULL,
                price TEXT NOT NULL,
                paypal_url TEXT NOT NULL,
                created_at TEXT NOT NULL
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


def normalize_image_url(value):
    """Accept Tavily image strings or objects, and reject non-web URLs."""
    if isinstance(value, dict):
        value = value.get("url") or value.get("image_url") or value.get("src") or ""
    if not isinstance(value, str):
        return ""
    value = value.strip()
    parsed = urlparse(value)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return ""
    return value


def normalize_store_url(value):
    """Only expose genuine HTTP(S) seller pages as clickable links."""
    if not isinstance(value, str):
        return ""
    value = value.strip()
    parsed = urlparse(value)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return ""
    return value


def valid_paypal_url(value):
    """Accept only HTTPS PayPal-hosted payment URLs, never arbitrary redirects."""
    if not isinstance(value, str):
        return ""
    value = value.strip()
    parsed = urlparse(value)
    host = (parsed.hostname or "").lower().rstrip(".")
    allowed = host == "paypal.com" or host.endswith(".paypal.com") or host == "paypal.me" or host.endswith(".paypal.me")
    if parsed.scheme != "https" or not allowed or not parsed.path or parsed.username or parsed.password:
        return ""
    return value


class PayPalLinkParser(HTMLParser):
    def __init__(self, base_url):
        super().__init__()
        self.base_url = base_url
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() != "a":
            return
        href = dict(attrs).get("href", "")
        candidate = valid_paypal_url(urljoin(self.base_url, href))
        if candidate and ("/ncp/payment/" in candidate.lower() or "paypal.me/" in candidate.lower() or "/checkoutnow" in candidate.lower() or "/pay/" in candidate.lower()):
            self.links.append(candidate)


def public_http_url(value):
    """Reject local/private destinations before fetching a seller page."""
    parsed = urlparse(value)
    if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username or parsed.password:
        return False
    try:
        addresses = socket.getaddrinfo(parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80), type=socket.SOCK_STREAM)
        return bool(addresses) and all(ipaddress.ip_address(entry[4][0]).is_global for entry in addresses)
    except (OSError, ValueError):
        return False


def discover_paypal_link(page_url):
    """Try to find a real PayPal payment anchor on a public seller page."""
    page_url = normalize_store_url(page_url)
    if not page_url or not public_http_url(page_url):
        return ""
    try:
        req = urllib.request.Request(page_url, headers={"User-Agent": "ShopperLinkChecker/1.0", "Accept": "text/html"})
        # Do not follow redirects: the redirect target would need a fresh SSRF check.
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):
                return None
        opener = urllib.request.build_opener(NoRedirect)
        with opener.open(req, timeout=3) as response:
            content_type = response.headers.get("Content-Type", "").lower()
            if "text/html" not in content_type:
                return ""
            html = response.read(1_500_000).decode("utf-8", errors="ignore")
        parser = PayPalLinkParser(page_url)
        parser.feed(html)
        return parser.links[0] if parser.links else ""
    except (OSError, ValueError, HTTPError, URLError, TimeoutError):
        return ""


def get_saved_paypal_link(product_url):
    if not product_url:
        return ""
    with db_connect() as conn:
        row = conn.execute("SELECT paypal_url FROM seller_paypal_links WHERE product_url = ?", (product_url,)).fetchone()
    return valid_paypal_url(row["paypal_url"]) if row else ""


def attach_result_images(results, images):
    """Use result-specific image fields first, then Tavily image results."""
    candidates = [normalize_image_url(x) for x in (images or [])]
    candidates = [x for x in candidates if x]
    for i, item in enumerate(results):
        item["url"] = normalize_store_url(item.get("url"))
        own = item.get("image_url") or item.get("image") or item.get("thumbnail") or item.get("thumbnail_url")
        item["image_url"] = normalize_image_url(own)
        if not item["image_url"] and i < len(candidates):
            item["image_url"] = candidates[i]
        # A result can itself be a PayPal payment page.
        item["paypal_url"] = valid_paypal_url(item["url"])
        if not item["paypal_url"]:
            item["paypal_url"] = get_saved_paypal_link(item["url"])
        # Limit live page checks to avoid slowing every search excessively.
        if not item["paypal_url"] and i < 3:
            item["paypal_url"] = discover_paypal_link(item["url"])
    return results


MARKETPLACE_DOMAINS = [
    "jumia.com.ng", "konga.com", "temu.com", "amazon.com", "amazon.co.uk",
    "aliexpress.com", "ebay.com", "shein.com", "walmart.com", "takealot.com",
]
SOCIAL_DOMAINS = ["facebook.com", "instagram.com", "tiktok.com", "x.com", "pinterest.com"]


def marketplace_name(page_url):
    try:
        host = (urlparse(page_url).hostname or "").lower()
    except ValueError:
        return ""
    labels = {
        "jumia.com.ng": "Jumia Nigeria", "konga.com": "Konga", "temu.com": "Temu",
        "amazon.com": "Amazon", "amazon.co.uk": "Amazon UK", "aliexpress.com": "AliExpress",
        "ebay.com": "eBay", "shein.com": "SHEIN", "walmart.com": "Walmart", "takealot.com": "Takealot",
    }
    for domain, label in labels.items():
        if host == domain or host.endswith("." + domain):
            return label
    return ""


def social_name(page_url):
    try:
        host = (urlparse(page_url).hostname or "").lower()
    except ValueError:
        return ""
    labels = {"facebook.com": "Facebook", "instagram.com": "Instagram", "tiktok.com": "TikTok", "x.com": "X", "pinterest.com": "Pinterest"}
    for domain, label in labels.items():
        if host == domain or host.endswith("." + domain):
            return label
    return ""


def _tavily_request(query, domains=None, max_results=8, exclude_domains=None):
    payload = {
        "api_key": TAVILY_API_KEY, "query": query, "search_depth": "advanced",
        "max_results": max_results, "include_images": True, "topic": "general", "country": "Nigeria",
    }
    if domains:
        payload["include_domains"] = domains
    if exclude_domains:
        payload["exclude_domains"] = exclude_domains
    return post_json("https://api.tavily.com/search", payload, timeout=35)


def _normal_words(value):
    value = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode().lower()
    words = re.findall(r"[a-z0-9]+", value)
    stop = {
        "the", "and", "for", "with", "from", "buy", "get", "find", "want", "need",
        "under", "below", "less", "than", "price", "budget", "naira", "ngn", "cheap",
        "best", "online", "product", "please", "around", "about", "maximum", "max",
        "up", "to", "in", "on", "at", "of", "a", "an", "me", "show", "search",
        "available", "sale", "selling", "Nigeria", "Nigerian"
    }
    return {w[:-1] if len(w) > 4 and w.endswith("s") else w for w in words if w not in stop and not w.isdigit()}


def _clean_product_query(query):
    """Remove budget expressions without deleting the product description."""
    value = str(query or "").strip()
    value = re.sub(r"(?:under|below|less\s+than|maximum|max|budget|up\s+to|for)\s*(?:₦|NGN|N)?\s*\d[\d,]*(?:\.\d+)?\s*(?:naira|NGN)?", " ", value, flags=re.I)
    value = re.sub(r"(?:₦|NGN|N)\s*\d[\d,]*(?:\.\d+)?", " ", value, flags=re.I)
    value = re.sub(r"\b\d[\d,]{2,}\b", " ", value)
    value = re.sub(r"\s+", " ", value).strip(" ,.-")
    return value or str(query or "").strip()


def requested_budget(query):
    """Read an explicit or shorthand NGN ceiling, e.g. '2500 beanies'."""
    q = str(query or "").lower().replace(",", "")
    patterns = [
        r"(?:under|below|less\s+than|max(?:imum)?|budget|up\s+to|for)\s*(?:₦|ngn|n)?\s*(\d{3,})",
        r"(?:₦|ngn|n)\s*(\d{3,})",
        r"\b(\d{3,})\s*(?:naira|ngn)\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, q, re.I)
        if match:
            return int(match.group(1))
    # Nigerian shoppers commonly type "2500 beanies" without a currency sign.
    match = re.search(r"\b(\d{3,})\b", q)
    return int(match.group(1)) if match else None


def extract_price(text):
    """Extract an explicitly labelled currency price; ignore bare measurements."""
    value = str(text or "")
    patterns = [
        ("NGN", r"₦\s*([\d,]+(?:\.\d{1,2})?)"),
        ("NGN", r"\bNGN\s*([\d,]+(?:\.\d{1,2})?)"),
        ("NGN", r"\bN\s*([\d,]{3,}(?:\.\d{1,2})?)"),
        ("NGN", r"([\d,]+(?:\.\d{1,2})?)\s*(?:naira|NGN)\b"),
        ("USD", r"\$\s*([\d,]+(?:\.\d{1,2})?)"),
        ("GBP", r"£\s*([\d,]+(?:\.\d{1,2})?)"),
        ("EUR", r"€\s*([\d,]+(?:\.\d{1,2})?)"),
    ]
    for currency, pattern in patterns:
        match = re.search(pattern, value, re.I)
        if match:
            try:
                amount = float(match.group(1).replace(",", ""))
                if amount > 0:
                    return amount, currency
            except ValueError:
                continue
    return None, None


def prepare_product_result(item, group):
    url = normalize_store_url(item.get("url"))
    if not url:
        return None
    item["url"] = url
    # Only use an image attached to this result. Positional image matching can show
    # a completely different product, so unrelated Tavily image results are ignored.
    item["image_url"] = normalize_image_url(item.get("image_url") or item.get("image") or item.get("thumbnail") or item.get("thumbnail_url"))
    item["paypal_url"] = valid_paypal_url(url) or get_saved_paypal_link(url)
    item["marketplace"] = marketplace_name(url)
    item["social_platform"] = social_name(url)
    item["source_group"] = "Online marketplaces & stores" if group == "marketplace" else "Social media"
    item["source_name"] = item["marketplace"] or item["social_platform"] or "Online store"
    price_text = " ".join(str(item.get(k, "") or "") for k in ("title", "content", "raw_content"))
    amount, currency = extract_price(price_text)
    item["price_value"] = amount
    item["price_currency"] = currency
    item["display_price"] = (("₦" if currency == "NGN" else "$" if currency == "USD" else "£" if currency == "GBP" else "€") + "{:,.2f}".format(amount).rstrip("0").rstrip(".")) if amount is not None else ""
    return item


def relevant_product(item, query, budget):
    wanted = _normal_words(_clean_product_query(query))
    found = _normal_words(str(item.get("title", "")) + " " + str(item.get("content", "")) + " " + str(item.get("raw_content", "")))
    if wanted:
        overlap = wanted & found
        # Require a meaningful share of the requested terms, not just a generic
        # word such as "cap" or "product". This blocks unrelated substitutes.
        required = 1 if len(wanted) <= 2 else max(2, (len(wanted) + 1) // 2)
        if len(overlap) < required:
            return False
        query_text = _clean_product_query(query).lower()
        # Strong category guard: a Christmas cap is not a beanie unless the listing
        # actually identifies itself as a beanie/knit cap.
        if "beanie" in query_text and "beanie" not in found and "knit cap" not in (str(item.get("title", "")).lower() + " " + str(item.get("content", "")).lower()):
            return False
    amount = item.get("price_value")
    currency = item.get("price_currency")
    item["budget_limit"] = budget
    item["budget_status"] = "unpriced"
    if amount is not None and currency == "NGN":
        if budget is not None and amount > budget:
            item["budget_status"] = "over_budget"
        else:
            item["budget_status"] = "within_budget"
    elif amount is not None:
        item["budget_status"] = "foreign_currency"
    return True


def _search_variants(product_query):
    base = product_query.strip()
    variants = [
        f'"{base}" price buy online Nigeria',
        f'{base} exact product listing current price Nigeria',
        f'{base} cheapest offer store listing for sale',
    ]
    # Keep requests distinct and bounded.
    seen, output = set(), []
    for value in variants:
        key = value.lower()
        if key not in seen:
            seen.add(key)
            output.append(value)
    return output


def search_tavily(query, time_range=None, product_search=True):
    """Deep price hunt across commerce sites and social listings, with separate price tiers."""
    if not TAVILY_API_KEY:
        return []
    budget = requested_budget(query)
    clean_query = _clean_product_query(query)
    pools = {"marketplace": [], "social": []}
    variants = _search_variants(clean_query)
    # Deep mode: two targeted searches per source group plus one broad store sweep.
    searches = []
    for variant in variants[:2]:
        searches.append(("marketplace", variant, MARKETPLACE_DOMAINS, None, 16))
    searches.append(("marketplace", f'{clean_query} online shop product page price Nigeria', None, SOCIAL_DOMAINS, 14))
    for variant in variants[:2]:
        searches.append(("social", f'{variant} Facebook Instagram TikTok marketplace', SOCIAL_DOMAINS, None, 16))

    for group, search_query, domains, excluded, max_results in searches:
        try:
            data = _tavily_request(search_query, domains=domains, max_results=max_results, exclude_domains=excluded)
            for raw in (data.get("results", []) or []):
                item = prepare_product_result(dict(raw), group)
                if not item:
                    continue
                if product_search and not relevant_product(item, clean_query, budget):
                    continue
                if not product_search:
                    item["budget_status"] = "unpriced"
                if not item.get("paypal_url") and len(pools[group]) < 3:
                    item["paypal_url"] = discover_paypal_link(item["url"])
                pools[group].append(item)
        except (urllib.error.URLError, TimeoutError, ValueError, KeyError) as exc:
            app.logger.warning("Tavily deep %s search failed: %s", group, exc)

    # Deduplicate each pool by canonical URL, retain strongest title match first.
    output, seen = [], set()
    for group in ("marketplace", "social"):
        unique = {}
        for item in pools[group]:
            key = item["url"].split("#", 1)[0].rstrip("/").lower()
            if key not in unique:
                unique[key] = item
        candidates = list(unique.values())
        candidates.sort(key=lambda x: (
            0 if x.get("budget_status") == "within_budget" else 1 if x.get("budget_status") == "unpriced" else 2,
            x.get("price_value") if x.get("price_value") is not None and x.get("price_currency") == "NGN" else float("inf"),
        ))
        # Equal source quotas: up to 12 from each. Never pad a short group with junk.
        kept = 0
        for item in candidates:
            key = item["url"].split("#", 1)[0].rstrip("/").lower()
            if key in seen or kept >= 12:
                continue
            seen.add(key)
            output.append(item)
            kept += 1
    # Lowest verified NGN prices appear first within the main display tier.
    output.sort(key=lambda x: (
        0 if x.get("budget_status") == "within_budget" else 1 if x.get("budget_status") == "unpriced" else 2,
        x.get("price_value") if x.get("price_value") is not None and x.get("price_currency") == "NGN" else float("inf"),
    ))
    return output


def find_seller_products(query="", limit=30):
    """Fetch seller-submitted products, optionally matching words in the search."""
    with db_connect() as conn:
        rows = conn.execute("SELECT * FROM seller_products ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    terms = [t.lower() for t in re.findall(r"[a-zA-Z0-9]+", query) if len(t) > 2]
    output = []
    for row in rows:
        item = dict(row)
        haystack = (item["title"] + " " + item["description"]).lower()
        if not terms or any(term in haystack for term in terms):
            output.append(item)
    return output


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
    seller_listings = []
    over_budget_results = []
    unpriced_results = []

    if request.method == "POST" or request.args.get("q"):
        query = (request.form.get("query", "") if request.method == "POST" else request.args.get("q", "")).strip()[:300]
        if not query:
            flash("Please enter a product to search for.")
        else:
            all_results = search_tavily(query)
            # Flexible budget: show affordable matches first, then clearly separated
            # above-budget and price-unverified alternatives.
            recent_results = [x for x in all_results if x.get("budget_status") == "within_budget"]
            over_budget_results = [x for x in all_results if x.get("budget_status") == "over_budget"]
            unpriced_results = [x for x in all_results if x.get("budget_status") in ("unpriced", "foreign_currency")]
            if requested_budget(query) is None:
                recent_results = all_results
                over_budget_results = []
                unpriced_results = []
            # Seller-submitted products are stored in Shopper's database and shown alongside web results.
            seller_listings = find_seller_products(query)
            older_results = []
            context = "\n\n".join(
                f"Title: {item.get('title', '')}\n"
                f"Link: {item.get('url', '')}\n"
                f"Content: {item.get('content', '')}"
                for item in all_results
            )
            prompt = (
                f"The shopper is looking for: {query}\n\n"
                f"Search results (prices shown only when extracted from the listing text):\n{context or 'No web results were returned.'}\n\n"
                "Only compare listings that match the exact product requested. This shopper selected flexible budget mode: identify listings whose extracted NGN price is within budget first, and discuss above-budget options only as clearly labelled alternatives. Never compare foreign currencies as if they were naira. Do not guess prices, shipping, seller reliability, stock, or product variants. If no verified affordable match is found, say so. Keep the response under 120 words."
            )
            result = ask_groq(prompt)
            if not TAVILY_API_KEY:
                flash("Tavily is not configured. Add TAVILY_API_KEY to enable live product search.")
    return render_template_string(
        HTML,
        result=result,
        recent_results=recent_results,
        older_results=older_results,
        seller_listings=seller_listings,
        over_budget_results=over_budget_results,
        unpriced_results=unpriced_results,
        query=query,
        balance=get_balance(),
        tavily_ready=bool(TAVILY_API_KEY),
        groq_ready=bool(GROQ_API_KEY),
        greeting=greeting_for_now(),
        promo_query="",
        promo_results=[],
        promo_error=None,
        promo_searched=False,
        fallback_image=FALLBACK_IMAGE,
    )


SELL_HTML = r"""
<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Sell on Shopper</title>
<style>body{margin:0;background:#f4f8f3;color:#263428;font:15px Arial,sans-serif}.wrap{max-width:720px;margin:35px auto;padding:18px}.box{background:white;border:1px solid #e4eadf;border-radius:20px;padding:25px;box-shadow:0 12px 34px rgba(45,74,39,.08)}h1{color:#2d4a27}p{color:#758273;line-height:1.6}.field{margin:17px 0}label{display:block;color:#2d4a27;font-weight:bold;font-size:13px;margin-bottom:8px}input,textarea{width:100%;box-sizing:border-box;border:1px solid #d7e1d2;border-radius:11px;padding:13px;font:inherit}textarea{min-height:120px;resize:vertical}.btn{display:inline-block;background:#386641;color:white;border:0;border-radius:12px;padding:14px 20px;font-weight:bold;text-decoration:none;cursor:pointer}.hint{font-size:12px;color:#758273}.flash{padding:12px;background:#fff2d7;border-radius:10px;color:#76541c;margin-bottom:12px}</style></head><body><div class="wrap"><div class="box"><a href="{{ url_for('home') }}">← Back to Shopper</a><h1>List a product on Shopper</h1><p>Submit your product details and your own PayPal checkout link. Once submitted, the listing can appear in Shopper search results when shoppers search for matching products.</p>
{% with messages = get_flashed_messages() %}{% for message in messages %}<div class="flash">{{ message }}</div>{% endfor %}{% endwith %}
<form method="post" action="{{ url_for('sell_product') }}">
<div class="field"><label>Product name</label><input name="title" maxlength="180" required placeholder="e.g. Oraimo 20000mAh Power Bank"></div>
<div class="field"><label>Product page link</label><input type="url" name="product_url" required placeholder="https://your-store.com/product"><p class="hint">The link shoppers can open to view or order your product.</p></div>
<div class="field"><label>Explain your product</label><textarea name="description" maxlength="2000" required placeholder="Describe features, condition, delivery options and what makes it useful..."></textarea></div>
<div class="field"><label>Price</label><input name="price" maxlength="60" required placeholder="e.g. ₦45,000"></div>
<div class="field"><label>Your PayPal checkout link</label><input type="url" name="paypal_url" required placeholder="https://www.paypal.com/ncp/payment/..."><p class="hint">Use a payment link created in your own eligible PayPal account. Shopper does not receive or hold the payment.</p></div>
<button class="btn" type="submit">Submit product to Shopper</button>
</form></div></div></body></html>
"""


@app.route("/sell", methods=["GET", "POST"])
def sell_product():
    if request.method == "GET":
        return render_template_string(SELL_HTML)
    title = request.form.get("title", "").strip()[:180]
    product_url = normalize_store_url(request.form.get("product_url", ""))
    description = request.form.get("description", "").strip()[:2000]
    price = request.form.get("price", "").strip()[:60]
    paypal_url = valid_paypal_url(request.form.get("paypal_url", ""))
    if not all([title, product_url, description, price, paypal_url]):
        flash("Please complete every field and use a valid HTTPS PayPal link.")
        return redirect(url_for("sell_product"))
    with db_connect() as conn:
        conn.execute("""INSERT INTO seller_products (title, product_url, description, price, paypal_url, created_at)
                        VALUES (?, ?, ?, ?, ?, ?)""",
                     (title, product_url, description, price, paypal_url, datetime.utcnow().isoformat(timespec="seconds")))
    flash("Your product has been submitted and is now eligible to appear in matching Shopper searches.")
    return redirect(url_for("home"))


@app.route("/seller-paypal-link", methods=["POST"])
def submit_seller_paypal_link():
    product_name = request.form.get("product_name", "").strip()[:200]
    product_url = normalize_store_url(request.form.get("product_url", ""))
    paypal_url = valid_paypal_url(request.form.get("paypal_url", ""))
    return_query = request.form.get("return_query", "").strip()[:300]
    if not product_name or not product_url or not paypal_url:
        flash("Please provide a valid product page and HTTPS PayPal payment link.")
        return redirect(url_for("home", q=return_query) if return_query else url_for("home"))
    with db_connect() as conn:
        conn.execute("""
            INSERT INTO seller_paypal_links (product_url, product_name, paypal_url, created_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(product_url) DO UPDATE SET
                product_name=excluded.product_name,
                paypal_url=excluded.paypal_url,
                created_at=excluded.created_at
        """, (product_url, product_name, paypal_url, datetime.utcnow().isoformat(timespec="seconds")))
    flash("PayPal link submitted. Shopper will show it with this product in future searches.")
    return redirect(url_for("home", q=return_query) if return_query else url_for("home"))


@app.route("/promos", methods=["POST"])
def promos():
    promo_query = request.form.get("promo_query", "").strip()[:250]
    promo_results = []
    promo_error = None
    promo_searched = bool(promo_query)

    if not promo_query:
        flash("Tell Shopper what kind of promotions you want to find.")
        return redirect(url_for("home"))

    if not TAVILY_API_KEY:
        promo_error = "Live promotions need a Tavily API key. Set TAVILY_API_KEY in your app environment."
    else:
        search_query = f"{promo_query} promotions discounts deals offers Nigeria"
        promo_results = search_tavily(search_query, time_range="week", product_search=False)
        if not promo_results:
            promo_error = "The promotion search returned no results. Try a different search phrase."

    return render_template_string(
        HTML,
        result=None,
        recent_results=[],
        older_results=[],
        seller_listings=[],
        query="",
        balance=get_balance(),
        checkout_msg=None,
        tavily_ready=bool(TAVILY_API_KEY),
        groq_ready=bool(GROQ_API_KEY),
        greeting=greeting_for_now(),
        promo_query=promo_query,
        promo_results=promo_results,
        promo_error=promo_error,
        promo_searched=promo_searched,
        fallback_image=FALLBACK_IMAGE,
    )


@app.route("/health")
def health():
    return {"status": "ok"}


init_db()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=False)
