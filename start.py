from os import getenv
from dotenv import load_dotenv
from backpack_exchange import BackpackExchange
from public_API import PublicClient
from time import sleep
from decimal import Decimal, ROUND_DOWN
import RequestEnums
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

load_dotenv()



def format_decimal(num) -> float:
    num = Decimal(str(num))
    
    if num >= 10**6:
        return float(num.quantize(Decimal("1.0"), rounding=ROUND_DOWN))
    elif 1 <= num < 10**6:
        integer_part = len(str(num.quantize(Decimal('1.'), rounding=ROUND_DOWN)))
        max_decimal_places = max(1, min(4, 5 - integer_part))
        format_str = f'1.{"0" * max_decimal_places}'
        return float(num.quantize(Decimal(format_str), rounding=ROUND_DOWN))
    else:
        return float(num)
    
def close_all_orders(client: BackpackExchange):
    """
    Close all open orders for the account.
    """
    try:
        open_orders = client.get_open_orders()
        if not open_orders: return

        for order in open_orders:
            client.cancel_open_order(symbol=order['symbol'], orderId=order["id"])
            logging.info(f"Cancelled order: {order['symbol']}, ID: {order['id']}")
    except Exception as e:
        logging.error(f"Error closing orders: {e}")

def start_trading(
        client: BackpackExchange,
        public_client: PublicClient,
        trading_pair: str,
        trading_amount: float = 100,  # Default trading amount in USD
        limit_price_percentage: float = 95,  # Default limit price at 95% of the current price
        stop_loss_percentage: float = 2,  # Default stop loss at 2% below the current price
        take_profit_percentage: float = 5,  # Default take profit at 5% above the current price
    ):
    try:
        market_data = public_client.get_mark_price(trading_pair)
        current_price = float(market_data[0]["indexPrice"])
        logging.info(f"Current price of {trading_pair}: {current_price}")

        # Calculate limit price, stop loss, and take profit prices
        limit_price = format_decimal(current_price * (limit_price_percentage / 100))
        logging.info(f"Limit price: {limit_price}")

        # Calculate quantity based on amount
        quantity = trading_amount / limit_price nay nay saii
        logging.info(f"Calculated quantity: {quantity}")

        stop_loss_price = format_decimal(limit_price * (1 - stop_loss_percentage / 100))
        take_profit_price = format_decimal(limit_price * (1 + take_profit_percentage / 100))

        logging.info(f"Placing limit order at price: {limit_price}")
        logging.info(f"Stop loss price: {stop_loss_price}, Take profit price: {take_profit_price}")

        order_status = client.execute_order(
            RequestEnums.OrderType.LIMIT.value,
            RequestEnums.OrderSide.BID.value,
            symbol=trading_pair,
            price=str(limit_price),
            quantity=str(quantity),
            postOnly=False,
            stopLossTriggerPrice=str(stop_loss_price),
            takeProfitTriggerPrice=str(take_profit_price),
        )

        return order_status
    
    except Exception as e:
        logging.error(f"Error in start_trading: {e}")

if __name__ == "__main__":
    leverageLimit = 25
    autoRepayBorrows = True
    trading_pair = "SOL_USDC_PERP"

    API_KEY = getenv("API_KEY")
    API_SECRET = getenv("API_SECRET")

    if not API_KEY or not API_SECRET:
        logging.error("API_KEY or API_SECRET is not set.")
        exit(1)

    public_client = PublicClient()

    client = BackpackExchange(API_KEY, API_SECRET)
    
    client.update_account(leverageLimit=leverageLimit, autoRepayBorrows=autoRepayBorrows)

    close_all_orders(client)

    
    
    start_trading(
        client=client,
        public_client=public_client,
        trading_pair=trading_pair, 
        trading_amount=100, 
        limit_price_percentage=95, 
        stop_loss_percentage=2,
        take_profit_percentage=5
    )