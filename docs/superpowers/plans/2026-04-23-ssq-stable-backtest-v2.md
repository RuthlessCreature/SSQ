# SSQ Stable Backtest v2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rework SSQ backtesting and number generation so the web app selects parameters on a tune/validate split, scores full ticket portfolios instead of only the best ticket, and keeps mystic features as a weak prior rather than a dominant signal.

**Architecture:** Keep the current single-file Flask app, but refactor the internals around three clearer layers inside `app.py`: scoring primitives, portfolio backtest evaluation, and deterministic ticket search. Preserve the current UI and data fetch flow while upgrading defaults, metrics, and explanatory text for a more realistic evaluation loop.

**Tech Stack:** Python 3, Flask, standard library (`dataclasses`, `statistics`, `itertools`, `math`, `functools`-style caching patterns), `lunar-python`

---

## File Structure

- Modify: `app.py`
  - Add utility and portfolio evaluation helpers
  - Expand `BacktestResult`
  - Replace “best ticket only” backtest logic with tune/validate portfolio scoring
  - Rework score mixing so mystic influence becomes a bounded multiplier
  - Replace random-heavy ticket generation with candidate-pool search and diversification
  - Update UI text and default values
- Create: `.pm/project.yml`
  - Track current project summary and this upgrade direction
- Create: `.pm/updates.md`
  - Record the design and planning milestone
- Create: `docs/superpowers/specs/2026-04-23-ssq-stable-backtest-design.md`
  - Persist the approved design
- Create: `docs/superpowers/plans/2026-04-23-ssq-stable-backtest-v2.md`
  - Persist this implementation plan

### Task 1: Add portfolio evaluation primitives

**Files:**
- Modify: `app.py`

- [ ] **Step 1: Add new dataclasses after `BacktestResult`**

```python
@dataclass
class TicketEvaluation:
    red_hits: int
    blue_hit: bool
    rank: str
    utility: float


@dataclass
class PortfolioEvaluation:
    ticket_count: int
    total_utility: float
    net_utility: float
    best_rank: str
    red_coverage: float
    blue_hits: int
    overlap_penalty: float
```

- [ ] **Step 2: Replace the old rank bonus logic with bounded utility mapping**

```python
def utility_by_rank(rank: str) -> float:
    utility_map = {
        "一等奖": 120.0,
        "二等奖": 40.0,
        "三等奖": 18.0,
        "四等奖": 8.0,
        "五等奖": 3.0,
        "六等奖": 1.0,
        "未中": 0.0,
    }
    return utility_map[rank]
```

- [ ] **Step 3: Rewrite `evaluate_ticket()` to return the new dataclass**

```python
def evaluate_ticket(ticket: Ticket, draw: Draw) -> TicketEvaluation:
    red_hits = len(set(ticket.reds) & set(draw.reds))
    blue_hit = ticket.blue == draw.blue
    rank = prize_rank(red_hits, blue_hit)
    utility = utility_by_rank(rank) + red_hits * 0.6 + (0.5 if blue_hit else 0.0)
    return TicketEvaluation(red_hits=red_hits, blue_hit=blue_hit, rank=rank, utility=utility)
```

- [ ] **Step 4: Add a new portfolio evaluator below `evaluate_ticket()`**

```python
def evaluate_portfolio(tickets: Sequence[Ticket], draw: Draw, cost_per_ticket: float = 1.0) -> PortfolioEvaluation:
    results = [evaluate_ticket(ticket, draw) for ticket in tickets]
    total_utility = sum(result.utility for result in results)
    overlaps = [
        len(set(left.reds) & set(right.reds))
        for left, right in combinations(tickets, 2)
    ]
    overlap_penalty = sum(max(0, overlap - 3) * 0.35 for overlap in overlaps)
    best_rank = min((result.rank for result in results), key=lambda rank: ["一等奖", "二等奖", "三等奖", "四等奖", "五等奖", "六等奖", "未中"].index(rank))
    red_coverage = sum(result.red_hits for result in results) / max(len(results), 1)
    blue_hits = sum(1 for result in results if result.blue_hit)
    net_utility = total_utility - len(tickets) * cost_per_ticket - overlap_penalty
    return PortfolioEvaluation(
        ticket_count=len(tickets),
        total_utility=total_utility,
        net_utility=net_utility,
        best_rank=best_rank,
        red_coverage=red_coverage,
        blue_hits=blue_hits,
        overlap_penalty=overlap_penalty,
    )
```

