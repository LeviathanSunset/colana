# OKX Web3 爬虫配置文件

# API endpoints
OKXLX_BASE_URL = "https://web3.okx.com"
HOLDERS_ENDPOINT = "/priapi/v1/dx/market/v2/holders/ranking-list"
WALLET_ASSETS_ENDPOINT = "/priapi/v2/wallet/asset/profile/all/explorer"

# 默认参数
DEFAULT_CHAIN_ID = "501"  # Solana
DEFAULT_CURRENT_USER_WALLET = "0xa6b67e6f61dba6363b36bbcef80d971a6d1f0ce5"

# 请求头配置
DEFAULT_HEADERS = {
    'Accept': 'application/json',
    'Accept-Encoding': 'gzip, deflate, br, zstd',
    'Accept-Language': 'en-US,en;q=0.9,zh-HK;q=0.8,zh-CN;q=0.7,zh;q=0.6',
    'App-Type': 'web',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
    'Sec-Ch-Ua': '"Not)A;Brand";v="8", "Chromium";v="138", "Google Chrome";v="138"',
    'Sec-Ch-Ua-Mobile': '?0',
    'Sec-Ch-Ua-Platform': '"Windows"',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'same-origin',
    'X-Cdn': 'https://web3.okx.com',
    'X-Locale': 'en_US',
    'X-Utc': '0',
    'X-Zkdex-Env': '0',
    'Priority': 'u=1, i',
    'Platform': 'web'
}

# 爬取设置
DEFAULT_MAX_HOLDERS = 10
DEFAULT_TOP_TOKENS = 10
REQUEST_DELAY_RANGE = (1, 3)  # 请求间隔范围（秒）
MAX_RETRIES = 3

# 支持的链ID映射
CHAIN_IDS = {
    'ethereum': '1',
    'bsc': '56',
    'polygon': '137',
    'arbitrum': '42161',
    'optimism': '10',
    'avalanche': '43114',
    'fantom': '250',
    'solana': '501',
    'aptos': '1000'
}
