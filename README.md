# cross-exchange-fee-spread

一个纯本地网页工具，用于查看不同交易所之间的永续合约资金费率差，并输出做多 / 做空组合下的结算明细、按日汇总和当前周期快照。

## Features

- 支持 Binance、Bybit、Bitget、OKX、Gate.io
- 浏览器里直接输入币种、做多交易所、做空交易所、合约/现货和回看天数
- 自动计算 `利差 = 做空费率 - 做多费率`
- 同时展示逐笔结算明细、按日汇总、历史推算和当前周期快照
- 不需要启动本地服务，也不要求 Python 运行环境

## Main Entry

[index.html](/Users/admin/Documents/Codex/2026-04-27/new-chat/cross-exchange-fee-spread/index.html)

直接双击打开即可运行。

## Current Structure

- [index.html](/Users/admin/Documents/Codex/2026-04-27/new-chat/cross-exchange-fee-spread/index.html): 当前唯一主维护入口
- [docs/project-memory.md](/Users/admin/Documents/Codex/2026-04-27/new-chat/cross-exchange-fee-spread/docs/project-memory.md): 当前产品状态和协作记忆
- [legacy/README.md](/Users/admin/Documents/Codex/2026-04-27/new-chat/cross-exchange-fee-spread/legacy/README.md): 旧 Flask / CLI 方案说明

## Legacy

旧的 Flask、CLI 和 Python 计算逻辑已移动到 [legacy](/Users/admin/Documents/Codex/2026-04-27/new-chat/cross-exchange-fee-spread/legacy)。

这些文件现在只作为归档保留，不再是默认维护主线。

## Current Limitations

- 页面目前还是本地单机版，没有任务历史和结果持久化
- 不同交易所返回格式不一致，极端情况下可能只返回部分结果
- 纯本地 HTML 版本依赖交易所接口允许浏览器直接跨域访问
- 某些交易所接口在浏览器直连下可能超时或被拦截，页面当前会尽量自动降级而不是卡死

## Suggested Next Steps

1. 增加 CSV / JSON 导出
2. 增加最近查询记录
3. 增加更细的错误提示和请求日志
4. 后续再拆成前后端分离也很顺
