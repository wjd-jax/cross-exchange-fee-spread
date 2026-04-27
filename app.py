from datetime import datetime, timedelta

from flask import Flask, render_template, request

from src.funding_analysis import DEFAULT_EXCHANGES, analyze_funding_rates

app = Flask(__name__)


def default_form_data():
    return {
        "symbol": "KAT",
        "long_exchange": "okx",
        "short_exchange": "binance",
        "lookback_days": "10",
    }


@app.route("/", methods=["GET", "POST"])
def index():
    form_data = default_form_data()
    result = None
    error = None

    if request.method == "POST":
        form_data = {
            "symbol": request.form.get("symbol", "").strip().upper(),
            "long_exchange": request.form.get("long_exchange", "").strip().lower(),
            "short_exchange": request.form.get("short_exchange", "").strip().lower(),
            "lookback_days": request.form.get("lookback_days", "").strip(),
        }
        try:
            lookback_days = int(form_data["lookback_days"])
            if lookback_days <= 0:
                raise ValueError("天数必须大于 0")

            end_dt = datetime.now().replace(second=0, microsecond=0)
            start_dt = end_dt - timedelta(days=lookback_days)
            result = analyze_funding_rates(
                symbol=form_data["symbol"],
                long_exchange=form_data["long_exchange"],
                short_exchange=form_data["short_exchange"],
                start_dt=start_dt,
                end_dt=end_dt,
            )
        except Exception as exc:
            error = str(exc)

    return render_template(
        "index.html",
        exchanges=DEFAULT_EXCHANGES,
        form_data=form_data,
        result=result,
        error=error,
    )


if __name__ == "__main__":
    app.run(debug=True)
