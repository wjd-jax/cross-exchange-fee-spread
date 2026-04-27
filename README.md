# cross-exchange-fee-spread

一个本地网页工具，用于查看不同交易所之间的永续合约资金费率差，并输出做多 / 做空组合下的逐笔结算明细与按日汇总。

## Features

- 支持 Binance、Bybit、Bitget、OKX、Gate.io
- 浏览器里直接输入币种、做多交易所、做空交易所和时间范围
- 自动计算 `利差 = 做空费率 - 做多费率`
- 同时展示逐笔结算明细和按日汇总结果
- 保留命令行入口，便于脚本化使用

## Project Structure

- [app.py](/Users/admin/Documents/Codex/2026-04-27/new-chat/cross-exchange-fee-spread/app.py): 本地网页入口
- [src/funding_analysis.py](/Users/admin/Documents/Codex/2026-04-27/new-chat/cross-exchange-fee-spread/src/funding_analysis.py): 核心采集和分析逻辑
- [templates/index.html](/Users/admin/Documents/Codex/2026-04-27/new-chat/cross-exchange-fee-spread/templates/index.html): 页面模板
- [fees.py](/Users/admin/Documents/Codex/2026-04-27/new-chat/cross-exchange-fee-spread/fees.py): 命令行入口

## Pure Local HTML

直接打开这个文件即可：

[index.html](/Users/admin/Documents/Codex/2026-04-27/new-chat/cross-exchange-fee-spread/index.html)

不需要启动 Flask，也不需要本地端口。

## Optional Setup

```bash
python3 -m pip install -r requirements.txt
```

## Run Flask Version

```bash
python3 app.py
```

启动后在浏览器打开：

`http://127.0.0.1:5000`

## Run CLI Version

```bash
python3 fees.py
```

默认配置在 [fees.py](/Users/admin/Documents/Codex/2026-04-27/new-chat/cross-exchange-fee-spread/fees.py) 里，适合快速临时跑一次。

## Current Limitations

- 页面目前还是本地单机版，没有任务历史和结果持久化
- 不同交易所返回格式不一致，极端情况下可能只返回部分结果
- 纯本地 HTML 版本依赖交易所接口允许浏览器直接跨域访问
- Flask 版本仍然保留，适合当某些交易所限制 `file://` 请求时兜底使用

## Suggested Next Steps

1. 增加 CSV / JSON 导出
2. 增加最近查询记录
3. 增加更细的错误提示和请求日志
4. 后续再拆成前后端分离也很顺
