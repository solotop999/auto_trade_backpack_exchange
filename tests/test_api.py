import base64
import unittest
from unittest.mock import Mock, patch

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from helpers.backpack_exchange import BackpackExchange
from helpers.format_types import OrderSide, OrderType, TimeInForce
from helpers.orders import close_all_positions
from helpers.public_API import PublicClient


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.seed = bytes(range(32))
        self.client = BackpackExchange('test-key', base64.b64encode(self.seed).decode())
        self.client.session = Mock()
        self.response = Mock(status_code=200)
        self.response.json.return_value = {'status': 'New'}
        for method in ('get', 'post', 'patch', 'delete'):
            getattr(self.client.session, method).return_value = self.response

    def test_signature_matches_documented_canonical_order(self):
        params = {'symbol': 'BTC_USDC_PERP', 'reduceOnly': False, 'clientId': 0}
        headers = self.client._generate_signature('orderExecute', 1234, params)
        message = (b'instruction=orderExecute&clientId=0&reduceOnly=false'
                   b'&symbol=BTC_USDC_PERP&timestamp=1234&window=5000')
        Ed25519PrivateKey.from_private_bytes(self.seed).public_key().verify(
            base64.b64decode(headers['X-Signature']), message)
        self.assertIs(params['reduceOnly'], False)

    def test_get_boolean_matches_signed_value_and_path_is_normalized(self):
        self.client._send_request('GET', '/api/v1/test', 'test', {'enabled': False})
        args, kwargs = self.client.session.get.call_args
        self.assertEqual(args[0], 'https://api.backpack.exchange/api/v1/test')
        self.assertEqual(kwargs['params'], {'enabled': 'false'})
        self.assertEqual(kwargs['timeout'], 30)

    def test_account_update_uses_decimal_string(self):
        self.client.update_account(leverageLimit=3, autoRepayBorrows=False)
        self.assertEqual(self.client.session.patch.call_args.kwargs['json'],
                         {'leverageLimit': '3', 'autoRepayBorrows': False})

    def test_removed_account_setting_fails_before_network(self):
        with self.assertRaises(ValueError):
            self.client.update_account(autoRealizePnl=True)
        self.client.session.patch.assert_not_called()

    def test_removed_pnl_endpoint_is_not_requested(self):
        with self.assertRaises(NotImplementedError):
            self.client.get_pnl_history()
        self.client.session.get.assert_not_called()

    def test_settlement_endpoint_and_instruction(self):
        with patch.object(self.client, '_send_request') as send:
            self.client.get_settlement_history(limit=25, offset=0)
        send.assert_called_once_with('GET', 'wapi/v1/history/settlement',
                                     'settlementHistoryQueryAll', {'limit': 25, 'offset': 0})

    def test_cancel_accepts_zero_client_id(self):
        self.client.cancel_open_order('BTC_USDC_PERP', clientId=0)
        self.assertEqual(self.client.session.delete.call_args.kwargs['json']['clientId'], 0)

    def test_cancel_requires_exactly_one_identifier(self):
        for kwargs in ({}, {'clientId': 0, 'orderId': '123'}):
            with self.assertRaises(ValueError):
                self.client.cancel_open_order('BTC_USDC_PERP', **kwargs)
        self.client.session.delete.assert_not_called()

    def test_limit_preserves_post_only_with_time_in_force(self):
        self.client.execute_order(OrderType.LIMIT, OrderSide.BUY, 'BTC_USDC_PERP',
                                  price=100, quantity=0.001, clientId=0,
                                  postOnly=True, timeInForce=TimeInForce.GTC,
                                  stopLossTriggerBy='MarkPrice',
                                  slippageTolerance='1', slippageToleranceType='Percent')
        body = self.client.session.post.call_args.kwargs['json']
        self.assertIs(body['postOnly'], True)
        self.assertEqual(body['timeInForce'], 'GTC')
        self.assertEqual(body['clientId'], 0)
        self.assertEqual(body['quantity'], '0.001')
        self.assertEqual(body['stopLossTriggerBy'], 'MarkPrice')
        self.assertEqual(body['slippageToleranceType'], 'Percent')

    def test_market_requires_one_quantity(self):
        for kwargs in ({}, {'quantity': '1', 'quoteQuantity': '10'}, {'quantity': 'NaN'},
                       {'quantity': '0'}, {'quantity': '-1'}):
            with self.assertRaises(ValueError):
                self.client.execute_order('Market', 'Bid', 'BTC_USDC_PERP', **kwargs)
        self.client.session.post.assert_not_called()

    def test_market_quote_quantity_is_supported(self):
        self.client.execute_order('Market', 'Bid', 'BTC_USDC', quoteQuantity='10')
        body = self.client.session.post.call_args.kwargs['json']
        self.assertEqual(body['quoteQuantity'], '10')
        self.assertNotIn('quantity', body)

    def test_public_markets_are_unsigned(self):
        self.client.get_markets()
        self.assertEqual(self.client.session.get.call_args.kwargs['headers'], {})

    def test_204_response(self):
        self.response.status_code = 204
        self.assertIsNone(self.client.update_account(leverageLimit='3'))

    def test_public_requests_have_timeout(self):
        public = PublicClient()
        public.session = Mock()
        public.session.get.return_value = self.response
        public.get_market('BTC_USDC_PERP')
        self.assertEqual(public.session.get.call_args.kwargs['timeout'], 30)

    def test_close_positions_preserves_decimal_precision_and_skips_zero(self):
        client = Mock()
        client.get_open_positions.return_value = [
            {'symbol': 'BTC_USDC_PERP', 'netQuantity': '-0.123456789123456789'},
            {'symbol': 'ETH_USDC_PERP', 'netQuantity': '0'},
        ]
        client.execute_order.return_value = {'status': 'Filled'}
        close_all_positions(client)
        client.execute_order.assert_called_once_with(
            orderType='Market', side='Bid', symbol='BTC_USDC_PERP',
            quantity='0.123456789123456789', reduceOnly=True)


if __name__ == '__main__':
    unittest.main()
