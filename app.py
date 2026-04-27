from datetime import datetime, timedelta

from flask import Flask, render_template, request

from src.funding_analysis import DEFAULT_EXCHANGES, analyze_funding_rates

app = Flask(__name__)


def default_form_data():
    end_time = datetime.now().replace(second=0, microsecond=0)
    start_time = end_time - timedelta(days=10)
    return {
        "symbol": "KAT",
        "long_exchange": "okx",
        "short_exchange": "binance",
        "start_time": start_time.strftime("%Y-%m-%dT%H:%M"),
        "end_time": end_time.strftime("%Y-%m-%dT%H:%M"),
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
            "start_time": request.form.get("start_time", "").strip(),
            "end_time": request.form.get("end_time", "").strip(),
        }
        try:
            result = analyze_funding_rates(
                symbol=form_data["symbol"],
                long_exchange=form_data["long_exchange"],
                short_exchange=form_data["short_exchange"],
                start_dt=datetime.strptime(form_data["start_time"], "%Y-%m-%dT%H:%M"),
                end_dt=datetime.strptime(form_data["end_time"], "%Y-%m-%dT%H:%M"),
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
