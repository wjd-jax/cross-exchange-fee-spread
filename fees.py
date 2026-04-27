#!/usr/bin/env python3

from datetime import datetime, timedelta

from src.funding_analysis import (
    DEFAULT_EXCHANGES,
    analyze_funding_rates,
    print_cli_report,
)


def build_default_config():
    end_time = datetime.now().replace(second=0, microsecond=0)
    start_time = end_time - timedelta(days=10)
    return {
        "symbol": "KAT",
        "long_exchange": "okx",
        "short_exchange": "binance",
        "start_time": start_time,
        "end_time": end_time,
    }


def main():
    config = build_default_config()
    result = analyze_funding_rates(
        symbol=config["symbol"],
        long_exchange=config["long_exchange"],
        short_exchange=config["short_exchange"],
        start_dt=config["start_time"],
        end_dt=config["end_time"],
    )
    print_cli_report(result)


if __name__ == "__main__":
    main()
