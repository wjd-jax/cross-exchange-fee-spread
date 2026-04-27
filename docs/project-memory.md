# Project Memory

## Current Product Shape

- Preferred entry is the pure local page: `index.html`
- Flask version is still kept as a fallback when some exchange APIs do not behave well under `file://`
- Core use case is comparing perpetual funding-rate spread across exchanges for a long/short hedge

## Current UI Defaults

- Default symbol: `KAT`
- Default long exchange: `bybit`
- Default short exchange: `bn` (display name for Binance)
- Form layout is tuned so long/short exchanges share one row and start/end time share one row on normal desktop widths

## Current Calculation Rules

- Spread is defined as `short funding rate - long funding rate`
- Settlement spread is only calculated when both sides have data at the same settlement time
- Missing data on one side is not treated as `0`
- Long-side funding impact:
  - positive funding rate -> pay funding
  - negative funding rate -> receive funding
- Short-side funding impact:
  - positive funding rate -> receive funding
  - negative funding rate -> pay funding

## Current Summary Cards

- Long total and short total show actual position impact rather than raw exchange rate sum
- Tags use:
  - `收资费`
  - `付资费`
  - `持平`
- Total spread card uses:
  - `盈利`
  - `亏损`
  - `持平`
- Daily interest line estimates `%/天` from:
  - the latest comparable spread
  - estimated settlements per day from recent comparable timestamps

## Current Repo Notes

- `index.html` is the main maintained surface right now
- `templates/index.html` and `app.py` remain for the Flask path
- `fees.py` and `src/funding_analysis.py` remain for script/server fallback usage
