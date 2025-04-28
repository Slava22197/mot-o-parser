import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
import requests
import time
import re
from urllib.parse import urljoin

base_url = "https://mot-o.com"

def get_product_details(product_url, product_name):
    product_resp = requests.get(product_url)
    soup = BeautifulSoup(product_resp.text, 'html.parser')

    images = []
    img_blocks = soup.select('.thumbnails img, .product-left img, .product-additional img')
    for img in img_blocks:
        src = img.get('src')
        if src and src not in images:
            images.append(src)
    if not images:
        images = ['N/A']

    description_tag = soup.select_one('#tab-description')
    description = description_tag.get_text(strip=True) if description_tag else 'N/A'

    model = sku = 'N/A'
    for li in soup.select('ul.list-unstyled li'):
        text = li.get_text()
        if 'Модель' in text:
            model = text.split(':')[-1].strip()
        elif 'Артикул' in text:
            sku = text.split(':')[-1].strip()

    brand_tag = soup.select_one('.product-manufacturer a')
    brand = brand_tag.text.strip() if brand_tag else 'N/A'

    breadcrumbs = soup.select('ul.breadcrumb li a')
    group_name = breadcrumbs[-2].text.strip() if len(breadcrumbs) > 2 else 'Інше'

    return {
        'images': images,
        'description': description,
        'model': model,
        'sku': sku,
        'group': group_name,
        'brand': brand
    }

# Основна структура
root = ET.Element('yml_catalog', date=time.strftime("%Y-%m-%d %H:%M"))
shop = ET.SubElement(root, 'shop')

ET.SubElement(shop, 'name').text = "mot-o.com"
ET.SubElement(shop, 'company').text = "mot-o.com"
ET.SubElement(shop, 'url').text = base_url

currencies = ET.SubElement(shop, 'currencies')
ET.SubElement(currencies, 'currency', id="UAH", rate="1")

categories_block = ET.SubElement(shop, 'categories')
offers = ET.SubElement(shop, 'offers')

# Збір унікальних груп
category_map = {}
category_id_counter = 1
all_products = []

for page in range(1, 1000):
    print(f"📄 Сторінка {page}")
    url = f"{base_url}/zapchasti/?page={page}"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    for card in soup.select('.product-layout .product-thumb'):
        link_tag = card.select_one('.name a')
        product_name = link_tag.text.strip()
        product_url = urljoin(base_url, link_tag['href'])

        details = get_product_details(product_url, product_name)
        all_products.append((details, card, product_url, product_name))

        group = details['group']
        if group not in category_map:
            category_map[group] = category_id_counter
            category_id_counter += 1

    time.sleep(1)

# Створення категорій
for group_name, group_id in category_map.items():
    ET.SubElement(categories_block, 'category', id=str(group_id)).text = group_name

# Створення товарів
for details, card, product_url, product_name in all_products:
    # Визначаємо ID для offer
    clean_id = re.sub(r'\D', '', details['sku'])  # Забираємо все, крім цифр
    offer_id = clean_id if clean_id else str(hash(product_name) % 1000000)

    offer = ET.SubElement(offers, 'offer', id=offer_id)

    ET.SubElement(offer, 'url').text = product_url

    price_tag = card.select_one('.price')
    if price_tag:
        match = re.search(r'\d+(?:[\.,]\d+)?', price_tag.text)
        price = match.group().replace(',', '.') if match else '0'
    else:
        price = '0'
    ET.SubElement(offer, 'price').text = price
    ET.SubElement(offer, 'currencyId').text = "UAH"
    ET.SubElement(offer, 'categoryId').text = str(category_map[details['group']])

    for img in details['images']:
        ET.SubElement(offer, 'picture').text = img

    ET.SubElement(offer, 'vendor').text = details['brand']
    ET.SubElement(offer, 'vendorCode').text = details['sku']
    ET.SubElement(offer, 'model').text = details['model']

    name_combined = f"{details['group']} {product_name}"
    ET.SubElement(offer, 'name').text = name_combined

    description = ET.SubElement(offer, 'description')
    description.text = f"<![CDATA[{details['description']}]]>"

    ET.SubElement(offer, 'available').text = 'true'

tree = ET.ElementTree(root)
tree.write('mot-o_final.xml', encoding='utf-8', xml_declaration=True)
