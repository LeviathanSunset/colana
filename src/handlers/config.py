"""
配置管理命令处理器
处理 /config 命令和相关回调
"""

from telebot import TeleBot
from telebot.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from ..core.config import get_config
from ..services.formatter import MessageFormatter
from ..services.blacklist import get_blacklist_manager


class ConfigCommandHandler:
    """配置命令处理器"""

    def __init__(self, bot: TeleBot):
        self.bot = bot
        self.config = get_config()
        self.formatter = MessageFormatter()
        self.blacklist_manager = get_blacklist_manager()

    def handle_config(self, message: Message) -> None:
        """处理 /config 命令"""
        config_msg = self.formatter.format_config_message(self.config)
        keyboard = self._create_config_keyboard()

        self.bot.reply_to(message, config_msg, parse_mode="HTML", reply_markup=keyboard)

    def _create_config_keyboard(self) -> InlineKeyboardMarkup:
        """创建配置键盘"""
        keyboard = InlineKeyboardMarkup(row_width=2)

        # 主要功能模块 - 6个核心功能按钮
        keyboard.add(
            InlineKeyboardButton("� 泵检警报", callback_data="config_pump_alert"),
            InlineKeyboardButton("🤖 自动泵检分析", callback_data="config_auto_pump_analysis"),
        )
        keyboard.add(
            InlineKeyboardButton("� 持有者分析", callback_data="config_holder_analysis"),
            InlineKeyboardButton("🪐 Jupiter分析", callback_data="config_jup_analysis"),
        )

        # 存储管理和黑名单管理
        keyboard.add(
            InlineKeyboardButton("📁 存储管理", callback_data="storage_management"),
            InlineKeyboardButton("🚫 黑名单管理", callback_data="blacklist_menu"),
        )

        return keyboard

    def handle_edit_config(self, call: CallbackQuery) -> None:
        """处理配置编辑回调"""
        key = call.data.replace("edit_", "")

        # 配置项映射
        config_map = {
            "interval": ("bot", "检查间隔（秒）"),
            "threshold": ("bot", "涨幅阈值（例如0.05表示5%）"),
            "min_market_cap": ("bot", "最小市值（美元）"),
            "min_age_days": ("bot", "最小年龄（天）"),
            "top_holders_count": ("analysis", "大户数量"),
            "ranking_size": ("analysis", "排行榜大小"),
            "detail_buttons_count": ("analysis", "详情按钮数"),
            "cluster_min_common_tokens": ("analysis", "集群最小通用代币数"),
            "cluster_min_addresses": ("analysis", "集群最小地址数"),
            "cluster_max_addresses": ("analysis", "集群最大地址数"),
            "clusters_per_page": ("analysis", "每页集群数"),
            "jupiter_max_mcap": ("jupiter", "最大市值（美元）"),
            "jupiter_min_token_age": ("jupiter", "最小代币年龄（秒）"),
            "jupiter_default_token_count": ("jupiter", "默认分析数量"),
            "jupiter_max_tokens_per_analysis": ("jupiter", "最大分析数量"),
        }

        if key in config_map:
            section, description = config_map[key]
            # 处理特殊的Jupiter参数名转换
            config_key = key
            if key.startswith("jupiter_"):
                config_key = key.replace("jupiter_", "")
            
            msg = self.bot.send_message(
                call.message.chat.id, f"请输入新的 <b>{description}</b>：", parse_mode="HTML"
            )
            self.bot.register_next_step_handler(
                msg, lambda m: self._save_config_value(m, section, config_key)
            )

        self.bot.answer_callback_query(call.id)

    def _save_config_value(self, message: Message, section: str, key: str) -> None:
        """保存配置值"""
        try:
            value = message.text.strip()

            # 类型转换
            if key in [
                "interval",
                "min_age_days",
                "top_holders_count",
                "ranking_size",
                "detail_buttons_count",
                "cluster_min_common_tokens",
                "cluster_min_addresses",
                "cluster_max_addresses",
                "clusters_per_page",
                "max_mcap",
                "min_token_age",
                "default_token_count",
                "max_tokens_per_analysis",
            ]:
                value = int(value)
            elif key in ["threshold", "min_market_cap"]:
                value = float(value)

            # 更新配置
            self.config.update_config(section, **{key: value})

            success_msg = self.formatter.format_success_message(f"配置已更新: {key} = {value}")
            self.bot.reply_to(message, success_msg, parse_mode="HTML")

        except ValueError:
            error_msg = self.formatter.format_error_message("输入格式错误，请输入正确的数值")
            self.bot.reply_to(message, error_msg, parse_mode="HTML")
        except Exception as e:
            error_msg = self.formatter.format_error_message(f"保存失败: {e}")
            self.bot.reply_to(message, error_msg, parse_mode="HTML")

    def handle_blacklist_menu(self, call: CallbackQuery) -> None:
        """处理黑名单菜单"""
        count = self.blacklist_manager.get_blacklist_count()
        blacklist_msg = self.formatter.format_blacklist_info(count)

        keyboard = InlineKeyboardMarkup()
        keyboard.add(
            InlineKeyboardButton("➕ 添加黑名单", callback_data="add_blacklist"),
            InlineKeyboardButton("➖ 移除黑名单", callback_data="remove_blacklist"),
        )
        keyboard.add(InlineKeyboardButton("📋 查看黑名单", callback_data="view_blacklist"))
        keyboard.add(InlineKeyboardButton("↩️ 返回配置", callback_data="back_to_config"))

        self.bot.edit_message_text(
            blacklist_msg,
            call.message.chat.id,
            call.message.message_id,
            parse_mode="HTML",
            reply_markup=keyboard,
        )
        self.bot.answer_callback_query(call.id)

    def handle_add_blacklist(self, call: CallbackQuery) -> None:
        """处理添加黑名单"""
        msg = self.bot.send_message(call.message.chat.id, "请输入要添加到黑名单的代币地址：")
        self.bot.register_next_step_handler(msg, self._add_blacklist_address)
        self.bot.answer_callback_query(call.id)

    def _add_blacklist_address(self, message: Message) -> None:
        """添加黑名单地址"""
        address = message.text.strip()

        if self.blacklist_manager.add_to_blacklist(address):
            response = self.formatter.format_success_message(f"已添加到黑名单: {address}")
        else:
            response = self.formatter.format_error_message("该地址已在黑名单中")

        self.bot.reply_to(message, response, parse_mode="HTML")

    def handle_remove_blacklist(self, call: CallbackQuery) -> None:
        """处理移除黑名单"""
        msg = self.bot.send_message(call.message.chat.id, "请输入要从黑名单移除的代币地址：")
        self.bot.register_next_step_handler(msg, self._remove_blacklist_address)
        self.bot.answer_callback_query(call.id)

    def _remove_blacklist_address(self, message: Message) -> None:
        """移除黑名单地址"""
        address = message.text.strip()

        if self.blacklist_manager.remove_from_blacklist(address):
            response = self.formatter.format_success_message(f"已从黑名单移除: {address}")
        else:
            response = self.formatter.format_error_message("该地址不在黑名单中")

        self.bot.reply_to(message, response, parse_mode="HTML")

    def handle_view_blacklist(self, call: CallbackQuery) -> None:
        """处理查看黑名单"""
        blacklist = self.blacklist_manager.get_blacklist_list()

        if not blacklist:
            response = "🚫 黑名单为空"
        else:
            response = f"🚫 <b>黑名单列表</b> (共{len(blacklist)}个)\n\n"
            for i, addr in enumerate(blacklist[:20], 1):  # 只显示前20个
                addr_short = f"{addr[:8]}...{addr[-8:]}" if len(addr) > 20 else addr
                response += f"{i}. <code>{addr_short}</code>\n"

            if len(blacklist) > 20:
                response += f"\n... 还有 {len(blacklist) - 20} 个地址"

        self.bot.send_message(call.message.chat.id, response, parse_mode="HTML")
        self.bot.answer_callback_query(call.id)

    def handle_auto_alert_config(self, call: CallbackQuery) -> None:
        """处理自动警报配置页面"""
        config = self.config.bot
        
        response = (
            "🔍 <b>自动警报配置</b>\n\n"
            f"⏱️ 检查间隔: <code>{config.interval}</code> 秒\n"
            f"📈 涨幅阈值: <code>{config.threshold * 100:.1f}%</code>\n"
            f"💰 最小市值: <code>${config.min_market_cap:,.0f}</code>\n"
            f"📅 最小年龄: <code>{config.min_age_days}</code> 天\n"
        )
        
        keyboard = InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            InlineKeyboardButton("⏱️ 检查间隔", callback_data="edit_interval"),
            InlineKeyboardButton("📈 涨幅阈值", callback_data="edit_threshold"),
        )
        keyboard.add(
            InlineKeyboardButton("💰 最小市值", callback_data="edit_min_market_cap"),
            InlineKeyboardButton("📅 最小年龄", callback_data="edit_min_age_days"),
        )
        keyboard.add(InlineKeyboardButton("⬅️ 返回主菜单", callback_data="back_to_config"))
        
        self.bot.edit_message_text(
            response,
            call.message.chat.id,
            call.message.message_id,
            parse_mode="HTML",
            reply_markup=keyboard,
        )
        self.bot.answer_callback_query(call.id)

    def handle_pump_alert_config(self, call: CallbackQuery) -> None:
        """处理泵检警报配置页面"""
        config = self.config.bot
        
        response = (
            "🔔 <b>泵检警报配置</b>\n\n"
            f"⏱️ 检查间隔: <code>{config.interval}</code> 秒\n"
            f"📈 涨幅阈值: <code>{config.threshold * 100:.1f}%</code>\n"
            f"💰 最小市值: <code>${config.min_market_cap:,.0f}</code>\n"
            f"📅 最小年龄: <code>{config.min_age_days}</code> 天\n"
        )
        
        keyboard = InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            InlineKeyboardButton("⏱️ 检查间隔", callback_data="edit_interval"),
            InlineKeyboardButton("📈 涨幅阈值", callback_data="edit_threshold"),
        )
        keyboard.add(
            InlineKeyboardButton("💰 最小市值", callback_data="edit_min_market_cap"),
            InlineKeyboardButton("📅 最小年龄", callback_data="edit_min_age_days"),
        )
        keyboard.add(InlineKeyboardButton("⬅️ 返回主菜单", callback_data="back_to_config"))
        
        self.bot.edit_message_text(
            response,
            call.message.chat.id,
            call.message.message_id,
            parse_mode="HTML",
            reply_markup=keyboard,
        )
        self.bot.answer_callback_query(call.id)

    def handle_auto_pump_analysis_config(self, call: CallbackQuery) -> None:
        """处理自动泵检分析配置页面"""
        config = self.config.capump
        
        response = (
            "🤖 <b>自动泵检分析配置</b>\n\n"
            f"⏱️ 爬取间隔: <code>{config.interval}</code> 秒\n"
            f"📈 涨幅阈值: <code>{config.threshold * 100:.1f}%</code>\n"
            f"💰 最小市值: <code>${config.min_market_cap:,.0f}</code>\n"
            f"📅 代币年龄: <code>{config.min_age_days}</code> 天\n"
            f"🔔 自动分析: <code>{'✅ 已启用' if config.auto_analysis_enabled else '❌ 已禁用'}</code>\n"
            f"🔢 批次大小: <code>{config.max_tokens_per_batch}</code> 个代币\n"
        )
        
        keyboard = InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            InlineKeyboardButton("⏱️ 爬取间隔", callback_data="edit_capump_interval"),
            InlineKeyboardButton("📈 涨幅阈值", callback_data="edit_capump_threshold"),
        )
        keyboard.add(
            InlineKeyboardButton("💰 最小市值", callback_data="edit_capump_min_market_cap"),
            InlineKeyboardButton("📅 代币年龄", callback_data="edit_capump_min_age_days"),
        )
        keyboard.add(
            InlineKeyboardButton("🔢 批次大小", callback_data="edit_capump_max_tokens_per_batch"),
            InlineKeyboardButton(
                f"🔔 自动分析 {'✅' if config.auto_analysis_enabled else '❌'}", 
                callback_data="toggle_capump_auto_analysis"
            ),
        )
        keyboard.add(InlineKeyboardButton("⬅️ 返回主菜单", callback_data="back_to_config"))
        
        self.bot.edit_message_text(
            response,
            call.message.chat.id,
            call.message.message_id,
            parse_mode="HTML",
            reply_markup=keyboard,
        )
        self.bot.answer_callback_query(call.id)

    def handle_holder_analysis_config(self, call: CallbackQuery) -> None:
        """处理持有者分析配置页面"""
        config = self.config.analysis
        
        response = (
            "👥 <b>持有者分析配置</b>\n\n"
            f"👥 大户数量: <code>{config.top_holders_count}</code>\n"
            f"📊 排行榜大小: <code>{config.ranking_size}</code>\n"
            f"🔘 详情按钮数: <code>{config.detail_buttons_count}</code>\n"
            f"🔗 集群最小通用代币: <code>{config.cluster_min_common_tokens}</code>\n"
            f"📊 集群最小地址数: <code>{config.cluster_min_addresses}</code>\n"
            f"📊 集群最大地址数: <code>{config.cluster_max_addresses}</code>\n"
            f"📄 每页集群数: <code>{config.clusters_per_page}</code>\n"
        )
        
        keyboard = InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            InlineKeyboardButton("👥 大户数量", callback_data="edit_top_holders_count"),
            InlineKeyboardButton("📊 排行榜大小", callback_data="edit_ranking_size"),
        )
        keyboard.add(
            InlineKeyboardButton("🔘 详情按钮数", callback_data="edit_detail_buttons_count"),
            InlineKeyboardButton("🔗 集群最小通用代币", callback_data="edit_cluster_min_common_tokens"),
        )
        keyboard.add(
            InlineKeyboardButton("📊 集群最小地址数", callback_data="edit_cluster_min_addresses"),
            InlineKeyboardButton("📊 集群最大地址数", callback_data="edit_cluster_max_addresses"),
        )
        keyboard.add(
            InlineKeyboardButton("📄 每页集群数", callback_data="edit_clusters_per_page"),
        )
        keyboard.add(InlineKeyboardButton("⬅️ 返回主菜单", callback_data="back_to_config"))
        
        self.bot.edit_message_text(
            response,
            call.message.chat.id,
            call.message.message_id,
            parse_mode="HTML",
            reply_markup=keyboard,
        )
        self.bot.answer_callback_query(call.id)

    def handle_jup_analysis_config(self, call: CallbackQuery) -> None:
        """处理Jupiter分析配置页面"""
        config = self.config.jupiter
        
        response = (
            "🪐 <b>Jupiter分析配置</b>\n\n"
            "Jupiter分析功能用于爬取Jupiter DEX热门代币数据并进行批量分析。\n\n"
            "📊 <b>当前配置</b>:\n"
            f"💰 最大市值: <code>${config.max_mcap:,}</code>\n"
            f"⏰ 最小代币年龄: <code>{config.min_token_age}</code> 秒\n"
            f"📱 需要社交信息: <code>{'✅ 是' if config.has_socials else '❌ 否'}</code>\n"
            f"📅 统计周期: <code>{config.period}</code>\n"
            f"🔢 默认分析数量: <code>{config.default_token_count}</code> 个\n"
            f"📊 最大分析数量: <code>{config.max_tokens_per_analysis}</code> 个\n\n"
            "💡 使用命令 /cajup <code>[数量]</code> 进行批量分析"
        )
        
        keyboard = InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            InlineKeyboardButton("💰 最大市值", callback_data="edit_jupiter_max_mcap"),
            InlineKeyboardButton("⏰ 最小年龄", callback_data="edit_jupiter_min_token_age"),
        )
        keyboard.add(
            InlineKeyboardButton("📅 统计周期", callback_data="edit_jupiter_period"),
            InlineKeyboardButton("🔢 默认数量", callback_data="edit_jupiter_default_token_count"),
        )
        keyboard.add(
            InlineKeyboardButton("📊 最大数量", callback_data="edit_jupiter_max_tokens_per_analysis"),
            InlineKeyboardButton(
                f"📱 社交信息 {'✅' if config.has_socials else '❌'}", 
                callback_data="toggle_jupiter_has_socials"
            ),
        )
        keyboard.add(InlineKeyboardButton("⬅️ 返回主菜单", callback_data="back_to_config"))
        
        self.bot.edit_message_text(
            response,
            call.message.chat.id,
            call.message.message_id,
            parse_mode="HTML",
            reply_markup=keyboard,
        )
        self.bot.answer_callback_query(call.id)

    def handle_edit_jupiter_period(self, call: CallbackQuery) -> None:
        """处理Jupiter周期编辑"""
        periods = ["24h", "7d", "30d"]
        current_period = self.config.jupiter.period
        
        response = f"📅 <b>选择统计周期</b>\n\n当前周期: <code>{current_period}</code>"
        
        keyboard = InlineKeyboardMarkup()
        for period in periods:
            text = f"{'✅ ' if period == current_period else ''}{period}"
            keyboard.add(InlineKeyboardButton(text, callback_data=f"set_jupiter_period_{period}"))
        keyboard.add(InlineKeyboardButton("⬅️ 返回Jupiter配置", callback_data="config_jup_analysis"))
        
        self.bot.edit_message_text(
            response,
            call.message.chat.id,
            call.message.message_id,
            parse_mode="HTML",
            reply_markup=keyboard,
        )
        self.bot.answer_callback_query(call.id)

    def handle_set_jupiter_period(self, call: CallbackQuery) -> None:
        """设置Jupiter周期"""
        period = call.data.replace("set_jupiter_period_", "")
        self.config.update_config("jupiter", period=period)
        
        # 返回Jupiter配置页面
        self.handle_jup_analysis_config(call)

    def handle_toggle_jupiter_has_socials(self, call: CallbackQuery) -> None:
        """切换Jupiter社交信息要求"""
        current_status = self.config.jupiter.has_socials
        self.config.update_config("jupiter", has_socials=not current_status)
        
        # 刷新页面
        self.handle_jup_analysis_config(call)

    def handle_capump_config(self, call: CallbackQuery) -> None:
        """处理Capump配置页面"""
        config = self.config.capump
        
        response = (
            "🚀 <b>Capump配置</b>\n\n"
            f"⏱️ 爬取间隔: <code>{config.interval}</code> 秒\n"
            f"📈 涨幅阈值: <code>{config.threshold * 100:.1f}%</code>\n"
            f"💰 最小市值: <code>${config.min_market_cap:,.0f}</code>\n"
            f"📅 代币年龄: <code>{config.min_age_days}</code> 天\n"
            f"🔔 自动分析: <code>{'✅ 已启用' if config.auto_analysis_enabled else '❌ 已禁用'}</code>\n"
            f"🔢 批次大小: <code>{config.max_tokens_per_batch}</code> 个代币\n"
        )
        
        keyboard = InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            InlineKeyboardButton("⏱️ 爬取间隔", callback_data="edit_capump_interval"),
            InlineKeyboardButton("📈 涨幅阈值", callback_data="edit_capump_threshold"),
        )
        keyboard.add(
            InlineKeyboardButton("💰 最小市值", callback_data="edit_capump_min_market_cap"),
            InlineKeyboardButton("📅 代币年龄", callback_data="edit_capump_min_age_days"),
        )
        keyboard.add(
            InlineKeyboardButton("🔢 批次大小", callback_data="edit_capump_max_tokens_per_batch"),
            InlineKeyboardButton(
                f"🔔 自动分析 {'✅' if config.auto_analysis_enabled else '❌'}", 
                callback_data="toggle_capump_auto_analysis"
            ),
        )
        keyboard.add(InlineKeyboardButton("⬅️ 返回主菜单", callback_data="back_to_config"))
        
        self.bot.edit_message_text(
            response,
            call.message.chat.id,
            call.message.message_id,
            parse_mode="HTML",
            reply_markup=keyboard,
        )
        self.bot.answer_callback_query(call.id)

    def handle_edit_capump_config(self, call: CallbackQuery) -> None:
        """处理Capump配置项编辑"""
        key = call.data.replace("edit_capump_", "")
        
        config_map = {
            "interval": "爬取间隔（秒）",
            "threshold": "涨幅阈值（例如0.10表示10%）",
            "min_market_cap": "最小市值（美元）",
            "min_age_days": "代币年龄（天）",
            "max_tokens_per_batch": "批次大小（个代币）",
        }
        
        if key in config_map:
            description = config_map[key]
            msg = self.bot.send_message(
                call.message.chat.id, 
                f"请输入新的 <b>{description}</b>：", 
                parse_mode="HTML"
            )
            self.bot.register_next_step_handler(
                msg, lambda m: self._save_capump_config_value(m, key)
            )
        
        self.bot.answer_callback_query(call.id)

    def handle_toggle_capump_auto_analysis(self, call: CallbackQuery) -> None:
        """切换Capump自动分析状态"""
        current_status = self.config.capump.auto_analysis_enabled
        self.config.update_config("capump", auto_analysis_enabled=not current_status)
        
        # 刷新页面
        self.handle_capump_config(call)

    def _save_capump_config_value(self, message: Message, key: str) -> None:
        """保存Capump配置值"""
        try:
            value = message.text.strip()
            
            # 类型转换
            if key in ["interval", "min_age_days", "max_tokens_per_batch"]:
                value = int(value)
            elif key in ["threshold", "min_market_cap"]:
                value = float(value)
            
            # 更新配置
            self.config.update_config("capump", **{key: value})
            
            success_msg = self.formatter.format_success_message(f"Capump配置已更新: {key} = {value}")
            self.bot.reply_to(message, success_msg, parse_mode="HTML")
            
        except ValueError:
            error_msg = self.formatter.format_error_message("❌ 输入格式错误，请输入有效的数值")
            self.bot.reply_to(message, error_msg, parse_mode="HTML")
        except Exception as e:
            error_msg = self.formatter.format_error_message(f"❌ 保存配置失败: {str(e)}")
            self.bot.reply_to(message, error_msg, parse_mode="HTML")

    def handle_storage_management(self, call: CallbackQuery) -> None:
        """处理存储管理页面"""
        try:
            from ..utils.data_manager import get_storage_status
            info = get_storage_status()
            
            response = "💾 <b>存储管理</b>\n\n"
            response += f"📊 <b>存储统计</b>\n"
            response += f"总文件数: <code>{info['total_files']}</code>\n"
            response += f"总大小: <code>{info['total_size_mb']} MB</code>\n\n"
            
            response += "📁 <b>分类详情</b>\n"
            for file_type, details in info["by_type"].items():
                if details['count'] > 0:
                    response += f"• {details['description']}: "
                    response += f"<code>{details['count']}/{details['max_files']}</code> 个文件, "
                    response += f"<code>{details['size_mb']} MB</code>\n"
            
            keyboard = InlineKeyboardMarkup(row_width=2)
            keyboard.add(
                InlineKeyboardButton("🗑️ 立即清理", callback_data="cleanup_storage"),
                InlineKeyboardButton("📊 刷新状态", callback_data="storage_management"),
            )
            keyboard.add(InlineKeyboardButton("⬅️ 返回主菜单", callback_data="back_to_config"))
            
            self.bot.edit_message_text(
                response,
                call.message.chat.id,
                call.message.message_id,
                parse_mode="HTML",
                reply_markup=keyboard,
            )
        except ImportError:
            response = "❌ 存储管理功能不可用\n\n存储管理模块未正确加载"
            keyboard = InlineKeyboardMarkup()
            keyboard.add(InlineKeyboardButton("⬅️ 返回主菜单", callback_data="back_to_config"))
            
            self.bot.edit_message_text(
                response,
                call.message.chat.id,
                call.message.message_id,
                parse_mode="HTML",
                reply_markup=keyboard,
            )
        except Exception as e:
            response = f"❌ 获取存储信息失败: {str(e)}"
            keyboard = InlineKeyboardMarkup()
            keyboard.add(InlineKeyboardButton("⬅️ 返回主菜单", callback_data="back_to_config"))
            
            self.bot.edit_message_text(
                response,
                call.message.chat.id,
                call.message.message_id,
                parse_mode="HTML",
                reply_markup=keyboard,
            )
        
        self.bot.answer_callback_query(call.id)

    def handle_cleanup_storage(self, call: CallbackQuery) -> None:
        """处理存储清理"""
        try:
            from ..utils.data_manager import cleanup_storage, get_storage_status
            
            # 获取清理前状态
            before_info = get_storage_status()
            
            # 执行清理
            cleanup_storage()
            
            # 获取清理后状态
            after_info = get_storage_status()
            
            # 计算清理效果
            files_removed = before_info['total_files'] - after_info['total_files']
            space_freed = before_info['total_size_mb'] - after_info['total_size_mb']
            
            response = "🗑️ <b>存储清理完成</b>\n\n"
            response += f"删除文件数: <code>{files_removed}</code>\n"
            response += f"释放空间: <code>{space_freed:.2f} MB</code>\n\n"
            response += f"当前状态:\n"
            response += f"• 总文件数: <code>{after_info['total_files']}</code>\n"
            response += f"• 总大小: <code>{after_info['total_size_mb']} MB</code>\n"
            
            keyboard = InlineKeyboardMarkup(row_width=2)
            keyboard.add(
                InlineKeyboardButton("📊 查看详情", callback_data="storage_management"),
                InlineKeyboardButton("⬅️ 返回主菜单", callback_data="back_to_config"),
            )
            
            self.bot.edit_message_text(
                response,
                call.message.chat.id,
                call.message.message_id,
                parse_mode="HTML",
                reply_markup=keyboard,
            )
            
        except Exception as e:
            response = f"❌ 存储清理失败: {str(e)}"
            keyboard = InlineKeyboardMarkup()
            keyboard.add(InlineKeyboardButton("⬅️ 返回主菜单", callback_data="back_to_config"))
            
            self.bot.edit_message_text(
                response,
                call.message.chat.id,
                call.message.message_id,
                parse_mode="HTML",
                reply_markup=keyboard,
            )
            
        self.bot.answer_callback_query(call.id)

    def handle_back_to_config(self, call: CallbackQuery) -> None:
        """返回配置菜单"""
        config_msg = self.formatter.format_config_message(self.config)
        keyboard = self._create_config_keyboard()

        self.bot.edit_message_text(
            config_msg,
            call.message.chat.id,
            call.message.message_id,
            parse_mode="HTML",
            reply_markup=keyboard,
        )
        self.bot.answer_callback_query(call.id)

    def register_handlers(self) -> None:
        """注册处理器"""

        @self.bot.message_handler(commands=["config"])
        def config_handler(message):
            self.handle_config(message)

        @self.bot.callback_query_handler(func=lambda call: call.data.startswith("edit_"))
        def edit_config_handler(call):
            self.handle_edit_config(call)

        @self.bot.callback_query_handler(func=lambda call: call.data == "blacklist_menu")
        def blacklist_menu_handler(call):
            self.handle_blacklist_menu(call)

        @self.bot.callback_query_handler(func=lambda call: call.data == "add_blacklist")
        def add_blacklist_handler(call):
            self.handle_add_blacklist(call)

        @self.bot.callback_query_handler(func=lambda call: call.data == "remove_blacklist")
        def remove_blacklist_handler(call):
            self.handle_remove_blacklist(call)

        @self.bot.callback_query_handler(func=lambda call: call.data == "view_blacklist")
        def view_blacklist_handler(call):
            self.handle_view_blacklist(call)

        @self.bot.callback_query_handler(func=lambda call: call.data == "back_to_config")
        def back_to_config_handler(call):
            self.handle_back_to_config(call)

        @self.bot.callback_query_handler(func=lambda call: call.data == "config_auto_alert")
        def auto_alert_config_handler(call):
            self.handle_auto_alert_config(call)

        @self.bot.callback_query_handler(func=lambda call: call.data == "config_pump_alert")
        def pump_alert_config_handler(call):
            self.handle_pump_alert_config(call)

        @self.bot.callback_query_handler(func=lambda call: call.data == "config_auto_pump_analysis")
        def auto_pump_analysis_config_handler(call):
            self.handle_auto_pump_analysis_config(call)

        @self.bot.callback_query_handler(func=lambda call: call.data == "config_holder_analysis")
        def holder_analysis_config_handler(call):
            self.handle_holder_analysis_config(call)

        @self.bot.callback_query_handler(func=lambda call: call.data == "config_jup_analysis")
        def jup_analysis_config_handler(call):
            self.handle_jup_analysis_config(call)

        @self.bot.callback_query_handler(func=lambda call: call.data == "edit_jupiter_period")
        def edit_jupiter_period_handler(call):
            self.handle_edit_jupiter_period(call)

        @self.bot.callback_query_handler(func=lambda call: call.data.startswith("set_jupiter_period_"))
        def set_jupiter_period_handler(call):
            self.handle_set_jupiter_period(call)

        @self.bot.callback_query_handler(func=lambda call: call.data == "toggle_jupiter_has_socials")
        def toggle_jupiter_has_socials_handler(call):
            self.handle_toggle_jupiter_has_socials(call)

        @self.bot.callback_query_handler(func=lambda call: call.data == "config_capump")
        def capump_config_handler(call):
            self.handle_capump_config(call)

        @self.bot.callback_query_handler(func=lambda call: call.data.startswith("edit_capump_"))
        def edit_capump_config_handler(call):
            self.handle_edit_capump_config(call)

        @self.bot.callback_query_handler(func=lambda call: call.data == "toggle_capump_auto_analysis")
        def toggle_capump_auto_analysis_handler(call):
            self.handle_toggle_capump_auto_analysis(call)

        @self.bot.callback_query_handler(func=lambda call: call.data == "storage_management")
        def storage_management_handler(call):
            self.handle_storage_management(call)

        @self.bot.callback_query_handler(func=lambda call: call.data == "cleanup_storage")
        def cleanup_storage_handler(call):
            self.handle_cleanup_storage(call)
