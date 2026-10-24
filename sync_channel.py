"""
OYMAOY.UZ — Telegram Channel Real-time Multi-Page Sync Script
Har 30 daqiqada yoki qo'lda ishga tushganda butun kanal tarixidagi
barcha mavjud (sotilmagan) telefonlarni to'liq qamrab oladi.
"""

import os
import re
import json
import urllib.request
import urllib.parse
import ssl
import time
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

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": CHANNEL_URL
}

def fetch_all_channel_messages(max_pages=8):
    """Kanalning bir nechta sahifalarini aylanib, barcha xabarlarni yig'adi."""
    all_messages = {}
    current_url = CHANNEL_URL

    for page in range(max_pages):
        try:
            req = urllib.request.Request(current_url, headers=HEADERS)
            with urllib.request.urlopen(req, context=ctx, timeout=12) as resp:
                html = resp.read().decode("utf-8")
        except Exception as e:
            print(f"Sahifa {page+1} yuklashda xatolik ({current_url}): {e}")
            break

        soup = BeautifulSoup(html, "html.parser")
        messages = soup.find_all("div", class_="tgme_widget_message")
        if not messages:
            break

        for msg in messages:
            raw_id = msg.get("data-post", "")
            if raw_id and raw_id not in all_messages:
                all_messages[raw_id] = msg

        more_elem = soup.find("a", class_="tme_messages_more")
        if more_elem and more_elem.get("data-before"):
            before_id = more_elem.get("data-before")
            current_url = f"{CHANNEL_URL}?before={before_id}"
        else:
            break

    print(f"Jami kanal xabarlari yuklandi: {len(all_messages)} ta ({page+1} sahifa).")
    return list(all_messages.values())

def download_image(photo_url, msg_id):
    if not photo_url or not msg_id:
        return ""
    safe_name = msg_id.replace("/", "_") + ".jpg"
    file_path = os.path.join(IMAGES_DIR, safe_name)

    # Agar allaqachon yuklangan bo'lsa va hajmi > 2000 bayt bo'lsa, qayta yuklamaymiz
    if os.path.exists(file_path) and os.path.getsize(file_path) > 2000:
        return f"images/{safe_name}"

    for attempt in range(3):
        try:
            req = urllib.request.Request(photo_url, headers=HEADERS)
            with urllib.request.urlopen(req, context=ctx, timeout=10) as r:
                data = r.read()
                if len(data) > 1000:
                    with open(file_path, "wb") as f:
                        f.write(data)
                    print(f"Rasm yuklandi: images/{safe_name} ({len(data)} bayt)")
                    return f"images/{safe_name}"
        except Exception as e:
            if attempt == 2:
                print(f"Rasm yuklashda xatolik ({safe_name}): {e}")
            time.sleep(1)

    if os.path.exists(file_path) and os.path.getsize(file_path) > 500:
        return f"images/{safe_name}"
    return photo_url

def extract_price(text):
    m = re.search(r'(?:sotuv\s*narxi?|narxi?)\s*[:\-]?\s*(\d+(?:[.,]\d+)?\s*(?:\$|usd|so[\'’`]?m)?)', text, re.I)
    if not m:
        m = re.search(r'(\d+(?:[.,]\d+)?\s*(?:\$|usd))', text, re.I)
    if m:
        val = m.group(1).strip()
        val = val.replace('.00', '').replace(',00', '')
        if not val.endswith('$') and 'usd' not in val.lower() and 'som' not in val.lower():
            val += '$'
        return val
    return ''

def parse_posts(messages):
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
        condition = cond_match.group(1).strip() if cond_match else "A'lo"

        # Narx (aniq va xatosiz)
        price = extract_price(text)

        # Sotilganlik
        is_sold = bool(re.search(r'(sotildi|baraka|❌|🔴)', text, re.I))

        # ID
        raw_id = msg.get("data-post", "")
        msg_id = raw_id.split("/")[-1] if "/" in raw_id else raw_id

        # Rasm
        photo = ""
        photo_elem = msg.find("a", class_="tgme_widget_message_photo_wrap")
        if photo_elem and photo_elem.get("style"):
            style = photo_elem["style"]
            url_match = re.search(r"background-image:url\('([^']+)'\)", style)
            if url_match:
                photo = url_match.group(1)

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
            "is_sold": is_sold,
            "photo": photo,
            "local_photo": local_photo,
            "raw_text": text
        })

    # Eng yangi postlar yuqorida turishi uchun ID bo'yicha saralash
    products.sort(key=lambda p: int(p['id']) if p['id'].isdigit() else 0, reverse=True)
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
        
        photo = p.get('local_photo') or p.get('photo') or ('https://placehold.co/600x800/00182a/2997ff?text=' + urllib.parse.quote(model))

        order_text = f"Salom, oymaoy.uz saytidan ko'rdim. {model} ({memory}, narxi: {price}) bo'yicha ma'lumot olmoqchiman."
        encoded_order = urllib.parse.quote(order_text)

        cats = ['available']
        if 'pro' in model.lower():
            cats.append('promax')
        try:
            pr = float(re.sub(r'[^0-9.]', '', price))
            if pr > 0 and pr <= 350:
                cats.append('budget')
        except:
            pass

        search_str = f"{model} {memory} {battery} {color} {price}".lower()

        card = f'''      <div class="product-card" data-cats="{' '.join(cats)}" data-search="{search_str}">
        <div class="product-img-box">
          <img src="{photo}" alt="{model}" loading="lazy" onerror="this.onerror=null;this.src='https://placehold.co/600x800/00182a/2997ff?text={urllib.parse.quote(model)}';">
          <span class="badge badge-sale">Mavjud</span>
        </div>
        <div class="product-body">
          <div class="product-title">{model}</div>
          <div class="product-specs">
            <span class="spec-tag">{memory or "Asl"}</span>
            <span class="spec-tag">🔋 {battery or "100%"}</span>
            <span class="spec-tag">{color or "Titanium"}</span>
          </div>
          <div class="product-price-row">
            <div>
              <div class="price-val">{price}</div>
              <div class="price-sub">Muddatli to'lov mavjud</div>
            </div>
            <a href="https://t.me/oymaoy_admin?text={encoded_order}" target="_blank" class="buy-btn">Band qilish</a>
          </div>
        </div>
      </div>'''
        cards_html.append(card)

    return "\n".join(cards_html)

