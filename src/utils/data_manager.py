"""
数据文件管理模块
统一管理所有数据和日志文件，bot重启时清空所有数据
"""

import os
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Dict
from .logger import get_logger


class DataManager:
    """数据文件管理器"""
    
    def __init__(self, base_dir: str = "storage"):
        """
        初始化数据管理器
        
        Args:
            base_dir: 统一存储目录名称
        """
        self.logger = get_logger("data_manager")
        self.base_dir = Path(base_dir)
        
        
        # 基本目录结构
        self.subdirs = ["analysis", "holders", "jupiter", "logs", "csv_data", "config"]
        
        # 确保目录存在
        self.base_dir.mkdir(exist_ok=True)
        
        # 创建子目录
        for subdir in self.subdirs:
            (self.base_dir / subdir).mkdir(exist_ok=True)
    
    def clear_all_storage(self):
        """清空所有存储文件（保留目录结构）"""
        print("🗑️ 正在清空所有存储文件...")
        self.logger.info("开始清空所有存储文件")
        
        cleared_count = 0
        for subdir in self.subdirs:
            subdir_path = self.base_dir / subdir
            if subdir_path.exists():
                for file_path in subdir_path.iterdir():
                    if file_path.is_file() and not file_path.name.startswith('.'):
                        try:
                            file_path.unlink()
                            cleared_count += 1
                            self.logger.debug(f"删除文件: {file_path}")
                        except Exception as e:
                            self.logger.error(f"删除文件失败: {file_path} - {e}")
        
        print(f"✅ 清空完成，共删除 {cleared_count} 个文件")
        self.logger.info(f"清空完成，共删除 {cleared_count} 个文件")
    
    def get_file_path(self, file_type: str, filename: str) -> Path:
        """
        获取指定类型文件的完整路径
        
        Args:
            file_type: 文件类型 (analysis, holders, jupiter, logs, csv_data, config)
            filename: 文件名
            
        Returns:
            Path: 文件完整路径
        """
        if file_type not in self.subdirs:
            raise ValueError(f"不支持的文件类型: {file_type}")
        
        return self.base_dir / file_type / filename


# 全局数据管理器实例
data_manager = DataManager()


def get_data_manager() -> DataManager:
    """获取数据管理器实例"""
    return data_manager


def clear_all_storage():
    """清空所有存储文件"""
    data_manager.clear_all_storage()
