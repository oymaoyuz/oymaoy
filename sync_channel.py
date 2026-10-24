"""
OYMAOY.UZ — Telegram Channel Real-time Sync Script
GitHub Actions yoki lokal kompyuterda avtomatik ishlaydi.
Kanal: https://t.me/s/oymaoyy
Barcha rasmlar lokal 'images/' papkasiga yuklanadi (Telegram CDN 404 xatosidan 100% himoya).
"""

import os
import re
import json
import urllib.request
import urllib.parse
import ssl
from bs4 import BeautifulSoup

CHANNEL_URL = "https://t.me/s/oymaoyy"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HTML_FILE = os.path.join(BASE_DIR, "index.html")
KATALOG_FILE = os.path.join(BASE_DIR, "katalog.html")
CACHE_FILE = os.path.join(BASE_DIR, "products_clean.json")
IMAGES_DIR = os.path.join(BASE_DIR, "images")

os.makedirs(IMAGES_DIR, exist_ok=True)

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def fetch_channel_html():
    req = urllib.request.Request(
        CHANNEL_URL,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    )
    with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
        return resp.read().decode("utf-8")

def download_image(photo_url, msg_id):
    if not photo_url or not msg_id:
        return ""
    safe_name = msg_id.replace("/", "_") + ".jpg"
    file_path = os.path.join(IMAGES_DIR, safe_name)

    # Agar allaqachon yuklangan bo'lsa va hajmi > 2000 bayt bo'lsa, qayta yuklamaymiz
    if os.path.exists(file_path) and os.path.getsize(file_path) > 2000:
        return f"images/{safe_name}"

    try:
        req = urllib.request.Request(
            photo_url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        )
        with urllib.request.urlopen(req, context=ctx, timeout=10) as r:
            data = r.read()
            if len(data) > 1000:
                with open(file_path, "wb") as f:
                    f.write(data)
                print(f"Rasm yuklandi: images/{safe_name} ({len(data)} bayt)")
                return f"images/{safe_name}"
    except Exception as e:
        print(f"Rasm yuklashda xatolik ({safe_name}): {e}")

    # Agar yuklab bo'lmasa lekin eski fayl bor bo'lsa
    if os.path.exists(file_path):
        return f"images/{safe_name}"
    return photo_url

def parse_posts(html):
    soup = BeautifulSoup(html, "html.parser")
    messages = soup.find_all("div", class_="tgme_widget_message")
    products = []

    for msg in messages:
        text_elem = msg.find("div", class_="tgme_widget_message_text")
        if not text_elem:
            continue
        text = text_elem.get_text("\n").strip()
        if not text:
            continue

        lines = [l.strip() for l in text.split("\n") if l.strip()]
        first_line = lines[0] if lines else ""

        # Model
        model_match = re.search(r'(iPhone\s+[^\n,]+|Samsung\s+[^\n,]+|Redmi\s+[^\n,]+|poco\s+[^\n,]+)', text, re.I)
        model = model_match.group(1).strip() if model_match else first_line[:30]

        # Xotira
        mem_match = re.search(r'(\d+\s*(?:GB|TB))', text, re.I)
        memory = mem_match.group(1).upper() if mem_match else ""

        # Batareya
        bat_match = re.search(r'(\d+)\s*%', text)
        battery = f"{bat_match.group(1)}%" if bat_match else ""

        # Rang
        color_match = re.search(r'rangi?\s*[:\-]?\s*([a-zA-Zа-яА-ЯёЁ\s]+)', text, re.I)
        color = color_match.group(1).strip() if color_match else ""

        # Holati
        cond_match = re.search(r'holati?\s*[:\-]?\s*([^\n,]+)', text, re.I)
        condition = cond_match.group(1).strip() if cond_match else ""

        # Narx
        price_match = re.search(r'(\d+[\d\s.,]*\s*(?:\$|usd|dollar))', text, re.I)
        if not price_match:
            price_match = re.search(r'(?:narxi|narx)\s*[:\-]?\s*(\d+[\d\s.,]*\$?)', text, re.I)
        price = price_match.group(1).strip() if price_match else ""
        if price and not price.endswith('$') and not 'usd' in price.lower():
            price += '$'

        # Sotilganlik holati (SOTILDI yoki ❌)
        is_sold = bool(re.search(r'(sotildi|sold|проdan)', text, re.I))

        # Rasm URL
        photo = ""
        photo_elem = msg.find("a", class_="tgme_widget_message_photo_wrap")
        if photo_elem and photo_elem.get("style"):
            style = photo_elem["style"]
            url_match = re.search(r"background-image:url\('([^']+)'\)", style)
            if url_match:
                photo = url_match.group(1)

        msg_id = msg.get("data-post", "")

        # Rasmni lokal images/ papkasiga yuklab olish
        local_photo = download_image(photo, msg_id) if photo and not is_sold else ""

        products.append({
            "id": msg_id,
            "model": model,
            "memory": memory,
            "battery": battery,
            "color": color,
            "condition": condition,
            "price": price,
            "photo": photo,
            "local_photo": local_photo,
            "is_sold": is_sold,
            "raw_text": text
        })

    return products

