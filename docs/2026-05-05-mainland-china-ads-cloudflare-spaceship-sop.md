# 中国大陆银行卡：广告平台注册、收款、Spaceship 域名与 Cloudflare Pages 部署 SOP

**日期：** 2026-05-05
**适用场景：** 你人在中国大陆，只有中国大陆银行卡；域名在 Spaceship；希望把静态工具站部署到 Cloudflare Pages，并接入 AdSense 或类似展示广告平台收款。

## 0. 先讲结论

### 最推荐路径

```text
Spaceship 买域名
-> Cloudflare 接管 DNS
-> Cloudflare Pages 部署静态工具站
-> 站点内容先做完整
-> 申请 AdSense
-> 用中国大陆银行账户接收 AdSense Wire Transfer
-> 达到付款阈值后按银行要求结汇/申报
```

### 中国大陆银行卡收款判断

AdSense 对中国付款方式的官方表里，**Wire Transfer 可用**。这意味着你的第一方案应该是：

- 用真实中国大陆身份注册 AdSense。
- 付款国家/地区选择中国。
- 添加中国大陆银行账户的国际电汇信息。
- 用银行账户本人姓名收款。
- 收到外币后按银行要求结汇到人民币。

不要把 PayPal、Payoneer、虚拟美国银行卡当第一方案。你现在只有大陆银行卡，最稳的是 AdSense + 银行电汇。

## 1. 关键风险和现实限制

### 1.1 AdSense 对大陆流量不一定友好

如果你的访问者主要在中国大陆，Google 广告脚本和广告填充可能不稳定。这个 SOP 更适合：

- 英文工具站。
- 面向海外搜索流量。
- 面向港澳台、新加坡、北美、欧洲等能正常加载 Google 广告的访问者。

如果你只想吃中国大陆流量，通常要考虑国内广告联盟，但国内广告联盟经常要求备案、主体审核、国内可访问站点和更本地化的合规流程。Cloudflare Pages + 海外域名不一定是最顺的组合。

### 1.2 不要做广告欺诈

禁止：

- 自己点广告。
- 让朋友点广告。
- 互点群。
- 机器流量。
- 诱导用户点击广告。
- 把广告伪装成按钮、结果、下载入口。
- 购买 autosurf、paid-to-click、click exchange 流量。

Google 对 invalid traffic 很敏感。账号一旦被限制或封禁，后面很难救。

### 1.3 只用大陆银行卡的收款准备

你需要提前确认自己的银行账户能接收境外汇款。准备这些信息：

| 信息 | 说明 |
| --- | --- |
| Beneficiary name | 收款人英文名/拼音，必须和银行账户持有人一致。 |
| Bank account number | 银行卡号或收款账号，按银行要求填写。 |
| Bank name in English | 例如 `BANK OF CHINA`、`CHINA MERCHANTS BANK`。 |
| SWIFT/BIC | 向开户行确认，不要网上随便抄。 |
| Bank branch address | 英文地址，部分银行要求。 |
| Intermediary bank | 有些银行可能要求中转行信息，以开户行答复为准。 |
| Currency | 通常按 USD 电汇理解，最终可在银行结汇为 RMB。 |

建议优先问这些银行：

- 中国银行
- 招商银行
- 工商银行
- 建设银行
- 交通银行

问题模板：

```text
我有 Google AdSense 境外广告收入，可能以美元电汇到个人账户。
请问我的这张银行卡/账户能不能接收境外美元电汇？
需要填写哪个 SWIFT/BIC、银行英文名、分行英文地址？
入账时是否需要提供收入说明或交易截图？
是否能在手机银行结汇成人民币？
```

## 2. 广告平台选择

### 2.1 首选：Google AdSense

适合原因：

- 小站也可以申请。
- 有中国付款方式。
- 文档和审核规则比较清楚。
- 对静态工具站友好，但内容不能太薄。

主要门槛：

- 网站必须完整可访问。
- 有原创内容和真实工具。
- 有隐私政策、联系方式、条款/免责声明。
- 不能有低质模板页、空页面、死链。
- 不能有违规内容和无效流量。

### 2.2 后续备选

| 平台 | 适合阶段 | 对你当前条件的判断 |
| --- | --- | --- |
| AdSense | MVP 到早期流量 | 第一优先级。中国大陆银行电汇可作为主收款路线。 |
| Ezoic | 有一定流量后 | 可能要求更多站点验证和支付配置，先不作为第一步。 |
| Mediavine / Raptive | 高流量内容站 | 通常要较高访问量门槛，不适合第一版。 |
| 直客广告/赞助 | 有垂直流量后 | 最终利润更高，但需要销售能力。 |
| 国内广告联盟 | 大陆流量站 | 可能需要备案和国内主体流程；与 Cloudflare 海外静态站路线不完全匹配。 |

