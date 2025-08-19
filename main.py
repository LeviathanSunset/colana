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

# 导入日志模块和健康检查
from src.utils.logger import get_logger
from src.utils.health_check import get_health_status, update_service_status, increment_stat

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
from src.utils.data_manager import DataManager, clear_all_storage


class TokenAnalysisBot:
    """代币分析机器人主类"""
    
    def __init__(self):
        """初始化分析机器人"""
        # 初始化日志器
        self.logger = get_logger("main")
        self.health_status = get_health_status()
        self.logger.info("🚀 初始化代币分析机器人...")
        
        try:
            self.config = get_config()
            update_service_status("telegram_bot", "initializing")
            
            # Bot重启时清空所有存储文件
            self.logger.info("🗑️ Bot重启，清空所有存储文件...")
            clear_all_storage()
            
            self.data_manager = DataManager()
            setup_proxy()
            
            # 初始化机器人
            self.bot = telebot.TeleBot(self.config.bot.telegram_token)
            self.logger.info("✅ Telegram Bot 初始化成功")
            update_service_status("telegram_bot", "healthy")
            
            # 初始化消息格式化器
            self.formatter = MessageFormatter()
            
            # 初始化处理器
            self.base_handler = BaseCommandHandler(self.bot)
            self.config_handler = ConfigCommandHandler(self.bot)
            self.holding_handler = HoldingAnalysisHandler(self.bot)
            self.jupiter_handler = JupiterAnalysisHandler(self.bot)
            self.auto_pump_handler = AutoPumpAnalysisHandler(self.bot)
            self.logger.info("✅ 所有处理器初始化成功")
            
        except Exception as e:
            update_service_status("telegram_bot", "error", str(e))
            self.logger.error_with_solution(e, "Bot初始化失败")
            raise
        
        # 注册处理器
        self._register_handlers()
    
    def _register_handlers(self):
        """注册所有处理器"""
        self.logger.info("📝 注册消息处理器...")
        try:
            self.base_handler.register_handlers()
            self.config_handler.register_handlers()
            self.holding_handler.register_handlers()
            self.jupiter_handler.register_handlers()
            self.auto_pump_handler.register_handlers()
            self.logger.info("✅ 所有处理器注册成功")
            
            # 测试命令
            @self.bot.message_handler(commands=['testtopic'])
            def test_topic_handler(message):
                self.logger.info(f"📧 收到测试topic命令，用户: {message.from_user.username}")
                thread_id = self.config.bot.message_thread_id
                self.bot.send_message(
                    self.config.bot.telegram_chat_id,
                    f"测试消息已发送到{thread_id or '主群'} topic!",
                    message_thread_id=thread_id
                )
                self.logger.info(f"✅ 测试消息发送成功到 thread_id: {thread_id}")
                
        except Exception as e:
            self.logger.exception(f"❌ 处理器注册失败: {e}")
            raise
    
    def compare_and_filter(self, pre_path: str, now_path: str) -> list:
        """比较并过滤代币数据"""
        self.logger.info(f"📊 开始比较数据文件: {os.path.basename(pre_path)} vs {os.path.basename(now_path)}")
        
        def read_csv(path):
            data = {}
            try:
                with open(path, encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        data[row.get('mint')] = row
                self.logger.debug(f"✅ 成功读取CSV文件 {path}: {len(data)} 条记录")
            except Exception as e:
                self.logger.error(f"❌ 读取CSV失败 {path}: {e}")
            return data
        
        pre = read_csv(pre_path)
        now = read_csv(now_path)
        
        if not pre or not now:
            self.logger.warning("⚠️ CSV数据为空，无法进行比较")
            return []
        
        results = []
        processed_count = 0
        blacklisted_count = 0
        threshold_filtered_count = 0
        
        self.logger.info(f"🔍 开始分析 {len(now)} 个代币...")
        
        for mint, now_row in now.items():
            processed_count += 1
            pre_row = pre.get(mint)
            if not pre_row:
                continue
            
            # 检查黑名单
            if is_blacklisted(mint):
                blacklisted_count += 1
                self.logger.debug(f"🚫 代币 {mint} 在黑名单中，跳过")
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
                    self.logger.debug(f"✅ 符合条件的代币: {token.symbol}({mint[:8]}...) "
                                    f"涨幅: {change:.2%}, 市值: ${now_cap:,.0f}")
                else:
                    threshold_filtered_count += 1
                    
            except Exception as e:
                self.logger.error(f"❌ 处理代币数据失败 {mint}: {e}")
                continue
        
        self.logger.info(f"📈 数据分析完成:")
        self.logger.info(f"   - 总处理: {processed_count} 个代币")
        self.logger.info(f"   - 黑名单过滤: {blacklisted_count} 个")
        self.logger.info(f"   - 条件不符: {threshold_filtered_count} 个")
        self.logger.info(f"   - 符合条件: {len(results)} 个")
        
        return results
    
    def crawler_loop(self):
        """爬虫循环"""
        self.logger.info("🚀 启动爬虫循环...")
        
        while True:
            try:
                # 重新加载配置
                self.logger.debug("🔄 重新加载配置...")
                self.config.load_config()
                
                self.logger.info("📊 开始爬取代币数据...")
                crawler = PumpFunCrawler()
                
                # 爬取数据
                crawl_start_time = time.time()
                crawler.crawl_all_pages(max_tokens=1000)
                crawler.deduplicate_by_mint(keep=1000)
                crawl_duration = time.time() - crawl_start_time
                self.logger.info(f"📊 数据爬取完成，耗时: {crawl_duration:.2f}秒")
                
                now_path = self.data_manager.get_file_path("csv_data", "now.csv")
                pre_path = self.data_manager.get_file_path("csv_data", "pre.csv")
                
                # 保存当前数据
                save_start_time = time.time()
                crawler.save_to_csv(str(now_path))
                save_duration = time.time() - save_start_time
                self.logger.info(f"💾 CSV数据保存完成: {now_path}, 耗时: {save_duration:.2f}秒")
                
                if not os.path.exists(pre_path):
                    shutil.copy(str(now_path), str(pre_path))
                    self.logger.info("📁 创建初始数据文件")
                else:
                    self.logger.info("🔍 开始分析价格变化...")
                    
                    # 分析价格变化
                    analysis_start_time = time.time()
                    results = self.compare_and_filter(str(pre_path), str(now_path))
                    analysis_duration = time.time() - analysis_start_time
                    self.logger.info(f"📈 价格分析完成，耗时: {analysis_duration:.2f}秒")
                    
                    if results:
                        # 计算时间差
                        old_ts = datetime.fromtimestamp(os.path.getmtime(str(pre_path))).strftime('%Y-%m-%d %H:%M:%S')
                        new_ts = datetime.fromtimestamp(os.path.getmtime(str(now_path))).strftime('%Y-%m-%d %H:%M:%S')
                        mins = int((os.path.getmtime(str(now_path)) - os.path.getmtime(str(pre_path))) / 60)
                        
                        self.logger.info(f"🎯 检测到 {len(results)} 个符合条件的涨幅代币")
                        self.logger.info(f"   时间跨度: {mins} 分钟 ({old_ts} -> {new_ts})")
                        
                        # 更新时间跨度
                        for result in results:
                            result.time_span_minutes = mins
                        
                        # 发送消息
                        self.logger.info("📤 开始发送Pump警报消息...")
                        send_start_time = time.time()
                        self._send_price_alerts(results, mins, old_ts, new_ts)
                        send_duration = time.time() - send_start_time
                        self.logger.info(f"✅ Pump警报发送完成，耗时: {send_duration:.2f}秒")
                    else:
                        self.logger.info(f"📊 未检测到符合条件的涨幅代币")
                        self.logger.info(f"   当前阈值: {self.config.bot.threshold*100:.1f}%")
                        self.logger.info(f"   最低市值: ${self.config.bot.min_market_cap:,.0f}")
                        self.logger.info(f"   最低年龄: {self.config.bot.min_age_days} 天")
                    
                    # 更新pre文件 - 无论是否有结果都要更新
                    shutil.copy(str(now_path), str(pre_path))
                    self.logger.debug("📁 更新基准数据文件")
                
                self.logger.info(f"😴 等待 {self.config.bot.interval} 秒后进行下一轮...")
                time.sleep(self.config.bot.interval)
                
            except Exception as e:
                self.logger.exception(f"❌ 爬虫循环发生错误: {e}")
                self.logger.info("⏳ 等待3秒后重试...")
                time.sleep(3)
    
    def _send_price_alerts(self, results: list, mins: int, old_ts: str, new_ts: str):
        """发送价格预警消息"""
        self.logger.info(f"📤 准备发送价格预警消息: {len(results)} 个代币")
        
        try:
            page_size = 10
            total = len(results)
            pages = (total + page_size - 1) // page_size
            max_pages = 5
            
            self.logger.info(f"📄 消息分页信息: 总计{total}个币种，分{pages}页，每页{page_size}个")
            
            if pages > max_pages:
                warning_msg = f'⚠️ 检测到{total}个涨幅币种（共{pages}页），为避免刷屏，仅显示前{max_pages}页（{max_pages*page_size}个币种）'
                self.logger.warning(f"页数过多: {pages} > {max_pages}，将限制显示")
                
                try:
                    self.bot.send_message(
                        self.config.bot.telegram_chat_id,
                        warning_msg,
                        parse_mode='HTML',
                        message_thread_id=self.config.bot.message_thread_id,
                        disable_web_page_preview=True
                    )
                    self.logger.info("✅ 警告消息发送成功")
                except Exception as e:
                    self.logger.error(f"❌ 警告消息发送失败: {e}")
                
                pages = max_pages
            
            sent_pages = 0
            failed_pages = 0
            
            for page in range(pages):
                try:
                    start_idx = page * page_size
                    end_idx = min(start_idx + page_size, len(results))
                    page_results = results[start_idx:end_idx]
                    
                    self.logger.debug(f"📑 准备发送第{page+1}页: 索引{start_idx}-{end_idx}")
                    
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
                    
                    sent_pages += 1
                    self.logger.info(f"✅ 第{page+1}/{pages}页发送成功")
                    
                    if page < pages - 1:
                        self.logger.debug("⏳ 页面间等待1.2秒...")
                        time.sleep(1.2)
                        
                except Exception as e:
                    failed_pages += 1
                    self.logger.error(f"❌ 第{page+1}页发送失败: {e}")
                    time.sleep(3)
            
            self.logger.info(f"📊 消息发送完成: 成功{sent_pages}页, 失败{failed_pages}页")
                    
        except Exception as e:
            self.logger.exception(f"❌ 发送预警消息时发生严重错误: {e}")
    
    def start(self):
        """启动机器人"""
        self.logger.info("🤖 启动代币分析Bot...")
        
        try:
            # 启动爬虫线程
            self.logger.info("🎯 启动爬虫线程...")
            crawler_thread = threading.Thread(target=self.crawler_loop, daemon=True)
            crawler_thread.start()
            self.logger.info("✅ 爬虫线程启动成功")
            update_service_status("crawler", "healthy")
            
            # 更新统计信息
            increment_stat("requests_total", 0)  # 初始化统计
            
            # 启动bot轮询
            while True:
                try:
                    self.logger.info("👂 开始监听Telegram消息...")
                    self.health_status.update_heartbeat()
                    self.bot.polling(none_stop=True, interval=3, timeout=30)
                except Exception as e:
                    increment_stat("errors_total")
                    update_service_status("telegram_bot", "error", str(e))
                    self.logger.error_with_solution(e, "Bot轮询错误")
                    self.logger.info("⏳ 等待5秒后重新开始轮询...")
                    time.sleep(5)
                    
        except Exception as e:
            update_service_status("telegram_bot", "error", str(e))
            self.logger.error_with_solution(e, "Bot启动失败")
            raise

    def run(self):
        """运行机器人（兼容性方法）"""
        self.start()


def main():
    """主函数"""
    logger = get_logger("startup")
    
    try:
        logger.info("🚀 启动代币分析Bot程序...")
        bot = TokenAnalysisBot()
        bot.start()
    except KeyboardInterrupt:
        logger.info("\n👋 程序被用户中断")
    except Exception as e:
        logger.exception(f"❌ 程序启动失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
