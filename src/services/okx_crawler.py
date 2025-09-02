#!/usr/bin/env python3
"""
简化的OKX Web3爬虫 - 专门为Telegram Bot使用
只获取大户持有的代币排行榜
"""

import requests
import json
import time
import random
import os
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import List, Dict, Optional
from ..utils.data_manager import DataManager
from ..utils.logger import get_logger

# SOL原生代币的合约地址
SOL_TOKEN_ADDRESS = "So11111111111111111111111111111111111111111"

# 稳定币地址列表（Solana主网）
STABLECOIN_ADDRESSES = {
    "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
    "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",  # USDT
    "4zMMC9srt5Ri5X14GAgXhaHii3GnPAEERYPJgZJDncDU",  # USDC (old)
    "7WXaHLjahp8BZq7e9jyshW4Bsg4GnDfLU9aJ7BWPq8YG",  # USD
    "7dHbWXmci3dT8UFYWYZweBLXgycu7Y3iL6trKn1Y7ARj",  # stSOL (质押SOL)
}

# SOL和稳定币地址合集
SOL_AND_STABLECOINS = {SOL_TOKEN_ADDRESS} | STABLECOIN_ADDRESSES

# 全局分析缓存，用于存储分析结果以供按钮回调使用
analysis_cache = {}

# 缓存管理配置
CACHE_TTL = 3600  # 缓存1小时
_cache_cleanup_started = False


def start_cache_cleanup():
    """启动缓存清理线程（全局单例）"""
    global _cache_cleanup_started
    if not _cache_cleanup_started:
        import threading
        cleanup_thread = threading.Thread(target=_cache_cleanup_worker, daemon=True)
        cleanup_thread.start()
        _cache_cleanup_started = True
        print("🧹 全局缓存清理线程已启动")


def _cache_cleanup_worker():
    """缓存清理工作线程"""
    import time
    while True:
        try:
            current_time = time.time()
            expired_keys = []
            
            for key, data in analysis_cache.items():
                if current_time - data.get("timestamp", 0) > CACHE_TTL:
                    expired_keys.append(key)
            
            for key in expired_keys:
                del analysis_cache[key]
                
            if expired_keys:
                print(f"🧹 清理了 {len(expired_keys)} 个过期缓存项")
                
        except Exception as e:
            print(f"❌ 缓存清理错误: {e}")
        
        # 每10分钟清理一次
        time.sleep(600)


def cleanup_expired_cache():
    """手动清理过期缓存"""
    import time
    current_time = time.time()
    expired_keys = []
    
    for key, data in analysis_cache.items():
        if current_time - data.get("timestamp", 0) > CACHE_TTL:
            expired_keys.append(key)
    
    for key in expired_keys:
        del analysis_cache[key]
        
    return len(expired_keys)


def get_cache_stats():
    """获取缓存统计信息"""
    import time
    current_time = time.time()
    
    total_items = len(analysis_cache)
    expired_items = 0
    
    for data in analysis_cache.values():
        if current_time - data.get("timestamp", 0) > CACHE_TTL:
            expired_items += 1
    
    return {
        "total_items": total_items,
        "expired_items": expired_items,
        "active_items": total_items - expired_items
    }


