import { Lunar, Solar } from "lunar-javascript";
import {
  composeReadingFromProfile,
  formatDateTime,
  trueSolarReport
} from "../public/assets/reading-core.js";

const GAN_ELEMENTS = {
  "甲": "木", "乙": "木", "丙": "火", "丁": "火", "戊": "土",
  "己": "土", "庚": "金", "辛": "金", "壬": "水", "癸": "水"
};

function json(data, init = {}) {
  return new Response(JSON.stringify(data), {
    ...init,
    headers: {
      "content-type": "application/json; charset=utf-8",
      "cache-control": "no-store",
      ...(init.headers || {})
    }
  });
}

function parseDateInput(value) {
  const match = String(value || "").match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (!match) throw new Error("请输入有效的公历日期。");
  return { year: Number(match[1]), month: Number(match[2]), day: Number(match[3]) };
}

function parseTimeInput(value) {
  const match = String(value || "").match(/^(\d{2}):(\d{2})$/);
  if (!match) throw new Error("请输入有效的出生时间。");
  return { hour: Number(match[1]), minute: Number(match[2]) };
}

function makeDate(year, month, day, hour = 0, minute = 0) {
  return new Date(Date.UTC(year, month - 1, day, hour, minute, 0, 0));
}

function partsFromDate(date) {
  return {
    year: date.getUTCFullYear(),
    month: date.getUTCMonth() + 1,
    day: date.getUTCDate(),
    hour: date.getUTCHours(),
    minute: date.getUTCMinutes()
  };
}

function solarFromDate(date) {
  const p = partsFromDate(date);
  return Solar.fromYmdHms(p.year, p.month, p.day, p.hour, p.minute, 0);
}

function dateFromSolar(solar) {
  return makeDate(solar.getYear(), solar.getMonth(), solar.getDay(), solar.getHour(), solar.getMinute());
}

function hiddenText(hideGan, shiShen) {
  return hideGan.map((gan, index) => `${gan}${shiShen[index] || ""}`).join("、");
}

function buildStrictProfile(payload) {
  const time = parseTimeInput(payload.birthTime || "08:00");
  let solar;
  let calendarNote;

  if (payload.calendarType === "lunar") {
    const year = Number(payload.lunarYear);
    const month = Number(payload.lunarMonth);
    const day = Number(payload.lunarDay);
    if (!Number.isInteger(year) || year < 1900 || year > 2100) throw new Error("农历年份支持 1900-2100。");
    if (!Number.isInteger(month) || month < 1 || month > 12) throw new Error("农历月份不正确。");
    if (!Number.isInteger(day) || day < 1 || day > 30) throw new Error("农历日期不正确。");
    const lunar = Lunar.fromYmdHms(year, payload.lunarLeap ? -month : month, day, time.hour, time.minute, 0);
    solar = lunar.getSolar();
    calendarNote = `输入为农历 ${lunar.toString()} ${String(time.hour).padStart(2, "0")}:${String(time.minute).padStart(2, "0")}，已按历法库换算为公历 ${solar.toYmd()}。`;
  } else {
    const date = parseDateInput(payload.solarDate);
    solar = Solar.fromYmdHms(date.year, date.month, date.day, time.hour, time.minute, 0);
    calendarNote = `输入为公历 ${solar.toYmdHms()}，农历为 ${solar.getLunar().toString()}。`;
  }

  const birthDate = dateFromSolar(solar);
  let adjustedBirth = birthDate;
  let trueSolar = null;
  if (payload.useTrueSolar) {
    trueSolar = trueSolarReport(birthDate, payload.province, payload.city, payload.district);
    adjustedBirth = trueSolar.correctedDate;
  }

  const adjustedSolar = solarFromDate(adjustedBirth);
  const lunar = adjustedSolar.getLunar();
  const eight = lunar.getEightChar();
  eight.setSect(2);

  const pillars = {
    "年柱": eight.getYear(),
    "月柱": eight.getMonth(),
    "日柱": eight.getDay(),
    "时柱": eight.getTime()
  };

  const tenGods = {
    "年柱": eight.getYearShiShenGan(),
    "月柱": eight.getMonthShiShenGan(),
    "日柱": "日主",
    "时柱": eight.getTimeShiShenGan()
  };

  const hiddenStems = {
    "年柱": hiddenText(eight.getYearHideGan(), eight.getYearShiShenZhi()),
    "月柱": hiddenText(eight.getMonthHideGan(), eight.getMonthShiShenZhi()),
    "日柱": hiddenText(eight.getDayHideGan(), eight.getDayShiShenZhi()),
    "时柱": hiddenText(eight.getTimeHideGan(), eight.getTimeShiShenZhi())
  };

  let luckDirection = "未计算";
  let bigLucks = [];
  try {
    const yun = eight.getYun(payload.gender === "male");
    luckDirection = yun.isForward() ? "顺行" : "逆行";
    bigLucks = yun.getDaYun(9)
      .filter((luck) => luck.getGanZhi())
      .slice(0, 8)
      .map((luck) => ({
        age: `${luck.getStartAge()}-${luck.getEndAge()}岁`,
        years: `${luck.getStartYear()}-${luck.getEndYear()}`,
        ganzhi: luck.getGanZhi()
      }));
  } catch (error) {
    luckDirection = "起运未计算";
  }

  const dayMaster = pillars["日柱"][0];
  return {
    birthDate,
    adjustedBirth,
    trueSolar,
    calendarNote,
    pillars,
    tenGods,
    hiddenStems,
    dayMaster,
    dayElement: GAN_ELEMENTS[dayMaster],
    luckDirection,
    bigLucks,
    engine: "lunar-javascript EightChar 子平法（节气定年月柱，Sect 2）",
    methodNote: "严格用子平四柱：公历/农历先换算为太阳历时间，再按节气取年柱和月柱，按日干定十神。",
    privacy: "输入会在 Worker 内排盘；若启用 DeepSeek，会把问题和结构化盘面发给模型生成解释。"
  };
}