## 3. AdSense 注册与审核 SOP

### 3.1 注册前准备站点

AdSense 审站前，至少准备：

- 首页。
- 3 个真实可用工具页。
- 6-10 篇原创指南页。
- `/privacy/`
- `/terms/`
- `/disclaimer/`
- `/about/`
- `/contact/`
- `robots.txt`
- `sitemap.xml`
- 无死链。
- 移动端可用。
- 页面能在公开互联网访问。

工具站例子：

```text
/tools/paint-calculator/
/tools/tile-calculator/
/tools/curtain-calculator/
/guides/how-much-paint/
/guides/tile-waste-rate/
/guides/curtain-fullness/
```

### 3.2 注册 AdSense

1. 进入 AdSense 官网。
2. 用你长期使用、能稳定登录的 Google 账号注册。
3. 账号类型选 Individual/个人。
4. 国家/地区选择 China/中国。
5. 姓名和地址用真实信息。
6. 地址必须能收到 PIN 邮件。
7. 添加网站域名，例如 `example.com`。
8. 按后台提示获取站点审核代码。

### 3.3 放 AdSense 审核代码

把后台给你的代码放到所有页面的 `<head>` 中。典型代码类似：

```html
<script
  async
  src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-XXXXXXXXXXXXXXXX"
  crossorigin="anonymous"></script>
```

如果你用本仓库的 `tool-sites/homecalc`：

- 修改所有 HTML 的 `<head>`。
- 或者后续改成模板/构建工具统一注入。
- 第一版手动加也行，但容易漏页面。

### 3.4 等待审核

审核期间：

- 不要频繁删页面。
- 不要改域名。
- 不要把站点关掉。
- 不要导入垃圾流量。
- 不要自己点广告。
- 保持隐私、条款、联系方式可访问。

### 3.5 审核通过后放广告位

第一版只放保守广告位：

| 位置 | 页面 | 建议 |
| --- | --- | --- |
| 指南页正文中段 | 指南页 | 第一屏正文后，不挡阅读。 |
| 工具结果下方 | 工具页 | 用户得到计算结果后再看到。 |
| 页底 | 全站 | 保守低风险。 |

不要放在：

- Calculate 按钮旁边。
- Download 按钮旁边。
- Share 按钮旁边。
- 表单输入项中间。
- 伪装成计算结果的位置。

手动广告位示例：

```html
<ins
  class="adsbygoogle"
  style="display:block"
  data-ad-client="ca-pub-XXXXXXXXXXXXXXXX"
  data-ad-slot="YYYYYYYYYY"
  data-ad-format="auto"
  data-full-width-responsive="true"></ins>
<script>
  (adsbygoogle = window.adsbygoogle || []).push({});
</script>
```

## 4. AdSense 收款 SOP：中国大陆银行卡

### 4.1 付款阈值

AdSense 通常有几个关键阈值：

| 阈值 | 作用 |
| --- | --- |
| 地址验证阈值 | 达到后 Google 会寄 PIN 验证地址。 |
| 付款方式选择阈值 | 达到后可添加付款方式。 |
| 付款阈值 | 达到后进入付款流程。常见默认是 USD 100 等值。 |

不同币种/地区阈值以 AdSense 后台为准。

### 4.2 添加银行账户

进入：

```text
AdSense -> Payments -> Payments info -> Manage payment methods
```

添加电汇信息：

- 收款人姓名：和银行账户姓名一致。
- 银行英文名：向银行确认。
- SWIFT/BIC：向开户行确认。
- 账号：按银行要求填写。
- 分行地址：如果后台要求，填银行提供的英文地址。

注意：

- 不要填亲属账户。
- 不要中英文姓名乱写。
- 不要随便复制别人银行的 SWIFT。
- 银行卡能消费不等于能收境外电汇，必须问银行。

### 4.3 税务信息

按 AdSense 后台要求填写税务信息。中国大陆个人通常会遇到非美国人士税务信息填写场景，常见是 W-8BEN 类表单路径。实际以后台为准。

注意：

- 信息必须真实。
- 国家/地区和付款资料要一致。
- 不确定税务处理时问专业人士。
- 银行入账和个人所得税申报按中国大陆法规自行处理。

### 4.4 收款与结汇

当 AdSense 付款后：

