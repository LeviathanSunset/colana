import os
import json

BLACKLIST_FILE = 'blacklist.json'

def load_blacklist():
    """加载黑名单"""
    if not os.path.exists(BLACKLIST_FILE):
        return set()
    try:
        with open(BLACKLIST_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return set(data.get('mints', []))
    except Exception:
        return set()

def save_blacklist(blacklist_set):
    """保存黑名单"""
    try:
        with open(BLACKLIST_FILE, 'w', encoding='utf-8') as f:
            json.dump({'mints': list(blacklist_set)}, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False

def add_to_blacklist(mint):
    """添加mint到黑名单"""
    blacklist = load_blacklist()
    blacklist.add(mint)
    return save_blacklist(blacklist)

def remove_from_blacklist(mint):
    """从黑名单移除mint"""
    blacklist = load_blacklist()
    if mint in blacklist:
        blacklist.remove(mint)
        return save_blacklist(blacklist)
    return False

def is_blacklisted(mint):
    """检查mint是否在黑名单中"""
    blacklist = load_blacklist()
    return mint in blacklist

def get_blacklist_count():
    """获取黑名单数量"""
    blacklist = load_blacklist()
    return len(blacklist)

def get_blacklist_list():
    """获取黑名单列表"""
    return list(load_blacklist())
