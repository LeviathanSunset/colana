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
🤖 <b>代币大户分析Bot</b>

<b>📋 主要功能:</b>
• 代币大户分析 - /ca1 &lt;代币地址&gt;
• 价格变动监控 - 自动推送涨幅预警
• 黑名单管理 - /config 配置

<b>🔍 使用示例:</b>
<code>/ca1 FbGsCHv8qPvUdmomVAiG72ET5D5kgBJgGoxxfMZipump</code>

<b>⚙️ 配置管理:</b>
使用 /config 命令进入配置界面

<b>💡 提示:</b>
• 分析结果会缓存30分钟
• 支持地址集群分析
• 可按不同维度排序
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
