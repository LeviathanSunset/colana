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
from ..utils.data_manager import DataManager
from ..utils.logger import get_logger


class BaseCrawler:
    """基础爬虫类"""

    def __init__(self):
        self.logger = get_logger("crawler")
        self.tokens_data: List[Dict[str, Any]] = []
        self.data_manager = DataManager()
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"
        }
        self.logger.debug("🔧 BaseCrawler 初始化完成")

    def get_data(self, url: str, params: Dict = None, max_retries: int = 3) -> Optional[Dict]:
        """通用数据获取方法"""
        self.logger.debug(f"🌐 发起请求: {url}")
        if params:
            self.logger.debug(f"📋 请求参数: {params}")
            
        for attempt in range(1, max_retries + 1):
            try:
                start_time = time.time()
                response = requests.get(url, headers=self.headers, params=params, timeout=15)
                request_time = time.time() - start_time
                
                response.raise_for_status()
                data = response.json()
                
                self.logger.info(f"✅ 请求成功: {url} (耗时: {request_time:.2f}s, 状态: {response.status_code})")
                self.logger.debug(f"📊 响应数据大小: {len(response.content)} bytes")
                
                return data
                
            except requests.exceptions.Timeout:
                self.logger.warning(f"⏰ 请求超时 ({attempt}/{max_retries}): {url}")
            except requests.exceptions.ConnectionError:
                self.logger.warning(f"🔌 连接错误 ({attempt}/{max_retries}): {url}")
            except requests.exceptions.HTTPError as e:
                self.logger.error(f"📡 HTTP错误 ({attempt}/{max_retries}): {e.response.status_code} - {url}")
            except Exception as e:
                self.logger.error(f"❌ 请求失败 ({attempt}/{max_retries}): {e}")
                
            if attempt < max_retries:
                retry_delay = 2**attempt
                self.logger.info(f"⏳ 等待 {retry_delay} 秒后重试...")
                time.sleep(retry_delay)  # 指数退避
            else:
                self.logger.error(f"❌ 达到最大重试次数，请求失败: {url}")
                return None

    def save_to_csv(self, filename: str = None) -> None:
        """保存数据到CSV文件"""
        if not self.tokens_data:
            self.logger.warning("⚠️ 没有数据可保存")
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
        
        self.logger.info(f"💾 开始保存数据到CSV: {filename}")
        self.logger.debug(f"📊 数据统计: {len(self.tokens_data)} 条记录, {len(fieldnames)} 个字段")

        try:
            start_time = time.time()
            with open(filename, "w", newline="", encoding="utf-8") as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                for token in self.tokens_data:
                    writer.writerow(token)
            
            save_time = time.time() - start_time
            file_size = os.path.getsize(filename) / 1024  # KB
            self.logger.info(f"✅ CSV保存成功: {filename} (耗时: {save_time:.2f}s, 大小: {file_size:.1f}KB)")
            
        except Exception as e:
            self.logger.exception(f"❌ 保存CSV失败: {e}")

    def save_to_json(self, filename: str = None) -> None:
        """保存数据到JSON文件"""
        if not self.tokens_data:
            self.logger.warning("⚠️ 没有数据可保存")
            return

        if filename is None:
            filename = f"tokens_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        try:
            filepath = self.data_manager.get_file_path("csv_data", filename)
            self.logger.info(f"💾 开始保存数据到JSON: {filepath}")
            
            start_time = time.time()
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(self.tokens_data, f, ensure_ascii=False, indent=2)
            
            save_time = time.time() - start_time
            file_size = os.path.getsize(filepath) / 1024  # KB
            self.logger.info(f"✅ JSON保存成功: {filepath} (耗时: {save_time:.2f}s, 大小: {file_size:.1f}KB)")
            
        except Exception as e:
            self.logger.exception(f"❌ 保存JSON失败: {e}")

    def deduplicate_by_mint(self, keep: int = 1000) -> None:
        """根据mint地址去重"""
        original_count = len(self.tokens_data)
        self.logger.info(f"🔄 开始去重处理: 原始数据 {original_count} 条，目标保留 {keep} 条")
        
        seen = set()
        unique = []

        for token in self.tokens_data:
            mint = token.get("mint")
            if mint and mint not in seen:
                seen.add(mint)
                unique.append(token)
                if len(unique) >= keep:
                    break

        removed_count = original_count - len(unique)
        self.tokens_data = unique
        self.logger.info(f"✅ 去重完成: 保留 {len(unique)} 个代币，移除 {removed_count} 个重复项")


