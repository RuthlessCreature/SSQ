import {
  LOCATION_DATA,
  buildTrueSolarOnly,
  convertSolarLunar
} from "./reading-core.js";

const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function setOptions(select, items, getLabel = (item) => item.name) {
  select.innerHTML = "";
  items.forEach((item) => {
    const option = document.createElement("option");
    option.value = item.name;
    option.textContent = getLabel(item);
    select.appendChild(option);
  });
}

function initLocationGroup(group) {
  const provinceSelect = $('[name="province"]', group);
  const citySelect = $('[name="city"]', group);
  const districtSelect = $('[name="district"]', group);
  if (!provinceSelect || !citySelect || !districtSelect) return;

  const refreshCities = () => {
    const province = LOCATION_DATA.find((item) => item.name === provinceSelect.value) || LOCATION_DATA[0];
    setOptions(citySelect, province.cities);
    refreshDistricts();
  };

  const refreshDistricts = () => {
    const province = LOCATION_DATA.find((item) => item.name === provinceSelect.value) || LOCATION_DATA[0];
    const city = province.cities.find((item) => item.name === citySelect.value) || province.cities[0];
    setOptions(districtSelect, city.districts, (item) => `${item.name}（${item.longitude.toFixed(2)}E）`);
  };

  setOptions(provinceSelect, LOCATION_DATA);
  provinceSelect.value = group.dataset.defaultProvince || "广东";
  refreshCities();
  citySelect.value = group.dataset.defaultCity || citySelect.value;
  refreshDistricts();
  districtSelect.value = group.dataset.defaultDistrict || districtSelect.value;

  provinceSelect.addEventListener("change", refreshCities);
  citySelect.addEventListener("change", refreshDistricts);
}

function initCalendarForm(form) {
  const solarFields = $$("[data-solar-fields]", form);
  const lunarFields = $$("[data-lunar-fields]", form);
  const radios = $$('[name="calendarType"]', form);
  if (!radios.length) return;

  const refresh = () => {
    const mode = $('[name="calendarType"]:checked', form)?.value || "solar";
    solarFields.forEach((node) => node.hidden = mode !== "solar");
    lunarFields.forEach((node) => node.hidden = mode !== "lunar");
  };

  radios.forEach((radio) => radio.addEventListener("change", refresh));
  refresh();
}

function initTrueSolarToggle(form) {
  const toggle = $('[name="useTrueSolar"]', form);
  const locationBlock = $("[data-true-solar-location]", form);
  if (!toggle || !locationBlock) return;
  const refresh = () => {
    locationBlock.hidden = !toggle.checked;
    $$("select", locationBlock).forEach((select) => {
      select.disabled = !toggle.checked;
    });
  };
  toggle.addEventListener("change", refresh);
  refresh();
}

function payloadFromReadingForm(form) {
  const data = new FormData(form);
  return {
    gender: data.get("gender"),
    calendarType: data.get("calendarType"),
    solarDate: data.get("solarDate"),
    lunarYear: Number(data.get("lunarYear")),
    lunarMonth: Number(data.get("lunarMonth")),
    lunarDay: Number(data.get("lunarDay")),
    lunarLeap: data.get("lunarLeap") === "on",
    birthTime: data.get("birthTime"),
    useTrueSolar: data.get("useTrueSolar") === "on",
    province: data.get("province"),
    city: data.get("city"),
    district: data.get("district"),
    question: data.get("question")
  };
}

async function requestReading(payload) {
  const response = await fetch("/api/reading", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(payload)
  });
  if (!response.ok) throw new Error("排盘服务暂时没连上，请用 Worker 预览或稍后重试。");
  const data = await response.json();
  if (!data.ok) throw new Error(data.error || "排盘失败，请检查输入。");
  return data.result;
}

function renderMetrics(container, rows) {
  if (!container) return;
  container.innerHTML = "";
  rows.forEach(([label, value]) => {
    const row = el("div", "metric");
    row.append(el("span", "", label), el("strong", "", value));
    container.append(row);
  });
}

function renderPillars(container, bazi) {
  if (!container) return;
  container.innerHTML = "";
  Object.entries(bazi.pillars).forEach(([name, pillar]) => {
    const card = el("div", "pillar-card");
    card.append(el("span", "muted", name), el("strong", "", pillar), el("small", "", bazi.tenGods[name] || ""));
    container.append(card);
  });
}

function renderElements(container, scores) {
  if (!container) return;
  container.innerHTML = "";
  const max = Math.max(...Object.values(scores), 1);
  Object.entries(scores).forEach(([elementName, score]) => {
    const row = el("div", "element-row");
    row.append(el("span", "", elementName));
    const bar = el("div", "bar");
    const fill = el("i");
    fill.style.width = `${Math.max(8, Math.round((score / max) * 100))}%`;
    bar.append(fill);
    row.append(bar, el("strong", "", score.toFixed(2)));
    container.append(row);
  });
}

