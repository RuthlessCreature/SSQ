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
        "avg_odd": statistics.mean(odd_counts),
        "avg_zone": tuple(statistics.mean(values) for values in zip(*zone_counts)),
        "latest_reds": set(draws[0].reds) if draws else set(),
        "historical_keys": historical_keys,
        "max_pair": max(pair_freq.values()) if pair_freq else 1.0,
    }


def mystic_score(number: int, profile: BaziProfile, blue: bool = False) -> float:
    element = number_element(number)
    score = 0.35
    if element in profile.useful_elements:
        score += 0.42
    if element == profile.day_element:
        score += 0.12
    if blue and number in profile.lucky_blues:
        score += 0.28
    if not blue and number in profile.lucky_reds:
        score += 0.24
    if number % 2 == (0 if profile.gender == "女" else 1):
        score += 0.04
    return min(score, 1.25)


def build_number_scores(draws: Sequence[Draw], profile: BaziProfile, config: Dict[str, float]) -> Dict[str, object]:
    stats = build_stats(draws, float(config["decay"]))
    red_keys = list(range(1, 34))
    blue_keys = list(range(1, 17))
    red_freq = normalize(stats["red_freq"], red_keys)
    red_recent = normalize(stats["red_recent"], red_keys)
    red_omission = normalize({k: math.log1p(v) for k, v in stats["red_omission"].items()}, red_keys)
    blue_freq = normalize(stats["blue_freq"], blue_keys)
    blue_recent = normalize(stats["blue_recent"], blue_keys)
    blue_omission = normalize({k: math.log1p(v) for k, v in stats["blue_omission"].items()}, blue_keys)

    red_scores = {}
    red_details = {}
    for number in red_keys:
        math_score = (
            0.46 * red_freq[number]
            + 0.34 * red_recent[number]
            + float(config["omission_weight"]) * red_omission[number]
        )
        mystic = mystic_score(number, profile)
        red_scores[number] = max(
            0.01,
            float(config["math_weight"]) * math_score + float(config["mystic_weight"]) * mystic,
        )
        red_details[number] = {
            "freq": red_freq[number],
            "recent": red_recent[number],
            "omission": red_omission[number],
            "mystic": mystic,
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
        mystic = mystic_score(number, profile, blue=True)
        blue_scores[number] = max(
            0.01,
            float(config["math_weight"]) * math_score + float(config["mystic_weight"]) * mystic,
        )
        blue_details[number] = {
            "freq": blue_freq[number],
            "recent": blue_recent[number],
            "omission": blue_omission[number],
            "mystic": mystic,
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
    repeat_penalty = max(0, len(set(reds) & stats["latest_reds"]) - 2) * 0.18
    return (
        base
        + float(config["pair_weight"]) * pair_score
        + float(config["distribution_weight"]) * (sum_score + odd_score + zone_score)
        - repeat_penalty
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
        f"玄学侧：日主 {profile.day_master}{profile.day_element}，取 {'、'.join(profile.useful_elements)} 为喜用；红球 {fmt_numbers(useful_matches) or '无'} 五行贴合。",
        f"结构侧：和值 {sum(ticket.reds)}、奇偶 {sum(n % 2 for n in ticket.reds)}:{6 - sum(n % 2 for n in ticket.reds)}、三区 {zones[0]}-{zones[1]}-{zones[2]}，贴近历史分布。",
        f"蓝球 {ticket.blue_text} 属{blue_details[ticket.blue]['element']}，同时结合蓝球热度、遗漏和八字映射得分，并避开本注红球数字重复。",
        f"参数侧：回测选中数学权重 {config['math_weight']:.2f} / 玄学权重 {config['mystic_weight']:.2f}，衰减 {config['decay']:.3f}。",
    ]
    return reasons


def fmt_numbers(numbers: Sequence[int]) -> str:
    return "、".join(f"{number:02d}" for number in numbers)


def generate_tickets(
    draws: Sequence[Draw],
    profile: BaziProfile,
    count: int,
    config: Dict[str, float],
    seed_context: str,
    include_reasons: bool = True,
    quick: bool = False,
) -> List[Ticket]:
    number_model = build_number_scores(draws, profile, config)
    red_scores = number_model["red_scores"]
    blue_scores = number_model["blue_scores"]
    historical_keys = number_model["stats"]["historical_keys"]
    rng = random.Random(stable_seed(seed_context, profile.birth_dt.isoformat(), profile.gender, config))
    attempts = max(count * (22 if quick else 55), 180 if quick else 650)
    candidates: Dict[Tuple[Tuple[int, ...], int], Ticket] = {}

    ranked_reds = sorted(red_scores, key=red_scores.get, reverse=True)
    ranked_blues = sorted(blue_scores, key=blue_scores.get, reverse=True)
    seed_sets = [tuple(sorted(ranked_reds[offset : offset + 6])) for offset in range(0, min(8, len(ranked_reds) - 5))]

    for reds in seed_sets:
        for blue in ranked_blues[:3]:
            if blue in reds:
                continue
            if len(reds) == 6 and (reds, blue) not in historical_keys:
                score = combo_score(reds, blue, number_model, config)
                candidates[(reds, blue)] = Ticket(reds=reds, blue=blue, score=score)

    for _ in range(attempts):
        reds = tuple(sorted(weighted_sample(red_scores, 6, rng)))
        available_blue_scores = {number: score for number, score in blue_scores.items() if number not in reds}
        blue = weighted_sample(available_blue_scores, 1, rng)[0]
        key = (reds, blue)
        if key in historical_keys or key in candidates:
            continue
        if blue in reds:
            continue
        if max(reds) - min(reds) < 14:
            continue
        score = combo_score(reds, blue, number_model, config)
        candidates[key] = Ticket(reds=reds, blue=blue, score=score)

    selected: List[Ticket] = []
    for ticket in sorted(candidates.values(), key=lambda item: item.score, reverse=True):
        if len(selected) >= count:
            break
        if any(ticket.reds == other.reds for other in selected):
            continue
        overlap_ok = all(len(set(ticket.reds) & set(other.reds)) <= 4 for other in selected)
        if overlap_ok or len(selected) < max(2, count // 4):
            selected.append(ticket)

    if len(selected) < count:
        for ticket in sorted(candidates.values(), key=lambda item: item.score, reverse=True):
            if len(selected) >= count:
                break
            if all(ticket.reds != existing.reds for existing in selected):
                selected.append(ticket)

    if len(selected) < count:
        for ticket in sorted(candidates.values(), key=lambda item: item.score, reverse=True):
            if len(selected) >= count:
                break
            if all(ticket.reds != existing.reds or ticket.blue != existing.blue for existing in selected):
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


def evaluate_ticket(ticket: Ticket, draw: Draw) -> Dict[str, object]:
    red_hits = len(set(ticket.reds) & set(draw.reds))
    blue_hit = ticket.blue == draw.blue
    rank = prize_rank(red_hits, blue_hit)
    rank_bonus = {"一等奖": 80, "二等奖": 35, "三等奖": 18, "四等奖": 9, "五等奖": 4, "六等奖": 1, "未中": 0}
    score = red_hits * 2.0 + (1.2 if blue_hit else 0.0) + rank_bonus[rank]
    return {"red_hits": red_hits, "blue_hit": blue_hit, "rank": rank, "score": score}


def config_grid(iterations: int) -> List[Dict[str, float]]:
    math_weights = [0.54, 0.60, 0.66, 0.72, 0.78]
    decays = [0.955, 0.970, 0.985]
    omissions = [0.16, 0.24, 0.32]
    pair_weights = [0.12, 0.20]
    distribution_weights = [0.18, 0.28]
    configs = []
    for math_weight, decay, omission, pair_weight, distribution_weight in product(
        math_weights, decays, omissions, pair_weights, distribution_weights
    ):
        configs.append(
            {
                "math_weight": math_weight,
                "mystic_weight": round(1.0 - math_weight, 2),
                "decay": decay,
                "omission_weight": omission,
                "pair_weight": pair_weight,
                "distribution_weight": distribution_weight,
            }
        )
    return configs[: max(1, min(iterations, len(configs)))]


def run_backtest(
    draws: Sequence[Draw],
    profile: BaziProfile,
    ticket_count: int,
    windows: int,
    iterations: int,
) -> BacktestResult:
    chronological = list(reversed(draws))
    if len(chronological) < 45:
        default_config = config_grid(1)[0]
        return BacktestResult(0, 1, ticket_count, default_config, 0.0, 0.0, 0.0, {}, [])

    start_index = max(30, len(chronological) - windows)
    configs = config_grid(iterations)
    tickets_per_draw = min(ticket_count, 30)
    summaries = []

    for config_index, config in enumerate(configs, start=1):
        total_score = 0.0
        total_red_hits = 0
        blue_hits = 0
        prize_counts: Counter[str] = Counter()
        evaluated = 0

        for target_index in range(start_index, len(chronological)):
            target = chronological[target_index]
            history = chronological[:target_index]
            if len(history) < 30:
                continue
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
            if not tickets:
                continue
            results = [evaluate_ticket(ticket, target) for ticket in tickets]
            best = max(results, key=lambda result: float(result["score"]))
            total_score += float(best["score"])
            total_red_hits += int(best["red_hits"])
            blue_hits += 1 if best["blue_hit"] else 0
            prize_counts[str(best["rank"])] += 1
            evaluated += 1

        if evaluated:
            summaries.append(
                {
                    "iteration": config_index,
                    "config": config,
                    "average_score": total_score / evaluated,
                    "average_red_hits": total_red_hits / evaluated,
                    "blue_hit_rate": blue_hits / evaluated,
                    "prize_counts": dict(prize_counts),
                    "evaluated": evaluated,
                }
            )

    if not summaries:
        default_config = configs[0]
        return BacktestResult(0, len(configs), tickets_per_draw, default_config, 0.0, 0.0, 0.0, {}, [])

    summaries.sort(
        key=lambda item: (
            float(item["average_score"]),
            float(item["average_red_hits"]),
            float(item["blue_hit_rate"]),
        ),
        reverse=True,
    )
    best = summaries[0]
    return BacktestResult(
        evaluated_windows=int(best["evaluated"]),
        iterations=len(configs),
        tickets_per_draw=tickets_per_draw,
        best_config=best["config"],
        average_score=float(best["average_score"]),
        average_red_hits=float(best["average_red_hits"]),
        blue_hit_rate=float(best["blue_hit_rate"]),
        best_prize_counts=best["prize_counts"],
        top_iterations=summaries[:5],
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


def build_backtest_explanation(backtest: BacktestResult) -> List[str]:
    score_hint = "说明这套参数整体更稳" if backtest.average_score >= 4 else "说明这套参数有一定效果，但不算特别强"
    math_bias = "数学成分略重" if backtest.best_config["math_weight"] >= backtest.best_config["mystic_weight"] else "玄学成分略重"
    return [
        f"这次拿最近 {backtest.evaluated_windows} 期历史开奖做了“模拟考试”，看看模型放到过去会打出什么成绩。",
        f"每一期回测都只看当期之前的数据，不偷看后面的开奖号码，所以更接近真实下注前能拿到的信息。",
        f"每期会先生成 {backtest.tickets_per_draw} 注，再只拿其中表现最好的一注给这一轮参数记分，所以这里是在比“这一轮参数最能打的上限”。",
        f"平均红球命中 {backtest.average_red_hits:.2f}，意思是回看这些历史期时，最好那一注平均能碰到接近 2 个红球。",
        f"蓝球命中率 {backtest.blue_hit_rate * 100:.1f}% ，意思是 100 期里大约有 {round(backtest.blue_hit_rate * 100)} 期蓝球能对上。",
        f"平均评分 {backtest.average_score:.2f} 不是奖金，是内部综合分；红球命中多、蓝球命中、奖级更高，分数就更高。{score_hint}。",
        f"最后选中的参数是数学 {backtest.best_config['math_weight']:.2f} + 玄学 {backtest.best_config['mystic_weight']:.2f}，也就是 {math_bias}；衰减 {backtest.best_config['decay']:.3f} 代表更看重近期走势，遗漏 {backtest.best_config['omission_weight']:.2f} 代表会给久未出的号一点补分。",
    ]


def build_iteration_plain_text(item: Dict[str, object]) -> str:
    prize_counts = item["prize_counts"]
    missed = int(prize_counts.get("未中", 0))
    blue_only = int(prize_counts.get("六等奖", 0))
    small_prize = int(prize_counts.get("五等奖", 0)) + int(prize_counts.get("四等奖", 0))
    return (
        f"大白话：这轮参数回看历史时，大约 {missed} 期完全没碰上，"
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
          <input type="number" name="backtest_windows" min="5" max="80" value="{{ form.backtest_windows }}">
        </div>
        <div class="span2">
          <label>迭代轮数</label>
          <input type="number" name="iterations" min="1" max="180" value="{{ form.iterations }}">
        </div>
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
          <span class="pill">平均评分：{{ "%.2f"|format(backtest.average_score) }}</span>
          <span class="pill">平均红球命中：{{ "%.2f"|format(backtest.average_red_hits) }}</span>
          <span class="pill">蓝球命中率：{{ "%.1f"|format(backtest.blue_hit_rate * 100) }}%</span>
        </p>
        <h3>优胜参数</h3>
        <p>
          <span class="pill">数学 {{ "%.2f"|format(backtest.best_config.math_weight) }}</span>
          <span class="pill">玄学 {{ "%.2f"|format(backtest.best_config.mystic_weight) }}</span>
          <span class="pill">衰减 {{ "%.3f"|format(backtest.best_config.decay) }}</span>
          <span class="pill">遗漏 {{ "%.2f"|format(backtest.best_config.omission_weight) }}</span>
        </p>
        <h3>前 5 轮</h3>
        <table class="small-table">
          <thead><tr><th>轮次</th><th>评分</th><th>红球</th><th>蓝球</th><th>奖级概览</th></tr></thead>
          <tbody>
            {% for item in top_iteration_rows %}
              <tr>
                <td>{{ item.iteration }}</td>
                <td>{{ "%.2f"|format(item.average_score) }}</td>
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
        "backtest_windows": request.form.get("backtest_windows", "30"),
        "iterations": request.form.get("iterations", "36"),
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
            backtest_windows = clamp_int(form["backtest_windows"], 30, 5, 80)
            iterations = clamp_int(form["iterations"], 36, 1, 180)
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