- [ ] **Step 5: Run a smoke check for the new evaluation helpers**

Run:

```bash
@'
from app import Draw, Ticket, evaluate_ticket, evaluate_portfolio

draw = Draw("2026001", "2026-01-01", (1, 2, 3, 4, 5, 6), 7)
ticket = Ticket((1, 2, 3, 4, 5, 6), 7, 0.0)
result = evaluate_ticket(ticket, draw)
print(result.rank, result.utility)
portfolio = evaluate_portfolio([ticket], draw)
print(portfolio.net_utility, portfolio.best_rank)
'@ | python -
```

Expected:

- Prints `一等奖`
- Prints a positive `utility`
- Prints a positive `net_utility`

- [ ] **Step 6: Commit**

```bash
git add app.py
git commit -m "refactor: add portfolio evaluation primitives"
```

### Task 2: Split backtest into tuning and validation

**Files:**
- Modify: `app.py`

- [ ] **Step 1: Expand `BacktestResult` with stability fields**

```python
@dataclass
class BacktestResult:
    evaluated_windows: int
    iterations: int
    tickets_per_draw: int
    best_config: Dict[str, float]
    average_score: float
    average_red_hits: float
    blue_hit_rate: float
    best_prize_counts: Dict[str, int]
    top_iterations: List[Dict[str, object]]
    tune_score: float = 0.0
    validate_score: float = 0.0
    volatility: float = 0.0
    max_miss_streak: int = 0
    small_prize_rate: float = 0.0
    mode_label: str = "stats_only"
```

- [ ] **Step 2: Add helpers for window splitting and stable config ranking**

```python
def split_backtest_indices(total_windows: int) -> tuple[range, range]:
    tune_count = max(6, int(total_windows * 0.7))
    tune_count = min(tune_count, max(total_windows - 3, 1))
    return range(0, tune_count), range(tune_count, total_windows)


def config_summary_score(net_utilities: Sequence[float], miss_streak: int) -> tuple[float, float]:
    average_value = statistics.mean(net_utilities) if net_utilities else 0.0
    volatility = statistics.pstdev(net_utilities) if len(net_utilities) > 1 else 0.0
    final_score = average_value - volatility * 0.35 - miss_streak * 0.18
    return final_score, volatility
```

- [ ] **Step 3: Rewrite `run_backtest()` around portfolio evaluation**

```python
def run_backtest(draws: Sequence[Draw], profile: BaziProfile, ticket_count: int, windows: int, iterations: int) -> BacktestResult:
    chronological = list(reversed(draws))
    start_index = max(30, len(chronological) - windows)
    target_indices = list(range(start_index, len(chronological)))
    tune_slice, validate_slice = split_backtest_indices(len(target_indices))
    configs = config_grid(iterations)
    tickets_per_draw = min(ticket_count, 30)
    summaries: list[dict[str, object]] = []

    for config_index, config in enumerate(configs, start=1):
        phase_metrics = {"tune": [], "validate": []}
        prize_counts: Counter[str] = Counter()

        for relative_index, target_index in enumerate(target_indices):
            target = chronological[target_index]
            history = chronological[:target_index]
            history_newest = list(reversed(history[-160:]))
            tickets = generate_tickets(
                history_newest,
                profile,
                tickets_per_draw,
                config,
                seed_context=f"backtest-{config_index}-{target.issue}",
                include_reasons=False,
                quick=True,
            )
            portfolio = evaluate_portfolio(tickets, target)
            phase_name = "tune" if relative_index in tune_slice else "validate"
            phase_metrics[phase_name].append(portfolio)
            prize_counts[portfolio.best_rank] += 1

        tune_values = [item.net_utility for item in phase_metrics["tune"]]
        validate_values = [item.net_utility for item in phase_metrics["validate"]]
        tune_miss_streak = longest_non_prize_streak(phase_metrics["tune"])
        validate_miss_streak = longest_non_prize_streak(phase_metrics["validate"])
        tune_score, _ = config_summary_score(tune_values, tune_miss_streak)
        validate_score, validate_volatility = config_summary_score(validate_values, validate_miss_streak)
        summaries.append(
            {
                "iteration": config_index,
                "config": config,
                "mode_label": str(config["mode_label"]),
                "tune_score": tune_score,
                "validate_score": validate_score,
                "average_score": statistics.mean(validate_values) if validate_values else 0.0,
                "average_red_hits": statistics.mean(item.red_coverage for item in phase_metrics["validate"])
                if phase_metrics["validate"]
                else 0.0,
                "blue_hit_rate": (
                    sum(item.blue_hits for item in phase_metrics["validate"])
                    / max(sum(item.ticket_count for item in phase_metrics["validate"]), 1)
                ),
                "prize_counts": dict(prize_counts),
                "evaluated": len(phase_metrics["validate"]),
                "volatility": validate_volatility,
                "max_miss_streak": validate_miss_streak,
                "small_prize_rate": small_prize_rate(phase_metrics["validate"]),
            }
        )
```

