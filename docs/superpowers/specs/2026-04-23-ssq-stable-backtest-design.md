# SSQ Stable Backtest v2 Design

**Date:** 2026-04-23
**Status:** approved in chat, documented for implementation

## Goal

在保留“玄学 + 数学”产品特色的前提下，重做 `SSQ` 的回测与选号流程，让结果更接近真实多注下注表现，而不是被“只记最好一注”的回测口径放大。新方案需要继续保持 `Flask` 单机 Web 直跑、少依赖、约 `15-30` 秒内完成一次排盘 + 回测 + 出号。

## Current Problems

1. `run_backtest()` 目前每期只记多注中的最好一注，导致结果偏乐观。
2. `config_grid()` 的参数空间有 `180` 组，但页面默认只跑 `36` 组，搜索覆盖不均匀。
3. `generate_tickets()` 主要依赖带随机性的加权采样，回测波动偏大。
4. `build_number_scores()` 里玄学分和数学分几乎平权混合，容易把噪声放大成“信号”。
5. 页面只展示单一平均分，无法区分“调参时表现好”与“验证时仍然稳定”。

## Product Decision

- 保留玄学作为产品特色。
- 玄学不再主导预测，只做弱先验与解释增强。
- 优先优化“综合收益感”和外推稳定性，而不是追求更夸张的回测分数。

## Non-Goals

- 不引入 `pandas`、`scikit-learn` 等额外重依赖。
- 不把项目拆成多模块工程；实现阶段仍以 `app.py` 为主，最多增加少量文档或轻量辅助结构。
- 不声称具备真实可预测彩票的能力；仍保留娱乐和实验定位。

## v2 Architecture

### 1. Backtest: Tune/Validate Split

将最近 `backtest_windows` 期按时间顺序拆成两段：

- 调参段：前 `70%`
- 验证段：后 `30%`

流程：

1. 枚举或均匀采样参数。
2. 所有参数先在调参段得到初始分数。
3. 只保留调参段前 `K` 名配置进入验证段。
4. 最终参数由验证段得分决定。

这样可以显著降低“同一批历史数据上反复刷最优”的过拟合风险。

### 2. Evaluation: Portfolio First

v2 不再以“这一期最好的一注”作为主分，而以“这一期整组 `n` 注号码的组合表现”作为主指标。

新增两层评价：

- 单注评价：保留红球命中数、蓝球命中、奖级。
- 组合评价：将一整组 `n` 注折算为一轮组合收益代理。

推荐的组合得分思路：

- `sum(ticket_utility)` 代表该期整组命中收益代理。
- `ticket_count * cost_per_ticket` 代表下注成本。
- 再减去波动和连续空窗惩罚。

最终参数分数优先用验证段的组合得分，不再用“最好一注平均分”。

### 3. Scoring: Math as Backbone, Mystic as Weak Prior

数学分继续做主干，来源包括：

- 长周期频率
- 短周期热度
- 遗漏回补
- 搭配支持度
- 和值/奇偶/三区/跨度等结构贴合度
- 最近重号与过窄结构惩罚

玄学分改为小幅修正，而不是与数学分平权相加：

```text
final_red_score = math_red_score * (1 + mystic_adjust_red)
final_blue_score = math_blue_score * (1 + mystic_adjust_blue)
```

其中：

- 红球 `mystic_adjust_red` 建议限制在 `[-0.08, +0.08]`
- 蓝球 `mystic_adjust_blue` 建议限制在 `[-0.12, +0.12]`

玄学影响来源只保留：

- 五行匹配
- 幸运号映射
- 蓝球偏好

### 4. Ticket Generation: Deterministic Candidate Search

回测 quick 模式和最终出号模式都改为“候选池 + 确定性搜索 + 多注分散”：

1. 根据单号得分选出红球、蓝球候选池。
2. 在候选池内生成组合候选。
3. 用结构规则与 `combo_score()` 过滤掉明显差的组合。
4. 按“组合分 - 重叠惩罚 - 同质化惩罚”贪心挑选最终 `n` 注。

推荐候选规模：

- quick 回测：红球 `11` 个、蓝球 `3` 个
- 最终出号：红球 `14` 个、蓝球 `6` 个

### 5. Baseline vs Mystic-Enhanced Safeguard

每个参数配置都同时评估两种模式：

- `stats_only`
- `stats_plus_mystic`

如果验证段里玄学增强版没有稳定优于纯统计版，则最终自动回退到纯统计模式。这样既保留玄学入口，又避免它在某些生日画像上拖累结果。

## Data Model Changes

建议新增或扩展以下结构：

- `TicketEvaluation`
  - `red_hits`
  - `blue_hit`
  - `rank`
  - `utility`
- `PortfolioEvaluation`
  - `ticket_count`
  - `total_utility`
  - `net_utility`
  - `best_rank`
  - `red_coverage`
  - `blue_hits`
- `BacktestResult`
  - 保留现有字段
  - 增加 `tune_score`
  - 增加 `validate_score`
  - 增加 `volatility`
  - 增加 `max_miss_streak`
  - 增加 `small_prize_rate`
  - 增加 `mode_label`

## Metrics

### Primary Metric

主指标使用验证段组合净收益代理：

```text
validate_score =
average(net_utility)
- volatility_penalty
- miss_streak_penalty
- overlap_penalty
```

### Supporting Metrics

- 平均红球命中
- 蓝球命中率
- 六等奖及以上覆盖率
- 四等奖及以上覆盖率
- 最长连续未中奖期数
- 多注平均重叠度

## UI Changes

页面保留现有输入项，只调整结果说明：

- “平均评分” 改成更偏真实含义的 “验证段组合得分”
- 新增“调参段得分”和“验证段得分”
- 新增“波动”“最长连挂”“玄学增强是否启用”
- 文案强调这是历史模拟，不是中奖承诺

## Performance Budget

为了控制在 `15-30` 秒：

- 对 `(target_index, decay)` 的历史统计做缓存
- 对 `profile` 相关的玄学分做缓存
- 降低回测 quick 模式的候选池规模
- 参数空间不再简单取前 `N` 个，而是均匀覆盖采样

## Risks

1. 改完后回测分数会更保守，看起来可能不如旧版“好看”。
2. 由于历史样本仍只有近 `200` 期，验证段稳定性会提升，但不可能消除随机性。
3. 候选池过小会让组合空间太窄，过大则会超出 Web 响应预算。

## Rollout Plan

1. 先重做回测评价口径。
2. 再把玄学降为弱先验，并增加 baseline 保护。
3. 最后替换随机采样为确定性候选搜索与分散。
4. 同步调整页面解释文案和默认参数。

## Acceptance Criteria

- 选参必须经过调参段和验证段两阶段。
- 回测主结果不再基于“每期最好一注”。
- 玄学增强必须能自动回退到纯统计基线。
- 生成多注时应明确控制号码组之间的重叠。
- 默认参数下页面响应仍控制在约 `15-30` 秒。

## Assumptions

- 用户接受回测数字更保守，但更真实。
- 用户希望保留玄学解释和轻微偏置，而不是完全拿掉。
- 当前项目短期内仍以单文件应用维护为主。

## Next Step

按本设计写出可执行的实施计划，并在用户选择执行方式后再进入代码实现。