1. 在 AdSense Payments 里下载或截图付款记录。
2. 等银行入账通知。
3. 如果银行要求说明资金来源，说明为网站广告服务收入/Google AdSense advertising revenue。
4. 如需材料，提供 AdSense 付款记录、网站 URL、个人身份证明等。
5. 到银行 App 或柜台办理结汇成人民币。

可能产生：

- 中转行手续费。
- 收款行手续费。
- 汇率差。
- 入账审核时间。
- 结汇申报要求。

### 4.5 收款前检查表

- AdSense 账号国家是中国。
- 付款资料姓名和银行卡姓名一致。
- 地址 PIN 已验证。
- 税务信息已提交。
- 银行确认可收境外美元电汇。
- SWIFT/BIC 来自银行官方或客服。
- 银行 App 能处理外汇入账/结汇，或知道去哪个网点。

## 5. Spaceship 域名接入 Cloudflare SOP

### 5.1 为什么要把 DNS 切到 Cloudflare

你可以在 Spaceship 管域名，也可以在 Cloudflare 管 DNS。为了部署 Pages 自定义域名、HTTPS、WAF、缓存和后续规则，推荐：

```text
域名注册商：Spaceship
DNS 托管：Cloudflare
静态部署：Cloudflare Pages
```

切换 nameserver 后：

- 域名仍在 Spaceship 续费。
- DNS 记录在 Cloudflare 改。
- Spaceship 原 DNS 记录会不再生效。

### 5.2 在 Cloudflare 添加站点

1. 登录 Cloudflare。
2. 点击 Add a site。
3. 输入你的根域名，例如 `example.com`。
4. 选择 Free plan。
5. Cloudflare 会扫描现有 DNS。
6. 检查是否需要保留邮箱、旧站、验证记录。
7. Cloudflare 给你两个 nameserver。

### 5.3 在 Spaceship 修改 nameserver

1. 登录 Spaceship。
2. 进入 Domain List。
3. 选择你的域名。
4. 找到 Nameservers / DNS 设置。
5. 选择 Custom nameservers。
6. 填入 Cloudflare 给的两个 nameserver。
7. 保存。
8. 回到 Cloudflare 等待激活。

等待时间：

- 通常几分钟到数小时。
- 最长可能 24-48 小时。

### 5.4 切 DNS 前的备份

如果你已经在 Spaceship 配过邮箱或其他服务，切换前记录下来：

- MX 记录。
- TXT 记录。
- SPF/DKIM/DMARC。
- CNAME。
- A/AAAA。
- 域名验证记录。

切到 Cloudflare 后，手动补到 Cloudflare DNS。

## 6. Cloudflare Pages 部署 SOP

### 6.1 本仓库 MVP 路径

当前静态站在：

```text
tool-sites/homecalc/public
```

部署前替换：

- `homecalc.tools` -> 你的真实域名。
- `contact@homecalc.tools` -> 你的真实邮箱。
- `pub-XXXXXXXXXXXXXXXX` -> 你的 AdSense publisher ID。

查找命令：

```bash
rg -n "homecalc.tools|contact@homecalc.tools|XXXXXXXXXXXXXXXX" tool-sites/homecalc
```

### 6.2 方式 A：Wrangler 直传

适合快速上线。

```bash
cd tool-sites/homecalc
npm install -g wrangler
wrangler login
wrangler pages project create homecalc-tools
wrangler pages deploy public --project-name=homecalc-tools
```

部署成功后会得到：

```text
https://homecalc-tools.pages.dev
```

先打开 `*.pages.dev` 检查：

- 首页。
- 三个工具页。
- 指南页。
- 隐私/条款/免责声明。
- `robots.txt`
- `sitemap.xml`
- `ads.txt`

### 6.3 方式 B：GitHub 自动部署

适合长期维护。

1. 把代码推到 GitHub。
2. Cloudflare Dashboard -> Workers & Pages。
3. Create application -> Pages。
4. Connect to Git。
5. 选择仓库。
6. Build settings：

| 配置 | 值 |
| --- | --- |
| Root directory | `tool-sites/homecalc` |
| Build command | 留空 |
| Build output directory | `public` |

7. Deploy。

以后每次 push 会自动部署。

### 6.4 绑定自定义域名

1. 进入 Cloudflare Pages 项目。
2. 打开 Custom domains。
3. 添加根域名：`example.com`。
4. 等待证书生效。
5. 添加 `www.example.com`。
6. 设置一个主域名，另一个跳转过去。

推荐：

```text
主域名：https://example.com
www 跳转：https://example.com
```

跳转可以用：

