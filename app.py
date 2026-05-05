from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
import re
import statistics
import time
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime
from itertools import combinations, product
from typing import Dict, List, Sequence, Tuple
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from flask import Flask, render_template_string, request


app = Flask(__name__)

GAN = "甲乙丙丁戊己庚辛壬癸"
ZHI = "子丑寅卯辰巳午未申酉戌亥"
GAN_ELEMENTS = {
    "甲": "木",
    "乙": "木",
    "丙": "火",
    "丁": "火",
    "戊": "土",
    "己": "土",
    "庚": "金",
    "辛": "金",
    "壬": "水",
    "癸": "水",
}
GAN_POLARITY = {
    "甲": "阳",
    "乙": "阴",
    "丙": "阳",
    "丁": "阴",
    "戊": "阳",
    "己": "阴",
    "庚": "阳",
    "辛": "阴",
    "壬": "阳",
    "癸": "阴",
}
HIDDEN_STEMS = {
    "子": ["癸"],
    "丑": ["己", "癸", "辛"],
    "寅": ["甲", "丙", "戊"],
    "卯": ["乙"],
    "辰": ["戊", "乙", "癸"],
    "巳": ["丙", "戊", "庚"],
    "午": ["丁", "己"],
    "未": ["己", "丁", "乙"],
    "申": ["庚", "壬", "戊"],
    "酉": ["辛"],
    "戌": ["戊", "辛", "丁"],
    "亥": ["壬", "甲"],
}
ELEMENT_GENERATES = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
ELEMENT_CONTROLS = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}
NUMBER_ELEMENTS = {
    1: "水",
    6: "水",
    2: "火",
    7: "火",
    3: "木",
    8: "木",
    4: "金",
    9: "金",
    5: "土",
    0: "土",
}
SOURCE_URL = "https://jc.zhcw.com/port/client_json.php"
SOURCE_REFERER = "https://www.zhcw.com/kjxx/ssq/"
CACHE_TTL_SECONDS = 30 * 60
DRAW_CACHE: Dict[str, object] = {"draws": [], "ts": 0.0, "fetched_at": ""}


@dataclass(frozen=True)
class Draw:
    issue: str
    open_time: str
    reds: Tuple[int, ...]
    blue: int

    @property
    def red_text(self) -> str:
        return " ".join(f"{n:02d}" for n in self.reds)

    @property
    def blue_text(self) -> str:
        return f"{self.blue:02d}"


@dataclass
class BaziProfile:
    gender: str
    birth_dt: datetime
    pillars: Dict[str, str]
    ten_gods: Dict[str, str]
    hidden_stems: Dict[str, str]
    element_scores: Dict[str, float]
    useful_elements: List[str]
    avoid_elements: List[str]
    day_master: str
    day_element: str
    strength_label: str
    luck_direction: str
    luck_start: str
    big_lucks: List[Dict[str, str]]
    lucky_reds: List[int]
    lucky_blues: List[int]
    calendar_note: str
    engine: str


@dataclass
class Ticket:
    reds: Tuple[int, ...]
    blue: int
    score: float
    reasons: List[str] = field(default_factory=list)

    @property
    def red_text(self) -> str:
        return " ".join(f"{n:02d}" for n in self.reds)

    @property
    def blue_text(self) -> str:
        return f"{self.blue:02d}"


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
    tune_expected_value: float = 0.0
    validate_expected_value: float = 0.0
    validate_ev_lcb: float = 0.0
    per_ticket_expected_value: float = 0.0
    ev_standard_error: float = 0.0
    volatility: float = 0.0
    max_miss_streak: int = 0
    small_prize_rate: float = 0.0
    mode_label: str = "stats_only"


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


def clamp_int(value: str, default: int, minimum: int, maximum: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, number))


def stable_seed(*parts: object) -> int:
    raw = "|".join(str(part) for part in parts)
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return int(digest[:16], 16)


def parse_jsonp(text: str) -> Dict[str, object]:
    body = text.strip()
    if body.startswith("{"):
        return json.loads(body)
    match = re.match(r"^[\w$.]+\((.*)\)\s*;?$", body, flags=re.S)
    if not match:
        raise ValueError("开奖接口返回格式不是 JSON/JSONP")
    return json.loads(match.group(1))


