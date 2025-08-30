"""
消息格式化服务
负责格式化各种类型的消息内容
"""

from typing import List, Optional, Dict


class MessageFormatter:
    """消息格式化器"""

    @staticmethod
    def format_welcome_message() -> str:
        """格式化欢迎消息"""
        return """
🤖 <b>简化版代币大户分析Bot</b>

<b>📋 主要功能:</b>
• 🔍 代币大户分析 - 深度分析代币持有者分布
• 📊 集群分析 - 识别关联地址和持仓模式
• ⚡ 多线程加速 - 快速获取大户数据
• 🎯 精准分析 - 专注核心功能，稳定可靠

<b>🚀 快速开始:</b>
<code>/help</code> - 显示详细帮助
<code>/ca1 &lt;代币地址&gt;</code> - 分析指定代币

<b>💡 Bot特色:</b>
• ⚡ 高速分析：前100大户深度扫描
• 🎯 智能集群：自动识别关联地址
• 📈 排名分析：代币持有者排名透视
• 🔄 实时缓存：避免重复分析浪费
• 📱 友好界面：交互式按钮操作

需要详细帮助请使用 /help 命令 📖
"""

    @staticmethod
    def format_help_message() -> str:
        """格式化详细帮助消息"""
        return """
📖 <b>简化版代币大户分析Bot 使用指南</b>

<b>🔍 代币大户分析 (/ca1)</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
<b>功能说明：</b>深度分析指定代币的前100大户持仓情况

<b>使用方法：</b>
<code>/ca1 &lt;代币合约地址&gt;</code>

<b>示例：</b>
<code>/ca1 FbGsCHv8qPvUdmomVAiG72ET5D5kgBJgGoxxfMZipump</code>

<b>分析内容：</b>
• 🎯 大户持有的所有代币排行榜
• 💰 按总价值/持有人数排序
• 🎯 地址集群分析（找出关联地址）
• 📊 目标代币在大户资产中的排名
• 🔍 详细的持有者地址信息

<b>交互功能：</b>
• 💰/👥 切换排序方式
• 🎯 查看地址集群分析
• 📊 查看代币排名分析
• 🔍 查看单个代币详情

<b>🛠️ 实用工具</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
<code>/topicid</code> - 获取当前Topic ID
<code>/start</code> - 显示欢迎信息
<code>/help</code> - 显示此帮助信息

<b>💡 使用技巧</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• 🎯 代币地址可以从GMGN等平台复制
• ⚡ 分析结果缓存30分钟，避免重复
• 🔄 支持分页浏览大量结果
• 🔗 点击地址可跳转到GMGN查看详情
• 📊 集群分析可发现潜在的巨鲸联盟
• 🏆 排名分析显示大户对代币的重视程度

<b>❓ 常见问题</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
<b>Q: 分析失败了怎么办？</b>
A: 检查代币地址是否正确，或稍后重试

<b>Q: 为什么有些代币不能分析？</b>
A: 可能是数据源暂时不可用，请稍后重试

<b>Q: 分析结果保存在哪里？</b>
A: 结果缓存在内存中，重启后清空

<b>🔧 技术支持</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
如遇问题请检查：
1. 网络连接是否正常
2. 代币地址格式是否正确
3. 查看日志文件获取详细错误信息

<b>⚙️ 配置说明</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
本Bot采用YAML+环境变量混合配置：
• 敏感信息：在 .env 文件中配置
• 业务参数：在 config.yaml 文件中调整
• 支持环境变量动态覆盖配置
"""

    @staticmethod
    def format_error_message(error: str, suggestion: str = None) -> str:
        """格式化错误消息"""
        msg = f"❌ <b>错误</b>\n\n{error}"
        if suggestion:
            msg += f"\n\n💡 <b>建议:</b>\n{suggestion}"
        return msg

    @staticmethod
    def format_success_message(message: str) -> str:
        """格式化成功消息"""
        return f"✅ <b>成功</b>\n\n{message}"