class PumpFunCrawler(BaseCrawler):
    """Pump.Fun API爬虫"""

    def __init__(self):
        super().__init__()
        self.base_url = "https://frontend-api-v3.pump.fun/coins"
        self.page_size = 50
        self.headers.update({"Referer": "https://pump.fun/"})
        self.logger.info(f"🔧 PumpFunCrawler 初始化完成，页面大小: {self.page_size}")

    def get_page_data(self, offset: int = 0) -> List[Dict]:
        """获取单页数据"""
        params = {
            "offset": offset,
            "limit": self.page_size,
            "sort": "market_cap",
            "includeNsfw": "true",
            "order": "DESC",
        }

        page_num = offset // self.page_size + 1
        self.logger.info(f"📖 正在请求第 {page_num} 页数据 (offset: {offset})")

        data = self.get_data(self.base_url, params)
        if data and isinstance(data, list):
            self.logger.debug(f"✅ 第 {page_num} 页获取成功: {len(data)} 条数据")
            return data
        else:
            self.logger.error(f"❌ 第 {page_num} 页返回数据格式异常: {type(data)}")
            return []

    def crawl_all_pages(self, max_tokens: int = 1000) -> None:
        """爬取所有页面数据"""
        self.logger.info(f"🚀 开始爬取 Pump.Fun 代币数据，目标: {max_tokens} 个代币")

        total_tokens = 0
        page = 0
        consecutive_failures = 0
        max_failures = 3

        while total_tokens < max_tokens:
            offset = page * self.page_size
            page_data = self.get_page_data(offset)

            if not page_data:
                consecutive_failures += 1
                self.logger.warning(f"⚠️ 第 {page + 1} 页无数据，连续失败次数: {consecutive_failures}")
                
                if consecutive_failures >= max_failures:
                    self.logger.warning(f"❌ 连续 {max_failures} 页无数据，停止爬取")
                    break
                    
                page += 1
                time.sleep(2)  # 增加等待时间
                continue
            
            consecutive_failures = 0  # 重置失败计数

            # 限制数量
            remaining = max_tokens - total_tokens
            if len(page_data) > remaining:
                page_data = page_data[:remaining]
                self.logger.debug(f"📏 数量限制: 只取前 {remaining} 条数据")

            self.tokens_data.extend(page_data)
            total_tokens += len(page_data)

            self.logger.info(f"📄 第 {page + 1} 页: 获得 {len(page_data)} 条数据，累计 {total_tokens} 条")

            if total_tokens >= max_tokens:
                self.logger.info(f"🎯 已达到目标数量 {max_tokens}，停止爬取")
                break

            page += 1
            time.sleep(1)  # 避免请求过快

        self.logger.info(f"✅ 爬取完成，共获得 {len(self.tokens_data)} 条代币数据")

    def to_token_info_list(self) -> List[TokenInfo]:
        """转换为TokenInfo对象列表"""
        self.logger.info(f"🔄 开始转换 {len(self.tokens_data)} 条数据为TokenInfo对象")
        
        tokens = []
        failed_count = 0
        
        for i, data in enumerate(self.tokens_data):
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
                
                if (i + 1) % 100 == 0:
                    self.logger.debug(f"🔄 已转换 {i + 1}/{len(self.tokens_data)} 条数据")
                    
            except Exception as e:
                failed_count += 1
                self.logger.error(f"❌ 转换TokenInfo失败 (第{i+1}条): {e}")
                continue

        self.logger.info(f"✅ 转换完成: 成功 {len(tokens)} 条，失败 {failed_count} 条")
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
