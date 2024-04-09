import requests
import sys
from bs4 import BeautifulSoup
import json
from datetime import datetime

def extract_id_from_url(url):
	try:
		return url.split('/')[-1].split('.')[0]
	except Exception as e:
		print(f"Error extracting ID from URL '{url}': {e}")
		return None

def extract_news_items(html_content):
	try:
		soup = BeautifulSoup(html_content, 'html.parser')
		news_items = []
		seen_ids = set()

		for link in soup.find_all('a', class_='news-item__title'):
			news_id = extract_id_from_url(link.get('href'))
			if news_id in seen_ids or not news_id:
				continue
			seen_ids.add(news_id)

			news_item_soup = link.find_parent(class_='news-item')
			img_tag = news_item_soup.find('img') if news_item_soup else None
			image = img_tag.get('data-src', img_tag.get('src')) if img_tag else None
			category = news_item_soup.find('div', class_='news-item__cat').get_text(strip=True) if news_item_soup and news_item_soup.find('div', class_='news-item__cat') else None
			time = news_item_soup.find('div', class_='news-item__time').get_text(strip=True) if news_item_soup and news_item_soup.find('div', class_='news-item__time') else None

			news_items.append({
				'id': news_id,
				'image': image,
				'link_href': link.get('href'),
				'link_text': link.get_text(strip=True),
				'category': category,
				'time': time
			})

		return news_items, seen_ids
	except Exception as e:
		print(f"Error extracting news items: {e}")
		return [], set()

def get_news_content(domain, path, params={}):
	try:
		url = f'https://{domain}{path}'
		headers = {
			'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:124.0) Gecko/20100101 Firefox/124.0',
			'Accept': '*/*',
			'Accept-Language': 'en-US,en;q=0.5'
		}
		response = requests.get(url, headers=headers, params=params)
		response.raise_for_status()
		return response.json()
	except requests.RequestException as e:
		print(f"Network error: {e}")
		return {}
	except json.JSONDecodeError as e:
		print(f"Error parsing JSON: {e}")
		return {}

def main(domain):
	try:
		print(f"Fetching initial data for domain: {domain}")
		initial_data = get_news_content(domain, '/api/blocks')
		blocks = initial_data.get('blocks', [])
		all_block = next((block for block in blocks if block['key'] == 'all'), None)
		if not all_block:
			print('No block with key "all" found.')
			return

		news_items, seen_ids = extract_news_items(all_block['news'])
		print(f"Initial news items fetched: {len(news_items)}")

		last_id = news_items[-1]['id'] if news_items else None
		print(f"Last ID from initial fetch: {last_id}")

		while True:
			print(f"Attempting to fetch more news items starting from ID: {last_id}")
			next_data = get_news_content(domain, '/api/cat', params={'key': 'all', 'id': last_id, 'type': 'block'})
			if not next_data.get('news'):
				print("No more news data in the response.")
				break

			next_news_items, new_ids = extract_news_items(next_data.get('news', ''))
			if not next_news_items:
				print("No additional news items found.")
				break

			news_items.extend(next_news_items)
			seen_ids.update(new_ids)
			last_id = next_news_items[-1]['id'] if next_news_items else None
			print(f"New last ID: {last_id}, Total news items fetched: {len(news_items)}")

		filename = f"{domain}_home_{datetime.now().strftime('%d-%m-%y')}.json"
		with open(filename, 'w') as file:
			json.dump(news_items, file, indent=4)
		print(f"Data saved to {filename}")
	except Exception as e:
		print(f"An error occurred: {e}")

if __name__ == "__main__":
	if len(sys.argv) < 2:
		print("Usage: python3 pravda-extract.py [DOMAIN]")
	else:
		domain = sys.argv[1]
		main(domain)
