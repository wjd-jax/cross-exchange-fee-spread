# 跨所资金费

一个纯本地网页工具，用于查看不同交易所之间的永续合约资金费率差，并输出做多 / 做空组合下的结算明细、按日汇总和当前周期快照。

## Features

- 支持 Binance、Bybit、Bitget、OKX、Gate.io
- 浏览器里直接输入币种、做多交易所、做空交易所、合约/现货和回看天数
- 自动计算 `利差 = 做空费率 - 做多费率`
- 默认拉取 14 天数据，支持快速切换 24 小时、3 天、7 天、14 天视图
- 支持利差走势图、走势图颗粒度选择、鼠标滚轮 / 触控板缩放和横向拖动
- 走势图同时展示汇总趋势线和实际发生资金费结算的利差点
- 同时展示逐笔结算明细、按日汇总、历史推算和当前周期快照
- 自动缓存上次输入的查询条件，刷新页面后保持配置
- 支持接入友盟 H5 统计，访问数据在友盟后台查看
- 接口错误以可复制提示展示，便于排查交易所或浏览器直连问题
- 不需要启动本地服务，也不要求 Python 运行环境

## Main Entry

[index.html](index.html)

直接双击打开即可运行。

## Analytics

页面已接入友盟 H5 统计，`appkey` 配置在 [index.html](index.html) 里的 `UMENG_APP_KEY`。本地 `file://` 预览时会跳过统计脚本，发布到 `http://` 或 `https://` 后访问数据会进入友盟后台，页面内不展示统计数据。

## Current Structure

- [index.html](index.html): 当前唯一主维护入口
- [docs/project-memory.md](docs/project-memory.md): 当前产品状态和协作记忆
- [legacy/README.md](legacy/README.md): 旧 Flask / CLI 方案说明

## Legacy

旧的 Flask、CLI 和 Python 计算逻辑已移动到 [legacy](legacy)。

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
