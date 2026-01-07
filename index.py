import os
import requests
from bs4 import BeautifulSoup
import time
import random
import json
from flask import Flask, request, render_template

# Correct single app creation with template path for Vercel
app = Flask(__name__, template_folder='../templates')

# Optional: helpful for debugging paths locally vs Vercel
# print("Template folder:", app.template_folder)




USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
]

def get_headers(referer='https://www.google.com/'):
    return {
        'User-Agent': random.choice(USER_AGENTS),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Referer': referer,
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }

def scrape_amazon(query, pages=1):
    base_url = 'https://www.amazon.com/s'
    products = []
    for page in range(1, pages + 1):
        params = {'k': query, 'page': page}
        response = requests.get(base_url, params=params, headers=get_headers('https://www.amazon.com/'), timeout=15)
        if response.status_code != 200:
            print(f"Amazon blocked or error on page {page}: {response.status_code}")
            continue

        soup = BeautifulSoup(response.text, 'html.parser')
        items = soup.select('div.s-result-item[data-component-type="s-search-result"]')

        for item in items:
            # Multiple fallbacks for name/title
            name_elem = (item.select_one('h2 a span') or 
                         item.select_one('h2 span') or 
                         item.select_one('a.a-link-normal span.a-text-normal') or
                         item.select_one('span.a-size-medium.a-color-base.a-text-normal'))

            # Price fallbacks
            price_whole = item.select_one('.a-price-whole')
            price_frac = item.select_one('.a-price-fraction')
            price_alt = item.select_one('.a-offscreen')  # Hidden price often more reliable

            rating_elem = item.select_one('.a-icon-alt')
            link_elem = item.select_one('h2 a') or item.select_one('a.a-link-normal')
            image_elem = item.select_one('img.s-image')

            price = 'N/A'
            if price_alt:
                price = price_alt.get_text(strip=True)
            elif price_whole:
                price = price_whole.get_text(strip=True) + ('.' + price_frac.get_text(strip=True) if price_frac else '')

            products.append({
                'site': 'Amazon',
                'name': name_elem.get_text(strip=True) if name_elem else 'N/A',
                'price': price,
                'rating': rating_elem.get_text(strip=True).split(' out')[0] if rating_elem else 'N/A',
                'url': 'https://www.amazon.com' + link_elem['href'] if link_elem and link_elem.get('href') else 'N/A',
                'image': image_elem['src'] if image_elem and image_elem.get('src') else 'N/A'
            })

        time.sleep(random.uniform(4, 8))  # Longer delay to avoid blocks

    return products

def scrape_walmart(query, pages=1):
    base_url = 'https://www.walmart.com/search'
    products = []
    for page in range(1, pages + 1):
        params = {'q': query, 'page': page, 'sort': 'best_seller'}
        response = requests.get(base_url, params=params, headers=get_headers('https://www.walmart.com/'), timeout=15)
        if response.status_code != 200:
            continue

        soup = BeautifulSoup(response.text, 'html.parser')
        script_tag = soup.find('script', {'id': '__NEXT_DATA__'})
        if not script_tag or not script_tag.string:
            continue

        try:
            data = json.loads(script_tag.string)
            item_stacks = data['props']['pageProps']['initialData']['searchResult']['itemStacks']
            items = item_stacks[0].get('items', []) if item_stacks else []

            for item in items:
                if item.get('__typename') == 'Product':
                    price_info = item.get('priceInfo', {}).get('currentPrice', {}) or item.get('price', {})
                    image_info = item.get('imageInfo', {}) or item.get('image', {})

                    products.append({
                        'site': 'Walmart',
                        'name': item.get('name', 'N/A'),
                        'price': price_info.get('priceString', 'N/A'),
                        'rating': f"{item.get('averageRating', 'N/A')}/5 ({item.get('numberOfReviews', 0)} reviews)",
                        'url': f"https://www.walmart.com/ip/{item.get('usItemId') or item.get('id', '')}" if item.get('id') or item.get('usItemId') else 'N/A',
                        'image': image_info.get('thumbnailUrl', 'N/A') or item.get('image', 'N/A')
                    })
        except Exception:
            pass

        time.sleep(random.uniform(5, 9))

    return products

def parse_price(price_str):
    if price_str == 'N/A':
        return float('inf')
    try:
        return float(price_str.replace('$', '').replace(',', '').replace('USD', '').strip())
    except ValueError:
        return float('inf')

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        query = request.form.get('query')
        sites = request.form.getlist('sites')
        pages = int(request.form.get('pages', 1))
        data = []

        if 'amazon' in sites or 'compare' in sites:
            data += scrape_amazon(query, pages)
        if 'walmart' in sites or 'compare' in sites:
            data += scrape_walmart(query, pages)

        data.sort(key=lambda p: parse_price(p['price']))

        return render_template('results.html', products=data, query=query)

    return render_template('form.html')

if __name__ == '__main__':
    app.run(debug=True)