function renderPlate(container, plate, focusKey) {
  if (!container) return;
  container.innerHTML = "";
  plate.forEach((palace) => {
    const cell = el("div", `palace ${palace.key === focusKey ? "is-focus" : ""}`);
    cell.append(
      el("span", "palace-name", `${palace.short} · ${palace.element}`),
      el("strong", "", palace.gate),
      el("span", "", `${palace.star} / ${palace.deity}`),
      el("small", "", `${palace.stem} · ${palace.direction} · ${palace.score}`)
    );
    container.append(cell);
  });
}

function renderSections(container, sections) {
  if (!container) return;
  container.innerHTML = "";
  sections.forEach((section) => {
    const block = el("article", "reading-section");
    block.append(el("h3", "", section.title), el("p", "", section.body));
    container.append(block);
  });
}

function renderList(container, items) {
  if (!container) return;
  container.innerHTML = "";
  items.forEach((item) => {
    const li = el("li", "", item);
    container.append(li);
  });
}

function renderReading(result) {
  window.__lastBaziQimenReading = result;
  const root = $("[data-reading-output]");
  if (!root) return;
  root.hidden = false;
  $("[data-verdict]", root).textContent = result.summary;
  $("[data-category]", root).textContent = result.meta.category;
  $("[data-score]", root).textContent = `${result.qimen.outcomeScore}/100`;
  $("[data-focus]", root).textContent = `${result.qimen.focusPalace.name} · ${result.qimen.focusPalace.gate}`;
  const generated = $("[data-generated]", root);
  if (generated) generated.textContent = result.meta.generatedAt;

  renderMetrics($("[data-reading-metrics]", root), [
    ["出生时间", result.meta.birthTime],
    ["排盘时间", result.meta.adjustedBirthTime],
    ["日主", `${result.bazi.dayMaster}${result.bazi.dayElement}`],
    ["命局身势", result.bazi.strength],
    ["喜用方向", result.bazi.usefulElements.join("、")],
    ["大运方向", result.bazi.luckDirection]
  ]);

  const solarNote = $("[data-solar-note]", root);
  if (result.meta.trueSolar) {
    solarNote.textContent = `真太阳时：${result.meta.trueSolar.province}${result.meta.trueSolar.city}${result.meta.trueSolar.district}，经度 ${result.meta.trueSolar.longitude.toFixed(2)}E，总校正 ${result.meta.trueSolar.totalCorrection} 分钟。`;
  } else {
    solarNote.textContent = "真太阳时：未启用，经纬度校正未参与时柱。";
  }
  $("[data-calendar-note]", root).textContent = result.meta.calendarNote;
  const engineNote = $("[data-engine-note]", root);
  if (engineNote) {
    engineNote.textContent = result.meta.llm
      ? `排盘：${result.meta.engine}；解释：${result.meta.llm.model}`
      : `排盘：${result.meta.engine}；解释：规则引擎`;
  }

  renderPillars($("[data-pillars]"), result.bazi);
  renderElements($("[data-elements]"), result.bazi.elementScores);
  renderPlate($("[data-plate]"), result.qimen.plate, result.qimen.focusPalace.key);
  renderSections($("[data-sections]"), result.sections);
  renderList($("[data-actions]"), result.actions);
  renderList($("[data-cautions]"), result.cautions);
}

function formatReadingText(result) {
  return [
    `结论：${result.summary}`,
    `问题：${result.meta.question}`,
    `分类：${result.meta.category}`,
    `四柱：${Object.values(result.bazi.pillars).join(" / ")}`,
    `焦点：${result.qimen.focusPalace.name} ${result.qimen.focusPalace.gate} ${result.qimen.focusPalace.star} ${result.qimen.focusPalace.deity}`,
    "",
    ...result.sections.map((section) => `${section.title}：${section.body}`),
    "",
    `行动：${result.actions.join("；")}`,
    `提示：${result.cautions[0]}`
  ].join("\n");
}

async function copyReading(button) {
  const result = window.__lastBaziQimenReading;
  if (!result) return;
  await navigator.clipboard.writeText(formatReadingText(result));
  const old = button.textContent;
  button.textContent = "已复制";
  window.setTimeout(() => { button.textContent = old; }, 1400);
}

