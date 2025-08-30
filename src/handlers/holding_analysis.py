"""
持仓分析命令处理器
处理 /ca 命令和相关回调
"""

import time
import threading
from telebot import TeleBot
from telebot.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from ..core.config import get_config
from ..services.formatter import MessageFormatter
from ..handlers.base import BaseCommandHandler

# 导入OKX相关功能
try:
    from ..services.okx_crawler import (
        OKXCrawlerForBot,
        format_tokens_table,
        format_token_holders_detail,
        analyze_address_clusters,
        format_cluster_analysis,
        analyze_target_token_rankings,
        format_target_token_rankings,
        analysis_cache,
        start_cache_cleanup,
        cleanup_expired_cache
    )
except ImportError:
    print("⚠️ 无法导入OKX爬虫模块，/ca功能可能不可用")
    OKXCrawlerForBot = None


class HoldingAnalysisHandler(BaseCommandHandler):
    """持仓分析处理器"""

    def __init__(self, bot: TeleBot):
        super().__init__(bot)
        self.config = get_config()
        self.formatter = MessageFormatter()
        
        # 添加logger
        try:
            from ..utils.logger import get_logger
            self.logger = get_logger("holding_analysis")
        except ImportError:
            # 如果logger模块不可用，使用print作为后备
            class SimpleLogger:
                def info(self, msg): print(f"INFO: {msg}")
                def error(self, msg): print(f"ERROR: {msg}")
                def warning(self, msg): print(f"WARNING: {msg}")
                def debug(self, msg): print(f"DEBUG: {msg}")
                def log_performance(self, *args, **kwargs): pass
                def error_with_solution(self, e, msg): 
                    print(f"ERROR: {msg}: {e}")
                    return {"error": str(e)}
            self.logger = SimpleLogger()

        # 启动全局缓存清理（只启动一次）
        start_cache_cleanup()

    def handle_ca(self, message: Message) -> None:
        """处理 /ca 命令 - OKX大户分析"""
        try:
            if not OKXCrawlerForBot:
                error_msg = (
                    "❌ OKX分析功能暂时不可用\n\n"
                    "🔧 可能的解决方案:\n"
                    "• 检查网络连接和代理设置\n"
                    "• 确认OKX API服务正常\n"
                    "• 重启Bot服务\n"
                    "• 联系管理员检查依赖模块"
                )
                self.reply_with_topic(message, error_msg)
                self.logger.error("OKX分析模块未加载，功能不可用")
                return

            # 检查群组权限
            chat_id = message.chat.id  # 保持为整数类型
            allowed_groups = self.config.ca_allowed_groups
            
            if allowed_groups and chat_id not in allowed_groups:
                self.reply_with_topic(
                    message, 
                    "❌ 此功能仅在特定群组中可用\n如需使用，请联系管理员"
                )
                self.logger.warning(f"未授权群组 {chat_id} 尝试使用ca功能")
                return

            # 提取代币地址参数
            parts = message.text.split(maxsplit=1)
            if len(parts) < 2:
                help_msg = (
                    "❌ 请提供代币地址\n\n"
                    "📋 使用方法:\n"
                    "<code>/ca &lt;代币合约地址&gt;</code>\n\n"
                    "📝 示例:\n"
                    "<code>/ca FbGsCHv8qPvUdmomVAiG72ET5D5kgBJgGoxxfMZipump</code>\n\n"
                    "💡 提示: 代币地址可从GMGN等平台复制"
                )
                self.reply_with_topic(message, help_msg, parse_mode="HTML")
                return

            token_address = parts[1].strip()

            # 验证代币地址
            if not token_address:
                error_msg = (
                    "❌ 代币地址不能为空\n\n"
                    "📋 正确格式:\n"
                    "<code>/ca FbGsCHv8qPvUdmomVAiG72ET5D5kgBJgGoxxfMZipump</code>"
                )
                self.reply_with_topic(message, error_msg, parse_mode="HTML")
                return

            if len(token_address) < 20:  # 简单验证地址长度
                error_msg = (
                    "❌ 代币地址格式不正确\n\n"
                    "🔍 要求:\n"
                    "• 地址长度至少20个字符\n"
                    "• 使用有效的Solana代币合约地址\n\n"
                    "💡 提示: 可从DEX平台或区块链浏览器获取正确地址"
                )
                self.reply_with_topic(message, error_msg, parse_mode="HTML")
                return

            self.logger.info(f"开始分析代币: {token_address}, 用户: {message.from_user.username}")

            # 发送开始分析的消息
            processing_msg = self.reply_with_topic(
                message,
                f"🔍 正在分析代币大户持仓...\n"
                f"代币地址: `{token_address}`\n"
                f"⏳ 预计需要1-2分钟，请稍候...\n"
                f"📊 将分析前100名大户的持仓情况",
                parse_mode="Markdown",
            )

            # 在后台线程中运行分析
            analysis_thread = threading.Thread(
                target=self._run_analysis, 
                args=(processing_msg, token_address), 
                daemon=True
            )
            analysis_thread.start()
            
        except Exception as e:
            self.logger.error_with_solution(e, f"ca命令处理失败 - 用户: {message.from_user.username}")
            error_msg = (
                "❌ 命令处理失败\n\n"
                "🔧 请尝试:\n"
                "• 检查代币地址格式\n"
                "• 稍后重试\n"
                "• 使用 /help 查看使用说明"
            )
            self.reply_with_topic(message, error_msg)

    def _run_analysis(self, processing_msg, token_address: str):
        """在后台运行分析"""
        start_time = time.time()
        try:
            self.logger.info(f"后台分析开始: {token_address}")
            
            # 清理过期缓存
            cleanup_expired_cache()

            # 创建OKX爬虫实例
            crawler = OKXCrawlerForBot()

            # 执行分析
            result = crawler.analyze_token_holders(
                token_address, top_holders_count=self.config.analysis.top_holders_count
            )

            if result and result.get("token_statistics"):
                # 缓存分析结果
                cache_key = f"{processing_msg.chat.id}_{processing_msg.message_id}"
                analysis_cache[cache_key] = {
                    "result": result,
                    "token_address": token_address,
                    "timestamp": time.time(),
                }

                print(f"缓存分析结果: cache_key={cache_key}")

                # 获取目标代币信息
                target_token_info = None
                for token in result["token_statistics"]["top_tokens_by_value"]:
                    if token.get("address") == token_address:
                        target_token_info = token
                        break
                
                target_symbol = target_token_info.get("symbol", "Unknown") if target_token_info else "Unknown"

                # 格式化表格消息（默认按人数排序）
                table_msg, table_markup = format_tokens_table(
                    result["token_statistics"],
                    max_tokens=self.config.analysis.ranking_size,
                    sort_by="count",
                    cache_key=cache_key,
                    target_token_symbol=target_symbol,
                )
                
                # 添加分析信息
                analysis_info = f"\n📊 <b>{target_symbol} 分析统计</b>\n"
                analysis_info += f"🕒 分析时间: {result.get('analysis_time', '').split('T')[0]}\n"
                analysis_info += f"👥 分析地址: 前{result.get('total_holders_analyzed', 0)} 个\n"
                target_holders = result.get("target_token_actual_holders", 0)
                if target_holders > 0:
                    analysis_info += f"🎯 实际持有 {target_symbol}: {target_holders} 人\n"
                analysis_info += f"📈 统计范围: 每个地址的前10大持仓\n"

                final_msg = table_msg + analysis_info

                # 创建完整的按钮布局
                if table_markup:
                    # 添加排序切换按钮
                    table_markup.add(
                        InlineKeyboardButton(
                            "💰 按价值排序", callback_data=f"ca_sort_value_{cache_key}"
                        ),
                        InlineKeyboardButton(
                            "👥 按人数排序 ✅", callback_data=f"ca_sort_count_{cache_key}"
                        ),
                    )
                    # 添加集群分析和排名分析按钮
                    table_markup.add(
                        InlineKeyboardButton(
                            "🎯 共同持仓分析", callback_data=f"ca_cluster_{cache_key}"
                        ),
                        InlineKeyboardButton(
                            "📊 目标代币排名", callback_data=f"ca_ranking_{cache_key}"
                        )
                    )
                    markup = table_markup
                else:
                    # 如果没有代币详情按钮，只添加排序、集群和排名按钮
                    markup = InlineKeyboardMarkup(row_width=2)
                    markup.add(
                        InlineKeyboardButton(
                            "💰 按价值排序", callback_data=f"ca_sort_value_{cache_key}"
                        ),
                        InlineKeyboardButton(
                            "👥 按人数排序 ✅", callback_data=f"ca_sort_count_{cache_key}"
                        ),
                    )
                    markup.add(
                        InlineKeyboardButton(
                            "🎯 共同持仓分析", callback_data=f"ca_cluster_{cache_key}"
                        ),
                        InlineKeyboardButton(
                            "📊 目标代币排名", callback_data=f"ca_ranking_{cache_key}"
                        )
                    )

                # 更新消息
                self.bot.edit_message_text(
                    final_msg,
                    processing_msg.chat.id,
                    processing_msg.message_id,
                    parse_mode="HTML",
                    reply_markup=markup,
                    disable_web_page_preview=True,
                )
                
                # 记录成功的性能数据
                analysis_duration = time.time() - start_time
                self.logger.log_performance(
                    f"代币分析-{token_address}", 
                    analysis_duration,
                    {
                        "token_count": len(result.get("token_statistics", {}).get("top_tokens_by_value", [])),
                        "holders_analyzed": result.get('total_holders_analyzed', 0),
                        "target_holders": result.get("target_token_actual_holders", 0)
                    }
                )
                self.logger.info(f"分析完成: {token_address}, 耗时: {analysis_duration:.2f}s")
                
            else:
                analysis_duration = time.time() - start_time
                error_msg = (
                    f"❌ 分析失败\n"
                    f"代币地址: `{token_address}`\n\n"
                    f"🔧 可能原因和解决方案:\n"
                    f"• 🔍 代币地址无效 → 请检查地址格式\n"
                    f"• 🌐 网络连接问题 → 检查网络和代理设置\n"
                    f"• ⚡ API服务限制 → 稍后重试\n"
                    f"• 📊 数据源异常 → 联系管理员\n\n"
                    f"💡 建议:\n"
                    f"• 确认代币在Solana链上\n"
                    f"• 检查代币是否为新创建的代币\n"
                    f"• 尝试使用其他代币地址测试\n\n"
                    f"🕒 分析耗时: {analysis_duration:.1f}秒"
                )
                
                self.bot.edit_message_text(
                    error_msg,
                    processing_msg.chat.id,
                    processing_msg.message_id,
                    parse_mode="Markdown",
                )
                
                self.logger.warning(f"分析失败但无异常: {token_address}, 耗时: {analysis_duration:.2f}s")

        except Exception as e:
            analysis_duration = time.time() - start_time
            
            # 使用增强的错误处理
            error_info = self.logger.error_with_solution(e, f"代币分析失败 - {token_address}")
            
            # 根据错误类型提供不同的用户消息
            if "timeout" in str(e).lower():
                user_error_msg = (
                    f"❌ 分析超时\n"
                    f"代币地址: `{token_address}`\n\n"
                    f"🔧 解决方案:\n"
                    f"• ⏰ 稍后重试（建议等待2-3分钟）\n"
                    f"• 🌐 检查网络连接稳定性\n"
                    f"• 📊 该代币可能持有者过多，处理时间较长\n\n"
                    f"🕒 已分析: {analysis_duration:.1f}秒"
                )
            elif "connection" in str(e).lower():
                user_error_msg = (
                    f"❌ 网络连接失败\n"
                    f"代币地址: `{token_address}`\n\n"
                    f"🔧 解决方案:\n"
                    f"• 🌐 检查网络连接\n"
                    f"• 🔄 检查代理设置\n"
                    f"• ⏰ 稍后重试\n\n"
                    f"💡 提示: 网络不稳定时可能影响分析效果"
                )
            elif "rate limit" in str(e).lower():
                user_error_msg = (
                    f"❌ API调用频率限制\n"
                    f"代币地址: `{token_address}`\n\n"
                    f"🔧 解决方案:\n"
                    f"• ⏰ 等待5-10分钟后重试\n"
                    f"• 📈 避免短时间内多次分析\n"
                    f"• 🎯 优先分析重要代币\n\n"
                    f"💡 提示: API限流是为了保护服务稳定性"
                )
            else:
                user_error_msg = (
                    f"❌ 分析过程中发生错误\n"
                    f"代币地址: `{token_address}`\n"
                    f"错误类型: {error_info['category']}\n\n"
                    f"🔧 建议解决方案:\n"
                )
                for i, solution in enumerate(error_info['solutions'][:3], 1):
                    user_error_msg += f"• {solution}\n"
                user_error_msg += f"\n🕒 分析耗时: {analysis_duration:.1f}秒"
                
            self.bot.edit_message_text(
                user_error_msg,
                processing_msg.chat.id,
                processing_msg.message_id,
                parse_mode="Markdown",
            )

    def handle_ca_sort(self, call: CallbackQuery) -> None:
        """处理排序切换回调"""
        try:
            # 解析回调数据: ca_sort_{sort_by}_{cache_key}
            callback_data = call.data[len("ca_sort_") :]
            parts = callback_data.split("_", 1)

            if len(parts) >= 2:
                sort_by = parts[0]  # 'value' 或 'count'
                cache_key = parts[1]  # cache_key
                print(f"排序回调: sort_by={sort_by}, cache_key={cache_key}")
                self._handle_sort_callback(call, sort_by, cache_key)
            else:
                print(f"排序回调数据格式错误: {call.data}")
                self.bot.answer_callback_query(call.id, "❌ 回调数据格式错误")
        except Exception as e:
            print(f"排序回调处理错误: {str(e)}")
            self.bot.answer_callback_query(call.id, f"❌ 处理回调失败: {str(e)}")

    def _handle_sort_callback(self, call: CallbackQuery, sort_by: str, cache_key: str):
        """处理排序切换逻辑"""
        try:
            # 从缓存中获取分析结果
            if cache_key not in analysis_cache:
                self._show_reanalyze_option(call, cache_key)
                return

            cached_data = analysis_cache[cache_key]
            result = cached_data["result"]

            # 检查缓存是否过期（24小时）
            if time.time() - cached_data["timestamp"] > 24 * 3600:
                self._show_expired_data_option(call, cached_data["token_address"])
                return

            # 获取目标代币信息
            target_token_address = result.get("token_address", "")
            target_token_info = None
            for token in result["token_statistics"]["top_tokens_by_value"]:
                if token.get("address") == target_token_address:
                    target_token_info = token
                    break
            
            target_symbol = target_token_info.get("symbol", "Unknown") if target_token_info else "Unknown"

            # 重新格式化表格
            table_msg, table_markup = format_tokens_table(
                result["token_statistics"],
                max_tokens=self.config.analysis.ranking_size,
                sort_by=sort_by,
                cache_key=cache_key,
                target_token_symbol=target_symbol,
            )

            if not table_msg:
                self.bot.answer_callback_query(call.id, "❌ 无法生成代币表格")
                return

            # 添加分析信息
            analysis_info = f"\n📊 <b>分析统计</b>\n"
            analysis_info += f"🕒 分析时间: {result.get('analysis_time', '').split('T')[0]}\n"
            analysis_info += f"👥 分析地址: 前{result.get('total_holders_analyzed', 0)} 个\n"
            analysis_info += f"🎯 每个地址命中持仓前10的代币\n"

            final_msg = table_msg + analysis_info

            # 创建完整的按钮布局
            if table_markup:
                # 添加排序切换按钮
                if sort_by == "value":
                    table_markup.add(
                        InlineKeyboardButton(
                            "💰 按价值排序 ✅", callback_data=f"ca_sort_value_{cache_key}"
                        ),
                        InlineKeyboardButton(
                            "👥 按人数排序", callback_data=f"ca_sort_count_{cache_key}"
                        ),
                    )
                else:
                    table_markup.add(
                        InlineKeyboardButton(
                            "💰 按价值排序", callback_data=f"ca_sort_value_{cache_key}"
                        ),
                        InlineKeyboardButton(
                            "👥 按人数排序 ✅", callback_data=f"ca_sort_count_{cache_key}"
                        ),
                    )
                # 添加集群分析和排名分析按钮
                table_markup.add(
                    InlineKeyboardButton(
                        "🎯 共同持仓分析", callback_data=f"ca_cluster_{cache_key}"
                    ),
                    InlineKeyboardButton(
                        "📊 目标代币排名", callback_data=f"ca_ranking_{cache_key}"
                    )
                )
                markup = table_markup
            else:
                # 如果没有代币详情按钮，只添加排序和集群按钮
                markup = InlineKeyboardMarkup(row_width=2)
                if sort_by == "value":
                    markup.add(
                        InlineKeyboardButton(
                            "💰 按价值排序 ✅", callback_data=f"ca_sort_value_{cache_key}"
                        ),
                        InlineKeyboardButton(
                            "👥 按人数排序", callback_data=f"ca_sort_count_{cache_key}"
                        ),
                    )
                else:
                    markup.add(
                        InlineKeyboardButton(
                            "💰 按价值排序", callback_data=f"ca_sort_value_{cache_key}"
                        ),
                        InlineKeyboardButton(
                            "👥 按人数排序 ✅", callback_data=f"ca_sort_count_{cache_key}"
                        ),
                    )
                markup.add(
                    InlineKeyboardButton(
                        "🎯 共同持仓分析", callback_data=f"ca_cluster_{cache_key}"
                    ),
                    InlineKeyboardButton(
                        "📊 目标代币排名", callback_data=f"ca_ranking_{cache_key}"
                    )
                )

            # 更新消息
            self.bot.edit_message_text(
                final_msg,
                call.message.chat.id,
                call.message.message_id,
                parse_mode="HTML",
                reply_markup=markup,
                disable_web_page_preview=True,
            )
            self.bot.answer_callback_query(
                call.id, f"已切换到{'价值' if sort_by == 'value' else '人数'}排序"
            )

        except Exception as e:
            print(f"排序切换错误: {str(e)}")
            self.bot.answer_callback_query(call.id, f"❌ 切换排序失败: {str(e)}")

    def handle_ca_cluster(self, call: CallbackQuery) -> None:
        """处理共同持仓分析回调"""
        try:
            # 解析回调数据: ca_cluster_{cache_key} 或 ca_cluster_page_{cache_key}_{page}
            if call.data.startswith("ca_cluster_page_"):
                # 分页回调
                parts = call.data[len("ca_cluster_page_"):].split("_")
                if len(parts) >= 2:
                    cache_key = "_".join(parts[:-1])
                    page = int(parts[-1])
                    print(f"集群分页回调: cache_key={cache_key}, page={page}")
                    self._handle_cluster_page_callback(call, cache_key, page)
                else:
                    self.bot.answer_callback_query(call.id, "❌ 分页回调数据格式错误")
            else:
                # 普通集群分析回调
                cache_key = call.data[len("ca_cluster_"):]
                print(f"集群分析回调: cache_key={cache_key}")
                self._handle_cluster_callback(call, cache_key)
        except Exception as e:
            print(f"集群分析回调处理错误: {str(e)}")
            self.bot.answer_callback_query(call.id, f"❌ 处理集群分析失败: {str(e)}")

    def _handle_cluster_page_callback(self, call: CallbackQuery, cache_key: str, page: int):
        """处理集群分页回调"""
        try:
            # 从缓存中获取分析结果
            if cache_key not in analysis_cache:
                self.bot.answer_callback_query(call.id, "❌ 数据缓存已失效，请重新运行 /ca 命令")
                return

            cached_data = analysis_cache[cache_key]
            result = cached_data["result"]
            token_address = cached_data["token_address"]

            # 检查缓存是否过期
            if time.time() - cached_data["timestamp"] > 24 * 3600:
                self._show_expired_data_option(call, token_address)
                return

            # 检查是否已有集群分析结果缓存
            cluster_cache_key = f"{cache_key}_clusters"
            if cluster_cache_key in analysis_cache:
                # 使用缓存的集群分析结果
                cluster_result = analysis_cache[cluster_cache_key]["cluster_result"]
                self._show_cluster_page(call, cache_key, cluster_result, page)
            else:
                # 需要重新运行集群分析
                self.bot.answer_callback_query(call.id, "🔄 重新分析集群数据...")
                self._handle_cluster_callback(call, cache_key)

        except Exception as e:
            print(f"集群分页回调错误: cache_key={cache_key}, page={page}, error={str(e)}")
            self.bot.answer_callback_query(call.id, f"❌ 切换页面失败: {str(e)}")

    def _show_cluster_page(self, call: CallbackQuery, cache_key: str, cluster_result: dict, page: int):
        """显示指定页的集群分析结果"""
        try:
            # 格式化集群分析结果（支持分页）
            clusters_per_page = self.config.analysis.clusters_per_page
            cluster_msg, current_page, total_pages = format_cluster_analysis(
                cluster_result, 
                page=page, 
                clusters_per_page=clusters_per_page
            )

            # 创建分页按钮
            markup = InlineKeyboardMarkup(row_width=3)
            
            # 添加分页导航按钮
            nav_buttons = []
            if current_page > 1:
                nav_buttons.append(
                    InlineKeyboardButton("⬅️ 上一页", callback_data=f"ca_cluster_page_{cache_key}_{current_page-1}")
                )
            
            nav_buttons.append(
                InlineKeyboardButton(f"{current_page}/{total_pages}", callback_data="noop")
            )
            
            if current_page < total_pages:
                nav_buttons.append(
                    InlineKeyboardButton("下一页 ➡️", callback_data=f"ca_cluster_page_{cache_key}_{current_page+1}")
                )
            
            if nav_buttons:
                markup.row(*nav_buttons)
            
            # 添加功能按钮
            markup.add(
                InlineKeyboardButton("⬅️ 返回代币排行", callback_data=f"ca_sort_count_{cache_key}"),
                InlineKeyboardButton("🔄 重新运行", callback_data=f"ca_cluster_{cache_key}"),
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
            print(f"显示集群页面错误: cache_key={cache_key}, page={page}, error={str(e)}")
            self.bot.answer_callback_query(call.id, f"❌ 显示页面失败: {str(e)}")

    def _handle_cluster_callback(self, call: CallbackQuery, cache_key: str):
        """处理集群分析逻辑"""
        try:
            # 从缓存中获取分析结果
            if cache_key not in analysis_cache:
                self.bot.answer_callback_query(call.id, "❌ 数据缓存已失效，请重新运行 /ca 命令")
                return

            cached_data = analysis_cache[cache_key]
            result = cached_data["result"]
            token_address = cached_data["token_address"]

            # 检查缓存是否过期
            if time.time() - cached_data["timestamp"] > 24 * 3600:
                self._show_expired_data_option(call, token_address)
                return

            # 获取目标代币信息
            target_token_info = None
            for token in result["token_statistics"]["top_tokens_by_value"]:
                if token.get("address") == token_address:
                    target_token_info = token
                    break
            
            target_symbol = target_token_info.get("symbol", "Unknown") if target_token_info else "Unknown"

            # 显示正在分析的消息
            self.bot.edit_message_text(
                f"🎯 正在进行共同持仓分析...\n代币: <b>{target_symbol}</b> (<code>{token_address}</code>)\n⏳ 分析大户间的共同投资模式...",
                call.message.chat.id,
                call.message.message_id,
                parse_mode="HTML",
            )

            # 在后台线程中运行集群分析
            cluster_thread = threading.Thread(
                target=self._run_cluster_analysis,
                args=(call, cache_key, result, token_address),
                daemon=True,
            )
            cluster_thread.start()

            self.bot.answer_callback_query(call.id, "🎯 开始集群分析...")

        except Exception as e:
            print(f"集群分析回调错误: cache_key={cache_key}, error={str(e)}")
            self.bot.answer_callback_query(call.id, f"❌ 启动集群分析失败: {str(e)}")

    def _run_cluster_analysis(
        self, call: CallbackQuery, cache_key: str, result: dict, token_address: str, page: int = 1
    ):
        """在后台运行集群分析"""
        try:
            # 执行集群分析
            cluster_result = analyze_address_clusters(result)
            
            # 缓存集群分析结果
            cluster_cache_key = f"{cache_key}_clusters"
            analysis_cache[cluster_cache_key] = {
                "cluster_result": cluster_result,
                "timestamp": time.time(),
            }

            # 格式化集群分析结果（支持分页）
            clusters_per_page = self.config.analysis.clusters_per_page
            cluster_msg, current_page, total_pages = format_cluster_analysis(
                cluster_result, 
                page=page, 
                clusters_per_page=clusters_per_page
            )

            # 创建分页按钮
            markup = InlineKeyboardMarkup(row_width=3)
            
            # 添加分页导航按钮
            nav_buttons = []
            if current_page > 1:
                nav_buttons.append(
                    InlineKeyboardButton("⬅️ 上一页", callback_data=f"ca_cluster_page_{cache_key}_{current_page-1}")
                )
            
            nav_buttons.append(
                InlineKeyboardButton(f"{current_page}/{total_pages}", callback_data="noop")
            )
            
            if current_page < total_pages:
                nav_buttons.append(
                    InlineKeyboardButton("下一页 ➡️", callback_data=f"ca_cluster_page_{cache_key}_{current_page+1}")
                )
            
            if nav_buttons:
                markup.row(*nav_buttons)
            
            # 添加功能按钮
            markup.add(
                InlineKeyboardButton("⬅️ 返回代币排行", callback_data=f"ca_sort_count_{cache_key}"),
                InlineKeyboardButton("🔄 重新运行", callback_data=f"ca_cluster_{cache_key}"),
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

        except Exception as e:
            error_msg = f"❌ 集群分析失败\n代币: <code>{token_address}</code>\n错误: {str(e)}\n\n"
            error_msg += (
                f"💡 可能原因:\n• 数据不足以形成集群\n• 地址数据处理错误\n• 配置参数过于严格"
            )

            markup = InlineKeyboardMarkup()
            markup.add(
                InlineKeyboardButton("⬅️ 返回代币排行", callback_data=f"ca_sort_count_{cache_key}")
            )

            self.bot.edit_message_text(
                error_msg,
                call.message.chat.id,
                call.message.message_id,
                parse_mode="HTML",
                reply_markup=markup,
            )

    def handle_token_detail(self, call: CallbackQuery) -> None:
        """处理代币详情查看回调"""
        try:
            # 解析回调数据: token_detail_{cache_key}_{token_index}_{sort_by}
            callback_data = call.data[len("token_detail_") :]
            parts = callback_data.rsplit("_", 2)  # 从右边分割

            print(f"代币详情回调数据: {call.data}")
            print(f"解析结果: parts={parts}")

            if len(parts) >= 3:
                cache_key = parts[0]
                token_index = parts[1]
                current_sort = parts[2]
                print(
                    f"详情回调: cache_key={cache_key}, token_index={token_index}, sort={current_sort}"
                )
                self._handle_token_detail_callback(call, cache_key, token_index, current_sort)
            else:
                self.bot.answer_callback_query(call.id, "❌ 回调数据格式错误")

        except Exception as e:
            print(f"代币详情回调处理错误: {str(e)}")
            self.bot.answer_callback_query(call.id, f"❌ 处理代币详情失败: {str(e)}")

    def _handle_token_detail_callback(
        self, call: CallbackQuery, cache_key: str, token_index: str, current_sort: str
    ):
        """处理代币详情查看逻辑"""
        try:
            # 从缓存中获取分析结果
            if cache_key not in analysis_cache:
                self._show_reanalyze_option(call, cache_key)
                return

            cached_data = analysis_cache[cache_key]
            result = cached_data["result"]

            # 检查缓存是否过期
            if time.time() - cached_data["timestamp"] > 24 * 3600:
                self._show_expired_data_option(call, cached_data["token_address"])
                return

            # 获取代币统计数据
            token_stats = result.get("token_statistics", {})
            all_tokens = token_stats.get("top_tokens_by_value", [])

            if not all_tokens:
                self.bot.answer_callback_query(call.id, "❌ 未找到代币数据")
                return

            # 验证索引
            try:
                token_index = int(token_index)
                if token_index < 0 or token_index >= len(all_tokens):
                    self.bot.answer_callback_query(call.id, f"❌ 代币索引无效")
                    return
            except ValueError:
                self.bot.answer_callback_query(call.id, "❌ 代币索引格式错误")
                return

            # 根据当前排序方式获取正确的代币
            if current_sort == "count":
                sorted_tokens = sorted(all_tokens, key=lambda x: x["holder_count"], reverse=True)
            else:
                sorted_tokens = sorted(all_tokens, key=lambda x: x["total_value"], reverse=True)

            # 获取指定索引的代币信息
            if token_index >= len(sorted_tokens):
                self.bot.answer_callback_query(call.id, f"❌ 排序后索引无效")
                return

            token_info = sorted_tokens[token_index]

            # 格式化详情消息
            detail_msg = format_token_holders_detail(token_info, token_stats)

            # 创建返回按钮，保持当前排序方式
            markup = InlineKeyboardMarkup()
            return_callback = f"ca_sort_{current_sort}_{cache_key}"
            markup.add(InlineKeyboardButton("⬅️ 返回排行榜", callback_data=return_callback))

            # 发送详情消息
            self.bot.edit_message_text(
                detail_msg,
                call.message.chat.id,
                call.message.message_id,
                parse_mode="HTML",
                reply_markup=markup,
                disable_web_page_preview=True,
            )
            self.bot.answer_callback_query(call.id, f"已显示 {token_info['symbol']} 大户详情")

        except Exception as e:
            print(
                f"代币详情回调错误: cache_key={cache_key}, token_index={token_index}, error={str(e)}"
            )
            self.bot.answer_callback_query(call.id, f"❌ 获取代币详情失败: {str(e)}")

    def _show_reanalyze_option(self, call: CallbackQuery, cache_key: str):
        """显示重新分析选项"""
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🔄 重新分析", callback_data=f"ca_reanalyze_{cache_key}"))
        self.bot.edit_message_text(
            "❌ 数据已过期或丢失\n\n请点击下方按钮重新分析，或重新运行 /ca 命令",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup,
        )
        self.bot.answer_callback_query(call.id, "❌ 数据已过期，请重新分析")

    def handle_ca_ranking(self, call: CallbackQuery) -> None:
        """处理目标代币排名回调"""
        try:
            # 解析回调数据: ca_ranking_{cache_key}
            cache_key = call.data[len("ca_ranking_"):]
            print(f"目标代币排名回调: cache_key={cache_key}")
            
            # 从缓存中获取分析结果
            if cache_key not in analysis_cache:
                self.bot.answer_callback_query(call.id, "❌ 数据缓存已失效，请重新运行 /ca 命令")
                return

            cached_data = analysis_cache[cache_key]
            result = cached_data["result"]
            token_address = cached_data["token_address"]

            # 检查缓存是否过期
            if time.time() - cached_data["timestamp"] > 24 * 3600:
                self._show_expired_data_option(call, token_address)
                return

            # 获取目标代币信息
            target_token_info = None
            for token in result["token_statistics"]["top_tokens_by_value"]:
                if token.get("address") == token_address:
                    target_token_info = token
                    break
            
            target_symbol = target_token_info.get("symbol", "Unknown") if target_token_info else "Unknown"

            # 显示正在分析的消息
            self.bot.edit_message_text(
                f"📊 正在进行目标代币排名...\n代币: <b>{target_symbol}</b> (<code>{token_address}</code>)\n⏳ 分析目标代币在各大户钱包中的排名...",
                call.message.chat.id,
                call.message.message_id,
                parse_mode="HTML",
            )

            # 在后台线程中运行排名分析
            ranking_thread = threading.Thread(
                target=self._run_ranking_analysis,
                args=(call, cache_key, result, token_address),
                daemon=True,
            )
            ranking_thread.start()

            self.bot.answer_callback_query(call.id, "📊 开始排名分析...")

        except Exception as e:
            print(f"排名分析回调错误: error={str(e)}")
            self.bot.answer_callback_query(call.id, f"❌ 启动排名分析失败: {str(e)}")

    def _run_ranking_analysis(
        self, call: CallbackQuery, cache_key: str, result: dict, token_address: str
    ):
        """在后台运行排名分析"""
        try:
            # 执行排名分析，传入原始持有者数据
            original_holders = result.get("original_holders_data", [])
            ranking_result = analyze_target_token_rankings(result, original_holders)

            if ranking_result and ranking_result.get("rankings"):
                # 缓存排名分析结果
                ranking_cache_key = f"{cache_key}_rankings"
                analysis_cache[ranking_cache_key] = {
                    "ranking_result": ranking_result,
                    "timestamp": time.time(),
                }

                # 格式化排名消息
                ranking_msg = format_target_token_rankings(ranking_result)

                # 创建排名按钮 (1-10名 + >10名)
                markup = InlineKeyboardMarkup(row_width=5)
                
                # 第一行：1-5名
                rank_buttons_1 = []
                for rank in range(1, 6):
                    count = sum(1 for r in ranking_result["rankings"] if r["target_token_rank"] == rank)
                    if count > 0:
                        rank_buttons_1.append(
                            InlineKeyboardButton(f"{rank}名({count})", callback_data=f"ca_rank_{cache_key}_{rank}")
                        )
                if rank_buttons_1:
                    markup.row(*rank_buttons_1)
                
                # 第二行：6-10名
                rank_buttons_2 = []
                for rank in range(6, 11):
                    count = sum(1 for r in ranking_result["rankings"] if r["target_token_rank"] == rank)
                    if count > 0:
                        rank_buttons_2.append(
                            InlineKeyboardButton(f"{rank}名({count})", callback_data=f"ca_rank_{cache_key}_{rank}")
                        )
                if rank_buttons_2:
                    markup.row(*rank_buttons_2)
                
                # 第三行：>10名 + 阴谋钱包
                third_row_buttons = []
                over_10_count = sum(1 for r in ranking_result["rankings"] if r["target_token_rank"] > 10)
                if over_10_count > 0:
                    third_row_buttons.append(
                        InlineKeyboardButton(f">10名({over_10_count})", callback_data=f"ca_rank_{cache_key}_over10")
                    )
                
                # 添加阴谋钱包按钮
                conspiracy_count = sum(1 for r in ranking_result["rankings"] if r.get("is_conspiracy_wallet", False))
                if conspiracy_count > 0:
                    third_row_buttons.append(
                        InlineKeyboardButton(f"🔴阴谋({conspiracy_count})", callback_data=f"ca_rank_{cache_key}_conspiracy")
                    )
                
                if third_row_buttons:
                    markup.row(*third_row_buttons)
                
                # 功能按钮
                markup.add(
                    InlineKeyboardButton("⬅️ 返回代币排行", callback_data=f"ca_sort_count_{cache_key}"),
                    InlineKeyboardButton("🎯 共同持仓分析", callback_data=f"ca_cluster_{cache_key}")
                )
                markup.add(
                    InlineKeyboardButton("🔄 重新运行", callback_data=f"ca_ranking_{cache_key}")
                )

                # 更新消息
                self.bot.edit_message_text(
                    ranking_msg,
                    call.message.chat.id,
                    call.message.message_id,
                    parse_mode="HTML",
                    reply_markup=markup,
                    disable_web_page_preview=True,
                )

            else:
                # 分析失败或无数据
                error_msg = f"❌ 排名分析失败\n代币: <code>{token_address}</code>\n"
                error_msg += "💡 可能原因:\n• 没有大户持有目标代币\n• 数据不足以进行排名分析"

                markup = InlineKeyboardMarkup()
                markup.add(
                    InlineKeyboardButton("⬅️ 返回代币排行", callback_data=f"ca_sort_count_{cache_key}")
                )

                self.bot.edit_message_text(
                    error_msg,
                    call.message.chat.id,
                    call.message.message_id,
                    parse_mode="HTML",
                    reply_markup=markup,
                    disable_web_page_preview=True,
                )

        except Exception as e:
            print(f"排名分析执行错误: cache_key={cache_key}, error={str(e)}")
            import traceback
            traceback.print_exc()

            # 显示错误消息
            error_msg = f"❌ 排名分析失败\n代币: <code>{token_address}</code>\n错误: {str(e)}"

            markup = InlineKeyboardMarkup()
            markup.add(
                InlineKeyboardButton("⬅️ 返回代币排行", callback_data=f"ca_sort_count_{cache_key}")
            )

            self.bot.edit_message_text(
                error_msg,
                call.message.chat.id,
                call.message.message_id,
                parse_mode="HTML",
                reply_markup=markup,
                disable_web_page_preview=True,
            )

    def handle_ca_rank_detail(self, call: CallbackQuery) -> None:
        """处理排名详情查看回调"""
        try:
            # 解析回调数据: ca_rank_{cache_key}_{rank} 或 ca_rank_{cache_key}_over10
            data_parts = call.data[len("ca_rank_"):].split("_")
            if len(data_parts) < 2:
                self.bot.answer_callback_query(call.id, "❌ 回调数据格式错误")
                return
                
            cache_key = "_".join(data_parts[:-1])  # 重组cache_key，可能包含下划线
            rank_part = data_parts[-1]
            
            print(f"排名详情回调: cache_key={cache_key}, rank_part={rank_part}")
            
            # 从缓存中获取排名分析结果
            ranking_cache_key = f"{cache_key}_rankings"
            if ranking_cache_key not in analysis_cache:
                self.bot.answer_callback_query(call.id, "❌ 排名数据缓存已失效，请重新运行排名分析")
                return

            cached_data = analysis_cache[ranking_cache_key]
            ranking_result = cached_data["ranking_result"]
            
            # 检查缓存是否过期
            if time.time() - cached_data["timestamp"] > 24 * 3600:
                self.bot.answer_callback_query(call.id, "❌ 数据已过期，请重新分析")
                return

            # 根据rank_part筛选地址
            rankings = ranking_result.get("rankings", [])
            if rank_part == "over10":
                filtered_rankings = [r for r in rankings if r["target_token_rank"] > 10]
                rank_title = ">10名"
            elif rank_part == "conspiracy":
                filtered_rankings = [r for r in rankings if r.get("is_conspiracy_wallet", False)]
                rank_title = "阴谋钱包"
            else:
                try:
                    target_rank = int(rank_part)
                    filtered_rankings = [r for r in rankings if r["target_token_rank"] == target_rank]
                    rank_title = f"第{target_rank}名"
                except ValueError:
                    self.bot.answer_callback_query(call.id, "❌ 排名参数格式错误")
                    return
            
            if not filtered_rankings:
                self.bot.answer_callback_query(call.id, f"❌ 没有找到{rank_title}的地址")
                return
            
            # 格式化详情消息
            target_token = ranking_result.get("target_token", {})
            symbol = target_token.get("symbol", "Unknown")
            
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
                InlineKeyboardButton("⬅️ 返回排名分析", callback_data=f"ca_ranking_{cache_key}")
            )
            
            # 更新消息
            self.bot.edit_message_text(
                msg,
                call.message.chat.id,
                call.message.message_id,
                parse_mode="HTML",
                reply_markup=markup,
                disable_web_page_preview=True,
            )
            
            self.bot.answer_callback_query(call.id, f"已显示{rank_title}的地址详情")

        except Exception as e:
            print(f"排名详情回调错误: error={str(e)}")
            import traceback
            traceback.print_exc()
            self.bot.answer_callback_query(call.id, f"❌ 获取排名详情失败: {str(e)}")

    def _show_expired_data_option(self, call: CallbackQuery, token_address: str):
        """显示过期数据选项"""
        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("🔄 重新分析", callback_data=f"ca_reanalyze_{token_address}")
        )
        self.bot.edit_message_text(
            f"❌ 数据已过期（超过24小时）\n代币: <code>{token_address}</code>\n\n请点击下方按钮重新分析，或重新运行 /ca 命令",
            call.message.chat.id,
            call.message.message_id,
            parse_mode="HTML",
            reply_markup=markup,
            disable_web_page_preview=True,
        )
        self.bot.answer_callback_query(call.id, "❌ 数据已过期，请重新分析")

    def register_handlers(self) -> None:
        """注册处理器"""

        @self.bot.message_handler(commands=["ca"])
        def ca_handler(message):
            self.handle_ca(message)

        @self.bot.callback_query_handler(func=lambda call: call.data.startswith("ca_sort_"))
        def ca_sort_handler(call):
            self.handle_ca_sort(call)

        @self.bot.callback_query_handler(func=lambda call: call.data.startswith("ca_cluster_"))
        def ca_cluster_handler(call):
            self.handle_ca_cluster(call)

        @self.bot.callback_query_handler(func=lambda call: call.data.startswith("ca_ranking_"))
        def ca_ranking_handler(call):
            self.handle_ca_ranking(call)

        @self.bot.callback_query_handler(func=lambda call: call.data.startswith("ca_rank_"))
        def ca_rank_detail_handler(call):
            self.handle_ca_rank_detail(call)

        @self.bot.callback_query_handler(func=lambda call: call.data.startswith("token_detail_"))
        def token_detail_handler(call):
            self.handle_token_detail(call)

        @self.bot.callback_query_handler(func=lambda call: call.data == "noop")
        def noop_handler(call):
            self.bot.answer_callback_query(call.id)
