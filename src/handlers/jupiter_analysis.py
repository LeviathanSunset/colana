"""
Jupiter 代币分析命令处理器
处理 /cajup 命令，爬取Jupiter热门代币并逐个分析
"""

import time
import threading
from typing import List, Dict
from telebot import TeleBot
from telebot.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from ..core.config import get_config
from ..services.blacklist import is_blacklisted
from ..handlers.base import BaseCommandHandler

# 导入Jupiter爬虫
try:
    from ..services.jupiter_crawler import JupiterAnalyzer
except ImportError:
    print("⚠️ 无法导入Jupiter爬虫模块")
    JupiterAnalyzer = None

# 导入OKX分析功能
try:
    from ..services.okx_crawler import (
        OKXCrawlerForBot, 
        format_tokens_table,
        analyze_address_clusters,
        format_cluster_analysis, 
        analyze_target_token_rankings,
        format_target_token_rankings,
        analysis_cache,
        start_cache_cleanup
    )
except ImportError:
    print("⚠️ 无法导入OKX分析模块")
    OKXCrawlerForBot = None


class JupiterAnalysisHandler(BaseCommandHandler):
    """Jupiter代币分析处理器"""
    
    def __init__(self, bot: TeleBot):
        super().__init__(bot)
        self.config = get_config()
        self.analysis_threads = {}  # chat_id -> thread
        self.analysis_status = {}   # chat_id -> status info
        self.token_messages = {}    # chat_id -> {token_address: message_id} 保存代币分析消息ID
        
        # 启动全局缓存清理（只启动一次）
        start_cache_cleanup()
    
    def handle_cajup(self, message: Message) -> None:
        """处理 /cajup 命令"""
        # 检查依赖模块
        if not JupiterAnalyzer or not OKXCrawlerForBot:
            self.reply_with_topic(
                message, 
                "❌ Jupiter分析功能暂时不可用\n请检查依赖模块是否正确安装"
            )
            return
        
        # 检查群组权限
        chat_id = str(message.chat.id)
        allowed_groups = self.config.ca1_allowed_groups
        
        if allowed_groups and chat_id not in allowed_groups:
            self.reply_with_topic(
                message, 
                "❌ 此功能仅在特定群组中可用\n如需使用，请联系管理员"
            )
            return
        
        # 检查是否已有分析在进行
        if chat_id in self.analysis_threads and self.analysis_threads[chat_id].is_alive():
            status = self.analysis_status.get(chat_id, {})
            current = status.get('current', 0)
            total = status.get('total', 0)
            
            self.reply_with_topic(
                message,
                f"📊 <b>热门代币榜单分析进行中...</b>\n\n"
                f"🔍 当前分析: <b>{current}/{total}</b>\n"
                f"🕐 开始时间: {status.get('start_time', '未知')}\n"
                f"⏳ 正在获取前100大户数据...\n\n"
                f"请等待当前分析完成后再开始新的分析",
                parse_mode='HTML'
            )
            return
        
        # 解析参数
        parts = message.text.split()
        token_count = self.config.jupiter.default_token_count  # 使用配置的默认值
        
        if len(parts) > 1:
            try:
                token_count = int(parts[1])
                # 使用配置的最大限制
                token_count = max(1, min(token_count, self.config.jupiter.max_tokens_per_analysis))
            except ValueError:
                self.reply_with_topic(
                    message,
                    "❌ 参数错误\n\n"
                    "💡 使用方法:\n"
                    f"• <code>/cajup</code> - 分析{self.config.jupiter.default_token_count}个热门代币\n"
                    f"• <code>/cajup 20</code> - 分析指定数量的热门代币\n"
                    f"• 最多支持{self.config.jupiter.max_tokens_per_analysis}个代币",
                    parse_mode='HTML'
                )
                return
        
        # 发送开始消息
        start_msg = (
            f"🚀 开始Jupiter热门代币分析\n\n"
            f"📊 分析数量: {token_count} 个代币\n"
            f"🔍 数据源: Jupiter DEX\n"
            f"⏳ 预计耗时: {token_count * 15} 秒\n\n"
            f"正在获取热门代币列表..."
        )
        
        processing_msg = self.reply_with_topic(message, start_msg)
        
        # 保存原始消息的thread_id用于后续回复
        original_thread_id = message.message_thread_id
        
        # 启动分析线程
        self._start_analysis_thread(chat_id, processing_msg, token_count, original_thread_id)
    
    def _start_analysis_thread(self, chat_id: str, processing_msg, token_count: int, thread_id=None):
        """启动分析线程"""
        thread = threading.Thread(
            target=self._run_jupiter_analysis,
            args=(chat_id, processing_msg, token_count, thread_id),
            daemon=True
        )
        thread.start()
        self.analysis_threads[chat_id] = thread
    
    def _run_jupiter_analysis(self, chat_id: str, processing_msg, token_count: int, thread_id=None):
        """运行Jupiter分析"""
        try:
            # 初始化状态
            self.analysis_status[chat_id] = {
                'start_time': time.strftime('%H:%M:%S'),
                'current': 0,
                'total': token_count,
                'analyzed': [],
                'failed': []
            }
            
            # 获取热门代币列表
            analyzer = JupiterAnalyzer()
            token_addresses = analyzer.get_tokens_for_analysis(token_count)
            
            if not token_addresses:
                self.bot.edit_message_text(
                    "❌ 获取Jupiter热门代币失败\n\n"
                    "可能原因:\n"
                    "• 网络连接问题\n"
                    "• Jupiter API暂时不可用\n"
                    "• 参数配置错误",
                    processing_msg.chat.id,
                    processing_msg.message_id
                )
                return
            
            # 更新实际数量
            actual_count = len(token_addresses)
            self.analysis_status[chat_id]['total'] = actual_count
            
            self.bot.edit_message_text(
                f"✅ 获取到 <b>{actual_count}</b> 个热门代币\n\n"
                f"� <b>热门代币榜单分析进行中...</b>\n"
                f"� 当前分析: <b>0/{actual_count}</b>\n"
                f"⏳ 准备开始分析...",
                processing_msg.chat.id,
                processing_msg.message_id,
                parse_mode='HTML'
            )
            
            # 逐个分析代币
            for i, token_address in enumerate(token_addresses, 1):
                try:
                    # 更新状态
                    self.analysis_status[chat_id]['current'] = i
                    
                    # 检查黑名单
                    if is_blacklisted(token_address):
                        print(f"⚫ 跳过黑名单代币: {token_address}")
                        self.analysis_status[chat_id]['failed'].append({
                            'address': token_address,
                            'reason': '黑名单'
                        })
                        continue
                    
                    # 更新进度
                    self.bot.edit_message_text(
                        f"📊 <b>热门代币榜单分析进行中...</b>\n\n"
                        f"🔍 当前分析: <b>{i}/{actual_count}</b>\n"
                        f"📍 代币地址: <code>{token_address}</code>\n"
                        f"⏳ 正在获取前100大户数据...",
                        processing_msg.chat.id,
                        processing_msg.message_id,
                        parse_mode='HTML'
                    )
                    
                    # 执行OKX大户分析
                    success = self._analyze_single_token(
                        chat_id, token_address, i, actual_count, thread_id
                    )
                    
                    if success:
                        self.analysis_status[chat_id]['analyzed'].append(token_address)
                    else:
                        self.analysis_status[chat_id]['failed'].append({
                            'address': token_address,
                            'reason': '分析失败'
                        })
                    
                    # 避免API限制
                    if i < actual_count:
                        time.sleep(12)  # 每个代币间隔12秒
                
                except Exception as e:
                    print(f"❌ 分析代币失败 {token_address}: {e}")
                    self.analysis_status[chat_id]['failed'].append({
                        'address': token_address,
                        'reason': str(e)[:50]
                    })
                    continue
            
            # 发送完成总结
            self._send_analysis_summary(chat_id, processing_msg)
            
        except Exception as e:
            print(f"❌ Jupiter分析线程错误: {e}")
            self.bot.edit_message_text(
                f"❌ Jupiter分析过程中发生错误\n\n"
                f"错误信息: {str(e)}\n\n"
                f"请稍后重试",
                processing_msg.chat.id,
                processing_msg.message_id
            )
        finally:
            # 清理状态
            if chat_id in self.analysis_status:
                del self.analysis_status[chat_id]
            if chat_id in self.analysis_threads:
                del self.analysis_threads[chat_id]
    
    def _analyze_cross_holdings(self, result: dict, target_token: str) -> str:
        """
        分析交叉持仓，找出与目标代币有交叉持仓的其他代币
        
        Args:
            result: OKX分析结果
            target_token: 目标代币地址
            
        Returns:
            交叉持仓信息字符串
        """
        try:
            token_stats = result.get("token_statistics", {})
            top_tokens = token_stats.get("top_tokens_by_value", [])
            
            if not top_tokens:
                return ""
            
            # USDC地址 (Solana)
            USDC_ADDRESS = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
            
            # 统计与目标代币有交叉持仓的其他代币
            cross_holdings = {}
            
            for token_info in top_tokens:
                token_address = token_info.get("address", "")
                token_symbol = token_info.get("symbol", "Unknown")
                token_name = token_info.get("name", "")
                
                # 跳过目标代币本身和USDC
                if token_address == target_token or token_address == USDC_ADDRESS:
                    continue
                
                # 获取持有该代币的大户数量
                holder_count = len(token_info.get("top_holders", []))
                
                # 只考虑有足够大户的代币
                if holder_count >= 9:  # 大户数>=9
                    cross_holdings[token_address] = {
                        'symbol': token_symbol,
                        'name': token_name,
                        'holder_count': holder_count,
                        'holders': token_info.get("top_holders", [])[:5]  # 取前5个大户
                    }
            
            # 如果没有符合条件的交叉持仓代币，返回空
            if not cross_holdings:
                return ""
            
            # 格式化交叉持仓信息
            cross_info = "\n🔗 <b>交叉持仓分析</b>\n"
            cross_info += f"发现 {len(cross_holdings)} 个代币存在较多交叉持仓大户:\n\n"
            
            # 按大户数量排序，取前5个
            sorted_tokens = sorted(
                cross_holdings.items(), 
                key=lambda x: x[1]['holder_count'], 
                reverse=True
            )[:5]
            
            for i, (token_addr, token_info) in enumerate(sorted_tokens, 1):
                symbol = token_info['symbol']
                name = token_info['name']
                holder_count = token_info['holder_count']
                
                # 清理名称中的链标识
                clean_name = name
                if clean_name:
                    # 移除常见的链标识后缀
                    clean_name = clean_name.replace(' (Solana)', '').replace('(Solana)', '')
                    clean_name = clean_name.replace(' (SOL)', '').replace('(SOL)', '')
                    clean_name = clean_name.strip()
                
                cross_info += f"{i}. <b>{symbol}</b>"
                if clean_name and clean_name != symbol:
                    cross_info += f" ({clean_name})"
                cross_info += f"\n"
                cross_info += f"   📊 交叉大户: {holder_count} 个\n"
                cross_info += f"   📍 <code>{token_addr}</code>\n"
                
                # 显示前5个交叉持仓大户
                holders = token_info['holders']
                if holders:
                    cross_info += f"   👥 前5大户:\n"
                    for j, holder in enumerate(holders[:5], 1):
                        addr = holder.get('address', '')
                        if addr:
                            short_addr = addr[:6] + "..." + addr[-6:]
                            balance = holder.get('balance', 0)
                            percentage = holder.get('percentage', 0)
                            cross_info += f"      {j}. {short_addr} ({percentage:.1f}%)\n"
                
                cross_info += "\n"
            
            return cross_info
            
        except Exception as e:
            print(f"❌ 交叉持仓分析失败: {e}")
            return ""
    
    def _analyze_single_token(self, chat_id: str, token_address: str, 
                            current: int, total: int, thread_id=None) -> bool:
        """分析单个代币"""
        try:
            # 创建OKX爬虫
            crawler = OKXCrawlerForBot()
            
            # 执行分析
            result = crawler.analyze_token_holders(
                token_address, 
                top_holders_count=self.config.analysis.top_holders_count
            )
            
            if result and result.get("token_statistics"):
                # 创建cache_key用于生成分析按钮 - 使用短格式避免Telegram按钮数据长度限制
                # 使用代币地址前8位+后6位+时间戳后6位保证唯一性
                timestamp_suffix = str(int(time.time()))[-6:]
                cache_key = f"jup_{token_address[:8]}{token_address[-6:]}_{timestamp_suffix}"
                
                # 存储分析结果到缓存中，以便按钮回调使用
                from ..services.okx_crawler import analysis_cache
                analysis_cache[cache_key] = {
                    'result': result,
                    'timestamp': time.time(),
                    'token_address': token_address,
                    'source': 'jupiter'
                }
                
                # 获取目标代币信息
                target_token_info = None
                for token in result["token_statistics"]["top_tokens_by_value"]:
                    if token.get("address") == token_address:
                        target_token_info = token
                        break
                
                target_symbol = target_token_info.get("symbol", "Unknown") if target_token_info else "Unknown"
                
                # 格式化分析结果 - 使用统一的全局缓存系统
                table_msg, table_markup = format_tokens_table(
                    result["token_statistics"], 
                    sort_by="count",
                    cache_key=cache_key,
                    target_token_symbol=target_symbol
                )
                
                if table_msg:
                    # 添加Jupiter分析标识
                    jupiter_info = (
                        f"🔥 <b>Jupiter热门代币分析</b> ({current}/{total})\n"
                        f"📊 数据源: Jupiter DEX\n"
                        f"📍 代币地址: <code>{token_address}</code>\n"
                        f"🕐 分析时间: {time.strftime('%H:%M:%S')}\n\n"
                    )
                    
                    # 添加分析统计信息（与ca1一致）
                    analysis_info = f"\n📊 <b>{target_symbol} 分析统计</b>\n"
                    analysis_info += f"🕒 分析时间: {result.get('analysis_time', '').split('T')[0]}\n"
                    analysis_info += f"👥 分析地址: 前{result.get('total_holders_analyzed', 0)} 个\n"
                    target_holders = result.get("target_token_actual_holders", 0)
                    if target_holders > 0:
                        analysis_info += f"🎯 实际持有 {target_symbol}: {target_holders} 人\n"
                    analysis_info += f"📈 统计范围: 每个地址的前10大持仓\n"
                    
                    final_msg = jupiter_info + table_msg + analysis_info
                    
                    # 检查交叉持仓
                    cross_holding_info = self._analyze_cross_holdings(result, token_address)
                    if cross_holding_info:
                        final_msg += f"\n{cross_holding_info}"
                    
                    # 添加完整的按钮布局（与ca1一致）
                    if table_markup:
                        # 添加排序切换按钮
                        table_markup.add(
                            InlineKeyboardButton(
                                "💰 按价值排序", callback_data=f"cajup_sort_value_{cache_key}"
                            ),
                            InlineKeyboardButton(
                                "👥 按人数排序 ✅", callback_data=f"cajup_sort_count_{cache_key}"
                            ),
                        )
                        # 添加集群分析和排名分析按钮
                        table_markup.add(
                            InlineKeyboardButton(
                                "🎯 地址集群分析", callback_data=f"cajup_cluster_{cache_key}"
                            ),
                            InlineKeyboardButton(
                                "📊 代币排名分析", callback_data=f"cajup_ranking_{cache_key}"
                            )
                        )
                    
                    # 发送分析结果到topic（如果有的话）
                    sent_message = self.send_to_topic(
                        chat_id,
                        final_msg,
                        thread_id=thread_id,
                        parse_mode="HTML",
                        reply_markup=table_markup,
                        disable_web_page_preview=True
                    )
                    
                    # 保存消息ID用于后续的"值得关注代币"汇总
                    if chat_id not in self.token_messages:
                        self.token_messages[chat_id] = {}
                    self.token_messages[chat_id][token_address] = {
                        'message_id': sent_message.message_id,
                        'symbol': target_symbol,
                        'result': result
                    }
                    
                    return True
            
            return False
            
        except Exception as e:
            print(f"❌ 单个代币分析失败 {token_address}: {e}")
            return False

    def _generate_worthy_tokens_message(self, chat_id: str, thread_id=None, page=1, page_size=10):
        """生成值得关注的代币消息"""
        try:
            if chat_id not in self.token_messages:
                print(f"⚠️ chat_id {chat_id} 的token_messages数据不存在")
                return
            
            # 检查token_messages数据是否为空
            if not self.token_messages[chat_id]:
                print(f"⚠️ chat_id {chat_id} 的token_messages数据为空")
                return
            
            # 定义排除的代币地址
            excluded_tokens = {
                'So11111111111111111111111111111111111111111',  # SOL
                'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v',  # USDC
                'Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB',   # USDT
            }
            
            worthy_target_tokens = []
            
            # 遍历所有分析的目标代币
            for target_token_address, token_data in self.token_messages[chat_id].items():
                result = token_data['result']
                token_stats = result.get('token_statistics', {})
                top_tokens = token_stats.get('top_tokens_by_value', [])
                
                # 检查该目标代币的大户持有的其他代币是否有符合条件的
                has_worthy_holdings = False
                worthy_holdings_details = []
                
                for token_info in top_tokens:
                    token_addr = token_info.get('address', '')
                    
                    # 跳过目标代币本身和排除列表中的代币
                    if token_addr == target_token_address or token_addr in excluded_tokens:
                        continue
                    
                    holder_count = token_info.get('holder_count', 0)
                    total_value = token_info.get('total_value', 0)
                    
                    # 检查是否符合条件：共同持仓人数>=8且总价值>10k
                    if holder_count >= 8 and total_value > 10000:
                        has_worthy_holdings = True
                        worthy_holdings_details.append({
                            'symbol': token_info.get('symbol', 'Unknown'),
                            'name': token_info.get('name', ''),
                            'holder_count': holder_count,
                            'total_value': total_value
                        })
                
                # 如果该目标代币的大户持有符合条件的代币，则该目标代币值得关注
                if has_worthy_holdings:
                    worthy_target_tokens.append({
                        'target_symbol': token_data['symbol'],
                        'target_address': target_token_address,
                        'message_id': token_data['message_id'],
                        'worthy_holdings': worthy_holdings_details,
                        'worthy_count': len(worthy_holdings_details),
                        'max_holder_count': max(h['holder_count'] for h in worthy_holdings_details),
                        'total_worthy_value': sum(h['total_value'] for h in worthy_holdings_details)
                    })
            
            if not worthy_target_tokens:
                return
            
            # 按worthy_count和max_holder_count排序
            sorted_tokens = sorted(
                worthy_target_tokens, 
                key=lambda x: (x['worthy_count'], x['max_holder_count'], x['total_worthy_value']), 
                reverse=True
            )
            
            # 分页计算
            total_tokens = len(sorted_tokens)
            total_pages = (total_tokens + page_size - 1) // page_size
            start_idx = (page - 1) * page_size
            end_idx = min(start_idx + page_size, total_tokens)
            page_tokens = sorted_tokens[start_idx:end_idx]
            
            # 构建消息
            msg = "🎯 <b>值得关注的代币</b>"
            if total_pages > 1:
                msg += f" (第{page}/{total_pages}页)"
            msg += "\n\n"
            msg += "📋 <i>筛选条件：大户持有其他代币中有共同持仓人数≥8且总价值>$10K的</i>\n"
            msg += "🚫 <i>已排除：SOL、USDC、USDT</i>\n\n"
            
            # 生成可点击的目标代币列表
            for i, target_token in enumerate(page_tokens, start_idx + 1):
                target_symbol = target_token['target_symbol']
                message_id = target_token['message_id']
                worthy_holdings = target_token['worthy_holdings']
                worthy_count = target_token['worthy_count']
                
                # 创建可点击的链接，点击后跳转到对应的分析消息
                # 使用 t.me 链接格式
                chat_id_str = chat_id.replace('-100', '')  # 移除群组ID前缀
                click_link = f"https://t.me/c/{chat_id_str}/{message_id}"
                
                msg += f"{i}. <a href=\"{click_link}\"><b>{target_symbol}</b></a>\n"
                
                # 计算过滤后的优质代币数量（排除SOL、USDC、USDT）
                filtered_count = 0
                for holding in worthy_holdings:
                    symbol = holding.get('symbol', '').upper()
                    if symbol not in ['SOL', 'USDC', 'USDT']:
                        filtered_count += 1
                
                msg += f"   🎯 大户持有 <b>{filtered_count}</b> 个优质代币:\n"
                
                # 显示前3个最优质的持仓（排除SOL、USDC、USDT）
                filtered_holdings = []
                for holding in worthy_holdings:
                    # 检查是否为排除的代币（通过符号匹配）
                    symbol = holding.get('symbol', '').upper()
                    if symbol not in ['SOL', 'USDC', 'USDT']:
                        filtered_holdings.append(holding)
                
                # 对过滤后的代币按持仓人数和总价值排序
                sorted_filtered_holdings = sorted(filtered_holdings, key=lambda x: (x['holder_count'], x['total_value']), reverse=True)
                
                for j, holding in enumerate(sorted_filtered_holdings[:3], 1):
                    symbol = holding['symbol']
                    name = holding['name']
                    holder_count = holding['holder_count']
                    total_value = holding['total_value']
                    
                    # 清理名称中的链标识
                    clean_name = name
                    if clean_name:
                        # 移除常见的链标识后缀
                        clean_name = clean_name.replace(' (Solana)', '').replace('(Solana)', '')
                        clean_name = clean_name.replace(' (SOL)', '').replace('(SOL)', '')
                        clean_name = clean_name.strip()
                    
                    msg += f"      • <b>{symbol}</b>"
                    if clean_name and clean_name != symbol:
                        msg += f" ({clean_name})"
                    msg += f": {holder_count}人 ${total_value:,.0f}\n"
                
                if len(sorted_filtered_holdings) > 3:
                    msg += f"      • ... 还有 {len(sorted_filtered_holdings) - 3} 个优质代币\n"
                
                msg += "\n"
            
            msg += "💡 <i>点击代币名称可跳转到对应的详细分析</i>"
            
            # 创建分页按钮
            markup = None
            if total_pages > 1:
                from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
                markup = InlineKeyboardMarkup()
                
                buttons = []
                if page > 1:
                    buttons.append(InlineKeyboardButton("⬅️ 上一页", callback_data=f"worthy_tokens_{chat_id}_{page-1}"))
                if page < total_pages:
                    buttons.append(InlineKeyboardButton("➡️ 下一页", callback_data=f"worthy_tokens_{chat_id}_{page+1}"))
                
                if buttons:
                    markup.row(*buttons)
                
                # 页码信息
                markup.row(InlineKeyboardButton(f"📄 {page}/{total_pages} (共{total_tokens}个)", callback_data="dummy"))
            
            # 发送消息
            self.send_to_topic(
                chat_id,
                msg,
                thread_id=thread_id,
                parse_mode="HTML",
                disable_web_page_preview=True,
                reply_markup=markup
            )
            
        except Exception as e:
            print(f"❌ 生成值得关注代币消息失败: {e}")
    
    def _send_analysis_summary(self, chat_id: str, processing_msg):
        """发送分析总结"""
        try:
            status = self.analysis_status.get(chat_id, {})
            analyzed = status.get('analyzed', [])
            failed = status.get('failed', [])
            total = status.get('total', 0)
            start_time = status.get('start_time', '未知')
            end_time = time.strftime('%H:%M:%S')
            
            # 获取原始thread_id（从processing_msg或analysis_status中）
            thread_id = getattr(processing_msg, 'message_thread_id', None)
            
            # 先发送"值得关注的代币"消息
            if len(analyzed) > 0:  # 只有成功分析了代币才发送
                self._generate_worthy_tokens_message(chat_id, thread_id)
                time.sleep(1)  # 稍微延迟一下再发送总结
            
            summary_msg = (
                f"✅ <b>Jupiter代币分析完成</b>\n\n"
                f"📊 总体统计:\n"
                f"• 计划分析: {total} 个代币\n"
                f"• 成功分析: {len(analyzed)} 个代币\n"
                f"• 分析失败: {len(failed)} 个代币\n"
                f"• 成功率: {len(analyzed)/total*100:.1f}%\n\n"
                f"⏰ 时间统计:\n"
                f"• 开始时间: {start_time}\n"
                f"• 结束时间: {end_time}\n\n"
            )
            
            if failed:
                summary_msg += f"❌ 失败代币:\n"
                for item in failed[:5]:  # 只显示前5个失败的
                    addr = item['address'][:8] + "..." + item['address'][-8:]
                    reason = item['reason']
                    summary_msg += f"• {addr}: {reason}\n"
                
                if len(failed) > 5:
                    summary_msg += f"• ... 还有 {len(failed) - 5} 个失败\n"
            
            summary_msg += "\n💡 所有成功的分析结果已发送到群组"
            
            # 添加重新分析按钮
            markup = InlineKeyboardMarkup()
            markup.add(
                InlineKeyboardButton("🔄 重新分析", callback_data="cajup_restart"),
                InlineKeyboardButton("📊 分析更多", callback_data="cajup_more")
            )
            
            self.bot.edit_message_text(
                summary_msg,
                processing_msg.chat.id,
                processing_msg.message_id,
                parse_mode='HTML',
                reply_markup=markup
            )
            
        except Exception as e:
            print(f"❌ 发送分析总结失败: {e}")
        finally:
            # 延迟清理token_messages缓存，给用户时间使用翻页功能
            def delayed_cleanup():
                import time
                time.sleep(1800)  # 30分钟后清理
                if chat_id in self.token_messages:
                    del self.token_messages[chat_id]
                    print(f"🧹 已清理chat_id {chat_id}的token_messages缓存")
            
            # 启动延迟清理线程
            import threading
            cleanup_thread = threading.Thread(target=delayed_cleanup, daemon=True)
            cleanup_thread.start()
    
    def register_handlers(self) -> None:
        """注册处理器"""
        @self.bot.message_handler(commands=["cajup", "jupca"])
        def cajup_handler(message):
            self.handle_cajup(message)
        
        @self.bot.callback_query_handler(func=lambda call: call.data.startswith("cajup_"))
        def cajup_callback_handler(call):
            self.handle_cajup_callback(call)
        
        @self.bot.callback_query_handler(func=lambda call: call.data.startswith("worthy_tokens_"))
        def worthy_tokens_callback_handler(call):
            self.handle_worthy_tokens_callback(call)
    
    def handle_cajup_callback(self, call):
        """处理cajup回调"""
        try:
            if call.data == "cajup_restart":
                self.bot.answer_callback_query(call.id, "🔄 请重新发送 /cajup 命令开始新的分析")
            elif call.data == "cajup_more":
                self.bot.answer_callback_query(call.id, "📊 请使用 /cajup 30 分析更多代币")
            elif call.data.startswith("cajup_sort_"):
                self.handle_cajup_sort(call)
            elif call.data.startswith("cajup_cluster_page_"):
                self.handle_cajup_cluster_page(call)
            elif call.data.startswith("cajup_cluster_"):
                self.handle_cajup_cluster(call)
            elif call.data.startswith("cajup_ranking_"):
                self.handle_cajup_ranking(call)
            elif call.data.startswith("cajup_rank_"):
                self.handle_cajup_rank_detail(call)
        except Exception as e:
            print(f"❌ 处理cajup回调失败: {e}")
            self.bot.answer_callback_query(call.id, "❌ 操作失败")

    def handle_worthy_tokens_callback(self, call):
        """处理值得关注代币分页回调"""
        try:
            # 解析回调数据：worthy_tokens_{chat_id}_{page}
            parts = call.data.split("_")
            if len(parts) != 4 or parts[0] != "worthy" or parts[1] != "tokens":
                self.bot.answer_callback_query(call.id, "❌ 回调数据格式错误")
                return
            
            chat_id = parts[2]
            page = int(parts[3])
            
            # 检查token_messages数据是否还存在
            if chat_id not in self.token_messages:
                self.bot.answer_callback_query(call.id, "❌ 分析数据已过期，请重新运行 /cajup 分析")
                return
            
            # 获取消息的thread_id
            thread_id = getattr(call.message, 'message_thread_id', None)
            
            # 删除当前消息
            try:
                self.bot.delete_message(call.message.chat.id, call.message.message_id)
            except:
                pass
            
            # 重新生成指定页的消息
            self._generate_worthy_tokens_message(chat_id, thread_id, page)
            
            self.bot.answer_callback_query(call.id, f"📄 已切换到第{page}页")
            
        except Exception as e:
            print(f"❌ 处理值得关注代币分页回调失败: {e}")
            self.bot.answer_callback_query(call.id, "❌ 分页操作失败")

    def handle_cajup_sort(self, call):
        """处理cajup排序回调"""
        try:
            # 解析回调数据
            parts = call.data.split("_")
            if len(parts) < 4:
                self.bot.answer_callback_query(call.id, "❌ 回调数据格式错误")
                return
                
            sort_type = parts[2]  # value 或 count
            cache_key = "_".join(parts[3:])  # 重建cache_key
            
            # 从缓存获取分析结果
            from ..services.okx_crawler import analysis_cache
            cached_data = analysis_cache.get(cache_key)
            
            if not cached_data:
                self.bot.answer_callback_query(call.id, "❌ 分析结果已过期，请重新分析")
                return
                
            result = cached_data['result']
            token_address = cached_data['token_address']
            
            # 获取目标代币信息
            target_token_info = None
            for token in result["token_statistics"]["top_tokens_by_value"]:
                if token.get("address") == token_address:
                    target_token_info = token
                    break
            
            target_symbol = target_token_info.get("symbol", "Unknown") if target_token_info else "Unknown"
            
            # 重新格式化表格
            table_msg, table_markup = format_tokens_table(
                result["token_statistics"],
                sort_by=sort_type,
                cache_key=cache_key,
                target_token_symbol=target_symbol
            )
            
            if table_msg:
                
                target_symbol = target_token_info.get("symbol", "Unknown") if target_token_info else "Unknown"
                
                # 添加Jupiter分析标识
                jupiter_info = (
                    f"🔥 <b>Jupiter热门代币分析</b>\n"
                    f"📊 数据源: Jupiter DEX\n"
                    f"📍 代币地址: <code>{token_address}</code>\n"
                    f"🕐 分析时间: {time.strftime('%H:%M:%S')}\n\n"
                )
                
                # 添加分析统计信息
                analysis_info = f"\n📊 <b>{target_symbol} 分析统计</b>\n"
                analysis_info += f"🕒 分析时间: {result.get('analysis_time', '').split('T')[0]}\n"
                analysis_info += f"👥 分析地址: 前{result.get('total_holders_analyzed', 0)} 个\n"
                target_holders = result.get("target_token_actual_holders", 0)
                if target_holders > 0:
                    analysis_info += f"🎯 实际持有 {target_symbol}: {target_holders} 人\n"
                analysis_info += f"📈 统计范围: 每个地址的前10大持仓\n"
                
                final_msg = jupiter_info + table_msg + analysis_info
                
                # 添加按钮
                if table_markup:
                    # 添加排序切换按钮
                    value_text = "💰 按价值排序" + (" ✅" if sort_type == "value" else "")
                    count_text = "👥 按人数排序" + (" ✅" if sort_type == "count" else "")
                    
                    table_markup.add(
                        InlineKeyboardButton(value_text, callback_data=f"cajup_sort_value_{cache_key}"),
                        InlineKeyboardButton(count_text, callback_data=f"cajup_sort_count_{cache_key}"),
                    )
                    # 添加集群分析和排名分析按钮
                    table_markup.add(
                        InlineKeyboardButton("🎯 地址集群分析", callback_data=f"cajup_cluster_{cache_key}"),
                        InlineKeyboardButton("📊 代币排名分析", callback_data=f"cajup_ranking_{cache_key}")
                    )
                
                # 更新消息
                self.bot.edit_message_text(
                    final_msg,
                    call.message.chat.id,
                    call.message.message_id,
                    parse_mode="HTML",
                    reply_markup=table_markup,
                    disable_web_page_preview=True,
                )
                
                sort_name = "价值" if sort_type == "value" else "人数"
                self.bot.answer_callback_query(call.id, f"✅ 已按{sort_name}重新排序")
            else:
                self.bot.answer_callback_query(call.id, "❌ 格式化失败")
                
        except Exception as e:
            print(f"❌ 处理cajup排序回调失败: {e}")
            self.bot.answer_callback_query(call.id, "❌ 排序失败")

    def handle_cajup_cluster(self, call):
        """处理cajup集群分析回调"""
        try:
            # 解析回调数据
            parts = call.data.split("_")
            if len(parts) < 3:
                self.bot.answer_callback_query(call.id, "❌ 回调数据格式错误")
                return
                
            cache_key = "_".join(parts[2:])  # 重建cache_key
            
            # 从缓存获取分析结果
            from ..services.okx_crawler import analysis_cache, analyze_address_clusters, format_cluster_analysis
            cached_data = analysis_cache.get(cache_key)
            
            if not cached_data:
                self.bot.answer_callback_query(call.id, "❌ 分析结果已过期，请重新分析")
                return
                
            result = cached_data['result']
            token_address = cached_data['token_address']
            
            # 获取目标代币信息
            target_token_info = None
            for token in result["token_statistics"]["top_tokens_by_value"]:
                if token.get("address") == token_address:
                    target_token_info = token
                    break
            
            target_symbol = target_token_info.get("symbol", "Unknown") if target_token_info else "Unknown"

            # 显示正在分析的消息
            self.bot.edit_message_text(
                f"🎯 正在进行地址集群分析...\n代币: <b>{target_symbol}</b> (<code>{token_address}</code>)\n⏳ 分析大户间的共同投资模式...",
                call.message.chat.id,
                call.message.message_id,
                parse_mode="HTML",
            )
            
            # 执行集群分析
            clusters = analyze_address_clusters(result)
            
            # 缓存集群分析结果
            cluster_cache_key = f"{cache_key}_clusters"
            analysis_cache[cluster_cache_key] = {
                "cluster_result": clusters,
                "timestamp": time.time(),
            }
            
            # 格式化集群分析结果（支持分页）
            clusters_per_page = self.config.analysis.clusters_per_page
            cluster_msg, current_page, total_pages = format_cluster_analysis(
                clusters, 
                page=1, 
                clusters_per_page=clusters_per_page
            )
            
            if cluster_msg:
                # 创建分页按钮
                markup = InlineKeyboardMarkup(row_width=3)
                
                # 添加分页导航按钮
                nav_buttons = []
                if current_page > 1:
                    nav_buttons.append(
                        InlineKeyboardButton("⬅️ 上一页", callback_data=f"cajup_cluster_page_{cache_key}_{current_page-1}")
                    )
                
                nav_buttons.append(
                    InlineKeyboardButton(f"{current_page}/{total_pages}", callback_data="noop")
                )
                
                if current_page < total_pages:
                    nav_buttons.append(
                        InlineKeyboardButton("下一页 ➡️", callback_data=f"cajup_cluster_page_{cache_key}_{current_page+1}")
                    )
                
                if nav_buttons:
                    markup.row(*nav_buttons)
                
                # 添加功能按钮
                markup.add(
                    InlineKeyboardButton("⬅️ 返回代币排行", callback_data=f"cajup_sort_count_{cache_key}"),
                    InlineKeyboardButton("🔄 重新运行", callback_data=f"cajup_cluster_{cache_key}"),
                )
                
                # 编辑原消息显示集群分析结果
                self.bot.edit_message_text(
                    cluster_msg,
                    call.message.chat.id,
                    call.message.message_id,
                    parse_mode="HTML",
                    reply_markup=markup,
                    disable_web_page_preview=True,
                )
                self.bot.answer_callback_query(call.id, "🎯 集群分析完成")
            else:
                # 显示未发现集群的消息
                error_msg = f"❌ 未发现明显的地址集群\n代币: <b>{target_symbol}</b> (<code>{token_address}</code>)\n\n"
                error_msg += "💡 可能原因:\n• 数据不足以形成集群\n• 地址数据处理错误\n• 配置参数过于严格"
                
                markup = InlineKeyboardMarkup()
                markup.add(
                    InlineKeyboardButton("⬅️ 返回代币排行", callback_data=f"cajup_sort_count_{cache_key}")
                )
                
                self.bot.edit_message_text(
                    error_msg,
                    call.message.chat.id,
                    call.message.message_id,
                    parse_mode="HTML",
                    reply_markup=markup,
                )
                self.bot.answer_callback_query(call.id, "❌ 未发现明显的地址集群")
                
        except Exception as e:
            print(f"❌ 处理cajup集群分析回调失败: {e}")
            self.bot.answer_callback_query(call.id, "❌ 集群分析失败")

    def handle_cajup_ranking(self, call):
        """处理cajup排名分析回调"""
        try:
            # 解析回调数据
            parts = call.data.split("_")
            if len(parts) < 3:
                self.bot.answer_callback_query(call.id, "❌ 回调数据格式错误")
                return
                
            cache_key = "_".join(parts[2:])  # 重建cache_key
            
            # 从缓存获取分析结果
            from ..services.okx_crawler import analysis_cache, analyze_target_token_rankings, format_target_token_rankings
            cached_data = analysis_cache.get(cache_key)
            
            if not cached_data:
                self.bot.answer_callback_query(call.id, "❌ 分析结果已过期，请重新分析")
                return
                
            result = cached_data['result']
            token_address = cached_data['token_address']
            
            # 获取目标代币信息
            target_token_info = None
            for token in result["token_statistics"]["top_tokens_by_value"]:
                if token.get("address") == token_address:
                    target_token_info = token
                    break
            
            target_symbol = target_token_info.get("symbol", "Unknown") if target_token_info else "Unknown"

            # 显示正在分析的消息
            self.bot.edit_message_text(
                f"📊 正在进行代币排名分析...\n代币: <b>{target_symbol}</b> (<code>{token_address}</code>)\n⏳ 分析目标代币在各大户钱包中的排名...",
                call.message.chat.id,
                call.message.message_id,
                parse_mode="HTML",
            )
            
            # 执行排名分析
            original_holders = result.get("original_holders_data", [])
            rankings = analyze_target_token_rankings(result, original_holders)
            ranking_msg = format_target_token_rankings(rankings)
            
            if ranking_msg:
                # 缓存排名分析结果
                ranking_cache_key = f"{cache_key}_rankings"
                analysis_cache[ranking_cache_key] = {
                    "ranking_result": rankings,
                    "timestamp": time.time(),
                }
                
                # 创建排名按钮 (1-10名 + >10名)
                markup = InlineKeyboardMarkup(row_width=5)
                
                # 第一行：1-5名
                rank_buttons_1 = []
                for rank in range(1, 6):
                    count = sum(1 for r in rankings["rankings"] if r["target_token_rank"] == rank)
                    if count > 0:
                        rank_buttons_1.append(
                            InlineKeyboardButton(f"{rank}名({count})", callback_data=f"cajup_rank_{cache_key}_{rank}")
                        )
                if rank_buttons_1:
                    markup.row(*rank_buttons_1)
                
                # 第二行：6-10名
                rank_buttons_2 = []
                for rank in range(6, 11):
                    count = sum(1 for r in rankings["rankings"] if r["target_token_rank"] == rank)
                    if count > 0:
                        rank_buttons_2.append(
                            InlineKeyboardButton(f"{rank}名({count})", callback_data=f"cajup_rank_{cache_key}_{rank}")
                        )
                if rank_buttons_2:
                    markup.row(*rank_buttons_2)
                
                # 第三行：>10名 + 阴谋钱包
                third_row_buttons = []
                over_10_count = sum(1 for r in rankings["rankings"] if r["target_token_rank"] > 10)
                if over_10_count > 0:
                    third_row_buttons.append(
                        InlineKeyboardButton(f">10名({over_10_count})", callback_data=f"cajup_rank_{cache_key}_over10")
                    )
                
                # 添加阴谋钱包按钮
                conspiracy_count = sum(1 for r in rankings["rankings"] if r.get("is_conspiracy_wallet", False))
                if conspiracy_count > 0:
                    third_row_buttons.append(
                        InlineKeyboardButton(f"🔴阴谋({conspiracy_count})", callback_data=f"cajup_rank_{cache_key}_conspiracy")
                    )
                
                if third_row_buttons:
                    markup.row(*third_row_buttons)
                
                # 功能按钮
                markup.add(
                    InlineKeyboardButton("⬅️ 返回代币排行", callback_data=f"cajup_sort_count_{cache_key}"),
                    InlineKeyboardButton("🎯 地址集群分析", callback_data=f"cajup_cluster_{cache_key}")
                )
                markup.add(
                    InlineKeyboardButton("🔄 重新运行", callback_data=f"cajup_ranking_{cache_key}")
                )
                
                # 编辑原消息显示排名分析结果
                self.bot.edit_message_text(
                    ranking_msg,
                    call.message.chat.id,
                    call.message.message_id,
                    parse_mode="HTML",
                    reply_markup=markup,
                    disable_web_page_preview=True,
                )
                self.bot.answer_callback_query(call.id, "📊 排名分析完成")
            else:
                # 显示分析失败的消息
                error_msg = f"❌ 排名分析数据不足\n代币: <b>{target_symbol}</b> (<code>{token_address}</code>)\n\n"
                error_msg += "💡 可能原因:\n• 没有大户持有目标代币\n• 数据不足以进行排名分析"
                
                markup = InlineKeyboardMarkup()
                markup.add(
                    InlineKeyboardButton("⬅️ 返回代币排行", callback_data=f"cajup_sort_count_{cache_key}")
                )
                
                self.bot.edit_message_text(
                    error_msg,
                    call.message.chat.id,
                    call.message.message_id,
                    parse_mode="HTML",
                    reply_markup=markup,
                )
                self.bot.answer_callback_query(call.id, "❌ 排名分析数据不足")
                
        except Exception as e:
            print(f"❌ 处理cajup排名分析回调失败: {e}")
            self.bot.answer_callback_query(call.id, "❌ 排名分析失败")

    def handle_cajup_rank_detail(self, call):
        """处理cajup排名详情查看回调"""
        try:
            # 解析回调数据: cajup_rank_{cache_key}_{rank} 或 cajup_rank_{cache_key}_over10
            data_parts = call.data[len("cajup_rank_"):].split("_")
            if len(data_parts) < 2:
                self.bot.answer_callback_query(call.id, "❌ 回调数据格式错误")
                return
                
            cache_key = "_".join(data_parts[:-1])  # 重组cache_key，可能包含下划线
            rank_part = data_parts[-1]
            
            print(f"CAJUP排名详情回调: cache_key={cache_key}, rank_part={rank_part}")
            
            # 从缓存中获取排名分析结果
            from ..services.okx_crawler import analysis_cache
            ranking_cache_key = f"{cache_key}_rankings"
            if ranking_cache_key not in analysis_cache:
                self.bot.answer_callback_query(call.id, "❌ 排名数据缓存已失效，请重新运行排名分析")
                return
                
            ranking_data = analysis_cache[ranking_cache_key]
            ranking_result = ranking_data["ranking_result"]
            
            # 解析rank_part
            if rank_part == "over10":
                target_rank = ">10"
                filtered_rankings = [r for r in ranking_result["rankings"] if r["target_token_rank"] > 10]
            elif rank_part == "conspiracy":
                target_rank = "阴谋"
                filtered_rankings = [r for r in ranking_result["rankings"] if r.get("is_conspiracy_wallet", False)]
            else:
                try:
                    target_rank = int(rank_part)
                    filtered_rankings = [r for r in ranking_result["rankings"] if r["target_token_rank"] == target_rank]
                except ValueError:
                    self.bot.answer_callback_query(call.id, "❌ 无效的排名参数")
                    return
            
            if not filtered_rankings:
                self.bot.answer_callback_query(call.id, f"❌ 没有找到排名 {target_rank} 的数据")
                return
            
            # 格式化排名详情消息
            target_token = ranking_result.get("target_token", {})
            symbol = target_token.get("symbol", "Unknown")
            
            if rank_part == "over10":
                rank_title = ">10名"
            elif rank_part == "conspiracy":
                rank_title = "阴谋钱包"
            else:
                rank_title = f"第{target_rank}名"
            
            msg = f"📊 <b>{symbol} - {rank_title}地址详情</b>\n"
            msg += f"👥 共 <b>{len(filtered_rankings)}</b> 个地址\n"
            
            # 为阴谋钱包添加特殊说明
            if rank_part == "conspiracy":
                msg += f"🔴 <i>阴谋钱包：{symbol}代币价值占总资产>50%的地址</i>\n"
            
            msg += "─" * 35 + "\n\n"
            
            # 按价值排序显示
            sorted_rankings = sorted(filtered_rankings, key=lambda x: x["target_token_value"], reverse=True)
            
            total_value = sum(r["target_token_value"] for r in sorted_rankings)
            if total_value >= 1_000_000:
                total_value_str = f"${total_value/1_000_000:.2f}M"
            elif total_value >= 1_000:
                total_value_str = f"${total_value/1_000:.2f}K"
            else:
                total_value_str = f"${total_value:.0f}"
            
            msg += f"💰 <b>总价值: {total_value_str}</b>\n\n"
            
            for i, ranking in enumerate(sorted_rankings, 1):
                holder_rank = ranking["holder_rank"]
                target_rank = ranking["target_token_rank"]
                target_value = ranking["target_token_value"]
                target_supply_percentage = ranking.get("target_supply_percentage", 0)
                total_tokens = ranking["total_tokens"]
                portfolio_value = ranking["portfolio_value"]
                holder_address = ranking["holder_address"]
                
                # 格式化价值显示
                if target_value >= 1_000_000:
                    value_str = f"${target_value/1_000_000:.2f}M"
                elif target_value >= 1_000:
                    value_str = f"${target_value/1_000:.2f}K"
                else:
                    value_str = f"${target_value:.0f}"
                    
                if portfolio_value >= 1_000_000:
                    portfolio_str = f"${portfolio_value/1_000_000:.2f}M"
                elif portfolio_value >= 1_000:
                    portfolio_str = f"${portfolio_value/1_000:.2f}K"
                else:
                    portfolio_str = f"${portfolio_value:.0f}"
                
                # 地址显示和链接
                addr_display = f"{holder_address[:6]}...{holder_address[-4:]}"
                gmgn_link = f"https://gmgn.ai/sol/address/{holder_address}"
                addr_with_link = f"<a href='{gmgn_link}'>{addr_display}</a>"
                
                # 排名emoji
                if target_rank == 1:
                    rank_emoji = "🥇"
                elif target_rank == 2:
                    rank_emoji = "🥈"
                elif target_rank == 3:
                    rank_emoji = "🥉"
                elif target_rank <= 5:
                    rank_emoji = "🏅"
                elif target_rank <= 10:
                    rank_emoji = "⭐"
                else:
                    rank_emoji = "📉"
                
                msg += f"<b>{i:2d}.</b> 大户#{holder_rank} {addr_with_link}\n"
                if rank_part == "over10":
                    percentage_str = f"({target_supply_percentage:.3f}%)" if target_supply_percentage > 0 else ""
                    msg += f"    {rank_emoji} 排名: <b>第{target_rank}名</b>/{total_tokens} | 价值: {value_str} {percentage_str}\n"
                elif rank_part == "conspiracy":
                    target_percentage = ranking.get("target_percentage", 0)
                    percentage_str = f"({target_supply_percentage:.3f}%)" if target_supply_percentage > 0 else ""
                    msg += f"    🔴 排名: <b>第{target_rank}名</b>/{total_tokens} | 占比: <b>{target_percentage:.1f}%</b> | 价值: {value_str} {percentage_str}\n"
                else:
                    percentage_str = f"({target_supply_percentage:.3f}%)" if target_supply_percentage > 0 else ""
                    msg += f"    {rank_emoji} 排名: <b>{rank_title}</b>/{total_tokens} | 价值: {value_str} {percentage_str}\n"
                msg += f"    💼 总资产: {portfolio_str}\n\n"
                
                # 限制显示条数，避免消息过长
                if i >= 15:
                    remaining = len(sorted_rankings) - 15
                    if remaining > 0:
                        msg += f"... 还有 {remaining} 个地址未显示\n"
                    break
            
            # 创建返回按钮
            markup = InlineKeyboardMarkup()
            markup.add(
                InlineKeyboardButton("⬅️ 返回排名分析", callback_data=f"cajup_ranking_{cache_key}")
            )
            
            # 编辑消息显示详情
            self.bot.edit_message_text(
                msg,
                call.message.chat.id,
                call.message.message_id,
                parse_mode="HTML",
                reply_markup=markup,
                disable_web_page_preview=True,
            )
            
            self.bot.answer_callback_query(call.id, f"✅ 显示排名 {target_rank} 详情")
            
        except Exception as e:
            print(f"❌ 处理cajup排名详情回调失败: {e}")
            self.bot.answer_callback_query(call.id, "❌ 显示详情失败")

    def handle_cajup_cluster_page(self, call):
        """处理cajup集群分页回调"""
        try:
            # 解析回调数据: cajup_cluster_page_{cache_key}_{page}
            parts = call.data[len("cajup_cluster_page_"):].split("_")
            if len(parts) < 2:
                self.bot.answer_callback_query(call.id, "❌ 分页回调数据格式错误")
                return
                
            cache_key = "_".join(parts[:-1])
            page = int(parts[-1])
            
            print(f"CAJUP集群分页回调: cache_key={cache_key}, page={page}")
            
            # 从缓存获取集群分析结果
            from ..services.okx_crawler import analysis_cache, format_cluster_analysis
            cluster_cache_key = f"{cache_key}_clusters"
            
            if cluster_cache_key not in analysis_cache:
                self.bot.answer_callback_query(call.id, "❌ 集群数据缓存已失效，请重新运行集群分析")
                return
                
            cluster_data = analysis_cache[cluster_cache_key]
            clusters = cluster_data["cluster_result"]
            
            # 格式化集群分析结果（支持分页）
            clusters_per_page = self.config.analysis.clusters_per_page
            cluster_msg, current_page, total_pages = format_cluster_analysis(
                clusters, 
                page=page, 
                clusters_per_page=clusters_per_page
            )
            
            # 创建分页按钮
            markup = InlineKeyboardMarkup(row_width=3)
            
            # 添加分页导航按钮
            nav_buttons = []
            if current_page > 1:
                nav_buttons.append(
                    InlineKeyboardButton("⬅️ 上一页", callback_data=f"cajup_cluster_page_{cache_key}_{current_page-1}")
                )
            
            nav_buttons.append(
                InlineKeyboardButton(f"{current_page}/{total_pages}", callback_data="noop")
            )
            
            if current_page < total_pages:
                nav_buttons.append(
                    InlineKeyboardButton("下一页 ➡️", callback_data=f"cajup_cluster_page_{cache_key}_{current_page+1}")
                )
            
            if nav_buttons:
                markup.row(*nav_buttons)
            
            # 添加功能按钮
            markup.add(
                InlineKeyboardButton("⬅️ 返回代币排行", callback_data=f"cajup_sort_count_{cache_key}"),
                InlineKeyboardButton("🔄 重新运行", callback_data=f"cajup_cluster_{cache_key}"),
            )
            
            # 更新消息
            self.bot.edit_message_text(
                cluster_msg,
                call.message.chat.id,
                call.message.message_id,
                parse_mode="HTML",
                reply_markup=markup,
                disable_web_page_preview=True,
            )
            
            self.bot.answer_callback_query(call.id, f"已切换到第{current_page}页")
            
        except Exception as e:
            print(f"❌ 处理cajup集群分页回调失败: {e}")
            self.bot.answer_callback_query(call.id, "❌ 切换页面失败")
