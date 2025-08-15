"""
黑名单管理服务
"""

import json
import os
from typing import List, Set
from threading import Lock


class BlacklistManager:
    """黑名单管理器"""

    def __init__(self, blacklist_file: str = "blacklist.json"):
        self.blacklist_file = blacklist_file
        self._blacklist: Set[str] = set()
        self._lock = Lock()
        self.load_blacklist()

    def load_blacklist(self) -> None:
        """加载黑名单"""
        try:
            if os.path.exists(self.blacklist_file):
                with open(self.blacklist_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._blacklist = set(data.get("blacklist", []))
            else:
                self._blacklist = set()
        except Exception as e:
            print(f"加载黑名单失败: {e}")
            self._blacklist = set()

    def save_blacklist(self) -> None:
        """保存黑名单"""
        try:
            with self._lock:
                with open(self.blacklist_file, "w", encoding="utf-8") as f:
                    json.dump({"blacklist": list(self._blacklist)}, f, indent=2)
        except Exception as e:
            print(f"保存黑名单失败: {e}")

    def add_to_blacklist(self, mint: str) -> bool:
        """
        添加到黑名单

        Args:
            mint: 代币地址

        Returns:
            是否添加成功
        """
        try:
            with self._lock:
                if mint not in self._blacklist:
                    self._blacklist.add(mint)
                    self.save_blacklist()
                    return True
                return False
        except Exception as e:
            print(f"添加黑名单失败: {e}")
            return False

    def remove_from_blacklist(self, mint: str) -> bool:
        """
        从黑名单移除

        Args:
            mint: 代币地址

        Returns:
            是否移除成功
        """
        try:
            with self._lock:
                if mint in self._blacklist:
                    self._blacklist.remove(mint)
                    self.save_blacklist()
                    return True
                return False
        except Exception as e:
            print(f"移除黑名单失败: {e}")
            return False

    def is_blacklisted(self, mint: str) -> bool:
        """
        检查是否在黑名单中

        Args:
            mint: 代币地址

        Returns:
            是否在黑名单中
        """
        return mint in self._blacklist

    def get_blacklist_count(self) -> int:
        """获取黑名单数量"""
        return len(self._blacklist)

    def get_blacklist_list(self) -> List[str]:
        """获取黑名单列表"""
        return list(self._blacklist)

    def clear_blacklist(self) -> None:
        """清空黑名单"""
        with self._lock:
            self._blacklist.clear()
            self.save_blacklist()


# 全局黑名单管理器实例
blacklist_manager = BlacklistManager()


def get_blacklist_manager() -> BlacklistManager:
    """获取黑名单管理器实例"""
    return blacklist_manager


# 向后兼容的函数
def is_blacklisted(mint: str) -> bool:
    """检查是否在黑名单中"""
    return blacklist_manager.is_blacklisted(mint)


def add_to_blacklist(mint: str) -> bool:
    """添加到黑名单"""
    return blacklist_manager.add_to_blacklist(mint)


def remove_from_blacklist(mint: str) -> bool:
    """从黑名单移除"""
    return blacklist_manager.remove_from_blacklist(mint)


def get_blacklist_count() -> int:
    """获取黑名单数量"""
    return blacklist_manager.get_blacklist_count()


def get_blacklist_list() -> List[str]:
    """获取黑名单列表"""
    return blacklist_manager.get_blacklist_list()
