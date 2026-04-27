from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Callable, Dict, List, Optional

import requests
import urllib3

urllib3.disable_warnings()

DEFAULT_EXCHANGES = ["binance", "bybit", "bitget", "okx", "gateio"]

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"


class FundingFeeCalculator:
    def __init__(self, symbol: str):
        self.symbol = symbol.upper()
        self.binance_url = "https://fapi.binance.com/fapi/v1/fundingRate"
        self.bitget_url = "https://api.bitget.com/api/v3/market/history-fund-rate"
        self.bybit_url = "https://api.bybit.com/v5/market/funding/history"
        self.okx_url = "https://www.okx.com/api/v5/public/funding-rate-history"
        self.gateio_url = "https://api.gateio.ws/api/v4/futures/usdt/funding_rate"
        self.warnings: List[str] = []

    def _append_warning(self, message: str):
        self.warnings.append(message)

    def get_binance_funding_rates(self, start_dt: datetime, end_dt: datetime) -> List[Dict]:
        rates = []
        current_start = int(start_dt.timestamp() * 1000)
        end_ts = int((end_dt + timedelta(seconds=2)).timestamp() * 1000)
        try:
            params = {
                "symbol": self.symbol + "USDT",
                "startTime": current_start,
                "endTime": end_ts,
                "limit": 1000,
            }
            resp = requests.get(self.binance_url, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, list):
                for item in data:
                    dt = datetime.fromtimestamp(item["fundingTime"] / 1000).replace(microsecond=0)
                    if dt.second == 59:
                        dt += timedelta(seconds=1)
                    rates.append({"time": dt, "rate": float(item["fundingRate"]) * 100})
        except Exception as exc:
            self._append_warning(f"Binance 获取失败: {exc}")
        return rates

    def get_bitget_funding_rates(self, start_dt: datetime, end_dt: datetime) -> List[Dict]:
        rates = []
        current_start = int(start_dt.timestamp() * 1000)
        end_ts = int((end_dt + timedelta(seconds=2)).timestamp() * 1000)
        try:
            params = {
                "category": "USDT-FUTURES",
                "symbol": self.symbol + "USDT",
                "startTime": current_start,
                "endTime": end_ts,
                "limit": 100,
            }
            resp = requests.get(self.bitget_url, params=params, timeout=10)
            resp.raise_for_status()
            payload = resp.json().get("data", {})
            data = payload.get("resultList", []) if isinstance(payload, dict) else []
            for item in data:
                ts = int(item["fundingRateTimestamp"])
                dt = datetime.fromtimestamp(ts / 1000).replace(microsecond=0)
                if dt < start_dt or dt > (end_dt + timedelta(seconds=2)):
                    continue
                rates.append({"time": dt, "rate": float(item["fundingRate"]) * 100})
        except Exception as exc:
            self._append_warning(f"Bitget 获取失败: {exc}")
        return rates

    def get_bybit_funding_rates(self, start_dt: datetime, end_dt: datetime) -> List[Dict]:
        rates = []
        current_end = int((end_dt + timedelta(seconds=2)).timestamp() * 1000)
        try:
            params = {
                "category": "linear",
                "symbol": self.symbol + "USDT",
                "endTime": current_end,
                "limit": 200,
            }
            resp = requests.get(self.bybit_url, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json().get("result", {}).get("list", [])
            for item in data:
                ts = int(item["fundingRateTimestamp"])
                dt = datetime.fromtimestamp(ts / 1000).replace(microsecond=0)
                if dt < start_dt or dt > (end_dt + timedelta(seconds=2)):
                    continue
                rates.append({"time": dt, "rate": float(item["fundingRate"]) * 100})
        except Exception as exc:
            self._append_warning(f"Bybit 获取失败: {exc}")
        return rates

    def get_okx_funding_rates(self, start_dt: datetime, end_dt: datetime) -> List[Dict]:
        rates = []
        inst_id_formats = [
            f"{self.symbol}-USD-SWAP",
            f"{self.symbol}-USDT-SWAP",
        ]

        for inst_id in inst_id_formats:
            try:
                params = {"instId": inst_id, "limit": 100}
                resp = requests.get(self.okx_url, params=params, timeout=15)
                resp.raise_for_status()
                data = resp.json()
                if data.get("code") != "0":
                    self._append_warning(f"OKX 返回错误 ({inst_id}): {data.get('msg')}")
                    continue

                items = data.get("data", [])
                for item in items:
                    ts = int(item["fundingTime"])
                    dt = datetime.fromtimestamp(ts / 1000).replace(microsecond=0)
                    if dt < start_dt or dt > end_dt:
                        continue
                    rates.append({"time": dt, "rate": float(item["realizedRate"]) * 100})

                if rates:
                    return rates
            except Exception as exc:
                self._append_warning(f"OKX 获取失败 ({inst_id}): {exc}")

        return rates

    def get_gateio_funding_rates(self, start_dt: datetime, end_dt: datetime) -> List[Dict]:
        rates = []
        current_start = int(start_dt.timestamp())
        end_ts = int((end_dt + timedelta(seconds=2)).timestamp())
        try:
            params = {
                "contract": f"{self.symbol}_USDT",
                "from": current_start,
                "to": end_ts,
                "limit": 100,
            }
            resp = requests.get(self.gateio_url, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            for item in data:
                dt = datetime.fromtimestamp(item["t"]).replace(second=0)
                if dt < start_dt or dt > end_dt:
                    continue
                rates.append({"time": dt, "rate": float(item["r"]) * 100})
        except Exception as exc:
            self._append_warning(f"Gate.io 获取失败: {exc}")
        return rates


def _format_cli_cell(val: Optional[float], width: int) -> str:
    if val is None:
        return f"{'-':>{width + 1}}"
    text = f"{val:>{width}.4f}%"
    if round(val, 8) == 0:
        return f"{YELLOW}{text}{RESET}"
    if val > 0:
        return f"{GREEN}{text}{RESET}"
    return f"{RED}{text}{RESET}"


def _exchange_method_map(calc: FundingFeeCalculator) -> Dict[str, Callable[[datetime, datetime], List[Dict]]]:
    return {
        "binance": calc.get_binance_funding_rates,
        "bybit": calc.get_bybit_funding_rates,
        "bitget": calc.get_bitget_funding_rates,
        "okx": calc.get_okx_funding_rates,
        "gateio": calc.get_gateio_funding_rates,
    }


def analyze_funding_rates(
    symbol: str,
    long_exchange: str,
    short_exchange: str,
    start_dt: datetime,
    end_dt: datetime,
):
    symbol = symbol.upper().strip()
    long_exchange = long_exchange.strip().lower()
    short_exchange = short_exchange.strip().lower()

    if long_exchange not in DEFAULT_EXCHANGES:
        raise ValueError(f"不支持的做多交易所: {long_exchange}")
    if short_exchange not in DEFAULT_EXCHANGES:
        raise ValueError(f"不支持的做空交易所: {short_exchange}")
    if not symbol:
        raise ValueError("币种不能为空")
    if start_dt >= end_dt:
        raise ValueError("开始时间必须早于结束时间")

    calc = FundingFeeCalculator(symbol)
    methods = _exchange_method_map(calc)

    long_raw = methods[long_exchange](start_dt, end_dt)
    short_raw = methods[short_exchange](start_dt, end_dt)

    merged_data: Dict[datetime, Dict[str, Optional[float]]] = {}
    for row in long_raw:
        settled_at = row["time"]
        merged_data.setdefault(settled_at, {long_exchange: None, short_exchange: None})
        merged_data[settled_at][long_exchange] = row["rate"]

    for row in short_raw:
        settled_at = row["time"]
        merged_data.setdefault(settled_at, {long_exchange: None, short_exchange: None})
        merged_data[settled_at][short_exchange] = row["rate"]

    daily_stats = defaultdict(lambda: {long_exchange: 0.0, short_exchange: 0.0})
    settlement_rows = []
    total_long = 0.0
    total_short = 0.0

    for settled_at in sorted(merged_data.keys()):
        values = merged_data[settled_at]
        long_val = values[long_exchange]
        short_val = values[short_exchange]
        spread = short_val - long_val if long_val is not None and short_val is not None else None

        if settled_at.hour == 0 and settled_at.minute == 0:
            stats_date = (settled_at - timedelta(days=1)).strftime("%Y-%m-%d")
        else:
            stats_date = settled_at.strftime("%Y-%m-%d")

        if long_val is not None:
            daily_stats[stats_date][long_exchange] += long_val
            total_long += long_val
        if short_val is not None:
            daily_stats[stats_date][short_exchange] += short_val
            total_short += short_val

        settlement_rows.append(
            {
                "settlement_time": settled_at.strftime("%Y-%m-%d %H:%M"),
                "long_rate": long_val,
                "short_rate": short_val,
                "spread": spread,
                "is_aligned": long_val is not None and short_val is not None,
            }
        )

    daily_rows = []
    for date_key in sorted(daily_stats.keys()):
        long_day = daily_stats[date_key][long_exchange]
        short_day = daily_stats[date_key][short_exchange]
        daily_rows.append(
            {
                "date": date_key,
                "long_rate": long_day,
                "short_rate": short_day,
                "spread": short_day - long_day,
            }
        )

    return {
        "symbol": symbol,
        "long_exchange": long_exchange,
        "short_exchange": short_exchange,
        "start_time": start_dt.strftime("%Y-%m-%d %H:%M"),
        "end_time": end_dt.strftime("%Y-%m-%d %H:%M"),
        "settlement_rows": settlement_rows,
        "daily_rows": daily_rows,
        "totals": {
            "long_rate": total_long,
            "short_rate": total_short,
            "spread": total_short - total_long,
        },
        "warnings": calc.warnings,
    }


def print_cli_report(result: Dict):
    long_exchange = result["long_exchange"]
    short_exchange = result["short_exchange"]
    w_t, w_l, w_s, w_d = 20, 15, 15, 15
    header = (
        f"{'结算时间':>{w_t}} | "
        f"{f'{long_exchange.capitalize()} %':>{w_l + 1}} | "
        f"{f'{short_exchange.capitalize()} %':>{w_s + 1}} | "
        f"{'利差 % (S-L)':>{w_d + 1}}"
    )
    divider = "-" * len(header)

    print(f"\n正在分析 {result['symbol']} 资金费率对冲表格...")
    print(f"做多交易所：{long_exchange} | 做空交易所：{short_exchange}")

    print("\n" + "=" * len(header))
    print("【 详细结算明细 】")
    print(header)
    print(divider)
    print(f"注：利差为负表示做多{long_exchange}的费率高于做空{short_exchange}，多头需要支付更多费用")
    print(f"    利差为正表示做多{long_exchange}的费率低于做空{short_exchange}，多头可以收取费用")
    print("    若某个结算时刻只有单边交易所有数据，则另一边显示为 -，且该行不计算利差")
    print(divider)

    for row in result["settlement_rows"]:
        print(
            f"{row['settlement_time']:>{w_t}} | "
            f"{_format_cli_cell(row['long_rate'], w_l)} | "
            f"{_format_cli_cell(row['short_rate'], w_s)} | "
            f"{_format_cli_cell(row['spread'], w_d)}"
        )

    totals = result["totals"]
    print(divider)
    print(
        f"{'累计总计':>{w_t}} | "
        f"{_format_cli_cell(totals['long_rate'], w_l)} | "
        f"{_format_cli_cell(totals['short_rate'], w_s)} | "
        f"{_format_cli_cell(totals['spread'], w_d)}"
    )
    print("=" * len(header))

    print("\n" + "=" * len(header))
    print("【 每日汇总统计 (按日归集) 】")
    daily_header = (
        f"{'统计日期':>{w_t}} | "
        f"{f'{long_exchange.capitalize()} 累计':>{w_l + 1}} | "
        f"{f'{short_exchange.capitalize()} 累计':>{w_s + 1}} | "
        f"{'当日总利差':>{w_d + 1}}"
    )
    print(daily_header)
    print(divider)

    for row in result["daily_rows"]:
        print(
            f"{row['date']:>{w_t}} | "
            f"{_format_cli_cell(row['long_rate'], w_l)} | "
            f"{_format_cli_cell(row['short_rate'], w_s)} | "
            f"{_format_cli_cell(row['spread'], w_d)}"
        )

    print("=" * len(header) + "\n")

    if result["warnings"]:
        print("【 警告信息 】")
        for warning in result["warnings"]:
            print(f"- {warning}")