- Cloudflare Redirect Rules / Bulk Redirects。
- 或在 Pages/Functions 后续做规则。

### 6.5 Cloudflare 基础开关

在 Cloudflare Dashboard 中设置：

- SSL/TLS：Full。
- Always Use HTTPS：开启。
- Automatic HTTPS Rewrites：开启。
- Brotli：开启。
- HTTP/3：开启。
- Web Analytics：开启。
- Bot Fight Mode：视流量情况开启。

如果你没有自己的服务器 origin，只用 Pages，SSL/TLS 配置通常不会像传统服务器那么复杂。

## 7. 上线后广告申请流程

### Day 0：部署完成

检查：

- `https://example.com/` 可访问。
- `https://example.com/sitemap.xml` 可访问。
- `https://example.com/robots.txt` 可访问。
- `https://example.com/ads.txt` 可访问。
- 所有工具正常计算。
- 手机端可用。
- 联系邮箱是真实可收信。

### Day 1：提交搜索和广告

1. 添加 Google Search Console。
2. 验证域名所有权。
3. 提交 sitemap。
4. 注册/登录 AdSense。
5. 添加站点。
6. 放审核代码。
7. 提交审核。

### Day 2-14：等审核

继续做：

- 每天补 1 篇指南。
- 每天检查 Cloudflare Analytics。
- 不买垃圾流量。
- 不改付款国家。
- 不频繁换主题。
- 不放诱导点击文案。

### 审核通过后

1. 开 Auto ads 或手动广告位。
2. 确认 `ads.txt` 状态。
3. 每天看异常流量。
4. 等达到阈值后添加付款方式、验证地址、填写税务信息。

## 8. 中国大陆收款运营 SOP

### 每月付款前

- 检查 Payments 页面是否有 hold。
- 检查付款方式是否有效。
- 检查税务信息是否有效。
- 检查地址/PIN 是否完成。
- 保留本月收入截图或导出记录。

### 收到银行通知后

1. 查看付款金额和币种。
2. 如果银行要求材料，提交：
   - AdSense payment receipt。
   - 网站 URL。
   - 身份证件。
   - 收入说明。
3. 完成入账。
4. 结汇成人民币。
5. 记录手续费、汇率和到账金额。

### 账本字段

建议用表格记录：

| 月份 | AdSense 付款金额 | 币种 | 到账金额 | 手续费 | 结汇人民币 | 汇率 | 银行 | 备注 |
| --- | ---: | --- | ---: | ---: | ---: | ---: | --- | --- |

## 9. 最小执行清单

### 你现在要做

1. 买/确认 Spaceship 域名。
2. 在 Cloudflare 添加站点。
3. 把 Spaceship nameserver 改成 Cloudflare。
4. 替换本项目里的域名、邮箱、AdSense ID 占位。
5. 用 Wrangler 或 GitHub 部署 `tool-sites/homecalc/public`。
6. 绑定自定义域名。
7. 提交 Search Console。
8. 注册 AdSense 并添加站点。
9. 银行确认境外美元电汇信息。
10. 等审核和阈值。

### 不要做

1. 不要买点击。
2. 不要互点。
3. 不要让亲友点广告。
4. 不要用别人银行卡。
5. 不要把付款国家乱选成美国/香港。
6. 不要上线空壳站申请 AdSense。
7. 不要只做中国大陆流量却依赖 Google 广告收入。

## 10. 官方参考

- AdSense add a site: https://support.google.com/adsense/answer/12169212
- AdSense code placement: https://support.google.com/adsense/answer/9274516
- AdSense ads.txt: https://support.google.com/adsense/answer/12171612?hl=en-GB
- AdSense payment thresholds: https://support.google.com/adsense/answer/1709871
- AdSense payment methods by location: https://support.google.com/adsense/answer/1714397
- AdSense US tax information: https://support.google.com/adsense/answer/2490070
- AdSense non-US tax information: https://support.google.com/adsense/answer/14131950
- AdSense invalid traffic: https://support.google.com/adsense/answer/16737
- Google traffic source policy: https://support.google.com/adsense/answer/48182
- Cloudflare Pages: https://developers.cloudflare.com/pages/
- Cloudflare Pages custom domains: https://developers.cloudflare.com/pages/configuration/custom-domains/
- Cloudflare Pages Direct Upload: https://developers.cloudflare.com/pages/get-started/direct-upload/
- Cloudflare Workers limits: https://developers.cloudflare.com/workers/platform/limits/
- Spaceship custom nameserver setup: https://www.spaceship.com/knowledgebase/connect-domain-custom-nameservers
