import logging
from helpers.format_types import OrderSide, OrderType
from helpers.backpack_exchange import BackpackExchange

def close_all_orders(client: BackpackExchange):
    """
    Close all open orders for the account.
    """
    try:
        open_orders = client.get_open_orders()
        if not open_orders:
            logging.info("No open order to close.")
            return

        for order in open_orders:
            client.cancel_open_order(symbol=order['symbol'], orderId=order["id"])
            logging.info(f"Cancelled order: {order['symbol']}, ID: {order['id']}")
    except Exception as e:
        logging.error(f"Error closing orders: {e}")


def close_all_positions(client: BackpackExchange):
    """
    Close all open positions for the account.
    """
    try:
        positions_status = client.get_open_positions()
        if not positions_status:
            logging.info("No open positions to close.")
            return

        for position in positions_status:
            side = (
                OrderSide.SELL.value
                if float(position['netQuantity']) > 0  # Long position
                else OrderSide.BUY.value  # Short position
            )
            logging.info(f"Closing position: {position['symbol']}, netQuantity: {position['netQuantity']}, side: {side}")

            order_status = client.execute_order(
                orderType=OrderType.MARKET.value,
                side=side,
                symbol=position['symbol'],
                quantity=abs(float(position['netQuantity'])),
                reduceOnly=True,
            )
            logging.info(f"Closed position status: {order_status['status']}")

    except Exception as e:
        logging.error(f"Error in close_all_positions: {e}")
