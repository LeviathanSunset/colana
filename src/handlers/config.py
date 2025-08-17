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

        # 主要功能设置 - 两个并列按钮
        keyboard.add(
            InlineKeyboardButton("🔍 自动警报配置", callback_data="config_auto_alert"),
            InlineKeyboardButton("🚀 Capump配置", callback_data="config_capump"),
        )

        # 监控设置
        keyboard.add(
            InlineKeyboardButton("⏱️ 检查间隔", callback_data="edit_interval"),
            InlineKeyboardButton("📈 涨幅阈值", callback_data="edit_threshold"),
        )
        keyboard.add(
            InlineKeyboardButton("💰 最小市值", callback_data="edit_min_market_cap"),
            InlineKeyboardButton("📅 最小年龄", callback_data="edit_min_age_days"),
        )

        # 分析设置
        keyboard.add(
            InlineKeyboardButton("👥 大户数量", callback_data="edit_top_holders_count"),
            InlineKeyboardButton("📊 排行榜大小", callback_data="edit_ranking_size"),
        )

        # 黑名单管理
        keyboard.add(InlineKeyboardButton("🚫 黑名单管理", callback_data="blacklist_menu"))

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
        }

        if key in config_map:
            section, description = config_map[key]
            msg = self.bot.send_message(
                call.message.chat.id, f"请输入新的 <b>{description}</b>：", parse_mode="HTML"
            )
            self.bot.register_next_step_handler(
                msg, lambda m: self._save_config_value(m, section, key)
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

        @self.bot.callback_query_handler(func=lambda call: call.data == "config_capump")
        def capump_config_handler(call):
            self.handle_capump_config(call)

        @self.bot.callback_query_handler(func=lambda call: call.data.startswith("edit_capump_"))
        def edit_capump_config_handler(call):
            self.handle_edit_capump_config(call)

        @self.bot.callback_query_handler(func=lambda call: call.data == "toggle_capump_auto_analysis")
        def toggle_capump_auto_analysis_handler(call):
            self.handle_toggle_capump_auto_analysis(call)
