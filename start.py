from os import getenv
from dotenv import load_dotenv
from backpack_exchange import BackpackExchange
from public_API import PublicClient
from time import sleep
import types
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

load_dotenv()



def format_decimal(value: any, tick_size: any) -> float:
    tick_size = str(tick_size)
    decimal_places = tick_size[::-1].find('.') if '.' in tick_size else 0
    formatted_value = f"{float(value):.{decimal_places}f}"
    return float(formatted_value)
    
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

def validate_inputs(limit_price_percentage: float, trade_side: str) -> bool:
    if not (0 < limit_price_percentage <= 100):  # Adjusted validation for percentage
        logging.error("limit_price_percentage must be > 0 and <= 100.")
        return False
    if trade_side not in ["LONG", "SHORT"]:
        logging.error("trade_side must be either 'LONG' or 'SHORT'.")
        return False
    return True

def get_market_data(public_client: PublicClient, trading_pair: str):
    try:
        trading_pair_info = public_client.get_market(symbol=trading_pair)
        tick_size = trading_pair_info["filters"]["price"]["tickSize"]
        step_size = trading_pair_info["filters"]["quantity"]["stepSize"]
        market_data = public_client.get_mark_price(trading_pair)
        current_price = float(market_data[0]["indexPrice"])
        logging.info(f"Current price of {trading_pair}: {current_price}")
        return tick_size, step_size, current_price
    except Exception as e:
        logging.error(f"Error in get_market_data: {e}")
        return None, None, None

def calculate_prices(trade_side: str, current_price: float, limit_price_percentage: float, stop_loss_percentage: float, take_profit_percentage: float, tick_size: str):
    if trade_side == "LONG":
        # Limit price is lower than current price by limit_price_percentage
        limit_price = format_decimal(current_price * (1 - limit_price_percentage / 100), tick_size)
        stop_loss_price = format_decimal(limit_price * (1 - stop_loss_percentage / 100), tick_size)
        take_profit_price = format_decimal(limit_price * (1 + take_profit_percentage / 100), tick_size)
    else:  # SHORT
        limit_price = format_decimal(current_price * (1 + limit_price_percentage / 100), tick_size)
        logging.info(f"zzzCurrent price: {current_price}, Limit price: {limit_price}m 'limit_price_percentage': {limit_price_percentage}")
        stop_loss_price = format_decimal(limit_price * (1 + stop_loss_percentage / 100), tick_size)
        take_profit_price = format_decimal(limit_price * (1 - take_profit_percentage / 100), tick_size)
    return limit_price, stop_loss_price, take_profit_price

def start_trading(
        client: BackpackExchange,
        public_client: PublicClient,
        trading_pair: str,
        trading_amount: float = 100,
        limit_price_percentage: float = 0.1,  # Default to 1% difference
        stop_loss_percentage: float = 2,
        take_profit_percentage: float = 5,
        trade_side: str = "LONG"
    ):

    if not validate_inputs(limit_price_percentage, trade_side):
        return False

    tick_size, step_size, current_price = get_market_data(public_client, trading_pair)
    if not tick_size or not step_size or not current_price:
        return False

    limit_price, stop_loss_price, take_profit_price = calculate_prices(
        trade_side, current_price, limit_price_percentage, stop_loss_percentage, take_profit_percentage, tick_size
    )
    logging.info(f"Limit price: {limit_price}, Stop loss price: {stop_loss_price}, Take profit price: {take_profit_price}")

    quantity = format_decimal(trading_amount / limit_price, tick_size=step_size)
    logging.info(f"Calculated quantity: {quantity}")

    order_side = types.OrderSide.BID.value if trade_side == "LONG" else types.OrderSide.ASK.value
    logging.info(f"Trade side: {trade_side}, Order side: {order_side}")

    try:
        order_status = client.execute_order(
            types.OrderType.LIMIT.value,
            order_side,
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
        return False

if __name__ == "__main__":
    ### setting ###
    leverageLimit = 25
    autoRepayBorrows = True
    trading_amount = 25
    limit_price_percentage = 0.1
    stop_loss_percentage = 2
    take_profit_percentage = 5
    trading_pair = "BTC_USDC_PERP"
    trade_side = "LONG"
    #########################

    API_KEY = getenv("API_KEY")
    API_SECRET = getenv("API_SECRET") 

    if not API_KEY or not API_SECRET:
        logging.error("API_KEY or API_SECRET is not set.")
        exit(1)

    public_client = PublicClient()
    client = BackpackExchange(API_KEY, API_SECRET)

    # client.update_account(leverageLimit=leverageLimit, autoRepayBorrows=autoRepayBorrows)

    close_all_orders(client)

    order_status = start_trading(
        client=client,
        public_client=public_client,
        trading_pair=trading_pair,
        trading_amount=trading_amount,
        limit_price_percentage=limit_price_percentage,
        stop_loss_percentage=stop_loss_percentage,
        take_profit_percentage=take_profit_percentage,
        trade_side=trade_side,
    )

    print(order_status)