import requests
import csv
import json
import time
import os

class PumpFunAPICrawler:
    def __init__(self):
        self.tokens_data = []
        self.base_url = "https://frontend-api-v3.pump.fun/coins"
        self.page_size = 50 
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
            "Referer": "https://pump.fun/"
            # 如遇403可加Cookie
            # "Cookie": "_ga=...; cf_clearance=...; ..."
        }

    def get_page_data(self, offset=0, max_retries=3, retry_delay=3):
        params = {
            "offset": offset,
            "limit": self.page_size,
            "sort": "market_cap",
            "includeNsfw": "true",
            "order": "DESC"
        }
        print(f"请求: {self.base_url} {params}")
        for attempt in range(1, max_retries + 1):
            try:
                resp = requests.get(self.base_url, headers=self.headers, params=params, timeout=15)
                resp.raise_for_status()
                data = resp.json()
                if isinstance(data, list):
                    return data
                else:
                    print("返回数据不是列表，实际内容：", data)
                    return []
            except Exception as e:
                print(f"请求出错: {e} (第{attempt}次尝试)")
                if attempt < max_retries:
                    time.sleep(retry_delay)
                else:
                    print("已达最大重试次数，放弃该页。")
                    return []

    def crawl_all_pages(self, max_tokens=1000):
        print(f"开始API爬取Pump.fun代币信息，最多{max_tokens}个代币")
        total_tokens = 0
        page = 0
        while total_tokens < max_tokens:
            offset = page * self.page_size
            page_data = self.get_page_data(offset)
            if not page_data:
                print(f"第{page+1}页无数据，停止爬取")
                break
            remaining = max_tokens - total_tokens
            if len(page_data) > remaining:
                page_data = page_data[:remaining]
            self.tokens_data.extend(page_data)
            total_tokens += len(page_data)
            print(f"第{page+1}页，获得{len(page_data)}条数据，总计{total_tokens}条")
            if total_tokens >= max_tokens:
                break
            page += 1
            time.sleep(1)  # 防止请求过快
        print(f"爬取完成，共获得{len(self.tokens_data)}条代币数据")

    def deduplicate_by_mint(self, keep=1000):
        seen = set()
        unique = []
        for token in self.tokens_data:
            mint = token.get('mint')
            if mint and mint not in seen:
                seen.add(mint)
                unique.append(token)
            if len(unique) >= keep:
                break
        self.tokens_data = unique

    def save_to_csv(self, filename=None):
        if not self.tokens_data:
            print("没有数据可保存")
            return
        import datetime
        if filename is None:
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            # 保存到snapshots目录
            os.makedirs('snapshots', exist_ok=True)
            filename = os.path.join('snapshots', f"pumpfun_tokens_api_{timestamp}.csv")
        # 自动收集所有字段
        all_fields = set()
        for token in self.tokens_data:
            all_fields.update(token.keys())
        fieldnames = list(all_fields)
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for token in self.tokens_data:
                writer.writerow(token)
        print(f"数据已保存到 {filename}")

    def save_to_json(self, filename=None):
        if not self.tokens_data:
            print("没有数据可保存")
            return
        if filename is None:
            os.makedirs('snapshots', exist_ok=True)
            filename = os.path.join('snapshots', "pumpfun_tokens_api.json")
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.tokens_data, f, ensure_ascii=False, indent=2)
        print(f"数据已保存到 {filename}")

def main():
    crawler = PumpFunAPICrawler()
    crawler.crawl_all_pages(max_tokens=1050)
    crawler.deduplicate_by_mint(keep=1000)
    crawler.save_to_csv()

if __name__ == "__main__":
    main()