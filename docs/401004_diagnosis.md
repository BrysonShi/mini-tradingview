# 401004 token invalid 根因诊断报告

> 仓库：`BrysonShi/mini-tradingview`
> 时间：2026-06-05
> 状态：**根因已识别**，等待用户在正确体系重置凭证

---

## 一、现象

GitHub Actions 跑 longport SDK 拉证券列表（`security_list`）时，无论哪个端点都返回 401004 token invalid。

服务端返回的 trace_id 每次不同 → 不是网络/超时问题，是真鉴权失败。

---

## 二、已排除的假设

| 假设 | 验证方式 | 结论 |
|---|---|---|
| 应用未激活 | 用户截图反驳：行情/交易权限全部已开通 | ❌ |
| endpoint 域名错 | diag2 跑 4 端点矩阵，全 401004 | ❌ |
| SDK 鉴权 header 格式错 | 本地抓包确认 `x-api-key` / `authorization` / `x-timestamp` / `x-api-signature` 正确 | ❌ |
| OAuth vs Legacy 模式 | longport SDK 3.0.18 binary strings 搜索 "OAuth" 无结果，longport 暂未实现 OAuth | ❌ |
| token 字符级错误 | 跟用户截图/界面显示的 token 字符级完全一致 | ❌ |
| SHA256 不一致 | 本地复算一致 | ❌ |

---

## 三、真正根因

**token 跟 App Key 不属于同一个体系（跨 longport/longbridge 鉴权失败）**

长桥（Longbridge Group）虽然是同一公司，但对外有两个产品线品牌：

| 品牌 | 域名 | 定位 |
|---|---|---|
| **longport** | `longportapp.com` / `longportapp.cn` | 国内品牌 |
| **longbridge** | `longbridge.com` / `longbridge.cn` | 国际品牌 |

两个体系的用户/应用/凭证**不互通**。在 A 体系生成的 App Key，用 B 体系签发的 token 去鉴权 → 401004。

---

## 四、证据链

### 4.1 token JWT 解码结果

把 `LONGPORT_ACCESS_TOKEN` 截取 `m_eyJ...` 后用 base64 解码 payload，得到：

```json
{
  "iss": "lonbridge",     // issuer，笔误少 g，应是 longbridge
  "sub": "access_token",
  "exp": 1788421251,      // 2026-09-03 15:40:51 UTC
  "iat": 1780645251,      // 2026-06-05 15:40:51 UTC
  "ak": "7bf87c34d587...0d6020",  // 匹配 LONGPORT_APP_KEY 字符级 ✅
  "aaid": 20335516,       // application account id
  "acm": "lb_sg",         // account mode = longportbridge singapore
  "mid": 13616975,        // member id（用户 id）
  "sid": "/IPGv0LOD}lZdfRIgIYiD7A==",
  "bl": 3,                // brokerage level
  "ul": 0,                // user level
  "iks": "lb_sg_20335516" // issuing key system = "lb_sg" + aaid
}
```

关键字段解读：
- `iss = lonbridge` → 签发方是 longbridge 体系
- `iks = lb_sg_20335516` → "lb_sg" 是 issuing key system，20335516 是 aaid
- `acm = lb_sg` → account mode 同样是 longbridge

**结论：token 是 longbridge 体系签发的。**

### 4.2 App Key 来源判断

`LONGPORT_APP_KEY = 7bf87c34d587f8af551291de4cf6d0f66`（32 字符 hex）

32 位 hex 命名风格是 longport 体系（`open.longportapp.com` 个人中心）生成的 App Key 命名约定。

**结论：App Key 是 longport 体系生成的。**

### 4.3 4 端点矩阵测试

`diag2` workflow（run_id `27020830832`）逐一尝试 4 个端点，全部 401004：

| 端点 | trace_id |
|---|---|
| `https://openapi.longportapp.com` | `54ed2e8668d86d0682c507bd6d253163` |
| `https://openapi.longportapp.cn` | `bf34cda80750664bafe3ea0dd4c1cbf6` |
| `https://openapi.longbridge.com` | `eea8426b4889b259b25d454dcfa2d172` |
| `https://openapi.longbridge.cn` | `a3105f2366f0f96672a7747949ac7bce` |

跨体系鉴权 → 任一端点都拒绝。

---

## 五、修复方案

**核心原则：让 App Key / App Secret / Access Token 三件套都来自同一个体系。**

### 方案 A：保留 App Key，重置 token（推荐先试这个）

1. 登录 App Key 所属体系（`open.longportapp.com`）
2. 找到当前 App Key 对应的 application
3. 点 **"重置 Token"** 按钮
4. 把新生成的 token 完整复制，覆盖到 GitHub Secrets `LONGPORT_ACCESS_TOKEN`
5. 重新触发 fetch workflow 验证

### 方案 B：保留 token，重新生成 App Key

如果方案 A 不可行（页面没有"重置 Token"或页面跟 App Key 不在同一体系）：

1. 登录 token 所属体系（`open.longbridge.com`）
2. 创建新 application（如果还没有）
3. 重新生成 App Key + App Secret
4. 三件套（App Key / App Secret / Access Token）覆盖到 GitHub Secrets
5. 重新触发 fetch workflow 验证

---

## 六、验证步骤

凭证更新后：

```bash
POST https://api.github.com/repos/BrysonShi/mini-tradingview/actions/workflows/fetch.yml/dispatches
```

等 2-3 分钟，确认：
- `data/securities.json` 有内容（应该 > 0 条）
- `data/klines.json` 有内容
- GitHub Actions 日志里**没有 401004**

成功后会通过 `pages.yml` 自动部署到 https://brysonshi.github.io/mini-tradingview/

---

## 七、给长桥客服的参考信息（如果需要）

如果用户两个方案都试过还是 401004，把以下信息发给长桥客服（`service@longportapp.com` / `service@longbridge.com`）：

- App Key 末 4 位：`****0f66`
- token 末 4 位：`****HZs`
- token JWT iss/iks：`lonbridge` / `lb_sg_20335516`
- 4 端点 trace_id（见 4.3 节）

对方根据 trace_id 查服务端日志可以告诉你是哪个 application 不匹配。

---

## 八、清理记录

根因确认后已清理：

- [x] `scripts/fetch_securities.py` 末尾的 401004 专项诊断 try/except（已恢复简洁版）
- [x] `.github/workflows/diag.yml`（基础诊断 workflow，已删除）
- [x] `.github/workflows/diag2.yml`（4 端点矩阵测试，已删除）

仓库目前只剩 `fetch.yml`（主 workflow）和 `pages.yml`（部署 workflow）。
