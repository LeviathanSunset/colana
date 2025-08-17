"""
自动pump分析处理器
处理 /capump on(off) 命令，自动分析pump异动（>10%）的持仓
"""

import time
import threading
import json
import os
from typing import Dict, Set
from telebot import TeleBot
from telebot.types import Message
from ..core.config import get_config
from ..services.blacklist import is_blacklisted
from ..utils.data_manager import DataManager

# 导入OKX相关功能
try:
    from ..services.okx_crawler import OKXCrawlerForBot
except ImportError:
    print("⚠️ 无法导入OKX爬虫模块，自动pump分析功能可能不可用")
    OKXCrawlerForBot = None


class AutoPumpAnalysisHandler:
    """自动pump分析处理器"""
    
    def __init__(self, bot: TeleBot):
        """初始化自动分析处理器"""
        self.bot = bot
        self.config = get_config()
        self.data_manager = DataManager()
        self.status_file = self.data_manager.get_file_path("config", "auto_pump_status.json")
        self.analysis_status: Dict[str, bool] = {}  # chat_id -> enabled
        self.analysis_threads: Dict[str, threading.Thread] = {}  # chat_id -> thread
        self.stop_flags: Dict[str, threading.Event] = {}  # chat_id -> stop_event
        self.analyzed_tokens: Dict[str, Set[str]] = {}  # chat_id -> set of analyzed tokens
        
        # 加载保存的状态
        self.load_status()
        
        # 为已启用的群组启动分析线程
        self.restore_analysis_threads()
    
    def load_status(self):
        """加载自动分析状态"""
        try:
            if os.path.exists(self.status_file):
                with open(self.status_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.analysis_status = data.get('analysis_status', {})
                    # 重置已分析的代币列表（重启后重新开始）
                    self.analyzed_tokens = {chat_id: set() for chat_id in self.analysis_status.keys()}
        except Exception as e:
            print(f"加载自动pump分析状态失败: {e}")
            self.analysis_status = {}
            self.analyzed_tokens = {}
    
    def save_status(self):
        """保存自动分析状态"""
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(self.status_file), exist_ok=True)
            
            data = {
                'analysis_status': self.analysis_status,
                'last_updated': time.time()
            }
            
            with open(self.status_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"保存自动pump分析状态失败: {e}")
    
    def handle_capump(self, message: Message) -> None:
        """处理 /capump 命令"""
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
        
        # 解析命令参数
        parts = message.text.split()
        if len(parts) < 2:
            # 显示当前状态
            current_status = self.analysis_status.get(chat_id, False)
            status_text = "🟢 已启用" if current_status else "🔴 已关闭"
            
            self.bot.reply_to(
                message,
                f"🤖 自动pump分析状态: {status_text}\n\n"
                f"📋 功能说明:\n"
                f"• 自动监控pump异动（>10%）的代币\n"
                f"• 对符合条件的代币自动进行持仓分析\n"
                f"• 黑名单中的代币将被跳过\n\n"
                f"💡 使用方法:\n"
                f"• <code>/capump on</code> - 启用自动分析\n"
                f"• <code>/capump off</code> - 关闭自动分析\n"
                f"• <code>/capump</code> - 查看当前状态",
                parse_mode='HTML'
            )
            return
        
        action = parts[1].lower()
        
        if action == "on":
            self._enable_auto_analysis(message, chat_id)
        elif action == "off":
            self._disable_auto_analysis(message, chat_id)
        else:
            self.bot.reply_to(
                message,
                "❌ 无效参数\n\n"
                "💡 使用方法:\n"
                "• <code>/capump on</code> - 启用自动分析\n"
                "• <code>/capump off</code> - 关闭自动分析\n"
                "• <code>/capump</code> - 查看当前状态",
                parse_mode='HTML'
            )
    
    def _enable_auto_analysis(self, message: Message, chat_id: str):
        """启用自动分析"""
        if chat_id in self.analysis_status and self.analysis_status[chat_id]:
            self.bot.reply_to(message, "✅ 自动pump分析已经在运行中")
            return
        
        # 启用状态
        self.analysis_status[chat_id] = True
        self.analyzed_tokens[chat_id] = set()
        self.save_status()
        
        # 启动分析线程
        self._start_analysis_thread(chat_id)
        
        self.bot.reply_to(
            message,
            "🟢 已启用自动pump分析\n\n"
            "📊 监控条件:\n"
            "• 价格异动 > 10%\n"
            "• 不在黑名单中\n"
            "• 自动进行持仓分析\n\n"
            "⚡ 分析结果将自动发送到当前群组"
        )
    
    def _disable_auto_analysis(self, message: Message, chat_id: str):
        """关闭自动分析"""
        if chat_id not in self.analysis_status or not self.analysis_status[chat_id]:
            self.bot.reply_to(message, "🔴 自动pump分析已经关闭")
            return
        
        # 停止分析线程
        self._stop_analysis_thread(chat_id)
        
        # 禁用状态
        self.analysis_status[chat_id] = False
        if chat_id in self.analyzed_tokens:
            del self.analyzed_tokens[chat_id]
        self.save_status()
        
        self.bot.reply_to(message, "🔴 已关闭自动pump分析")
    
    def _start_analysis_thread(self, chat_id: str):
        """启动分析线程"""
        if chat_id in self.analysis_threads and self.analysis_threads[chat_id].is_alive():
            return
        
        # 创建停止标志
        stop_event = threading.Event()
        self.stop_flags[chat_id] = stop_event
        
        # 创建并启动线程
        thread = threading.Thread(
            target=self._analysis_loop,
            args=(chat_id, stop_event),
            daemon=True
        )
        thread.start()
        self.analysis_threads[chat_id] = thread
        
        print(f"🚀 为群组 {chat_id} 启动自动pump分析线程")
    
    def _stop_analysis_thread(self, chat_id: str):
        """停止分析线程"""
        if chat_id in self.stop_flags:
            self.stop_flags[chat_id].set()
        
        if chat_id in self.analysis_threads:
            thread = self.analysis_threads[chat_id]
            if thread.is_alive():
                thread.join(timeout=5)
            del self.analysis_threads[chat_id]
        
        if chat_id in self.stop_flags:
            del self.stop_flags[chat_id]
        
        print(f"🛑 已停止群组 {chat_id} 的自动pump分析线程")
    
    def restore_analysis_threads(self):
        """恢复分析线程（重启后）"""
        for chat_id, enabled in self.analysis_status.items():
            if enabled:
                self._start_analysis_thread(chat_id)
    
    def _analysis_loop(self, chat_id: str, stop_event: threading.Event):
        """分析循环"""
        print(f"📊 开始群组 {chat_id} 的自动pump分析循环")
        
        # 初始延迟，避免启动时立即检查
        if not stop_event.wait(30):  # 启动后等待30秒
            pass
        
        while not stop_event.is_set():
            try:
                # 检查是否仍然启用
                if not self.analysis_status.get(chat_id, False):
                    break
                
                # 检查数据文件是否存在且足够新
                now_path = 'data/now.csv'
                pre_path = 'data/pre.csv'
                
                if not os.path.exists(now_path) or not os.path.exists(pre_path):
                    print(f"📊 群组 {chat_id}: 等待数据文件...")
                    stop_event.wait(60)
                    continue
                
                # 检查数据文件是否太旧（超过10分钟不更新）
                now_mtime = os.path.getmtime(now_path)
                if time.time() - now_mtime > 600:  # 10分钟
                    print(f"📊 群组 {chat_id}: 数据文件过旧，跳过检查")
                    stop_event.wait(300)
                    continue
                
                # 获取当前代币数据并检查pump异动
                pump_tokens = self._detect_pump_tokens()
                
                # 过滤已分析的代币
                new_pump_tokens = []
                analyzed_set = self.analyzed_tokens.get(chat_id, set())
                
                for token_data in pump_tokens:
                    token_address = token_data['mint']
                    if token_address not in analyzed_set:
                        new_pump_tokens.append(token_data)
                        analyzed_set.add(token_address)
                
                # 限制单次分析的代币数量
                if len(new_pump_tokens) > 5:
                    new_pump_tokens = new_pump_tokens[:5]
                    print(f"📊 群组 {chat_id}: 限制单次分析代币数量为5个")
                
                # 分析新的pump代币
                if new_pump_tokens:
                    print(f"📊 群组 {chat_id}: 发现 {len(new_pump_tokens)} 个新pump代币")
                    self._analyze_pump_tokens(chat_id, new_pump_tokens)
                else:
                    print(f"📊 群组 {chat_id}: 未发现新pump代币")
                
                # 定期清理已分析代币缓存（每小时）
                if len(analyzed_set) > 1000:  # 如果缓存过大
                    # 保留最近的500个
                    recent_tokens = list(analyzed_set)[-500:]
                    self.analyzed_tokens[chat_id] = set(recent_tokens)
                    print(f"📊 群组 {chat_id}: 清理已分析代币缓存")
                
                # 等待一段时间再检查（避免过于频繁）
                stop_event.wait(300)  # 5分钟检查一次
                
            except Exception as e:
                print(f"❌ 群组 {chat_id} 自动pump分析错误: {e}")
                stop_event.wait(60)  # 出错时等待1分钟后重试
        
        print(f"📊 群组 {chat_id} 的自动pump分析循环已结束")
    
    def _detect_pump_tokens(self) -> list:
        """检测pump异动的代币"""
        try:
            # 读取当前和历史数据
            now_path = 'data/now.csv'
            pre_path = 'data/pre.csv'
            
            if not os.path.exists(now_path) or not os.path.exists(pre_path):
                return []
            
            def read_csv(path):
                import csv
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
            
            pump_tokens = []
            pump_threshold = 0.10  # 10%涨幅阈值
            
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
                    
                    # 检查是否达到pump阈值
                    if change >= pump_threshold:
                        pump_tokens.append({
                            'mint': mint,
                            'name': now_row.get('name', ''),
                            'symbol': now_row.get('symbol', ''),
                            'change': change,
                            'old_cap': pre_cap,
                            'new_cap': now_cap,
                            'created_timestamp': now_row.get('created_timestamp', 0)
                        })
                
                except Exception as e:
                    continue
            
            # 按涨幅排序
            pump_tokens.sort(key=lambda x: x['change'], reverse=True)
            
            # 限制数量避免过载
            return pump_tokens[:10]
        
        except Exception as e:
            print(f"❌ 检测pump代币失败: {e}")
            return []
    
    def _analyze_pump_tokens(self, chat_id: str, pump_tokens: list):
        """分析pump代币"""
        for i, token_data in enumerate(pump_tokens):
            try:
                # 检查是否仍然启用（防止在分析过程中被关闭）
                if not self.analysis_status.get(chat_id, False):
                    print(f"📊 群组 {chat_id}: 分析被中断（功能已关闭）")
                    break
                
                token_address = token_data['mint']
                
                # 发送开始分析消息
                start_msg = (
                    f"🔥 检测到pump异动，开始自动分析... ({i+1}/{len(pump_tokens)})\n\n"
                    f"💰 代币: {token_data['symbol']} ({token_data['name']})\n"
                    f"📈 涨幅: {token_data['change']:.1%}\n"
                    f"� 市值: ${token_data['old_cap']:,.0f} → ${token_data['new_cap']:,.0f}\n"
                    f"�📍 地址: <code>{token_address}</code>\n\n"
                    f"⏳ 正在分析大户持仓..."
                )
                
                try:
                    start_message = self.bot.send_message(
                        chat_id,
                        start_msg,
                        parse_mode='HTML',
                        disable_web_page_preview=True
                    )
                except Exception as e:
                    print(f"❌ 发送开始消息失败: {e}")
                    continue
                
                # 创建OKX爬虫并执行分析
                try:
                    crawler = OKXCrawlerForBot()
                    result = crawler.analyze_token_holders(
                        token_address, 
                        top_holders_count=self.config.analysis.top_holders_count
                    )
                    
                    if result and result.get("token_statistics"):
                        # 导入格式化函数
                        from ..services.okx_crawler import format_tokens_table
                        
                        # 格式化分析结果 - 传递token_statistics部分而不是整个result
                        table_msg, table_markup = format_tokens_table(
                            result["token_statistics"], 
                            sort_by="count"
                        )
                        
                        if table_msg:
                            # 添加pump分析标识
                            pump_info = (
                                f"🔥 <b>自动pump分析结果</b> ({i+1}/{len(pump_tokens)})\n"
                                f"📈 检测涨幅: {token_data['change']:.1%}\n"
                                f"💰 市值变化: ${token_data['old_cap']:,.0f} → ${token_data['new_cap']:,.0f}\n"
                                f"🕐 分析时间: {time.strftime('%H:%M:%S')}\n\n"
                            )
                            
                            final_msg = pump_info + table_msg
                            
                            # 更新消息
                            try:
                                self.bot.edit_message_text(
                                    final_msg,
                                    start_message.chat.id,
                                    start_message.message_id,
                                    parse_mode="HTML",
                                    reply_markup=table_markup,
                                    disable_web_page_preview=True,
                                )
                                print(f"✅ 成功分析pump代币: {token_data['symbol']}")
                            except Exception as e:
                                print(f"❌ 更新分析结果失败: {e}")
                        else:
                            # 分析失败 - 无数据
                            error_msg = (
                                f"❌ 自动分析失败 ({i+1}/{len(pump_tokens)})\n"
                                f"💰 代币: {token_data['symbol']}\n"
                                f"📍 地址: <code>{token_address}</code>\n\n"
                                f"📊 分析结果为空，可能原因:\n"
                                f"• 代币持仓数据不足\n"
                                f"• 代币地址无效\n"
                                f"• 暂无大户持仓"
                            )
                            
                            try:
                                self.bot.edit_message_text(
                                    error_msg,
                                    start_message.chat.id,
                                    start_message.message_id,
                                    parse_mode="HTML"
                                )
                            except Exception as e:
                                print(f"❌ 更新错误消息失败: {e}")
                    else:
                        # 分析失败 - API错误
                        error_msg = (
                            f"❌ 自动分析失败 ({i+1}/{len(pump_tokens)})\n"
                            f"💰 代币: {token_data['symbol']}\n"
                            f"📍 地址: <code>{token_address}</code>\n\n"
                            f"🔍 未获取到有效的持仓数据\n"
                            f"可能原因:\n"
                            f"• 网络连接问题\n"
                            f"• API服务限制\n"
                            f"• 代币数据异常"
                        )
                        
                        try:
                            self.bot.edit_message_text(
                                error_msg,
                                start_message.chat.id,
                                start_message.message_id,
                                parse_mode="HTML"
                            )
                        except Exception as e:
                            print(f"❌ 更新错误消息失败: {e}")
                
                except Exception as e:
                    print(f"❌ 分析代币失败 {token_data['mint']}: {e}")
                    # 尝试更新错误消息
                    try:
                        error_msg = (
                            f"❌ 分析过程中发生错误 ({i+1}/{len(pump_tokens)})\n"
                            f"💰 代币: {token_data['symbol']}\n"
                            f"📍 地址: <code>{token_address}</code>\n\n"
                            f"⚠️ 错误信息: {str(e)[:100]}..."
                        )
                        self.bot.edit_message_text(
                            error_msg,
                            start_message.chat.id,
                            start_message.message_id,
                            parse_mode="HTML"
                        )
                    except:
                        pass
                
                # 避免API限制，添加延迟（最后一个不延迟）
                if i < len(pump_tokens) - 1:
                    time.sleep(15)  # 增加到15秒间隔
                
            except Exception as e:
                print(f"❌ 处理pump代币失败 {token_data.get('mint', 'unknown')}: {e}")
                continue
    
    def register_handlers(self) -> None:
        """注册处理器"""
        @self.bot.message_handler(commands=["capump"])
        def capump_handler(message):
            self.handle_capump(message)
