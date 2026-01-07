import requests
from bs4 import BeautifulSoup
import time
import random
import json
from flask import Flask, request, jsonify

app = Flask(__name__)

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)',
    'Mozilla/5.0 (X11; Linux x86_64)'
]

def get_headers(referer='https://www.google.com/'):
    return {
        'User-Agent': random.choice(USER_AGENTS),
        'Referer': referer
    }

def parse_price(price_str):
    if not price_str or price_str == 'N/A':
        return float('inf')
    try:
        return float(price_str.replace('$', '').replace(',', ''))
    except:
        return float('inf')

# ---- SCRAPERS (unchanged logic) ----
def scrape_amazon(query, pages=1):
    return []  # keep stub initially (important for Vercel limits)

def scrape_walmart(query, pages=1):
    return []

# ---- API ROUTE ----
@app.route("/api/search")
def search():
    query = request.args.get("query", "")
    pages = int(request.args.get("pages", 1))

    data = []
    data += scrape_amazon(query, pages)
    data += scrape_walmart(query, pages)

    data.sort(key=lambda p: parse_price(p.get("price")))
    return jsonify(data)