- [ ] **Step 4: Add `longest_non_prize_streak()` and `small_prize_rate()` helpers**

```python
def longest_non_prize_streak(portfolios: Sequence[PortfolioEvaluation]) -> int:
    longest = 0
    current = 0
    for item in portfolios:
        if item.best_rank == "未中":
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return longest


def small_prize_rate(portfolios: Sequence[PortfolioEvaluation]) -> float:
    if not portfolios:
        return 0.0
    hit_count = sum(1 for item in portfolios if item.best_rank != "未中")
    return hit_count / len(portfolios)
```

- [ ] **Step 5: Rank configs by validation score, then tune score**

```python
summaries.sort(
    key=lambda item: (
        float(item["validate_score"]),
        float(item["tune_score"]),
        -float(item["volatility"]),
        -int(item["max_miss_streak"]),
    ),
    reverse=True,
)
```

- [ ] **Step 6: Run a smoke check over a synthetic rolling window**

Run:

```bash
@'
from datetime import datetime
from app import Draw, build_bazi_profile, run_backtest

draws = []
for issue in range(1, 81):
    reds = tuple(sorted((((issue + offset) % 33) + 1) for offset in range(6)))
    blue = (issue % 16) + 1
    draws.append(Draw(f"2026{issue:03d}", "2026-01-01", reds, blue))

profile = build_bazi_profile("男", datetime(1990, 1, 1, 8, 0))
result = run_backtest(list(reversed(draws)), profile, 5, 30, 12)
print(result.validate_score, result.tune_score, result.volatility, result.mode_label)
'@ | python -
```

Expected:

- Prints four values without raising an exception
- `result.iterations` equals `12`

- [ ] **Step 7: Commit**

```bash
git add app.py
git commit -m "refactor: split backtest into tune and validate phases"
```

### Task 3: Rework config sampling and defaults

**Files:**
- Modify: `app.py`

- [ ] **Step 1: Replace the old config axes with tighter, stability-focused axes**

```python
def config_grid(iterations: int) -> List[Dict[str, float]]:
    decays = [0.955, 0.970, 0.985]
    omissions = [0.12, 0.20, 0.28]
    pair_weights = [0.10, 0.18, 0.26]
    distribution_weights = [0.18, 0.28, 0.38]
    diversity_weights = [0.18, 0.30]
    mystic_caps = [0.00, 0.04, 0.08]
    base_modes = ["stats_only", "stats_plus_mystic"]
    configs = [
        {
            "decay": decay,
            "omission_weight": omission,
            "pair_weight": pair_weight,
            "distribution_weight": distribution_weight,
            "diversity_weight": diversity_weight,
            "mystic_cap": mystic_cap,
            "mode_label": base_mode,
        }
        for decay, omission, pair_weight, distribution_weight, diversity_weight, mystic_cap, base_mode in product(
            decays,
            omissions,
            pair_weights,
            distribution_weights,
            diversity_weights,
            mystic_caps,
            base_modes,
        )
    ]
    if iterations >= len(configs):
        return configs
    step = len(configs) / iterations
    return [configs[min(int(index * step), len(configs) - 1)] for index in range(iterations)]
```

- [ ] **Step 2: Add `mode_label` and `mystic_cap` to each config**

```python
{
    "decay": decay,
    "omission_weight": omission,
    "pair_weight": pair_weight,
    "distribution_weight": distribution_weight,
    "diversity_weight": diversity_weight,
    "mystic_cap": mystic_cap,
    "mode_label": base_mode,
}
```

- [ ] **Step 3: Update form defaults for a deeper but still bounded search**

```python
form = {
    "gender": request.form.get("gender", "男"),
    "calendar_type": request.form.get("calendar_type", "solar"),
    "birth_date": request.form.get("birth_date", "1990-01-01"),
    "birth_time": request.form.get("birth_time", "08:00"),
    "lunar_year": request.form.get("lunar_year", "1990"),
    "lunar_month": request.form.get("lunar_month", "1"),
    "lunar_day": request.form.get("lunar_day", "1"),
    "lunar_leap": request.form.get("lunar_leap", "0"),
    "ticket_count": request.form.get("ticket_count", "5"),
    "backtest_windows": request.form.get("backtest_windows", "60"),
    "iterations": request.form.get("iterations", "72"),
}
```

