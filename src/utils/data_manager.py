"""
数据文件管理模块
统一管理所有数据和日志文件，包括自动清理功能
"""

import os
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Dict


class DataManager:
    """数据文件管理器"""
    
    def __init__(self, base_dir: str = "storage"):
        """
        初始化数据管理器
        
        Args:
            base_dir: 统一存储目录名称
        """
        self.base_dir = Path(base_dir)
        self.max_files = 50  # 最大文件数量
        
        # 文件类型配置
        self.file_types = {
            "analysis": {
                "pattern": "analysis_*.json",
                "description": "代币分析结果",
                "max_files": 20
            },
            "holders": {
                "pattern": "holders_raw_*.json", 
                "description": "持有者原始数据",
                "max_files": 15
            },
            "jupiter": {
                "pattern": "jupiter_tokens_*.json",
                "description": "Jupiter代币数据", 
                "max_files": 10
            },
            "logs": {
                "pattern": "okx_crawler_*.log",
                "description": "OKX爬虫日志",
                "max_files": 5
            },
            "csv_data": {
                "pattern": "*.csv",
                "description": "CSV数据文件",
                "max_files": 2  # 只保留now.csv和pre.csv
            },
            "config": {
                "pattern": "auto_pump_status.json",
                "description": "配置状态文件",
                "max_files": 1
            }
        }
        
        # 确保目录存在
        self.base_dir.mkdir(exist_ok=True)
        
        # 创建子目录
        for file_type in self.file_types.keys():
            (self.base_dir / file_type).mkdir(exist_ok=True)
    
    def migrate_existing_files(self):
        """迁移现有的data和okx_log目录中的文件"""
        print("🚀 开始迁移现有文件到统一存储目录...")
        
        migration_map = [
            # (源目录, 目标子目录, 文件模式)
            ("data", "csv_data", "*.csv"),
            ("data", "config", "auto_pump_status.json"),
            ("data/jupiter", "jupiter", "jupiter_tokens_*.json"),
            ("okx_log", "analysis", "analysis_*.json"),
            ("okx_log", "holders", "holders_raw_*.json"),
            ("okx_log", "logs", "okx_crawler_*.log"),
        ]
        
        migrated_count = 0
        for source_dir, target_subdir, pattern in migration_map:
            source_path = Path(source_dir)
            target_path = self.base_dir / target_subdir
            
            if source_path.exists():
                for file_path in source_path.glob(pattern):
                    if file_path.is_file():
                        target_file = target_path / file_path.name
                        try:
                            shutil.move(str(file_path), str(target_file))
                            print(f"  ✅ 迁移: {file_path} -> {target_file}")
                            migrated_count += 1
                        except Exception as e:
                            print(f"  ❌ 迁移失败: {file_path} - {e}")
        
        print(f"📦 迁移完成，共迁移 {migrated_count} 个文件")
        
        # 清理空目录
        self._cleanup_empty_dirs()
    
    def _cleanup_empty_dirs(self):
        """清理空目录"""
        dirs_to_check = ["data/jupiter", "data", "okx_log"]
        for dir_path in dirs_to_check:
            path = Path(dir_path)
            if path.exists() and path.is_dir():
                try:
                    if not any(path.iterdir()):  # 目录为空
                        path.rmdir()
                        print(f"  🗑️ 清理空目录: {dir_path}")
                except Exception as e:
                    print(f"  ⚠️ 无法清理目录 {dir_path}: {e}")
    
    def get_file_path(self, file_type: str, filename: str) -> Path:
        """
        获取指定类型文件的完整路径
        
        Args:
            file_type: 文件类型 (analysis, holders, jupiter, logs, csv_data, config)
            filename: 文件名
            
        Returns:
            Path: 文件完整路径
        """
        if file_type not in self.file_types:
            raise ValueError(f"不支持的文件类型: {file_type}")
        
        return self.base_dir / file_type / filename
    
    def cleanup_old_files(self, file_type: str = None):
        """
        清理旧文件
        
        Args:
            file_type: 指定清理的文件类型，None表示清理所有类型
        """
        if file_type:
            if file_type not in self.file_types:
                print(f"❌ 不支持的文件类型: {file_type}")
                return
            self._cleanup_by_type(file_type)
        else:
            for ftype in self.file_types.keys():
                self._cleanup_by_type(ftype)
    
    def _cleanup_by_type(self, file_type: str):
        """按类型清理文件"""
        config = self.file_types[file_type]
        type_dir = self.base_dir / file_type
        pattern = config["pattern"]
        max_files = config["max_files"]
        
        if not type_dir.exists():
            return
        
        # 获取所有匹配的文件
        files = list(type_dir.glob(pattern))
        if len(files) <= max_files:
            return
        
        # 按修改时间排序，最旧的在前
        files.sort(key=lambda x: x.stat().st_mtime)
        
        # 计算需要删除的文件数量
        files_to_delete = files[:len(files) - max_files]
        
        print(f"🗑️ 清理 {config['description']} 文件:")
        print(f"   总文件数: {len(files)}, 限制: {max_files}, 将删除: {len(files_to_delete)}")
        
        for file_path in files_to_delete:
            try:
                file_path.unlink()
                print(f"   ✅ 删除: {file_path.name}")
            except Exception as e:
                print(f"   ❌ 删除失败: {file_path.name} - {e}")
    
    def get_storage_info(self) -> Dict:
        """获取存储信息"""
        info = {
            "total_files": 0,
            "total_size_mb": 0,
            "by_type": {}
        }
        
        for file_type, config in self.file_types.items():
            type_dir = self.base_dir / file_type
            if not type_dir.exists():
                continue
            
            files = list(type_dir.glob(config["pattern"]))
            total_size = sum(f.stat().st_size for f in files if f.is_file())
            
            info["by_type"][file_type] = {
                "count": len(files),
                "size_mb": round(total_size / 1024 / 1024, 2),
                "description": config["description"],
                "max_files": config["max_files"]
            }
            
            info["total_files"] += len(files)
            info["total_size_mb"] += total_size
        
        info["total_size_mb"] = round(info["total_size_mb"] / 1024 / 1024, 2)
        return info
    
    def auto_cleanup_check(self):
        """自动检查并清理文件"""
        total_files = sum(
            len(list((self.base_dir / file_type).glob(config["pattern"])))
            for file_type, config in self.file_types.items()
            if (self.base_dir / file_type).exists()
        )
        
        if total_files > self.max_files:
            print(f"📊 存储空间检查: 当前 {total_files} 个文件，超过限制 {self.max_files}")
            self.cleanup_old_files()
        else:
            print(f"📊 存储空间检查: 当前 {total_files} 个文件，未超过限制 {self.max_files}")


# 全局数据管理器实例
data_manager = DataManager()


def get_data_manager() -> DataManager:
    """获取数据管理器实例"""
    return data_manager


def migrate_to_unified_storage():
    """迁移到统一存储目录"""
    data_manager.migrate_existing_files()


def cleanup_storage():
    """清理存储空间"""
    data_manager.cleanup_old_files()


def get_storage_status():
    """获取存储状态"""
    return data_manager.get_storage_info()
