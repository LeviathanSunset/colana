import importlib
from telebot import types
from config import TELEGRAM_CHAT_ID, INTERVAL, THRESHOLD, MIN_MARKET_CAP, MIN_AGE_DAYS, TOP_HOLDERS_COUNT, RANKING_SIZE, DETAIL_BUTTONS_COUNT, CLUSTER_MIN_COMMON_TOKENS, CLUSTER_MIN_ADDRESSES, CLUSTER_MAX_ADDRESSES
from blacklist import add_to_blacklist, remove_from_blacklist, get_blacklist_count, get_blacklist_list
from okx_crawler import OKXCrawlerForBot, format_tokens_table, format_token_holders_detail, analyze_address_clusters, format_cluster_analysis
import threading
import time

# 全局缓存存储分析结果
analysis_cache = {}

def cleanup_expired_cache():
    """清理过期的缓存条目"""
    try:
        current_time = time.time()
        expired_keys = []
        
        for key, data in analysis_cache.items():
            if current_time - data['timestamp'] > 24 * 3600:  # 24小时过期
                expired_keys.append(key)
        
        for key in expired_keys:
            del analysis_cache[key]
            
        if expired_keys:
            print(f"清理了 {len(expired_keys)} 个过期缓存条目")
            
    except Exception as e:
        print(f"清理缓存时出错: {str(e)}")

def update_config_impl(bot, message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton(f"INTERVAL: {INTERVAL}", callback_data="edit_INTERVAL"),
        types.InlineKeyboardButton(f"THRESHOLD: {THRESHOLD}", callback_data="edit_THRESHOLD"),
        types.InlineKeyboardButton(f"MIN_MARKET_CAP: {MIN_MARKET_CAP}", callback_data="edit_MIN_MARKET_CAP"),
        types.InlineKeyboardButton(f"MIN_AGE_DAYS: {MIN_AGE_DAYS}", callback_data="edit_MIN_AGE_DAYS")
    )
    markup.add(
        types.InlineKeyboardButton(f"TOP_HOLDERS_COUNT: {TOP_HOLDERS_COUNT}", callback_data="edit_TOP_HOLDERS_COUNT"),
        types.InlineKeyboardButton(f"RANKING_SIZE: {RANKING_SIZE}", callback_data="edit_RANKING_SIZE")
    )
    markup.add(
        types.InlineKeyboardButton(f"DETAIL_BUTTONS: {DETAIL_BUTTONS_COUNT}", callback_data="edit_DETAIL_BUTTONS_COUNT")
    )
    markup.add(
        types.InlineKeyboardButton(f"CLUSTER_MIN_TOKENS: {CLUSTER_MIN_COMMON_TOKENS}", callback_data="edit_CLUSTER_MIN_COMMON_TOKENS"),
        types.InlineKeyboardButton(f"CLUSTER_SIZE: {CLUSTER_MIN_ADDRESSES}-{CLUSTER_MAX_ADDRESSES}", callback_data="edit_CLUSTER_SIZE")
    )
    markup.add(
        types.InlineKeyboardButton(f"🚫 黑名单管理 ({get_blacklist_count()})", callback_data="blacklist_menu")
    )
    bot.send_message(message.chat.id, "请选择要更改的配置项：", reply_markup=markup)

def send_welcome_impl(bot, message):
    help_text = """
🤖 <b>Bot 功能说明</b>

📈 <b>主要功能</b>
• 自动监控代币涨幅变化
• 发送涨幅预警到指定群组
• 黑名单管理功能
• 代币大户分析功能
• <b>🎯 地址集群分析 (NEW!)</b>

🔧 <b>可用命令</b>
/start 或 /help - 显示此帮助信息
/config - 配置监控参数
/ca1 &lt;token_address&gt; - 分析代币大户持仓
/topicid - 获取当前topic ID

⚙️ <b>配置项说明</b>
• TOP_HOLDERS_COUNT - 分析的大户数量 (1-200)
• RANKING_SIZE - 排行榜显示的代币数量 (1-100)  
• DETAIL_BUTTONS - 详情按钮数量 (1-100)
• CLUSTER_MIN_COMMON_TOKENS - 集群最少共同代币数 (2-10)
• 其他监控参数 (INTERVAL, THRESHOLD 等)

🎯 <b>集群分析功能</b>
• 识别经常投资相同代币的地址群体
• 发现可能的机构投资者、项目方团队
• 分析聪明钱集群和跟随者模式
• 显示集群共同持有的代币和投资价值
• 在 /ca1 分析结果中点击"🎯 地址集群分析"按钮使用

💡 <b>使用示例</b>
/ca1 FbGsCHv8qPvUdmomVAiG72ET5D5kgBJgGoxxfMZipump

📝 <b>注意事项</b>
• /ca1 分析需要1-2分钟时间
• 集群分析需要额外30-60秒
• 分析日志保存在 okx_log/ 目录
• 支持Solana链代币分析
• 可通过按钮切换排序方式
• 排行榜和按钮数量可通过 /config 调整
• 集群分析参数可通过 /config 调整
    """
    bot.reply_to(message, help_text, parse_mode='HTML', disable_web_page_preview=True)

