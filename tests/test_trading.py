import unittest
from unittest.mock import Mock, patch

import start


class TradingTests(unittest.TestCase):
    def test_rounds_to_step_multiple(self):
        self.assertEqual(start.format_decimal('1.239', '0.05'), '1.20')
        self.assertEqual(start.format_decimal('123', '5'), '120')
        self.assertEqual(start.format_decimal('0.000000019', '0.00000001'), '0.00000001')

    def test_nonpositive_tick_is_rejected(self):
        for tick in ('0', '-1', 'NaN'):
            with self.assertRaises(ValueError):
                start.format_decimal('1', tick)

    def test_long_and_short_prices(self):
        self.assertEqual(start.calculate_prices('LONG', 100, 1, 5, 10, '0.05'),
                         ('99.00', '94.05', '108.90'))
        self.assertEqual(start.calculate_prices('SHORT', 100, 1, 5, 10, '0.05'),
                         ('101.00', '106.05', '90.90'))

    def test_trading_builds_decimal_strings(self):
        client = Mock()
        client.execute_order.return_value = {
            'price': '99.00', 'stopLossTriggerPrice': '94.05',
            'takeProfitTriggerPrice': '108.90',
        }
        with patch.object(start, 'get_market_data', return_value=('0.05', '0.001', 100)):
            result = start.start_trading(client, Mock(), 'BTC_USDC_PERP',
                                         trading_amount=100, limit_price_percentage=1,
                                         trade_side='LONG')
        self.assertTrue(result)
        body = client.execute_order.call_args.kwargs
        self.assertEqual(body['quantity'], '1.010')
        self.assertEqual(body['price'], '99.00')
        self.assertTrue(body['postOnly'])


if __name__ == '__main__':
    unittest.main()