def update_index_html(available_products):
    if not os.path.exists(HTML_FILE):
        print(f"Xato: {HTML_FILE} fayli topilmadi.")
        return False

    with open(HTML_FILE, 'r', encoding='utf-8') as f:
        html = f.read()

    new_cards = render_cards(available_products[:6])
    
    start_tag = '<div id="product-list" class="product-grid">'
    end_tag = '</div>\n\n      <!-- 4-rasim: Barcha modellarni ko\'rish tugmasi -->'
    
    start_idx = html.find(start_tag)
    if start_idx != -1:
        end_idx = html.find(end_tag, start_idx)
        if end_idx != -1:
            html = html[:start_idx + len(start_tag)] + '\n' + new_cards + '\n      ' + html[end_idx:]
        else:
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

    # JavaScript sintaksis xatolarini to'g'irlash
    html = html.replace("countLabel.innerHTML = 'Jami: <b>' + totalMatched + ' ta</b> telefon ko'rsatilmoqda';", 'countLabel.innerHTML = "Jami: <b>" + totalMatched + " ta</b> telefon ko\'rsatilmoqda";')
    html = html.replace("countLabel.innerHTML = 'Ko'rsatilmoqda: <b>' + startItem + '–' + endItem + '</b> / jami <b>' + totalMatched + ' ta</b>';", 'countLabel.innerHTML = "Ko\'rsatilmoqda: <b>" + startItem + " – " + endItem + "</b> / jami <b>" + totalMatched + " ta</b>";')

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

    # Paginatsiya tugmalarini dinamik render qilish skripti mavjudligini ta'minlash
    if "function renderPaginationButtons" not in html:
        # Paginatsiya yaratish funksiyasini qo'shish
        pag_script = """
function renderPaginationButtons(totalPages) {
  var paginationEl = document.getElementById('katalog-pagination');
  if (!paginationEl) return;
  if (totalPages <= 1) {
    paginationEl.style.display = 'none';
    paginationEl.innerHTML = '';
    return;
  }
  paginationEl.style.display = 'flex';
  var pagHtml = '';
  pagHtml += '<button class="page-btn" onclick="goToPage(' + (currentPage - 1) + ')"' + (currentPage === 1 ? ' disabled' : '') + '>← Oldingi</button>';
  for (var p = 1; p <= totalPages; p++) {
    pagHtml += '<button class="page-btn' + (p === currentPage ? ' active' : '') + '" onclick="goToPage(' + p + ')">' + p + '</button>';
  }
  pagHtml += '<button class="page-btn" onclick="goToPage(' + (currentPage + 1) + ')"' + (currentPage === totalPages ? ' disabled' : '') + '>Keyingi →</button>';
  paginationEl.innerHTML = pagHtml;
}
"""
        html = html.replace("function goToPage(page)", pag_script + "\nfunction goToPage(page)")
        html = re.sub(r'applyFilters\(\);\s*</script>', 'renderPaginationButtons(totalPages);\n}\napplyFilters();\n</script>', html)
    else:
        # Agar funksiya bor bo'lsa, applyFilters oxirida chaqirilishini tekshirish
        pass

    with open(KATALOG_FILE, 'w', encoding='utf-8') as f:
        f.write(html)

    return True

def sync():
    print("Telegram kanal (@oymaoyy) barcha sahifalari bo'yicha tekshirilmoqda...")
    try:
        messages = fetch_all_channel_messages(max_pages=8)
        products = parse_posts(messages)
    except Exception as e:
        print(f"Xatolik yuz berdi: {e}")
        return False

    if not products:
        print("Hech qanday post topilmadi.")
        return False

    # Faqat sotuvda mavjud haqiqiy telefonlar
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

    print(f"Jami kanal xabarlaridan topilgan: {len(products)} ta.")
    print(f"Sotuvda mavjud haqiqiy telefonlar: {len(available)} ta.")

    print("index.html va katalog.html yangilanmoqda...")
    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(products, f, ensure_ascii=False, indent=2)

    update_index_html(available)
    update_katalog_html(available)
    print(f"Muvaffaqiyatli yangilandi! Barcha {len(available)} ta mavjud telefon saytga to'liq joylandi.")
    return True

if __name__ == "__main__":
    sync()
