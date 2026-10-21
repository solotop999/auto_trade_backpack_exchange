# Backpack Exchange Python Trading Tools

[![Offline tests](https://github.com/solotop999/auto_trade_backpack_exchange/actions/workflows/tests.yml/badge.svg)](https://github.com/solotop999/auto_trade_backpack_exchange/actions/workflows/tests.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

Python API clients and a configurable trading script for Backpack Exchange. The request-signing, order-building, and market-data code is available for inspection, reuse, and community improvement.

Maintained by [@solotop999](https://github.com/solotop999). This is an independent community project, not affiliated with or endorsed by Backpack Exchange.

## Features

- Public client for market information, order books, mark prices, funding rates, and trades.
- Authenticated client for account settings, balances, positions, order execution, cancellation, and settlement history.
- ED25519 request signing with canonical parameter ordering.
- Decimal-string order payloads and tick/step rounding helpers.
- Configurable perpetual-futures trading loop with post-only entries and attached TP/SL trigger prices.
- Optional Telegram notifications.
- Offline regression tests and a GitHub Actions workflow.

The client implements a subset of the exchange API; it is not a complete SDK.

## Before running live trading

**`python start.py` uses the live exchange API and can place real orders. There is no dry-run mode.**

Before every new entry, the loop attempts to cancel **all open orders** and close **all open positions** accessible to the configured account, including positions outside `TRADING_PAIR`. Use a dedicated account or subaccount. Cleanup errors are logged; successful cleanup is not guaranteed before the loop continues.

Trading can lose money. Post-only orders can remain unfilled or be rejected. TP/SL settings do not guarantee realized PnL: fees, funding, slippage, partial fills, and trigger execution affect results. The next iteration may close a position before either trigger executes.

## Getting started

Python 3.11 is configured in CI. Offline development tests have also passed on Python 3.13; installation of the pinned dependencies on other Python versions has not been verified.

```bash
git clone https://github.com/solotop999/auto_trade_backpack_exchange.git
cd auto_trade_backpack_exchange
python -m venv venv
```

Activate the environment on Windows PowerShell:

```powershell
.\venv\Scripts\Activate.ps1
```

Or on macOS/Linux:

```bash
source venv/bin/activate
```

Install dependencies and run the offline tests:

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
```

Tests use mocked requests and a synthetic signing key. They do not require exchange credentials or place orders.

### Read-only example

This example fetches public market data without an API key:

```python
from helpers.public_API import PublicClient

client = PublicClient()
market = client.get_market("BTC_USDC_PERP")
print(market["symbol"], market["filters"])
```

### Credentials

Create an API key in the API Keys settings on [Backpack Exchange](https://backpack.exchange/). Refer to the [official API documentation](https://docs.backpack.exchange/) for authentication and permissions.

Copy `env_example` to `.env` in the repository root:

```powershell
# Windows PowerShell
Copy-Item env_example .env
```

```bash
# macOS/Linux
cp env_example .env
```

Set these values locally:

```dotenv
API_KEY=your_base64_api_public_key
API_SECRET=your_base64_ed25519_private_key
```

`API_SECRET` is the exchange API signing key, not your wallet recovery phrase. Never include credentials in commits, issues, screenshots, or shared logs. The trading script does not need withdrawal permissions.

Telegram variables are unused when `TELEGRAM_ALERT` is `false`. To enable alerts, set `TELEGRAM_MSG_TO`, `TELEGRAM_API_ID`, `TELEGRAM_API_HASH`, and `TELEGRAM_BOT_TOKEN` as shown in `env_example`.

### Configuration

Review `settings.json` before running. The checked-in values below are examples, not trading recommendations.

| Setting | Default | Meaning |
| --- | --- | --- |
| `TOTAL_TRADES` | `20` | Number of loop iterations, not confirmed fills. |
| `MIN_SLEEP` | `600` | Minimum interval delay in seconds. |
| `MAX_SLEEP` | `1200` | Maximum interval delay in seconds. |
| `TRADING_PAIR` | `BTC_USDC_PERP` | Perpetual market for new entries. |
| `TRADE_SIDE` | `SHORT` | Entry direction: `LONG` or `SHORT`. |
| `LEVERAGE_LIMIT` | `3` | Account leverage limit requested at startup. |
| `TRADING_AMOUNT` | `150` | Target entry notional in USDC before quantity rounding, not a margin budget. |
| `LIMIT_PRICE_PERCENTAGE` | `0.05` | Entry offset from the index price, in percent. |
| `STOP_LOSS_USDC` | `10` | Input for calculating the stop-loss percentage. |
| `TAKE_PROFIT_USDC` | `10` | Input for calculating the take-profit percentage. |
| `AUTO_REPAY_BORROWS` | `true` | Account auto-repayment setting requested at startup. |
| `TELEGRAM_ALERT` | `false` | Enable Telegram notifications. |

TP/SL percentages are calculated as `configured USDC amount / TRADING_AMOUNT * 100`, then applied to the rounded entry price. They are not guaranteed net PnL targets.

After reviewing the account-wide cleanup behavior and configuration, start the live loop:

```bash
python start.py
```

Logs are written to `trade.log` in the current working directory. Also check order and position status in the exchange interface.

## API compatibility

Compared with the [official Backpack documentation](https://docs.backpack.exchange/) on **October 21, 2026**:

- Signed parameters are sorted alphabetically. Boolean values use lowercase `true`/`false` in signatures and GET queries.
- Order decimal fields and account leverage are sent as strings. Trading helpers round down to actual tick/step multiples.
- `clientId=0` is preserved; single-order cancellation requires exactly one of `clientId` or `orderId`.
- `postOnly` is preserved when `timeInForce` is supplied.
- `execute_order()` supports `triggerBy`, `stopLossTriggerBy`, `takeProfitTriggerBy`, and the paired `slippageTolerance` / `slippageToleranceType` fields.
- `autoRealizePnl` is no longer writable. Passing it to `update_account()` raises a local error.
- `/history/pnl` was removed on August 7, 2025. `get_pnl_history()` raises `NotImplementedError`. `get_settlement_history()` returns settlement events with a different schema, not an equivalent PnL history response.
- HTTP requests have a 30-second timeout. Orders are not automatically resubmitted after network failures, when execution status may be uncertain.

## Validation and limitations

The 19 offline tests cover signing, API payloads, decimal handling, identifier validation, removed API behavior, and trading helpers. GitHub Actions runs the tests on pushes and pull requests.

A live read-only check confirmed the `BTC_USDC_PERP` market filters and mark-price response shape. Authenticated order execution, cancellation, TP/SL execution, and Telegram delivery have not been validated end to end in this update. CI does not perform live trading.

Current limitations include:

- No dry-run mode or fill-confirmation state machine.
- Account-wide, best-effort cleanup.
- A trading strategy built for the configured perpetual-market workflow; other market types need separate validation.
- Possible incompatibilities as the exchange API evolves.

## Project structure

```text
helpers/
  backpack_exchange.py  Authenticated API client
  public_API.py         Public market-data client
  orders.py             Account-wide cleanup helpers
  format_types.py       API enums
tests/
  test_api.py           API and signing regression tests
  test_trading.py       Price and quantity helper tests
.github/workflows/
  tests.yml             Offline CI workflow
start.py                Live trading loop
settings.json           Example configuration
env_example             Credential template without real keys
```

## Contributing

Bug reports, documentation improvements, tests, and focused pull requests are welcome.

1. Open an [issue](https://github.com/solotop999/auto_trade_backpack_exchange/issues) describing the problem or proposal. Discuss larger changes first.
2. Fork the repository and create a branch.
3. Keep changes focused. Add regression tests for behavior changes, using mocked HTTP requests rather than live trading credentials.
4. Run `python -m unittest discover -s tests -v`.
5. Open a pull request explaining the change, relevant API documentation, and validation performed.

Bug reports should include your Python version, reproduction steps, expected behavior, and a sanitized error message. Remove API secrets, Telegram credentials, and private account information.

Useful future contributions include a dry-run mode, symbol-scoped cleanup, fill-confirmation handling, and additional API error-path tests. These are proposed improvements, not implemented features.

For suspected credential-exposure vulnerabilities, do not publish secrets or exploit details in public issues. Use GitHub private vulnerability reporting if that option is available on the repository.

## License

Released under the [MIT License](LICENSE). See the license for permissions, conditions, and the warranty disclaimer. Dependencies retain their respective licenses.
