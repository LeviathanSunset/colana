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
from datetime import datetime
from typing import List, Dict, Optional
from ..utils.data_manager import DataManager

# 全局分析缓存，用于存储分析结果以供按钮回调使用
analysis_cache = {}


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
            "limit": 10,
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

                # 过滤掉SOL代币（原生代币，不需要分析）
                if symbol == "SOL":
                    continue

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

                # 只添加有价值的代币（排除SOL后）
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

    def analyze_token_holders(self, token_address: str, top_holders_count: int = None) -> Dict:
        """
        分析代币大户并返回代币统计信息
        专门为Bot优化，只返回必要的信息
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

        # 2. 分析每个大户的资产
        holder_analysis = []

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

        # 过滤总价值大于20U的代币，然后按总价值排序
        filtered_tokens = [token for token in all_tokens.values() if token["total_value"] >= 20]
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
            f"发现 {len(all_tokens)} 种代币，过滤后 {len(filtered_tokens)} 种代币(≥$20)，总价值 ${sum(token['total_value'] for token in sorted_tokens):,.2f}"
        )

        return analysis_result


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
        # 收集该地址持有的所有代币价值（前10大持仓）
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
        
        # 如果目标代币不在前10名，需要加上目标代币价值到总价值中
        if target_rank > 10 and target_value > 0:
            portfolio_total_value += target_value
        
        target_percentage = 0
        is_conspiracy_wallet = False
        
        if portfolio_total_value > 0 and target_value > 0:
            target_percentage = (target_value / portfolio_total_value) * 100
            is_conspiracy_wallet = target_percentage > 50  # 阴谋钱包：目标代币占比>50%
        
        # 获取目标代币的持有百分比（占总供应量）
        target_supply_percentage = 0
        if holder_address in original_target_holders:
            target_supply_percentage = original_target_holders[holder_address]["holdAmountPercentage"]
        
        address_rankings.append({
            "holder_address": holder_address,
            "holder_rank": holder_rank,
            "target_token_rank": target_rank,
            "target_token_value": target_value,
            "target_supply_percentage": target_supply_percentage,  # 占总供应量百分比
            "total_tokens": len(holder_tokens),
            "portfolio_value": portfolio_total_value,
            "target_percentage": target_percentage,
            "is_conspiracy_wallet": is_conspiracy_wallet
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
        
        # 基础统计（只计算实际持有的地址，排除>10名）
        actual_ranks = [r for r in ranks if r <= 10]
        if actual_ranks:
            avg_rank = sum(actual_ranks) / len(actual_ranks)
            median_rank = sorted(actual_ranks)[len(actual_ranks) // 2]
        else:
            avg_rank = 0
            median_rank = 0
        
        # 阴谋钱包统计
        conspiracy_wallets = [addr for addr in address_rankings if addr["is_conspiracy_wallet"]]
        conspiracy_count = len(conspiracy_wallets)
        conspiracy_total_value = sum(wallet["target_token_value"] for wallet in conspiracy_wallets)
        
        # 智能分析
        analysis_text = _generate_ranking_analysis(address_rankings, avg_rank, rank_distribution)
        
        statistics = {
            "total_addresses": len(address_rankings),
            "actual_holders": len(actual_ranks),  # 实际持有目标代币的地址数
            "conspiracy_wallets": conspiracy_count,  # 阴谋钱包数量
            "conspiracy_total_value": conspiracy_total_value,  # 阴谋钱包总价值
            "average_rank": avg_rank,
            "median_rank": median_rank,
            "rank_distribution": rank_distribution,
            "top3_count": len([r for r in ranks if r <= 3]),
            "top5_count": len([r for r in ranks if r <= 5]),
            "top10_count": len([r for r in ranks if r <= 10]),
            "over10_count": len([r for r in ranks if r > 10]),
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
    conspiracy_count = len(conspiracy_wallets)
    conspiracy_supply = sum(r.get("target_supply_percentage", 0) for r in conspiracy_wallets)
    
    # 排名分布统计
    top3_count = len([r for r in rankings if r["target_token_rank"] <= 3])
    top5_count = len([r for r in rankings if r["target_token_rank"] <= 5])
    top10_count = len([r for r in rankings if r["target_token_rank"] <= 10])
    
    # 百分比计算
    top3_pct = (top3_count / total_addresses) * 100 if total_addresses > 0 else 0
    top5_pct = (top5_count / total_addresses) * 100 if total_addresses > 0 else 0
    top10_pct = (top10_count / total_addresses) * 100 if total_addresses > 0 else 0
    
    # 总流通量
    total_supply = sum(r.get("target_supply_percentage", 0) for r in rankings)
    conspiracy_risk_ratio = conspiracy_supply / total_supply if total_supply > 0 else 0
    
    return {
        "total_addresses": total_addresses,
        "conspiracy_count": conspiracy_count,
        "conspiracy_supply": conspiracy_supply,
        "conspiracy_risk_ratio": conspiracy_risk_ratio,
        "top3_count": top3_count,
        "top5_count": top5_count,
        "top10_count": top10_count,
        "top3_pct": top3_pct,
        "top5_pct": top5_pct,
        "top10_pct": top10_pct,
        "total_supply": total_supply
    }


def _analyze_conspiracy_risk(metrics: Dict) -> str:
    """分析阴谋钱包风险"""
    conspiracy_count = metrics["conspiracy_count"]
    conspiracy_supply = metrics["conspiracy_supply"]
    conspiracy_risk_ratio = metrics["conspiracy_risk_ratio"]
    
    if conspiracy_count == 0:
        return "✅ 无阴谋风险：未发现过度集中持仓钱包"
    
    if conspiracy_risk_ratio >= 0.6:
        return f"🔴 阴谋风险极高：{conspiracy_count}个钱包过度集中({conspiracy_supply:.1f}%)，砸盘风险大"
    elif conspiracy_risk_ratio >= 0.3:
        return f"🟡 阴谋风险中等：{conspiracy_count}个钱包集中持仓({conspiracy_supply:.1f}%)，需谨慎"
    else:
        return f"🟢 阴谋风险较低：{conspiracy_count}个集中钱包占比{conspiracy_supply:.1f}%，可控"


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
    top10_pct = metrics["top10_pct"]
    
    if top3_pct >= 50:
        return f"💪 {top3_pct:.1f}%大户将其列为前3重仓，信心度极高"
    elif top5_pct >= 50:
        return f"⭐ {top5_pct:.1f}%大户将其列为前5配置，认可度较高"
    elif top10_pct >= 50:
        return f"📊 {top10_pct:.1f}%大户将其列为前10配置，有基础共识"
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
    top10_pct = metrics["top10_pct"]
    
    if avg_rank <= 3 and top3_pct >= 20:
        return "极强"
    elif avg_rank <= 5 and top5_pct >= 15:
        return "较强"
    elif avg_rank <= 8 and top10_pct >= 10:
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

    # 1. 构建地址-代币映射
    address_tokens = {}  # {address: set(token_addresses)}
    token_holders = {}  # {token_address: set(addresses)}

    for token in all_tokens:
        token_address = token["address"]
        holders_details = token.get("holders_details", [])

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
    token_stats: Dict, max_tokens: int = None, sort_by: str = "value", cache_key: str = None
) -> tuple:
    """
    格式化代币统计表格，专门为Telegram消息优化

    Args:
        token_stats: 代币统计数据
        max_tokens: 显示的最大代币数量 (如果为None，从配置文件读取)
        sort_by: 排序方式 ('value' 按总价值, 'count' 按持有人数)
        cache_key: 缓存键，用于生成详情按钮

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

    # 构建表格
    msg = f"🔥 <b>大户热门代币排行榜</b> ({sort_icon} {sort_desc})\n"
    msg += f"💰 总资产: <b>${total_portfolio_value:,.0f}</b>\n"
    msg += f"🔢 代币种类: <b>{total_unique_tokens}</b>\n"
    msg += "─" * 35 + "\n"

    # 创建按钮布局
    markup = None
    detail_buttons = []

    # 为前10个代币创建详情按钮
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
        msg += f"💰 总价值: <b>{value_str}</b> | 平均: ${avg_value:,.0f}/地址\n"
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

            # 添加代币链接
            gmgn_link = f"https://gmgn.ai/sol/token/{token_address}"
            symbol_with_link = f"<a href='{gmgn_link}'>{symbol}</a>"

            msg += (
                f"  <b>{i}.</b> {symbol_with_link} {token_value_str} ({cluster_percentage:.1f}%)\n"
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
    
    # 计算阴谋钱包流通量占比（需要在前面计算，因为后面会用到）
    conspiracy_supply_percentage = sum(r.get("target_supply_percentage", 0) for r in rankings if r.get("is_conspiracy_wallet", False))
    
    msg = f"📊 <b>{symbol} 价值排名分析</b>\n"
    msg += f"🎯 分析地址: <b>{total_addresses}</b> 个大户\n"
    msg += f"💎 实际持有: <b>{actual_holders}</b> 个 ({(actual_holders/total_addresses)*100:.1f}%)\n"
    
    # 阴谋钱包信息
    if conspiracy_count > 0:
        conspiracy_percentage = (conspiracy_count / total_addresses) * 100
        if conspiracy_total_value >= 1_000_000:
            conspiracy_value_str = f"${conspiracy_total_value/1_000_000:.2f}M"
        elif conspiracy_total_value >= 1_000:
            conspiracy_value_str = f"${conspiracy_total_value/1_000:.2f}K"
        else:
            conspiracy_value_str = f"${conspiracy_total_value:.0f}"
        msg += f"🔴 阴谋钱包: <b>{conspiracy_count}</b> 个 ({conspiracy_supply_percentage:.1f}%) | 总值: {conspiracy_value_str}\n"
    
    msg += "─" * 35 + "\n\n"
    
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
    msg += f"📊 <b>排名分布</b> (占流通量比例)\n"
    
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
            if value >= 1_000_000:
                value_str = f"${value/1_000_000:.2f}M"
            elif value >= 1_000:
                value_str = f"${value/1_000:.2f}K"
            else:
                value_str = f"${value:.0f}"
            msg += f"{emoji} {rank_key}: <b>{count}</b> 人 ({value_str}) {supply_percentage:.2f}%\n"
    
    # 添加>10名统计
    if over_10_count > 0:
        supply_percentage = rank_supply_percentages.get(">10名", 0)
        value = rank_values.get(">10名", 0)
        if value >= 1_000_000:
            value_str = f"${value/1_000_000:.2f}M"
        elif value >= 1_000:
            value_str = f"${value/1_000:.2f}K"
        else:
            value_str = f"${value:.0f}"
        # 计算>10名地址的平均持仓价值
        avg_value = value / over_10_count if over_10_count > 0 else 0
        if avg_value >= 1000:
            avg_value_str = f"${avg_value/1000:.1f}K"
        else:
            avg_value_str = f"${avg_value:.0f}"
        msg += f"📉 >10名: <b>{over_10_count}</b> 人 ({value_str}, 均值: {avg_value_str}) {supply_percentage:.2f}%\n"
    
    # Top排名统计 - 计算流通量占比
    top3_count = statistics.get("top3_count", 0)
    top5_count = statistics.get("top5_count", 0) 
    top10_count = statistics.get("top10_count", 0)
    
    # 计算各层级的流通量占比
    top3_supply_percentage = sum(r.get("target_supply_percentage", 0) for r in rankings if r["target_token_rank"] <= 3)
    top5_supply_percentage = sum(r.get("target_supply_percentage", 0) for r in rankings if r["target_token_rank"] <= 5)
    top10_supply_percentage = sum(r.get("target_supply_percentage", 0) for r in rankings if r["target_token_rank"] <= 10)
    
    msg += f"\n🎯 <b>重点统计</b>\n"
    msg += f"🔥 前3名: <b>{top3_count}</b> 人 ({top3_supply_percentage:.2f}%)\n"
    msg += f"⭐ 前5名: <b>{top5_count}</b> 人 ({top5_supply_percentage:.2f}%)\n"
    msg += f"📈 前10名: <b>{top10_count}</b> 人 ({top10_supply_percentage:.2f}%)\n"
    
    # 阴谋钱包统计
    if conspiracy_count > 0:
        msg += f"🔴 阴谋钱包: <b>{conspiracy_count}</b> 人 ({conspiracy_supply_percentage:.2f}%) | 持仓占比>50%\n"
    
    msg += "\n"
    
    # 智能分析
    msg += f"🧠 <b>智能分析</b>\n"
    msg += f"{analysis}\n\n"
    
    msg += f"⭐ <i>点击下方按钮查看对应排名的地址详情</i>\n"
    msg += f"📊 <i>所有百分比均为占代币流通量的比例</i>\n"
    
    return msg
