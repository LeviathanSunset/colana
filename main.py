#!/usr/bin/env python3
"""
代币大户分析Bot - 重构版主程序
优化的项目结构和模块化设计
"""
import os
import sys
import time
import threading
import shutil
import csv
from datetime import datetime

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import telebot
from src.core.config import get_config, setup_proxy
from src.services.crawler import PumpFunCrawler
from src.services.blacklist import is_blacklisted
from src.services.formatter import MessageFormatter
from src.handlers.base import BaseCommandHandler
from src.handlers.config import ConfigCommandHandler
from src.handlers.holding_analysis import HoldingAnalysisHandler
from src.handlers.jupiter_analysis import JupiterAnalysisHandler
from src.handlers.auto_pump_analysis import AutoPumpAnalysisHandler
from src.models import TokenInfo, PriceChangeResult
from src.utils import format_number, format_percentage, chunk_list
from src.utils.data_manager import DataManager
from src.utils.data_manager import DataManager


class TokenAnalysisBot:
    """代币分析机器人主类"""
    
    def __init__(self):
        """初始化分析机器人"""
        self.config = get_config()
        self.data_manager = DataManager()
        setup_proxy()
        
        # 初始化机器人
        self.bot = telebot.TeleBot(self.config.bot.telegram_token)
        
        # 初始化处理器
        self.base_handler = BaseCommandHandler(self.bot)
        self.config_handler = ConfigCommandHandler(self.bot)
        self.holding_handler = HoldingAnalysisHandler(self.bot)
        self.jupiter_handler = JupiterAnalysisHandler(self.bot)
        self.auto_pump_handler = AutoPumpAnalysisHandler(self.bot)
        
        # 注册处理器
        self._register_handlers()
    
    def _register_handlers(self):
        """注册所有处理器"""
        self.base_handler.register_handlers()
        self.config_handler.register_handlers()
        self.holding_handler.register_handlers()
        self.jupiter_handler.register_handlers()
        self.auto_pump_handler.register_handlers()
        
        # 测试命令
        @self.bot.message_handler(commands=['testtopic'])
        def test_topic_handler(message):
            thread_id = self.config.bot.message_thread_id
            self.bot.send_message(
                self.config.bot.telegram_chat_id,
                f"测试消息已发送到{thread_id or '主群'} topic!",
                message_thread_id=thread_id
            )
    
    def compare_and_filter(self, pre_path: str, now_path: str) -> list:
        """比较并过滤代币数据"""
        def read_csv(path):
            data = {}
            try:
                with open(path, encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        data[row.get('mint')] = row
            except Exception as e:
                print(f"读取CSV失败 {path}: {e}")
            return data
        
        pre = read_csv(pre_path)
        now = read_csv(now_path)
        
        if not pre or not now:
            return []
        
        results = []
        
        for mint, now_row in now.items():
            pre_row = pre.get(mint)
            if not pre_row:
                continue
            
            # 检查黑名单
            if is_blacklisted(mint):
                continue
            
            try:
                pre_cap = float(pre_row.get('usd_market_cap', 0))
                now_cap = float(now_row.get('usd_market_cap', 0))
                
                if pre_cap <= 0:
                    continue
                
                change = (now_cap - pre_cap) / pre_cap
                
                # 计算年龄
                created_timestamp = float(now_row.get('created_timestamp', 0))
                if created_timestamp > 0:
                    age_days = (time.time() * 1000 - created_timestamp) / 1000 / 60 / 60 / 24
                else:
                    age_days = 0
                
                # 检查条件
                if (change >= self.config.bot.threshold and 
                    now_cap >= self.config.bot.min_market_cap and 
                    age_days >= self.config.bot.min_age_days):
                    
                    # 创建TokenInfo对象
                    token = TokenInfo(
                        mint=mint,
                        name=now_row.get('name', ''),
                        symbol=now_row.get('symbol', ''),
                        usd_market_cap=now_cap,
                        created_timestamp=int(created_timestamp),
                        age_days=age_days,
                        change=change
                    )
                    
                    # 创建PriceChangeResult对象
                    result = PriceChangeResult(
                        token=token,
                        old_price=pre_cap,
                        new_price=now_cap,
                        change_percent=change,
                        time_span_minutes=0  # 将在后面计算
                    )
                    
                    results.append(result)
                    
            except Exception as e:
                print(f"处理代币数据失败 {mint}: {e}")
                continue
        
        return results
    
    def crawler_loop(self):
        """爬虫循环"""
        print("🚀 启动爬虫循环...")
        
        while True:
            try:
                # 重新加载配置
                self.config.load_config()
                
                print("📊 开始爬取代币数据...")
                crawler = PumpFunCrawler()
                crawler.crawl_all_pages(max_tokens=1000)
                crawler.deduplicate_by_mint(keep=1000)
                
                now_path = self.data_manager.get_file_path("csv_data", "now.csv")
                pre_path = self.data_manager.get_file_path("csv_data", "pre.csv")
                
                crawler.save_to_csv(str(now_path))
                
                if not os.path.exists(pre_path):
                    shutil.copy(str(now_path), str(pre_path))
                    print("📁 创建初始数据文件")
                else:
                    # 分析价格变化
                    results = self.compare_and_filter(str(pre_path), str(now_path))
                    
                    if results:
                        # 计算时间差
                        old_ts = datetime.fromtimestamp(os.path.getmtime(str(pre_path))).strftime('%Y-%m-%d %H:%M:%S')
                        new_ts = datetime.fromtimestamp(os.path.getmtime(str(now_path))).strftime('%Y-%m-%d %H:%M:%S')
                        mins = int((os.path.getmtime(str(now_path)) - os.path.getmtime(str(pre_path))) / 60)
                        
                        # 更新时间跨度
                        for result in results:
                            result.time_span_minutes = mins
                        
                        # 发送消息
                        self._send_price_alerts(results, mins, old_ts, new_ts)
                    
                    # 更新pre文件
                    shutil.copy(str(now_path), str(pre_path))
                
                print(f"😴 等待 {self.config.bot.interval} 秒...")
                time.sleep(self.config.bot.interval)
                
            except Exception as e:
                print(f"❌ 爬虫循环错误: {e}")
                time.sleep(3)
    
    def _send_price_alerts(self, results: list, mins: int, old_ts: str, new_ts: str):
        """发送价格预警消息"""
        try:
            page_size = 10
            total = len(results)
            pages = (total + page_size - 1) // page_size
            max_pages = 5
            
            if pages > max_pages:
                self.bot.send_message(
                    self.config.bot.telegram_chat_id,
                    f'⚠️ 检测到{total}个涨幅币种（共{pages}页），为避免刷屏，仅显示前{max_pages}页（{max_pages*page_size}个币种）',
                    parse_mode='HTML',
                    message_thread_id=self.config.bot.message_thread_id,
                    disable_web_page_preview=True
                )
                pages = max_pages
            
            for page in range(pages):
                try:
                    start_idx = page * page_size
                    end_idx = min(start_idx + page_size, len(results))
                    page_results = results[start_idx:end_idx]
                    
                    message = self.formatter.format_price_change_message(
                        page_results, mins, old_ts, new_ts, page, pages
                    )
                    
                    self.bot.send_message(
                        self.config.bot.telegram_chat_id,
                        message,
                        parse_mode='HTML',
                        disable_web_page_preview=True,
                        message_thread_id=self.config.bot.message_thread_id
                    )
                    
                    if page < pages - 1:
                        time.sleep(1.2)
                        
                except Exception as e:
                    print(f"❌ 发送消息失败 (页面 {page + 1}): {e}")
                    time.sleep(3)
                    
        except Exception as e:
            print(f"❌ 发送预警失败: {e}")
    
    def start(self):
        """启动机器人"""
        print("🤖 启动代币分析Bot...")
        
        # 启动爬虫线程
        crawler_thread = threading.Thread(target=self.crawler_loop, daemon=True)
        crawler_thread.start()
        
        # 启动bot轮询
        while True:
            try:
                print("👂 开始监听消息...")
                self.bot.polling(none_stop=True, interval=3, timeout=30)
            except Exception as e:
                print(f"❌ Bot轮询错误: {e}")
                time.sleep(3)


def main():
    """主函数"""
    try:
        bot = TokenAnalysisBot()
        bot.start()
    except KeyboardInterrupt:
        print("\n👋 程序被用户中断")
    except Exception as e:
        print(f"❌ 程序启动失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
