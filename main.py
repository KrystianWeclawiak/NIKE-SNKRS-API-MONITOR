import requests
import time
import random
import sys
import json
import os
from datetime import datetime, timezone
from config import Monitor_Discord_Embed_Colors, Monitor_Discord_Username, Monitor_Discord_Avatar_URL, \
    Monitor_Discord_Channel_Webhooks_List, Monitor_Nike_API, Monitor_Discord_Embed_Footer_Text, \
    logger, Monitor_Discord_STOCK_DATE_SIZE_Change


class SnkrsMonitor:
    def __init__(self):
        self.username = Monitor_Discord_Username
        self.avatar_url = Monitor_Discord_Avatar_URL
        self.webhooks = Monitor_Discord_Channel_Webhooks_List
        self.api_url = Monitor_Nike_API
        self.colors = Monitor_Discord_Embed_Colors
        self.user_agents = self.load_user_agents()
        self.session = requests.Session()

        self.inventory_file = "inventory.json"
        self.inventory = self.load_inventory()

    def load_user_agents(self):
        try:
            with open("users.txt", "r") as f:
                return [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            return [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"]


    def load_inventory(self):
        if not os.path.exists(self.inventory_file):
            logger.info("inventory.json not found. Creating a new file on first save.")
            return {}

        try:
            with open(self.inventory_file, "r", encoding='utf-8') as f:
                data = json.load(f)
                logger.info(f"Loaded {len(data)} products from inventory.")
                return data
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Error reading inventory.json: {e}. Starting with an empty database.")
            return {}

    def save_inventory(self):
        try:
            with open(self.inventory_file, "w", encoding='utf-8') as f:
                json.dump(self.inventory, f, indent=4)
        except Exception as e:
            logger.error(f"Failed to save inventory to file: {e}")

    def get_headers(self):
        return {
            'accept': '*/*',
            'appid': 'com.nike.commerce.snkrs.web',
            'nike-api-caller-id': 'nike:snkrs:web:1.0',
            'origin': 'https://www.nike.com',
            'referer': 'https://www.nike.com/',
            'user-agent': random.choice(self.user_agents),
            'Cache-Control': 'no-cache',
        }

    def fetch_products(self):
        try:
            response = self.session.get(self.api_url, headers=self.get_headers(), timeout=15)
            if response.status_code == 200:
                return response.json().get('objects', [])
            else:
                logger.error(f"Nike API Error: {response.status_code}")
        except Exception as e:
            logger.error(f"Exception during data fetching: {e}")
        return []

    def find_image(self, item, sku):
        try:
            nodes = item.get('publishedContent', {}).get('nodes', [])
            for node in nodes:
                internal_name = node.get('properties', {}).get('internalName', '')
                if sku and sku in internal_name:
                    return node.get('nodes', [{}])[0].get('properties', {}).get('portraitURL', self.avatar_url)

            return item.get('publishedContent', {}).get('properties', {}).get('coverCard', {}).get('properties',
                                                                                                   {}).get(
                'squarishURL', self.avatar_url)
        except:
            return self.avatar_url

    def parse_sizes_and_stock(self, one_item):
        sizes_text_list = []
        gtin_stock_map = {}

        for gtin_info in one_item.get('availableGtins', []):
            gtin_stock_map[gtin_info.get('gtin')] = gtin_info.get('level')

        for sku_info in one_item.get('skus', []):
            gtin = sku_info.get('gtin')
            if gtin in gtin_stock_map:
                try:
                    size_val = sku_info.get('countrySpecifications', [{}])[0].get('localizedSize', 'N/A')
                    level = gtin_stock_map.get(gtin, 'UNKNOWN')
                    sizes_text_list.append(f"{size_val}  [{level}]")
                except:
                    continue

        return "\n".join(sizes_text_list), gtin_stock_map

    def send_discord_webhook(self, event_type, p_data, extra_info=None):
        titles = Monitor_Discord_STOCK_DATE_SIZE_Change

        color = self.colors.get(event_type, 15277667)
        date_str = p_data.get('start_date', 'TBA')
        if event_type == 'DATE' and extra_info:
            date_str = f"~~{extra_info}~~ -> **{p_data.get('start_date')}**"

        payload = {
            'username': self.username,
            'avatar_url': self.avatar_url,
            'embeds': [{
                'title': titles.get(event_type, 'SNKRS Update'),
                'color': color,
                'image': {'url': p_data.get('image', self.avatar_url)},
                'footer': {'text': Monitor_Discord_Embed_Footer_Text, 'icon_url': self.avatar_url},
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'fields': [
                    {'name': 'Model', 'value': p_data.get('title', 'No Name'), 'inline': False},
                    {'name': 'SKU', 'value': f"`{p_data.get('sku', 'N/A')}`", 'inline': True},
                    {'name': 'Method', 'value': p_data.get('method', 'N/A'), 'inline': True},
                    {'name': 'Date', 'value': date_str, 'inline': True},
                    {'name': 'Available Sizes', 'value': p_data.get('size_str') or "No Data", 'inline': False},
                    {'name': 'Links',
                     'value': f"[APPLICATION](http://atc.yeet.ai/redirect?link=SNKRS://product/{p_data.get('sku', '')})",
                     'inline': False}
                ]
            }]
        }

        for url in self.webhooks:
            try:
                res = self.session.post(url, json=payload, timeout=10)
                if res.status_code == 204:
                    logger.info(f"Webhook sent successfully: {p_data.get('title')}")
                else:
                    logger.error(f"Discord Error {res.status_code}: {res.text}")
            except Exception as e:
                logger.error(f"Connection error with Discord: {e}")

    def process_item(self, parent_item):
        product_info_list = parent_item.get('productInfo', [])

        for one_item in product_info_list:
            if not one_item.get('availability', {}).get('available', False):
                continue

            start_date = one_item.get('launchView', {}).get('startEntryDate', '')[:10]
            if not start_date: continue

            merch = one_item.get('merchProduct', {})
            pid = merch.get('id')
            sku = merch.get('styleColor')

            if not pid: continue

            size_str, gtin_map = self.parse_sizes_and_stock(one_item)

            p_data = {
                'title': one_item.get('productContent', {}).get('title', 'No Name'),
                'method': one_item.get('launchView', {}).get('method', 'FLOW'),
                'status': merch.get('status', 'N/A'),
                'start_date': start_date,
                'size_str': size_str,
                'sku': sku,
                'image': self.find_image(parent_item, sku)
            }

            if pid not in self.inventory:
                logger.info(f"New product detected: {p_data.get('title')}")
                self.send_discord_webhook('NEW', p_data)
                self.inventory[pid] = {'date': start_date, 'stock': gtin_map}
                self.save_inventory()
            else:
                cached_data = self.inventory.get(pid, {})

                if cached_data.get('date') != start_date:
                    old_date = cached_data.get('date')
                    self.inventory[pid]['date'] = start_date
                    self.send_discord_webhook('DATE', p_data, extra_info=old_date)
                    self.save_inventory()

                elif cached_data.get('stock') != gtin_map:
                    self.inventory[pid]['stock'] = gtin_map
                    self.send_discord_webhook('STOCK', p_data)
                    self.save_inventory()

    def run(self):
        logger.info("Monitor started")
        while True:
            products = self.fetch_products()
            if products:
                for product in products:
                    self.process_item(product)

            logger.info(f"Loop finished. Tracking {len(self.inventory)} products.")
            time.sleep(150)


if __name__ == "__main__":
    try:
        monitor = SnkrsMonitor()
        monitor.run()
    except KeyboardInterrupt:
        logger.info("Monitor stopped by user.")
        sys.exit()
    except Exception as e:
        logger.error(f"Unknown error in main loop: {e}")
