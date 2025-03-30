import requests


class PublicClient:
    def __init__(self):
        self.base_url = "https://api.backpack.exchange/"
        self.session = requests.session()

    def _get(self, endpoint, params=None):
        response = self.session.get(url=f"{self.base_url}{endpoint}", params=params)

        if 200 <= response.status_code < 300:
            if response.status_code == 204:
                return None
            try:
                response_data = response.json()
                return response_data
            except ValueError:
                return response.text
        else:
            try:
                error = response.json()
                raise Exception(f"API Error: {error.get('code')} - {error.get('message')}")
            except ValueError:
                raise Exception(f"HTTP Error {response.status_code}: {response.text}")

    # ================================================================
    # Assets - Assets and collateral data.
    # ================================================================
    def get_assets(self):
        """
        Retrieves all the assets that are supported by the exchange.
        """
        return self._get("api/v1/assets")

    def get_collateral(self):
        """
        Get collateral parameters for assets.
        """
        return self._get("api/v1/collateral")

    # ================================================================
    # Market - Public market data.
    # ================================================================
    def get_markets(self):
        """
        Retrieves all the markets that are supported by the exchange.
        """
        return self._get("api/v1/markets")

    def get_market(self, symbol: str):
        """
        Retrieves a market supported by the exchange.
        """
        return self._get("api/v1/market", params={"symbol": symbol})


    def get_depth(self, symbol: str):
        """
        Retrieves the order book depth for a given market symbol.
        """
        return self._get("api/v1/depth", params={"symbol": symbol})

    def get_klines(self, symbol: str, interval: str, start_time: int, end_time: int = None):
        """
        Get K-Lines for the given market symbol, providing a startTime and optionally an endTime.
        If no endTime is provided, the current time will be used.
        """
        params = {"symbol": symbol, "interval": interval, "startTime": start_time}
        if end_time is not None:
            params["endTime"] = end_time
        return self._get("api/v1/klines", params=params)

    def get_mark_price(self, symbol: str):
        """
        Retrieves mark price, index price and funding rate for the given market symbol.
        """
        return self._get("api/v1/markPrices", params={"symbol": symbol})

    def get_open_interest(self, symbol: str):
        """
        Retrieves the current open interest for the given market.
        """
        return self._get("api/v1/openInterest", params={"symbol": symbol})

    def get_funding_interval_rates(self, symbol: str, limit: int = 100, offset: int = 0):
        """
        Funding interval rate history for futures.
        """
        params = {"symbol": symbol, "limit": limit, "offset": offset}
        return self._get("api/v1/fundingRates", params=params)

    # ================================================================
    # System - Exchange system status.
    # ================================================================

    def get_status(self):
        """
        Get the system status, and the status message, if any.
        """
        return self._get("api/v1/status")

    def send_ping(self) -> str:
        """
        Responds with pong.
        """
        return self._get("api/v1/ping")

    def get_system_time(self) -> str:
        """
        Retrieves the current system time.
        """
        return self._get("api/v1/time")

    # ================================================================
    # Trades - Public trade data.
    # ================================================================
    def get_recent_trades(self, symbol: str, limit: int = 100):
        """
        Retrieve the most recent trades for a symbol. This is public data and is not specific to any account.
        The maximum available recent trades is 1000. If you need more than 1000 trades use the historical trades
        endpoint.
        """
        params = {"symbol": symbol, "limit": limit}
        return self._get("api/v1/trades", params=params)

    def get_historical_trades(self, symbol: str, limit: int = 100, offset: int = 0):
        """
        Retrieves all historical trades for the given symbol. This is public trade data and is not specific to any
        account.
        """
        params = {"symbol": symbol, "limit": limit, "offset": offset}
        return self._get("api/v1/trades/history", params=params)

    # ================================================================
    # Borrow Lend Markets - Borrowing and lending.
    # ================================================================
    def get_borrow_lend_markets(self):
        """
        Get all borrow lend markets information.

        Returns:
            List of dictionaries containing market information including state, interest rates,
            quantities, utilization rates and other parameters for each market.
        """
        return self._get("api/v1/borrowLend/markets")

    def get_borrow_lend_market_history(self, interval: str, symbol: str = None):
        """
        Get borrow lend market history for specified interval and optional symbol.

        Args:
            interval (str): Time interval - must be one of: "1d", "1w", "1month", "1year"
            symbol (str, optional): Market symbol to query. If not set, all markets are returned.

        Returns:
            Historical borrow lend market data for the specified interval and symbol.
        """
        params = {"interval": interval}
        if symbol:
            params["symbol"] = symbol
        return self._get("api/v1/borrowLend/markets/history", params=params)