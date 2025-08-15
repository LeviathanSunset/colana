"""
数据爬虫服务模块
负责从各种API获取代币数据
"""

import requests
import csv
import json
import time
import os
from typing import List, Dict, Optional, Any
from datetime import datetime
from ..models import TokenInfo
from ..utils import safe_float, safe_int, calculate_age_days


class BaseCrawler:
    """基础爬虫类"""

    def __init__(self):
        self.tokens_data: List[Dict[str, Any]] = []
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"
        }

    def get_data(self, url: str, params: Dict = None, max_retries: int = 3) -> Optional[Dict]:
        """通用数据获取方法"""
        for attempt in range(1, max_retries + 1):
            try:
                response = requests.get(url, headers=self.headers, params=params, timeout=15)
                response.raise_for_status()
                return response.json()
            except Exception as e:
                print(f"请求失败 ({attempt}/{max_retries}): {e}")
                if attempt < max_retries:
                    time.sleep(2**attempt)  # 指数退避
                else:
                    print("达到最大重试次数")
                    return None

    def save_to_csv(self, filename: str = None) -> None:
        """保存数据到CSV文件"""
        if not self.tokens_data:
            print("没有数据可保存")
            return

        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            os.makedirs("data/snapshots", exist_ok=True)
            filename = f"data/snapshots/tokens_{timestamp}.csv"

        # 收集所有字段
        all_fields = set()
        for token in self.tokens_data:
            all_fields.update(token.keys())

        fieldnames = list(all_fields)

        try:
            with open(filename, "w", newline="", encoding="utf-8") as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                for token in self.tokens_data:
                    writer.writerow(token)
            print(f"数据已保存到 {filename}")
        except Exception as e:
            print(f"保存CSV失败: {e}")

    def save_to_json(self, filename: str = None) -> None:
        """保存数据到JSON文件"""
        if not self.tokens_data:
            print("没有数据可保存")
            return

        if filename is None:
            os.makedirs("data/snapshots", exist_ok=True)
            filename = f"data/snapshots/tokens_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        try:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(self.tokens_data, f, ensure_ascii=False, indent=2)
            print(f"数据已保存到 {filename}")
        except Exception as e:
            print(f"保存JSON失败: {e}")

    def deduplicate_by_mint(self, keep: int = 1000) -> None:
        """根据mint地址去重"""
        seen = set()
        unique = []

        for token in self.tokens_data:
            mint = token.get("mint")
            if mint and mint not in seen:
                seen.add(mint)
                unique.append(token)
                if len(unique) >= keep:
                    break

        self.tokens_data = unique
        print(f"去重完成，保留 {len(unique)} 个代币")


class PumpFunCrawler(BaseCrawler):
    """Pump.Fun API爬虫"""

    def __init__(self):
        super().__init__()
        self.base_url = "https://frontend-api-v3.pump.fun/coins"
        self.page_size = 50
        self.headers.update({"Referer": "https://pump.fun/"})

    def get_page_data(self, offset: int = 0) -> List[Dict]:
        """获取单页数据"""
        params = {
            "offset": offset,
            "limit": self.page_size,
            "sort": "market_cap",
            "includeNsfw": "true",
            "order": "DESC",
        }

        print(f"请求第 {offset // self.page_size + 1} 页数据...")

        data = self.get_data(self.base_url, params)
        if data and isinstance(data, list):
            return data
        else:
            print(f"返回数据格式异常: {type(data)}")
            return []

    def crawl_all_pages(self, max_tokens: int = 1000) -> None:
        """爬取所有页面数据"""
        print(f"开始爬取 Pump.Fun 代币数据，目标: {max_tokens} 个代币")

        total_tokens = 0
        page = 0

        while total_tokens < max_tokens:
            offset = page * self.page_size
            page_data = self.get_page_data(offset)

            if not page_data:
                print(f"第 {page + 1} 页无数据，停止爬取")
                break

            # 限制数量
            remaining = max_tokens - total_tokens
            if len(page_data) > remaining:
                page_data = page_data[:remaining]

            self.tokens_data.extend(page_data)
            total_tokens += len(page_data)

            print(f"第 {page + 1} 页: 获得 {len(page_data)} 条数据，总计 {total_tokens} 条")

            if total_tokens >= max_tokens:
                break

            page += 1
            time.sleep(1)  # 避免请求过快

        print(f"爬取完成，共获得 {len(self.tokens_data)} 条代币数据")

    def to_token_info_list(self) -> List[TokenInfo]:
        """转换为TokenInfo对象列表"""
        tokens = []
        for data in self.tokens_data:
            try:
                token = TokenInfo(
                    mint=data.get("mint", ""),
                    name=data.get("name", ""),
                    symbol=data.get("symbol", ""),
                    usd_market_cap=safe_float(data.get("usd_market_cap", 0)),
                    created_timestamp=safe_int(data.get("created_timestamp", 0)),
                    age_days=calculate_age_days(data.get("created_timestamp", 0)),
                )
                tokens.append(token)
            except Exception as e:
                print(f"转换TokenInfo失败: {e}")
                continue

        return tokens


class OKXCrawler(BaseCrawler):
    """OKX API爬虫"""

    def __init__(self):
        super().__init__()
        self.base_url = "https://www.okx.com/api/v5"

    def get_token_holders(self, token_address: str, limit: int = 100) -> List[Dict]:
        """获取代币持有者信息"""
        url = f"{self.base_url}/explorer/token/token-holder-list"
        params = {
            "chainId": "501",  # Solana
            "tokenContractAddress": token_address,
            "limit": limit,
            "page": "1",
        }

        data = self.get_data(url, params)
        if data and data.get("code") == "0":
            return data.get("data", [])
        return []

    def get_address_tokens(self, address: str) -> List[Dict]:
        """获取地址持有的代币列表"""
        url = f"{self.base_url}/explorer/address/token-balance"
        params = {"chainId": "501", "address": address}

        data = self.get_data(url, params)
        if data and data.get("code") == "0":
            return data.get("data", [])
        return []


class CrawlerFactory:
    """爬虫工厂类"""

    @staticmethod
    def create_crawler(crawler_type: str) -> BaseCrawler:
        """创建爬虫实例"""
        if crawler_type.lower() == "pumpfun":
            return PumpFunCrawler()
        elif crawler_type.lower() == "okx":
            return OKXCrawler()
        else:
            raise ValueError(f"不支持的爬虫类型: {crawler_type}")


# 向后兼容的类别名
PumpFunAPICrawler = PumpFunCrawler
