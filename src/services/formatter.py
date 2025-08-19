"""
消息格式化服务
负责Telegram消息的格式化和美化
"""

from typing import List, Optional, Dict
from ..models import HolderInfo, AnalysisResult, PriceChangeResult
from ..utils import format_number, format_percentage


class MessageFormatter:
    """消息格式化器"""

    @staticmethod
    def format_welcome_message() -> str:
        """格式化欢迎消息"""
        return """
🤖 <b>代币大户分析Bot v2.1</b>

<b>📋 主要功能:</b>
• 🔍 代币大户分析 - 深度分析代币持有者分布
• 🪐 Jupiter热门分析 - 分析Jupiter平台热门代币
• 🤖 自动pump分析 - 自动监控异动代币
• 📊 价格变动监控 - 实时推送涨幅预警
• ⚙️ 智能配置管理 - 动态调整参数
• 🚫 黑名单管理 - 过滤不良代币

<b>� 快速开始:</b>
<code>/help</code> - 显示详细帮助
<code>/ca1 &lt;代币地址&gt;</code> - 分析指定代币
<code>/cajup</code> - Jupiter热门代币分析
<code>/capump</code> - 查看自动分析状态
<code>/config</code> - 配置管理界面

<b>💡 Bot特色:</b>
• ⚡ 高速分析：前100大户深度扫描
• 🎯 智能集群：自动识别关联地址
• 📈 排名分析：代币持有者排名透视
• 🔄 实时缓存：避免重复分析浪费
• 🛡️ 安全过滤：黑名单自动跳过
• 📱 友好界面：交互式按钮操作

需要详细帮助请使用 /help 命令 📖
"""

    @staticmethod
    def format_help_message() -> str:
        """格式化详细帮助消息"""
        return """
📖 <b>Colana Bot 详细使用指南</b>

<b>🔍 代币大户分析 (/ca1)</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
<b>功能说明：</b>分析指定代币的前100大户持仓情况

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

<b>🪐 Jupiter热门分析 (/cajup)</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
<b>功能说明：</b>获取Jupiter平台热门代币并逐个分析

<b>使用方法：</b>
<code>/cajup</code> - 分析默认数量
<code>/cajup &lt;数量&gt;</code> - 分析指定数量

<b>示例：</b>
<code>/cajup</code> - 分析10个热门代币
<code>/cajup 20</code> - 分析20个热门代币

<b>分析流程：</b>
• 📊 获取Jupiter平台热门代币列表
• 🔍 对每个代币进行大户分析
• 🚫 自动跳过黑名单中的代币
• ⏸️ 支持中途停止分析

<b>🤖 自动Pump分析 (/capump)</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
<b>功能说明：</b>自动监控价格异动超过阈值的代币

<b>使用方法：</b>
<code>/capump</code> - 查看当前状态
<code>/capump on</code> - 启用自动分析
<code>/capump off</code> - 关闭自动分析

<b>工作原理：</b>
• 🔄 定期监控代币价格变动
• 📈 发现涨幅超过10%的代币
• 🤖 自动触发大户分析
• 📤 将分析结果推送到群组
• 🚫 智能跳过黑名单代币
• 🛡️ 避免重复分析同一代币

<b>配置选项：</b>
• ⏱️ 监控间隔（默认58秒）
• 📈 涨幅阈值（默认10%）
• 💰 最小市值过滤
• 📅 最小代币年龄

<b>⚙️ 配置管理 (/config)</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
<b>功能说明：</b>动态调整Bot各项参数

<b>配置模块：</b>
• 🔔 泵检警报设置
• 🤖 自动分析参数
• 📊 持有者分析配置
• 🪐 Jupiter分析设置
• 🚫 黑名单管理

<b>主要配置项：</b>
• 检查间隔、涨幅阈值
• 最小市值、代币年龄
• 大户数量、排行榜大小
• 集群分析参数

<b>🚫 黑名单管理</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
<b>功能说明：</b>管理不需要分析的代币列表

<b>操作功能：</b>
• ➕ 添加代币到黑名单
• ➖ 从黑名单移除代币
• 📋 查看当前黑名单
• 🔍 黑名单自动过滤

<b>🛠️ 实用工具</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
<code>/topicid</code> - 获取当前Topic ID
<code>/testtopic</code> - 测试Topic功能
<code>/start</code> - 显示欢迎信息

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
A: 可能在黑名单中，或者数据源暂时不可用

<b>Q: 如何停止自动分析？</b>
A: 使用 <code>/capump off</code> 命令

<b>Q: 分析结果保存在哪里？</b>
A: 结果保存在storage目录，重启后清空

<b>🔧 技术支持</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
如遇问题请检查：
1. 网络连接是否正常
2. 代币地址格式是否正确
3. 是否有足够的API调用配额
4. 查看日志文件获取详细错误信息

<b>📈 更新日志</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
v2.1: 新增健康检查、完善帮助系统
v2.0: 自动pump分析、多群组支持
v1.x: 基础大户分析功能

欢迎使用 Colana Bot! 🚀
"""

    @staticmethod
    def format_config_message(config) -> str:
        """格式化配置消息"""
        return f"""
⚙️ <b>当前配置</b>

<b>📊 监控设置:</b>
• 检查间隔: {config.bot.interval} 秒
• 涨幅阈值: {format_percentage(config.bot.threshold)}
• 最小市值: ${format_number(config.bot.min_market_cap)}
• 最小年龄: {config.bot.min_age_days} 天

<b>🔍 分析设置:</b>
• 大户数量: {config.analysis.top_holders_count}
• 排行榜大小: {config.analysis.ranking_size}
• 详情按钮数: {config.analysis.detail_buttons_count}
• 集群最小共同代币: {config.analysis.cluster_min_common_tokens}
• 集群最小地址数: {config.analysis.cluster_min_addresses}
• 集群最大地址数: {config.analysis.cluster_max_addresses}

点击下方按钮修改配置 👇
"""

    @staticmethod
    def format_price_change_message(
        results: List[PriceChangeResult],
        mins: Optional[int] = None,
        old_ts: Optional[str] = None,
        new_ts: Optional[str] = None,
        page: int = 0,
        pages: int = 1,
    ) -> str:
        """格式化价格变动消息"""
        if not results:
            return "⚠️ 无符合条件的币种。"

        header = ""
        if mins and old_ts and new_ts:
            header = f"<b>📈 近{mins}分钟涨幅预警</b> 第{page+1}/{pages}页\n"
            header += f"📸 快照: {old_ts} → {new_ts}\n\n"

        message_lines = [header] if header else []

        for i, result in enumerate(results, 1):
            token = result.token
            link = f"https://gmgn.ai/sol/token/{token.mint}"

            old_value = format_number(result.old_price)
            new_value = format_number(result.new_price)
            change_percent = format_percentage(result.change_percent)

            line = (
                f"<b>{i}. <a href='{link}'>{token.name}</a></b> "
                f"<a href='{link}'>📊</a> "
                f"涨幅: <b>{change_percent}</b> "
                f"(${old_value}→${new_value}) "
                f"创建: {token.created_date}"
            )
            message_lines.append(line)

        return "\n".join(message_lines)

    @staticmethod
    def format_analysis_result(result: AnalysisResult, sort_by: str = "balance") -> str:
        """格式化分析结果消息"""
        token = result.token
        holders = result.holders

        # 排序持有者
        if sort_by == "percentage":
            holders = sorted(holders, key=lambda x: x.percentage, reverse=True)
        elif sort_by == "usd_value":
            holders = sorted(holders, key=lambda x: x.usd_value, reverse=True)
        else:
            holders = sorted(holders, key=lambda x: x.balance, reverse=True)

        # 构建消息
        message_lines = [
            f"🎯 <b>{token.name} ({token.symbol})</b>",
            f"💰 市值: ${format_number(token.usd_market_cap)}",
            f"📅 创建: {token.created_date}",
            f"⏰ 年龄: {token.age_days:.1f}天",
            "",
            f"👥 <b>TOP {len(holders)} 大户分析</b> (按{sort_by}排序)",
            "",
        ]

        for i, holder in enumerate(holders[:10], 1):  # 只显示前10个
            balance_str = format_number(holder.balance)
            percentage_str = f"{holder.percentage:.2f}%"
            usd_value_str = format_number(holder.usd_value)

            # 截断地址显示
            addr_short = f"{holder.address[:4]}...{holder.address[-4:]}"

            line = (
                f"{i}. <code>{addr_short}</code> "
                f"💎{balance_str} ({percentage_str}) "
                f"💵${usd_value_str}"
            )
            message_lines.append(line)

        if len(holders) > 10:
            message_lines.append(f"\n... 还有 {len(holders) - 10} 个大户")

        # 添加集群信息
        if result.clusters:
            message_lines.extend(["", f"🔗 <b>发现 {len(result.clusters)} 个地址集群</b>", ""])

            for i, cluster in enumerate(result.clusters[:3], 1):  # 只显示前3个集群
                message_lines.append(
                    f"集群{i}: {cluster.total_addresses}个地址, "
                    f"{cluster.common_token_count}个共同代币"
                )

        return "\n".join(message_lines)

    @staticmethod
    def format_holder_detail(holder: HolderInfo, tokens: List[Dict]) -> str:
        """格式化持有者详细信息"""
        addr_short = f"{holder.address[:8]}...{holder.address[-8:]}"

        message_lines = [
            f"🔍 <b>大户详情: {addr_short}</b>",
            f"💎 持仓: {format_number(holder.balance)}",
            f"📊 占比: {holder.percentage:.2f}%",
            f"💵 价值: ${format_number(holder.usd_value)}",
            "",
            f"🎯 <b>该地址持有的其他代币 (TOP 10)</b>",
            "",
        ]

        for i, token in enumerate(tokens[:10], 1):
            name = token.get("tokenName", "Unknown")[:20]  # 限制长度
            balance = format_number(float(token.get("balance", 0)))
            value = format_number(float(token.get("balanceValue", 0)))

            message_lines.append(f"{i}. <b>{name}</b> " f"💎{balance} 💵${value}")

        return "\n".join(message_lines)

    @staticmethod
    def format_cluster_analysis(clusters: List[Dict]) -> str:
        """格式化集群分析结果"""
        if not clusters:
            return "🔍 未发现明显的地址集群模式"

        message_lines = [
            f"🔗 <b>发现 {len(clusters)} 个地址集群</b>",
            "可能的关联地址或协调行为:",
            "",
        ]

        for i, cluster in enumerate(clusters, 1):
            addresses = cluster.get("addresses", [])
            common_tokens = cluster.get("common_tokens", [])

            message_lines.extend(
                [
                    f"<b>集群 {i}:</b>",
                    f"📍 地址数量: {len(addresses)}",
                    f"🎯 共同代币: {len(common_tokens)}",
                    "",
                ]
            )

            # 显示部分地址
            for addr in addresses[:3]:
                addr_short = f"{addr[:6]}...{addr[-6:]}"
                message_lines.append(f"  • <code>{addr_short}</code>")

            if len(addresses) > 3:
                message_lines.append(f"  • ... 还有 {len(addresses) - 3} 个地址")

            message_lines.append("")

        return "\n".join(message_lines)

    @staticmethod
    def format_blacklist_info(count: int) -> str:
        """格式化黑名单信息"""
        return f"""
🚫 <b>黑名单管理</b>

📊 当前黑名单数量: <b>{count}</b>

<b>功能说明:</b>
• 添加黑名单: 将代币加入黑名单，不再监控
• 移除黑名单: 从黑名单中移除代币
• 查看黑名单: 显示当前所有黑名单代币

选择操作 👇
"""

    @staticmethod
    def format_error_message(error: str) -> str:
        """格式化错误消息"""
        return f"❌ <b>错误</b>\n\n{error}"

    @staticmethod
    def format_success_message(message: str) -> str:
        """格式化成功消息"""
        return f"✅ <b>成功</b>\n\n{message}"

    @staticmethod
    def paginate_message(content: str, max_length: int = 4000) -> List[str]:
        """分页处理长消息"""
        if len(content) <= max_length:
            return [content]

        pages = []
        current_page = ""

        lines = content.split("\n")
        for line in lines:
            if len(current_page) + len(line) + 1 <= max_length:
                current_page += line + "\n"
            else:
                if current_page:
                    pages.append(current_page.rstrip())
                current_page = line + "\n"

        if current_page:
            pages.append(current_page.rstrip())

        return pages
