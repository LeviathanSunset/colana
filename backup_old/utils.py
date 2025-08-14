from datetime import datetime
import os

def format_number(x):
    """Format numbers with commas and K/M/B suffixes for large values"""
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

def timestamp_to_date(ts, with_time=False):
    """将时间戳（秒或毫秒）转为日期字符串。with_time=True时带时分秒"""
    try:
        ts = float(ts)
        if ts > 1e12:
            dt = datetime.fromtimestamp(ts / 1000)
        else:
            dt = datetime.fromtimestamp(ts)
        return dt.strftime('%Y-%m-%d %H:%M:%S' if with_time else '%Y-%m-%d')
    except Exception:
        return str(ts)

def parse_snapshot_filename(fname):
    """从快照文件名中提取时间字符串（如20250607_120133）"""
    import re
    match = re.search(r'pumpfun_tokens_api_(\d{8}_\d{6})\.csv', fname)
    if match:
        return match.group(1)
    return None

def get_all_snapshots(snapshots_dir, n=None):
    """获取快照文件列表，按时间倒序，可选n限制数量，返回完整路径"""
    files = [f for f in os.listdir(snapshots_dir) if f.startswith('pumpfun_tokens_api_') and f.endswith('.csv')]
    files = sorted(files, reverse=True)
    if n:
        files = files[:n]
    # 返回完整路径
    return [os.path.join(snapshots_dir, f) for f in files]
