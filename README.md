# Mini TradingView · LongPort 通用画图看板

> 基于 [LongPort OpenAPI](https://open.longportapp.com/) 的轻量 TradingView 风格画图看板，**任意 ticker 都能放进去**——不只针对某几只 ETF。

- 前端：[KLineCharts 9](https://klinecharts.com/) + [trading-chest](https://www.npmjs.com/package/trading-chest) 0.5.3（CDN 引入，零打包）
- 后端：GitHub Actions 定时拉数据 → 提交 → GitHub Pages 静态展示
- 部署：纯前端，国内外均可访问
- 画图：trading-chest 内置全套画图工具（趋势线、斐波那契回撤、通道、矩形、文字、测量、形态识别等）

---

## 1. 快速开始

### 1.1 Fork / 创建仓库

1. 在 GitHub 创建新仓库 `mini-tradingview`（私有也行）
2. 把本目录所有文件推上去

### 1.2 配置 LongPort 凭证（Secrets）

仓库 **Settings → Secrets and variables → Actions → New repository secret**，添加三个：

| Secret 名 | 来源 |
| --- | --- |
| `LONGPORT_APP_KEY` | [LongPort OpenAPI 控制台](https://open.longportapp.com/) → 应用 → App Key |
| `LONGPORT_APP_SECRET` | 同上 → App Secret |
| `LONGPORT_ACCESS_TOKEN` | 同上 → Access Token（首次需要扫码绑定） |

### 1.3 配置 GitHub Pages

**Settings → Pages → Source**: 选 `GitHub Actions`

### 1.4 首次手动触发 workflow

**Actions → Fetch Mini TradingView → Run workflow**

5-10 分钟后看 `data/securities.json` 和 `data/klines.json` 是否生成。

### 1.5 访问看板

`https://<username>.github.io/mini-tradingview/`

---

## 2. 添加你想追踪的标的

编辑 `data/symbols.json`，按 `data/symbols.example.json` 的格式添加。

支持的市场（长桥 ticker 格式）：

| 市场 | 格式 | 示例 |
| --- | --- | --- |
| 美股 | 直接用 ticker | `AAPL` / `TSLA` / `NVDA` |
| 港股 | 5 位数字 + `.HK` | `00700.HK` / `09988.HK` |
| A 股 | 6 位数字 + `.SH`（上交所）或 `.SZ`（深交所） | `600519.SH` / `000001.SZ` |
| 加密货币 | 长桥支持的币种 | `BTCUSD` / `ETHUSD` |

提交后 GitHub Actions 会自动重新拉取（也支持手动触发）。

---

## 3. 覆盖范围说明（重要）

**长桥 OpenAPI 的 `security_list` 接口只暴露 `Overnight`（夜盘）一个枚举变体**，无法通过长桥拿到全市场普通股票清单（A股/港股/美股全量）。

- ✅ `data/securities.json`：每日 06:00 北京时间自动拉取，包含**美股盘前/盘中/盘后** + **港股夜盘**标的
- ✅ `data/symbols.json`：手动添加任意 ticker，workflow 拉 K 线
- ✅ 前端「搜索」tab：从夜盘清单里搜（几千只标的，覆盖大部分美股和港股活跃票）
- ✅ 前端「手动输入」tab：输入任意 ticker（**夜盘外也能加**，但 K 线依赖 workflow 跑过才有）

> 想要"全市场清单"？需要引入第三方数据源（akshare / 东方财富 / yfinance），超出长桥 SDK 能力，本项目暂不支持。

---

## 4. 数据流

```
GitHub Actions
  ├─ 每日 06:00 北京 (22:00 UTC) → fetch_securities.py → data/securities.json
  └─ 工作日 21:00 北京 (13:00 UTC) → fetch_klines.py    → data/klines.json
                                          ↑
                                    data/symbols.json
                                          ↓
GitHub Pages
  └─ index.html ← fetch('./data/*.json')
```

## 5. 画图工具

trading-chest 0.5.3 内置工具栏（图表左/右侧）：

- **趋势类**：趋势线、射线、水平线、垂直线
- **通道类**：平行通道、回归线
- **斐波那契**：回撤、扩展、时区、扇形
- **形态类**：矩形、三角、圆弧
- **标注类**：文字、箭头、测量
- **几何类**：价格范围、日期范围

快捷键 `Alt + 拖拽`、`双击删除` 等见 trading-chest 文档。

---

## 6. 本地调试

```bash
pip install -r requirements.txt
export LONGPORT_APP_KEY=...
export LONGPORT_APP_SECRET=...
export LONGPORT_ACCESS_TOKEN=...
python scripts/fetch_securities.py
python scripts/fetch_klines.py
# 起个静态服务器
python -m http.server 8000
# 浏览器打开 http://localhost:8000
```

---

## 7. 文件结构

```
mini-tradingview/
├── .github/workflows/fetch.yml   # 双 job：securities + klines
├── .gitignore
├── README.md
├── data/
│   ├── symbols.json              # 用户维护的标的清单
│   ├── symbols.example.json      # 格式示例
│   ├── securities.json           # 自动生成：长桥夜盘清单
│   └── klines.json               # 自动生成：K 线数据
├── index.html                    # 前端（CDN 引入，无构建）
├── requirements.txt              # longport>=3.0.0
└── scripts/
    ├── fetch_securities.py       # 拉夜盘清单
    └── fetch_klines.py           # 拉 K 线
```

---

## 8. License

MIT