def render_cards(available_products):
    cards_html = []
    for p in available_products:
        model = p.get('model', 'iPhone')
        memory = p.get('memory', '')
        battery = p.get('battery', '')
        color = p.get('color', '')
        condition = p.get('condition', '')
        price = p.get('price', '')
        
        # Mahalliy rasm ustuvor, bo'lmasa original rasm, bo'lmasa placeholder
        photo = p.get('local_photo') or p.get('photo') or ('https://placehold.co/600x800/00182a/2997ff?text=' + urllib.parse.quote(model))

        order_text = f"Salom, oymaoy.uz saytidan ko'rdim. {model} ({memory}, narxi: {price}) bo'yicha ma'lumot olmoqchiman."
        encoded_order = urllib.parse.quote(order_text)

        cats = ['available']
        if 'pro' in model.lower():
            cats.append('promax')
        price_num = 0
        try:
            price_num = float(re.sub(r'[^0-9.]', '', price))
        except:
            pass
        if price_num > 0 and price_num <= 350:
            cats.append('budget')
        cat_class = ' '.join(cats)

        specs_parts = []
        if memory: specs_parts.append(memory)
        if battery: specs_parts.append(f"{battery} batareya")
        if color: specs_parts.append(color)
        specs_line = " • ".join(specs_parts)
        search_data = f"{model} {memory} {battery} {color} {price} {condition}".lower().replace('"', '&quot;')

        card = f'''      <div class="product-card" data-cats="{cat_class}" data-search="{search_data}">
        <div class="card-media">
          <img src="{photo}" alt="{model}" loading="lazy" onerror="this.onerror=null;this.src='https://placehold.co/600x800/00182a/2997ff?text={urllib.parse.quote(model)}';">
          <div class="card-badge-top">
            <span class="status-dot">● Mavjud</span>
          </div>
        </div>
        <div class="card-content">
          <h3 class="card-title">{model}</h3>
          <p class="card-specs">{specs_line}</p>
          <div class="card-footer">
            <div class="card-price">{price}</div>
            <a class="card-action" href="https://t.me/oymaoy_admin?text={encoded_order}" target="_blank" rel="noopener noreferrer">
              <span>Shartini bilish</span>
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
            </a>
          </div>
        </div>
      </div>'''
        cards_html.append(card)

    return "\n\n".join(cards_html)

def update_index_html(available_products):
    if not os.path.exists(HTML_FILE):
        print(f"Xato: {HTML_FILE} fayli topilmadi.")
        return False

    with open(HTML_FILE, 'r', encoding='utf-8') as f:
        html = f.read()

    total_cnt = len(available_products)
    top4 = available_products[:4]
    new_cards = render_cards(top4)

    # "Barcha modellarni ko'rish (12)" tugmasini yangilash
    html = re.sub(r"Barcha modellarni ko'rish \(\d+\)", f"Barcha modellarni ko'rish ({total_cnt})", html)
    html = re.sub(r"barcha \d+ ta telefonni", f"barcha {total_cnt} ta telefonni", html)

    # <div id="product-list" class="product-grid"> ... </div> o'rnini almashtirish
    start_tag = '<div id="product-list" class="product-grid">'
    end_tag = '</div>\n\n      <!-- 4-rasim: Barcha modellarni ko\'rish tugmasi -->'
    
    start_idx = html.find(start_tag)
    if start_idx != -1:
        end_idx = html.find(end_tag, start_idx)
        if end_idx != -1:
            html = html[:start_idx + len(start_tag)] + '\n' + new_cards + '\n      ' + html[end_idx:]
        else:
            # Fallback regex
            pattern = r'(<div id="product-list" class="product-grid">)(.*?)(</div>\s*<!-- 4-rasim)'
            html = re.sub(pattern, rf'\g<1>\n{new_cards}\n      \g<3>', html, flags=re.DOTALL)

    with open(HTML_FILE, 'w', encoding='utf-8') as f:
        f.write(html)

    return True