function downloadReadingCard() {
  const result = window.__lastBaziQimenReading;
  if (!result) return;
  const canvas = document.createElement("canvas");
  canvas.width = 1200;
  canvas.height = 680;
  const ctx = canvas.getContext("2d");
  ctx.fillStyle = "#f7f7f2";
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = "#16695d";
  ctx.fillRect(0, 0, canvas.width, 18);
  ctx.fillStyle = "#17211f";
  ctx.font = "700 42px Arial";
  ctx.fillText("八字奇门问事", 70, 88);
  ctx.font = "700 56px Arial";
  wrapCanvasText(ctx, result.summary, 70, 170, 1060, 64);
  ctx.font = "28px Arial";
  ctx.fillStyle = "#50615d";
  ctx.fillText(`四柱：${Object.values(result.bazi.pillars).join(" / ")}`, 70, 290);
  ctx.fillText(`焦点：${result.qimen.focusPalace.name} ${result.qimen.focusPalace.gate} ${result.qimen.focusPalace.star}`, 70, 338);
  ctx.fillText(`分类：${result.meta.category}    分数：${result.qimen.outcomeScore}/100`, 70, 386);
  ctx.fillStyle = "#17211f";
  ctx.font = "24px Arial";
  wrapCanvasText(ctx, result.sections[0].body, 70, 460, 1030, 36);
  ctx.fillStyle = "#7b4a24";
  ctx.font = "20px Arial";
  ctx.fillText("仅作传统文化娱乐与自我复盘参考，不构成专业建议。", 70, 630);
  const link = document.createElement("a");
  link.download = "bazi-qimen-reading.png";
  link.href = canvas.toDataURL("image/png");
  link.click();
}

function wrapCanvasText(ctx, text, x, y, maxWidth, lineHeight) {
  const chars = String(text).split("");
  let line = "";
  chars.forEach((char) => {
    const test = line + char;
    if (ctx.measureText(test).width > maxWidth) {
      ctx.fillText(line, x, y);
      line = char;
      y += lineHeight;
    } else {
      line = test;
    }
  });
  if (line) ctx.fillText(line, x, y);
}

function initReadingForm(form) {
  initCalendarForm(form);
  initTrueSolarToggle(form);
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const submit = $("button[type='submit']", form);
    const submitLabel = submit.textContent;
    const error = $("[data-form-error]", form);
    if (error) error.textContent = "";
    submit.disabled = true;
    submit.textContent = "开局中";
    try {
      const result = await requestReading(payloadFromReadingForm(form));
      renderReading(result);
    } catch (err) {
      if (error) error.textContent = err.message || "排盘失败，请检查输入。";
    } finally {
      submit.disabled = false;
      submit.textContent = submitLabel;
    }
  });
  form.dispatchEvent(new Event("submit", { cancelable: true }));
}

function initSolarTool(form) {
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const output = $("[data-solar-output]");
    try {
      const data = new FormData(form);
      const result = buildTrueSolarOnly({
        solarDate: data.get("solarDate"),
        birthTime: data.get("birthTime"),
        province: data.get("province"),
        city: data.get("city"),
        district: data.get("district")
      });
      output.hidden = false;
      output.innerHTML = "";
      renderMetrics(output, [
        ["原始北京时间", result.original],
        ["校正后真太阳时", result.corrected],
        ["出生地经度", `${result.longitude.toFixed(2)}E`],
        ["经度校正", `${result.longitudeCorrection} 分钟`],
        ["均时差", `${result.equationOfTime} 分钟`],
        ["总校正", `${result.totalCorrection} 分钟`]
      ]);
    } catch (err) {
      output.hidden = false;
      output.textContent = err.message || "计算失败。";
    }
  });
  form.dispatchEvent(new Event("submit", { cancelable: true }));
}

function initConverter(form) {
  const mode = $('[name="mode"]', form);
  const solarFields = $$("[data-convert-solar]", form);
  const lunarFields = $$("[data-convert-lunar]", form);
  const refresh = () => {
    const lunarMode = mode.value === "lunar-to-solar";
    solarFields.forEach((node) => node.hidden = lunarMode);
    lunarFields.forEach((node) => node.hidden = !lunarMode);
  };
  mode.addEventListener("change", refresh);
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const output = $("[data-converter-output]");
    try {
      const data = new FormData(form);
      const result = convertSolarLunar({
        mode: data.get("mode"),
        solarDate: data.get("solarDate"),
        lunarYear: Number(data.get("lunarYear")),
        lunarMonth: Number(data.get("lunarMonth")),
        lunarDay: Number(data.get("lunarDay")),
        lunarLeap: data.get("lunarLeap") === "on"
      });
      output.hidden = false;
      renderMetrics(output, [["公历", result.solar], ["农历", result.lunar]]);
    } catch (err) {
      output.hidden = false;
      output.textContent = err.message || "换算失败。";
    }
  });
  refresh();
  form.dispatchEvent(new Event("submit", { cancelable: true }));
}

document.addEventListener("DOMContentLoaded", () => {
  $$("[data-location-group]").forEach(initLocationGroup);
  const readingForm = $("[data-reading-form]");
  if (readingForm) initReadingForm(readingForm);
  const solarTool = $("[data-solar-tool]");
  if (solarTool) initSolarTool(solarTool);
  const converter = $("[data-converter-tool]");
  if (converter) initConverter(converter);
  $$("[data-copy-reading]").forEach((button) => button.addEventListener("click", () => copyReading(button)));
  $$("[data-download-reading]").forEach((button) => button.addEventListener("click", downloadReadingCard));
});
