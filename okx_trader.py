import ccxt
import json
from typing import Dict, Tuple, Optional
from decimal import Decimal

from api_test import test_okx_connection
from config import API_CONFIG, TRADE_CONFIG
from typing import Dict, Tuple, Optional, List  # Add List to the imports


class OKXTrader:
    def __init__(self):
        """初始化交易对象，从config.py读取配置"""
        self.exchange = ccxt.okx(API_CONFIG)
        self.exchange.load_markets()  # 预加载市场数据
        self.trade_config = TRADE_CONFIG

    def get_token_balance(self, token: str) -> float:
        """获取指定代币的余额"""
        try:
            balance = self.exchange.fetch_balance()
            return float(balance.get(token, {}).get('free', 0))
        except Exception as e:
            print(f"获取{token}余额失败: {str(e)}")
            return 0

    def check_token_in_portfolio(self, token: str) -> Tuple[bool, float]:
        """检查代币是否在投资组合中，返回(是否存在, 余额)"""
        balance = self.get_token_balance(token)
        return balance > 0, balance

    def format_amount(self, symbol: str, amount: float) -> float:
        """根据交易所规则格式化交易数量"""
        market = self.exchange.market(symbol)
        precision = market['precision']['amount']
        return float(Decimal(str(amount)).quantize(Decimal(f"0.{'0' * precision}")))

    def market_buy(self, token: str, usdt_amount: float) -> Optional[Dict]:
        """市价买入指定代币

        Args:
            token: 代币名称 (例如 'BTC', 'ETH')
            usdt_amount: 要使用的USDT数量

        Returns:
            下单结果字典或None（如果失败）
        """
        try:
            symbol = f"{token}/USDT"

            # 检查交易对是否存在
            if symbol not in self.exchange.markets:
                print(f"❌ 交易对{symbol}不存在")
                return None

            # 检查USDT余额
            usdt_balance = self.get_token_balance('USDT')
            if usdt_balance < usdt_amount:
                print(f"❌ USDT余额不足: {usdt_balance} < {usdt_amount}")
                return None

            # 获取当前市价
            ticker = self.exchange.fetch_ticker(symbol)
            current_price = ticker['last']

            # 计算可以买入的代币数量
            token_amount = usdt_amount / current_price
            token_amount = self.format_amount(symbol, token_amount)

            # 执行市价买入
            print(f"\n正在以市价买入 {token_amount} {token} (约{usdt_amount} USDT)...")
            order = self.exchange.create_market_buy_order(
                symbol,
                token_amount,
                params={'tgtCcy': 'USDT'}  # 指定使用USDT作为计价货币
            )

            print(f"✅ 买入成功！价格: {current_price} USDT")
            print(json.dumps(order, indent=2))
            return order

        except Exception as e:
            print(f"❌ 买入失败: {str(e)}")
            return None

    def market_sell(self, token: str) -> Optional[Dict]:
        """市价卖出指定代币的全部余额"""
        try:
            symbol = f"{token}/USDT"
            print(f"Debug 1 - Symbol: {symbol}")

            # 检查代币是否在投资组合中
            has_token, balance = self.check_token_in_portfolio(token)
            print(f"Debug 2 - Has token: {has_token}")
            print(f"Debug 2.1 - Balance type: {type(balance)}, value: {balance}")

            if not has_token:
                print(f"❌ 投资组合中没有{token}，无法卖出")
                return None

            # 格式化卖出数量 - 直接使用完整余额
            try:
                sell_amount = self.format_amount(symbol, balance)
                print(f"Debug 3 - Sell amount after format: {type(sell_amount)}, value: {sell_amount}")
            except Exception as e:
                print(f"Debug Error in amount formatting: {str(e)}")
                raise

            if sell_amount <= 0:
                print(f"❌ 可卖出数量为0")
                return None

            # 获取当前市价估算USDT价值
            try:
                ticker = self.exchange.fetch_ticker(symbol)
                print(f"Debug 4 - Ticker raw: {ticker['last']}, type: {type(ticker['last'])}")

                current_price = float(ticker['last'])
                print(f"Debug 5 - Current price: {type(current_price)}, value: {current_price}")

                usdt_value = sell_amount * current_price
                print(f"Debug 6 - USDT value calculated: {usdt_value}")
            except Exception as e:
                print(f"Debug Error in price calculation: {str(e)}")
                raise

            # 执行市价卖出
            print(f"\n正在以市价卖出 {sell_amount} {token} (约{usdt_value:.2f} USDT)...")
            order = self.exchange.create_market_sell_order(
                symbol,
                sell_amount
            )

            print(f"✅ 卖出成功！价格: {current_price} USDT")
            print(json.dumps(order, indent=2))
            return order

        except Exception as e:
            print(f"❌ 卖出失败: {str(e)}")
            return None

    def limit_sell(self, token: str) -> Optional[Dict]:
        """限价卖出指定代币，以当前最低卖价下单以获得更低手续费"""
        try:
            symbol = f"{token}/USDT"
            print(f"Debug 1 - Symbol: {symbol}")

            # 检查代币是否在投资组合中
            has_token, balance = self.check_token_in_portfolio(token)
            print(f"Debug 2 - Has token: {has_token}")
            print(f"Debug 2.1 - Balance type: {type(balance)}, value: {balance}")

            if not has_token:
                print(f"❌ 投资组合中没有{token}，无法卖出")
                return None

            # 格式化卖出数量
            try:
                sell_amount = self.format_amount(symbol, balance)
                print(f"Debug 3 - Sell amount after format: {type(sell_amount)}, value: {sell_amount}")
            except Exception as e:
                print(f"Debug Error in amount formatting: {str(e)}")
                raise

            if sell_amount <= 0:
                print(f"❌ 可卖出数量为0")
                return None

            try:
                # 获取订单簿数据来确定最低卖价
                order_book = self.exchange.fetch_order_book(symbol)
                if not order_book['asks']:
                    print(f"❌ 无法获取{token}的卖单数据")
                    return None

                # Print top 5 asks and bids
                print("\n订单簿数据:")
                print("卖单 (Asks):")
                for i, ask in enumerate(order_book['asks'][:5], 1):
                    print(f"  {i}. 价格: {ask[0]} USDT, 数量: {ask[1]} {token}")

                print("\n买单 (Bids):")
                for i, bid in enumerate(order_book['bids'][:5], 1):
                    print(f"  {i}. 价格: {bid[0]} USDT, 数量: {bid[1]} {token}")

                # 获取当前最低卖价
                lowest_ask = float(order_book['asks'][0][0])
                print(f"\nDebug 4 - Lowest ask price: {lowest_ask}")

                # 获取当前最高买价（用于参考）
                highest_bid = float(order_book['bids'][0][0]) if order_book['bids'] else None
                print(f"Debug 5 - Highest bid price: {highest_bid}")

                # 设置我们的卖出价格为最低卖价
                sell_price = lowest_ask
                usdt_value = sell_amount * sell_price

                print(f"Debug 6 - Pre-order values:")
                print(f"  sell_amount: {sell_amount}")
                print(f"  sell_price: {sell_price}")
                print(f"  estimated_value: {usdt_value:.2f} USDT")

            except Exception as e:
                print(f"Debug Error in price calculation: {str(e)}")
                raise

            # 执行限价卖出
            print(f"\n正在以限价 {sell_price} USDT 卖出 {sell_amount} {token} (约{usdt_value:.2f} USDT)...")
            try:
                order = self.exchange.create_limit_sell_order(
                    symbol,
                    sell_amount,
                    sell_price
                )

                print(f"✅ 限价卖出订单提交成功！")
                print(json.dumps(order, indent=2))
                return order

            except Exception as e:
                print(f"❌ 限价卖出订单提交失败: {str(e)}")
                return None

        except Exception as e:
            print(f"❌ 卖出失败: {str(e)}")
            return None

    def format_amount(self, symbol: str, amount: float) -> float:
        """根据交易所规则格式化交易数量"""
        try:
            print(f"Format Debug 1 - Input amount type: {type(amount)}, value: {amount}")

            market = self.exchange.market(symbol)
            # Get precision and ensure we have at least 4 decimal places for most tokens
            if isinstance(market['precision']['amount'], str):
                precision = max(4, int(abs(Decimal(market['precision']['amount']).as_tuple().exponent)))
            else:
                precision = max(4, int(market['precision']['amount']))

            print(f"Format Debug 2 - Precision converted to int: {precision}")

            decimal_str = f"0.{'0' * precision}"
            print(f"Format Debug 3 - Decimal string: {decimal_str}")

            # Use ROUND_DOWN to ensure we don't exceed available balance
            formatted = float(Decimal(str(amount)).quantize(Decimal(decimal_str), rounding='ROUND_DOWN'))
            print(f"Format Debug 4 - Output amount type: {type(formatted)}, value: {formatted}")

            return formatted
        except Exception as e:
            print(f"Format Debug Error: {str(e)}")
            raise

    def get_portfolio_summary(self) -> Dict:
        """获取当前投资组合摘要"""
        try:
            summary = {}
            balance = self.exchange.fetch_balance()

            # 检查配置中的所有代币
            for token in self.trade_config['coin_weights'].keys():
                amount = float(balance.get(token, {}).get('free', 0))
                if amount > 0:
                    ticker = self.exchange.fetch_ticker(f"{token}/USDT")
                    current_price = ticker['last']
                    usdt_value = amount * current_price

                    summary[token] = {
                        'amount': amount,
                        'price': current_price,
                        'value_usdt': usdt_value
                    }

            return summary

        except Exception as e:
            print(f"❌ 获取投资组合摘要失败: {str(e)}")
            return {}

    def check_order_status(self, order_id: str, symbol: str) -> Dict:
        """检查订单状态"""
        try:
            order = self.exchange.fetch_order(order_id, symbol)

            print(f"\n订单状态:")
            print(f"订单ID: {order['id']}")
            print(f"状态: {order['status']}")
            print(f"已成交数量: {order.get('filled', 0)}")
            print(f"剩余数量: {order.get('remaining', 0)}")
            if order.get('fee'):
                print(f"手续费: {order['fee']}")

            return order
        except Exception as e:
            print(f"❌ 检查订单状态失败: {str(e)}")
            return {}

    def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict]:
        """获取未完成的订单"""
        try:
            orders = self.exchange.fetch_open_orders(symbol)

            print(f"\n未完成订单列表:")
            if not orders:
                print("没有未完成的订单")
                return []

            for order in orders:
                print(f"\n订单ID: {order['id']}")
                print(f"交易对: {order['symbol']}")
                print(f"类型: {order['type']}")
                print(f"方向: {order['side']}")
                print(f"价格: {order['price']}")
                print(f"数量: {order['amount']}")
                print(f"已成交: {order.get('filled', 0)}")
                print(f"剩余: {order.get('remaining', 0)}")
                print(f"状态: {order['status']}")

            return orders
        except Exception as e:
            print(f"❌ 获取未完成订单失败: {str(e)}")
            return []

    def cancel_order(self, order_id: str, symbol: str) -> bool:
        """取消指定订单"""
        try:
            result = self.exchange.cancel_order(order_id, symbol)
            print(f"✅ 订单 {order_id} 已成功取消")
            return True
        except Exception as e:
            print(f"❌ 取消订单失败: {str(e)}")
            return False

    def sell_all_tokens(self) -> None:
        """使用限价卖出功能卖出投资组合中的所有代币"""
        try:
            # 获取当前投资组合
            portfolio = self.get_portfolio_summary()
            if not portfolio:
                print("❌ 获取投资组合失败或投资组合为空")
                return

            print("\n=== 开始批量限价卖出 ===")
            print(f"投资组合中共有 {len(portfolio)} 个代币")

            # 跳过USDT和余额很小的代币
            skip_tokens = {'USDT'}
            orders_placed = []

            for token, data in portfolio.items():
                if token in skip_tokens:
                    continue

                # 如果代币价值小于1 USDT，跳过
                if data['value_usdt'] < 1:
                    print(f"\n跳过 {token}: 价值太小 ({data['value_usdt']:.2f} USDT)")
                    continue

                print(f"\n正在处理 {token}:")
                print(f"当前持有: {data['amount']} (价值约: {data['value_usdt']:.2f} USDT)")

                # 使用limit_sell下单
                order = self.limit_sell(token)
                if order:
                    orders_placed.append({
                        'token': token,
                        'order_id': order['id'],
                        'symbol': order['symbol']
                    })
                    print(f"✅ {token} 限价卖出订单已提交")
                else:
                    print(f"❌ {token} 限价卖出失败")

            # 打印订单汇总
            if orders_placed:
                print("\n=== 订单提交汇总 ===")
                print(f"成功提交 {len(orders_placed)} 个限价卖出订单")
                for order in orders_placed:
                    print(f"- {order['token']}: Order ID {order['order_id']}")

                # 检查订单状态
                print("\n=== 检查订单状态 ===")
                for order in orders_placed:
                    print(f"\n检查 {order['token']} 订单状态:")
                    self.check_order_status(order['order_id'], order['symbol'])

            print("\n=== 批量限价卖出完成 ===")

            # 获取未完成订单
            print("\n=== 查看未完成订单 ===")
            self.get_open_orders()

        except Exception as e:
            print(f"❌ 批量卖出过程中发生错误: {str(e)}")

