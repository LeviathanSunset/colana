"""
基础命令处理器
处理基本的bot命令如 /start, /help
"""
from telebot import TeleBot
from telebot.types import Message
from ..services.formatter import MessageFormatter


class BaseCommandHandler:
    """基础命令处理器"""
    
    def __init__(self, bot: TeleBot):
        self.bot = bot
        self.formatter = MessageFormatter()
    
    def handle_start(self, message: Message) -> None:
        """处理 /start 命令"""
        welcome_msg = self.formatter.format_welcome_message()
        self.bot.reply_to(message, welcome_msg, parse_mode='HTML')
    
    def handle_help(self, message: Message) -> None:
        """处理 /help 命令"""
        welcome_msg = self.formatter.format_welcome_message()
        self.bot.reply_to(message, welcome_msg, parse_mode='HTML')
    
    def handle_topicid(self, message: Message) -> None:
        """处理 /topicid 命令"""
        topic_id = getattr(message, 'message_thread_id', None)
        if topic_id:
            response = f"当前Topic ID: <code>{topic_id}</code>"
        else:
            response = "此消息没有Topic ID（可能不在群组中或群组未开启Topics）"
        
        self.bot.reply_to(message, response, parse_mode='HTML')
    
    def register_handlers(self) -> None:
        """注册处理器"""
        @self.bot.message_handler(commands=['start'])
        def start_handler(message):
            self.handle_start(message)
        
        @self.bot.message_handler(commands=['help'])
        def help_handler(message):
            self.handle_help(message)
        
        @self.bot.message_handler(commands=['topicid'])
        def topicid_handler(message):
            self.handle_topicid(message)