def update_katalog_html(available_products):
    if not os.path.exists(KATALOG_FILE):
        print(f"Xato: {KATALOG_FILE} fayli topilmadi.")
        return False

    with open(KATALOG_FILE, 'r', encoding='utf-8') as f:
        html = f.read()

    total_cnt = len(available_products)
    pro_cnt = sum(1 for p in available_products if 'pro' in p.get('model', '').lower())
    budget_cnt = 0
    for p in available_products:
        try:
            pr = float(re.sub(r'[^0-9.]', '', p.get('price', '')))
            if pr > 0 and pr <= 350: budget_cnt += 1
        except: pass

    # Tab hisoblagichlarini yangilash
    html = re.sub(r'Barcha modellar \(\d+\)', f'Barcha modellar ({total_cnt})', html)
    html = re.sub(r'Pro / Pro Max \(\d+\)', f'Pro / Pro Max ({pro_cnt})', html)
    html = re.sub(r'350\$ gacha \(\d+\)', f'350$ gacha ({budget_cnt})', html)
    html = re.sub(r'yangilanadigan \d+ ta mavjud', f'yangilanadigan {total_cnt} ta mavjud', html)
    html = re.sub(r'Jami: <b>\d+ ta</b>', f'Jami: <b>{total_cnt} ta</b>', html)

    # Mahsulot kartochkalarini yangilash
    all_cards = render_cards(available_products)
    
    start_tag = '<div id="product-list" class="product-grid">'
    end_tag = '</div>\n\n      <!-- Pagination System (11-rasim: 12 tadan sahifalash) -->'
    start_idx = html.find(start_tag)
    if start_idx != -1:
        end_idx = html.find(end_tag, start_idx)
        if end_idx != -1:
            html = html[:start_idx + len(start_tag)] + '\n' + all_cards + '\n      ' + html[end_idx:]
        else:
            pattern = r'(<div id="product-list" class="product-grid">)(.*?)(</div>\s*<!-- (?:Pagination|Empty))'
            html = re.sub(pattern, rf'\g<1>\n{all_cards}\n      \g<3>', html, flags=re.DOTALL)

    with open(KATALOG_FILE, 'w', encoding='utf-8') as f:
        f.write(html)

    return True

def sync():
    print("Telegram kanal (@oymaoyy) tekshirilmoqda...")
    try:
        channel_html = fetch_channel_html()
        products = parse_posts(channel_html)
    except Exception as e:
        print(f"Xatolik yuz berdi: {e}")
        return False

    if not products:
        print("Hech qanday post topilmadi.")
        return False

    # Faqat sotuvda mavjud haqiqiy telefonlar (Manzil videosi yoki narxsiz postlar chiqarilmaydi)
    available = []
    for p in products:
        m = p.get('model', '').strip()
        pr = p.get('price', '').strip()
        raw = p.get('raw_text', '').strip().lower()
        if p.get('is_sold'): continue
        if not pr: continue
        if 'manzil' in m.lower() or 'manzil' in raw or 'video' in m.lower(): continue
        if not any(k in m.lower() for k in ['iphone', 'samsung', 'redmi', 'poco', 'pro', 'max', 'mini', 'plus']): continue
        available.append(p)
    print(f"Jami topilgan e'lonlar: {len(products)} ta. Sotuvda mavjud: {len(available)} ta.")

    print("index.html va katalog.html yangilanmoqda...")
    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(products, f, ensure_ascii=False, indent=2)

    update_index_html(available)
    update_katalog_html(available)
    print(f"Muvaffaqiyatli yangilandi! {len(available)} ta mavjud telefon saytga joylandi (Lokal rasmlar bilan).")
    return True

if __name__ == "__main__":
    sync()