def main():
    """测试函数"""
    # 初始化
    trader = OKXTrader()

    # 测试链接
    print("\n配置验证通过，开始测试API连接...")
    test_okx_connection()

    # 测试限价卖出单个币
    # print("\n1. 提交限价卖出订单")
    # sell_token = "BCH"
    # order = trader.limit_sell(sell_token)
    #
    # if order:
    #     order_id = order['id']
    #     symbol = f"{sell_token}/USDT"
    #
    #     # 检查订单状态
    #     print("\n2. 检查订单状态")
    #     trader.check_order_status(order_id, symbol)
    #
    #     # 获取所有未完成订单
    #     print("\n3. 获取所有未完成订单")
    #     open_orders = trader.get_open_orders()
    #
    #     # 如果需要取消订单
    #     if open_orders and input("\n是否取消未完成的订单？(y/n): ").lower() == 'y':
    #         for order in open_orders:
    #             trader.cancel_order(order['id'], order['symbol'])

    # 测试限价卖出整个订单
    print("\n当前投资组合:")
    portfolio = trader.get_portfolio_summary()
    if portfolio:
        total_value = sum(coin['value_usdt'] for coin in portfolio.values())
        print(f"总价值: {total_value:.2f} USDT")
        for token, data in portfolio.items():
            print(f"{token}: {data['amount']} (价值: {data['value_usdt']:.2f} USDT)")

    # 确认是否执行全部卖出
    if input("\n确定要卖出所有代币吗？(y/n): ").lower() == 'y':
        trader.sell_all_tokens()
    else:
        print("操作已取消")


    # #  以下代码片段获取所有未完成订单且看看是否需要取消订单
    # 获取所有未完成订单
    print("\n3. 获取所有未完成订单")
    open_orders = trader.get_open_orders()
    # 如果需要取消订单
    if open_orders and input("\n是否取消未完成的订单？(y/n): ").lower() == 'y':
        for order in open_orders:
            trader.cancel_order(order['id'], order['symbol'])

if __name__ == "__main__":
    main()