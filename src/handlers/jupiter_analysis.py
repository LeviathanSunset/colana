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
        format_target_token_rankings
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
                f"⏳ Jupiter分析正在进行中...\n\n"
                f"📊 进度: {current}/{total}\n"
                f"🕐 开始时间: {status.get('start_time', '未知')}\n\n"
                f"请等待当前分析完成后再开始新的分析"
            )
            return
        
        # 解析参数
        parts = message.text.split()
        token_count = 10  # 默认分析10个代币
        
        if len(parts) > 1:
            try:
                token_count = int(parts[1])
                token_count = max(1, min(token_count, 50))  # 限制在1-50之间
            except ValueError:
                self.reply_with_topic(
                    message,
                    "❌ 参数错误\n\n"
                    "💡 使用方法:\n"
                    "• <code>/cajup</code> - 分析10个热门代币\n"
                    "• <code>/cajup 20</code> - 分析20个热门代币\n"
                    "• 最多支持50个代币",
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
                f"✅ 获取到 {actual_count} 个热门代币\n\n"
                f"🔍 开始逐个分析大户持仓...\n"
                f"📊 进度: 0/{actual_count}",
                processing_msg.chat.id,
                processing_msg.message_id
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
                        f"📊 Jupiter代币分析进行中...\n\n"
                        f"🔍 当前分析: {i}/{actual_count}\n"
                        f"📍 代币地址: <code>{token_address}</code>\n"
                        f"⏳ 正在获取大户数据...",
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
                
                cross_info += f"{i}. <b>{symbol}</b>"
                if name and name != symbol:
                    cross_info += f" ({name})"
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
                
                # 格式化分析结果 - 使用与ca1相同的完整格式
                table_msg, table_markup = format_tokens_table(
                    result["token_statistics"], 
                    sort_by="count",
                    cache_key=cache_key
                )
                
                if table_msg:
                    # 获取目标代币信息
                    target_token_info = None
                    for token in result["token_statistics"]["top_tokens_by_value"]:
                        if token.get("address") == token_address:
                            target_token_info = token
                            break
                    
                    target_symbol = target_token_info.get("symbol", "Unknown") if target_token_info else "Unknown"
                    
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
                    self.send_to_topic(
                        chat_id,
                        final_msg,
                        thread_id=thread_id,
                        parse_mode="HTML",
                        reply_markup=table_markup,
                        disable_web_page_preview=True
                    )
                    
                    return True
            
            return False
            
        except Exception as e:
            print(f"❌ 单个代币分析失败 {token_address}: {e}")
            return False
    
    def _send_analysis_summary(self, chat_id: str, processing_msg):
        """发送分析总结"""
        try:
            status = self.analysis_status.get(chat_id, {})
            analyzed = status.get('analyzed', [])
            failed = status.get('failed', [])
            total = status.get('total', 0)
            start_time = status.get('start_time', '未知')
            end_time = time.strftime('%H:%M:%S')
            
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
    
    def register_handlers(self) -> None:
        """注册处理器"""
        @self.bot.message_handler(commands=["cajup", "jupca"])
        def cajup_handler(message):
            self.handle_cajup(message)
        
        @self.bot.callback_query_handler(func=lambda call: call.data.startswith("cajup_"))
        def cajup_callback_handler(call):
            self.handle_cajup_callback(call)
    
    def handle_cajup_callback(self, call):
        """处理cajup回调"""
        try:
            if call.data == "cajup_restart":
                self.bot.answer_callback_query(call.id, "🔄 请重新发送 /cajup 命令开始新的分析")
            elif call.data == "cajup_more":
                self.bot.answer_callback_query(call.id, "📊 请使用 /cajup 30 分析更多代币")
            elif call.data.startswith("cajup_sort_"):
                self.handle_cajup_sort(call)
            elif call.data.startswith("cajup_cluster_"):
                self.handle_cajup_cluster(call)
            elif call.data.startswith("cajup_ranking_"):
                self.handle_cajup_ranking(call)
        except Exception as e:
            print(f"❌ 处理cajup回调失败: {e}")
            self.bot.answer_callback_query(call.id, "❌ 操作失败")

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
            
            # 重新格式化表格
            table_msg, table_markup = format_tokens_table(
                result["token_statistics"],
                sort_by=sort_type,
                cache_key=cache_key
            )
            
            if table_msg:
                # 获取目标代币信息
                target_token_info = None
                for token in result["token_statistics"]["top_tokens_by_value"]:
                    if token.get("address") == token_address:
                        target_token_info = token
                        break
                
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
            cluster_msg = format_cluster_analysis(clusters, page=0)
            
            if cluster_msg:
                # 创建返回按钮
                markup = InlineKeyboardMarkup()
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
                # 创建返回按钮
                markup = InlineKeyboardMarkup()
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
