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

    def _normalize_settlement_time(self, dt: datetime) -> datetime:
        dt = dt.replace(microsecond=0)
        if dt.second >= 59:
            dt += timedelta(seconds=60 - dt.second)
        return dt.replace(second=0, microsecond=0)

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
                    dt = self._normalize_settlement_time(datetime.fromtimestamp(item["fundingTime"] / 1000))
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
                dt = self._normalize_settlement_time(datetime.fromtimestamp(ts / 1000))
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
                dt = self._normalize_settlement_time(datetime.fromtimestamp(ts / 1000))
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
                    dt = self._normalize_settlement_time(datetime.fromtimestamp(ts / 1000))
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
                dt = self._normalize_settlement_time(datetime.fromtimestamp(item["t"]))
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


def _percentile(values: List[float], quantile: float) -> Optional[float]:
    if not values:
        return None
    sorted_values = sorted(values)
    if len(sorted_values) == 1:
        return sorted_values[0]
    index = (len(sorted_values) - 1) * quantile
    lower = int(index)
    upper = min(lower + 1, len(sorted_values) - 1)
    weight = index - lower
    return sorted_values[lower] + (sorted_values[upper] - sorted_values[lower]) * weight


def _infer_interval_hours_from_rows(rows: List[Dict]) -> Optional[float]:
    timestamps = sorted({int(row["time"].timestamp()) for row in rows if row.get("time") is not None})
    if len(timestamps) < 2:
        return None
    intervals = []
    for index in range(1, len(timestamps)):
        delta_seconds = timestamps[index] - timestamps[index - 1]
        if delta_seconds > 0:
            intervals.append(delta_seconds / 3600)
    if not intervals:
        return None
    intervals.sort()
    return intervals[len(intervals) // 2]


def _calc_basis_percent(mark_price: Optional[float], index_price: Optional[float]) -> Optional[float]:
    if mark_price is None or index_price in (None, 0):
        return None
    return ((mark_price - index_price) / index_price) * 100


def _build_current_snapshot(
    exchange: str,
    current_rate: Optional[float],
    cycle_hours: Optional[float],
    mark_price: Optional[float] = None,
    index_price: Optional[float] = None,
    next_funding_time: Optional[str] = None,
) -> Dict:
    normalized_8h_rate = None
    dailyized_rate = None
    annualized_rate = None
    if current_rate is not None and cycle_hours not in (None, 0):
        normalized_8h_rate = current_rate * (8 / cycle_hours)
        dailyized_rate = current_rate * (24 / cycle_hours)
        annualized_rate = dailyized_rate * 365

    return {
        "exchange": exchange,
        "current_rate": current_rate,
        "cycle_hours": cycle_hours,
        "normalized_8h_rate": normalized_8h_rate,
        "dailyized_rate": dailyized_rate,
        "annualized_rate": annualized_rate,
        "mark_price": mark_price,
        "index_price": index_price,
        "basis_percent": _calc_basis_percent(mark_price, index_price),
        "next_funding_time": next_funding_time,
    }


def _exchange_method_map(calc: FundingFeeCalculator) -> Dict[str, Callable[[datetime, datetime], List[Dict]]]:
    return {
        "binance": calc.get_binance_funding_rates,
        "bybit": calc.get_bybit_funding_rates,
        "bitget": calc.get_bitget_funding_rates,
        "okx": calc.get_okx_funding_rates,
        "gateio": calc.get_gateio_funding_rates,
    }


def _fetch_current_snapshot(
    calc: FundingFeeCalculator,
    exchange: str,
    historical_rows: List[Dict],
) -> Dict:
    try:
        if exchange == "binance":
            resp = requests.get(
                "https://fapi.binance.com/fapi/v1/premiumIndex",
                params={"symbol": calc.symbol + "USDT"},
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            cycle_hours = _infer_interval_hours_from_rows(historical_rows)
            next_funding_time = datetime.fromtimestamp(data["nextFundingTime"] / 1000).strftime("%Y-%m-%d %H:%M")
            return _build_current_snapshot(
                exchange=exchange,
                current_rate=float(data["lastFundingRate"]) * 100,
                cycle_hours=cycle_hours,
                mark_price=float(data["markPrice"]),
                index_price=float(data["indexPrice"]),
                next_funding_time=next_funding_time,
            )

        if exchange == "bybit":
            resp = requests.get(
                "https://api.bybit.com/v5/market/tickers",
                params={"category": "linear", "symbol": calc.symbol + "USDT"},
                timeout=10,
            )
            resp.raise_for_status()
            item = resp.json()["result"]["list"][0]
            next_funding_time = datetime.fromtimestamp(int(item["nextFundingTime"]) / 1000).strftime("%Y-%m-%d %H:%M")
            return _build_current_snapshot(
                exchange=exchange,
                current_rate=float(item["fundingRate"]) * 100,
                cycle_hours=float(item["fundingIntervalHour"]),
                mark_price=float(item["markPrice"]),
                index_price=float(item["indexPrice"]),
                next_funding_time=next_funding_time,
            )

        if exchange == "bitget":
            funding_resp = requests.get(
                "https://api.bitget.com/api/v3/market/current-fund-rate",
                params={"symbol": calc.symbol + "USDT"},
                timeout=10,
            )
            funding_resp.raise_for_status()
            funding_item = funding_resp.json()["data"][0]

            ticker_resp = requests.get(
                "https://api.bitget.com/api/v2/mix/market/ticker",
                params={"symbol": calc.symbol + "USDT", "productType": "USDT-FUTURES"},
                timeout=10,
            )
            ticker_resp.raise_for_status()
            ticker_item = ticker_resp.json()["data"][0]

            next_funding_time = datetime.fromtimestamp(int(funding_item["nextUpdate"]) / 1000).strftime("%Y-%m-%d %H:%M")
            return _build_current_snapshot(
                exchange=exchange,
                current_rate=float(funding_item["fundingRate"]) * 100,
                cycle_hours=float(funding_item["fundingRateInterval"]),
                mark_price=float(ticker_item["markPrice"]),
                index_price=float(ticker_item["indexPrice"]),
                next_funding_time=next_funding_time,
            )

        if exchange == "okx":
            for inst_id in [f"{calc.symbol}-USD-SWAP", f"{calc.symbol}-USDT-SWAP"]:
                try:
                    funding_resp = requests.get(
                        "https://www.okx.com/api/v5/public/funding-rate",
                        params={"instId": inst_id},
                        timeout=10,
                    )
                    funding_resp.raise_for_status()
                    funding_data = funding_resp.json()
                    if funding_data.get("code") != "0" or not funding_data.get("data"):
                        continue
                    item = funding_data["data"][0]

                    mark_resp = requests.get(
                        "https://www.okx.com/api/v5/public/mark-price",
                        params={"instType": "SWAP", "instId": inst_id},
                        timeout=10,
                    )
                    mark_resp.raise_for_status()
                    mark_data = mark_resp.json()
                    mark_price = None
                    if mark_data.get("code") == "0" and mark_data.get("data"):
                        mark_price = float(mark_data["data"][0]["markPx"])

                    cycle_hours = _infer_interval_hours_from_rows(historical_rows)
                    next_funding_time = datetime.fromtimestamp(int(item["nextFundingTime"]) / 1000).strftime("%Y-%m-%d %H:%M")
                    return _build_current_snapshot(
                        exchange=exchange,
                        current_rate=float(item["fundingRate"]) * 100,
                        cycle_hours=cycle_hours,
                        mark_price=mark_price,
                        index_price=None,
                        next_funding_time=next_funding_time,
                    )
                except Exception:
                    continue
            raise ValueError("OKX 当前快照不可用")

        if exchange == "gateio":
            resp = requests.get(
                f"https://api.gateio.ws/api/v4/futures/usdt/contracts/{calc.symbol}_USDT",
                timeout=10,
            )
            resp.raise_for_status()
            item = resp.json()
            next_funding_time = datetime.fromtimestamp(int(item["funding_next_apply"])).strftime("%Y-%m-%d %H:%M")
            return _build_current_snapshot(
                exchange=exchange,
                current_rate=float(item["funding_rate"]) * 100,
                cycle_hours=float(item["funding_interval"]) / 3600,
                mark_price=float(item["mark_price"]),
                index_price=float(item["index_price"]),
                next_funding_time=next_funding_time,
            )
    except Exception as exc:
        calc._append_warning(f"{exchange.upper()} 当前周期快照获取失败: {exc}")

    return _build_current_snapshot(exchange=exchange, current_rate=None, cycle_hours=None)


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
    long_current_snapshot = _fetch_current_snapshot(calc, long_exchange, long_raw)
    short_current_snapshot = _fetch_current_snapshot(calc, short_exchange, short_raw)

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
    comparable_times = []
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

        if spread is not None:
            comparable_times.append(int(settled_at.timestamp() * 1000))

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

    latest_daily = daily_rows[-1] if daily_rows else None

    latest_spread = None
    for row in reversed(settlement_rows):
        if row["spread"] is not None:
            latest_spread = row["spread"]
            break

    settlements_per_day = None
    if len(comparable_times) >= 2:
        intervals = []
        for index in range(1, len(comparable_times)):
            interval = comparable_times[index] - comparable_times[index - 1]
            if interval > 0:
                intervals.append(interval)
        if intervals:
            intervals.sort()
            median_interval = intervals[len(intervals) // 2]
            settlements_per_day = (24 * 60 * 60 * 1000) / median_interval

    predicted_daily_spread = None
    if latest_spread is not None and settlements_per_day is not None:
        predicted_daily_spread = latest_spread * settlements_per_day

    predicted_annualized_spread = predicted_daily_spread * 365 if predicted_daily_spread is not None else None
    cycle_hours = (24 / settlements_per_day) if settlements_per_day else None

    historical_daily_spreads = [row["spread"] for row in daily_rows]
    median_daily_spread = _percentile(historical_daily_spreads, 0.5)
    upper_quartile_daily_spread = _percentile(historical_daily_spreads, 0.75)
    positive_ratio = (
        sum(1 for value in historical_daily_spreads if value > 0) / len(historical_daily_spreads)
        if historical_daily_spreads
        else None
    )

    if predicted_daily_spread is None or median_daily_spread is None or upper_quartile_daily_spread is None or positive_ratio is None:
        recommendation = {
            "tone": "warn",
            "title": "历史建议：先观望",
            "message": "同结算点历史样本不足，暂时无法结合资费周期和历史分布给出可靠建议。",
        }
    else:
        positive_ratio_pct = positive_ratio * 100
        if predicted_daily_spread <= 0:
            recommendation = {
                "tone": "error",
                "title": "历史建议：暂不进入",
                "message": (
                    f"当前预测当日总利差为 {predicted_daily_spread:.4f}% ，低于 0；"
                    f"历史正收益日占比约 {positive_ratio_pct:.0f}%。"
                    "更适合先观望，等待资费重新转正后再评估。"
                ),
            }
        elif positive_ratio >= 0.6 and predicted_daily_spread >= upper_quartile_daily_spread:
            recommendation = {
                "tone": "good",
                "title": "历史建议：可以考虑进入",
                "message": (
                    f"历史正收益日占比约 {positive_ratio_pct:.0f}%，"
                    f"当前预测当日总利差 {predicted_daily_spread:.4f}% 高于历史 75 分位 {upper_quartile_daily_spread:.4f}%。"
                    "若手续费、滑点和资金占用成本可控，可考虑现在进入套取资费。"
                ),
            }
        elif positive_ratio >= 0.55 and predicted_daily_spread >= median_daily_spread:
            recommendation = {
                "tone": "info",
                "title": "历史建议：有条件参与",
                "message": (
                    f"历史正收益日占比约 {positive_ratio_pct:.0f}%，"
                    f"当前预测当日总利差 {predicted_daily_spread:.4f}% 高于历史中位 {median_daily_spread:.4f}%，"
                    "但还没有进入最强区间。更适合轻仓试探，或等待更好的资费窗口。"
                ),
            }
        else:
            recommendation = {
                "tone": "warn",
                "title": "历史建议：继续观察",
                "message": (
                    f"当前预测当日总利差 {predicted_daily_spread:.4f}% 未明显高于历史中位 {median_daily_spread:.4f}%，"
                    f"历史正收益日占比约 {positive_ratio_pct:.0f}%。"
                    "相比马上进入，更适合继续等待更好的价差和资费位置。"
                ),
            }

    current_snapshot = {
        "long": long_current_snapshot,
        "short": short_current_snapshot,
        "comparable_8h_spread": None,
        "comparable_daily_spread": None,
        "comparable_annualized_spread": None,
    }
    if (
        long_current_snapshot["normalized_8h_rate"] is not None
        and short_current_snapshot["normalized_8h_rate"] is not None
    ):
        current_snapshot["comparable_8h_spread"] = (
            short_current_snapshot["normalized_8h_rate"] - long_current_snapshot["normalized_8h_rate"]
        )
        current_snapshot["comparable_daily_spread"] = current_snapshot["comparable_8h_spread"] * 3
        current_snapshot["comparable_annualized_spread"] = current_snapshot["comparable_daily_spread"] * 365

    return {
        "symbol": symbol,
        "long_exchange": long_exchange,
        "short_exchange": short_exchange,
        "start_time": start_dt.strftime("%Y-%m-%d %H:%M"),
        "end_time": end_dt.strftime("%Y-%m-%d %H:%M"),
        "settlement_rows": settlement_rows,
        "daily_rows": daily_rows,
        "latest_daily": latest_daily,
        "prediction": {
            "latest_spread": latest_spread,
            "settlements_per_day": settlements_per_day,
            "cycle_hours": cycle_hours,
            "predicted_daily_spread": predicted_daily_spread,
            "predicted_annualized_spread": predicted_annualized_spread,
        },
        "recommendation": recommendation,
        "current_snapshot": current_snapshot,
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