class OKXCrawlerForBot:
    """
    简化的OKX Web3爬虫 - 专门为Bot使用
    只关注获取大户持有的代币统计信息
    """

    def __init__(self):
        """初始化爬虫"""
        self.session = requests.Session()

        # 基础请求头 - 模拟真实浏览器
        self.headers = {
            "accept": "application/json",
            "accept-encoding": "gzip, deflate, br, zstd",
            "accept-language": "en-US,en;q=0.9,zh-HK;q=0.8,zh-CN;q=0.7,zh;q=0.6,es-MX;q=0.5,es;q=0.4,ru-RU;q=0.3,ru;q=0.2",
            "app-type": "web",
            "cache-control": "no-cache",
            "dnt": "1",
            "pragma": "no-cache",
            "priority": "u=1, i",
            "sec-ch-ua": '"Chromium";v="130", "Google Chrome";v="130", "Not?A_Brand";v="99"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
            "x-cdn": "https://web3.okx.com",
        }

        # 确保日志目录存在
        self.data_manager = DataManager()
        self.log_dir = self.data_manager.get_file_path("logs", "okx_crawler.log").parent

    def log_info(self, message):
        """记录信息到日志文件"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] {message}\n"

        # 写入到日志文件
        log_file = os.path.join(
            self.log_dir, f"okx_crawler_{datetime.now().strftime('%Y%m%d')}.log"
        )
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(log_message)

        # 也打印到控制台
        print(f"[OKX] {message}")

    def get_token_holders(
        self, token_address: str, chain_id: str = "501", max_retries: int = 3
    ) -> List[Dict]:
        """
        获取代币持有者排行榜
        """
        self.log_info(f"开始获取代币持有者: {token_address}")

        for attempt in range(1, max_retries + 1):
            if attempt > 1:
                self.log_info(f"重试获取持有者信息... (尝试 {attempt}/{max_retries})")

            current_timestamp = str(int(time.time() * 1000))

            url = "https://web3.okx.com/priapi/v1/dx/market/v2/holders/ranking-list"
            params = {
                "chainId": chain_id,
                "tokenAddress": token_address,
                "currentUserWalletAddress": "0xa6b67e6f61dba6363b36bbcef80d971a6d1f0ce5",
                "t": current_timestamp,
            }

            # 合并真实请求头
            headers = self.headers.copy()
            headers.update(
                {
                    "cookie": 'devId=31011088-da0a-4bd8-8f3d-9731400b5208; locale=en_US; _monitor_extras={"deviceId":"uC3r8hJBpqO__FJ2_Z2NMj","eventId":106,"sequenceNumber":106}',
                    "devid": "31011088-da0a-4bd8-8f3d-9731400b5208",
                    "x-request-timestamp": current_timestamp,
                    "referer": f"https://web3.okx.com/token/solana/{token_address}",
                }
            )

            try:
                response = self.session.get(url, params=params, headers=headers, timeout=30)

                if response.status_code == 200:
                    try:
                        data = response.json()

                        # 保存原始的holderRankingList数据到日志文件
                        if data.get("code") == 0:
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            raw_data_file = self.data_manager.get_file_path(
                                "holders", f"holders_raw_{token_address}_{timestamp}.json"
                            )
                            with open(raw_data_file, "w", encoding="utf-8") as f:
                                json.dump(data, f, ensure_ascii=False, indent=2)
                            self.log_info(f"原始持有者数据已保存到: {raw_data_file}")

                        if data.get("code") == 0:
                            holders_data = data.get("data", {})

                            # 尝试不同的数据路径
                            holders = []
                            if isinstance(holders_data, dict):
                                # 尝试多个可能的键名
                                possible_keys = [
                                    "holderRankingList",
                                    "data",
                                    "holders",
                                    "list",
                                    "ranking",
                                ]
                                for key in possible_keys:
                                    if key in holders_data and isinstance(holders_data[key], list):
                                        holders = holders_data[key]
                                        break

                            if holders:
                                self.log_info(f"成功获取到 {len(holders)} 个持有者")
                                # 使用配置文件中的数量设置
                                try:
                                    from ..core.config import get_config

                                    config = get_config()
                                    return holders[: config.analysis.top_holders_count]
                                except ImportError:
                                    return holders[:20]  # 回退到默认值
                            else:
                                self.log_info("未找到持有者数据")
                                return []
                        else:
                            self.log_info(f"API返回错误: {data.get('msg', '未知错误')}")

                    except json.JSONDecodeError as e:
                        self.log_info(f"JSON解析失败: {str(e)}")

                else:
                    self.log_info(f"HTTP错误 {response.status_code}")

                # 根据状态码决定是否重试
                if response.status_code in [429, 500, 502, 503, 504]:
                    if attempt < max_retries:
                        delay = random.uniform(2, 5)
                        self.log_info(f"等待 {delay:.1f} 秒后重试...")
                        time.sleep(delay)
                        continue

                break

            except requests.exceptions.RequestException as e:
                self.log_info(f"请求异常: {str(e)}")
                if attempt < max_retries:
                    delay = random.uniform(2, 5)
                    self.log_info(f"等待 {delay:.1f} 秒后重试...")
                    time.sleep(delay)
                    continue
                else:
                    break

        self.log_info("获取持有者信息失败")
        return []

    def get_wallet_assets(self, wallet_address: str) -> Dict:
        """
        获取钱包资产组合信息
        """
        self.log_info(f"获取钱包资产: {wallet_address[:8]}...{wallet_address[-6:]}")

        current_timestamp = str(int(time.time() * 1000))

        # 正确的POST API端点
        url = "https://web3.okx.com/priapi/v2/wallet/asset/profile/all/explorer"
        params = {"t": current_timestamp}

        payload = {
            "userUniqueId": "",
            "hideValueless": False,
            "address": wallet_address,
            "forceRefresh": True,
            "page": 1,
            "limit": 15,
            "chainIndexes": [],
        }

        headers = self.headers.copy()
        headers.update(
            {
                "content-type": "application/json",
                "content-length": "156",
                "origin": "https://web3.okx.com",
                "referer": f"https://web3.okx.com/portfolio/{wallet_address}",
                "x-request-timestamp": current_timestamp,
                # 使用基础的认证头
                "device-token": "01980a38-038a-44d9-8da3-a8276bbcb5b9",
                "devid": "01980a38-038a-44d9-8da3-a8276bbcb5b9",
                "platform": "web",
                "x-locale": "en_US",
                "x-utc": "0",
                "x-zkdex-env": "0",
            }
        )

        # 简化的cookie
        cookie_str = "devId=01980a38-038a-44d9-8da3-a8276bbcb5b9; locale=en_US"
        headers["cookie"] = cookie_str

        try:
            response = self.session.post(
                url, params=params, json=payload, headers=headers, timeout=30
            )

            if response.status_code == 200:
                try:
                    data = response.json()

                    if data.get("code") == 0:
                        assets_data = data.get("data", {})
                        tokens_info = assets_data.get("tokens", {})
                        token_list = tokens_info.get("tokenlist", [])

                        if token_list:
                            # 计算总价值
                            total_value = 0
                            for token in token_list:
                                try:
                                    value = float(token.get("currencyAmount", 0) or 0)
                                    total_value += value
                                except (ValueError, TypeError):
                                    continue

                            self.log_info(
                                f"获取到资产信息: ${total_value:,.2f} (包含 {len(token_list)} 个代币)"
                            )
                        else:
                            self.log_info("未找到代币列表")

                        return assets_data
                    else:
                        self.log_info(f"API返回错误: {data.get('msg', '未知错误')}")

                except json.JSONDecodeError as e:
                    self.log_info(f"JSON解析失败: {str(e)}")
            else:
                self.log_info(f"HTTP错误 {response.status_code}")

        except requests.exceptions.RequestException as e:
            self.log_info(f"请求异常: {str(e)}")

        return {}

    def get_wallet_assets_threaded(self, wallet_addresses: List[str], max_workers: int = 10) -> Dict[str, Dict]:
        """
        使用多线程并发获取多个钱包的资产组合信息
        
        Args:
            wallet_addresses: 钱包地址列表
            max_workers: 最大线程数，默认10个
            
        Returns:
            Dict: {wallet_address: assets_data} 格式的结果字典
        """
        results = {}
        results_lock = threading.Lock()
        request_semaphore = threading.Semaphore(max_workers)  # 控制并发请求数
        
        def fetch_single_wallet(wallet_address: str) -> tuple:
            """获取单个钱包资产的线程函数"""
            max_retries = 3
            for attempt in range(max_retries):
                with request_semaphore:  # 限制并发数
                    try:
                        # 添加随机延迟避免过于频繁的请求
                        time.sleep(random.uniform(0.5, 1.5))
                        assets_data = self.get_wallet_assets(wallet_address)
                        
                        # 如果成功获取数据，直接返回
                        if assets_data:
                            return wallet_address, assets_data
                        elif attempt < max_retries - 1:
                            # 如果失败但还有重试机会，等待更长时间
                            time.sleep(random.uniform(2, 5))
                            
                    except Exception as e:
                        if "429" in str(e) and attempt < max_retries - 1:
                            # 遇到429错误，等待更长时间后重试
                            wait_time = (attempt + 1) * 5 + random.uniform(0, 5)
                            self.log_info(f"钱包 {wallet_address[:8]}...{wallet_address[-6:]} 遇到频率限制，等待 {wait_time:.1f}s 后重试")
                            time.sleep(wait_time)
                            continue
                        else:
                            self.log_info(f"线程获取钱包 {wallet_address[:8]}...{wallet_address[-6:]} 资产失败: {str(e)}")
                            break
            
            return wallet_address, {}
        
        self.log_info(f"开始多线程获取 {len(wallet_addresses)} 个钱包资产 (使用 {max_workers} 个线程)")
        start_time = time.time()
        
        # 调整线程数：如果钱包数量少于设定的线程数，减少线程数避免过度并发
        actual_workers = min(max_workers, len(wallet_addresses), 5)  # 最多5个线程避免频率限制
        self.log_info(f"实际使用 {actual_workers} 个线程（避免频率限制）")
        
        # 使用线程池执行器
        with ThreadPoolExecutor(max_workers=actual_workers) as executor:
            # 提交所有任务
            future_to_address = {
                executor.submit(fetch_single_wallet, addr): addr 
                for addr in wallet_addresses
            }
            
            # 收集结果
            completed_count = 0
            for future in as_completed(future_to_address):
                try:
                    wallet_address, assets_data = future.result(timeout=120)  # 120秒超时
                    
                    with results_lock:
                        results[wallet_address] = assets_data
                        completed_count += 1
                        
                    if completed_count % 10 == 0:  # 每完成10个打印一次进度
                        elapsed = time.time() - start_time
                        rate = completed_count / elapsed if elapsed > 0 else 0
                        remaining = len(wallet_addresses) - completed_count
                        eta = remaining / rate if rate > 0 else 0
                        self.log_info(f"已完成 {completed_count}/{len(wallet_addresses)} 个钱包 (速度: {rate:.1f}/s, 预计剩余: {eta:.0f}s)")
                        
                except Exception as e:
                    self.log_info(f"获取钱包资产时出现异常: {str(e)}")
        
        elapsed_time = time.time() - start_time
        successful_count = len([data for data in results.values() if data])
        average_rate = len(wallet_addresses) / elapsed_time if elapsed_time > 0 else 0
        
        self.log_info(f"多线程资产获取完成: 成功 {successful_count}/{len(wallet_addresses)} 个钱包")
        self.log_info(f"总耗时: {elapsed_time:.1f}s, 平均速度: {average_rate:.1f} 钱包/秒")
        
        return results

    def extract_top_tokens(self, assets_data: Dict) -> List[Dict]:
        """
        从资产数据中提取有价值的代币
        """
        all_tokens = []

        tokens_info = assets_data.get("tokens", {})
        token_list = tokens_info.get("tokenlist", [])

        if not token_list:
            return []

        for token in token_list:
            try:
                symbol = token.get("symbol", "Unknown")
                name = token.get("name", "Unknown")
                chain = token.get("chainName", "Unknown")

                # 从 coinBalanceDetails 中获取地址信息
                balance_details = token.get("coinBalanceDetails", [])
                address = ""
                if balance_details and len(balance_details) > 0:
                    address = balance_details[0].get("address", "")

                # 注意：SOL代币现在包含在代币表中，但不参与地址集群分析

                # 数值字段转换
                try:
                    balance = float(token.get("coinAmount", "0") or 0)
                    price_usd = float(token.get("coinUnitPrice", "0") or 0)
                    value_usd = float(token.get("currencyAmount", "0") or 0)
                except (ValueError, TypeError):
                    continue

                token_info = {
                    "chain": chain,
                    "symbol": symbol,
                    "name": name,
                    "address": address,
                    "balance": balance,
                    "value_usd": value_usd,
                    "price_usd": price_usd,
                }

                # 只添加有价值的代币（现在包括SOL）
                if token_info["value_usd"] > 0:
                    all_tokens.append(token_info)

            except Exception:
                continue

        # 按价值排序
        all_tokens.sort(key=lambda x: x["value_usd"], reverse=True)
        return all_tokens

    def is_excluded_holder(self, holder: Dict) -> bool:
        """
        判断持有者是否应该被排除（流动性池、交易所等）
        """
        # 获取钱包地址
        wallet_address = holder.get("holderWalletAddress", "")
        
        # 检查是否为已知的池子地址（即使OKX没有标记也要排除）
        try:
            from ..core.config import get_config
            config = get_config()
            known_pools = getattr(config.analysis, 'known_pool_addresses', [])
            if wallet_address in known_pools:
                self.log_info(f"识别到已知池子地址: {wallet_address[:8]}...{wallet_address[-6:]}")
                return True
        except (ImportError, AttributeError):
            # 回退到硬编码的已知池子地址
            known_pools = ["5Q544fKrFoe6tsEbD7S8EmxGTJYAKtTVhAW5Q5pge4j1"]
            if wallet_address in known_pools:
                self.log_info(f"识别到已知池子地址: {wallet_address[:8]}...{wallet_address[-6:]}")
                return True
        
        # 检查 holderTagVO
        holder_tag_vo = holder.get("holderTagVO", {})
        if holder_tag_vo:
            # 检查是否为流动性池
            if holder_tag_vo.get("liquidityPool") == "1":
                return True
        
        # 检查 tagList
        tag_list = holder.get("tagList", [])
        for tag in tag_list:
            if isinstance(tag, list) and len(tag) > 0:
                tag_name = tag[0]
                # 排除流动性池和交易所
                if tag_name in ["liquidityPool", "exchange"]:
                    return True
        
        # 检查 userAddressTagVO
        user_address_tag_vo = holder.get("userAddressTagVO", {})
        if "liquidityPool" in user_address_tag_vo or "exchange" in user_address_tag_vo:
            return True
        
        return False

    def analyze_token_holders(self, token_address: str, top_holders_count: int = None, use_threading: bool = True) -> Dict:
        """
        分析代币大户并返回代币统计信息
        专门为Bot优化，只返回必要的信息
        
        Args:
            token_address: 代币合约地址
            top_holders_count: 分析的前N名大户数量
            use_threading: 是否使用多线程加速资产获取，默认True
        """
        # 如果没有提供参数，从配置文件获取
        if top_holders_count is None:
            try:
                from ..core.config import get_config

                config = get_config()
                top_holders_count = config.analysis.top_holders_count
            except ImportError:
                top_holders_count = 20  # 回退到默认值
        self.log_info(f"开始分析代币: {token_address}")

        # 1. 获取持有者排行榜
        holders = self.get_token_holders(token_address)

        if not holders:
            self.log_info("无法获取持有者信息")
            return {}

        # 过滤掉流动性池和交易所地址
        filtered_holders = []
        excluded_count = 0
        
        for holder in holders:
            if self.is_excluded_holder(holder):
                excluded_count += 1
                # 记录被排除的地址信息
                wallet_address = holder.get("holderWalletAddress", "")
                tag_list = holder.get("tagList", [])
                tag_names = [tag[0] if isinstance(tag, list) and len(tag) > 0 else str(tag) for tag in tag_list]
                self.log_info(f"排除地址: {wallet_address[:8]}...{wallet_address[-6:]} (标签: {', '.join(tag_names)})")
            else:
                filtered_holders.append(holder)
        
        self.log_info(f"原始持有者: {len(holders)} 个，排除 {excluded_count} 个流动性池/交易所地址，剩余 {len(filtered_holders)} 个")

        if not filtered_holders:
            self.log_info("过滤后没有可分析的持有者")
            return {}

        # 2. 分析每个大户的资产 - 根据参数选择单线程或多线程
        holder_analysis = []

        if use_threading:
            # 多线程模式：准备钱包地址列表
            wallet_addresses = []
            wallet_to_holder_info = {}  # 保存钱包地址到持有者信息的映射
            
            # 使用过滤后的持有者列表，取前N名
            for i, holder in enumerate(filtered_holders[:top_holders_count], 1):
                # 从explorerUrl中提取钱包地址，或直接使用holderWalletAddress
                explorer_url = holder.get("explorerUrl", "")
                if "solscan.io/account/" in explorer_url:
                    wallet_address = explorer_url.split("solscan.io/account/")[-1]
                else:
                    wallet_address = holder.get("holderWalletAddress", "") or holder.get("holderAddress", "")

                if not wallet_address:
                    self.log_info(f"大户 #{i} 无法获取钱包地址")
                    continue

                wallet_addresses.append(wallet_address)
                wallet_to_holder_info[wallet_address] = {
                    "rank": i,
                    "holder_data": holder
                }

            if not wallet_addresses:
                self.log_info("没有可分析的钱包地址")
                return {}

            # 使用多线程获取所有钱包资产
            try:
                from ..core.config import get_config
                config = get_config()
                max_workers = getattr(config.analysis, 'max_concurrent_threads', 10)
            except (ImportError, AttributeError):
                max_workers = 10
                
            assets_results = self.get_wallet_assets_threaded(wallet_addresses, max_workers)

            # 处理获取到的资产数据
            for wallet_address, assets_data in assets_results.items():
                if wallet_address not in wallet_to_holder_info:
                    continue
                    
                holder_info_map = wallet_to_holder_info[wallet_address]
                rank = holder_info_map["rank"]
                holder = holder_info_map["holder_data"]
                
                if assets_data:
                    # 提取所有有价值的代币
                    top_tokens = self.extract_top_tokens(assets_data)

                    # 只有当成功提取到代币时才添加到分析结果
                    if top_tokens:
                        holder_info = {
                            "rank": rank,
                            "address": wallet_address,
                            "hold_amount": holder.get("holdAmount", "0"),
                            "hold_percentage": holder.get("holdAmountPercentage", "0"),
                            "top_tokens": top_tokens,
                        }

                        holder_analysis.append(holder_info)
                        self.log_info(f"大户 #{rank} 分析完成，发现 {len(top_tokens)} 个有价值代币")
                    else:
                        self.log_info(f"大户 #{rank} 没有发现有价值的代币")
                else:
                    self.log_info(f"大户 #{rank} 获取资产失败")
        else:
            # 单线程模式：保持原来的逻辑
            for i, holder in enumerate(filtered_holders[:top_holders_count], 1):
                # 从explorerUrl中提取钱包地址，或直接使用holderWalletAddress
                explorer_url = holder.get("explorerUrl", "")
                if "solscan.io/account/" in explorer_url:
                    wallet_address = explorer_url.split("solscan.io/account/")[-1]
                else:
                    wallet_address = holder.get("holderWalletAddress", "") or holder.get("holderAddress", "")

                if not wallet_address:
                    self.log_info(f"大户 #{i} 无法获取钱包地址")
                    continue

                self.log_info(f"分析大户 #{i}: {wallet_address[:8]}...{wallet_address[-6:]}")

                # 获取钱包资产
                assets_data = self.get_wallet_assets(wallet_address)

                if assets_data:
                    # 提取所有有价值的代币
                    top_tokens = self.extract_top_tokens(assets_data)

                    # 只有当成功提取到代币时才添加到分析结果
                    if top_tokens:
                        holder_info = {
                            "rank": i,
                            "address": wallet_address,
                            "hold_amount": holder.get("holdAmount", "0"),
                            "hold_percentage": holder.get("holdAmountPercentage", "0"),
                            "top_tokens": top_tokens,
                        }

                        holder_analysis.append(holder_info)
                        self.log_info(f"大户 #{i} 分析完成，发现 {len(top_tokens)} 个有价值代币")
                    else:
                        self.log_info(f"大户 #{i} 没有发现有价值的代币")
                else:
                    self.log_info(f"大户 #{i} 获取资产失败")

                # 添加延迟避免频率限制
                time.sleep(1)

        # 3. 统计所有大户持有的代币，每个大户每个代币只计算一次
        all_tokens = {}
        target_token_holders = set()  # 记录持有目标代币的大户地址

        for holder in holder_analysis:
            # 对于每个大户，记录他持有的唯一代币（避免重复计算）
            holder_unique_tokens = {}

            # 先收集该大户的所有唯一代币
            for token in holder["top_tokens"]:
                symbol = token["symbol"]
                token_address_current = token["address"]

                # 检查是否是目标代币
                if token_address_current == token_address:
                    target_token_holders.add(holder["address"])

                # 使用address作为键，这样可以区分不同的代币（即使名字相同）
                if token_address_current not in holder_unique_tokens:
                    holder_unique_tokens[token_address_current] = {
                        "symbol": symbol,
                        "name": token["name"],
                        "chain": token["chain"],
                        "address": token_address_current,
                        "price_usd": token["price_usd"],
                        "total_balance": token["balance"],
                        "total_value_usd": token["value_usd"],
                        "is_target_token": token_address_current == token_address,
                    }
                else:
                    # 如果已存在，累加数值
                    holder_unique_tokens[token_address_current]["total_balance"] += token["balance"]
                    holder_unique_tokens[token_address_current]["total_value_usd"] += token[
                        "value_usd"
                    ]
                    # 如果是目标代币，标记它
                    if token_address_current == token_address:
                        holder_unique_tokens[token_address_current]["is_target_token"] = True

            # 现在统计到全局代币记录中，每个大户每个代币只计算一次
            for token_addr, token_data in holder_unique_tokens.items():
                if token_addr not in all_tokens:
                    all_tokens[token_addr] = {
                        "symbol": token_data["symbol"],
                        "name": token_data["name"],
                        "chain": token_data["chain"],
                        "address": token_data["address"],
                        "price_usd": token_data["price_usd"],
                        "total_value": 0,
                        "holder_count": 0,
                        "holders_details": [],
                        "is_target_token": token_data["is_target_token"],
                    }
                else:
                    # 如果是目标代币，确保标记正确
                    if token_data["is_target_token"]:
                        all_tokens[token_addr]["is_target_token"] = True

                # 每个大户每个代币只计算一次
                all_tokens[token_addr]["total_value"] += token_data["total_value_usd"]
                all_tokens[token_addr]["holder_count"] += 1

                # 添加大户持有详情
                holder_detail = {
                    "holder_rank": holder["rank"],
                    "holder_address": holder["address"],
                    "balance": token_data["total_balance"],
                    "value_usd": token_data["total_value_usd"],
                }
                all_tokens[token_addr]["holders_details"].append(holder_detail)

        # 过滤：持有人数>=5 且 总价值>=50U 的代币，然后按总价值排序
        filtered_tokens = [token for token in all_tokens.values() if token["total_value"] >= 50 and token["holder_count"] >= 5]
        sorted_tokens = sorted(filtered_tokens, key=lambda x: x["total_value"], reverse=True)

        analysis_result = {
            "token_address": token_address,
            "analysis_time": datetime.now().isoformat(),
            "filtering_stats": {
                "original_holders_count": len(holders),
                "excluded_holders_count": excluded_count,
                "filtered_holders_count": len(filtered_holders),
                "analyzed_holders_count": len(holder_analysis)
            },
            "total_holders_analyzed": len(holder_analysis),
            "target_token_actual_holders": len(target_token_holders),  # 添加实际持有目标代币的人数
            "original_holders_data": holders,  # 保存原始持有者数据用于排名分析
            "token_statistics": {
                "total_unique_tokens": len(filtered_tokens),
                "total_portfolio_value": sum(token["total_value"] for token in sorted_tokens),
                "top_tokens_by_value": sorted_tokens,
            },
        }

        # 保存详细日志到文件
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = self.data_manager.get_file_path("analysis", f"analysis_{token_address}_{timestamp}.json")
        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(analysis_result, f, ensure_ascii=False, indent=2)

        self.log_info(f"分析完成，结果已保存到: {log_file}")
        self.log_info(f"过滤统计: 原始 {len(holders)} 个持有者，排除 {excluded_count} 个流动性池/交易所，分析 {len(holder_analysis)} 个真实投资者")
        self.log_info(
            f"发现 {len(all_tokens)} 种代币，过滤后 {len(filtered_tokens)} 种代币(≥5人持有且≥$50价值)，总价值 ${sum(token['total_value'] for token in sorted_tokens):,.2f}"
        )

        return analysis_result

    def analyze_wallet_group_holdings(self, target_token_address: str, wallet_addresses: list) -> dict:
        """
        分析指定钱包组的持仓情况
        
        Args:
            target_token_address: 目标代币地址  
            wallet_addresses: 要分析的钱包地址列表
            
        Returns:
            dict: 分析结果，格式与analyze_token_holders相同
        """
        start_time = time.time()
        logger = get_logger("crawler")
        
        try:
            logger.info(f"开始钱包组分析: 目标代币={target_token_address}, 钱包数量={len(wallet_addresses)}")
            
            # 获取目标代币的持有者信息，用于获取流通量百分比
            target_token_holders = self.get_token_holders(target_token_address)
            target_holders_map = {}
            if target_token_holders:
                for holder in target_token_holders:
                    wallet_addr = holder.get("holderWalletAddress", "")
                    if wallet_addr:
                        target_holders_map[wallet_addr] = {
                            "holdAmountPercentage": float(holder.get("holdAmountPercentage", 0)),
                            "holdAmount": holder.get("holdAmount", "0"),
                            "holdVolume": float(holder.get("holdVolume", 0))
                        }
                logger.info(f"获取到目标代币 {len(target_holders_map)} 个持有者的流通量信息")
            
            # 收集所有代币信息
            all_tokens = []
            all_addresses = set()
            
            # 首先获取目标代币信息（放在第一位）
            target_token_data = None
            
            # 使用多线程获取所有钱包资产
            wallet_assets = self.get_wallet_assets_threaded(wallet_addresses, max_workers=5)
            
            # 分析每个钱包的持仓
            for wallet_address, wallet_data in wallet_assets.items():
                try:
                    if not wallet_data:
                        logger.warning(f"钱包 {wallet_address} 无数据")
                        continue
                        
                    all_addresses.add(wallet_address)
                    
                    # 直接复用 extract_top_tokens 的逻辑
                    top_tokens = self.extract_top_tokens(wallet_data)
                    
                    logger.info(f"钱包 {wallet_address[:8]}...{wallet_address[-6:]} 有 {len(top_tokens)} 个有价值代币")
                    
                    for token in top_tokens:
                        token_address = token.get("address", "")
                        if not token_address:
                            continue
                            
                        token_value = token.get("value_usd", 0)
                        token_symbol = token.get("symbol", "Unknown")
                        token_name = token.get("name", token_symbol)  # 获取代币名称
                        token_balance = token.get("balance", 0)
                        
                        logger.info(f"  代币: {token_symbol} ({token_address[:8]}...) 价值: ${token_value:.2f}")
                        
                        # 查找是否已存在该代币
                        existing_token = None
                        for existing in all_tokens:
                            if existing["address"] == token_address:
                                existing_token = existing
                                break
                        
                        if existing_token:
                            # 获取流通量百分比（如果是目标代币）
                            percentage = 0
                            if token_address == target_token_address and wallet_address in target_holders_map:
                                percentage = target_holders_map[wallet_address]["holdAmountPercentage"]
                            
                            # 更新现有代币的持有者信息
                            existing_token["holders_details"].append({
                                "holder_address": wallet_address,
                                "value_usd": token_value,
                                "balance": token_balance,
                                "percentage": percentage,  # 使用真实的流通量百分比（如果是目标代币）
                                "holder_rank": len(existing_token["holders_details"]) + 1  # 设置持有者排名
                            })
                            existing_token["total_value"] += token_value
                            existing_token["holder_count"] += 1
                        else:
                            # 获取流通量百分比（如果是目标代币）
                            percentage = 0
                            if token_address == target_token_address and wallet_address in target_holders_map:
                                percentage = target_holders_map[wallet_address]["holdAmountPercentage"]
                            
                            # 新代币
                            new_token = {
                                "address": token_address,
                                "symbol": token_symbol,
                                "name": token_name,  # 添加代币名称
                                "total_value": token_value,
                                "holder_count": 1,
                                "holders_details": [{
                                    "holder_address": wallet_address,
                                    "value_usd": token_value,
                                    "balance": token_balance,
                                    "percentage": percentage,  # 使用真实的流通量百分比（如果是目标代币）
                                    "holder_rank": 1  # 设置持有者排名
                                }]
                            }
                            
                            # 如果是目标代币，保存引用并放在首位
                            if token_address == target_token_address:
                                target_token_data = new_token
                                all_tokens.insert(0, new_token)
                            else:
                                all_tokens.append(new_token)
                
                except Exception as e:
                    logger.error(f"分析钱包 {wallet_address} 失败: {e}")
                    continue
            
            # 确保目标代币在第一位
            if target_token_data and all_tokens[0]["address"] != target_token_address:
                # 移除目标代币并插入到首位
                all_tokens = [token for token in all_tokens if token["address"] != target_token_address]
                all_tokens.insert(0, target_token_data)
            
            # 过滤和排序代币
            filtered_tokens = []
            for token in all_tokens:
                if token["holder_count"] >= 1 and token["total_value"] >= 1:  # 降低门槛
                    filtered_tokens.append(token)
            
            # 目标代币保持在第一位，其他按价值排序
            if filtered_tokens and filtered_tokens[0]["address"] == target_token_address:
                target_token = filtered_tokens[0]
                other_tokens = sorted(filtered_tokens[1:], key=lambda x: x["total_value"], reverse=True)
                sorted_tokens = [target_token] + other_tokens
            else:
                sorted_tokens = sorted(filtered_tokens, key=lambda x: x["total_value"], reverse=True)
            
            analysis_duration = time.time() - start_time
            
            # 构建原始持有者数据（用于目标代币排名分析）
            original_holders_data = []
            if target_token_data:
                for i, holder_detail in enumerate(target_token_data.get("holders_details", [])):
                    holder_address = holder_detail["holder_address"]
                    # 从目标代币持有者信息中获取真实的流通量百分比
                    target_holder_info = target_holders_map.get(holder_address, {})
                    hold_amount_percentage = target_holder_info.get("holdAmountPercentage", 0)
                    hold_volume = target_holder_info.get("holdVolume", holder_detail["value_usd"])
                    hold_amount = target_holder_info.get("holdAmount", str(holder_detail["balance"]))
                    
                    holder_info = {
                        "holderWalletAddress": holder_address,
                        "holdVolume": hold_volume,
                        "holdAmount": hold_amount,
                        "holdAmountPercentage": hold_amount_percentage,  # 使用真实的流通量百分比
                        "rank": i + 1
                    }
                    original_holders_data.append(holder_info)
                    logger.info(f"钱包 {holder_address[:8]}...{holder_address[-6:]} 流通量占比: {hold_amount_percentage:.3f}%")
            
            # 构建分析结果，与普通分析结果格式保持一致
            analysis_result = {
                "token_address": target_token_address,
                "analysis_time": datetime.now().isoformat(),
                "filtering_stats": {
                    "original_holders_count": len(wallet_addresses),
                    "excluded_holders_count": 0,
                    "filtered_holders_count": len(all_addresses),
                    "analyzed_holders_count": len(all_addresses)
                },
                "total_holders_analyzed": len(all_addresses),
                "target_token_actual_holders": len([t for t in sorted_tokens if t["address"] == target_token_address]),
                "original_holders_data": original_holders_data,  # 添加目标代币持有者数据
                "is_wallet_group_analysis": True,  # 标记为钱包组分析
                "wallet_group_size": len(wallet_addresses),
                "successful_wallets": len(all_addresses),
                "token_statistics": {
                    "total_unique_tokens": len(filtered_tokens),
                    "total_portfolio_value": sum(token["total_value"] for token in sorted_tokens),
                    "top_tokens_by_value": sorted_tokens,
                }
            }
            
            logger.info(f"钱包组分析完成: 耗时{analysis_duration:.2f}s, 成功分析{len(all_addresses)}个钱包, 发现{len(sorted_tokens)}种代币")
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"钱包组分析失败: {e}")
            import traceback
            traceback.print_exc()
            return None


def analyze_target_token_rankings(analysis_result: Dict, original_holders: List[Dict] = None) -> Dict:
    """
    分析目标代币在各个地址内的价值排名
    
    Args:
        analysis_result: analyze_token_holders 的结果
        original_holders: 原始持有者数据，用于获取准确的目标代币持仓价值
        
    Returns:
        Dict: 排名分析结果，包含排名分布和统计
    """
    token_stats = analysis_result.get("token_statistics", {})
    all_tokens = token_stats.get("top_tokens_by_value", [])
    target_token_address = analysis_result.get("token_address", "")
    
    if not all_tokens or not target_token_address:
        return {"rankings": [], "statistics": {}}
    
    # 找到目标代币信息
    target_token = None
    for token in all_tokens:
        if token.get("address") == target_token_address:
            target_token = token
            break
    
    if not target_token:
        return {"rankings": [], "statistics": {}}
    
    # 构建原始持有者的目标代币信息字典
    original_target_holders = {}
    if original_holders:
        for holder in original_holders:
            wallet_address = holder.get("holderWalletAddress", "")
            if wallet_address:
                original_target_holders[wallet_address] = {
                    "holdVolume": float(holder.get("holdVolume", 0)),
                    "holdAmountPercentage": float(holder.get("holdAmountPercentage", 0)),
                    "holdAmount": holder.get("holdAmount", "0")
                }
    
    # 构建所有分析的大户地址集合
    all_analyzed_addresses = set()
    for token in all_tokens:
        for holder_info in token.get("holders_details", []):
            holder_address = holder_info.get("holder_address")
            if holder_address:
                all_analyzed_addresses.add(holder_address)
    
    print(f"总共分析了 {len(all_analyzed_addresses)} 个大户地址")
    
    # 构建每个地址的代币价值排名
    address_rankings = []
    
    # 获取持有目标代币的地址
    target_holders_dict = {}
    for holder_detail in target_token.get("holders_details", []):
        holder_address = holder_detail.get("holder_address")
        if holder_address:
            target_holders_dict[holder_address] = holder_detail
    
    print(f"其中 {len(target_holders_dict)} 个地址持有目标代币")
    
    # 遍历所有分析的大户地址
    for holder_address in all_analyzed_addresses:
        # 收集该地址持有的所有代币价值（前15大持仓）
        holder_tokens = []
        
        for token in all_tokens:
            for holder_info in token.get("holders_details", []):
                if holder_info.get("holder_address") == holder_address:
                    holder_tokens.append({
                        "symbol": token["symbol"],
                        "address": token["address"],
                        "value_usd": holder_info.get("value_usd", 0),
                        "is_target": token["address"] == target_token_address
                    })
                    break
        
        # 按价值排序，获取该地址的投资组合排名
        holder_tokens.sort(key=lambda x: x["value_usd"], reverse=True)
        
        # 找到目标代币的排名
        target_rank = None
        target_value = 0
        
        for i, token in enumerate(holder_tokens, 1):
            if token["is_target"]:
                target_rank = i
                target_value = token["value_usd"]
                break
        
        # 确定该地址在原始大户排行榜中的排名
        holder_rank = 0
        if holder_address in target_holders_dict:
            holder_rank = target_holders_dict[holder_address].get("holder_rank", 0)
        else:
            # 如果不在目标代币持有者中，尝试从其他代币的持有者信息中找到排名
            for token in all_tokens:
                for holder_info in token.get("holders_details", []):
                    if holder_info.get("holder_address") == holder_address:
                        holder_rank = holder_info.get("holder_rank", 0)
                        break
                if holder_rank > 0:
                    break
        
        # 如果没有找到目标代币，说明排名>10，但检查原始数据
        if target_rank is None:
            target_rank = 11  # 表示>10名
            # 从原始持有者数据中获取目标代币价值
            if holder_address in original_target_holders:
                target_value = original_target_holders[holder_address]["holdVolume"]
            else:
                target_value = 0   # 该地址确实不持有目标代币
        
        # 计算目标代币价值占比，判断是否为阴谋钱包
        portfolio_total_value = sum(token["value_usd"] for token in holder_tokens)
        
        # 如果目标代币不在前15名，需要加上目标代币价值到总价值中
        if target_rank > 15 and target_value > 0:
            portfolio_total_value += target_value
        
        # 计算排除SOL和稳定币后的资产总价值（用于阴谋β计算）
        portfolio_value_without_sol_stable = 0
        target_value_for_beta = target_value  # 目标代币价值（用于阴谋β）
        
        for token in holder_tokens:
            token_addr = token.get("address", "")
            token_value = token.get("value_usd", 0)
            
            # 如果不是SOL和稳定币，加入阴谋β计算
            if token_addr not in SOL_AND_STABLECOINS:
                portfolio_value_without_sol_stable += token_value
        
        # 如果目标代币不在前15名且不是SOL/稳定币，需要加上目标代币价值
        target_token_address_current = target_token_address  # 目标代币地址
        if (target_rank > 15 and target_value > 0 and 
            target_token_address_current not in SOL_AND_STABLECOINS):
            portfolio_value_without_sol_stable += target_value
        
        # 如果目标代币是SOL或稳定币，阴谋β中目标代币价值为0
        if target_token_address_current in SOL_AND_STABLECOINS:
            target_value_for_beta = 0
        
        # 计算阴谋α（所有资产）
        target_percentage_alpha = 0
        is_conspiracy_alpha = False
        if portfolio_total_value > 0 and target_value > 0:
            target_percentage_alpha = (target_value / portfolio_total_value) * 100
            is_conspiracy_alpha = target_percentage_alpha > 50
        
        # 计算阴谋β（排除SOL和稳定币）
        target_percentage_beta = 0
        is_conspiracy_beta = False
        if portfolio_value_without_sol_stable > 0 and target_value_for_beta > 0:
            target_percentage_beta = (target_value_for_beta / portfolio_value_without_sol_stable) * 100
            is_conspiracy_beta = target_percentage_beta > 50
        
        # 综合判断：任一条件满足即为阴谋钱包
        is_conspiracy_wallet = is_conspiracy_alpha or is_conspiracy_beta
        
        # 保持向后兼容性，target_percentage使用阴谋α的值
        target_percentage = target_percentage_alpha
        
        # 获取目标代币的持有百分比（占总供应量）
        target_supply_percentage = 0
        if holder_address in original_target_holders:
            target_supply_percentage = original_target_holders[holder_address]["holdAmountPercentage"]
        else:
            # 如果该地址不在原始目标持有者中，但持有目标代币，
            # 尝试从目标代币的详细信息中获取百分比
            if target_rank <= 15 and target_value > 0:
                # 从target_token的holders_details中查找该地址的百分比
                for holder_detail in target_token.get("holders_details", []):
                    if holder_detail.get("holder_address") == holder_address:
                        # 使用目标代币价值和总持有价值来估算百分比
                        # 这里我们根据价值占比来估算流通量百分比
                        # 这是一个近似值，因为我们没有代币的具体数量信息
                        break
        
        address_rankings.append({
            "holder_address": holder_address,
            "holder_rank": holder_rank,
            "target_token_rank": target_rank,
            "target_token_value": target_value,
            "target_supply_percentage": target_supply_percentage,  # 占总供应量百分比
            "total_tokens": len(holder_tokens),
            "portfolio_value": portfolio_total_value,
            "portfolio_value_without_sol_stable": portfolio_value_without_sol_stable,  # 排除SOL和稳定币的资产价值
            "target_percentage": target_percentage,  # 阴谋α占比（所有资产）
            "target_percentage_alpha": target_percentage_alpha,  # 阴谋α占比（所有资产）
            "target_percentage_beta": target_percentage_beta,  # 阴谋β占比（排除SOL和稳定币）
            "is_conspiracy_wallet": is_conspiracy_wallet,  # 综合阴谋钱包判断
            "is_conspiracy_alpha": is_conspiracy_alpha,  # 阴谋α
            "is_conspiracy_beta": is_conspiracy_beta  # 阴谋β
        })
    
    print(f"最终统计了 {len(address_rankings)} 个地址的排名")
    
    # 计算统计信息
    if address_rankings:
        ranks = [addr["target_token_rank"] for addr in address_rankings]
        
        # 排名分布统计
        rank_distribution = {}
        for rank in ranks:
            if rank <= 10:
                rank_key = f"第{rank}名"
            else:
                rank_key = ">10名"
            rank_distribution[rank_key] = rank_distribution.get(rank_key, 0) + 1
        
        # 实际持有者统计（目标代币在钱包中排名≤15的地址）
        actual_holders_all = [addr for addr in address_rankings if addr["target_token_rank"] <= 15]
        
        # 基础统计（只计算前15名的地址，用于平均排名和中位数计算）
        actual_ranks = [r for r in ranks if r <= 15]
        if actual_ranks:
            avg_rank = sum(actual_ranks) / len(actual_ranks)
            median_rank = sorted(actual_ranks)[len(actual_ranks) // 2]
        else:
            avg_rank = 0
            median_rank = 0
        
        # 阴谋钱包统计
        conspiracy_wallets = [addr for addr in address_rankings if addr["is_conspiracy_wallet"]]
        conspiracy_alpha_wallets = [addr for addr in address_rankings if addr["is_conspiracy_alpha"]]
        conspiracy_beta_wallets = [addr for addr in address_rankings if addr["is_conspiracy_beta"]]
        
        conspiracy_count = len(conspiracy_wallets)
        conspiracy_alpha_count = len(conspiracy_alpha_wallets)
        conspiracy_beta_count = len(conspiracy_beta_wallets)
        
        conspiracy_total_value = sum(wallet["target_token_value"] for wallet in conspiracy_wallets)
        conspiracy_alpha_total_value = sum(wallet["target_token_value"] for wallet in conspiracy_alpha_wallets)
        conspiracy_beta_total_value = sum(wallet["target_token_value"] for wallet in conspiracy_beta_wallets)
        
        # 流通量占比统计
        conspiracy_supply_percentage = sum(wallet.get("target_supply_percentage", 0) for wallet in conspiracy_wallets)
        conspiracy_alpha_supply_percentage = sum(wallet.get("target_supply_percentage", 0) for wallet in conspiracy_alpha_wallets)
        conspiracy_beta_supply_percentage = sum(wallet.get("target_supply_percentage", 0) for wallet in conspiracy_beta_wallets)
        
        # 智能分析
        analysis_text = _generate_ranking_analysis(address_rankings, avg_rank, rank_distribution)
        
        # 计算原始目标代币持有者数量（有流通量占比的地址）
        original_target_holders_count = len([addr for addr in address_rankings if addr.get("target_supply_percentage", 0) > 0])
        
        statistics = {
            "total_addresses": original_target_holders_count,  # 原始目标代币持有者数量
            "actual_holders": len(actual_holders_all),  # 目标代币在钱包中排名≤15的地址数
            "conspiracy_wallets": conspiracy_count,  # 综合阴谋钱包数量
            "conspiracy_alpha_wallets": conspiracy_alpha_count,  # 阴谋α钱包数量
            "conspiracy_beta_wallets": conspiracy_beta_count,  # 阴谋β钱包数量
            "conspiracy_total_value": conspiracy_total_value,  # 综合阴谋钱包总价值
            "conspiracy_alpha_total_value": conspiracy_alpha_total_value,  # 阴谋α钱包总价值
            "conspiracy_beta_total_value": conspiracy_beta_total_value,  # 阴谋β钱包总价值
            "conspiracy_supply_percentage": conspiracy_supply_percentage,  # 综合阴谋钱包流通量占比
            "conspiracy_alpha_supply_percentage": conspiracy_alpha_supply_percentage,  # 阴谋α钱包流通量占比
            "conspiracy_beta_supply_percentage": conspiracy_beta_supply_percentage,  # 阴谋β钱包流通量占比
            "average_rank": avg_rank,
            "median_rank": median_rank,
            "rank_distribution": rank_distribution,
            "top3_count": len([r for r in ranks if r <= 3]),
            "top5_count": len([r for r in ranks if r <= 5]),
            "top15_count": len([r for r in ranks if r <= 15]),
            "over15_count": len([r for r in ranks if r > 15]),
            "analysis": analysis_text
        }
    else:
        statistics = {
            "total_addresses": 0,
            "actual_holders": 0,
            "conspiracy_wallets": 0,
            "conspiracy_total_value": 0,
            "average_rank": 0,
            "median_rank": 0,
            "rank_distribution": {},
            "analysis": "未找到分析数据"
        }
    
    return {
        "target_token": {
            "symbol": target_token["symbol"],
            "address": target_token_address
        },
        "rankings": address_rankings,
        "statistics": statistics
    }


def _generate_ranking_analysis(rankings: List[Dict], avg_rank: float, distribution: Dict) -> str:
    """生成简化的投资建议分析 - 专注于阴谋持仓比例和大户持仓信心"""
    # 1. 计算基础指标
    metrics = _calculate_analysis_metrics(rankings)
    
    analysis_parts = []
    
    # 2. 阴谋钱包风险评估
    conspiracy_analysis = _analyze_conspiracy_risk(metrics)
    analysis_parts.append(conspiracy_analysis)
    
    # 3. 大户持仓信心评估
    confidence_analysis = _analyze_holder_confidence(avg_rank, metrics)
    analysis_parts.append(confidence_analysis)
    
    # 4. 大户分布信心补充
    distribution_analysis = _analyze_distribution_confidence(metrics)
    analysis_parts.append(distribution_analysis)
    
    # 5. 综合投资建议
    investment_advice = _generate_investment_advice(metrics, avg_rank)
    analysis_parts.append(investment_advice)
    
    return " ".join(analysis_parts)


def _calculate_analysis_metrics(rankings: List[Dict]) -> Dict:
    """计算分析所需的所有指标"""
    total_addresses = len(rankings)
    
    # 阴谋钱包相关
    conspiracy_wallets = [r for r in rankings if r.get("is_conspiracy_wallet", False)]
    conspiracy_alpha_wallets = [r for r in rankings if r.get("is_conspiracy_alpha", False)]
    conspiracy_beta_wallets = [r for r in rankings if r.get("is_conspiracy_beta", False)]
    
    conspiracy_count = len(conspiracy_wallets)
    conspiracy_alpha_count = len(conspiracy_alpha_wallets)
    conspiracy_beta_count = len(conspiracy_beta_wallets)
    
    conspiracy_supply = sum(r.get("target_supply_percentage", 0) for r in conspiracy_wallets)
    conspiracy_alpha_supply = sum(r.get("target_supply_percentage", 0) for r in conspiracy_alpha_wallets)
    conspiracy_beta_supply = sum(r.get("target_supply_percentage", 0) for r in conspiracy_beta_wallets)
    
    # 排名分布统计
    top3_count = len([r for r in rankings if r["target_token_rank"] <= 3])
    top5_count = len([r for r in rankings if r["target_token_rank"] <= 5])
    top15_count = len([r for r in rankings if r["target_token_rank"] <= 15])
    
    # 百分比计算
    top3_pct = (top3_count / total_addresses) * 100 if total_addresses > 0 else 0
    top5_pct = (top5_count / total_addresses) * 100 if total_addresses > 0 else 0
    top15_pct = (top15_count / total_addresses) * 100 if total_addresses > 0 else 0
    
    # 总流通量
    total_supply = sum(r.get("target_supply_percentage", 0) for r in rankings)
    conspiracy_risk_ratio = conspiracy_supply / total_supply if total_supply > 0 else 0
    conspiracy_alpha_risk_ratio = conspiracy_alpha_supply / total_supply if total_supply > 0 else 0
    conspiracy_beta_risk_ratio = conspiracy_beta_supply / total_supply if total_supply > 0 else 0
    
    return {
        "total_addresses": total_addresses,
        "conspiracy_count": conspiracy_count,
        "conspiracy_alpha_count": conspiracy_alpha_count,
        "conspiracy_beta_count": conspiracy_beta_count,
        "conspiracy_supply": conspiracy_supply,
        "conspiracy_alpha_supply": conspiracy_alpha_supply,
        "conspiracy_beta_supply": conspiracy_beta_supply,
        "conspiracy_risk_ratio": conspiracy_risk_ratio,
        "conspiracy_alpha_risk_ratio": conspiracy_alpha_risk_ratio,
        "conspiracy_beta_risk_ratio": conspiracy_beta_risk_ratio,
        "top3_count": top3_count,
        "top5_count": top5_count,
        "top15_count": top15_count,
        "top3_pct": top3_pct,
        "top5_pct": top5_pct,
        "top15_pct": top15_pct,
        "total_supply": total_supply
    }


def _analyze_conspiracy_risk(metrics: Dict) -> str:
    """分析阴谋钱包风险"""
    conspiracy_count = metrics["conspiracy_count"]
    conspiracy_alpha_count = metrics["conspiracy_alpha_count"]
    conspiracy_beta_count = metrics["conspiracy_beta_count"]
    conspiracy_supply = metrics["conspiracy_supply"]
    conspiracy_alpha_supply = metrics["conspiracy_alpha_supply"]
    conspiracy_beta_supply = metrics["conspiracy_beta_supply"]
    conspiracy_risk_ratio = metrics["conspiracy_risk_ratio"]
    conspiracy_alpha_risk_ratio = metrics["conspiracy_alpha_risk_ratio"]
    conspiracy_beta_risk_ratio = metrics["conspiracy_beta_risk_ratio"]
    
    if conspiracy_count == 0:
        return "✅ 无阴谋风险：未发现过度集中持仓钱包"
    
    # 构建详细的阴谋钱包分析
    analysis_parts = []
    
    # 总体风险评估
    if conspiracy_risk_ratio >= 0.6:
        analysis_parts.append(f"🔴 阴谋风险极高：{conspiracy_count}个钱包过度集中({conspiracy_supply:.1f}%)，砸盘风险大")
    elif conspiracy_risk_ratio >= 0.3:
        analysis_parts.append(f"🟡 阴谋风险中等：{conspiracy_count}个钱包集中持仓({conspiracy_supply:.1f}%)，需谨慎")
    else:
        analysis_parts.append(f"🟢 阴谋风险较低：{conspiracy_count}个集中钱包占比{conspiracy_supply:.1f}%，可控")
    
    # 详细分析阴谋α和阴谋β
    detail_parts = []
    if conspiracy_alpha_count > 0:
        detail_parts.append(f"α型{conspiracy_alpha_count}个({conspiracy_alpha_supply:.1f}%)")
    if conspiracy_beta_count > 0:
        detail_parts.append(f"β型{conspiracy_beta_count}个({conspiracy_beta_supply:.1f}%)")
    
    if detail_parts:
        analysis_parts.append(f"其中{', '.join(detail_parts)}")
    
    return " ".join(analysis_parts)


def _analyze_holder_confidence(avg_rank: float, metrics: Dict) -> str:
    """分析大户持仓信心"""
    if avg_rank <= 0:
        return "⚡ 大户信心偏弱：无有效持仓数据"
    
    if avg_rank <= 3:
        return "🔥 大户信心极强：平均排名前3，属核心重仓资产"
    elif avg_rank <= 5:
        return "🚀 大户信心较强：平均排名前5，属重要配置"
    elif avg_rank <= 8:
        return "📈 大户信心一般：平均排名中等，适度配置"
    else:
        return "⚡ 大户信心偏弱：排名偏低，多为试探性配置"


def _analyze_distribution_confidence(metrics: Dict) -> str:
    """分析大户分布信心"""
    top3_pct = metrics["top3_pct"]
    top5_pct = metrics["top5_pct"]
    top15_pct = metrics["top15_pct"]
    
    if top3_pct >= 50:
        return f"💪 {top3_pct:.1f}%大户将其列为前3重仓，信心度极高"
    elif top5_pct >= 50:
        return f"⭐ {top5_pct:.1f}%大户将其列为前5配置，认可度较高"
    elif top15_pct >= 50:
        return f"📊 {top15_pct:.1f}%大户将其列为前15配置，有基础共识"
    else:
        return "🔄 多数大户仅试探性配置，整体信心不足"


def _generate_investment_advice(metrics: Dict, avg_rank: float) -> str:
    """生成投资建议"""
    # 评估阴谋风险等级
    conspiracy_risk = _evaluate_conspiracy_risk(metrics)
    
    # 评估大户信心等级
    holder_confidence = _evaluate_holder_confidence(avg_rank, metrics)
    
    # 投资建议映射表
    advice_map = {
        ("无风险", "极强"): "✅ 投资建议：BUY - 阴谋风险低，大户信心强，适合重仓",
        ("无风险", "较强"): "✅ 投资建议：BUY - 阴谋风险低，大户信心强，适合重仓",
        ("低风险", "极强"): "✅ 投资建议：BUY - 阴谋风险可控，大户看好，推荐配置",
        ("低风险", "较强"): "✅ 投资建议：BUY - 阴谋风险可控，大户看好，推荐配置",
        ("无风险", "一般"): "📊 投资建议：HODL - 风险可控但信心一般，适度配置",
        ("低风险", "一般"): "📊 投资建议：HODL - 风险可控但信心一般，适度配置",
        ("中风险", "极强"): "⚠️ 投资建议：小仓位 - 大户看好但有阴谋风险，控制仓位",
        ("中风险", "较强"): "⚠️ 投资建议：小仓位 - 大户看好但有阴谋风险，控制仓位",
        ("高风险", "*"): "🔴 投资建议：PASS - 阴谋风险过高，不建议投资"
    }
    
    # 优先检查高风险情况
    if conspiracy_risk == "高风险":
        return advice_map[("高风险", "*")]
    
    # 查找匹配的建议
    advice_key = (conspiracy_risk, holder_confidence)
    if advice_key in advice_map:
        return advice_map[advice_key]
    
    # 默认建议
    return "⚡ 投资建议：观望 - 大户信心不足，建议等待更好时机"


def _evaluate_conspiracy_risk(metrics: Dict) -> str:
    """评估阴谋风险等级"""
    conspiracy_count = metrics["conspiracy_count"]
    conspiracy_risk_ratio = metrics["conspiracy_risk_ratio"]
    
    if conspiracy_count == 0:
        return "无风险"
    elif conspiracy_risk_ratio < 0.3:
        return "低风险"
    elif conspiracy_risk_ratio < 0.6:
        return "中风险"
    else:
        return "高风险"


def _evaluate_holder_confidence(avg_rank: float, metrics: Dict) -> str:
    """评估大户信心等级"""
    top3_pct = metrics["top3_pct"]
    top5_pct = metrics["top5_pct"]
    top15_pct = metrics["top15_pct"]
    
    if avg_rank <= 3 and top3_pct >= 20:
        return "极强"
    elif avg_rank <= 5 and top5_pct >= 15:
        return "较强"
    elif avg_rank <= 12 and top15_pct >= 10:
        return "一般"
    else:
        return "偏弱"


def analyze_address_clusters(analysis_result: Dict) -> Dict:
    """
    分析地址集群：找出共同持有相同代币的地址群体

    Args:
        analysis_result: analyze_token_holders 的结果

    Returns:
        Dict: 集群分析结果
    """
    try:
        from ..core.config import get_config

        config = get_config()
        CLUSTER_MIN_COMMON_TOKENS = config.analysis.cluster_min_common_tokens
        CLUSTER_MIN_ADDRESSES = config.analysis.cluster_min_addresses
        CLUSTER_MAX_ADDRESSES = config.analysis.cluster_max_addresses
    except ImportError:
        CLUSTER_MIN_COMMON_TOKENS = 3
        CLUSTER_MIN_ADDRESSES = 2
        CLUSTER_MAX_ADDRESSES = 10

    # 获取所有代币的持有者信息
    token_stats = analysis_result.get("token_statistics", {})
    all_tokens = token_stats.get("top_tokens_by_value", [])

    if not all_tokens:
        return {"clusters": []}

    # 1. 构建地址-代币映射 (排除SOL代币，因为SOL不参与集群分析)
    address_tokens = {}  # {address: set(token_addresses)}
    token_holders = {}  # {token_address: set(addresses)}

    for token in all_tokens:
        token_address = token["address"]
        holders_details = token.get("holders_details", [])

        # 排除SOL代币参与地址集群分析（使用合约地址判断更准确）
        if token_address == SOL_TOKEN_ADDRESS:
            logger.info(f"过滤SOL代币，地址: {token_address}")
            continue

        if not token_address or not holders_details:
            continue

        token_holders[token_address] = set()

        for holder_detail in holders_details:
            holder_addr = holder_detail.get("holder_address")
            if not holder_addr:
                continue

            # 记录该地址持有的代币
            if holder_addr not in address_tokens:
                address_tokens[holder_addr] = set()
            address_tokens[holder_addr].add(token_address)

            # 记录该代币的持有者
            token_holders[token_address].add(holder_addr)

    # 2. 寻找地址集群
    clusters = []
    processed_addresses = set()

    # 按持有代币数量排序地址，优先处理持有代币多的地址
    sorted_addresses = sorted(address_tokens.items(), key=lambda x: len(x[1]), reverse=True)

    for addr, tokens in sorted_addresses:
        if addr in processed_addresses:
            continue

        if len(tokens) < CLUSTER_MIN_COMMON_TOKENS:
            continue

        # 寻找与当前地址有共同代币的其他地址
        cluster_addresses = {addr}

        # 遍历其他地址，找到有共同代币的
        for other_addr, other_tokens in sorted_addresses:
            if other_addr == addr or other_addr in processed_addresses:
                continue

            # 计算共同代币
            shared_tokens = tokens & other_tokens

            if len(shared_tokens) >= CLUSTER_MIN_COMMON_TOKENS:
                cluster_addresses.add(other_addr)

                # 限制集群大小
                if len(cluster_addresses) >= CLUSTER_MAX_ADDRESSES:
                    break

        # 计算集群中所有地址真正的共同代币
        if len(cluster_addresses) >= CLUSTER_MIN_ADDRESSES:
            # 找出所有集群地址都持有的代币
            common_tokens = None
            for cluster_addr in cluster_addresses:
                if common_tokens is None:
                    common_tokens = address_tokens[cluster_addr].copy()
                else:
                    common_tokens &= address_tokens[cluster_addr]

        # 如果找到了足够的地址形成集群且有足够的共同代币
        if (
            len(cluster_addresses) >= CLUSTER_MIN_ADDRESSES
            and len(common_tokens) >= CLUSTER_MIN_COMMON_TOKENS
        ):

            # 收集共同代币的详细信息
            cluster_tokens_info = []
            total_cluster_value = 0

            for token_addr in common_tokens:
                # 找到对应的代币信息
                token_info = None
                for token in all_tokens:
                    if token["address"] == token_addr:
                        token_info = token
                        break

                if token_info:
                    # 计算集群在该代币中的总价值
                    cluster_value_in_token = 0
                    cluster_holders_in_token = []

                    for holder_detail in token_info.get("holders_details", []):
                        if holder_detail.get("holder_address") in cluster_addresses:
                            cluster_value_in_token += holder_detail.get("value_usd", 0)
                            cluster_holders_in_token.append(
                                {
                                    "address": holder_detail.get("holder_address"),
                                    "value_usd": holder_detail.get("value_usd", 0),
                                    "rank": holder_detail.get("holder_rank", 0),
                                }
                            )

                    cluster_tokens_info.append(
                        {
                            "symbol": token_info["symbol"],
                            "name": token_info["name"],
                            "address": token_addr,
                            "cluster_value": cluster_value_in_token,
                            "cluster_holders": cluster_holders_in_token,
                            "total_token_value": token_info["total_value"],
                            "cluster_percentage": (
                                (cluster_value_in_token / token_info["total_value"]) * 100
                                if token_info["total_value"] > 0
                                else 0
                            ),
                        }
                    )

                    total_cluster_value += cluster_value_in_token

            # 按集群中持有该代币的地址数量排序
            cluster_tokens_info.sort(key=lambda x: len(x["cluster_holders"]), reverse=True)

            cluster_info = {
                "cluster_id": len(clusters) + 1,
                "addresses": list(cluster_addresses),
                "address_count": len(cluster_addresses),
                "common_tokens": cluster_tokens_info,
                "common_tokens_count": len(common_tokens),
                "total_value": total_cluster_value,
                "avg_value_per_address": (
                    total_cluster_value / len(cluster_addresses)
                    if len(cluster_addresses) > 0
                    else 0
                ),
            }

            clusters.append(cluster_info)
            processed_addresses.update(cluster_addresses)

    # 按代币数量和地址数量综合排序集群
    # 计算综合评分：代币数量 * 地址数量 (代币数量权重更高)
    clusters.sort(key=lambda x: x["common_tokens_count"] * x["address_count"], reverse=True)

    cluster_result = {
        "clusters": clusters,
        "analysis_summary": {
            "total_clusters": len(clusters),
            "total_addresses_in_clusters": sum(c["address_count"] for c in clusters),
            "cluster_config": {
                "min_common_tokens": CLUSTER_MIN_COMMON_TOKENS,
                "min_addresses": CLUSTER_MIN_ADDRESSES,
                "max_addresses": CLUSTER_MAX_ADDRESSES,
            },
        },
    }

    return cluster_result


def format_tokens_table(
    token_stats: Dict, max_tokens: int = None, sort_by: str = "value", cache_key: str = None, target_token_symbol: str = None
) -> tuple:
    """
    格式化代币统计表格，专门为Telegram消息优化

    Args:
        token_stats: 代币统计数据
        max_tokens: 显示的最大代币数量 (如果为None，从配置文件读取)
        sort_by: 排序方式 ('value' 按总价值, 'count' 按持有人数)
        cache_key: 缓存键，用于生成详情按钮
        target_token_symbol: 目标代币的符号，用于显示在标题中

    Returns:
        tuple: (消息文本, 按钮markup对象)
    """
    # 如果没有提供参数，从配置文件获取
    if max_tokens is None:
        try:
            from ..core.config import get_config

            config = get_config()
            max_tokens = config.analysis.ranking_size
        except ImportError:
            max_tokens = 30  # 回退到默认值

    # 获取详情按钮数量配置
    detail_buttons_count = max_tokens  # 默认与排行榜大小相同
    try:
        from ..core.config import get_config

        config = get_config()
        detail_buttons_count = config.analysis.detail_buttons_count
    except ImportError:
        pass
    if not token_stats or not token_stats.get("top_tokens_by_value"):
        return "❌ 未找到代币数据", None

    # 根据排序方式重新排序
    all_tokens = token_stats["top_tokens_by_value"]
    if sort_by == "count":
        sorted_tokens = sorted(all_tokens, key=lambda x: x["holder_count"], reverse=True)
        sort_desc = "按持有人数排序"
        sort_icon = "👥"
    else:
        sorted_tokens = sorted(all_tokens, key=lambda x: x["total_value"], reverse=True)
        sort_desc = "按总价值排序"
        sort_icon = "💰"

    sorted_tokens = sorted_tokens[:max_tokens]
    total_portfolio_value = token_stats.get("total_portfolio_value", 0)
    total_unique_tokens = token_stats.get("total_unique_tokens", 0)

    # 构建表格标题
    if target_token_symbol:
        title = f"🔥 <b>{target_token_symbol}大户主要持仓</b> ({sort_icon} {sort_desc})"
    else:
        title = f"🔥 <b>大户热门代币排行榜</b> ({sort_icon} {sort_desc})"
    
    msg = f"{title}\n"
    msg += f"💰 总资产: <b>${total_portfolio_value:,.0f}</b>\n"
    msg += f"🔢 代币种类: <b>{total_unique_tokens}</b>\n"
    msg += "─" * 35 + "\n"

    # 创建按钮布局
    markup = None
    detail_buttons = []

    # 为前15个代币创建详情按钮
    if cache_key:
        try:
            # 尝试导入telebot
            from telebot import types

            markup = types.InlineKeyboardMarkup()
        except ImportError:
            # 如果telebot不可用，返回None
            markup = None

    for i, token in enumerate(sorted_tokens, 1):
        symbol = token["symbol"][:8]  # 限制长度
        value = token["total_value"]
        count = token["holder_count"]
        token_address = token.get("address", "")

        # 格式化价值
        if value >= 1_000_000:
            value_str = f"${value/1_000_000:.1f}M"
        elif value >= 1_000:
            value_str = f"${value/1_000:.1f}K"
        else:
            value_str = f"${value:.0f}"

        # 为代币名称添加超链接
        if token_address:
            gmgn_token_link = f"https://gmgn.ai/sol/token/{token_address}"
            symbol_with_link = f"<a href='{gmgn_token_link}'>{symbol}</a>"
        else:
            symbol_with_link = symbol

        if sort_by == "count":
            # 按持有人数排序时，突出显示人数
            msg += f"<b>{i:2d}.</b> {symbol_with_link} <b>({count}人)</b> {value_str}\n"
        else:
            # 按价值排序时，突出显示价值
            msg += f"<b>{i:2d}.</b> {symbol_with_link} <b>{value_str}</b> ({count}人)\n"

        # 为代币添加详情按钮
        if i <= detail_buttons_count and cache_key and markup:
            button_text = f"{i}. {symbol}"
            # 在回调数据中包含排序信息
            callback_data = f"token_detail_{cache_key}_{i-1}_{sort_by}"  # 添加排序信息
            try:
                from telebot import types

                detail_buttons.append(
                    types.InlineKeyboardButton(button_text, callback_data=callback_data)
                )
            except ImportError:
                pass

    # 添加代币详情按钮（每行3个）
    if detail_buttons and cache_key:
        msg += f"\n💡 <i>点击下方按钮查看前{min(detail_buttons_count, len(sorted_tokens))}个代币的大户详情</i>\n"

        # 分行添加按钮，每行3个
        for i in range(0, len(detail_buttons), 3):
            row_buttons = detail_buttons[i : i + 3]
            markup.add(*row_buttons)

    return msg, markup


def format_token_holders_detail(token_info: Dict, token_stats: Dict) -> str:
    """
    格式化单个代币的大户持有详情

    Args:
        token_info: 代币信息
        token_stats: 完整的代币统计数据

    Returns:
        str: 格式化的大户详情消息
    """
    symbol = token_info["symbol"]
    name = token_info["name"]
    total_value = token_info["total_value"]
    holder_count = token_info["holder_count"]

    # 格式化总价值
    if total_value >= 1_000_000:
        value_str = f"${total_value/1_000_000:.2f}M"
    elif total_value >= 1_000:
        value_str = f"${total_value/1_000:.2f}K"
    else:
        value_str = f"${total_value:.2f}"

    msg = f"🪙 <b>{symbol}</b> ({name}) 大户持有详情\n"
    msg += f"💰 总持有价值: <b>{value_str}</b>\n"
    msg += f"👥 持有大户数: <b>{holder_count} 人</b>\n"
    msg += "─" * 40 + "\n"

    # 获取持有该代币的大户详情
    holders_details = token_info.get("holders_details", [])

    # 添加调试信息
    print(f"调试: {symbol} 的 holders_details 长度: {len(holders_details)}")

    if holders_details:
        # 按持有价值排序
        sorted_holders = sorted(holders_details, key=lambda x: x.get("value_usd", 0), reverse=True)

        msg += "📊 <b>大户持有排行</b>:\n\n"

        for i, holder in enumerate(sorted_holders, 1):
            holder_rank = holder.get("holder_rank", 0)
            holder_addr = holder.get("holder_address", "")
            balance = holder.get("balance", 0)
            value_usd = holder.get("value_usd", 0)

            # 验证数据有效性
            if not holder_addr or value_usd <= 0:
                print(f"警告: 大户#{holder_rank} 数据无效: addr={holder_addr}, value={value_usd}")
                continue

            # 格式化地址显示和超链接
            addr_display = (
                f"{holder_addr[:6]}...{holder_addr[-4:]}" if len(holder_addr) >= 10 else holder_addr
            )
            gmgn_link = f"https://gmgn.ai/sol/address/{holder_addr}"
            addr_with_link = f"<a href='{gmgn_link}'>{addr_display} 🔗</a>"

            # 格式化持有价值
            if value_usd >= 1_000_000:
                holder_value_str = f"${value_usd/1_000_000:.2f}M"
            elif value_usd >= 1_000:
                holder_value_str = f"${value_usd/1_000:.2f}K"
            else:
                holder_value_str = f"${value_usd:.2f}"

            # 格式化余额
            if balance >= 1_000_000:
                balance_str = f"{balance/1_000_000:.2f}M"
            elif balance >= 1_000:
                balance_str = f"{balance/1_000:.2f}K"
            else:
                balance_str = f"{balance:,.2f}"

            msg += f"<b>{i:2d}.</b> 大户#{holder_rank} {addr_with_link}\n"
            msg += f"    💰 价值: <b>{holder_value_str}</b> | 数量: {balance_str}\n\n"

            # 限制显示前15个大户，避免消息过长
            if i >= 15:
                remaining = len(sorted_holders) - 15
                if remaining > 0:
                    msg += f"... 还有 {remaining} 个大户持有该代币\n"
                break
    else:
        msg += "❌ 暂无大户详情数据\n"
        msg += f"💡 <i>这可能是因为:</i>\n"
        msg += f"• 数据收集过程中出现了错误\n"
        msg += f"• 大户资产获取失败\n"
        msg += f"• 网络连接问题\n"
        print(f"错误: {symbol} 没有 holders_details 数据")

    return msg


def format_cluster_analysis(cluster_result: Dict, max_clusters: int = 5, page: int = 1, clusters_per_page: int = 3) -> str:
    """
    格式化集群分析结果为Telegram消息

    Args:
        cluster_result: 集群分析结果
        max_clusters: 最多显示的集群数量（已废弃，为了兼容性保留）
        page: 当前页码（从1开始）
        clusters_per_page: 每页显示的集群数量

    Returns:
        str: 格式化的消息文本
    """
    clusters = cluster_result.get("clusters", [])
    summary = cluster_result.get("analysis_summary", {})

    if not clusters:
        return "❌ 未发现符合条件的地址集群"

    total_clusters = summary.get("total_clusters", 0)
    total_pages = (len(clusters) + clusters_per_page - 1) // clusters_per_page  # 向上取整
    
    # 确保页码在有效范围内
    page = max(1, min(page, total_pages))
    
    # 计算当前页显示的集群范围
    start_idx = (page - 1) * clusters_per_page
    end_idx = min(start_idx + clusters_per_page, len(clusters))
    
    msg = f"🎯 <b>地址集群分析</b> (第{page}/{total_pages}页, 共{total_clusters}个)\n"
    msg += "─" * 35 + "\n\n"

    # 显示当前页的集群
    displayed_clusters = clusters[start_idx:end_idx]

    for cluster in displayed_clusters:
        cluster_id = cluster["cluster_id"]
        addresses = cluster["addresses"]
        address_count = cluster["address_count"]
        total_value = cluster["total_value"]
        common_tokens = cluster["common_tokens"]
        common_tokens_count = cluster["common_tokens_count"]
        avg_value = cluster["avg_value_per_address"]

        # 格式化总价值
        if total_value >= 1_000_000:
            value_str = f"${total_value/1_000_000:.2f}M"
        elif total_value >= 1_000:
            value_str = f"${total_value/1_000:.2f}K"
        else:
            value_str = f"${total_value:.0f}"

        msg += f"🏆 <b>集群 #{cluster_id}</b>\n"
        msg += f"💰 共同代币总价值: <b>{value_str}</b> | 平均: ${avg_value:,.0f}/地址\n"
        msg += f"👥 地址数量: <b>{address_count}</b> | 共同代币: <b>{common_tokens_count}</b>\n\n"

        # 显示共同持有的代币
        msg += "🪙 <b>共同持有代币</b>:\n"
        for i, token in enumerate(common_tokens[:5], 1):  # 最多显示5个代币
            symbol = token["symbol"]
            token_address = token["address"]
            cluster_value = token["cluster_value"]
            cluster_percentage = token["cluster_percentage"]

            # 格式化代币价值
            if cluster_value >= 1_000_000:
                token_value_str = f"${cluster_value/1_000_000:.2f}M"
            elif cluster_value >= 1_000:
                token_value_str = f"${cluster_value/1_000:.2f}K"
            else:
                token_value_str = f"${cluster_value:.0f}"

            # 计算地址平均价值
            avg_token_value = cluster_value / address_count
            if avg_token_value >= 1_000_000:
                avg_value_str = f"${avg_token_value/1_000_000:.2f}M"
            elif avg_token_value >= 1_000:
                avg_value_str = f"${avg_token_value/1_000:.2f}K"
            else:
                avg_value_str = f"${avg_token_value:.0f}"

            # 添加代币链接
            gmgn_link = f"https://gmgn.ai/sol/token/{token_address}"
            symbol_with_link = f"<a href='{gmgn_link}'>{symbol}</a>"

            msg += (
                f"  <b>{i}.</b> {symbol_with_link} {token_value_str} (平均{avg_value_str}/地址)\n"
            )

        if len(common_tokens) > 5:
            msg += f"  ... 还有 {len(common_tokens) - 5} 个代币\n"

        # 显示所有地址 (带GMGN链接)
        msg += f"\n📍 <b>集群地址</b> ({address_count}个):\n"
        for i, addr in enumerate(addresses, 1):
            addr_short = f"{addr[:6]}...{addr[-6:]}"
            gmgn_addr_link = f"https://gmgn.ai/sol/address/{addr}"
            msg += f"  {i}. <a href='{gmgn_addr_link}'>{addr_short}</a>\n"

        msg += "\n" + "─" * 30 + "\n\n"

    msg += f"\n🎯 <b>集群说明</b>\n"
    msg += f"• 按 代币数量×地址数量 综合评分排序\n"
    msg += f"• 百分比：集群在该代币中的持仓占大户总持仓的比例\n"

    return msg, page, total_pages


def format_target_token_rankings(ranking_result: Dict) -> str:
    """
    格式化目标代币排名分析结果为Telegram消息
    
    Args:
        ranking_result: 排名分析结果
        
    Returns:
        str: 格式化的消息文本
    """
    target_token = ranking_result.get("target_token", {})
    rankings = ranking_result.get("rankings", [])
    statistics = ranking_result.get("statistics", {})
    
    if not rankings:
        return "❌ 未找到持有目标代币的地址数据"
    
    symbol = target_token.get("symbol", "Unknown")
    total_addresses = statistics.get("total_addresses", 0)
    actual_holders = statistics.get("actual_holders", 0)
    conspiracy_count = statistics.get("conspiracy_wallets", 0)
    conspiracy_total_value = statistics.get("conspiracy_total_value", 0)
    avg_rank = statistics.get("average_rank", 0)
    median_rank = statistics.get("median_rank", 0)
    distribution = statistics.get("rank_distribution", {})
    analysis = statistics.get("analysis", "")
    
    # 计算阴谋钱包流通量占比
    conspiracy_supply_percentage = sum(r.get("target_supply_percentage", 0) for r in rankings if r.get("is_conspiracy_wallet", False))
    conspiracy_alpha_supply_percentage = sum(r.get("target_supply_percentage", 0) for r in rankings if r.get("is_conspiracy_alpha", False))
    conspiracy_beta_supply_percentage = sum(r.get("target_supply_percentage", 0) for r in rankings if r.get("is_conspiracy_beta", False))
    
    # 获取阴谋钱包统计
    conspiracy_alpha_count = statistics.get("conspiracy_alpha_wallets", 0)
    conspiracy_beta_count = statistics.get("conspiracy_beta_wallets", 0)
    
    # 计算分析地址流通量占比（只计算原始目标代币持有者，即有target_supply_percentage的地址）
    all_analysis_percentage = sum(r.get("target_supply_percentage", 0) for r in rankings if r.get("target_supply_percentage", 0) > 0)
    
    # 计算实际持有地址流通量占比（目标代币在钱包中排名≤10的地址）
    actual_holders_supply_percentage = sum(r.get("target_supply_percentage", 0) for r in rankings if r["target_token_rank"] <= 10)
    
    msg = f"📊 <b>{symbol} 价值排名分析</b>\n"
    msg += f"🎯 分析地址: <b>{total_addresses}</b> 个大户（{all_analysis_percentage:.1f}%）\n"
    msg += f"💎 实际持有: <b>{actual_holders}</b> 个 ({actual_holders_supply_percentage:.1f}%)\n"
    
    # 阴谋钱包信息 - 显示详细的α和β分类
    if conspiracy_count > 0:
        msg += f"🔴 阴谋钱包: <b>{conspiracy_count}</b> 个 ({conspiracy_supply_percentage:.1f}%)\n"
        detail_parts = []
        if conspiracy_alpha_count > 0:
            detail_parts.append(f"α型{conspiracy_alpha_count}个({conspiracy_alpha_supply_percentage:.1f}%)")
        if conspiracy_beta_count > 0:
            detail_parts.append(f"β型{conspiracy_beta_count}个({conspiracy_beta_supply_percentage:.1f}%)")
        if detail_parts:
            msg += f"   ├ {', '.join(detail_parts)}\n"
            msg += f"   └ α型：所有资产>50% | β型：除SOL/稳定币>50%\n"
    
    msg += "───────────────────────────────────\n\n"
    
    # 统计信息
    if avg_rank > 0:
        msg += f"📈 <b>排名统计</b> (仅统计持有者)\n"
        msg += f"• 平均排名: <b>第{avg_rank:.1f}名</b>\n"
        msg += f"• 中位数排名: <b>第{median_rank}名</b>\n\n"
    else:
        msg += f"📈 <b>排名统计</b>\n"
        msg += f"• 所有分析地址均未持有目标代币\n\n"
    
    # 计算每个排名的总价值和总供应量占比
    rank_values = {}  # {rank: total_value}
    rank_supply_percentages = {}  # {rank: total_supply_percentage}
    
    for ranking in rankings:
        rank = ranking["target_token_rank"]
        value = ranking["target_token_value"]
        supply_percentage = ranking.get("target_supply_percentage", 0)
        
        if rank <= 10:
            rank_key = f"第{rank}名"
        else:
            rank_key = ">10名"
        
        rank_values[rank_key] = rank_values.get(rank_key, 0) + value
        rank_supply_percentages[rank_key] = rank_supply_percentages.get(rank_key, 0) + supply_percentage
    
    # 排名分布（显示占流通量比例）
    msg += f"📊 <b>排名分布</b>  | 均值 | 总值 | 占流通量\n\n"
    
    # 定义排名区间和对应emoji
    rank_ranges = [
        ("第1名", "🥇"),
        ("第2名", "🥈"), 
        ("第3名", "🥉"),
        ("第4名", "🏅"),
        ("第5名", "🏅"),
        ("第6名", "⭐"),
        ("第7名", "⭐"),
        ("第8名", "⭐"),
        ("第9名", "⭐"),
        ("第10名", "⭐"),
    ]
    
    # 统计>10名的情况
    over_10_count = len([r for r in rankings if r["target_token_rank"] > 10])
    if over_10_count > 0:
        distribution[">10名"] = over_10_count
        rank_values[">10名"] = sum(r["target_token_value"] for r in rankings if r["target_token_rank"] > 10)
        rank_supply_percentages[">10名"] = sum(r.get("target_supply_percentage", 0) for r in rankings if r["target_token_rank"] > 10)
    
    for rank_key, emoji in rank_ranges:
        count = distribution.get(rank_key, 0)
        if count > 0:
            supply_percentage = rank_supply_percentages.get(rank_key, 0)
            value = rank_values.get(rank_key, 0)
            
            # 计算均值
            avg_value = value / count if count > 0 else 0
            
            # 格式化总值
            if value >= 1_000_000:
                value_str = f"${value/1_000_000:.1f}M"
            elif value >= 1_000:
                value_str = f"${value/1_000:.1f}K"
            else:
                value_str = f"${value:.0f}"
            
            # 格式化均值
            if avg_value >= 1_000_000:
                avg_value_str = f"${avg_value/1_000_000:.1f}M"
            elif avg_value >= 1_000:
                avg_value_str = f"${avg_value/1_000:.1f}K"
            else:
                avg_value_str = f"${avg_value:.0f}"
            
            msg += f"{emoji} {rank_key}: <b>{count}</b> 人 | {avg_value_str} | {value_str} | {supply_percentage:.2f}%\n"
    
    # 添加>10名统计
    if over_10_count > 0:
        supply_percentage = rank_supply_percentages.get(">10名", 0)
        value = rank_values.get(">10名", 0)
        
        # 计算>10名地址的平均持仓价值
        avg_value = value / over_10_count if over_10_count > 0 else 0
        
        # 格式化总值
        if value >= 1_000_000:
            value_str = f"${value/1_000_000:.1f}M"
        elif value >= 1_000:
            value_str = f"${value/1_000:.1f}K"
        else:
            value_str = f"${value:.0f}"
        
        # 格式化均值
        if avg_value >= 1_000_000:
            avg_value_str = f"${avg_value/1_000_000:.1f}M"
        elif avg_value >= 1_000:
            avg_value_str = f"${avg_value/1_000:.1f}K"
        else:
            avg_value_str = f"${avg_value:.0f}"
        
        msg += f"📉 >10名: <b>{over_10_count}</b> 人 | {avg_value_str} | {value_str} | {supply_percentage:.2f}%\n"
    
    msg += "\n───────────────────────────────────\n\n"
    
    msg += f"⭐️ <i>点击下方按钮查看对应排名的地址详情</i>\n"
    msg += f"📊 <i>所有百分比均为占代币流通量的比例</i>\n"
    
    return msg