def fetch_recent_draws(limit: int = 200, force: bool = False) -> List[Draw]:
    now = time.time()
    cached = DRAW_CACHE.get("draws") or []
    if cached and not force and now - float(DRAW_CACHE.get("ts") or 0) < CACHE_TTL_SECONDS:
        return list(cached)

    params = {
        "callback": "ssq_callback",
        "transactionType": "10001001",
        "lotteryId": "1",
        "issueCount": str(limit),
        "startIssue": "",
        "endIssue": "",
        "startDate": "",
        "endDate": "",
        "type": "0",
        "pageNum": "1",
        "pageSize": str(limit),
        "tt": str(now),
    }
    req = Request(
        f"{SOURCE_URL}?{urlencode(params)}",
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X) AppleWebKit/537.36",
            "Referer": SOURCE_REFERER,
            "Accept": "*/*",
        },
    )
    with urlopen(req, timeout=20) as response:
        payload = response.read().decode("utf-8", errors="ignore")

    data = parse_jsonp(payload)
    if data.get("resCode") != "000000":
        raise RuntimeError(str(data.get("message") or "开奖接口返回失败"))

    draws: List[Draw] = []
    for item in data.get("data", []):
        reds = tuple(sorted(int(part) for part in str(item["frontWinningNum"]).split()))
        blue = int(str(item["backWinningNum"]).strip())
        if len(reds) == 6 and all(1 <= n <= 33 for n in reds) and 1 <= blue <= 16:
            draws.append(Draw(str(item["issue"]), str(item["openTime"]), reds, blue))

    if not draws:
        raise RuntimeError("没有解析到双色球开奖数据")

    draws = draws[:limit]
    DRAW_CACHE["draws"] = draws
    DRAW_CACHE["ts"] = now
    DRAW_CACHE["fetched_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return draws


def get_draws(force: bool = False) -> Tuple[List[Draw], str]:
    try:
        return fetch_recent_draws(200, force=force), ""
    except Exception as exc:
        cached = DRAW_CACHE.get("draws") or []
        if cached:
            return list(cached), f"刷新失败，正在使用缓存：{exc}"
        return [], f"开奖数据获取失败：{exc}"


def relation_ten_god(day_gan: str, other_gan: str) -> str:
    if other_gan not in GAN_ELEMENTS or day_gan not in GAN_ELEMENTS:
        return "-"
    day_element = GAN_ELEMENTS[day_gan]
    other_element = GAN_ELEMENTS[other_gan]
    same_polarity = GAN_POLARITY[day_gan] == GAN_POLARITY[other_gan]
    if other_element == day_element:
        return "比肩" if same_polarity else "劫财"
    if ELEMENT_GENERATES[day_element] == other_element:
        return "食神" if same_polarity else "伤官"
    if ELEMENT_CONTROLS[day_element] == other_element:
        return "偏财" if same_polarity else "正财"
    if ELEMENT_CONTROLS[other_element] == day_element:
        return "七杀" if same_polarity else "正官"
    if ELEMENT_GENERATES[other_element] == day_element:
        return "偏印" if same_polarity else "正印"
    return "-"


def inverse_lookup(mapping: Dict[str, str], value: str) -> str:
    for key, mapped in mapping.items():
        if mapped == value:
            return key
    return value


def element_scores_from_pillars(pillars: Dict[str, str]) -> Dict[str, float]:
    scores = {element: 0.0 for element in "木火土金水"}
    for pillar_name, pillar in pillars.items():
        if len(pillar) < 2:
            continue
        gan, zhi = pillar[0], pillar[1]
        if gan in GAN_ELEMENTS:
            scores[GAN_ELEMENTS[gan]] += 1.0
        hidden = HIDDEN_STEMS.get(zhi, [])
        for index, hidden_gan in enumerate(hidden):
            weight = 0.9 if index == 0 else 0.35
            scores[GAN_ELEMENTS[hidden_gan]] += weight
        if pillar_name == "月柱" and hidden:
            scores[GAN_ELEMENTS[hidden[0]]] += 1.1
    return {key: round(value, 2) for key, value in scores.items()}


def useful_elements(day_element: str, scores: Dict[str, float]) -> Tuple[List[str], List[str], str]:
    total = sum(scores.values()) or 1.0
    day_score = scores.get(day_element, 0.0)
    resource_element = inverse_lookup(ELEMENT_GENERATES, day_element)
    body_score = day_score + scores.get(resource_element, 0.0)
    strength = "偏强" if body_score / total >= 0.42 else "偏弱"
    if strength == "偏强":
        useful = [
            ELEMENT_GENERATES[day_element],
            ELEMENT_CONTROLS[day_element],
            inverse_lookup(ELEMENT_CONTROLS, day_element),
        ]
        avoid = [day_element, resource_element]
    else:
        useful = [day_element, resource_element]
        avoid = [
            ELEMENT_GENERATES[day_element],
            ELEMENT_CONTROLS[day_element],
            inverse_lookup(ELEMENT_CONTROLS, day_element),
        ]
    return list(dict.fromkeys(useful)), list(dict.fromkeys(avoid)), strength


def number_element(number: int) -> str:
    return NUMBER_ELEMENTS[number % 10]


def mapped_lucky_numbers(birth_dt: datetime, pillars: Dict[str, str]) -> Tuple[List[int], List[int]]:
    parts = [
        birth_dt.year,
        birth_dt.year % 100,
        birth_dt.month,
        birth_dt.day,
        birth_dt.hour,
        birth_dt.minute,
        sum(int(char) for char in birth_dt.strftime("%Y%m%d%H%M") if char.isdigit()),
    ]
    for pillar in pillars.values():
        for char in pillar:
            if char in GAN:
                parts.append(GAN.index(char) + 1)
            if char in ZHI:
                parts.append(ZHI.index(char) + 1)
    reds = sorted({((part - 1) % 33) + 1 for part in parts})
    blues = sorted({((part - 1) % 16) + 1 for part in parts})
    return reds[:12], blues[:8]


def fallback_year_for_lichun(birth_day: date) -> int:
    if (birth_day.month, birth_day.day) < (2, 4):
        return birth_day.year - 1
    return birth_day.year


def ganzhi_by_index(index: int) -> str:
    return f"{GAN[index % 10]}{ZHI[index % 12]}"


def julian_day(day: date) -> int:
    month_shift = (14 - day.month) // 12
    year = day.year + 4800 - month_shift
    month = day.month + 12 * month_shift - 3
    return day.day + ((153 * month + 2) // 5) + 365 * year + year // 4 - year // 100 + year // 400 - 32045


def fallback_day_pillar(birth_day: date) -> str:
    base_jdn = julian_day(date(2000, 1, 1))
    base_index = 16
    return ganzhi_by_index((julian_day(birth_day) - base_jdn + base_index) % 60)


def fallback_month_pillar(birth_day: date, year_gan: str) -> str:
    boundaries = [
        ((2, 4), "寅"),
        ((3, 6), "卯"),
        ((4, 5), "辰"),
        ((5, 6), "巳"),
        ((6, 6), "午"),
        ((7, 7), "未"),
        ((8, 8), "申"),
        ((9, 8), "酉"),
        ((10, 8), "戌"),
        ((11, 7), "亥"),
        ((12, 7), "子"),
    ]
    month_branch = "丑"
    for (month, day), branch in boundaries:
        if (birth_day.month, birth_day.day) >= (month, day):
            month_branch = branch
    branch_offset = "寅卯辰巳午未申酉戌亥子丑".index(month_branch)
    start_stem = {"甲": 2, "己": 2, "乙": 4, "庚": 4, "丙": 6, "辛": 6, "丁": 8, "壬": 8, "戊": 0, "癸": 0}
    month_gan = GAN[(start_stem[year_gan] + branch_offset) % 10]
    return f"{month_gan}{month_branch}"


def fallback_hour_pillar(hour: int, day_gan: str) -> str:
    branch_index = ((hour + 1) // 2) % 12
    start_stem = {"甲": 0, "己": 0, "乙": 2, "庚": 2, "丙": 4, "辛": 4, "丁": 6, "壬": 6, "戊": 8, "癸": 8}
    hour_gan = GAN[(start_stem[day_gan] + branch_index) % 10]
    return f"{hour_gan}{ZHI[branch_index]}"


def fallback_pillars(birth_dt: datetime) -> Dict[str, str]:
    adjusted_year = fallback_year_for_lichun(birth_dt.date())
    year_pillar = ganzhi_by_index((adjusted_year - 4) % 60)
    month_pillar = fallback_month_pillar(birth_dt.date(), year_pillar[0])
    day_pillar = fallback_day_pillar(birth_dt.date())
    hour_pillar = fallback_hour_pillar(birth_dt.hour, day_pillar[0])
    return {"年柱": year_pillar, "月柱": month_pillar, "日柱": day_pillar, "时柱": hour_pillar}


def build_profile_from_pillars(
    gender: str,
    birth_dt: datetime,
    pillars: Dict[str, str],
    calendar_note: str,
    engine: str,
    luck_direction: str = "按年干阴阳与性别取顺逆",
    luck_start: str = "未计算精确起运",
    big_lucks: List[Dict[str, str]] | None = None,
) -> BaziProfile:
    day_master = pillars["日柱"][0]
    day_element = GAN_ELEMENTS.get(day_master, "木")
    ten_gods = {
        name: ("日主" if name == "日柱" else relation_ten_god(day_master, pillar[0]))
        for name, pillar in pillars.items()
    }
    hidden = {
        name: "、".join(f"{gan}{relation_ten_god(day_master, gan)}" for gan in HIDDEN_STEMS.get(pillar[1], []))
        for name, pillar in pillars.items()
        if len(pillar) >= 2
    }
    scores = element_scores_from_pillars(pillars)
    useful, avoid, strength = useful_elements(day_element, scores)
    lucky_reds, lucky_blues = mapped_lucky_numbers(birth_dt, pillars)
    return BaziProfile(
        gender=gender,
        birth_dt=birth_dt,
        pillars=pillars,
        ten_gods=ten_gods,
        hidden_stems=hidden,
        element_scores=scores,
        useful_elements=useful,
        avoid_elements=avoid,
        day_master=day_master,
        day_element=day_element,
        strength_label=strength,
        luck_direction=luck_direction,
        luck_start=luck_start,
        big_lucks=big_lucks or [],
        lucky_reds=lucky_reds,
        lucky_blues=lucky_blues,
        calendar_note=calendar_note,
        engine=engine,
    )


def build_bazi_profile(gender: str, birth_dt: datetime) -> BaziProfile:
    try:
        from lunar_python import Solar

        lunar = Solar.fromYmdHms(
            birth_dt.year, birth_dt.month, birth_dt.day, birth_dt.hour, birth_dt.minute, 0
        ).getLunar()
        eight = lunar.getEightChar()
        pillars = {
            "年柱": eight.getYear(),
            "月柱": eight.getMonth(),
            "日柱": eight.getDay(),
            "时柱": eight.getTime(),
        }
        is_male = gender == "男"
        yun = eight.getYun(is_male)
        luck_direction = "顺行" if yun.isForward() else "逆行"
        luck_start = f"{yun.getStartYear()}年 {yun.getStartMonth()}个月 {yun.getStartDay()}天起运"
        big_lucks = []
        for luck in yun.getDaYun(9):
            ganzhi = luck.getGanZhi()
            if not ganzhi:
                continue
            big_lucks.append(
                {
                    "age": f"{luck.getStartAge()}-{luck.getEndAge()}岁",
                    "years": f"{luck.getStartYear()}-{luck.getEndYear()}",
                    "ganzhi": ganzhi,
                }
            )
        return build_profile_from_pillars(
            gender=gender,
            birth_dt=birth_dt,
            pillars=pillars,
            calendar_note=f"农历：{lunar}",
            engine="lunar-python（节气换月）",
            luck_direction=luck_direction,
            luck_start=luck_start,
            big_lucks=big_lucks,
        )
    except Exception as exc:
        pillars = fallback_pillars(birth_dt)
        adjusted_year = fallback_year_for_lichun(birth_dt.date())
        year_gan = pillars["年柱"][0]
        forward = (gender == "男" and GAN_POLARITY[year_gan] == "阳") or (
            gender == "女" and GAN_POLARITY[year_gan] == "阴"
        )
        return build_profile_from_pillars(
            gender=gender,
            birth_dt=birth_dt,
            pillars=pillars,
            calendar_note=f"未安装或调用 lunar-python 失败，使用近似节气算法；立春年按 {adjusted_year} 年计。错误：{exc}",
            engine="内置近似算法",
            luck_direction="顺行" if forward else "逆行",
        )


def normalize(values: Dict[int, float], keys: Sequence[int]) -> Dict[int, float]:
    present = [values.get(key, 0.0) for key in keys]
    min_value = min(present) if present else 0.0
    max_value = max(present) if present else 0.0
    if math.isclose(max_value, min_value):
        return {key: 0.5 for key in keys}
    return {key: (values.get(key, 0.0) - min_value) / (max_value - min_value) for key in keys}


def build_stats(draws: Sequence[Draw], decay: float) -> Dict[str, object]:
    red_freq: Counter[int] = Counter()
    blue_freq: Counter[int] = Counter()
    red_recent: Counter[int] = Counter()
    blue_recent: Counter[int] = Counter()
    pair_freq: Counter[Tuple[int, int]] = Counter()
    for index, draw in enumerate(draws):
        weight = decay**index
        for red in draw.reds:
            red_freq[red] += 1
            red_recent[red] += weight
        blue_freq[draw.blue] += 1
        blue_recent[draw.blue] += weight
        for pair in combinations(draw.reds, 2):
            pair_freq[tuple(sorted(pair))] += weight

    red_omission = {}
    for number in range(1, 34):
        red_omission[number] = next(
            (index for index, draw in enumerate(draws) if number in draw.reds), len(draws)
        )
    blue_omission = {}
    for number in range(1, 17):
        blue_omission[number] = next(
            (index for index, draw in enumerate(draws) if number == draw.blue), len(draws)
        )

    sums = [sum(draw.reds) for draw in draws] or [102]
    spans = [max(draw.reds) - min(draw.reds) for draw in draws] or [26]
    odd_counts = [sum(1 for red in draw.reds if red % 2) for draw in draws] or [3]
    zone_counts = [
        (
            sum(1 for red in draw.reds if red <= 11),
            sum(1 for red in draw.reds if 12 <= red <= 22),
            sum(1 for red in draw.reds if red >= 23),
        )
        for draw in draws
    ] or [(2, 2, 2)]
    historical_keys = {(draw.reds, draw.blue) for draw in draws}

    return {
        "red_freq": red_freq,
        "blue_freq": blue_freq,
        "red_recent": red_recent,
        "blue_recent": blue_recent,
        "red_omission": red_omission,
        "blue_omission": blue_omission,
        "pair_freq": pair_freq,
        "avg_sum": statistics.mean(sums),
        "std_sum": statistics.pstdev(sums) or 18.0,
        "avg_span": statistics.mean(spans),
        "std_span": statistics.pstdev(spans) or 6.0,
        "avg_odd": statistics.mean(odd_counts),
        "avg_zone": tuple(statistics.mean(values) for values in zip(*zone_counts)),
        "latest_reds": set(draws[0].reds) if draws else set(),
        "historical_keys": historical_keys,
        "max_pair": max(pair_freq.values()) if pair_freq else 1.0,
    }


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


def build_number_scores(
    draws: Sequence[Draw],
    profile: BaziProfile,
    config: Dict[str, float],
    stats: Dict[str, object] | None = None,
) -> Dict[str, object]:
    stats = stats if stats is not None else build_stats(draws, float(config["decay"]))
    red_keys = list(range(1, 34))
    blue_keys = list(range(1, 17))
    red_freq = normalize(stats["red_freq"], red_keys)
    red_recent = normalize(stats["red_recent"], red_keys)
    red_omission = normalize({k: math.log1p(v) for k, v in stats["red_omission"].items()}, red_keys)
    blue_freq = normalize(stats["blue_freq"], blue_keys)
    blue_recent = normalize(stats["blue_recent"], blue_keys)
    blue_omission = normalize({k: math.log1p(v) for k, v in stats["blue_omission"].items()}, blue_keys)
    mystic_cap = float(config.get("mystic_cap", 0.0))
    use_mystic = config.get("mode_label") == "stats_plus_mystic"

    red_scores = {}
    red_details = {}
    for number in red_keys:
        math_score = (
            0.46 * red_freq[number]
            + 0.34 * red_recent[number]
            + float(config["omission_weight"]) * red_omission[number]
        )
        adjust = mystic_adjustment(number, profile, mystic_cap) if use_mystic else 0.0
        red_scores[number] = max(0.01, math_score * (1.0 + adjust))
        red_details[number] = {
            "freq": red_freq[number],
            "recent": red_recent[number],
            "omission": red_omission[number],
            "math_score": math_score,
            "mystic_adjust": adjust,
            "element": number_element(number),
        }

    blue_scores = {}
    blue_details = {}
    for number in blue_keys:
        math_score = (
            0.48 * blue_freq[number]
            + 0.34 * blue_recent[number]
            + float(config["omission_weight"]) * blue_omission[number]
        )
        adjust = mystic_adjustment(number, profile, mystic_cap, blue=True) if use_mystic else 0.0
        blue_scores[number] = max(0.01, math_score * (1.0 + adjust))
        blue_details[number] = {
            "freq": blue_freq[number],
            "recent": blue_recent[number],
            "omission": blue_omission[number],
            "math_score": math_score,
            "mystic_adjust": adjust,
            "element": number_element(number),
        }

    return {
        "stats": stats,
        "red_scores": red_scores,
        "blue_scores": blue_scores,
        "red_details": red_details,
        "blue_details": blue_details,
    }


def weighted_sample(weights: Dict[int, float], count: int, rng: random.Random) -> Tuple[int, ...]:
    available = dict(weights)
    selected = []
    for _ in range(count):
        total = sum(max(weight, 0.001) for weight in available.values())
        cursor = rng.random() * total
        running = 0.0
        chosen = next(iter(available))
        for number, weight in available.items():
            running += max(weight, 0.001)
            if running >= cursor:
                chosen = number
                break
        selected.append(chosen)
        available.pop(chosen, None)
    return tuple(selected)


def closeness(value: float, target: float, spread: float) -> float:
    spread = max(spread, 1.0)
    return max(0.0, 1.0 - abs(value - target) / spread)


def combo_score(
    reds: Tuple[int, ...],
    blue: int,
    number_model: Dict[str, object],
    config: Dict[str, float],
) -> float:
    stats = number_model["stats"]
    red_scores = number_model["red_scores"]
    blue_scores = number_model["blue_scores"]
    base = sum(red_scores[number] for number in reds) + blue_scores[blue] * 0.72
    pair_total = sum(stats["pair_freq"].get(tuple(sorted(pair)), 0.0) for pair in combinations(reds, 2))
    pair_score = pair_total / (float(stats["max_pair"]) * 15.0)
    sum_score = closeness(sum(reds), float(stats["avg_sum"]), float(stats["std_sum"]) * 1.65)
    span_score = closeness(max(reds) - min(reds), float(stats["avg_span"]), float(stats["std_span"]) * 1.65)
    odd_score = closeness(sum(1 for red in reds if red % 2), float(stats["avg_odd"]), 2.2)
    zones = (
        sum(1 for red in reds if red <= 11),
        sum(1 for red in reds if 12 <= red <= 22),
        sum(1 for red in reds if red >= 23),
    )
    zone_score = 1.0 - min(
        1.0,
        sum(abs(zones[index] - stats["avg_zone"][index]) for index in range(3)) / 6.0,
    )
    consecutive_pairs = sum(1 for left, right in zip(reds, reds[1:]) if right == left + 1)
    consecutive_penalty = max(0, consecutive_pairs - 1) * 0.16
    recent_overlap_penalty = max(0, len(set(reds) & stats["latest_reds"]) - 2) * 0.20
    return (
        base
        + float(config["pair_weight"]) * pair_score
        + float(config["distribution_weight"]) * (sum_score + span_score + odd_score + zone_score)
        - consecutive_penalty
        - recent_overlap_penalty
    )


def explain_ticket(
    ticket: Ticket,
    number_model: Dict[str, object],
    profile: BaziProfile,
    config: Dict[str, float],
) -> List[str]:
    red_details = number_model["red_details"]
    blue_details = number_model["blue_details"]
    hot_reds = sorted(ticket.reds, key=lambda num: red_details[num]["freq"], reverse=True)[:2]
    omitted_reds = sorted(ticket.reds, key=lambda num: red_details[num]["omission"], reverse=True)[:2]
    useful_matches = [num for num in ticket.reds if red_details[num]["element"] in profile.useful_elements]
    zones = (
        sum(1 for red in ticket.reds if red <= 11),
        sum(1 for red in ticket.reds if 12 <= red <= 22),
        sum(1 for red in ticket.reds if red >= 23),
    )
    reasons = [
        f"数学侧：红球 {fmt_numbers(hot_reds)} 在近200期频率/近期权重较靠前，{fmt_numbers(omitted_reds)} 兼顾遗漏回补。",
        f"玄学侧：日主 {profile.day_master}{profile.day_element}，取 {'、'.join(profile.useful_elements)} 为喜用；玄学只做小幅偏置修正，红球 {fmt_numbers(useful_matches) or '无'} 五行贴合。",
        f"结构侧：和值 {sum(ticket.reds)}、奇偶 {sum(n % 2 for n in ticket.reds)}:{6 - sum(n % 2 for n in ticket.reds)}、三区 {zones[0]}-{zones[1]}-{zones[2]}，贴近历史分布。",
        f"蓝球 {ticket.blue_text} 属{blue_details[ticket.blue]['element']}，同时结合蓝球热度、遗漏和八字映射得分，并避开本注红球数字重复。",
        f"参数侧：回测选中模式 {config['mode_label']}，玄学偏置上限 {config['mystic_cap']:.2f}，衰减 {config['decay']:.3f}。",
    ]
    return reasons


def fmt_numbers(numbers: Sequence[int]) -> str:
    return "、".join(f"{number:02d}" for number in numbers)


def candidate_pool(scores: Dict[int, float], limit: int) -> List[int]:
    return sorted(scores, key=scores.get, reverse=True)[:limit]


def candidate_combos(numbers: Sequence[int], size: int) -> List[Tuple[int, ...]]:
    return [tuple(combo) for combo in combinations(numbers, size)]


def diversification_penalty(ticket: Ticket, selected: Sequence[Ticket], diversity_weight: float) -> float:
    if not selected:
        return 0.0
    overlap = sum(max(0, len(set(ticket.reds) & set(existing.reds)) - 3) for existing in selected)
    same_blue = sum(1 for existing in selected if existing.blue == ticket.blue)
    return diversity_weight * (overlap + same_blue * 0.6)


def generate_tickets(
    draws: Sequence[Draw],
    profile: BaziProfile,
    count: int,
    config: Dict[str, float],
    seed_context: str,
    include_reasons: bool = True,
    quick: bool = False,
    number_model: Dict[str, object] | None = None,
) -> List[Ticket]:
    if number_model is None:
        number_model = build_number_scores(draws, profile, config)
    red_scores = number_model["red_scores"]
    blue_scores = number_model["blue_scores"]
    historical_keys = number_model["stats"]["historical_keys"]
    candidates: Dict[Tuple[Tuple[int, ...], int], Ticket] = {}

    red_pool_size = 8 if quick else 14
    blue_pool_size = 3 if quick else 6
    red_pool = candidate_pool(red_scores, red_pool_size)
    blue_pool = candidate_pool(blue_scores, blue_pool_size)

    for reds in candidate_combos(red_pool, 6):
        reds = tuple(sorted(reds))
        for blue in blue_pool:
            if blue in reds:
                continue
            key = (reds, blue)
            if key in historical_keys or key in candidates:
                continue
            score = combo_score(reds, blue, number_model, config)
            candidates[key] = Ticket(reds=reds, blue=blue, score=score)

    selected: List[Ticket] = []
    remaining = list(candidates.values())
    diversity_weight = float(config.get("diversity_weight", 0.0))
    while remaining and len(selected) < count:
        ticket = max(
            remaining,
            key=lambda item: item.score - diversification_penalty(item, selected, diversity_weight),
        )
        remaining.remove(ticket)
        if any(ticket.reds == other.reds for other in selected):
            continue
        selected.append(ticket)

    for ticket in sorted(remaining, key=lambda item: item.score, reverse=True):
        if len(selected) >= count:
            break
        if any(ticket.reds == other.reds for other in selected):
            continue
        selected.append(ticket)

    if include_reasons:
        selected = [
            Ticket(
                reds=ticket.reds,
                blue=ticket.blue,
                score=ticket.score,
                reasons=explain_ticket(ticket, number_model, profile, config),
            )
            for ticket in selected
        ]
    return selected


def prize_rank(red_hits: int, blue_hit: bool) -> str:
    if red_hits == 6 and blue_hit:
        return "一等奖"
    if red_hits == 6:
        return "二等奖"
    if red_hits == 5 and blue_hit:
        return "三等奖"
    if red_hits == 5 or (red_hits == 4 and blue_hit):
        return "四等奖"
    if red_hits == 4 or (red_hits == 3 and blue_hit):
        return "五等奖"
    if blue_hit:
        return "六等奖"
    return "未中"


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


def evaluate_ticket(ticket: Ticket, draw: Draw) -> TicketEvaluation:
    red_hits = len(set(ticket.reds) & set(draw.reds))
    blue_hit = ticket.blue == draw.blue
    rank = prize_rank(red_hits, blue_hit)
    utility = utility_by_rank(rank) + red_hits * 0.6 + (0.5 if blue_hit else 0.0)
    return TicketEvaluation(red_hits=red_hits, blue_hit=blue_hit, rank=rank, utility=utility)


def evaluate_portfolio(
    tickets: Sequence[Ticket], draw: Draw, cost_per_ticket: float = 1.0
) -> PortfolioEvaluation:
    results = [evaluate_ticket(ticket, draw) for ticket in tickets]
    total_utility = sum(result.utility for result in results)
    overlaps = [
        len(set(left.reds) & set(right.reds))
        for left, right in combinations(tickets, 2)
    ]
    overlap_penalty = sum(max(0, overlap - 3) * 0.35 for overlap in overlaps)
    rank_order = ["一等奖", "二等奖", "三等奖", "四等奖", "五等奖", "六等奖", "未中"]
    best_rank = min((result.rank for result in results), key=lambda rank: rank_order.index(rank), default="未中")
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


def split_backtest_indices(total_windows: int) -> Tuple[range, range]:
    tune_count = max(6, int(total_windows * 0.7))
    tune_count = min(tune_count, max(total_windows - 3, 1))
    return range(0, tune_count), range(tune_count, total_windows)


def expected_value_lcb(
    net_utilities: Sequence[float],
    uncertainty_z: float = 1.28,
    volatility_weight: float = 0.12,
) -> Tuple[float, float, float, float]:
    average_value = statistics.mean(net_utilities) if net_utilities else 0.0
    volatility = statistics.pstdev(net_utilities) if len(net_utilities) > 1 else 0.0
    standard_error = volatility / math.sqrt(len(net_utilities)) if net_utilities else 0.0
    lower_bound = average_value - volatility * volatility_weight - standard_error * uncertainty_z
    return average_value, volatility, standard_error, lower_bound


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


def config_grid(iterations: int) -> List[Dict[str, float]]:
    decays = [0.955, 0.970, 0.985]
    omissions = [0.12, 0.20, 0.28]
    pair_weights = [0.10, 0.18, 0.26]
    distribution_weights = [0.18, 0.28, 0.38]
    diversity_weights = [0.18, 0.30]
    mystic_caps = [0.00, 0.04, 0.08]
    base_modes = ["stats_only", "stats_plus_mystic"]
    configs = []
    for decay, omission, pair_weight, distribution_weight, diversity_weight, mystic_cap, base_mode in product(
        decays,
        omissions,
        pair_weights,
        distribution_weights,
        diversity_weights,
        mystic_caps,
        base_modes,
    ):
        configs.append(
            {
                "decay": decay,
                "omission_weight": omission,
                "pair_weight": pair_weight,
                "distribution_weight": distribution_weight,
                "diversity_weight": diversity_weight,
                "mystic_cap": mystic_cap,
                "mode_label": base_mode,
            }
        )

    configs = sorted(
        configs,
        key=lambda config: stable_seed(
            config["decay"],
            config["omission_weight"],
            config["pair_weight"],
            config["distribution_weight"],
            config["diversity_weight"],
            config["mystic_cap"],
            config["mode_label"],
        ),
    )
    if iterations >= len(configs):
        return configs
    target = max(1, iterations)
    if target == 1:
        return [configs[0]]
    indices = [round(index * (len(configs) - 1) / (target - 1)) for index in range(target)]
    return [configs[index] for index in indices]


def run_backtest(
    draws: Sequence[Draw],
    profile: BaziProfile,
    ticket_count: int,
    windows: int,
    iterations: int,
) -> BacktestResult:
    chronological = list(reversed(draws))
    configs = config_grid(iterations)
    tickets_per_draw = min(ticket_count, 30)
    if len(chronological) < 45:
        default_config = configs[0]
        return BacktestResult(
            evaluated_windows=0,
            iterations=len(configs),
            tickets_per_draw=tickets_per_draw,
            best_config=default_config,
            average_score=0.0,
            average_red_hits=0.0,
            blue_hit_rate=0.0,
            best_prize_counts={},
            top_iterations=[],
        )

    start_index = max(30, len(chronological) - windows)
    target_indices = list(range(start_index, len(chronological)))
    tune_range, validate_range = split_backtest_indices(len(target_indices))
    summaries = []
    stats_cache: Dict[Tuple[int, float], Dict[str, object]] = {}
    number_model_cache: Dict[Tuple[int, float, float, float, str], Dict[str, object]] = {}

    for config_index, config in enumerate(configs, start=1):
        tune_portfolios: List[PortfolioEvaluation] = []
        validate_portfolios: List[PortfolioEvaluation] = []
        all_portfolios: List[PortfolioEvaluation] = []
        tune_utilities: List[float] = []
        validate_utilities: List[float] = []
        prize_counts: Counter[str] = Counter()

        for offset, target_index in enumerate(target_indices):
            target = chronological[target_index]
            history = chronological[:target_index]
            if len(history) < 30:
                continue
            history_newest = list(reversed(history[-160:]))
            decay = float(config["decay"])
            stats_key = (target_index, decay)
            stats = stats_cache.get(stats_key)
            if stats is None:
                stats = build_stats(history_newest, decay)
                stats_cache[stats_key] = stats
            model_key = (
                target_index,
                decay,
                float(config["omission_weight"]),
                float(config.get("mystic_cap", 0.0)),
                str(config.get("mode_label", "")),
            )
            number_model = number_model_cache.get(model_key)
            if number_model is None:
                number_model = build_number_scores(history_newest, profile, config, stats=stats)
                number_model_cache[model_key] = number_model
            tickets = generate_tickets(
                history_newest,
                profile,
                tickets_per_draw,
                config,
                seed_context=f"backtest-{config_index}-{target.issue}",
                include_reasons=False,
                quick=True,
                number_model=number_model,
            )
            if not tickets:
                continue
            portfolio = evaluate_portfolio(tickets, target)
            all_portfolios.append(portfolio)
            if offset in tune_range:
                tune_portfolios.append(portfolio)
                tune_utilities.append(portfolio.net_utility)
            elif offset in validate_range:
                validate_portfolios.append(portfolio)
                validate_utilities.append(portfolio.net_utility)
            prize_counts[portfolio.best_rank] += 1

        evaluated = len(all_portfolios)
        if evaluated:
            net_utilities = [item.net_utility for item in all_portfolios]
            tune_miss_streak = longest_non_prize_streak(tune_portfolios)
            validate_miss_streak = longest_non_prize_streak(validate_portfolios)
            tune_ev, tune_volatility, tune_standard_error, tune_score = expected_value_lcb(tune_utilities)
            validate_ev, validate_volatility, validate_standard_error, validate_score = expected_value_lcb(
                validate_utilities
            )
            all_ev, all_volatility, all_standard_error, all_score = expected_value_lcb(net_utilities)
            selection_portfolios = validate_portfolios or tune_portfolios or all_portfolios
            selection_utilities = [item.net_utility for item in selection_portfolios]
            selection_red_coverages = [item.red_coverage for item in selection_portfolios]
            selection_blue_hits = sum(1 for item in selection_portfolios if item.blue_hits > 0)
            selection_evaluated = len(selection_portfolios)
            selection_expected_value = statistics.mean(selection_utilities) if selection_utilities else all_ev
            selection_score = validate_score if validate_portfolios else tune_score if tune_portfolios else all_score
            selection_standard_error = (
                validate_standard_error
                if validate_portfolios
                else tune_standard_error if tune_portfolios else all_standard_error
            )
            selection_volatility = (
                validate_volatility if validate_portfolios else tune_volatility if tune_portfolios else all_volatility
            )
            mode_label = "stats_only"
            if tune_utilities and validate_utilities:
                mode_label = "tune_validate"
            elif tune_utilities:
                mode_label = "tune_only"
            elif validate_utilities:
                mode_label = "validate_only"
            summaries.append(
                {
                    "iteration": config_index,
                    "config": config,
                    "average_score": selection_expected_value,
                    "average_red_hits": statistics.mean(selection_red_coverages),
                    "blue_hit_rate": selection_blue_hits / selection_evaluated,
                    "prize_counts": dict(prize_counts),
                    "evaluated": evaluated,
                    "tune_score": tune_score,
                    "validate_score": validate_score,
                    "tune_expected_value": tune_ev,
                    "validate_expected_value": validate_ev,
                    "validate_ev_lcb": selection_score,
                    "per_ticket_expected_value": selection_expected_value / max(tickets_per_draw, 1),
                    "ev_standard_error": selection_standard_error,
                    "volatility": selection_volatility,
                    "max_miss_streak": validate_miss_streak if validate_portfolios else tune_miss_streak,
                    "small_prize_rate": small_prize_rate(selection_portfolios),
                    "mode_label": mode_label,
                }
            )

    if not summaries:
        default_config = configs[0]
        return BacktestResult(
            evaluated_windows=0,
            iterations=len(configs),
            tickets_per_draw=tickets_per_draw,
            best_config=default_config,
            average_score=0.0,
            average_red_hits=0.0,
            blue_hit_rate=0.0,
            best_prize_counts={},
            top_iterations=[],
        )

    tune_shortlist_size = max(3, min(12, max(1, len(summaries) // 6)))
    summaries.sort(
        key=lambda item: (
            -float(item["tune_score"]),
            -float(item["tune_expected_value"]),
            float(item["volatility"]),
            -float(item["validate_score"]),
            int(item["max_miss_streak"]),
        ),
    )
    tune_shortlist = summaries[:tune_shortlist_size]
    tune_shortlist.sort(
        key=lambda item: (
            -float(item["validate_score"]),
            -float(item["validate_expected_value"]),
            float(item["ev_standard_error"]),
            float(item["volatility"]),
            int(item["max_miss_streak"]),
            -float(item["tune_score"]),
        ),
    )
    best = tune_shortlist[0]
    return BacktestResult(
        evaluated_windows=int(best["evaluated"]),
        iterations=len(configs),
        tickets_per_draw=tickets_per_draw,
        best_config=best["config"],
        average_score=float(best["average_score"]),
        average_red_hits=float(best["average_red_hits"]),
        blue_hit_rate=float(best["blue_hit_rate"]),
        best_prize_counts=best["prize_counts"],
        top_iterations=tune_shortlist[:5],
        tune_score=float(best["tune_score"]),
        validate_score=float(best["validate_score"]),
        tune_expected_value=float(best["tune_expected_value"]),
        validate_expected_value=float(best["validate_expected_value"]),
        validate_ev_lcb=float(best["validate_ev_lcb"]),
        per_ticket_expected_value=float(best["per_ticket_expected_value"]),
        ev_standard_error=float(best["ev_standard_error"]),
        volatility=float(best["volatility"]),
        max_miss_streak=int(best["max_miss_streak"]),
        small_prize_rate=float(best["small_prize_rate"]),
        mode_label=str(best["mode_label"]),
    )


def parse_birth_datetime(date_value: str, time_value: str) -> datetime:
    if not date_value or not time_value:
        raise ValueError("请填写公历出生日期和出生时间")
    return datetime.strptime(f"{date_value} {time_value}", "%Y-%m-%d %H:%M")


def parse_time_value(time_value: str) -> Tuple[int, int]:
    if not time_value:
        raise ValueError("请填写出生时间")
    parsed = datetime.strptime(time_value, "%H:%M")
    return parsed.hour, parsed.minute


def parse_birth_input(form: Dict[str, str]) -> Tuple[datetime, str]:
    calendar_type = form.get("calendar_type", "solar")
    time_value = form.get("birth_time", "")
    hour, minute = parse_time_value(time_value)
    if calendar_type == "lunar":
        year_text = form.get("lunar_year", "").strip()
        month_text = form.get("lunar_month", "").strip()
        day_text = form.get("lunar_day", "").strip()
        if not year_text or not month_text or not day_text:
            raise ValueError("请填写完整的农历年月日")
        lunar_year = int(year_text)
        lunar_month = int(month_text)
        lunar_day = int(day_text)
        if not (1900 <= lunar_year <= 2100):
            raise ValueError("农历年份请填写 1900-2100")
        if not (1 <= lunar_month <= 12):
            raise ValueError("农历月份请填写 1-12")
        if not (1 <= lunar_day <= 30):
            raise ValueError("农历日期请填写 1-30")
        if form.get("lunar_leap") == "1":
            lunar_month = -lunar_month
        try:
            from lunar_python import Lunar
        except Exception as exc:
            raise RuntimeError(f"阴历输入需要 `lunar-python` 依赖：{exc}") from exc
        lunar = Lunar.fromYmdHms(lunar_year, lunar_month, lunar_day, hour, minute, 0)
        solar = lunar.getSolar()
        birth_dt = datetime(solar.getYear(), solar.getMonth(), solar.getDay(), hour, minute)
        return (
            birth_dt,
            f"输入生日：农历 {lunar} {time_value}，已换算为公历 {birth_dt.strftime('%Y-%m-%d %H:%M')}",
        )
    birth_dt = parse_birth_datetime(form.get("birth_date", ""), time_value)
    return birth_dt, f"输入生日：公历 {birth_dt.strftime('%Y-%m-%d %H:%M')}"


def format_prize_counts(prize_counts: Dict[str, int]) -> str:
    order = ["一等奖", "二等奖", "三等奖", "四等奖", "五等奖", "六等奖", "未中"]
    parts = [f"{name}{prize_counts[name]}期" for name in order if prize_counts.get(name)]
    return "，".join(parts) if parts else "暂无"


def backtest_mode_label(backtest: BacktestResult) -> str:
    mode_value = backtest.mode_label
    if mode_value not in {"stats_plus_mystic", "stats_only"}:
        mode_value = str(backtest.best_config.get("mode_label", mode_value))
    return "玄学增强" if mode_value == "stats_plus_mystic" else "纯统计基线"


def build_backtest_explanation(backtest: BacktestResult) -> List[str]:
    return [
        f"这次先用最近 {backtest.evaluated_windows} 期里的前半段挑参数，再用后半段做验证，尽量减少参数刷分。",
        f"主指标改成整组 {backtest.tickets_per_draw} 注号码的数学期望下置信界，不再优先追小奖覆盖率。",
        f"验证段期望净值 {backtest.validate_expected_value:.2f}，风险折扣后 EV {backtest.validate_ev_lcb:.2f}，每注期望 {backtest.per_ticket_expected_value:.2f}。",
        f"调参段风险折扣 EV {backtest.tune_score:.2f}，验证段波动 {backtest.volatility:.2f}，标准误 {backtest.ev_standard_error:.2f}。",
        f"最长连挂 {backtest.max_miss_streak} 期，有奖覆盖率 {backtest.small_prize_rate * 100:.1f}%。",
        f"当前模式：{backtest_mode_label(backtest)}。",
    ]


def build_iteration_plain_text(item: Dict[str, object]) -> str:
    prize_counts = item["prize_counts"]
    missed = int(prize_counts.get("未中", 0))
    blue_only = int(prize_counts.get("六等奖", 0))
    small_prize = int(prize_counts.get("五等奖", 0)) + int(prize_counts.get("四等奖", 0))
    validate_ev = float(item.get("validate_expected_value", item.get("average_score", 0.0)))
    ev_lcb = float(item.get("validate_ev_lcb", item.get("validate_score", 0.0)))
    return (
        f"大白话：这轮参数验证期望 {validate_ev:.2f}，风险折扣后 {ev_lcb:.2f}；"
        f"回看历史时大约 {missed} 期完全没碰上，"
        f"{blue_only} 期主要靠蓝球命中，{small_prize} 期能摸到小奖。"
    )


TEMPLATE = """
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>双色球玄数双模选号</title>
  <style>
    :root { color-scheme: light; --red:#dc2626; --blue:#2563eb; --ink:#111827; --muted:#6b7280; --line:#e5e7eb; --bg:#f8fafc; --card:#ffffff; }
    body { margin:0; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif; color:var(--ink); background:linear-gradient(180deg,#fff7f7 0,#f8fafc 260px); }
    .wrap { max-width:1180px; margin:0 auto; padding:28px 18px 60px; }
    .hero { display:grid; grid-template-columns:1.3fr .7fr; gap:18px; align-items:stretch; }
    .card { background:rgba(255,255,255,.92); border:1px solid var(--line); border-radius:18px; box-shadow:0 14px 40px rgba(15,23,42,.07); padding:20px; }
    h1 { margin:0 0 8px; font-size:32px; letter-spacing:-.04em; }
    h2 { margin:0 0 14px; font-size:20px; }
    h3 { margin:18px 0 10px; font-size:17px; }
    p { line-height:1.65; }
    .muted { color:var(--muted); font-size:14px; }
    .pill { display:inline-flex; align-items:center; gap:6px; padding:5px 10px; border-radius:999px; background:#f1f5f9; color:#334155; font-size:13px; margin:3px 4px 3px 0; }
    .red-ball,.blue-ball { display:inline-flex; justify-content:center; align-items:center; width:30px; height:30px; border-radius:50%; color:#fff; font-weight:700; margin-right:4px; font-size:13px; }
    .red-ball { background:var(--red); }
    .blue-ball { background:var(--blue); }
    form { display:grid; grid-template-columns:repeat(6, minmax(0,1fr)); gap:14px; }
    label { display:block; font-size:13px; color:#374151; margin-bottom:6px; font-weight:650; }
    input,select { width:100%; box-sizing:border-box; border:1px solid #d1d5db; border-radius:12px; padding:11px 12px; font-size:15px; background:#fff; }
    .span2 { grid-column:span 2; }
    .span3 { grid-column:span 3; }
    .span6 { grid-column:span 6; }
    button { border:0; border-radius:12px; padding:12px 16px; color:#fff; background:linear-gradient(135deg,#dc2626,#7c3aed); cursor:pointer; font-weight:700; font-size:15px; }
    .secondary { color:#334155; background:#e2e8f0; text-decoration:none; display:inline-flex; justify-content:center; align-items:center; border-radius:12px; padding:12px 16px; font-weight:700; }
    table { width:100%; border-collapse:collapse; font-size:14px; }
    th,td { border-bottom:1px solid var(--line); padding:9px 8px; text-align:left; vertical-align:top; }
    th { color:#475569; background:#f8fafc; font-weight:700; }
    .grid { display:grid; grid-template-columns:1fr 1fr; gap:18px; margin-top:18px; }
    .tickets { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:16px; }
    .ticket { border:1px solid var(--line); border-radius:16px; padding:16px; background:#fff; }
    .ticket-title { display:flex; justify-content:space-between; gap:12px; align-items:center; margin-bottom:12px; }
    .score { color:#7c3aed; font-weight:800; }
    ul { margin:10px 0 0 20px; padding:0; }
    li { margin:6px 0; line-height:1.5; }
    .alert { background:#fff7ed; color:#9a3412; border:1px solid #fed7aa; border-radius:14px; padding:12px 14px; margin:14px 0; }
    .ok { background:#ecfdf5; color:#047857; border-color:#a7f3d0; }
    .hidden { display:none !important; }
    .field-note { color:var(--muted); font-size:13px; align-self:center; }
    .checkbox-inline { display:flex; align-items:center; min-height:43px; color:#374151; font-weight:650; }
    .checkbox-inline input { width:auto; margin-right:8px; }
    .bar { height:8px; background:#e5e7eb; border-radius:999px; overflow:hidden; }
    .bar > span { display:block; height:100%; background:linear-gradient(90deg,#ef4444,#2563eb); }
    .small-table td,.small-table th { padding:7px 8px; }
    .plain-list { background:#f8fafc; border:1px solid var(--line); border-radius:14px; padding:12px 14px; }
    .plain-list ul { margin-top:0; }
    .toast { position:fixed; right:22px; bottom:22px; max-width:380px; padding:13px 16px; border-radius:14px; color:#fff; background:#334155; box-shadow:0 18px 45px rgba(15,23,42,.25); opacity:0; transform:translateY(12px); pointer-events:none; transition:.22s ease; z-index:9999; line-height:1.45; }
    .toast.show { opacity:1; transform:translateY(0); }
    .toast.success { background:#047857; }
    .toast.error { background:#b91c1c; }
    .toast.info { background:#334155; }
    @media (max-width:900px) { .hero,.grid,.tickets { grid-template-columns:1fr; } form { grid-template-columns:1fr 1fr; } .span2,.span3,.span6 { grid-column:span 2; } }
  </style>
</head>
<body>
<div id="toast" class="toast" role="status" aria-live="polite"></div>
<div class="wrap">
  <div class="hero">
    <section class="card">
      <h1>双色球玄数双模选号</h1>
      <p class="muted">抓取最近 200 期开奖数据，按子平八字排盘，再通过历史回测迭代选择参数，生成每注号码及理由。彩票结果随机，本工具仅作娱乐和数据实验参考。</p>
      {% if latest %}
        <div>
          <span class="pill">最新期号：{{ latest.issue }}</span>
          <span class="pill">开奖日期：{{ latest.open_time }}</span>
          <span class="pill">已获取：{{ draws|length }} 期</span>
          <span class="pill">数据源：中彩网 JSONP</span>
        </div>
        <p>
          {% for red in latest.reds %}<span class="red-ball">{{ "%02d"|format(red) }}</span>{% endfor %}
          <span class="blue-ball">{{ "%02d"|format(latest.blue) }}</span>
        </p>
      {% endif %}
      {% if data_message %}<div class="alert">{{ data_message }}</div>{% endif %}
      {% if fetched_at %}<p class="muted">本地抓取时间：{{ fetched_at }}；缓存 30 分钟，可点“刷新开奖数据”。</p>{% endif %}
    </section>
    <section class="card">
      <h2>输入信息</h2>
      <form method="post" id="forecastForm">
        <div class="span2">
          <label>性别</label>
          <select name="gender">
            <option value="男" {% if form.gender == "男" %}selected{% endif %}>男</option>
            <option value="女" {% if form.gender == "女" %}selected{% endif %}>女</option>
          </select>
        </div>
        <div class="span2">
          <label>生日类型</label>
          <select name="calendar_type" id="calendarType">
            <option value="solar" {% if form.calendar_type == "solar" %}selected{% endif %}>公历 / 阳历</option>
            <option value="lunar" {% if form.calendar_type == "lunar" %}selected{% endif %}>农历 / 阴历</option>
          </select>
        </div>
        <div class="span2">
          <label>出生时间</label>
          <input type="time" name="birth_time" value="{{ form.birth_time }}" required>
        </div>
        <div class="span2 calendar-field solar-field {% if form.calendar_type == 'lunar' %}hidden{% endif %}">
          <label>公历出生日期</label>
          <input type="date" name="birth_date" value="{{ form.birth_date }}">
        </div>
        <div class="span2 calendar-field lunar-field {% if form.calendar_type != 'lunar' %}hidden{% endif %}">
          <label>农历年份</label>
          <input type="number" name="lunar_year" min="1900" max="2100" value="{{ form.lunar_year }}">
        </div>
        <div class="span2 calendar-field lunar-field {% if form.calendar_type != 'lunar' %}hidden{% endif %}">
          <label>农历月份</label>
          <input type="number" name="lunar_month" min="1" max="12" value="{{ form.lunar_month }}">
        </div>
        <div class="span2 calendar-field lunar-field {% if form.calendar_type != 'lunar' %}hidden{% endif %}">
          <label>农历日期</label>
          <input type="number" name="lunar_day" min="1" max="30" value="{{ form.lunar_day }}">
        </div>
        <div class="span2 calendar-field lunar-field {% if form.calendar_type != 'lunar' %}hidden{% endif %}">
          <label>是否闰月</label>
          <label class="checkbox-inline"><input type="checkbox" name="lunar_leap" value="1" {% if form.lunar_leap == "1" %}checked{% endif %}>这是闰月</label>
        </div>
        <div class="span6 field-note" id="calendarHint">
          {% if form.calendar_type == "lunar" %}
            阴历模式会先把农历生日换算成公历，再按节气排四柱。
          {% else %}
            公历模式会直接按输入日期和时间排四柱。
          {% endif %}
        </div>
        <div class="span2">
          <label>生成注数 n</label>
          <input type="number" name="ticket_count" min="1" max="30" value="{{ form.ticket_count }}">
        </div>
        <div class="span2">
          <label>回测期数</label>
          <input type="number" name="backtest_windows" min="20" max="100" value="{{ form.backtest_windows }}">
        </div>
        <div class="span2">
          <label>迭代轮数</label>
          <input type="number" name="iterations" min="12" max="180" value="{{ form.iterations }}">
        </div>
        <div class="span6 field-note">默认使用 60 期回测和 72 轮参数覆盖；数值越大越稳但耗时越长。</div>
        <div class="span3">
          <button type="submit" id="generateButton">排盘 + 回测迭代 + 生成号码</button>
        </div>
        <div class="span3">
          <a class="secondary" href="/?refresh=1">刷新开奖数据</a>
        </div>
      </form>
    </section>
  </div>

  {% if error %}
    <div class="alert">{{ error }}</div>
  {% endif %}

  {% if profile and backtest %}
    <div class="grid">
      <section class="card">
        <h2>子平排盘</h2>
        {% if birth_input_summary %}<p class="muted">{{ birth_input_summary }}</p>{% endif %}
        <p class="muted">{{ profile.engine }}；{{ profile.calendar_note }}</p>
        <table class="small-table">
          <thead><tr><th>四柱</th><th>干支</th><th>十神</th><th>藏干</th></tr></thead>
          <tbody>
            {% for name, pillar in profile.pillars.items() %}
              <tr>
                <td>{{ name }}</td>
                <td><b>{{ pillar }}</b></td>
                <td>{{ profile.ten_gods[name] }}</td>
                <td>{{ profile.hidden_stems.get(name, "-") }}</td>
              </tr>
            {% endfor %}
          </tbody>
        </table>
        <p>
          <span class="pill">日主：{{ profile.day_master }} {{ profile.day_element }}</span>
          <span class="pill">旺衰：{{ profile.strength_label }}</span>
          <span class="pill">喜用：{{ "、".join(profile.useful_elements) }}</span>
          <span class="pill">忌向：{{ "、".join(profile.avoid_elements) }}</span>
          <span class="pill">大运：{{ profile.luck_direction }}</span>
        </p>
        <h3>五行权重</h3>
        {% for element, value in profile.element_scores.items() %}
          <div class="muted">{{ element }}：{{ "%.2f"|format(value) }}</div>
          <div class="bar"><span style="width:{{ [value * 12, 100]|min }}%"></span></div>
        {% endfor %}
      </section>

      <section class="card">
        <h2>回测迭代结果</h2>
        <div class="plain-list">
          <b>大白话解读</b>
          <ul>
            {% for line in backtest_explanation %}
              <li>{{ line }}</li>
            {% endfor %}
          </ul>
        </div>
        <p>
          <span class="pill">有效回测：{{ backtest.evaluated_windows }} 期</span>
          <span class="pill">迭代：{{ backtest.iterations }} 轮</span>
          <span class="pill">每期：{{ backtest.tickets_per_draw }} 注</span>
        </p>
        <p>
          <span class="pill">验证EV：{{ "%.2f"|format(backtest.validate_expected_value) }}</span>
          <span class="pill">风险折扣EV：{{ "%.2f"|format(backtest.validate_ev_lcb) }}</span>
          <span class="pill">每注EV：{{ "%.2f"|format(backtest.per_ticket_expected_value) }}</span>
          <span class="pill">调参EV-LCB：{{ "%.2f"|format(backtest.tune_score) }}</span>
          <span class="pill">波动：{{ "%.2f"|format(backtest.volatility) }}</span>
          <span class="pill">标准误：{{ "%.2f"|format(backtest.ev_standard_error) }}</span>
          <span class="pill">最长连挂：{{ backtest.max_miss_streak }} 期</span>
          <span class="pill">有奖覆盖：{{ "%.1f"|format(backtest.small_prize_rate * 100) }}%</span>
          <span class="pill">模式：{{ backtest_mode_text }}</span>
        </p>
        <h3>优胜参数</h3>
        <p>
          <span class="pill">模式 {{ backtest.best_config.mode_label }}</span>
          <span class="pill">玄学偏置 {{ "%.2f"|format(backtest.best_config.mystic_cap) }}</span>
          <span class="pill">衰减 {{ "%.3f"|format(backtest.best_config.decay) }}</span>
          <span class="pill">遗漏 {{ "%.2f"|format(backtest.best_config.omission_weight) }}</span>
        </p>
        <h3>前 5 轮</h3>
        <table class="small-table">
          <thead><tr><th>轮次</th><th>EV-LCB</th><th>验证EV</th><th>红球</th><th>蓝球</th><th>奖级概览</th></tr></thead>
          <tbody>
            {% for item in top_iteration_rows %}
              <tr>
                <td>{{ item.iteration }}</td>
                <td>{{ "%.2f"|format(item.validate_ev_lcb) }}</td>
                <td>{{ "%.2f"|format(item.validate_expected_value) }}</td>
                <td>{{ "%.2f"|format(item.average_red_hits) }}</td>
                <td>{{ "%.1f"|format(item.blue_hit_rate * 100) }}%</td>
                <td>
                  {{ item.prize_text }}
                  <div class="muted">{{ item.plain_text }}</div>
                </td>
              </tr>
            {% endfor %}
          </tbody>
        </table>
      </section>
    </div>

    <section class="card" style="margin-top:18px;">
      <h2>生成的 {{ tickets|length }} 注号码</h2>
      <div class="tickets">
        {% for ticket in tickets %}
          <div class="ticket">
            <div class="ticket-title">
              <b>第 {{ loop.index }} 注</b>
              <span class="score">模型分 {{ "%.2f"|format(ticket.score) }}</span>
            </div>
            <p>
              {% for red in ticket.reds %}<span class="red-ball">{{ "%02d"|format(red) }}</span>{% endfor %}
              <span class="blue-ball">{{ "%02d"|format(ticket.blue) }}</span>
            </p>
            <ul>
              {% for reason in ticket.reasons %}
                <li>{{ reason }}</li>
              {% endfor %}
            </ul>
          </div>
        {% endfor %}
      </div>
    </section>
  {% endif %}

  <section class="card" style="margin-top:18px;">
    <h2>最近开奖记录（前 30 条预览）</h2>
    <table>
      <thead><tr><th>期号</th><th>日期</th><th>红球</th><th>蓝球</th></tr></thead>
      <tbody>
        {% for draw in draws[:30] %}
          <tr>
            <td>{{ draw.issue }}</td>
            <td>{{ draw.open_time }}</td>
            <td>
              {% for red in draw.reds %}<span class="red-ball">{{ "%02d"|format(red) }}</span>{% endfor %}
            </td>
            <td><span class="blue-ball">{{ "%02d"|format(draw.blue) }}</span></td>
          </tr>
        {% endfor %}
      </tbody>
    </table>
  </section>
</div>
<script>
  const toastEl = document.getElementById("toast");
  function showToast(message, type = "info", duration = 3600) {
    if (!toastEl || !message) return;
    toastEl.textContent = message;
    toastEl.className = `toast ${type} show`;
    if (duration > 0) {
      window.clearTimeout(window.__toastTimer);
      window.__toastTimer = window.setTimeout(() => toastEl.classList.remove("show"), duration);
    }
  }

  const calendarType = document.getElementById("calendarType");
  const calendarHint = document.getElementById("calendarHint");
  function syncCalendarFields() {
    const mode = calendarType ? calendarType.value : "solar";
    document.querySelectorAll(".solar-field").forEach((el) => el.classList.toggle("hidden", mode !== "solar"));
    document.querySelectorAll(".lunar-field").forEach((el) => el.classList.toggle("hidden", mode !== "lunar"));
    if (calendarHint) {
      calendarHint.textContent = mode === "lunar"
        ? "阴历模式会先把农历生日换算成公历，再按节气排四柱。闰月生日请勾选“这是闰月”。"
        : "公历模式会直接按输入日期和时间排四柱。";
    }
  }
  if (calendarType) {
    calendarType.addEventListener("change", syncCalendarFields);
    syncCalendarFields();
  }

  const formEl = document.getElementById("forecastForm");
  const generateButton = document.getElementById("generateButton");
  if (formEl) {
    formEl.addEventListener("submit", () => {
      showToast("正在排盘、回测迭代并生成号码，可能需要几秒钟…", "info", 0);
      if (generateButton) {
        generateButton.disabled = true;
        generateButton.textContent = "正在计算中…";
      }
    });
  }

  const initialToast = {{ toast_message|tojson }};
  const initialToastType = {{ toast_type|tojson }};
  if (initialToast) {
    showToast(initialToast, initialToastType || "success", 4800);
  }
</script>
</body>
</html>
"""


@app.route("/", methods=["GET", "POST"])
def index():
    force_refresh = request.args.get("refresh") == "1"
    draws, data_message = get_draws(force=force_refresh)
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
    profile = None
    backtest = None
    tickets: List[Ticket] = []
    error = ""
    toast_message = "开奖数据已刷新" if force_refresh and not data_message else ""
    toast_type = "success"
    birth_input_summary = ""

    if request.method == "POST":
        try:
            if not draws:
                raise RuntimeError("没有开奖数据，无法回测和生成号码")
            gender = form["gender"] if form["gender"] in {"男", "女"} else "男"
            calendar_type = form["calendar_type"] if form["calendar_type"] in {"solar", "lunar"} else "solar"
            form["calendar_type"] = calendar_type
            form["lunar_leap"] = "1" if request.form.get("lunar_leap") == "1" else "0"
            birth_dt, birth_input_summary = parse_birth_input(form)
            ticket_count = clamp_int(form["ticket_count"], 5, 1, 30)
            backtest_windows = clamp_int(form["backtest_windows"], 60, 20, 100)
            iterations = clamp_int(form["iterations"], 72, 12, 180)
            form["gender"] = gender
            form["ticket_count"] = str(ticket_count)
            form["backtest_windows"] = str(backtest_windows)
            form["iterations"] = str(iterations)

            profile = build_bazi_profile(gender, birth_dt)
            backtest = run_backtest(draws, profile, ticket_count, backtest_windows, iterations)
            tickets = generate_tickets(
                draws,
                profile,
                ticket_count,
                backtest.best_config,
                seed_context=f"final-{draws[0].issue}-{backtest.average_score:.4f}",
                include_reasons=True,
                quick=False,
            )
            toast_message = f"已完成：生成 {len(tickets)} 注号码，回测 {backtest.evaluated_windows} 期。"
            toast_type = "success"
        except Exception as exc:
            error = str(exc)
            toast_message = f"生成失败：{error}"
            toast_type = "error"

    backtest_explanation = build_backtest_explanation(backtest) if backtest else []
    top_iteration_rows = []
    if backtest:
        for item in backtest.top_iterations:
            row = dict(item)
            row["prize_text"] = format_prize_counts(row["prize_counts"])
            row["plain_text"] = build_iteration_plain_text(row)
            top_iteration_rows.append(row)

    return render_template_string(
        TEMPLATE,
        draws=draws,
        latest=draws[0] if draws else None,
        data_message=data_message,
        fetched_at=DRAW_CACHE.get("fetched_at", ""),
        form=form,
        profile=profile,
        backtest=backtest,
        backtest_explanation=backtest_explanation,
        backtest_mode_text=backtest_mode_label(backtest) if backtest else "",
        top_iteration_rows=top_iteration_rows,
        birth_input_summary=birth_input_summary,
        tickets=tickets,
        error=error,
        toast_message=toast_message,
        toast_type=toast_type,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="双色球玄数双模选号 Web 服务")
    parser.add_argument("--host", default=os.getenv("HOST", "127.0.0.1"), help="监听地址")
    parser.add_argument("--port", type=int, default=int(os.getenv("PORT", "5000")), help="监听端口")
    parser.add_argument(
        "--debug",
        action="store_true",
        default=os.getenv("DEBUG", "").lower() in {"1", "true", "yes", "on"},
        help="开启 Flask 调试模式",
    )
    args = parser.parse_args()
    app.run(host=args.host, port=args.port, debug=args.debug)
