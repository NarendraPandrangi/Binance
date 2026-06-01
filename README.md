
# Binance Futures Testnet Trading Bot

A small Python CLI application for placing orders on the Binance USDT-M Futures Testnet.

It supports:

- MARKET orders
- LIMIT orders
- STOP-LIMIT orders as an optional bonus feature
- BUY and SELL sides
- CLI input validation
- Lightweight browser UI
- Structured API/client and CLI layers
- File logging for requests, responses, and errors

## Setup

1. Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Install dependencies:

```powershell
pip install -r requirements.txt
```

3. Create Binance Futures Testnet credentials:

- Register at the Binance Futures Testnet.
- Generate an API key and secret.
- Make sure the account has test USDT available.

4. Create a `.env` file from the example:

```powershell
Copy-Item .env.example .env
```

Then edit `.env`:

```text
BINANCE_API_KEY=your_testnet_api_key
BINANCE_API_SECRET=your_testnet_api_secret
BINANCE_FUTURES_BASE_URL=https://testnet.binancefuture.com
```

## Run Examples

Show help:

```powershell
python -m trading_bot.cli --help
```

Place a MARKET BUY order:

```powershell
python -m trading_bot.cli --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001
```

Place a LIMIT SELL order:

```powershell
python -m trading_bot.cli --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.001 --price 75000
```

Place a STOP-LIMIT SELL order:

```powershell
python -m trading_bot.cli --symbol BTCUSDT --side SELL --type STOP_LIMIT --quantity 0.001 --price 74000 --stop-price 74500
```

Preview an order without calling Binance:

```powershell
python -m trading_bot.cli --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001 --dry-run
```

## Browser UI

Start the local UI:

```powershell
python -m trading_bot.web
```

Then open:

```text
http://127.0.0.1:8000
```

The UI uses the same `.env` credentials, validation, order placement logic, and log file as the CLI. Keep **Dry run** checked while testing the form. Uncheck it only when you want to submit the order to Binance Futures Testnet.

## Output

The CLI prints:

- Order request summary
- Binance response details
- Success or failure message

Example response fields include:

- `orderId`
- `status`
- `executedQty`
- `avgPrice`

## Logs

Runtime logs are written to:

```text
logs/trading_bot.log
```

The log file includes API request metadata, response bodies, and error details. API secrets are never logged.

To satisfy the task deliverable, run at least one successful MARKET order and one successful LIMIT order, then include the generated `logs/trading_bot.log` file in your zip or GitHub repository submission.

## Assumptions

- This app targets Binance USDT-M Futures Testnet only.
- The default base URL is `https://testnet.binancefuture.com`.
- LIMIT and STOP-LIMIT orders use `GTC` time in force.
- Quantity and price must be positive numbers.
- For MARKET orders, Binance may return `avgPrice` as `0.00000` until the order is fully processed by the exchange.


Screen Shots 
1) Web UI : 
<img width="1216" height="718" alt="Screenshot 2026-06-01 122200" src="https://github.com/user-attachments/assets/2ff758a0-dfc7-4766-b3e9-d22ac1f8b836" />

2) Logs :
<img width="1801" height="778" alt="Screenshot 2026-06-01 123030" src="https://github.com/user-attachments/assets/d9c75326-86f7-4a7f-b912-4fbe9b6998ad" />
<img width="1829" height="716" alt="Screenshot 2026-06-01 123106" src="https://github.com/user-attachments/assets/621fa801-dc52-46c3-914a-19021289375e" />