def save_config_value_impl(bot, message, key):
    allowed = {
        'INTERVAL': int, 
        'THRESHOLD': float, 
        'MIN_MARKET_CAP': int, 
        'MIN_AGE_DAYS': int,
        'TOP_HOLDERS_COUNT': int,
        'RANKING_SIZE': int,
        'DETAIL_BUTTONS_COUNT': int,
        'CLUSTER_MIN_COMMON_TOKENS': int
    }
    if key not in allowed:
        bot.reply_to(message, "不支持的配置项。")
        return
    try:
        value = allowed[key](message.text)
        # 添加数值范围检查
        if key == 'TOP_HOLDERS_COUNT' and (value < 1 or value > 200):
            bot.reply_to(message, "TOP_HOLDERS_COUNT 应在 1-200 之间")
            return
        elif key == 'RANKING_SIZE' and (value < 1 or value > 100):
            bot.reply_to(message, "RANKING_SIZE 应在 1-100 之间")
            return
        elif key == 'DETAIL_BUTTONS_COUNT' and (value < 1 or value > 100):
            bot.reply_to(message, "DETAIL_BUTTONS_COUNT 应在 1-100 之间")
            return
        elif key == 'CLUSTER_MIN_COMMON_TOKENS' and (value < 2 or value > 10):
            bot.reply_to(message, "CLUSTER_MIN_COMMON_TOKENS 应在 2-10 之间")
            return
    except Exception:
        bot.reply_to(message, f"{key} 类型错误，应为 {allowed[key].__name__}")
        return
    # 修改 config.py
    with open('config.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()
    for i, line in enumerate(lines):
        if line.strip().startswith(f'{key} ='):
            comment = ''
            if '#' in line:
                comment = line[line.index('#'):]
            lines[i] = f'{key} = {value} {comment}\n'
    with open('config.py', 'w', encoding='utf-8') as f:
        f.writelines(lines)
    # 立即生效
    importlib.invalidate_caches()
    import config as config_mod
    importlib.reload(config_mod)
    global INTERVAL, THRESHOLD, MIN_MARKET_CAP, MIN_AGE_DAYS, TOP_HOLDERS_COUNT, RANKING_SIZE, DETAIL_BUTTONS_COUNT, CLUSTER_MIN_COMMON_TOKENS
    INTERVAL = config_mod.INTERVAL
    THRESHOLD = config_mod.THRESHOLD
    MIN_MARKET_CAP = config_mod.MIN_MARKET_CAP
    MIN_AGE_DAYS = config_mod.MIN_AGE_DAYS
    TOP_HOLDERS_COUNT = config_mod.TOP_HOLDERS_COUNT
    RANKING_SIZE = config_mod.RANKING_SIZE
    DETAIL_BUTTONS_COUNT = config_mod.DETAIL_BUTTONS_COUNT
    CLUSTER_MIN_COMMON_TOKENS = config_mod.CLUSTER_MIN_COMMON_TOKENS
    bot.reply_to(message, f"已更新 {key}={value}")
    update_config_impl(bot, message)

def show_blacklist_menu(bot, message):
    """显示黑名单菜单"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("➕ 添加黑名单", callback_data="add_blacklist"),
        types.InlineKeyboardButton("➖ 移除黑名单", callback_data="remove_blacklist")
    )
    markup.add(
        types.InlineKeyboardButton("📋 查看黑名单", callback_data="view_blacklist"),
        types.InlineKeyboardButton("⬅️ 返回配置", callback_data="back_to_config")
    )
    
    count = get_blacklist_count()
    text = f"🚫 黑名单管理\n\n当前黑名单数量: {count}\n\n请选择操作："
    bot.edit_message_text(text, message.chat.id, message.message_id, reply_markup=markup)

def add_blacklist_handler(bot, message, mint):
    """添加黑名单处理"""
    mint = mint.strip()
    if not mint:
        bot.reply_to(message, "CA不能为空")
        return
    
    if len(mint) < 20:  # 简单验证CA长度
        bot.reply_to(message, "请输入有效的CA")
        return
    
    if add_to_blacklist(mint):
        bot.reply_to(message, f"✅ 已将 {mint} 添加到黑名单")
    else:
        bot.reply_to(message, "❌ 添加失败，请重试")

def remove_blacklist_handler(bot, message, mint):
    """移除黑名单处理"""
    mint = mint.strip()
    if not mint:
        bot.reply_to(message, "CA不能为空")
        return
    
    if remove_from_blacklist(mint):
        bot.reply_to(message, f"✅ 已将 {mint} 从黑名单移除")
    else:
        bot.reply_to(message, f"❌ {mint} 不在黑名单中或移除失败")

def view_blacklist_handler(bot, chat_id, message_id=None):
    """查看黑名单"""
    blacklist = get_blacklist_list()
    if not blacklist:
        text = "🚫 黑名单为空"
    else:
        text = f"🚫 黑名单 (共{len(blacklist)}个):\n\n"
        for i, mint in enumerate(blacklist, 1):
            text += f"{i}. `{mint}`\n"
            if i >= 20:  # 限制显示数量
                text += f"\n... 还有 {len(blacklist) - 20} 个"
                break
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("⬅️ 返回黑名单菜单", callback_data="blacklist_menu"))
    
    if message_id:
        bot.edit_message_text(text, chat_id, message_id, reply_markup=markup, parse_mode='Markdown', disable_web_page_preview=True)
    else:
        bot.send_message(chat_id, text, reply_markup=markup, parse_mode='Markdown', disable_web_page_preview=True)

def ca1_handler(bot, message, token_address):
    """处理/ca1命令 - OKX大户分析"""
    token_address = token_address.strip()
    if not token_address:
        bot.reply_to(message, "❌ 请提供代币地址\n用法: /ca1 <token_address>")
        return
    
    if len(token_address) < 20:  # 简单验证地址长度
        bot.reply_to(message, "❌ 请输入有效的代币地址")
        return
    
    # 发送开始分析的消息
    processing_msg = bot.reply_to(message, f"🔍 正在分析代币大户持仓...\n代币地址: `{token_address}`\n⏳ 预计需要1-2分钟，请稍候...", parse_mode='Markdown')
    
    def run_analysis():
        try:
            # 清理过期缓存
            cleanup_expired_cache()
            
            # 创建OKX爬虫实例
            crawler = OKXCrawlerForBot()
            
            # 执行分析
            result = crawler.analyze_token_holders(token_address, top_holders_count=TOP_HOLDERS_COUNT)
            
            if result and result.get('token_statistics'):
                # 缓存分析结果
                cache_key = f"{processing_msg.chat.id}_{processing_msg.message_id}"
                analysis_cache[cache_key] = {
                    'result': result,
                    'token_address': token_address,
                    'timestamp': time.time()
                }
                
                print(f"缓存分析结果: cache_key={cache_key}")  # 调试日志
                
                # 格式化表格消息（默认按人数排序）
                table_msg, table_markup = format_tokens_table(
                    result['token_statistics'], 
                    max_tokens=30, 
                    sort_by='count',
                    cache_key=cache_key
                )
                
                # 添加分析信息
                analysis_info = f"\n📊 <b>分析统计</b>\n"
                analysis_info += f"🕒 分析时间: {result.get('analysis_time', '').split('T')[0]}\n"
                analysis_info += f"👥 分析地址: 前{result.get('total_holders_analyzed', 0)} 个\n"
                target_holders = result.get('target_token_actual_holders', 0)
                if target_holders > 0:
                    analysis_info += f"🎯 实际持有目标代币: {target_holders} 人\n"
                analysis_info += f"📈 统计范围: 每个地址的前10大持仓\n"
                
                final_msg = table_msg + analysis_info
                
                # 创建完整的按钮布局
                if table_markup:
                    # 添加排序切换按钮到现有的按钮布局
                    table_markup.add(
                        types.InlineKeyboardButton("💰 按价值排序", callback_data=f"ca1_sort_value_{cache_key}"),
                        types.InlineKeyboardButton("👥 按人数排序 ✅", callback_data=f"ca1_sort_count_{cache_key}")
                    )
                    # 添加集群分析按钮
                    table_markup.add(
                        types.InlineKeyboardButton("🎯 地址集群分析", callback_data=f"ca1_cluster_{cache_key}")
                    )
                    markup = table_markup
                else:
                    # 如果没有代币详情按钮，只添加排序和集群按钮
                    markup = types.InlineKeyboardMarkup(row_width=2)
                    markup.add(
                        types.InlineKeyboardButton("💰 按价值排序", callback_data=f"ca1_sort_value_{cache_key}"),
                        types.InlineKeyboardButton("👥 按人数排序 ✅", callback_data=f"ca1_sort_count_{cache_key}")
                    )
                    markup.add(
                        types.InlineKeyboardButton("🎯 地址集群分析", callback_data=f"ca1_cluster_{cache_key}")
                    )
                
                # 更新消息
                bot.edit_message_text(final_msg, processing_msg.chat.id, processing_msg.message_id, parse_mode='HTML', reply_markup=markup, disable_web_page_preview=True)
            else:
                bot.edit_message_text(
                    f"❌ 分析失败\n代币地址: `{token_address}`\n\n可能原因:\n• 代币地址无效\n• 网络连接问题\n• API限制\n\n详细日志请查看 okx_log/ 目录", 
                    processing_msg.chat.id, 
                    processing_msg.message_id, 
                    parse_mode='Markdown'
                )
                
        except Exception as e:
            bot.edit_message_text(
                f"❌ 分析过程中发生错误\n代币地址: `{token_address}`\n错误信息: {str(e)}\n\n详细日志请查看 okx_log/ 目录", 
                processing_msg.chat.id, 
                processing_msg.message_id, 
                parse_mode='Markdown'
            )
    
    # 在后台线程中运行分析，避免阻塞Bot
    thread = threading.Thread(target=run_analysis, daemon=True)
    thread.start()

def handle_ca1_sort_callback(bot, call, sort_by, cache_key):
    """处理排序切换回调"""
    try:
        # 从缓存中获取分析结果
        if cache_key not in analysis_cache:
            # 提供重新分析选项
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🔄 重新分析", callback_data=f"ca1_reanalyze_{cache_key}"))
            bot.edit_message_text(
                "❌ 数据已过期或丢失\n\n请点击下方按钮重新分析，或重新运行 /ca1 命令",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=markup
            )
            bot.answer_callback_query(call.id, "❌ 数据已过期，请重新分析")
            return
        
        cached_data = analysis_cache[cache_key]
        result = cached_data['result']
        token_address = cached_data['token_address']
        
        # 检查缓存是否过期（24小时）
        if time.time() - cached_data['timestamp'] > 24 * 3600:
            # 提供重新分析选项
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🔄 重新分析", callback_data=f"ca1_reanalyze_{token_address}"))
            bot.edit_message_text(
                f"❌ 数据已过期（超过24小时）\n代币: <code>{token_address}</code>\n\n请点击下方按钮重新分析，或重新运行 /ca1 命令",
                call.message.chat.id,
                call.message.message_id,
                parse_mode='HTML',
                reply_markup=markup,
                disable_web_page_preview=True
            )
            bot.answer_callback_query(call.id, "❌ 数据已过期，请重新分析")
            return
        
        # 重新格式化表格
        table_msg, table_markup = format_tokens_table(
            result['token_statistics'], 
            max_tokens=30, 
            sort_by=sort_by,
            cache_key=cache_key
        )
        
        if not table_msg:
            bot.answer_callback_query(call.id, "❌ 无法生成代币表格")
            return
        
        # 添加分析信息
        analysis_info = f"\n📊 <b>分析统计</b>\n"
        analysis_info += f"🕒 分析时间: {result.get('analysis_time', '').split('T')[0]}\n"
        analysis_info += f"👥 分析地址: 前{result.get('total_holders_analyzed', 0)} 个\n"
        analysis_info += f"🎯 每个地址命中持仓前10的代币\n"
        
        final_msg = table_msg + analysis_info
        
        # 创建完整的按钮布局
        if table_markup:
            # 添加排序切换按钮到现有的按钮布局
            if sort_by == 'value':
                table_markup.add(
                    types.InlineKeyboardButton("💰 按价值排序 ✅", callback_data=f"ca1_sort_value_{cache_key}"),
                    types.InlineKeyboardButton("👥 按人数排序", callback_data=f"ca1_sort_count_{cache_key}")
                )
            else:
                table_markup.add(
                    types.InlineKeyboardButton("💰 按价值排序", callback_data=f"ca1_sort_value_{cache_key}"),
                    types.InlineKeyboardButton("👥 按人数排序 ✅", callback_data=f"ca1_sort_count_{cache_key}")
                )
            # 添加集群分析按钮
            table_markup.add(
                types.InlineKeyboardButton("🎯 地址集群分析", callback_data=f"ca1_cluster_{cache_key}")
            )
            markup = table_markup
        else:
            # 如果没有代币详情按钮，只添加排序和集群按钮
            markup = types.InlineKeyboardMarkup(row_width=2)
            if sort_by == 'value':
                markup.add(
                    types.InlineKeyboardButton("💰 按价值排序 ✅", callback_data=f"ca1_sort_value_{cache_key}"),
                    types.InlineKeyboardButton("👥 按人数排序", callback_data=f"ca1_sort_count_{cache_key}")
                )
            else:
                markup.add(
                    types.InlineKeyboardButton("💰 按价值排序", callback_data=f"ca1_sort_value_{cache_key}"),
                    types.InlineKeyboardButton("👥 按人数排序 ✅", callback_data=f"ca1_sort_count_{cache_key}")
                )
            markup.add(
                types.InlineKeyboardButton("🎯 地址集群分析", callback_data=f"ca1_cluster_{cache_key}")
            )
        
        # 更新消息
        bot.edit_message_text(final_msg, call.message.chat.id, call.message.message_id, parse_mode='HTML', reply_markup=markup, disable_web_page_preview=True)
        bot.answer_callback_query(call.id, f"已切换到{'价值' if sort_by == 'value' else '人数'}排序")
        
    except Exception as e:
        print(f"排序切换错误: {str(e)}")  # 添加调试日志
        bot.answer_callback_query(call.id, f"❌ 切换排序失败: {str(e)}")

def handle_token_detail_callback(bot, call, cache_key, token_index, current_sort='value'):
    """处理代币详情查看回调"""
    try:
        # 从缓存中获取分析结果
        if cache_key not in analysis_cache:
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🔄 重新分析", callback_data=f"ca1_reanalyze_{cache_key}"))
            bot.edit_message_text(
                "❌ 数据已过期或丢失\n\n请点击下方按钮重新分析，或重新运行 /ca1 命令",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=markup
            )
            bot.answer_callback_query(call.id, "❌ 数据已过期")
            return
        
        cached_data = analysis_cache[cache_key]
        result = cached_data['result']
        token_address = cached_data['token_address']
        
        # 检查缓存是否过期（24小时）
        if time.time() - cached_data['timestamp'] > 24 * 3600:
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🔄 重新分析", callback_data=f"ca1_reanalyze_{token_address}"))
            bot.edit_message_text(
                f"❌ 数据已过期（超过24小时）\n代币: <code>{token_address}</code>\n\n请点击下方按钮重新分析，或重新运行 /ca1 命令",
                call.message.chat.id,
                call.message.message_id,
                parse_mode='HTML',
                reply_markup=markup,
                disable_web_page_preview=True
            )
            bot.answer_callback_query(call.id, "❌ 数据已过期")
            return
        
        # 获取代币统计数据
        token_stats = result.get('token_statistics', {})
        all_tokens = token_stats.get('top_tokens_by_value', [])
        
        if not all_tokens:
            bot.answer_callback_query(call.id, "❌ 未找到代币数据")
            return
        
        # 验证索引
        try:
            token_index = int(token_index)
            if token_index < 0 or token_index >= len(all_tokens):
                bot.answer_callback_query(call.id, f"❌ 代币索引无效 (索引: {token_index}, 总数: {len(all_tokens)})")
                return
        except ValueError:
            bot.answer_callback_query(call.id, "❌ 代币索引格式错误")
            return
        
        # 根据当前排序方式获取正确的代币
        if current_sort == 'count':
            sorted_tokens = sorted(all_tokens, key=lambda x: x['holder_count'], reverse=True)
        else:
            sorted_tokens = sorted(all_tokens, key=lambda x: x['total_value'], reverse=True)
        
        # 获取指定索引的代币信息
        if token_index >= len(sorted_tokens):
            bot.answer_callback_query(call.id, f"❌ 排序后索引无效 (索引: {token_index}, 排序后总数: {len(sorted_tokens)})")
            return
            
        token_info = sorted_tokens[token_index]
        
        # 格式化详情消息
        detail_msg = format_token_holders_detail(token_info, token_stats)
        
        # 创建返回按钮，保持当前排序方式
        markup = types.InlineKeyboardMarkup()
        return_callback = f"ca1_sort_{current_sort}_{cache_key}"
        markup.add(types.InlineKeyboardButton("⬅️ 返回排行榜", callback_data=return_callback))
        
        # 发送详情消息
        bot.edit_message_text(detail_msg, call.message.chat.id, call.message.message_id, parse_mode='HTML', reply_markup=markup, disable_web_page_preview=True)
        bot.answer_callback_query(call.id, f"已显示 {token_info['symbol']} 大户详情")
        
    except Exception as e:
        print(f"代币详情回调错误: cache_key={cache_key}, token_index={token_index}, error={str(e)}")  # 添加调试日志
        bot.answer_callback_query(call.id, f"❌ 获取代币详情失败: {str(e)}")

def handle_ca1_cluster_callback(bot, call, cache_key):
    """处理地址集群分析回调"""
    try:
        # 从缓存中获取分析结果
        if cache_key not in analysis_cache:
            bot.answer_callback_query(call.id, "❌ 数据缓存已失效，请重新运行 /ca1 命令")
            return
        
        cached_data = analysis_cache[cache_key]
        result = cached_data['result']
        token_address = cached_data['token_address']
        
        # 检查缓存是否过期
        if time.time() - cached_data['timestamp'] > 24 * 3600:
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🔄 重新分析", callback_data=f"ca1_reanalyze_{token_address}"))
            bot.edit_message_text(
                f"❌ 数据已过期（超过24小时）\n代币: <code>{token_address}</code>\n\n请点击下方按钮重新分析，或重新运行 /ca1 命令",
                call.message.chat.id,
                call.message.message_id,
                parse_mode='HTML',
                reply_markup=markup,
                disable_web_page_preview=True
            )
            bot.answer_callback_query(call.id, "❌ 数据已过期，请重新分析")
            return
        
        # 显示正在分析的消息
        bot.edit_message_text(
            f"🎯 正在进行地址集群分析...\n代币: <code>{token_address}</code>\n⏳ 分析大户间的共同投资模式...",
            call.message.chat.id,
            call.message.message_id,
            parse_mode='HTML'
        )
        
        def run_cluster_analysis():
            try:
                # 执行集群分析
                cluster_result = analyze_address_clusters(result)
                
                # 格式化集群分析结果
                cluster_msg = format_cluster_analysis(cluster_result, max_clusters=3)
                
                # 创建返回按钮
                markup = types.InlineKeyboardMarkup()
                markup.add(
                    types.InlineKeyboardButton("⬅️ 返回代币排行", callback_data=f"ca1_sort_count_{cache_key}"),
                    types.InlineKeyboardButton("🔄 重新运行", callback_data=f"ca1_cluster_{cache_key}")
                )
                
                # 更新消息
                bot.edit_message_text(
                    cluster_msg, 
                    call.message.chat.id, 
                    call.message.message_id, 
                    parse_mode='HTML', 
                    reply_markup=markup, 
                    disable_web_page_preview=True
                )
                
            except Exception as e:
                error_msg = f"❌ 集群分析失败\n代币: <code>{token_address}</code>\n错误: {str(e)}\n\n"
                error_msg += f"💡 可能原因:\n• 数据不足以形成集群\n• 地址数据处理错误\n• 配置参数过于严格"
                
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton("⬅️ 返回代币排行", callback_data=f"ca1_sort_count_{cache_key}"))
                
                bot.edit_message_text(
                    error_msg,
                    call.message.chat.id,
                    call.message.message_id,
                    parse_mode='HTML',
                    reply_markup=markup
                )
        
        # 在后台线程中运行集群分析
        thread = threading.Thread(target=run_cluster_analysis, daemon=True)
        thread.start()
        
        bot.answer_callback_query(call.id, "🎯 开始集群分析...")
        
    except Exception as e:
        print(f"集群分析回调错误: cache_key={cache_key}, error={str(e)}")
        bot.answer_callback_query(call.id, f"❌ 启动集群分析失败: {str(e)}")


def handle_ca1_reanalyze_callback(bot, call, token_address):
    """处理重新分析回调"""
    try:
        # 显示重新分析开始的消息
        bot.edit_message_text(
            f"🔄 正在重新分析代币大户持仓...\n代币地址: `{token_address}`\n⏳ 预计需要1-2分钟，请稍候...",
            call.message.chat.id,
            call.message.message_id,
            parse_mode='Markdown'
        )
        
        def run_reanalysis():
            try:
                # 创建OKX爬虫实例
                crawler = OKXCrawlerForBot()
                
                # 执行分析
                result = crawler.analyze_token_holders(token_address, top_holders_count=TOP_HOLDERS_COUNT)
                
                if result and result.get('token_statistics'):
                    # 更新缓存
                    cache_key = f"{call.message.chat.id}_{call.message.message_id}"
                    analysis_cache[cache_key] = {
                        'result': result,
                        'token_address': token_address,
                        'timestamp': time.time()
                    }
                    
                    # 格式化表格消息（默认按人数排序）
                    table_msg, table_markup = format_tokens_table(
                        result['token_statistics'], 
                        max_tokens=30, 
                        sort_by='count',
                        cache_key=cache_key
                    )
                    
                    # 添加分析信息
                    analysis_info = f"\n📊 <b>分析统计</b>\n"
                    analysis_info += f"🕒 分析时间: {result.get('analysis_time', '').split('T')[0]}\n"
                    analysis_info += f"👥 分析地址: 前{result.get('total_holders_analyzed', 0)} 个\n"
                    analysis_info += f"🎯 每个地址命中持仓前10的代币\n"
                    
                    final_msg = table_msg + analysis_info
                    
                    # 创建按钮布局
                    if table_markup:
                        table_markup.add(
                            types.InlineKeyboardButton("💰 按价值排序", callback_data=f"ca1_sort_value_{cache_key}"),
                            types.InlineKeyboardButton("👥 按人数排序 ✅", callback_data=f"ca1_sort_count_{cache_key}")
                        )
                        markup = table_markup
                    else:
                        markup = types.InlineKeyboardMarkup(row_width=2)
                        markup.add(
                            types.InlineKeyboardButton("💰 按价值排序", callback_data=f"ca1_sort_value_{cache_key}"),
                            types.InlineKeyboardButton("👥 按人数排序 ✅", callback_data=f"ca1_sort_count_{cache_key}")
                        )
                    
                    # 更新消息
                    bot.edit_message_text(final_msg, call.message.chat.id, call.message.message_id, parse_mode='HTML', reply_markup=markup, disable_web_page_preview=True)
                else:
                    bot.edit_message_text(
                        f"❌ 重新分析失败\n代币地址: `{token_address}`\n\n可能原因:\n• 代币地址无效\n• 网络连接问题\n• API限制",
                        call.message.chat.id,
                        call.message.message_id,
                        parse_mode='Markdown'
                    )
                    
            except Exception as e:
                bot.edit_message_text(
                    f"❌ 重新分析过程中发生错误\n代币地址: `{token_address}`\n错误信息: {str(e)}",
                    call.message.chat.id,
                    call.message.message_id,
                    parse_mode='Markdown'
                )
        
        # 在后台线程中运行重新分析
        thread = threading.Thread(target=run_reanalysis, daemon=True)
        thread.start()
        
        bot.answer_callback_query(call.id, "开始重新分析...")
        
    except Exception as e:
        bot.answer_callback_query(call.id, f"❌ 启动重新分析失败: {str(e)}")


def register_handlers(bot):
    @bot.message_handler(commands=['start', 'help'])
    def send_welcome(message):
        send_welcome_impl(bot, message)

    @bot.message_handler(commands=['config'])
    def config_handler(message):
        update_config_impl(bot, message)

    @bot.callback_query_handler(func=lambda call: call.data.startswith('edit_'))
    def handle_edit_config(call):
        key = call.data.replace('edit_', '')
        msg = bot.send_message(call.message.chat.id, f"请输入新的 {key} 值：")
        bot.register_next_step_handler(msg, lambda m: save_config_value_impl(bot, m, key))

    @bot.callback_query_handler(func=lambda call: call.data == 'blacklist_menu')
    def handle_blacklist_menu(call):
        show_blacklist_menu(bot, call.message)

    @bot.callback_query_handler(func=lambda call: call.data == 'add_blacklist')
    def handle_add_blacklist(call):
        msg = bot.send_message(call.message.chat.id, "请输入要添加到黑名单的CA：")
        bot.register_next_step_handler(msg, lambda m: add_blacklist_handler(bot, m, m.text))

    @bot.callback_query_handler(func=lambda call: call.data == 'remove_blacklist')
    def handle_remove_blacklist(call):
        msg = bot.send_message(call.message.chat.id, "请输入要从黑名单移除的CA：")
        bot.register_next_step_handler(msg, lambda m: remove_blacklist_handler(bot, m, m.text))

    @bot.callback_query_handler(func=lambda call: call.data == 'view_blacklist')
    def handle_view_blacklist(call):
        view_blacklist_handler(bot, call.message.chat.id, call.message.message_id)

    @bot.callback_query_handler(func=lambda call: call.data == 'back_to_config')
    def handle_back_to_config(call):
        # 重新显示配置菜单
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton(f"INTERVAL: {INTERVAL}", callback_data="edit_INTERVAL"),
            types.InlineKeyboardButton(f"THRESHOLD: {THRESHOLD}", callback_data="edit_THRESHOLD"),
            types.InlineKeyboardButton(f"MIN_MARKET_CAP: {MIN_MARKET_CAP}", callback_data="edit_MIN_MARKET_CAP"),
            types.InlineKeyboardButton(f"MIN_AGE_DAYS: {MIN_AGE_DAYS}", callback_data="edit_MIN_AGE_DAYS")
        )
        markup.add(
            types.InlineKeyboardButton(f"TOP_HOLDERS_COUNT: {TOP_HOLDERS_COUNT}", callback_data="edit_TOP_HOLDERS_COUNT"),
            types.InlineKeyboardButton(f"RANKING_SIZE: {RANKING_SIZE}", callback_data="edit_RANKING_SIZE")
        )
        markup.add(
            types.InlineKeyboardButton(f"DETAIL_BUTTONS: {DETAIL_BUTTONS_COUNT}", callback_data="edit_DETAIL_BUTTONS_COUNT")
        )
        markup.add(
            types.InlineKeyboardButton(f"🚫 黑名单管理 ({get_blacklist_count()})", callback_data="blacklist_menu")
        )
        bot.edit_message_text("请选择要更改的配置项：", call.message.chat.id, call.message.message_id, reply_markup=markup)

    @bot.message_handler(commands=['topicid'])
    def send_topic_id(message):
        topic_id = getattr(message, 'message_thread_id', None)
        bot.reply_to(message, f"本 topic 的 ID 是: {topic_id}")

    @bot.message_handler(commands=['ca1'])
    def handle_ca1(message):
        # 提取代币地址参数
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            bot.reply_to(message, "❌ 请提供代币地址\n用法: /ca1 <token_address>")
            return
        
        token_address = parts[1]
        ca1_handler(bot, message, token_address)

    # 处理排序切换回调
    @bot.callback_query_handler(func=lambda call: call.data.startswith('ca1_sort_'))
    def handle_ca1_sort(call):
        try:
            # 解析回调数据: ca1_sort_{sort_by}_{cache_key}
            # 使用更安全的解析方式
            callback_data = call.data[len('ca1_sort_'):]  # 移除前缀
            parts = callback_data.split('_', 1)  # 只分割一次，避免cache_key被错误分割
            
            if len(parts) >= 2:
                sort_by = parts[0]  # 'value' 或 'count'
                cache_key = parts[1]  # cache_key (可能包含下划线)
                print(f"排序回调: sort_by={sort_by}, cache_key={cache_key}")  # 调试日志
                handle_ca1_sort_callback(bot, call, sort_by, cache_key)
            else:
                print(f"排序回调数据格式错误: {call.data}")  # 调试日志
                bot.answer_callback_query(call.id, "❌ 回调数据格式错误")
        except Exception as e:
            print(f"排序回调处理错误: {str(e)}")  # 调试日志
            bot.answer_callback_query(call.id, f"❌ 处理回调失败: {str(e)}")

    # 处理地址集群分析回调
    @bot.callback_query_handler(func=lambda call: call.data.startswith('ca1_cluster_'))
    def handle_ca1_cluster(call):
        try:
            # 解析回调数据: ca1_cluster_{cache_key}
            cache_key = call.data[len('ca1_cluster_'):]  # 移除前缀获取cache_key
            print(f"集群分析回调: cache_key={cache_key}")  # 调试日志
            handle_ca1_cluster_callback(bot, call, cache_key)
        except Exception as e:
            print(f"集群分析回调处理错误: {str(e)}")  # 调试日志
            bot.answer_callback_query(call.id, f"❌ 处理集群分析失败: {str(e)}")

    # 处理代币详情查看回调
    @bot.callback_query_handler(func=lambda call: call.data.startswith('token_detail_'))
    def handle_token_detail(call):
        try:
            # 解析回调数据: token_detail_{cache_key}_{token_index}_{sort_by}
            # 使用更安全的解析方式，从右边分割
            callback_data = call.data[len('token_detail_'):]  # 移除前缀
            parts = callback_data.rsplit('_', 2)  # 从右边分割，最多分割2次
            
            print(f"代币详情回调数据: {call.data}")  # 调试日志
            print(f"解析结果: parts={parts}")  # 调试日志
            
            if len(parts) >= 3:
                cache_key = parts[0]  # cache_key (可能包含下划线)
                token_index = parts[1]  # token_index
                current_sort = parts[2]  # current_sort (value 或 count)
                print(f"详情回调: cache_key={cache_key}, token_index={token_index}, sort={current_sort}")  # 调试日志
                handle_token_detail_callback(bot, call, cache_key, token_index, current_sort)
            elif len(parts) >= 2:
                # 兼容旧格式，默认按人数排序
                cache_key = parts[0]
                token_index = parts[1]
                print(f"详情回调(兼容): cache_key={cache_key}, token_index={token_index}")  # 调试日志
                handle_token_detail_callback(bot, call, cache_key, token_index, 'count')
            else:
                print(f"详情回调数据格式错误: {call.data}")  # 调试日志
                bot.answer_callback_query(call.id, "❌ 回调数据格式错误")
        except Exception as e:
            print(f"详情回调处理错误: {str(e)}")  # 调试日志
            bot.answer_callback_query(call.id, f"❌ 处理详情回调失败: {str(e)}")



    # 处理重新分析回调
    @bot.callback_query_handler(func=lambda call: call.data.startswith('ca1_reanalyze_'))
    def handle_ca1_reanalyze(call):
        try:
            # 解析回调数据: ca1_reanalyze_{token_address}
            token_address = call.data[len('ca1_reanalyze_'):]
            print(f"重新分析回调: token_address={token_address}")  # 调试日志
            
            if not token_address:
                bot.answer_callback_query(call.id, "❌ 代币地址无效")
                return
                
            handle_ca1_reanalyze_callback(bot, call, token_address)
        except Exception as e:
            print(f"重新分析回调处理错误: {str(e)}")  # 调试日志
            bot.answer_callback_query(call.id, f"❌ 重新分析失败: {str(e)}")