- [ ] **Step 4: Update the clamps to match the new defaults**

```python
backtest_windows = clamp_int(form["backtest_windows"], 60, 20, 100)
iterations = clamp_int(form["iterations"], 72, 12, 180)
```

- [ ] **Step 5: Run a config coverage smoke check**

Run:

```bash
@'
from app import config_grid

configs = config_grid(24)
print(len(configs))
print(sorted({item["mode_label"] for item in configs}))
print(sorted({item["mystic_cap"] for item in configs}))
'@ | python -
```

Expected:

- Prints `24`
- Includes both `stats_only` and `stats_plus_mystic`
- Includes at least two distinct `mystic_cap` values

- [ ] **Step 6: Commit**

```bash
git add app.py
git commit -m "tune: rebalance config sampling and defaults"
```

### Task 4: Make mystic scoring a bounded adjustment

**Files:**
- Modify: `app.py`

- [ ] **Step 1: Replace the existing `mystic_score()` with a centered adjustment helper**

```python
def mystic_adjustment(number: int, profile: BaziProfile, cap: float, blue: bool = False) -> float:
    raw = 0.0
    element = number_element(number)
    if element in profile.useful_elements:
        raw += 0.55
    if element in profile.avoid_elements:
        raw -= 0.40
    if element == profile.day_element:
        raw += 0.12
    if blue and number in profile.lucky_blues:
        raw += 0.28
    if (not blue) and number in profile.lucky_reds:
        raw += 0.18
    scaled = math.tanh(raw) * cap
    return scaled
```

- [ ] **Step 2: Rework `build_number_scores()` so math stays primary**

```python
math_score = (
    0.46 * red_freq[number]
    + 0.34 * red_recent[number]
    + float(config["omission_weight"]) * red_omission[number]
)
if config["mode_label"] == "stats_plus_mystic":
    adjust = mystic_adjustment(number, profile, float(config["mystic_cap"]))
else:
    adjust = 0.0
red_scores[number] = max(0.01, math_score * (1.0 + adjust))
```

- [ ] **Step 3: Preserve detailed explanation fields**

```python
red_details[number] = {
    "freq": red_freq[number],
    "recent": red_recent[number],
    "omission": red_omission[number],
    "mystic_adjust": adjust,
    "element": number_element(number),
}
```

- [ ] **Step 4: Update explanation copy to reflect weak-prior behavior**

```python
f"玄学侧：本次只做小幅偏置修正，优先保留统计主分；命理贴合的号码会得到轻微加分。"
```

- [ ] **Step 5: Run a score-comparison smoke check**

Run:

```bash
@'
from datetime import datetime
from app import Draw, build_bazi_profile, build_number_scores

draws = [Draw("1", "2026-01-01", (1, 2, 3, 4, 5, 6), 7)] * 40
profile = build_bazi_profile("男", datetime(1990, 1, 1, 8, 0))
stats_only = build_number_scores(draws, profile, {
    "decay": 0.97,
    "omission_weight": 0.2,
    "pair_weight": 0.18,
    "distribution_weight": 0.28,
    "diversity_weight": 0.18,
    "mystic_cap": 0.0,
    "mode_label": "stats_only",
})
stats_plus = build_number_scores(draws, profile, {
    "decay": 0.97,
    "omission_weight": 0.2,
    "pair_weight": 0.18,
    "distribution_weight": 0.28,
    "diversity_weight": 0.18,
    "mystic_cap": 0.08,
    "mode_label": "stats_plus_mystic",
})
print(stats_only["red_scores"][1], stats_plus["red_scores"][1])
'@ | python -
```

Expected:

- Prints two close values
- The difference remains modest rather than exploding

- [ ] **Step 6: Commit**

```bash
git add app.py
git commit -m "refactor: make mystic scoring a bounded adjustment"
```

### Task 5: Replace random-heavy generation with candidate search

**Files:**
- Modify: `app.py`

- [ ] **Step 1: Add candidate-pool helpers near `generate_tickets()`**

```python
def candidate_pool(scores: Dict[int, float], limit: int) -> List[int]:
    return sorted(scores, key=scores.get, reverse=True)[:limit]


def candidate_combos(numbers: Sequence[int], size: int) -> List[Tuple[int, ...]]:
    return [tuple(combo) for combo in combinations(numbers, size)]
```

