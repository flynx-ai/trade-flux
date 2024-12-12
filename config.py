"""
Trade Flux 配置文件
包含API配置和交易参数
"""

# API 配置
API_CONFIG = {
    'apiKey': "",  # OKX API Key
    'secret': "",  # OKX Secret Key
    'password': "",  # OKX API 密码
    'enableRateLimit': True  # 启用频率限制
}

# 交易配置
TRADE_CONFIG = {
    'total_usdt': 3000,  # 总交易金额 (USDT)

    # 交易权重配置 (总和必须等于1)
    'coin_weights': {
        # 第一梯队 (每个0.025 = 75USDT)
        'XRP': 0.025, 'SOL': 0.025, 'DOGE': 0.025, 'ADA': 0.025,
        'TRX': 0.025, 'AVAX': 0.025, 'SHIB': 0.025, 'TON': 0.025,
        'LINK': 0.025, 'DOT': 0.025, 'XLM': 0.025, 'SUI': 0.025,
        'HBAR': 0.025, 'BCH': 0.025, 'PEPE': 0.025, 'UNI': 0.025,
        'NEAR': 0.025, 'APT': 0.025, 'ICP': 0.025, 'POL': 0.025,

        # 第二梯队 (每个0.05 = 150USDT)
        'RENDER': 0.05, 'AAVE': 0.05, 'OM': 0.05, 'ARB': 0.05,
        'IMX': 0.05, 'OP': 0.05, 'GPT': 0.05, 'SNX': 0.05,
        'RSR': 0.05, 'DYDX': 0.05
    }
}