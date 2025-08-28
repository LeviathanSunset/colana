"""
Jupiter 代币爬虫服务
爬取 Jupiter 交易平台的热门代币数据
"""

import requests
import time
import json
import os
from typing import List, Dict, Optional
from datetime import datetime
from ..utils.data_manager import DataManager
from ..core.config import get_config


class JupiterCrawler:
    """Jupiter 代币爬虫"""
    
    def __init__(self):
        self.base_url = "https://datapi.jup.ag"
        self.session = requests.Session()
        self.data_manager = DataManager()
        self.config = get_config()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9',
            'Origin': 'https://jup.ag',
            'Referer': 'https://jup.ag/',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-site'
        })
        
        # 从配置系统获取默认参数
        jupiter_config = self.config.jupiter
        self.default_params = {
            'mintAuthorityDisabled': 'true',
            'freezeAuthorityDisabled': 'true',
            'maxMcap': str(jupiter_config.max_mcap),
            'hasSocials': str(jupiter_config.has_socials).lower(),
            'minTokenAge': str(jupiter_config.min_token_age)
        }
    
    def fetch_top_traded_tokens(self, 
                               period: str = None, 
                               max_mcap: int = None,
                               min_token_age: int = None,
                               has_socials: bool = None,
                               min_net_volume_24h: int = None,
                               min_net_volume_5m: int = None) -> List[Dict]:
        """
        获取热门交易代币
        
        Args:
            period: 时间周期 (5min, 24h, 7d, 30d)，默认使用配置值
            max_mcap: 最大市值，默认使用配置值
            min_token_age: 最小代币年龄（秒），默认使用配置值
            has_socials: 是否需要社交媒体信息，默认使用配置值
            min_net_volume_24h: 最小24小时净交易量，默认不限制
            min_net_volume_5m: 最小5分钟净交易量，默认不限制
            
        Returns:
            代币列表
        """
        try:
            # 使用配置值作为默认值
            jupiter_config = self.config.jupiter
            period = period if period is not None else jupiter_config.period
            max_mcap = max_mcap if max_mcap is not None else jupiter_config.max_mcap
            min_token_age = min_token_age if min_token_age is not None else jupiter_config.min_token_age
            has_socials = has_socials if has_socials is not None else jupiter_config.has_socials
            
            url = f"{self.base_url}/v1/pools/toptraded/{period}"
            
            params = {
                'mintAuthorityDisabled': 'true',
                'freezeAuthorityDisabled': 'true',
                'maxMcap': str(max_mcap),
                'hasSocials': str(has_socials).lower(),
                'minTokenAge': str(min_token_age)
            }
            
            # 添加最小净交易量参数（根据周期选择正确的参数名）
            if period == '5m' and min_net_volume_5m is not None:
                params['minNetVolume5m'] = str(min_net_volume_5m)
            elif min_net_volume_24h is not None:
                params['minNetVolume24h'] = str(min_net_volume_24h)
            
            print(f"🔍 正在获取Jupiter热门代币数据...")
            print(f"📊 参数: 周期={period}, 最大市值=${max_mcap:,}, 最小年龄={min_token_age}秒, 需要社交={has_socials}")
            if period == '5m' and min_net_volume_5m:
                print(f"📊 最小5min净交易量: ${min_net_volume_5m:,}")
            elif min_net_volume_24h:
                print(f"📊 最小24h净交易量: ${min_net_volume_24h:,}")
            
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # 处理不同的返回格式
            if isinstance(data, list):
                print(f"✅ 成功获取 {len(data)} 个代币")
                return data
            elif isinstance(data, dict):
                # 可能包含在某个字段中
                if 'data' in data:
                    tokens = data['data']
                elif 'pools' in data:
                    tokens = data['pools']
                elif 'tokens' in data:
                    tokens = data['tokens']
                else:
                    # 打印数据结构以便调试
                    print(f"📊 返回数据结构: {list(data.keys())}")
                    # 尝试获取第一个列表字段
                    for key, value in data.items():
                        if isinstance(value, list):
                            print(f"✅ 在字段 '{key}' 中找到 {len(value)} 个项目")
                            return value
                    print(f"⚠️ 未找到代币列表，返回空")
                    return []
                
                if isinstance(tokens, list):
                    print(f"✅ 成功获取 {len(tokens)} 个代币")
                    return tokens
                else:
                    print(f"⚠️ 代币数据格式异常: {type(tokens)}")
                    return []
            else:
                print(f"⚠️ 返回数据格式异常: {type(data)}")
                return []
                
        except requests.exceptions.RequestException as e:
            print(f"❌ 网络请求失败: {e}")
            return []
        except json.JSONDecodeError as e:
            print(f"❌ JSON解析失败: {e}")
            return []
        except Exception as e:
            print(f"❌ 获取代币数据失败: {e}")
            return []
    
    def get_token_info(self, mint_address: str) -> Optional[Dict]:
        """
        获取单个代币详细信息
        
        Args:
            mint_address: 代币地址
            
        Returns:
            代币信息字典
        """
        try:
            # 这里可以扩展获取更详细的代币信息
            # 暂时返回基础信息
            return {
                'mint': mint_address,
                'source': 'jupiter',
                'timestamp': time.time()
            }
        except Exception as e:
            print(f"❌ 获取代币信息失败 {mint_address}: {e}")
            return None
    
    def parse_token_data(self, token_data: Dict) -> Dict:
        """
        解析代币数据，标准化格式
        
        Args:
            token_data: 原始代币数据
            
        Returns:
            标准化的代币信息
        """
        try:
            # 从baseAsset中提取代币信息
            base_asset = token_data.get('baseAsset', {})
            
            # 提取关键信息
            parsed = {
                'mint': base_asset.get('id', ''),
                'symbol': base_asset.get('symbol', ''),
                'name': base_asset.get('name', ''),
                'decimals': base_asset.get('decimals', 0),
                'supply': base_asset.get('totalSupply', 0),
                'market_cap': base_asset.get('mcap') or base_asset.get('fdv', 0),
                'volume_24h': token_data.get('volume24h', 0),
                'price': base_asset.get('usdPrice', 0),
                'price_change_24h': 0,  # 需要从stats24h中计算
                'liquidity': token_data.get('liquidity', 0),
                'holders': base_asset.get('holderCount', 0),
                'created_at': token_data.get('createdAt', ''),
                'socials': {
                    'twitter': base_asset.get('twitter', ''),
                    'website': base_asset.get('website', '')
                },
                'source': 'jupiter',
                'fetch_time': datetime.now().isoformat(),
                # 额外的Jupiter特有信息
                'pool_id': token_data.get('id', ''),
                'dex': token_data.get('dex', ''),
                'launchpad': base_asset.get('launchpad', ''),
                'organic_score': base_asset.get('organicScore', 0),
                'audit': base_asset.get('audit', {})
            }
            
            # 从stats24h中提取价格变化
            stats_24h = base_asset.get('stats24h', {})
            if stats_24h:
                parsed['price_change_24h'] = stats_24h.get('priceChange', 0)
                parsed['holder_change_24h'] = stats_24h.get('holderChange', 0)
                parsed['buy_volume_24h'] = stats_24h.get('buyVolume', 0)
                parsed['sell_volume_24h'] = stats_24h.get('sellVolume', 0)
            
            # 验证mint地址
            if not parsed['mint']:
                print(f"⚠️ 代币mint地址为空，跳过")
                return {}
            
            return parsed
            
        except Exception as e:
            print(f"❌ 解析代币数据失败: {e}")
            return {}
    
    def save_tokens_to_file(self, tokens: List[Dict], filename: str = None) -> str:
        """
        保存代币数据到文件
        
        Args:
            tokens: 代币列表
            filename: 文件名（可选）
            
        Returns:
            保存的文件路径
        """
        try:
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"jupiter_tokens_{timestamp}.json"
            
            # 使用统一存储管理器
            filepath = self.data_manager.get_file_path("jupiter", filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(tokens, f, indent=2, ensure_ascii=False)
            
            print(f"💾 代币数据已保存到: {filepath}")
            return filepath
            
        except Exception as e:
            print(f"❌ 保存文件失败: {e}")
            return ""
    
    def filter_tokens(self, tokens: List[Dict], 
                     min_volume: float = 0,
                     min_market_cap: float = 0,
                     min_holders: int = 0) -> List[Dict]:
        """
        过滤代币
        
        Args:
            tokens: 代币列表
            min_volume: 最小24h交易量
            min_market_cap: 最小市值
            min_holders: 最小持有者数量
            
        Returns:
            过滤后的代币列表
        """
        filtered = []
        
        for token in tokens:
            try:
                volume = float(token.get('volume_24h', 0))
                market_cap = float(token.get('market_cap', 0))
                holders = int(token.get('holders', 0))
                
                if (volume >= min_volume and 
                    market_cap >= min_market_cap and 
                    holders >= min_holders):
                    filtered.append(token)
                    
            except (ValueError, TypeError):
                continue
        
        print(f"🔍 过滤后剩余 {len(filtered)} 个代币")
        return filtered


class JupiterAnalyzer:
    """Jupiter 代币分析器"""
    
    def __init__(self):
        self.crawler = JupiterCrawler()
        self.config = self.crawler.config
    
    def analyze_trending_tokens(self, limit: int = None) -> List[Dict]:
        """
        分析热门代币
        
        Args:
            limit: 限制分析数量，默认使用配置值
            
        Returns:
            分析结果列表
        """
        try:
            # 使用配置的默认值
            if limit is None:
                limit = self.config.jupiter.default_token_count
            
            # 确保不超过最大限制
            limit = min(limit, self.config.jupiter.max_tokens_per_analysis)
            
            # 获取热门代币
            raw_tokens = self.crawler.fetch_top_traded_tokens()
            
            if not raw_tokens:
                print("❌ 未获取到代币数据")
                return []
            
            # 解析和标准化数据
            parsed_tokens = []
            for token_data in raw_tokens[:limit]:
                parsed = self.crawler.parse_token_data(token_data)
                if parsed:
                    parsed_tokens.append(parsed)
            
            # 保存数据
            if parsed_tokens:
                self.crawler.save_tokens_to_file(parsed_tokens)
            
            return parsed_tokens
            
        except Exception as e:
            print(f"❌ 分析热门代币失败: {e}")
            return []
    
    def get_tokens_for_analysis(self, count: int = None) -> List[str]:
        """
        获取需要分析的代币地址列表
        
        Args:
            count: 代币数量，默认使用配置值
            
        Returns:
            代币地址列表
        """
        try:
            # 使用配置的默认值
            if count is None:
                count = self.config.jupiter.default_token_count
            
            tokens = self.analyze_trending_tokens(limit=count)
            addresses = [token['mint'] for token in tokens if token.get('mint')]
            
            print(f"📋 准备分析 {len(addresses)} 个代币")
            return addresses
            
        except Exception as e:
            print(f"❌ 获取分析代币列表失败: {e}")
            return []


# 测试函数
def test_jupiter_crawler():
    """测试Jupiter爬虫功能"""
    print("🧪 测试Jupiter爬虫功能...")
    
    analyzer = JupiterAnalyzer()
    tokens = analyzer.get_tokens_for_analysis(5)
    
    if tokens:
        print(f"✅ 测试成功，获取到 {len(tokens)} 个代币地址:")
        for i, addr in enumerate(tokens, 1):
            print(f"  {i}. {addr}")
    else:
        print("❌ 测试失败，未获取到代币")


if __name__ == "__main__":
    test_jupiter_crawler()