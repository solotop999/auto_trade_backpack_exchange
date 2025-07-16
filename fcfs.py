from os import getenv
from dotenv import load_dotenv
from time import sleep
from helpers.backpack_exchange import BackpackExchange
from helpers.public_API import PublicClient
from helpers.format_types import OrderSide, OrderType

load_dotenv()


def BUY_MARKET(client: BackpackExchange, pairs: str, amount: str):
    order_status = client.execute_order(
        symbol = pairs,
        quoteQuantity = amount,
        orderType = OrderType.MARKET.value,
        side= OrderSide.BUY.value
    )

    if not order_status:
        print("SOMETHING WRONG... ", order_status)
        return
    msg = (
        f"✅ Ordered: {order_status['id']} - Status: {order_status['status']}\n"
        f"- Swap: {AMOUNT_USDC} $USDC to {order_status['executedQuantity']} ${PAIRS_SPOT.split('_')[0]}\n"
    )

    return msg

def SHORT_PERP(client: BackpackExchange, pairs: str, amount: str):
    order_status = client.execute_order(
        symbol = pairs,
        quoteQuantity = amount,
        orderType = OrderType.MARKET.value,
        side= OrderSide.SELL.value
    )
    print(order_status)
    if not order_status:
        print("SOMETHING WRONG... ", order_status)
        return
    msg = (
        f"✅ Ordered: {order_status['id']} - Status: {order_status['status']}\n"
        f"- SHORT: {AMOUNT_USDC} {PAIRS_PERP}\n"
    )

    return msg


if __name__ == "__main__":

    
    ### SETTING ######
    AMOUNT_USDC = 5
    PAIRS_SPOT = "ES_USDC"
    PAIRS_PERP = "ES_USDC_PERP"
    #####################

    API_KEY = getenv("API_KEY")
    API_SECRET = getenv("API_SECRET")

    if not API_KEY or not API_SECRET:
        print("API_KEY or API_SECRET is not set.")
        exit(1)

    try:
        public_client = PublicClient()
        client = BackpackExchange(API_KEY, API_SECRET)

        status = BUY_MARKET(client=client, pairs=PAIRS_SPOT, amount=AMOUNT_USDC)
        print(status)

        print("----------------------\n")
        sleep(0.1)

        ## TRADE PERP
        status = SHORT_PERP(client=client, pairs=PAIRS_PERP, amount=AMOUNT_USDC)
        print(status)

    except Exception as e:
        print(f"Error: {e}")
        input("Press Enter to exit...")