- [ ] **Step 2: Add structural penalties inside `combo_score()`**

```python
span = max(reds) - min(reds)
span_score = closeness(span, float(stats["avg_span"]), float(stats["std_span"]) * 1.4)
consecutive_pairs = sum(1 for left, right in zip(reds, reds[1:]) if right - left == 1)
consecutive_penalty = max(0, consecutive_pairs - 1) * 0.14
recent_overlap_penalty = max(0, len(set(reds) & stats["latest_reds"]) - 1) * 0.20
```

- [ ] **Step 3: Rewrite `generate_tickets()` to search candidates deterministically**

```python
red_pool_size = 11 if quick else 14
blue_pool_size = 3 if quick else 6
red_pool = candidate_pool(red_scores, red_pool_size)
blue_pool = candidate_pool(blue_scores, blue_pool_size)
candidates = {}
for reds in candidate_combos(red_pool, 6):
    for blue in blue_pool:
        if blue in reds:
            continue
        key = (tuple(sorted(reds)), blue)
        if key in historical_keys:
            continue
        score = combo_score(key[0], blue, number_model, config)
        candidates[key] = Ticket(reds=key[0], blue=blue, score=score)
```

- [ ] **Step 4: Add diversification-aware final selection**

```python
def diversification_penalty(ticket: Ticket, selected: Sequence[Ticket], diversity_weight: float) -> float:
    if not selected:
        return 0.0
    overlap = sum(max(0, len(set(ticket.reds) & set(existing.reds)) - 3) for existing in selected)
    same_blue = sum(1 for existing in selected if existing.blue == ticket.blue)
    return diversity_weight * (overlap + same_blue * 0.6)
```

- [ ] **Step 5: Select the final `n` tickets with marginal score**

```python
for ticket in ranked_candidates:
    marginal_score = ticket.score - diversification_penalty(ticket, selected, float(config["diversity_weight"]))
    if marginal_score <= 0:
        continue
    selected.append(Ticket(reds=ticket.reds, blue=ticket.blue, score=marginal_score))
    if len(selected) >= count:
        break
```

- [ ] **Step 6: Run a generation smoke check**

Run:

```bash
@'
from datetime import datetime
from app import Draw, build_bazi_profile, generate_tickets

draws = []
for issue in range(1, 90):
    reds = tuple(sorted((((issue * 2) + offset) % 33) + 1 for offset in range(6)))
    blue = (issue % 16) + 1
    draws.append(Draw(f"2026{issue:03d}", "2026-01-01", reds, blue))

profile = build_bazi_profile("男", datetime(1990, 1, 1, 8, 0))
config = {
    "decay": 0.97,
    "omission_weight": 0.2,
    "pair_weight": 0.18,
    "distribution_weight": 0.28,
    "diversity_weight": 0.3,
    "mystic_cap": 0.04,
    "mode_label": "stats_plus_mystic",
}
tickets = generate_tickets(list(reversed(draws)), profile, 5, config, "demo", include_reasons=False, quick=True)
print(len(tickets))
print(len({ticket.reds for ticket in tickets}))
'@ | python -
```

Expected:

- Prints `5`
- The red sets are all distinct

- [ ] **Step 7: Commit**

```bash
git add app.py
git commit -m "refactor: add deterministic candidate ticket search"
```

### Task 6: Update UI metrics and explanations

**Files:**
- Modify: `app.py`

- [ ] **Step 1: Update `build_backtest_explanation()` to describe tune/validate results**

```python
return [
    f"这次先用最近 {backtest.evaluated_windows} 期里的前半段挑参数，再用后半段做验证，尽量减少参数刷分。",
    f"主指标改成整组 {backtest.tickets_per_draw} 注号码的组合表现，不再只看每期最好的一注。",
    f"验证段组合得分 {backtest.validate_score:.2f}，调参段 {backtest.tune_score:.2f}，波动 {backtest.volatility:.2f}。",
    f"最长连挂 {backtest.max_miss_streak} 期，小奖覆盖率 {backtest.small_prize_rate * 100:.1f}%。",
    f"当前模式：{'玄学增强' if backtest.mode_label == 'stats_plus_mystic' else '纯统计基线'}。",
]
```

- [ ] **Step 2: Update the result pills in the template**