function deepseekPrompt(baseReading) {
  return [
    {
      role: "system",
      content: [
        "你是一个面向 20-35 岁年轻人的八字奇门问事解释器。",
        "你不能改四柱、十神、九宫盘、分数、真太阳时、分类。",
        "你的任务是把已经算好的结构化结果讲得轻松、清楚、像朋友在旁边拆局。",
        "口吻：年轻、短句、别端着，可以说“别上头”“先试一手”“这波先稳住”，但不要油腻、不要玄乎吓人。",
        "边界：不做绝对预言，不给医疗、法律、投资结论。涉及高风险时要提醒找专业人士。",
        "只输出 JSON，不要 Markdown，不要额外解释。JSON 字段：summary(string), sections(array of {title, body}), actions(array string)。"
      ].join("\n")
    },
    {
      role: "user",
      content: JSON.stringify({
        question: baseReading.meta.question,
        category: baseReading.meta.category,
        bazi: baseReading.bazi,
        qimen: {
          outcomeScore: baseReading.qimen.outcomeScore,
          verdict: baseReading.qimen.verdict,
          focusPalace: baseReading.qimen.focusPalace,
          dutyGate: baseReading.qimen.dutyGate,
          dutyStar: baseReading.qimen.dutyStar
        },
        draft: {
          summary: baseReading.summary,
          sections: baseReading.sections,
          actions: baseReading.actions
        }
      })
    }
  ];
}

function safeParseJson(text) {
  try {
    return JSON.parse(text);
  } catch (error) {
    const match = String(text || "").match(/\{[\s\S]*\}/);
    if (!match) throw error;
    return JSON.parse(match[0]);
  }
}

async function enhanceWithDeepSeek(reading, env) {
  if (!env.DEEPSEEK_API_KEY) return reading;
  const model = env.DEEPSEEK_MODEL || "deepseek-v4-flash";
  const baseUrl = (env.DEEPSEEK_BASE_URL || "https://api.deepseek.com").replace(/\/$/, "");
  const response = await fetch(`${baseUrl}/chat/completions`, {
    method: "POST",
    headers: {
      "authorization": `Bearer ${env.DEEPSEEK_API_KEY}`,
      "content-type": "application/json"
    },
    body: JSON.stringify({
      model,
      messages: deepseekPrompt(reading),
      response_format: { type: "json_object" },
      thinking: { type: env.DEEPSEEK_THINKING || "disabled" },
      temperature: Number(env.DEEPSEEK_TEMPERATURE || 0.7),
      max_tokens: Number(env.DEEPSEEK_MAX_TOKENS || 1200),
      stream: false
    })
  });
  if (!response.ok) {
    reading.meta.llm = { provider: "DeepSeek", model, used: false, error: `HTTP ${response.status}` };
    return reading;
  }
  const data = await response.json();
  const content = data.choices?.[0]?.message?.content;
  if (!content) {
    reading.meta.llm = { provider: "DeepSeek", model, used: false, error: "empty response" };
    return reading;
  }
  const enhanced = safeParseJson(content);
  if (typeof enhanced.summary === "string" && enhanced.summary.length > 4) reading.summary = enhanced.summary;
  if (Array.isArray(enhanced.sections) && enhanced.sections.length) {
    reading.sections = enhanced.sections
      .filter((item) => item && typeof item.title === "string" && typeof item.body === "string")
      .slice(0, 5);
  }
  if (Array.isArray(enhanced.actions) && enhanced.actions.length) {
    reading.actions = enhanced.actions.filter((item) => typeof item === "string").slice(0, 5);
  }
  reading.meta.llm = { provider: "DeepSeek", model, used: true };
  return reading;
}

async function handleReading(request, env) {
  const payload = await request.json();
  const profile = buildStrictProfile(payload);
  let reading = composeReadingFromProfile(payload, profile, { now: new Date() });
  try {
    reading = await enhanceWithDeepSeek(reading, env);
  } catch (error) {
    reading.meta.llm = {
      provider: "DeepSeek",
      model: env.DEEPSEEK_MODEL || "deepseek-v4-flash",
      used: false,
      error: "LLM explanation failed; deterministic reading returned"
    };
  }
  return json({ ok: true, result: reading });
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname === "/api/health") {
      return json({ ok: true, engine: "worker", time: formatDateTime(new Date()) });
    }
    if (url.pathname === "/api/reading") {
      if (request.method !== "POST") return json({ ok: false, error: "Method not allowed" }, { status: 405 });
      try {
        return await handleReading(request, env);
      } catch (error) {
        return json({ ok: false, error: error.message || "Reading failed" }, { status: 400 });
      }
    }
    return env.ASSETS.fetch(request);
  }
};
