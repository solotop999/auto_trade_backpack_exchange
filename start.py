import json
from os import getenv
from pathlib import Path
from decimal import Decimal, ROUND_DOWN
from dotenv import load_dotenv
from time import sleep
import logging
import random
from helpers.backpack_exchange import BackpackExchange
from helpers.public_API import PublicClient
from helpers.orders import close_all_orders, close_all_positions
from helpers.format_types import OrderSide, OrderType

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filename="trade.log",
    filemode="a"
)

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

TELEGRAM_INFO = {
    "MSG_TO": getenv("TELEGRAM_MSG_TO"),
    "API_ID": getenv("TELEGRAM_API_ID"),
    "API_HASH": getenv("TELEGRAM_API_HASH"),
    "BOT_TOKEN": getenv("TELEGRAM_BOT_TOKEN")
}

def send_bot_message(message: str):
    from telethon.sync import TelegramClient
    from telethon.tl.functions.messages import SendMessageRequest

    if not all(TELEGRAM_INFO.values()):
        raise ValueError("Telegram alerts require all TELEGRAM_* environment variables")
    with TelegramClient('telegram_bp_bot', int(TELEGRAM_INFO["API_ID"]), TELEGRAM_INFO["API_HASH"]).start(bot_token=TELEGRAM_INFO["BOT_TOKEN"]) as client:
        try:
            entity = client.get_input_entity(TELEGRAM_INFO["MSG_TO"])
            client(SendMessageRequest(peer=entity, message=message, no_webpage=True))
            print(message)
        except Exception as e:
            print(f"❌ Failed to send message: {e}")


# Load settings from settings.json
with open(BASE_DIR / "settings.json", "r", encoding="utf-8") as f:
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
TELEGRAM_ALERT = settings["TELEGRAM_ALERT"]

def format_decimal(value, tick_size) -> str:
    """Round down to an actual tick/step multiple without float serialization."""
    value, increment = Decimal(str(value)), Decimal(str(tick_size))
    if not value.is_finite() or not increment.is_finite() or increment <= 0:
        raise ValueError("Value must be finite and tick/step must be positive")
    rounded = (value / increment).to_integral_value(rounding=ROUND_DOWN) * increment
    return format(rounded, "f")

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
    current_price = Decimal(str(current_price))
    limit_price_percentage = Decimal(str(limit_price_percentage))
    stop_loss_percentage = Decimal(str(stop_loss_percentage))
    take_profit_percentage = Decimal(str(take_profit_percentage))
    if trade_side == "LONG":
        # Limit price is lower than current price by limit_price_percentage
        limit_price = format_decimal(current_price * (1 - limit_price_percentage / 100), tick_size)
        stop_loss_price = format_decimal(Decimal(limit_price) * (1 - stop_loss_percentage / 100), tick_size)
        take_profit_price = format_decimal(Decimal(limit_price) * (1 + take_profit_percentage / 100), tick_size)
    else:  # SHORT
        limit_price = format_decimal(current_price * (1 + limit_price_percentage / 100), tick_size)
        stop_loss_price = format_decimal(Decimal(limit_price) * (1 + stop_loss_percentage / 100), tick_size)
        take_profit_price = format_decimal(Decimal(limit_price) * (1 - take_profit_percentage / 100), tick_size)
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

    quantity = format_decimal(Decimal(str(trading_amount)) / Decimal(limit_price), tick_size=step_size)
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
            msg = (
                f"✅ Ordered: {trade_side} \n"
                f"- Amount: {trading_amount}USDC\n"
                f"- Price: {order_status['price']}\n"
                f"- takeProfitTriggerPrice: {order_status['takeProfitTriggerPrice']} (+{take_profit_percentage:.0f}%) (+{take_profit_usdc:.0f} USDC)\n"
                f"- stopLossTriggerPrice: {order_status['stopLossTriggerPrice']} (-{stop_loss_percentage:.0f}%) (-{stop_loss_usdc:.0f} USDC)"
            )
            logging.info(msg)
            return msg
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
    print("Backpack Exchange trading client")

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

            if TELEGRAM_ALERT: send_bot_message(f"Trading {i+1}/{TOTAL_TRADES}:\n\n{order_status}")

            countdown_sleep(MIN_SLEEP, MAX_SLEEP)
    except Exception as e:
        logging.error(f"Error: {e}")
        input("Press Enter to exit...")
