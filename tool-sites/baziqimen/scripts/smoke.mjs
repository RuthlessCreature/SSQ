import worker from "../src/worker.js";

const payload = {
  gender: "female",
  calendarType: "solar",
  solarDate: "1992-06-15",
  birthTime: "08:30",
  useTrueSolar: true,
  province: "广东",
  city: "深圳市",
  district: "南山区",
  question: "我今年要不要换工作，新的 offer 值不值得冲"
};

const response = await worker.fetch(new Request("https://kaijuyixia.com/api/reading", {
  method: "POST",
  headers: { "content-type": "application/json" },
  body: JSON.stringify(payload)
}), {});

const data = await response.json();
if (!data.ok) {
  throw new Error(data.error || "smoke failed");
}
const pillars = Object.values(data.result.bazi.pillars);
if (pillars.length !== 4 || pillars.some((pillar) => !/^[甲乙丙丁戊己庚辛壬癸][子丑寅卯辰巳午未申酉戌亥]$/.test(pillar))) {
  throw new Error(`invalid pillars: ${pillars.join("/")}`);
}
if (!data.result.qimen.plate || data.result.qimen.plate.length !== 9) {
  throw new Error("invalid qimen plate");
}
console.log("ok", pillars.join(" "), data.result.summary);
