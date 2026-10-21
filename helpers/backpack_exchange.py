import time
import base64
import requests
from enum import Enum
from decimal import Decimal
from cryptography.hazmat.primitives.asymmetric import ed25519

from helpers.format_types import (
    CancelOrderType,
    FillType,
    MarketType,
    OrderSide,
    OrderType,
    SelfTradePrevention,
    SettlementSourceFilter,
    TimeInForce,
)

class BackpackExchange:
    BASE_URL = "https://api.backpack.exchange/"

    def __init__(self, api_key: str, private_key: str):
        """
        Initialize the BackpackExchange client.

        :param api_key: Your API key (Base64 encoded verifying key of the ED25519 keypair).
        :param private_key: Your private key for signing requests.
        """
        self.api_key = api_key
        self.private_key = ed25519.Ed25519PrivateKey.from_private_bytes(base64.b64decode(private_key))
        self.session = requests.session()
        self.window = 5000


    def _send_request(self, method, endpoint, action, params=None):
        """
        Send authenticated request to API endpoint.
        """
        method = method.upper()
        if method not in {"GET", "DELETE", "PATCH", "PUT", "POST"}:
            raise ValueError(f"Unsupported HTTP method: {method}")
        url = f"{self.BASE_URL.rstrip('/')}/{endpoint.lstrip('/')}"
        params = {k: v for k, v in (params or {}).items() if v is not None}
        params = {k: (v.value if isinstance(v, Enum) else v) for k, v in params.items()}
        ts = int(time.time() * 1e3)
        headers = self._generate_signature(action, ts, params) if action else {}
        if method == "GET":
            params = {k: str(v).lower() if isinstance(v, bool) else v for k, v in params.items()}

        try:
            if method == "GET":
                response = self.session.get(url, headers=headers, params=params, timeout=30)
            elif method == "DELETE":
                response = self.session.delete(url, headers=headers, json=params, timeout=30)
            elif method == "PATCH":
                response = self.session.patch(url, headers=headers, json=params, timeout=30)
            elif method == "PUT":
                response = self.session.put(url, headers=headers, json=params, timeout=30)
            else:
                response = self.session.post(url, headers=headers, json=params, timeout=30)

            if 200 <= response.status_code < 300:
                if response.status_code == 204:
                    return None
                try:
                    return response.json()
                except ValueError:
                    return response.text
            else:
                try:
                    error = response.json()
                    raise Exception(f"API Error: {error.get('code') if isinstance(error, dict) else response.status_code} - {error.get('message') if isinstance(error, dict) else error}")
                except ValueError:
                    raise Exception(f"HTTP Error {response.status_code}: {response.text}")

        except requests.exceptions.RequestException as e:
            raise Exception(f"Request failed: {str(e)}")

    def _generate_signature(self, action: str, timestamp: int, params=None):
        if params:
            params = params.copy()
            for key, value in params.items():
                if isinstance(value, bool):
                    params[key] = str(value).lower()

            param_str = "&" + "&".join(f"{k}={v}" for k, v in sorted(params.items()))
        else:
            param_str = ""
        if not param_str:
            param_str = ""
        sign_str = f"instruction={action}{param_str}&timestamp={timestamp}&window={self.window}"
        signature = base64.b64encode(self.private_key.sign(sign_str.encode())).decode()
        return {
            "X-API-Key": self.api_key,
            "X-Signature": signature,
            "X-Timestamp": str(timestamp),
            "X-Window": str(self.window),
            "Content-Type": "application/json; charset=utf-8",
        }

    def get_account(self):
        """
        Retrieves account settings.
        """
        return self._send_request("GET", "api/v1/account", "accountQuery")
    
    def update_account(
        self,
        autoBorrowSettlements: bool = None,
        autoLend: bool = None,
        autoRealizePnl: bool = None,
        autoRepayBorrows: bool = None,
        leverageLimit: str = None,
    ) -> None:
        """
        Update account settings.
        """
        data = {}
        if autoBorrowSettlements is not None:
            data["autoBorrowSettlements"] = autoBorrowSettlements
        if autoLend is not None:
            data["autoLend"] = autoLend
        if autoRealizePnl is not None:
            raise ValueError("autoRealizePnl is no longer writable; Backpack realizes PnL continuously")
        if autoRepayBorrows is not None:
            data["autoRepayBorrows"] = autoRepayBorrows
        if leverageLimit is not None:
            data["leverageLimit"] = str(leverageLimit)

        self._send_request("PATCH", "api/v1/account", "accountUpdate", data)

    def get_balances(self):
        """
        Get account balances.
        """
        return self._send_request("GET", "api/v1/capital", "balanceQuery")

    def get_open_orders(self, symbol: str = None):
        """
        Get all open orders.

        :param symbol: Market symbol to filter orders (optional).
        """
        params = {"symbol": symbol} if symbol else {}
        return self._send_request("GET", "api/v1/orders", "orderQueryAll", params=params)

    def cancel_open_order(self, symbol: str, clientId: int = None, orderId: str = None):
        """
        Cancels an open order from the order book.

        One of orderId or clientId must be specified. If both are specified then the request will be rejected.
        """
        if (clientId is None) == (orderId is None):
            raise ValueError("Specify exactly one of clientId or orderId")
        data = {"symbol": symbol}
        if clientId is not None:
            data["clientId"] = clientId
        if orderId is not None:
            data["orderId"] = orderId
        return self._send_request("DELETE", "api/v1/order", "orderCancel", data)
    
    def get_markets(self):
        """
        Get all supported markets.
        """
        return self._send_request("GET", "api/v1/markets", None)
    
    def get_open_positions(self):
        """
        Retrieves account position summary.
        """
        return self._send_request("GET", "api/v1/position", "positionQuery")

    
    def get_pnl_history(self, subaccountId: int = None, symbol: str = None, limit: int = 100, offset: int = 0):
        """
        History of profit and loss realization for an account.
        """
        raise NotImplementedError(
            "Backpack removed /history/pnl on 2025-08-07. "
            "Use get_settlement_history() for settlements; its response is not the old PnL schema."
        )

    def get_settlement_history(self, limit: int = 100, offset: int = 0):
        """Retrieve settlement events using the current history endpoint."""
        return self._send_request(
            "GET", "wapi/v1/history/settlement", "settlementHistoryQueryAll",
            {"limit": limit, "offset": offset},
        )

    def get_max_order_quantity(
        self,
        symbol: str,
        side: str,
        price: str = None,
        reduceOnly: bool = None,
        autoBorrow: bool = None,
        autoBorrowRepay: bool = None,
        autoLendRedeem: bool = None,
    ) -> str:
        """
        Retrieves the maximum quantity an account can trade for a given symbol based on the account's balances, existing exposure and margin requirements.
        """
        params = {"symbol": symbol, "side": side}

        if price is not None:
            params["price"] = price
        if reduceOnly is not None:
            params["reduceOnly"] = reduceOnly
        if autoBorrow is not None:
            params["autoBorrow"] = autoBorrow
        if autoBorrowRepay is not None:
            params["autoBorrowRepay"] = autoBorrowRepay
        if autoLendRedeem is not None:
            params["autoLendRedeem"] = autoLendRedeem

        return self._send_request("GET", "api/v1/account/limits/order", "maxOrderQuantity", params)
    
    def execute_order(
        self,
        orderType: OrderType,
        side: OrderSide,
        symbol: str,
        postOnly: bool = False,
        clientId: int = None,
        price: str = None,
        quantity: str = None,
        timeInForce: TimeInForce = None,
        quoteQuantity: str = None,
        selfTradePrevention: SelfTradePrevention = None,
        triggerPrice: str = None,
        reduceOnly: bool = None,
        autoBorrow: bool = None,
        autoBorrowRepay: bool = None,
        autoLend: bool = None,
        autoLendRedeem: bool = None,
        stopLossTriggerPrice: str = None,
        stopLossLimitPrice: str = None,
        takeProfitTriggerPrice: str = None,
        takeProfitLimitPrice: str = None,
        triggerQuantity: str = None,
        triggerBy: str = None,
        stopLossTriggerBy: str = None,
        takeProfitTriggerBy: str = None,
        slippageTolerance: str = None,
        slippageToleranceType: str = None,
    ):
        """
        Executes an order on the order book. If the order is not immediately filled,
        it will be placed on the order book.

        Args:
            orderType: Order type, market or limit.
            side: Order side, Bid (buy) or Ask (sell).
            symbol: The market for the order.
            postOnly: Only post liquidity, do not take liquidity.
            clientId: Custom order id.
            price: The order price if this is a limit order.
            quantity: The order quantity. Market orders must specify either a quantity or quoteQuantity.
            timeInForce: How long the order is good for (GTC, IOC, FOK).
            quoteQuantity: The maximum amount of the quote asset to spend (Ask) or receive (Bid) for market orders.
            selfTradePrevention: Action to take if the user crosses themselves in the order book.
            triggerPrice: Trigger price if this is a conditional order.
            reduceOnly: If true then the order can only reduce the position. Futures only.
            autoBorrow: If true then the order can borrow. Spot margin only.
            autoBorrowRepay: If true then the order can repay a borrow. Spot margin only.
            autoLend: If true then the order can lend. Spot margin only.
            autoLendRedeem: If true then the order can redeem a lend if required. Spot margin only.
            stopLossTriggerPrice: Reference price that should trigger the stop loss order.
            stopLossLimitPrice: Stop loss limit price. If set the stop loss will be a limit order.
            takeProfitTriggerPrice: Reference price that should trigger the take profit order.
            takeProfitLimitPrice: Take profit limit price. If set the take profit will be a limit order.
            triggerQuantity: Trigger quantity type if this is a trigger order.

        Returns:
            The order execution response.
        """
        data = {
            "orderType": orderType.value if isinstance(orderType, OrderType) else orderType,
            "symbol": symbol,
            "side": side.value if isinstance(side, OrderSide) else side,
        }

        if orderType == OrderType.LIMIT or orderType == "Limit":
            data["price"] = price
            data["quantity"] = quantity
            if price is None or quantity is None:
                raise ValueError("Limit orders require price and quantity")
            data["postOnly"] = postOnly
            if timeInForce:
                data["timeInForce"] = timeInForce.value if isinstance(timeInForce, TimeInForce) else timeInForce

        if orderType == OrderType.MARKET or orderType == "Market":
            if (quantity is None) == (quoteQuantity is None):
                raise ValueError("Market orders require exactly one of quantity or quoteQuantity")
            if quantity is not None:
                data["quantity"] = quantity
            else:
                data["quoteQuantity"] = quoteQuantity

        if clientId is not None:
            data["clientId"] = clientId

        if selfTradePrevention:
            data["selfTradePrevention"] = (
                selfTradePrevention.value
                if isinstance(selfTradePrevention, SelfTradePrevention)
                else selfTradePrevention
            )

        if triggerPrice:
            data["triggerPrice"] = triggerPrice

        if reduceOnly is not None:
            data["reduceOnly"] = reduceOnly

        if autoBorrow is not None:
            data["autoBorrow"] = autoBorrow

        if autoBorrowRepay is not None:
            data["autoBorrowRepay"] = autoBorrowRepay

        if autoLend is not None:
            data["autoLend"] = autoLend

        if autoLendRedeem is not None:
            data["autoLendRedeem"] = autoLendRedeem

        if stopLossTriggerPrice:
            data["stopLossTriggerPrice"] = stopLossTriggerPrice

        if stopLossLimitPrice:
            data["stopLossLimitPrice"] = stopLossLimitPrice

        if takeProfitTriggerPrice:
            data["takeProfitTriggerPrice"] = takeProfitTriggerPrice

        if takeProfitLimitPrice:
            data["takeProfitLimitPrice"] = takeProfitLimitPrice

        if triggerQuantity:
            data["triggerQuantity"] = triggerQuantity

        if data["orderType"] not in {"Limit", "Market"}:
            raise ValueError("orderType must be Limit or Market")
        if data["side"] not in {"Bid", "Ask"}:
            raise ValueError("side must be Bid or Ask")
        if selfTradePrevention is not None and data["selfTradePrevention"] not in {
            "RejectTaker", "RejectMaker", "RejectBoth"
        }:
            raise ValueError("Unsupported selfTradePrevention")
        for field, value in {
            "triggerBy": triggerBy, "stopLossTriggerBy": stopLossTriggerBy,
            "takeProfitTriggerBy": takeProfitTriggerBy,
        }.items():
            if value is not None:
                if value not in {"MarkPrice", "LastPrice", "IndexPrice"}:
                    raise ValueError(f"Unsupported {field}")
                data[field] = value
        if (slippageTolerance is None) != (slippageToleranceType is None):
            raise ValueError("Provide both slippageTolerance and slippageToleranceType")
        if slippageToleranceType is not None:
            if slippageToleranceType not in {"TickSize", "Percent"}:
                raise ValueError("Unsupported slippageToleranceType")
            data["slippageToleranceType"] = slippageToleranceType
            data["slippageTolerance"] = slippageTolerance
        for field in (
            "price", "quantity", "quoteQuantity", "triggerPrice", "triggerQuantity",
            "stopLossTriggerPrice", "stopLossLimitPrice", "takeProfitTriggerPrice",
            "takeProfitLimitPrice", "slippageTolerance",
        ):
            if field in data:
                value = Decimal(str(data[field]))
                if not value.is_finite() or value <= 0:
                    raise ValueError(f"{field} must be a finite positive decimal")
                data[field] = format(value, "f")

        return self._send_request("POST", "api/v1/order", "orderExecute", data)