```html
<span class="pill">调参段：{{ "%.2f"|format(backtest.tune_score) }}</span>
<span class="pill">验证段：{{ "%.2f"|format(backtest.validate_score) }}</span>
<span class="pill">波动：{{ "%.2f"|format(backtest.volatility) }}</span>
<span class="pill">最长连挂：{{ backtest.max_miss_streak }} 期</span>
<span class="pill">小奖覆盖：{{ "%.1f"|format(backtest.small_prize_rate * 100) }}%</span>
<span class="pill">模式：{{ "玄学增强" if backtest.mode_label == "stats_plus_mystic" else "纯统计基线" }}</span>
```

- [ ] **Step 3: Update the form defaults in the template**

```html
<input type="number" name="backtest_windows" min="20" max="100" value="{{ form.backtest_windows }}">
<input type="number" name="iterations" min="12" max="180" value="{{ form.iterations }}">
```

- [ ] **Step 4: Run a Flask render smoke check**

Run:

```bash
@'
from app import app

with app.test_client() as client:
    response = client.get("/")
    print(response.status_code)
    print("验证段" in response.get_data(as_text=True))
'@ | python -
```

Expected:

- Prints `200`
- Prints `True`

- [ ] **Step 5: Commit**

```bash
git add app.py
git commit -m "feat: update UI copy for stable backtest metrics"
```

### Task 7: Final verification and project metadata

**Files:**
- Modify: `app.py`
- Create: `.pm/project.yml`
- Create: `.pm/updates.md`

- [ ] **Step 1: Create `.pm/project.yml` with current status**

```yaml
version: 1
name: SSQ
summary: 本地 Flask 双色球选号工具，结合历史开奖统计与弱化后的玄学偏置，目标是提升回测稳定性而非夸张刷分。
status: active
phase: building
tags:
  - flask
  - lottery
  - data-experiment

features:
  - id: FEAT-1
    title: 开奖抓取与排盘
    status: done
    priority: high
    summary: 已支持抓取最近 200 期开奖、八字排盘和基础解释。
  - id: FEAT-2
    title: 稳定回测 v2
    status: doing
    priority: high
    summary: 正在把回测改成调参段和验证段分离，并以组合表现作为主指标。

requirements:
  - id: REQ-1
    title: 保持 Web 端直接运行
    status: doing
    priority: high
    summary: 不引入重依赖，单次计算控制在约 15-30 秒。
  - id: REQ-2
    title: 保留玄学特色但降低噪声
    status: doing
    priority: high
    summary: 玄学只做弱先验，验证段不占优时自动回退到统计基线。

progress:
  summary: 已完成稳定回测 v2 的设计和实施计划，下一步进入代码改造。
  counts:
    planned: 2
    doing: 2
    done: 1
    blocked: 0

blockers:
  - 历史样本仍只有近 200 期，稳定性提升有限但优于旧回测口径。

next_actions:
  - 按计划重做组合评价与双阶段回测
  - 将随机采样替换为候选池搜索和分散选票
  - 更新页面解释和默认参数

links:
  - label: repo-path
    value: E:\github\SSQ

meta:
  source: codex-maintained
  last_reviewed_at: 2026-04-23
```

- [ ] **Step 2: Append an update entry to `.pm/updates.md`**

```markdown
## 2026-04-23
- Documented the stable backtest v2 design for SSQ
- Added an implementation plan focused on tune/validate backtesting and portfolio-based scoring
- Captured project metadata for future Codex maintenance
```

- [ ] **Step 3: Run end-to-end smoke checks before handoff**

Run:

```bash
@'
from datetime import datetime
from app import app, build_bazi_profile, config_grid

profile = build_bazi_profile("男", datetime(1990, 1, 1, 8, 0))
print(profile.day_master, len(config_grid(18)))

with app.test_client() as client:
    response = client.get("/")
    print(response.status_code)
'@ | python -
```

Expected:

- Prints a valid day master and `18`
- Prints `200`

- [ ] **Step 4: Review plan coverage manually**

Check:

- Task 1 covers the new single-ticket and portfolio scoring primitives
- Task 2 covers tune/validate backtesting and summary ranking
- Task 3 covers config sampling and default parameters
- Task 4 covers mystic weakening and baseline fallback behavior
- Task 5 covers deterministic ticket generation and diversification
- Task 6 covers UI and explanation updates
- Task 7 covers metadata and final smoke validation

- [ ] **Step 5: Commit**

```bash
git add app.py .pm/project.yml .pm/updates.md
git commit -m "docs: capture stable backtest v2 implementation plan"
```
