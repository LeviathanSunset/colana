#!/usr/bin/env python3
"""
简化版代币分析Bot - 仅保留 /ca 功能
"""
import os
import sys

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import telebot
from src.core.config import get_config, setup_proxy
from src.handlers.holding_analysis import HoldingAnalysisHandler


class SimpleTokenBot:
    """简化版代币分析机器人 - 仅支持 /ca 命令"""
    
    def __init__(self):
        """初始化机器人"""
        print("🚀 初始化简化版代币分析机器人...")
        
        try:
            self.config = get_config()
            setup_proxy()
            
            # 初始化机器人
            self.bot = telebot.TeleBot(self.config.bot.telegram_token)
            print("✅ Telegram Bot 初始化成功")
            
            # 初始化 ca 处理器
            self.holding_handler = HoldingAnalysisHandler(self.bot)
            print("✅ CA 处理器初始化成功")
            print("✅ CA 处理器初始化成功")
            
        except Exception as e:
            print(f"❌ Bot初始化失败: {e}")
            raise
        
        # 注册处理器
        self._register_handlers()
    
    def _register_handlers(self):
        """注册处理器"""
        print("📝 注册消息处理器...")
        try:
            # 只注册 ca 处理器
            self.holding_handler.register_handlers()
            
            # 添加基本的 start 和 help 命令
            @self.bot.message_handler(commands=['start'])
            def start_handler(message):
                welcome_msg = (
                    "🤖 <b>代币分析Bot</b>\n\n"
                    "📋 <b>可用命令:</b>\n"
                    "• <code>/ca &lt;代币地址&gt;</code> - 分析代币大户持仓\n"
                    "• <code>/caw [代币地址\\n钱包地址...]</code> - 分析指定钱包组\n"
                    "• <code>/help</code> - 显示帮助信息\n\n"
                    "💡 <b>使用示例:</b>\n"
                    "<code>/ca FbGsCHv8qPvUdmomVAiG72ET5D5kgBJgGoxxfMZipump</code>"
                )
                self._reply_to_user(message, welcome_msg, parse_mode="HTML")
            
            @self.bot.message_handler(commands=['help'])
            def help_handler(message):
                help_msg = (
                    "📖 <b>帮助文档</b>\n\n"
                    "🔍 <b>/ca 命令使用方法:</b>\n"
                    "• 命令格式: <code>/ca &lt;代币合约地址&gt;</code>\n"
                    "• 功能: 分析指定代币的大户持仓情况\n"
                    "• 分析范围: 前100名大户的持仓分布\n\n"
                    "🎯 <b>/caw 钱包组分析:</b>\n"
                    "• 命令格式: <code>/caw [代币地址\\n钱包地址1\\n钱包地址2...]</code>\n"
                    "• 功能: 分析指定钱包组对特定代币的持仓\n"
                    "• 目标代币会显示在第一行\n\n"
                    "💡 <b>使用提示:</b>\n"
                    "• 确保地址格式正确\n"
                    "• 分析通常需要30-60秒\n"
                    "• 可从GMGN、DEX等平台获取地址\n\n"
                    "📝 <b>示例:</b>\n"
                    "<code>/ca FbGsCHv8qPvUdmomVAiG72ET5D5kgBJgGoxxfMZipump</code>\n"
                    "<code>/caw [EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v\\n4vbZLV...\\n66T4v4...]</code>"
                )
                self._reply_to_user(message, help_msg, parse_mode="HTML")
                
            print("✅ 所有处理器注册成功")
            
        except Exception as e:
            print(f"❌ 处理器注册失败: {e}")
            raise
    
    def _reply_to_user(self, message, text, **kwargs):
        """回复用户消息"""
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
    
    def start(self):
        """启动机器人"""
        print("🤖 启动代币分析Bot...")
        
        try:
            # 启动bot轮询
            while True:
                try:
                    print("👂 开始监听Telegram消息...")
                    self.bot.polling(none_stop=True, interval=3, timeout=30)
                except Exception as e:
                    print(f"❌ Bot轮询错误: {e}")
                    print("⏳ 等待5秒后重新开始轮询...")
                    import time
                    time.sleep(5)
                    
        except Exception as e:
            print(f"❌ Bot启动失败: {e}")
            raise


def main():
    """主函数"""
    bot = None
    
    try:
        print("🚀 启动简化版代币分析Bot...")
        bot = SimpleTokenBot()
        bot.start()
    except KeyboardInterrupt:
        print("\n👋 程序被用户中断")
    except Exception as e:
        print(f"❌ 程序启动失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
