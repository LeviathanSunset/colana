"""
Jupiter热门代币监控处理器
监控Jupiter平台的热门代币变化，每30秒检查一次
"""

import threading
import time
import json
import os
from collections import defaultdict
from typing import Dict, Set, List, Optional
from datetime import datetime, timedelta
from telebot import TeleBot
from telebot.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from ..core.config import get_config
from ..services.jupiter_crawler import JupiterCrawler
from ..services.formatter import MessageFormatter
from ..handlers.base import BaseCommandHandler
from ..utils.data_manager import DataManager
from ..utils.logger import get_logger


class JupiterMonitorHandler(BaseCommandHandler):
    """Jupiter热门代币监控处理器"""

    def __init__(self, bot: TeleBot):
        super().__init__(bot)
        self.config = get_config()
        self.formatter = MessageFormatter()
        self.data_manager = DataManager()
        self.logger = get_logger("jupiter_monitor")
        self.jupiter_crawler = JupiterCrawler()
        
        # 状态管理
        self.status_file = self.data_manager.get_file_path("config", "jupiter_monitor_status.json")
        self.monitor_status: Dict[str, bool] = {}  # chat_id -> enabled
        self.monitor_threads: Dict[str, threading.Thread] = {}  # chat_id -> thread
        self.stop_flags: Dict[str, threading.Event] = {}  # chat_id -> stop_event
        self.previous_tokens: Dict[str, Set[str]] = {}  # chat_id -> set of token addresses
        self.token_first_seen: Dict[str, Dict[str, float]] = {}  # chat_id -> token_address -> timestamp
        
        # 监控参数（与请求URL参数匹配）
        self.monitor_params = {
            'period': '5m',  # 修正为正确的API参数
            'min_net_volume_5m': 1000,  # 5分钟参数名
            'max_mcap': 30000,
            'has_socials': True,
            'min_token_age': 10000  # 10000秒
        }
        
        self.logger.info("🔧 JupiterMonitorHandler 初始化开始")
        
        # 加载保存的状态
        self.load_status()
        
        # 为已启用的群组启动监控线程
        self.restore_monitor_threads()
        
        self.logger.info("✅ JupiterMonitorHandler 初始化完成")

    def register_handlers(self):
        """注册命令处理器"""
        self.logger.info("📝 注册Jupiter监控命令处理器...")
        
        @self.bot.message_handler(commands=['jupiter_monitor', 'jmonitor'])
        def handle_jupiter_monitor_command(message):
            self.handle_jupiter_monitor(message)
        
        self.logger.info("✅ Jupiter监控命令处理器注册成功")

    def reply_with_topic(self, message: Message, text: str, **kwargs):
        """统一的回复方法，回复到用户消息所在的topic"""
        user_topic_id = getattr(message, "message_thread_id", None)
        
        if user_topic_id:
            kwargs['message_thread_id'] = user_topic_id
            return self.bot.send_message(
                chat_id=message.chat.id,
                text=text,
                **kwargs
            )
        else:
            return self.bot.reply_to(message, text, **kwargs)

    def send_to_topic(self, chat_id: str, text: str, topic_id: Optional[int] = None, **kwargs):
        """发送消息到指定topic"""
        try:
            if topic_id:
                kwargs['message_thread_id'] = topic_id
            
            return self.bot.send_message(
                chat_id=int(chat_id),
                text=text,
                **kwargs
            )
        except Exception as e:
            self.logger.error(f"❌ 发送消息失败 chat_id={chat_id}, topic_id={topic_id}: {e}")
            return None

    def load_status(self):
        """加载监控状态"""
        try:
            if os.path.exists(self.status_file):
                with open(self.status_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.monitor_status = data.get('monitor_status', {})
                    # 重置之前的代币列表（重启后重新开始）
                    self.previous_tokens = {chat_id: set() for chat_id in self.monitor_status.keys()}
                    self.token_first_seen = {chat_id: {} for chat_id in self.monitor_status.keys()}
                    self.logger.info(f"📋 Jupiter监控状态加载成功: {len(self.monitor_status)} 个群组")
            else:
                self.logger.info("📋 Jupiter监控状态文件不存在，使用默认设置")
                self.monitor_status = {}
                self.previous_tokens = {}
                self.token_first_seen = {}
        except Exception as e:
            self.logger.exception(f"❌ 加载Jupiter监控状态失败: {e}")
            self.monitor_status = {}
            self.previous_tokens = {}
            self.token_first_seen = {}

    def save_status(self):
        """保存监控状态"""
        try:
            os.makedirs(os.path.dirname(self.status_file), exist_ok=True)
            
            data = {
                'monitor_status': self.monitor_status,
                'last_updated': time.time()
            }
            
            with open(self.status_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"❌ 保存Jupiter监控状态失败: {e}")

    def restore_monitor_threads(self):
        """恢复已启用群组的监控线程"""
        for chat_id, enabled in self.monitor_status.items():
            if enabled:
                self.logger.info(f"🔄 恢复群组 {chat_id} 的Jupiter监控")
                self.start_monitor_for_group(chat_id)

    def handle_jupiter_monitor(self, message: Message) -> None:
        """处理 /jupiter_monitor 或 /jmonitor 命令"""
        chat_id = str(message.chat.id)
        
        # 检查群组权限（使用与pump监控相同的权限配置）
        allowed_groups = self.config.ca1_allowed_groups
        if allowed_groups and chat_id not in allowed_groups:
            self.reply_with_topic(
                message, 
                "❌ 此功能仅在特定群组中可用\n如需使用，请联系管理员"
            )
            return

        # 解析命令参数
        parts = message.text.split()
        if len(parts) < 2:
            # 显示当前状态
            current_status = self.monitor_status.get(chat_id, False)
            status_text = "🟢 已启用" if current_status else "🔴 已禁用"
            
            self.reply_with_topic(
                message,
                f"🪙 **Jupiter热门代币监控状态**\n\n"
                f"当前状态: {status_text}\n\n"
                f"💡 **使用方法:**\n"
                f"• `/jmonitor on` - 启用监控\n"
                f"• `/jmonitor off` - 禁用监控\n"
                f"• `/jmonitor status` - 查看状态\n\n"
                f"📊 **监控参数:**\n"
                f"• 检查间隔: 30秒\n"
                f"• 时间周期: {self.monitor_params['period']}\n"
                f"• 最大市值: ${self.monitor_params['max_mcap']:,}\n"
                f"• 最小5min交易量: ${self.monitor_params['min_net_volume_5m']:,}\n"
                f"• 最小代币年龄: {self.monitor_params['min_token_age']}秒\n"
                f"• 需要社交媒体: {'是' if self.monitor_params['has_socials'] else '否'}",
                parse_mode='Markdown'
            )
            return

        command = parts[1].lower()
        
        if command == "on":
            self.enable_monitor(message, chat_id)
        elif command == "off":
            self.disable_monitor(message, chat_id)
        elif command == "status":
            self.show_monitor_status(message, chat_id)
        else:
            self.reply_with_topic(
                message,
                "❌ 未知命令\n\n"
                "💡 **可用命令:**\n"
                "• `/jmonitor on` - 启用监控\n"
                "• `/jmonitor off` - 禁用监控\n"
                "• `/jmonitor status` - 查看状态"
            )

    def enable_monitor(self, message: Message, chat_id: str):
        """启用Jupiter监控"""
        if self.monitor_status.get(chat_id, False):
            self.reply_with_topic(message, "⚠️ Jupiter监控已经在运行中")
            return

        try:
            # 启用监控
            self.monitor_status[chat_id] = True
            self.save_status()
            
            # 启动监控线程
            self.start_monitor_for_group(chat_id)
            
            self.reply_with_topic(
                message,
                "✅ **Jupiter热门代币监控已启用**\n\n"
                "🔍 正在监控Jupiter平台热门代币变化...\n"
                "⏰ 检查间隔: 30秒\n"
                "📊 将通知新增和消失的代币\n\n"
                "使用 `/jmonitor off` 可停止监控"
            )
            
            self.logger.info(f"✅ 群组 {chat_id} 启用Jupiter监控")
            
        except Exception as e:
            self.logger.exception(f"❌ 启用Jupiter监控失败 {chat_id}: {e}")
            self.reply_with_topic(message, f"❌ 启用监控失败: {str(e)}")

    def disable_monitor(self, message: Message, chat_id: str):
        """禁用Jupiter监控"""
        if not self.monitor_status.get(chat_id, False):
            self.reply_with_topic(message, "⚠️ Jupiter监控未运行")
            return

        try:
            # 停止监控线程
            self.stop_monitor_for_group(chat_id)
            
            # 禁用监控
            self.monitor_status[chat_id] = False
            self.save_status()
            
            self.reply_with_topic(
                message,
                "🛑 **Jupiter热门代币监控已停止**\n\n"
                "使用 `/jmonitor on` 可重新启用监控"
            )
            
            self.logger.info(f"🛑 群组 {chat_id} 禁用Jupiter监控")
            
        except Exception as e:
            self.logger.exception(f"❌ 禁用Jupiter监控失败 {chat_id}: {e}")
            self.reply_with_topic(message, f"❌ 禁用监控失败: {str(e)}")

    def show_monitor_status(self, message: Message, chat_id: str):
        """显示监控状态"""
        current_status = self.monitor_status.get(chat_id, False)
        status_text = "🟢 运行中" if current_status else "🔴 已停止"
        
        # 获取统计信息
        thread_alive = chat_id in self.monitor_threads and self.monitor_threads[chat_id].is_alive()
        thread_status = "🟢 活跃" if thread_alive else "🔴 不活跃"
        
        previous_count = len(self.previous_tokens.get(chat_id, set()))
        
        self.reply_with_topic(
            message,
            f"📊 **Jupiter监控状态报告**\n\n"
            f"监控状态: {status_text}\n"
            f"线程状态: {thread_status}\n"
            f"上次检测代币数: {previous_count}\n"
            f"检查间隔: 30秒\n\n"
            f"**监控参数:**\n"
            f"• 时间周期: {self.monitor_params['period']}\n"
            f"• 最大市值: ${self.monitor_params['max_mcap']:,}\n"
            f"• 最小5min交易量: ${self.monitor_params['min_net_volume_5m']:,}\n"
            f"• 最小代币年龄: {self.monitor_params['min_token_age']}秒",
            parse_mode='Markdown'
        )

    def start_monitor_for_group(self, chat_id: str):
        """为指定群组启动监控线程"""
        # 如果已经有线程在运行，先停止
        if chat_id in self.monitor_threads and self.monitor_threads[chat_id].is_alive():
            self.stop_monitor_for_group(chat_id)

        # 创建停止标志
        stop_flag = threading.Event()
        self.stop_flags[chat_id] = stop_flag
        
        # 初始化数据结构
        if chat_id not in self.previous_tokens:
            self.previous_tokens[chat_id] = set()
        if chat_id not in self.token_first_seen:
            self.token_first_seen[chat_id] = {}

        # 创建并启动监控线程
        thread = threading.Thread(
            target=self._monitor_loop,
            args=(chat_id, stop_flag),
            daemon=True,
            name=f"JupiterMonitor-{chat_id}"
        )
        
        self.monitor_threads[chat_id] = thread
        thread.start()
        
        self.logger.info(f"🚀 群组 {chat_id} 的Jupiter监控线程已启动")

    def stop_monitor_for_group(self, chat_id: str):
        """停止指定群组的监控线程"""
        # 设置停止标志
        if chat_id in self.stop_flags:
            self.stop_flags[chat_id].set()

        # 等待线程结束
        if chat_id in self.monitor_threads:
            thread = self.monitor_threads[chat_id]
            if thread.is_alive():
                self.logger.info(f"⏳ 等待群组 {chat_id} 的Jupiter监控线程结束...")
                thread.join(timeout=5)  # 最多等待5秒
                if thread.is_alive():
                    self.logger.warning(f"⚠️ 群组 {chat_id} 的Jupiter监控线程未能及时结束")
                else:
                    self.logger.info(f"✅ 群组 {chat_id} 的Jupiter监控线程已结束")
            
            # 清理线程引用
            del self.monitor_threads[chat_id]

        # 清理停止标志
        if chat_id in self.stop_flags:
            del self.stop_flags[chat_id]

    def _monitor_loop(self, chat_id: str, stop_flag: threading.Event):
        """监控循环主逻辑"""
        self.logger.info(f"🔄 群组 {chat_id} 的Jupiter监控循环开始")
        
        error_count = 0
        max_errors = 5  # 最大连续错误次数
        
        while not stop_flag.is_set():
            try:
                # 获取当前热门代币
                current_tokens = self._fetch_current_tokens()
                
                if current_tokens is not None:
                    # 处理代币变化
                    self._process_token_changes(chat_id, current_tokens)
                    error_count = 0  # 重置错误计数
                else:
                    error_count += 1
                    self.logger.warning(f"⚠️ 群组 {chat_id} 获取代币数据失败，错误次数: {error_count}")
                    
                    if error_count >= max_errors:
                        self.logger.error(f"❌ 群组 {chat_id} 连续错误次数过多，停止监控")
                        self._send_error_notification(chat_id, "连续获取数据失败，监控已停止")
                        break
                
                # 等待30秒或直到收到停止信号
                if stop_flag.wait(timeout=30):
                    break
                    
            except Exception as e:
                error_count += 1
                self.logger.exception(f"❌ 群组 {chat_id} 监控循环异常: {e}")
                
                if error_count >= max_errors:
                    self.logger.error(f"❌ 群组 {chat_id} 连续异常次数过多，停止监控")
                    self._send_error_notification(chat_id, f"监控异常，已停止: {str(e)}")
                    break
                
                # 异常后等待更长时间
                if stop_flag.wait(timeout=60):
                    break
        
        self.logger.info(f"🛑 群组 {chat_id} 的Jupiter监控循环结束")

    def _fetch_current_tokens(self) -> Optional[Set[str]]:
        """获取当前热门代币地址列表"""
        try:
            # 使用与API请求相同的参数
            tokens_data = self.jupiter_crawler.fetch_top_traded_tokens(
                period=self.monitor_params['period'],
                min_net_volume_5m=self.monitor_params['min_net_volume_5m']
            )
            
            if not tokens_data:
                return None
            
            # 根据参数过滤代币
            filtered_tokens = []
            for token_data in tokens_data:
                base_asset = token_data.get('baseAsset', {})
                
                # 检查市值
                mcap = base_asset.get('mcap') or base_asset.get('fdv', 0)
                if mcap > self.monitor_params['max_mcap']:
                    continue
                
                # 检查24h交易量
                volume_24h = token_data.get('volume24h', 0)
                if volume_24h < self.monitor_params['min_net_volume_24h']:
                    continue
                
                # 检查是否有社交媒体信息
                if self.monitor_params['has_socials']:
                    twitter = base_asset.get('twitter', '')
                    website = base_asset.get('website', '')
                    if not twitter and not website:
                        continue
                
                # 检查代币年龄
                created_at = token_data.get('createdAt', '')
                if created_at:
                    try:
                        # 假设created_at是时间戳或ISO格式
                        if isinstance(created_at, (int, float)):
                            token_age = time.time() - created_at
                        else:
                            # 尝试解析ISO格式时间
                            created_time = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                            token_age = (datetime.now() - created_time).total_seconds()
                        
                        if token_age < self.monitor_params['min_token_age']:
                            continue
                    except:
                        # 如果无法解析时间，跳过年龄检查
                        pass
                
                filtered_tokens.append(token_data)
            
            # 提取代币地址
            token_addresses = set()
            for token_data in filtered_tokens:
                base_asset = token_data.get('baseAsset', {})
                mint_address = base_asset.get('id', '')
                if mint_address:
                    token_addresses.add(mint_address)
            
            self.logger.debug(f"🔍 获取到 {len(token_addresses)} 个符合条件的热门代币")
            return token_addresses
            
        except Exception as e:
            self.logger.exception(f"❌ 获取热门代币失败: {e}")
            return None

    def _process_token_changes(self, chat_id: str, current_tokens: Set[str]):
        """处理代币变化"""
        try:
            previous_tokens = self.previous_tokens.get(chat_id, set())
            current_time = time.time()
            
            # 找出新增的代币
            new_tokens = current_tokens - previous_tokens
            
            # 找出消失的代币
            removed_tokens = previous_tokens - current_tokens
            
            # 更新记录
            self.previous_tokens[chat_id] = current_tokens.copy()
            
            # 记录新代币的首次出现时间
            for token in new_tokens:
                self.token_first_seen[chat_id][token] = current_time
            
            # 清理消失代币的记录
            for token in removed_tokens:
                self.token_first_seen[chat_id].pop(token, None)
            
            # 发送通知
            if new_tokens:
                self._send_new_tokens_notification(chat_id, new_tokens)
            
            if removed_tokens:
                self._send_removed_tokens_notification(chat_id, removed_tokens)
            
            # 记录日志
            if new_tokens or removed_tokens:
                self.logger.info(
                    f"📊 群组 {chat_id} 代币变化: "
                    f"新增 {len(new_tokens)}，消失 {len(removed_tokens)}，"
                    f"当前总数 {len(current_tokens)}"
                )
            
        except Exception as e:
            self.logger.exception(f"❌ 处理代币变化失败: {e}")

    def _send_new_tokens_notification(self, chat_id: str, new_tokens: Set[str]):
        """发送新增代币通知"""
        try:
            if not new_tokens:
                return
            
            # 为了获取代币详细信息，我们需要重新调用API
            # 这里先用简化版本，只显示地址
            tokens_info = []
            for token_address in new_tokens:
                tokens_info.append({
                    'address': token_address,
                    'symbol': 'Unknown',
                    'name': 'Unknown'
                })
            
            # 构建消息
            message_lines = ["🆕 **Jupiter新增热门代币**\n"]
            
            for i, token in enumerate(tokens_info, 1):
                address = token['address']
                
                message_lines.append(
                    f"`{i}.` 📍 `{address}`\n"
                    f"   � [Jupiter](https://jup.ag/swap/SOL-{address})\n"
                    f"   � [DexScreener](https://dexscreener.com/solana/{address})\n"
                )
            
            message = "\n".join(message_lines)
            
            # 发送到与pump监控相同的topic（如果配置了的话）
            self.send_to_topic(
                chat_id,
                message,
                parse_mode='Markdown',
                disable_web_page_preview=True
            )
            
        except Exception as e:
            self.logger.exception(f"❌ 发送新增代币通知失败: {e}")

    def _send_removed_tokens_notification(self, chat_id: str, removed_tokens: Set[str]):
        """发送消失代币通知"""
        try:
            if not removed_tokens:
                return
            
            # 构建消息
            message_lines = ["📉 **Jupiter消失热门代币**\n"]
            
            for i, token_address in enumerate(removed_tokens, 1):
                message_lines.append(
                    f"`{i}.` 📍 `{token_address}`\n"
                )
            
            message = "\n".join(message_lines)
            
            # 发送到与pump监控相同的topic
            self.send_to_topic(
                chat_id,
                message,
                parse_mode='Markdown',
                disable_web_page_preview=True
            )
            
        except Exception as e:
            self.logger.exception(f"❌ 发送消失代币通知失败: {e}")

    def _send_error_notification(self, chat_id: str, error_message: str):
        """发送错误通知"""
        try:
            message = f"⚠️ **Jupiter监控异常**\n\n{error_message}\n\n使用 `/jmonitor on` 重新启动监控"
            
            self.send_to_topic(
                chat_id,
                message,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            self.logger.exception(f"❌ 发送错误通知失败: {e}")

    def cleanup(self):
        """清理资源"""
        self.logger.info("🧹 正在清理Jupiter监控资源...")
        
        # 停止所有监控线程
        for chat_id in list(self.monitor_threads.keys()):
            self.stop_monitor_for_group(chat_id)
        
        # 保存状态
        self.save_status()
        
        self.logger.info("✅ Jupiter监控资源清理完成")
