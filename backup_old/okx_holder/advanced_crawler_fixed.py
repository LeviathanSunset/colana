#!/usr/bin/env python3
"""
OKX Web3 高级爬虫 - 基于真实浏览器请求头
完整的持有者分析和资产提取功能
"""

import requests
import json
import time
import random
from datetime import datetime
from typing import List, Dict, Optional
from config import *

class OKXAdvancedCrawler:
    """
    基于真实请求头的OKX Web3爬虫
    使用从浏览器捕获的完整认证信息
    """
    
    def __init__(self, real_headers: Dict = None):
        """初始化爬虫"""
        self.session = requests.Session()
        
        # 基础请求头 - 模拟真实浏览器
        self.headers = {
            'accept': 'application/json',
            'accept-encoding': 'gzip, deflate, br, zstd',
            'accept-language': 'en-US,en;q=0.9,zh-HK;q=0.8,zh-CN;q=0.7,zh;q=0.6,es-MX;q=0.5,es;q=0.4,ru-RU;q=0.3,ru;q=0.2',
            'app-type': 'web',
            'cache-control': 'no-cache',
            'dnt': '1',
            'pragma': 'no-cache',
            'priority': 'u=1, i',
            'sec-ch-ua': '"Chromium";v="130", "Google Chrome";v="130", "Not?A_Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
            'x-cdn': 'https://web3.okx.com'
        }
        
        # 设置真实请求头（如果提供）
        self.real_headers = real_headers or {}
        
        print("🚀 OKX Web3 高级爬虫启动")
        print("=" * 50)
        
        # 显示使用说明
        self._show_usage_instructions()
    
    def _show_usage_instructions(self):
        """显示如何获取真实认证头的说明"""
        print("🔧 使用说明:")
        print("如需更精确的认证，请在浏览器开发者工具中获取最新的认证头信息")
        print("详细步骤可查看源码注释")
        print()
    
    def get_token_holders(self, token_address: str, chain_id: str = "501", max_retries: int = 3) -> List[Dict]:
        """
        获取代币持有者排行榜
        
        Args:
            token_address: 代币合约地址
            chain_id: 区块链ID (默认501为Solana)
            max_retries: 最大重试次数
            
        Returns:
            持有者列表
        """
        for attempt in range(1, max_retries + 1):
            if attempt > 1:
                print(f"� 重试获取持有者信息... (尝试 {attempt}/{max_retries})")
            
            current_timestamp = str(int(time.time() * 1000))
            
            url = "https://web3.okx.com/priapi/v1/dx/market/v2/holders/ranking-list"
            params = {
                'chainId': chain_id,
                'tokenAddress': token_address,
                'currentUserWalletAddress': '0xa6b67e6f61dba6363b36bbcef80d971a6d1f0ce5',
                't': current_timestamp
            }
            
            # 合并真实请求头
            headers = self.headers.copy()
            headers.update({
                'cookie': 'devId=31011088-da0a-4bd8-8f3d-9731400b5208; locale=en_US; _monitor_extras={"deviceId":"uC3r8hJBpqO__FJ2_Z2NMj","eventId":106,"sequenceNumber":106}',
                'devid': '31011088-da0a-4bd8-8f3d-9731400b5208',
                'x-request-timestamp': current_timestamp,
                'referer': f'https://web3.okx.com/token/solana/{token_address}'
            })
            
            try:
                response = self.session.get(url, params=params, headers=headers, timeout=30)
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        
                        if data.get('code') == 0:
                            holders_data = data.get('data', {})
                            
                            # 尝试不同的数据路径
                            holders = []
                            if isinstance(holders_data, dict):
                                # 尝试多个可能的键名
                                possible_keys = ['holderRankingList', 'data', 'holders', 'list', 'ranking']
                                for key in possible_keys:
                                    if key in holders_data and isinstance(holders_data[key], list):
                                        holders = holders_data[key]
                                        break
                            
                            if holders:
                                print(f"✅ 获取到 {len(holders)} 个持有者，分析前 {min(20, len(holders))} 个大户")
                                return holders[:20]  # 返回前20个大户
                            else:
                                print("⚠️  未找到持有者数据")
                                return []
                        else:
                            print(f"❌ API返回错误: {data.get('msg', '未知错误')}")
                            
                    except json.JSONDecodeError as e:
                        print(f"❌ JSON解析失败: {str(e)}")
                        
                else:
                    print(f"❌ HTTP错误 {response.status_code}")
                    
                # 根据状态码决定是否重试
                if response.status_code in [429, 500, 502, 503, 504]:
                    if attempt < max_retries:
                        delay = random.uniform(2, 5)
                        print(f"⏱️  等待 {delay:.1f} 秒后重试...")
                        time.sleep(delay)
                        continue
                
                break
                
            except requests.exceptions.RequestException as e:
                print(f"❌ 请求异常: {str(e)}")
                if attempt < max_retries:
                    delay = random.uniform(2, 5)
                    print(f"⏱️  等待 {delay:.1f} 秒后重试...")
                    time.sleep(delay)
                    continue
                else:
                    break
        
        print("❌ 获取持有者信息失败")
        return []

    def get_wallet_assets(self, wallet_address: str) -> Dict:
        """
        获取钱包资产组合信息 - 使用正确的POST API
        """
        current_timestamp = str(int(time.time() * 1000))
        
        # 正确的POST API端点
        url = "https://web3.okx.com/priapi/v2/wallet/asset/profile/all/explorer"
        params = {'t': current_timestamp}
        
        payload = {
            "userUniqueId": "",
            "hideValueless": False,
            "address": wallet_address,
            "forceRefresh": True,
            "page": 1,
            "limit": 10,
            "chainIndexes": []
        }
        
        headers = self.real_headers.copy()
        headers.update({
            'content-type': 'application/json',
            'content-length': '156',
            'origin': 'https://web3.okx.com',
            'referer': f'https://web3.okx.com/portfolio/{wallet_address}',
            'x-request-timestamp': current_timestamp,
            # 使用最新的认证头
            'device-token': '01980a38-038a-44d9-8da3-a8276bbcb5b9',
            'devid': '01980a38-038a-44d9-8da3-a8276bbcb5b9',
            'platform': 'web',
            'x-fptoken': 'eyJraWQiOiIxNjgzMzgiLCJhbGciOiJFUzI1NiJ9.eyJpYXQiOjE3NTUwODc5ODcsImVmcCI6IkJZc2ZyTkt6UU4yeFo3aXhqL09IeDRUSjBQaDViZlg0QjhiMTQrTGlHK21NdEt6WWx4TWpFdi9yK0o2MXlCcnIiLCJkaWQiOiIwMTk4MGEzOC0wMzhhLTQ0ZDktOGRhMy1hODI3NmJiY2I1YjkiLCJjcGsiOiJNRmt3RXdZSEtvWkl6ajBDQVFZSUtvWkl6ajBEQVFjRFFnQUVGOGE4RnFDNElLWDJxSHFaOHhaamJnd3BiMDloU2VCSWdxSkdjZ1FEWng0SEp2Z1lIN0g3NE5QblZsRHFWWWNUR0VBWm41aUw4bWdEQTVKbjY5SHJ5Zz09In0.Jya0xtvUWaGgUnThzmsnzgym8-AdL6Zkg14n8VnwfBA32JIAfldhlZgVmnEzuyNPAj3zBuJf9FAo2bvvPjyC1Q',
            'x-fptoken-signature': '{P1363}JQcuHd1UbUnWjo0685p82LTBajuRHZt3hwqvlDcKD/gzHVpzQmJv1spQhmaN6A27NWZPNh0DWjK7jMez+k/ynw==',
            'x-id-group': '2131150883586580003-c-27',
            'x-locale': 'en_US',
            'x-site-info': '==QfxojI5RXa05WZiwiIMFkQPx0Rfh1SPJiOiUGZvNmIsICUKJiOi42bpdWZyJye',
            'x-simulated-trading': 'undefined',
            'x-utc': '0',
            'x-zkdex-env': '0',
        })
        
        # 更新cookie为最新的认证cookie
        cookie_str = 'connected=0; devId=01980a38-038a-44d9-8da3-a8276bbcb5b9; ok_site_info===QfxojI5RXa05WZiwiIMFkQPx0Rfh1SPJiOiUGZvNmIsICUKJiOi42bpdWZyJye; locale=en_US; ok-exp-time=1755087984028; ok_prefer_currency=0%7C1%7Cfalse%7CUSD%7C2%7C%24%7C1%7C1%7CUSD; ok_prefer_udColor=0; ok_prefer_udTimeZone=0; fingerprint_id=01980a38-038a-44d9-8da3-a8276bbcb5b9; first_ref=https%3A%2F%2Fweb3.okx.com%2Ftoken%2Fsolana%2FFbGsCHv8qPvUdmomVAiG72ET5D5kgBJgGoxxfMZipump; ok_global={%22g_t%22:2}; okg.currentMedia=xl; connectedWallet=0; _gid=GA1.2.1926170199.1755087985; tmx_session_id=ulmvrdkaeun_1755087985421; fp_s=0; mse=nf=7; _ga_G0EKWWQGTZ=GS2.1.s1755085758$o90$g1$t1755088135$j33$l0$h0; _ga=GA1.1.2083537763.1750302376; ok-ses-id=+zZlho7BSk0iSdxx0zcdBBc4RryYtehxcoR+q9vAqEdkq1SMUySs8MR6LBRda2P+EIvbv1kHPbDCnu6joMGUQ78M4Ba7LBTLRfmYwB8qYANFdtFOlF6A0OsvrWGdfGfc; traceId=2131150883586580003; ok_prefer_exp=1; _monitor_extras={"deviceId":"KmpeI8VVHan-2zL3_DbOJB","eventId":4903,"sequenceNumber":4903}'
        headers['cookie'] = cookie_str
        
        try:
            response = self.session.post(url, params=params, json=payload, headers=headers, timeout=30)
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    
                    if data.get('code') == 0:
                        assets_data = data.get('data', {})
                        tokens_info = assets_data.get('tokens', {})
                        token_list = tokens_info.get('tokenlist', [])
                        
                        if token_list:
                            # 计算总价值 - 使用正确的字段名称
                            total_value = 0
                            for token in token_list:
                                try:
                                    value = float(token.get('currencyAmount', 0) or 0)
                                    total_value += value
                                except (ValueError, TypeError):
                                    continue
                            
                            print(f"💰 总资产: ${total_value:,.2f} (包含 {len(token_list)} 个代币)")
                        else:
                            print("⚠️  未找到代币列表")
                        
                        return assets_data
                    else:
                        print(f"❌ API返回错误: {data.get('msg', '未知错误')}")
                        
                except json.JSONDecodeError as e:
                    print(f"❌ JSON解析失败: {str(e)}")
            else:
                print(f"❌ HTTP错误 {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            print(f"❌ 请求异常: {str(e)}")
        
        return {}
    
    def extract_top_tokens(self, assets_data: Dict, top_n: int = None) -> List[Dict]:
        """
        从资产数据中提取价值最高的代币
        如果top_n为None，则返回所有有价值的代币
        """
        all_tokens = []
        
        # 根据测试结果，使用确定的数据路径
        tokens_info = assets_data.get('tokens', {})
        token_list = tokens_info.get('tokenlist', [])
        
        if not token_list:
            print("❌ extract_top_tokens: 未找到代币列表")
            return []
        
        for i, token in enumerate(token_list):
            try:
                # 使用验证过的字段名称
                symbol = token.get('symbol', 'Unknown')
                name = token.get('name', 'Unknown')
                chain = token.get('chainName', 'Unknown')
                address = token.get('contractAddress', '')
                
                # 数值字段，需要转换 - 使用正确的字段名称
                balance_str = token.get('coinAmount', '0')
                price_str = token.get('coinUnitPrice', '0')
                value_str = token.get('currencyAmount', '0')  # 修正：使用 currencyAmount 而不是 totalValueUsd
                
                # 转换为数值类型
                try:
                    balance = float(balance_str) if balance_str else 0
                    price_usd = float(price_str) if price_str else 0
                    value_usd = float(value_str) if value_str else 0
                except (ValueError, TypeError) as e:
                    continue
                
                token_info = {
                    'chain': chain,
                    'symbol': symbol,
                    'name': name,
                    'address': address,
                    'balance': balance,
                    'value_usd': value_usd,
                    'price_usd': price_usd
                }
                
                # 只添加有价值的代币
                if token_info['value_usd'] > 0:
                    all_tokens.append(token_info)
                
            except Exception as e:
                continue
        
        # 按价值排序
        all_tokens.sort(key=lambda x: x['value_usd'], reverse=True)
        
        # 如果指定了top_n，则返回前N个，否则返回所有
        if top_n is not None:
            return all_tokens[:top_n]
        else:
            return all_tokens
    
    def analyze_holders(self, token_address: str, top_holders_count: int = 20) -> Dict:
        """
        分析代币大户的资产组合
        
        Args:
            token_address: 代币合约地址
            top_holders_count: 分析的大户数量
            
        Returns:
            分析结果字典
        """
        print(f"🎯 开始分析代币: {token_address}")
        print("-" * 50)
        
        # 1. 获取持有者排行榜
        holders = self.get_token_holders(token_address)
        
        if not holders:
            print("❌ 无法获取持有者信息")
            return {}
        
        print()
        
        # 2. 分析每个大户的资产
        holder_analysis = []
        
        for i, holder in enumerate(holders[:top_holders_count], 1):
            # 从explorerUrl中提取钱包地址
            explorer_url = holder.get('explorerUrl', '')
            if 'solscan.io/account/' in explorer_url:
                wallet_address = explorer_url.split('solscan.io/account/')[-1]
            else:
                wallet_address = holder.get('holderAddress', '')
            
            if not wallet_address:
                print(f"⚠️  大户 #{i} 无法获取钱包地址")
                continue
            
            print(f"👤 大户 #{i}: {wallet_address[:8]}...{wallet_address[-6:]}")
            print(f"   持有比例: {holder.get('holdAmountPercentage', 'N/A')}%")
            
            # 获取钱包资产
            assets_data = self.get_wallet_assets(wallet_address)
            
            if assets_data:
                # 提取所有有价值的代币，不限制数量
                top_tokens = self.extract_top_tokens(assets_data)
                
                holder_info = {
                    'rank': i,
                    'address': wallet_address,
                    'hold_amount': holder.get('holdAmount', '0'),
                    'hold_percentage': holder.get('holdAmountPercentage', '0'),
                    'top_tokens': top_tokens
                }
                
                holder_analysis.append(holder_info)
                print(f"✅ 分析完成")
            else:
                print(f"❌ 获取资产失败")
            
            print()
            
            # 添加延迟避免频率限制
            time.sleep(1)
        
        # 3. 汇总分析结果和代币统计
        # 统计所有大户持有的代币
        all_tokens = {}
        
        for holder in holder_analysis:
            for token in holder['top_tokens']:
                symbol = token['symbol']
                if symbol not in all_tokens:
                    all_tokens[symbol] = {
                        'symbol': symbol,
                        'name': token['name'],
                        'chain': token['chain'],
                        'address': token['address'],
                        'price_usd': token['price_usd'],
                        'total_value': 0,
                        'holder_count': 0,
                        'holders_details': []
                    }
                
                all_tokens[symbol]['total_value'] += token['value_usd']
                all_tokens[symbol]['holder_count'] += 1
                all_tokens[symbol]['holders_details'].append({
                    'holder_address': holder['address'],
                    'holder_rank': holder['rank'],
                    'balance': token['balance'],
                    'value_usd': token['value_usd']
                })
        
        # 按总价值排序
        sorted_tokens = sorted(all_tokens.values(), key=lambda x: x['total_value'], reverse=True)
        
        analysis_result = {
            'token_address': token_address,
            'analysis_time': datetime.now().isoformat(),
            'total_holders_analyzed': len(holder_analysis),
            'holders': holder_analysis,
            'token_statistics': {
                'total_unique_tokens': len(all_tokens),
                'total_portfolio_value': sum(token['total_value'] for token in sorted_tokens),
                'top_tokens_by_value': sorted_tokens
            }
        }
        
        # 4. 生成报告
        self._generate_analysis_report(analysis_result)
        
        return analysis_result
    
    def _generate_analysis_report(self, analysis_result: Dict):
        """生成分析报告"""
        print("=" * 50)
        print("📊 分析报告")
        print("=" * 50)
        
        token_address = analysis_result['token_address']
        holders = analysis_result['holders']
        token_stats = analysis_result.get('token_statistics', {})
        
        print(f"🔍 代币地址: {token_address}")
        print(f"👥 分析大户数量: {len(holders)}")
        print()
        
        if token_stats and token_stats.get('top_tokens_by_value'):
            sorted_tokens = token_stats['top_tokens_by_value']
            
            print("🔥 大户们最热门的代币 (前30个):")
            print("-" * 50)
            print(f"{'排名':<4} {'代币':<12} {'总价值':<15} {'持有人数'}")
            print("-" * 50)
            
            for i, token in enumerate(sorted_tokens[:30], 1):
                symbol = token['symbol'][:10]  # 限制长度
                value = f"${token['total_value']:,.0f}"
                count = token['holder_count']
                print(f"{i:<4} {symbol:<12} {value:<15} {count}")
            
            total_portfolio_value = token_stats.get('total_portfolio_value', 0)
            print()
            print(f"💰 大户总资产价值: ${total_portfolio_value:,.2f}")
            print(f"🔢 发现的代币种类: {token_stats.get('total_unique_tokens', 0)}")
        else:
            print("⚠️  未能获取到有效的代币统计信息")

def main():
    """主函数"""
    # 示例代币地址
    token_address = "FbGsCHv8qPvUdmomVAiG72ET5D5kgBJgGoxxfMZipump"
    
    # 创建爬虫实例
    crawler = OKXAdvancedCrawler()
    
    # 开始分析
    result = crawler.analyze_holders(token_address, top_holders_count=20)
    
    if result:
        # 保存完整结果到文件
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 1. 保存完整的holders分析文件
        holders_filename = f"okx_holders_analysis_{timestamp}.json"
        with open(holders_filename, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"\n✅ 完整分析结果已保存到: {holders_filename}")
        
        # 2. 保存专门的代币持仓文件
        if 'token_statistics' in result and result['token_statistics']['top_tokens_by_value']:
            tokens_data = {
                'analysis_time': result['analysis_time'],
                'token_address': result['token_address'],
                'total_holders_analyzed': result['total_holders_analyzed'],
                'token_statistics': result['token_statistics']
            }
            
            tokens_filename = f"okx_tokens_portfolio_{timestamp}.json"
            with open(tokens_filename, 'w', encoding='utf-8') as f:
                json.dump(tokens_data, f, ensure_ascii=False, indent=2)
            print(f"✅ 代币持仓信息已保存到: {tokens_filename}")
            
            # 3. 生成简化的代币摘要文件
            simplified_tokens = []
            for token in result['token_statistics']['top_tokens_by_value'][:20]:  # 只保留前20个
                simplified_token = {
                    'symbol': token['symbol'],
                    'name': token['name'],
                    'chain': token['chain'],
                    'price_usd': token['price_usd'],
                    'total_value': token['total_value'],
                    'holder_count': token['holder_count']
                }
                simplified_tokens.append(simplified_token)
            
            summary_data = {
                'analysis_time': result['analysis_time'],
                'token_address': result['token_address'],
                'total_holders_analyzed': result['total_holders_analyzed'],
                'total_unique_tokens': result['token_statistics']['total_unique_tokens'],
                'total_portfolio_value': result['token_statistics']['total_portfolio_value'],
                'top_20_tokens': simplified_tokens
            }
            
            summary_filename = f"okx_tokens_summary_{timestamp}.json"
            with open(summary_filename, 'w', encoding='utf-8') as f:
                json.dump(summary_data, f, ensure_ascii=False, indent=2)
            print(f"✅ 代币摘要信息已保存到: {summary_filename}")
        else:
            print("⚠️  未能获取到有效的代币持仓信息")

if __name__ == "__main__":
    main()
