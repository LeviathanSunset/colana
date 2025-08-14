import os
# 设置 Clash 代理（如有需要可修改端口）
os.environ["HTTP_PROXY"] = "http://127.0.0.1:10808"
os.environ["HTTPS_PROXY"] = "http://127.0.0.1:10808"

import telebot
import time
import importlib
import shutil
import csv
import os
from crawler import PumpFunAPICrawler
import config
import threading
from utils import timestamp_to_date
import datetime
from blacklist import is_blacklisted

from config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, INTERVAL, THRESHOLD, MIN_MARKET_CAP, MIN_AGE_DAYS
from handlers import register_handlers

bot = telebot.TeleBot(TELEGRAM_TOKEN)

def reload_config():
    importlib.reload(config)
    return config.TELEGRAM_TOKEN, config.TELEGRAM_CHAT_ID, config.INTERVAL, config.THRESHOLD, config.MIN_MARKET_CAP, config.MIN_AGE_DAYS

def compare_and_filter(pre_path, now_path, threshold, min_market_cap, min_age_days):
    # 读取csv为dict，key为mint
    def read_csv(path):
        data = {}
        with open(path, encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                data[row.get('mint')] = row
        return data
    pre = read_csv(pre_path)
    now = read_csv(now_path)
    up_results = []
    for mint, now_row in now.items():
        pre_row = pre.get(mint)
        if not pre_row:
            continue
        
        # 检查是否在黑名单中
        if is_blacklisted(mint):
            continue
            
        try:
            pre_cap = float(pre_row.get('usd_market_cap', 0))
            now_cap = float(now_row.get('usd_market_cap', 0))
            if pre_cap <= 0:
                continue
            change = (now_cap - pre_cap) / pre_cap
            age_days = (float(now_row.get('created_timestamp', 0)) or 0)
            age_days = (time.time()*1000 - float(now_row.get('created_timestamp', 0)))/1000/60/60/24 if now_row.get('created_timestamp') else 0
            if change >= threshold and now_cap >= min_market_cap and age_days >= min_age_days:
                up_results.append({
                    'name': now_row.get('name', ''),
                    'mint': mint,
                    'change': change,
                    'usd_market_cap': now_cap,
                    'created_timestamp': now_row.get('created_timestamp', ''),
                    'age_days': age_days
                })
        except Exception:
            continue
    return up_results

def format_number(x):
    try:
        x = float(x)
        if abs(x) >= 1_000_000_000:
            return f"{x/1_000_000_000:.2f}B"
        elif abs(x) >= 1_000_000:
            return f"{x/1_000_000:.2f}M"
        elif abs(x) >= 1_000:
            return f"{x/1_000:.2f}K"
        else:
            return f"{x:,.2f}"
    except Exception:
        return str(x)

def format_message(results, mins=None, old_ts=None, new_ts=None, page=0, pages=1):
    if not results:
        return '无符合条件的币种。'
    msg = f'<b>近{mins}分钟</b> 涨幅预警 第{page+1}/{pages}页:\n快照: {old_ts} → {new_ts}' if mins and old_ts and new_ts else ''
    for r in results:
        link = f"https://gmgn.ai/sol/token/{r['mint']}"
        # 格式化创建日期
        created_date = ''
        if r.get('created_timestamp'):
            try:
                created_timestamp = float(r['created_timestamp']) / 1000  # 转换为秒
                created_date = datetime.datetime.fromtimestamp(created_timestamp).strftime('%Y-%m-%d')
            except:
                created_date = '未知'
        else:
            created_date = '未知'
        
        msg += f"\n<b>{r['name']}</b> <a href='{link}'>gmgn</a> 涨幅: <b>{r['change']*100:.1f}%</b>  (${format_number(r['usd_market_cap']/(1+r['change']))}→${format_number(r['usd_market_cap'])}) 创建: {created_date}"
    return msg

def crawler_loop():
    while True:
        try:
            TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, INTERVAL, THRESHOLD, MIN_MARKET_CAP, MIN_AGE_DAYS = reload_config()
            crawler = PumpFunAPICrawler()
            crawler.crawl_all_pages(max_tokens=1000)
            crawler.deduplicate_by_mint(keep=1000)
            now_path = 'now.csv'
            crawler.save_to_csv(now_path)
            pre_path = 'pre.csv'
            if not os.path.exists(pre_path):
                shutil.copy(now_path, pre_path)
            else:
                up_results = compare_and_filter(pre_path, now_path, THRESHOLD, MIN_MARKET_CAP, MIN_AGE_DAYS)
                # 获取快照时间戳
                old_ts = datetime.datetime.fromtimestamp(os.path.getmtime(pre_path)).strftime('%Y-%m-%d %H:%M:%S')
                new_ts = datetime.datetime.fromtimestamp(os.path.getmtime(now_path)).strftime('%Y-%m-%d %H:%M:%S')
                mins = int((os.path.getmtime(now_path) - os.path.getmtime(pre_path)) / 60)
                # 分页，每页10个币
                page_size = 10
                total_up = len(up_results)
                pages_up = (total_up + page_size - 1) // page_size
                max_pages = 5
                if pages_up > max_pages:
                    bot.send_message(TELEGRAM_CHAT_ID, f'⚠️ 检测到{total_up}个涨幅币种（共{pages_up}页），为避免刷屏，仅显示前{max_pages}页（{max_pages*page_size}个币种）', parse_mode='HTML', message_thread_id=40517, disable_web_page_preview=True)
                    pages_up = max_pages
                for page in range(pages_up):
                    try:
                        page_results = up_results[page*page_size:(page+1)*page_size]
                        msg = format_message(page_results, mins=mins, old_ts=old_ts, new_ts=new_ts, page=page, pages=pages_up)
                        bot.send_message(TELEGRAM_CHAT_ID, msg, parse_mode='HTML', disable_web_page_preview=True, message_thread_id=40517)
                        if page < pages_up - 1:
                            time.sleep(1.2)
                    except Exception as send_error:
                        print(f"[ERROR] Failed to send up page {page+1}: {send_error}")
                        time.sleep(3)
                shutil.copy(now_path, pre_path)
            time.sleep(INTERVAL)
        except Exception as e:
            print(f"[ERROR] Bot polling error: {e}. Restarting in 3 seconds...")
            time.sleep(3)

@bot.message_handler(commands=['testtopic'])
def test_topic_handler(message):
    bot.send_message(TELEGRAM_CHAT_ID, "测试消息已发送到40517 topic!", message_thread_id=40517)

if __name__ == "__main__":
    print("Bot is polling...")
    register_handlers(bot)
    t = threading.Thread(target=crawler_loop, daemon=True)
    t.start()
    while True:
        try:
            bot.polling(none_stop=True, interval=3, timeout=30)
        except Exception as e:
            print(f"[ERROR] Polling error: {e}. Reconnecting in 3 seconds...")
            time.sleep(3)