"""
基础命令处理器
处理基本的bot命令如 /start, /help
"""

from telebot import TeleBot
from telebot.types import Message
from ..services.formatter import MessageFormatter
from ..core.config import get_config


class BaseCommandHandler:
    """基础命令处理器"""

    def __init__(self, bot: TeleBot):
        self.bot = bot
        self.formatter = MessageFormatter()
        self.config = get_config()

    def reply_with_topic(self, message: Message, text: str, **kwargs):
        """统一的回复方法，回复到用户消息所在的topic"""
        # 获取用户消息所在的topic ID
        user_topic_id = getattr(message, "message_thread_id", None)
        
        if user_topic_id:
            # 如果用户在某个topic中发送消息，回复到同一个topic
            kwargs['message_thread_id'] = user_topic_id
            return self.bot.send_message(
                chat_id=message.chat.id,
                text=text,
                **kwargs
            )
        else:
            # 如果不在topic中，使用普通回复
            return self.bot.reply_to(message, text, **kwargs)

    def send_to_topic(self, chat_id: str, text: str, thread_id=None, **kwargs):
        """统一的发送方法，确保消息发送到正确的topic"""
        if thread_id:
            kwargs['message_thread_id'] = thread_id
        elif self.config.bot.message_thread_id:
            kwargs['message_thread_id'] = self.config.bot.message_thread_id
        return self.bot.send_message(
            chat_id=chat_id,
            text=text,
            **kwargs
        )

    def handle_start(self, message: Message) -> None:
        """处理 /start 命令"""
        welcome_msg = self.formatter.format_welcome_message()
        self.reply_with_topic(message, welcome_msg, parse_mode="HTML")

    def handle_help(self, message: Message) -> None:
        """处理 /help 命令"""
        help_msg = self.formatter.format_welcome_message()
        self.reply_with_topic(message, help_msg, parse_mode="HTML")

    def handle_topicid(self, message: Message) -> None:
        """处理 /topicid 命令"""
        topic_id = getattr(message, "message_thread_id", None)
        if topic_id:
            response = f"当前Topic ID: <code>{topic_id}</code>"
        else:
            response = "此消息没有Topic ID（可能不在群组中或群组未开启Topics）"

        self.reply_with_topic(message, response, parse_mode="HTML")

    def register_handlers(self) -> None:
        """注册处理器"""

        @self.bot.message_handler(commands=["start"])
        def start_handler(message):
            self.handle_start(message)

        @self.bot.message_handler(commands=["help"])
        def help_handler(message):
            self.handle_help(message)

        @self.bot.message_handler(commands=["topicid"])
        def topicid_handler(message):
            self.handle_topicid(message)
