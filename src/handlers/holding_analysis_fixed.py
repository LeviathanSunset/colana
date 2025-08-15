"""
持仓分析命令处理器
处理 /ca1 命令和相关的OKX大户分析功能
"""

import time
import threading
from telebot import TeleBot
from telebot.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from ..services.formatter import MessageFormatter
from ..core.config import get_config

# 导入OKX相关功能
try:
    from ..services.okx_crawler import (
        OKXCrawlerForBot,
        format_tokens_table,
        format_token_holders_detail,
        analyze_address_clusters,
        format_cluster_analysis,
    )
except ImportError:
    print("⚠️ 无法导入OKX爬虫模块，/ca1功能可能不可用")
    OKXCrawlerForBot = None


class HoldingAnalysisHandler:
    """持仓分析处理器"""

    def __init__(self, bot: TeleBot):
        self.bot = bot
        self.config = get_config()
        self.formatter = MessageFormatter()

        # 全局缓存存储分析结果
        self.analysis_cache = {}

        # 启动缓存清理线程
        self._start_cache_cleanup()

    def _start_cache_cleanup(self):
        """启动缓存清理线程"""

        def cleanup_loop():
            while True:
                try:
                    self._cleanup_expired_cache()
                    time.sleep(3600)  # 每小时清理一次
                except Exception as e:
                    print(f"缓存清理错误: {e}")
                    time.sleep(600)  # 出错时10分钟后重试

        cleanup_thread = threading.Thread(target=cleanup_loop, daemon=True)
        cleanup_thread.start()

    def _cleanup_expired_cache(self):
        """清理过期的缓存条目"""
        current_time = time.time()
        expired_keys = []

        for key, data in self.analysis_cache.items():
            if current_time - data.get("timestamp", 0) > 24 * 3600:  # 24小时过期
                expired_keys.append(key)

        for key in expired_keys:
            del self.analysis_cache[key]

        if expired_keys:
            print(f"清理了 {len(expired_keys)} 个过期缓存")

    def handle_ca1(self, message: Message) -> None:
        """处理 /ca1 命令 - OKX大户分析"""
        if not OKXCrawlerForBot:
            self.bot.reply_to(message, "❌ OKX分析功能暂时不可用\n请检查依赖模块是否正确安装")
            return

        # 检查群组权限
        chat_id = str(message.chat.id)
        allowed_groups = self.config.ca1_allowed_groups
        
        if allowed_groups and chat_id not in allowed_groups:
            self.bot.reply_to(
                message, 
                "❌ 此功能仅在特定群组中可用\n如需使用，请联系管理员"
            )
            return

        # 提取代币地址参数
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            self.bot.reply_to(message, "❌ 请提供代币地址\n用法: /ca1 <token_address>")
            return

        token_address = parts[1].strip()

        if not token_address:
            self.bot.reply_to(message, "❌ 请提供代币地址\n用法: /ca1 <token_address>")
            return

        if len(token_address) < 20:  # 简单验证地址长度
            self.bot.reply_to(message, "❌ 请输入有效的代币地址")
            return

        # 发送开始分析的消息
        processing_msg = self.bot.reply_to(
            message,
            f"🔍 正在分析代币大户持仓...\n代币地址: `{token_address}`\n⏳ 预计需要1-2分钟，请稍候...",
            parse_mode="Markdown",
        )

        # 在后台线程中运行分析
        analysis_thread = threading.Thread(
            target=self._run_analysis, args=(processing_msg, token_address), daemon=True
        )
        analysis_thread.start()

    def _run_analysis(self, processing_msg, token_address: str):
        """在后台运行分析"""
        try:
            # 清理过期缓存
            self._cleanup_expired_cache()

            # 创建OKX爬虫实例
            crawler = OKXCrawlerForBot()

            # 执行分析
            result = crawler.analyze_token_holders(
                token_address, top_holders_count=self.config.analysis.top_holders_count
            )

            if result and result.get("token_statistics"):
                # 缓存分析结果
                cache_key = f"{processing_msg.chat.id}_{processing_msg.message_id}"
                self.analysis_cache[cache_key] = {
                    "result": result,
                    "token_address": token_address,
                    "timestamp": time.time(),
                }

                print(f"缓存分析结果: cache_key={cache_key}")

                # 格式化表格消息（默认按人数排序）
                table_msg, table_markup = format_tokens_table(
                    result["token_statistics"],
                    max_tokens=self.config.analysis.ranking_size,
                    sort_by="count",
                    cache_key=cache_key,
                )

                # 添加分析信息
                analysis_info = f"\n📊 <b>分析统计</b>\n"
                analysis_info += f"🕒 分析时间: {result.get('analysis_time', '').split('T')[0]}\n"
                analysis_info += f"👥 分析地址: 前{result.get('total_holders_analyzed', 0)} 个\n"
                target_holders = result.get("target_token_actual_holders", 0)
                if target_holders > 0:
                    analysis_info += f"🎯 实际持有目标代币: {target_holders} 人\n"
                analysis_info += f"📈 统计范围: 每个地址的前10大持仓\n"

                final_msg = table_msg + analysis_info

                # 创建完整的按钮布局
                if table_markup:
                    # 添加排序切换按钮
                    table_markup.add(
                        InlineKeyboardButton(
                            "💰 按价值排序", callback_data=f"ca1_sort_value_{cache_key}"
                        ),
                        InlineKeyboardButton(
                            "👥 按人数排序 ✅", callback_data=f"ca1_sort_count_{cache_key}"
                        ),
                    )
                    # 添加集群分析按钮
                    table_markup.add(
                        InlineKeyboardButton(
                            "🎯 地址集群分析", callback_data=f"ca1_cluster_{cache_key}"
                        )
                    )
                    markup = table_markup
                else:
                    # 如果没有代币详情按钮，只添加排序和集群按钮
                    markup = InlineKeyboardMarkup(row_width=2)
                    markup.add(
                        InlineKeyboardButton(
                            "💰 按价值排序", callback_data=f"ca1_sort_value_{cache_key}"
                        ),
                        InlineKeyboardButton(
                            "👥 按人数排序 ✅", callback_data=f"ca1_sort_count_{cache_key}"
                        ),
                    )
                    markup.add(
                        InlineKeyboardButton(
                            "🎯 地址集群分析", callback_data=f"ca1_cluster_{cache_key}"
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
            else:
                self.bot.edit_message_text(
                    f"❌ 分析失败\n代币地址: `{token_address}`\n\n可能原因:\n• 代币地址无效\n• 网络连接问题\n• API限制\n\n详细日志请查看 logs/okx_analysis/ 目录",
                    processing_msg.chat.id,
                    processing_msg.message_id,
                    parse_mode="Markdown",
                )

        except Exception as e:
            self.bot.edit_message_text(
                f"❌ 分析过程中发生错误\n代币地址: `{token_address}`\n错误信息: {str(e)}\n\n详细日志请查看 logs/okx_analysis/ 目录",
                processing_msg.chat.id,
                processing_msg.message_id,
                parse_mode="Markdown",
            )

    def handle_ca1_sort(self, call: CallbackQuery) -> None:
        """处理排序切换回调"""
        try:
            # 解析回调数据: ca1_sort_{sort_by}_{cache_key}
            callback_data = call.data[len("ca1_sort_") :]
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
            if cache_key not in self.analysis_cache:
                self._show_reanalyze_option(call, cache_key)
                return

            cached_data = self.analysis_cache[cache_key]
            result = cached_data["result"]

            # 检查缓存是否过期（24小时）
            if time.time() - cached_data["timestamp"] > 24 * 3600:
                self._show_expired_data_option(call, cached_data["token_address"])
                return

            # 重新格式化表格
            table_msg, table_markup = format_tokens_table(
                result["token_statistics"],
                max_tokens=self.config.analysis.ranking_size,
                sort_by=sort_by,
                cache_key=cache_key,
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
                            "💰 按价值排序 ✅", callback_data=f"ca1_sort_value_{cache_key}"
                        ),
                        InlineKeyboardButton(
                            "👥 按人数排序", callback_data=f"ca1_sort_count_{cache_key}"
                        ),
                    )
                else:
                    table_markup.add(
                        InlineKeyboardButton(
                            "💰 按价值排序", callback_data=f"ca1_sort_value_{cache_key}"
                        ),
                        InlineKeyboardButton(
                            "👥 按人数排序 ✅", callback_data=f"ca1_sort_count_{cache_key}"
                        ),
                    )
                # 添加集群分析按钮
                table_markup.add(
                    InlineKeyboardButton(
                        "🎯 地址集群分析", callback_data=f"ca1_cluster_{cache_key}"
                    )
                )
                markup = table_markup
            else:
                # 如果没有代币详情按钮，只添加排序和集群按钮
                markup = InlineKeyboardMarkup(row_width=2)
                if sort_by == "value":
                    markup.add(
                        InlineKeyboardButton(
                            "💰 按价值排序 ✅", callback_data=f"ca1_sort_value_{cache_key}"
                        ),
                        InlineKeyboardButton(
                            "👥 按人数排序", callback_data=f"ca1_sort_count_{cache_key}"
                        ),
                    )
                else:
                    markup.add(
                        InlineKeyboardButton(
                            "💰 按价值排序", callback_data=f"ca1_sort_value_{cache_key}"
                        ),
                        InlineKeyboardButton(
                            "👥 按人数排序 ✅", callback_data=f"ca1_sort_count_{cache_key}"
                        ),
                    )
                markup.add(
                    InlineKeyboardButton(
                        "🎯 地址集群分析", callback_data=f"ca1_cluster_{cache_key}"
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

    def handle_ca1_cluster(self, call: CallbackQuery) -> None:
        """处理地址集群分析回调"""
        try:
            # 解析回调数据: ca1_cluster_{cache_key} 或 ca1_cluster_page_{cache_key}_{page}
            if call.data.startswith("ca1_cluster_page_"):
                # 分页回调
                parts = call.data[len("ca1_cluster_page_"):].split("_")
                if len(parts) >= 2:
                    cache_key = "_".join(parts[:-1])
                    page = int(parts[-1])
                    print(f"集群分页回调: cache_key={cache_key}, page={page}")
                    self._handle_cluster_page_callback(call, cache_key, page)
                else:
                    self.bot.answer_callback_query(call.id, "❌ 分页回调数据格式错误")
            else:
                # 普通集群分析回调
                cache_key = call.data[len("ca1_cluster_"):]
                print(f"集群分析回调: cache_key={cache_key}")
                self._handle_cluster_callback(call, cache_key)
        except Exception as e:
            print(f"集群分析回调处理错误: {str(e)}")
            self.bot.answer_callback_query(call.id, f"❌ 处理集群分析失败: {str(e)}")

    def _handle_cluster_page_callback(self, call: CallbackQuery, cache_key: str, page: int):
        """处理集群分页回调"""
        try:
            # 从缓存中获取分析结果
            if cache_key not in self.analysis_cache:
                self.bot.answer_callback_query(call.id, "❌ 数据缓存已失效，请重新运行 /ca1 命令")
                return

            cached_data = self.analysis_cache[cache_key]
            result = cached_data["result"]
            token_address = cached_data["token_address"]

            # 检查缓存是否过期
            if time.time() - cached_data["timestamp"] > 24 * 3600:
                self._show_expired_data_option(call, token_address)
                return

            # 检查是否已有集群分析结果缓存
            cluster_cache_key = f"{cache_key}_clusters"
            if cluster_cache_key in self.analysis_cache:
                # 使用缓存的集群分析结果
                cluster_result = self.analysis_cache[cluster_cache_key]["cluster_result"]
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
                    InlineKeyboardButton("⬅️ 上一页", callback_data=f"ca1_cluster_page_{cache_key}_{current_page-1}")
                )
            
            nav_buttons.append(
                InlineKeyboardButton(f"{current_page}/{total_pages}", callback_data="noop")
            )
            
            if current_page < total_pages:
                nav_buttons.append(
                    InlineKeyboardButton("下一页 ➡️", callback_data=f"ca1_cluster_page_{cache_key}_{current_page+1}")
                )
            
            if nav_buttons:
                markup.row(*nav_buttons)
            
            # 添加功能按钮
            markup.add(
                InlineKeyboardButton("⬅️ 返回代币排行", callback_data=f"ca1_sort_count_{cache_key}"),
                InlineKeyboardButton("🔄 重新运行", callback_data=f"ca1_cluster_{cache_key}"),
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
            if cache_key not in self.analysis_cache:
                self.bot.answer_callback_query(call.id, "❌ 数据缓存已失效，请重新运行 /ca1 命令")
                return

            cached_data = self.analysis_cache[cache_key]
            result = cached_data["result"]
            token_address = cached_data["token_address"]

            # 检查缓存是否过期
            if time.time() - cached_data["timestamp"] > 24 * 3600:
                self._show_expired_data_option(call, token_address)
                return

            # 显示正在分析的消息
            self.bot.edit_message_text(
                f"🎯 正在进行地址集群分析...\n代币: <code>{token_address}</code>\n⏳ 分析大户间的共同投资模式...",
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
            self.analysis_cache[cluster_cache_key] = {
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
                    InlineKeyboardButton("⬅️ 上一页", callback_data=f"ca1_cluster_page_{cache_key}_{current_page-1}")
                )
            
            nav_buttons.append(
                InlineKeyboardButton(f"{current_page}/{total_pages}", callback_data="noop")
            )
            
            if current_page < total_pages:
                nav_buttons.append(
                    InlineKeyboardButton("下一页 ➡️", callback_data=f"ca1_cluster_page_{cache_key}_{current_page+1}")
                )
            
            if nav_buttons:
                markup.row(*nav_buttons)
            
            # 添加功能按钮
            markup.add(
                InlineKeyboardButton("⬅️ 返回代币排行", callback_data=f"ca1_sort_count_{cache_key}"),
                InlineKeyboardButton("🔄 重新运行", callback_data=f"ca1_cluster_{cache_key}"),
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
                InlineKeyboardButton("⬅️ 返回代币排行", callback_data=f"ca1_sort_count_{cache_key}")
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
            if cache_key not in self.analysis_cache:
                self._show_reanalyze_option(call, cache_key)
                return

            cached_data = self.analysis_cache[cache_key]
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
            return_callback = f"ca1_sort_{current_sort}_{cache_key}"
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
        markup.add(InlineKeyboardButton("🔄 重新分析", callback_data=f"ca1_reanalyze_{cache_key}"))
        self.bot.edit_message_text(
            "❌ 数据已过期或丢失\n\n请点击下方按钮重新分析，或重新运行 /ca1 命令",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup,
        )
        self.bot.answer_callback_query(call.id, "❌ 数据已过期，请重新分析")

    def _show_expired_data_option(self, call: CallbackQuery, token_address: str):
        """显示过期数据选项"""
        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("🔄 重新分析", callback_data=f"ca1_reanalyze_{token_address}")
        )
        self.bot.edit_message_text(
            f"❌ 数据已过期（超过24小时）\n代币: <code>{token_address}</code>\n\n请点击下方按钮重新分析，或重新运行 /ca1 命令",
            call.message.chat.id,
            call.message.message_id,
            parse_mode="HTML",
            reply_markup=markup,
            disable_web_page_preview=True,
        )
        self.bot.answer_callback_query(call.id, "❌ 数据已过期，请重新分析")

    def register_handlers(self) -> None:
        """注册处理器"""

        @self.bot.message_handler(commands=["ca1"])
        def ca1_handler(message):
            self.handle_ca1(message)

        @self.bot.callback_query_handler(func=lambda call: call.data.startswith("ca1_sort_"))
        def ca1_sort_handler(call):
            self.handle_ca1_sort(call)

        @self.bot.callback_query_handler(func=lambda call: call.data.startswith("ca1_cluster_"))
        def ca1_cluster_handler(call):
            self.handle_ca1_cluster(call)

        @self.bot.callback_query_handler(func=lambda call: call.data.startswith("token_detail_"))
        def token_detail_handler(call):
            self.handle_token_detail(call)

        @self.bot.callback_query_handler(func=lambda call: call.data == "noop")
        def noop_handler(call):
            self.bot.answer_callback_query(call.id)
