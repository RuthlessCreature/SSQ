const GAN = "甲乙丙丁戊己庚辛壬癸".split("");
const ZHI = "子丑寅卯辰巳午未申酉戌亥".split("");

const GAN_ELEMENTS = {
  "甲": "木", "乙": "木", "丙": "火", "丁": "火", "戊": "土",
  "己": "土", "庚": "金", "辛": "金", "壬": "水", "癸": "水"
};

const GAN_POLARITY = {
  "甲": "阳", "乙": "阴", "丙": "阳", "丁": "阴", "戊": "阳",
  "己": "阴", "庚": "阳", "辛": "阴", "壬": "阳", "癸": "阴"
};

const HIDDEN_STEMS = {
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
  "亥": ["壬", "甲"]
};

const ELEMENT_GENERATES = { "木": "火", "火": "土", "土": "金", "金": "水", "水": "木" };
const ELEMENT_CONTROLS = { "木": "土", "土": "水", "水": "火", "火": "金", "金": "木" };

const LUNAR_INFO = [
  0x04bd8, 0x04ae0, 0x0a570, 0x054d5, 0x0d260, 0x0d950, 0x16554, 0x056a0, 0x09ad0, 0x055d2,
  0x04ae0, 0x0a5b6, 0x0a4d0, 0x0d250, 0x1d255, 0x0b540, 0x0d6a0, 0x0ada2, 0x095b0, 0x14977,
  0x04970, 0x0a4b0, 0x0b4b5, 0x06a50, 0x06d40, 0x1ab54, 0x02b60, 0x09570, 0x052f2, 0x04970,
  0x06566, 0x0d4a0, 0x0ea50, 0x06e95, 0x05ad0, 0x02b60, 0x186e3, 0x092e0, 0x1c8d7, 0x0c950,
  0x0d4a0, 0x1d8a6, 0x0b550, 0x056a0, 0x1a5b4, 0x025d0, 0x092d0, 0x0d2b2, 0x0a950, 0x0b557,
  0x06ca0, 0x0b550, 0x15355, 0x04da0, 0x0a5d0, 0x14573, 0x052d0, 0x0a9a8, 0x0e950, 0x06aa0,
  0x0aea6, 0x0ab50, 0x04b60, 0x0aae4, 0x0a570, 0x05260, 0x0f263, 0x0d950, 0x05b57, 0x056a0,
  0x096d0, 0x04dd5, 0x04ad0, 0x0a4d0, 0x0d4d4, 0x0d250, 0x0d558, 0x0b540, 0x0b6a0, 0x195a6,
  0x095b0, 0x049b0, 0x0a974, 0x0a4b0, 0x0b27a, 0x06a50, 0x06d40, 0x0af46, 0x0ab60, 0x09570,
  0x04af5, 0x04970, 0x064b0, 0x074a3, 0x0ea50, 0x06b58, 0x055c0, 0x0ab60, 0x096d5, 0x092e0,
  0x0c960, 0x0d954, 0x0d4a0, 0x0da50, 0x07552, 0x056a0, 0x0abb7, 0x025d0, 0x092d0, 0x0cab5,
  0x0a950, 0x0b4a0, 0x0baa4, 0x0ad50, 0x055d9, 0x04ba0, 0x0a5b0, 0x15176, 0x052b0, 0x0a930,
  0x07954, 0x06aa0, 0x0ad50, 0x05b52, 0x04b60, 0x0a6e6, 0x0a4e0, 0x0d260, 0x0ea65, 0x0d530,
  0x05aa0, 0x076a3, 0x096d0, 0x04bd7, 0x04ad0, 0x0a4d0, 0x1d0b6, 0x0d250, 0x0d520, 0x0dd45,
  0x0b5a0, 0x056d0, 0x055b2, 0x049b0, 0x0a577, 0x0a4b0, 0x0aa50, 0x1b255, 0x06d20, 0x0ada0,
  0x14b63, 0x09370, 0x049f8, 0x04970, 0x064b0, 0x168a6, 0x0ea50, 0x06b20, 0x1a6c4, 0x0aae0,
  0x0a2e0, 0x0d2e3, 0x0c960, 0x0d557, 0x0d4a0, 0x0da50, 0x05d55, 0x056a0, 0x0a6d0, 0x055d4,
  0x052d0, 0x0a9b8, 0x0a950, 0x0b4a0, 0x0b6a6, 0x0ad50, 0x055a0, 0x0aba4, 0x0a5b0, 0x052b0,
  0x0b273, 0x06930, 0x07337, 0x06aa0, 0x0ad50, 0x14b55, 0x04b60, 0x0a570, 0x054e4, 0x0d160,
  0x0e968, 0x0d520, 0x0daa0, 0x16aa6, 0x056d0, 0x04ae0, 0x0a9d4, 0x0a2d0, 0x0d150, 0x0f252,
  0x0d520
];

const DAY_MS = 24 * 60 * 60 * 1000;

export const LOCATION_DATA = [
  { name: "北京", cities: [{ name: "北京市", districts: [
    { name: "东城区", longitude: 116.42 }, { name: "朝阳区", longitude: 116.49 }, { name: "海淀区", longitude: 116.30 }
  ] }] },
  { name: "上海", cities: [{ name: "上海市", districts: [
    { name: "黄浦区", longitude: 121.49 }, { name: "浦东新区", longitude: 121.55 }, { name: "徐汇区", longitude: 121.44 }
  ] }] },
  { name: "天津", cities: [{ name: "天津市", districts: [
    { name: "和平区", longitude: 117.20 }, { name: "河西区", longitude: 117.22 }, { name: "滨海新区", longitude: 117.70 }
  ] }] },
  { name: "重庆", cities: [{ name: "重庆市", districts: [
    { name: "渝中区", longitude: 106.57 }, { name: "江北区", longitude: 106.57 }, { name: "沙坪坝区", longitude: 106.46 }
  ] }] },
  { name: "广东", cities: [
    { name: "广州市", districts: [{ name: "越秀区", longitude: 113.27 }, { name: "天河区", longitude: 113.36 }, { name: "番禺区", longitude: 113.38 }] },
    { name: "深圳市", districts: [{ name: "福田区", longitude: 114.05 }, { name: "南山区", longitude: 113.93 }, { name: "龙岗区", longitude: 114.25 }] },
    { name: "佛山市", districts: [{ name: "禅城区", longitude: 113.12 }, { name: "南海区", longitude: 113.14 }, { name: "顺德区", longitude: 113.30 }] },
    { name: "东莞市", districts: [{ name: "莞城区", longitude: 113.75 }, { name: "松山湖", longitude: 113.88 }] }
  ] },
  { name: "浙江", cities: [
    { name: "杭州市", districts: [{ name: "上城区", longitude: 120.17 }, { name: "西湖区", longitude: 120.13 }, { name: "萧山区", longitude: 120.27 }] },
    { name: "宁波市", districts: [{ name: "海曙区", longitude: 121.55 }, { name: "鄞州区", longitude: 121.55 }, { name: "北仑区", longitude: 121.84 }] },
    { name: "温州市", districts: [{ name: "鹿城区", longitude: 120.65 }, { name: "瓯海区", longitude: 120.61 }] }
  ] },
  { name: "江苏", cities: [
    { name: "南京市", districts: [{ name: "玄武区", longitude: 118.80 }, { name: "秦淮区", longitude: 118.79 }, { name: "江宁区", longitude: 118.84 }] },
    { name: "苏州市", districts: [{ name: "姑苏区", longitude: 120.62 }, { name: "工业园区", longitude: 120.72 }, { name: "吴中区", longitude: 120.63 }] },
    { name: "无锡市", districts: [{ name: "梁溪区", longitude: 120.30 }, { name: "滨湖区", longitude: 120.27 }] }
  ] },
  { name: "四川", cities: [
    { name: "成都市", districts: [{ name: "锦江区", longitude: 104.08 }, { name: "武侯区", longitude: 104.04 }, { name: "高新区", longitude: 104.06 }] },
    { name: "绵阳市", districts: [{ name: "涪城区", longitude: 104.74 }, { name: "游仙区", longitude: 104.77 }] }
  ] },
  { name: "湖北", cities: [{ name: "武汉市", districts: [{ name: "江岸区", longitude: 114.31 }, { name: "武昌区", longitude: 114.32 }, { name: "洪山区", longitude: 114.34 }] }] },
  { name: "湖南", cities: [{ name: "长沙市", districts: [{ name: "芙蓉区", longitude: 113.03 }, { name: "岳麓区", longitude: 112.93 }, { name: "雨花区", longitude: 113.04 }] }] },
  { name: "河南", cities: [
    { name: "郑州市", districts: [{ name: "金水区", longitude: 113.66 }, { name: "中原区", longitude: 113.61 }] },
    { name: "洛阳市", districts: [{ name: "洛龙区", longitude: 112.46 }, { name: "涧西区", longitude: 112.40 }] }
  ] },
  { name: "山东", cities: [
    { name: "济南市", districts: [{ name: "历下区", longitude: 117.08 }, { name: "市中区", longitude: 116.99 }] },
    { name: "青岛市", districts: [{ name: "市南区", longitude: 120.39 }, { name: "崂山区", longitude: 120.47 }] }
  ] },
  { name: "福建", cities: [
    { name: "福州市", districts: [{ name: "鼓楼区", longitude: 119.30 }, { name: "仓山区", longitude: 119.32 }] },
    { name: "厦门市", districts: [{ name: "思明区", longitude: 118.08 }, { name: "湖里区", longitude: 118.15 }] }
  ] },
  { name: "陕西", cities: [{ name: "西安市", districts: [{ name: "碑林区", longitude: 108.94 }, { name: "雁塔区", longitude: 108.95 }, { name: "未央区", longitude: 108.95 }] }] },
  { name: "辽宁", cities: [
    { name: "沈阳市", districts: [{ name: "和平区", longitude: 123.40 }, { name: "沈河区", longitude: 123.45 }] },
    { name: "大连市", districts: [{ name: "中山区", longitude: 121.64 }, { name: "甘井子区", longitude: 121.52 }] }
  ] },
  { name: "河北", cities: [{ name: "石家庄市", districts: [{ name: "长安区", longitude: 114.54 }, { name: "桥西区", longitude: 114.46 }] }] },
  { name: "安徽", cities: [{ name: "合肥市", districts: [{ name: "庐阳区", longitude: 117.26 }, { name: "蜀山区", longitude: 117.26 }] }] },
  { name: "江西", cities: [{ name: "南昌市", districts: [{ name: "东湖区", longitude: 115.90 }, { name: "红谷滩区", longitude: 115.86 }] }] },
  { name: "广西", cities: [{ name: "南宁市", districts: [{ name: "青秀区", longitude: 108.50 }, { name: "西乡塘区", longitude: 108.31 }] }] },
  { name: "云南", cities: [{ name: "昆明市", districts: [{ name: "五华区", longitude: 102.70 }, { name: "官渡区", longitude: 102.75 }] }] },
  { name: "贵州", cities: [{ name: "贵阳市", districts: [{ name: "南明区", longitude: 106.71 }, { name: "观山湖区", longitude: 106.62 }] }] },
  { name: "山西", cities: [{ name: "太原市", districts: [{ name: "迎泽区", longitude: 112.56 }, { name: "小店区", longitude: 112.57 }] }] },
  { name: "吉林", cities: [{ name: "长春市", districts: [{ name: "朝阳区", longitude: 125.29 }, { name: "南关区", longitude: 125.35 }] }] },
  { name: "黑龙江", cities: [{ name: "哈尔滨市", districts: [{ name: "道里区", longitude: 126.62 }, { name: "南岗区", longitude: 126.67 }] }] },
  { name: "内蒙古", cities: [{ name: "呼和浩特市", districts: [{ name: "新城区", longitude: 111.67 }, { name: "赛罕区", longitude: 111.70 }] }] },
  { name: "新疆", cities: [
    { name: "乌鲁木齐市", districts: [{ name: "天山区", longitude: 87.62 }, { name: "沙依巴克区", longitude: 87.60 }] },
    { name: "喀什市", districts: [{ name: "喀什市区", longitude: 75.99 }] }
  ] },
  { name: "西藏", cities: [{ name: "拉萨市", districts: [{ name: "城关区", longitude: 91.13 }, { name: "堆龙德庆区", longitude: 91.00 }] }] },
  { name: "青海", cities: [{ name: "西宁市", districts: [{ name: "城中区", longitude: 101.78 }, { name: "城西区", longitude: 101.75 }] }] },
  { name: "宁夏", cities: [{ name: "银川市", districts: [{ name: "兴庆区", longitude: 106.29 }, { name: "金凤区", longitude: 106.24 }] }] },
  { name: "甘肃", cities: [{ name: "兰州市", districts: [{ name: "城关区", longitude: 103.85 }, { name: "七里河区", longitude: 103.78 }] }] },
  { name: "海南", cities: [
    { name: "海口市", districts: [{ name: "龙华区", longitude: 110.33 }, { name: "美兰区", longitude: 110.36 }] },
    { name: "三亚市", districts: [{ name: "吉阳区", longitude: 109.58 }, { name: "天涯区", longitude: 109.45 }] }
  ] },
  { name: "香港", cities: [{ name: "香港", districts: [{ name: "中西区", longitude: 114.15 }, { name: "九龙城区", longitude: 114.19 }] }] },
  { name: "澳门", cities: [{ name: "澳门", districts: [{ name: "澳门半岛", longitude: 113.55 }, { name: "氹仔", longitude: 113.56 }] }] },
  { name: "台湾", cities: [
    { name: "台北市", districts: [{ name: "中正区", longitude: 121.52 }, { name: "信义区", longitude: 121.57 }] },
    { name: "高雄市", districts: [{ name: "苓雅区", longitude: 120.31 }, { name: "左营区", longitude: 120.29 }] }
  ] }
];

const PALACES = [
  { key: "kan", name: "坎一宫", short: "坎", element: "水", direction: "北" },
  { key: "kun", name: "坤二宫", short: "坤", element: "土", direction: "西南" },
  { key: "zhen", name: "震三宫", short: "震", element: "木", direction: "东" },
  { key: "xun", name: "巽四宫", short: "巽", element: "木", direction: "东南" },
  { key: "zhong", name: "中五宫", short: "中", element: "土", direction: "中" },
  { key: "qian", name: "乾六宫", short: "乾", element: "金", direction: "西北" },
  { key: "dui", name: "兑七宫", short: "兑", element: "金", direction: "西" },
  { key: "gen", name: "艮八宫", short: "艮", element: "土", direction: "东北" },
  { key: "li", name: "离九宫", short: "离", element: "火", direction: "南" }
];

const RENDER_ORDER = ["xun", "li", "kun", "zhen", "zhong", "dui", "gen", "kan", "qian"];
const GATES = ["休门", "生门", "伤门", "杜门", "景门", "死门", "惊门", "开门"];
const STARS = ["天蓬", "天任", "天冲", "天辅", "天英", "天芮", "天柱", "天心", "天禽"];
const DEITIES = ["值符", "腾蛇", "太阴", "六合", "白虎", "玄武", "九地", "九天"];

const GATE_TONE = {
  "开门": { score: 18, text: "利开局、沟通、成交，适合把事情摆到台面上处理。" },
  "生门": { score: 20, text: "主生发、资源、收益，适合争取支持与增量。" },
  "休门": { score: 10, text: "主缓和、修整、恢复，适合先稳住节奏。" },
  "景门": { score: 8, text: "主表达、曝光、文书，适合展示方案但忌只讲漂亮话。" },
  "杜门": { score: -6, text: "主闭塞、保守、卡点，适合审资料、堵漏洞。" },
  "伤门": { score: -9, text: "主冲突、损耗、硬碰硬，适合拆问题但不宜鲁莽推进。" },
  "惊门": { score: -8, text: "主消息波动、口舌惊扰，适合查证，不宜听风就是雨。" },
  "死门": { score: -14, text: "主停滞、收束、旧账，适合止损、归档、复盘。" }
};

const CATEGORY_RULES = [
  { key: "career", label: "事业项目", gates: ["开门", "景门"], keywords: ["工作", "事业", "项目", "老板", "客户", "面试", "跳槽", "升职", "创业", "offer"] },
  { key: "wealth", label: "财务合作", gates: ["生门", "开门"], keywords: ["钱", "财", "投资", "收入", "合作", "合同", "报价", "订单", "回款", "生意"] },
  { key: "relationship", label: "关系情感", gates: ["六合", "休门"], keywords: ["感情", "关系", "对象", "婚", "恋", "复合", "分手", "朋友", "家人", "沟通"] },
  { key: "study", label: "学习考试", gates: ["景门", "天辅"], keywords: ["学习", "考试", "证书", "论文", "申请", "学校", "课程", "语言"] },
  { key: "health", label: "身心状态", gates: ["休门", "生门"], keywords: ["健康", "病", "医院", "焦虑", "睡眠", "身体", "手术", "疼"] },
  { key: "travel", label: "出行迁移", gates: ["开门", "休门"], keywords: ["搬家", "出行", "旅行", "出国", "签证", "迁移", "城市"] }
];

function pad2(value) {
  return String(value).padStart(2, "0");
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
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

function addMinutes(date, minutes) {
  return new Date(date.getTime() + minutes * 60 * 1000);
}

function parseDateInput(value) {
  const match = String(value || "").match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (!match) {
    throw new Error("请输入有效的公历日期。");
  }
  return { year: Number(match[1]), month: Number(match[2]), day: Number(match[3]) };
}

function parseTimeInput(value) {
  const match = String(value || "").match(/^(\d{2}):(\d{2})$/);
  if (!match) {
    throw new Error("请输入有效的出生时间。");
  }
  return { hour: Number(match[1]), minute: Number(match[2]) };
}

export function formatDateTime(date) {
  const p = partsFromDate(date);
  return `${p.year}-${pad2(p.month)}-${pad2(p.day)} ${pad2(p.hour)}:${pad2(p.minute)}`;
}

export function formatDateOnly(date) {
  const p = partsFromDate(date);
  return `${p.year}-${pad2(p.month)}-${pad2(p.day)}`;
}

function lunarInfo(year) {
  if (year < 1900 || year > 2100) {
    throw new Error("农历换算支持 1900-2100 年。");
  }
  return LUNAR_INFO[year - 1900];
}

function leapMonth(year) {
  return lunarInfo(year) & 0xf;
}

function leapDays(year) {
  const leap = leapMonth(year);
  return leap ? ((lunarInfo(year) & 0x10000) ? 30 : 29) : 0;
}

function lunarMonthDays(year, month) {
  return (lunarInfo(year) & (0x10000 >> month)) ? 30 : 29;
}

function lunarYearDays(year) {
  let sum = 348;
  let info = lunarInfo(year);
  for (let mask = 0x8000; mask > 0x8; mask >>= 1) {
    if (info & mask) sum += 1;
  }
  return sum + leapDays(year);
}

export function lunarToSolarDate(year, month, day, isLeap = false) {
  year = Number(year);
  month = Number(month);
  day = Number(day);
  if (year < 1900 || year > 2100 || month < 1 || month > 12 || day < 1 || day > 30) {
    throw new Error("农历日期超出可换算范围。");
  }
  const leap = leapMonth(year);
  if (isLeap && leap !== month) {
    throw new Error(`${year} 年没有闰 ${month} 月。`);
  }
  const maxDay = isLeap ? leapDays(year) : lunarMonthDays(year, month);
  if (day > maxDay) {
    throw new Error(`该农历月份最多 ${maxDay} 天。`);
  }
  let offset = 0;
  for (let y = 1900; y < year; y += 1) offset += lunarYearDays(y);
  for (let m = 1; m < month; m += 1) {
    offset += lunarMonthDays(year, m);
    if (leap === m) offset += leapDays(year);
  }
  if (isLeap) offset += lunarMonthDays(year, month);
  offset += day - 1;
  return new Date(Date.UTC(1900, 0, 31) + offset * DAY_MS);
}

export function solarToLunarDate(date) {
  const p = partsFromDate(date);
  const solar = makeDate(p.year, p.month, p.day);
  let offset = Math.floor((solar.getTime() - Date.UTC(1900, 0, 31)) / DAY_MS);
  if (offset < 0) throw new Error("农历换算支持 1900-2100 年。");
  let year = 1900;
  let yearDays = lunarYearDays(year);
  while (year < 2100 && offset >= yearDays) {
    offset -= yearDays;
    year += 1;
    yearDays = lunarYearDays(year);
  }
  const leap = leapMonth(year);
  let isLeap = false;
  let month = 1;
  while (month <= 12) {
    let days = isLeap ? leapDays(year) : lunarMonthDays(year, month);
    if (offset < days) break;
    offset -= days;
    if (leap === month && !isLeap) {
      isLeap = true;
    } else {
      if (isLeap) isLeap = false;
      month += 1;
    }
  }
  return { year, month, day: offset + 1, isLeap };
}

export function formatLunar(lunar) {
  return `${lunar.year}年${lunar.isLeap ? "闰" : ""}${lunar.month}月${lunar.day}日`;
}

export function getLocationEntry(provinceName, cityName, districtName) {
  const province = LOCATION_DATA.find((item) => item.name === provinceName) || LOCATION_DATA[0];
  const city = province.cities.find((item) => item.name === cityName) || province.cities[0];
  const district = city.districts.find((item) => item.name === districtName) || city.districts[0];
  return { province, city, district };
}

export function equationOfTimeMinutes(date) {
  const start = Date.UTC(date.getUTCFullYear(), 0, 0);
  const day = Math.floor((date.getTime() - start) / DAY_MS);
  const b = (2 * Math.PI * (day - 81)) / 364;
  return 9.87 * Math.sin(2 * b) - 7.53 * Math.cos(b) - 1.5 * Math.sin(b);
}

export function trueSolarReport(date, provinceName, cityName, districtName) {
  const { province, city, district } = getLocationEntry(provinceName, cityName, districtName);
  const longitudeCorrection = (district.longitude - 120) * 4;
  const equation = equationOfTimeMinutes(date);
  const total = longitudeCorrection + equation;
  return {
    province: province.name,
    city: city.name,
    district: district.name,
    longitude: district.longitude,
    longitudeCorrection: Number(longitudeCorrection.toFixed(1)),
    equationOfTime: Number(equation.toFixed(1)),
    totalCorrection: Number(total.toFixed(1)),
    correctedDate: addMinutes(date, total)
  };
}

function ganzhiByIndex(index) {
  return `${GAN[((index % 10) + 10) % 10]}${ZHI[((index % 12) + 12) % 12]}`;
}

function fallbackYearForLichun(date) {
  const p = partsFromDate(date);
  return (p.month < 2 || (p.month === 2 && p.day < 4)) ? p.year - 1 : p.year;
}

function julianDay(year, month, day) {
  const shift = Math.floor((14 - month) / 12);
  const y = year + 4800 - shift;
  const m = month + 12 * shift - 3;
  return day + Math.floor((153 * m + 2) / 5) + 365 * y + Math.floor(y / 4) - Math.floor(y / 100) + Math.floor(y / 400) - 32045;
}

function fallbackDayPillar(date) {
  const p = partsFromDate(date);
  const baseJdn = julianDay(2000, 1, 1);
  const baseIndex = 16;
  return ganzhiByIndex((julianDay(p.year, p.month, p.day) - baseJdn + baseIndex) % 60);
}

function fallbackMonthPillar(date, yearGan) {
  const p = partsFromDate(date);
  const boundaries = [
    [[2, 4], "寅"], [[3, 6], "卯"], [[4, 5], "辰"], [[5, 6], "巳"],
    [[6, 6], "午"], [[7, 7], "未"], [[8, 8], "申"], [[9, 8], "酉"],
    [[10, 8], "戌"], [[11, 7], "亥"], [[12, 7], "子"]
  ];
  let monthBranch = "丑";
  boundaries.forEach(([[month, day], branch]) => {
    if (p.month > month || (p.month === month && p.day >= day)) monthBranch = branch;
  });
  const branchOffset = "寅卯辰巳午未申酉戌亥子丑".indexOf(monthBranch);
  const startStem = { "甲": 2, "己": 2, "乙": 4, "庚": 4, "丙": 6, "辛": 6, "丁": 8, "壬": 8, "戊": 0, "癸": 0 };
  return `${GAN[(startStem[yearGan] + branchOffset) % 10]}${monthBranch}`;
}

function fallbackHourPillar(date, dayGan) {
  const hour = date.getUTCHours();
  const branchIndex = Math.floor((hour + 1) / 2) % 12;
  const startStem = { "甲": 0, "己": 0, "乙": 2, "庚": 2, "丙": 4, "辛": 4, "丁": 6, "壬": 6, "戊": 8, "癸": 8 };
  return `${GAN[(startStem[dayGan] + branchIndex) % 10]}${ZHI[branchIndex]}`;
}

function buildPillars(date) {
  const year = fallbackYearForLichun(date);
  const yearPillar = ganzhiByIndex((year - 4) % 60);
  const monthPillar = fallbackMonthPillar(date, yearPillar[0]);
  const dayPillar = fallbackDayPillar(date);
  const hourPillar = fallbackHourPillar(date, dayPillar[0]);
  return { "年柱": yearPillar, "月柱": monthPillar, "日柱": dayPillar, "时柱": hourPillar };
}

function inverseLookup(mapping, value) {
  return Object.entries(mapping).find(([, mapped]) => mapped === value)?.[0] || value;
}

function relationTenGod(dayGan, otherGan) {
  const dayElement = GAN_ELEMENTS[dayGan];
  const otherElement = GAN_ELEMENTS[otherGan];
  const same = GAN_POLARITY[dayGan] === GAN_POLARITY[otherGan];
  if (otherElement === dayElement) return same ? "比肩" : "劫财";
  if (ELEMENT_GENERATES[dayElement] === otherElement) return same ? "食神" : "伤官";
  if (ELEMENT_CONTROLS[dayElement] === otherElement) return same ? "偏财" : "正财";
  if (ELEMENT_CONTROLS[otherElement] === dayElement) return same ? "七杀" : "正官";
  if (ELEMENT_GENERATES[otherElement] === dayElement) return same ? "偏印" : "正印";
  return "-";
}

function elementScores(pillars) {
  const scores = { "木": 0, "火": 0, "土": 0, "金": 0, "水": 0 };
  Object.entries(pillars).forEach(([name, pillar]) => {
    const gan = pillar[0];
    const zhi = pillar[1];
    scores[GAN_ELEMENTS[gan]] += 1;
    (HIDDEN_STEMS[zhi] || []).forEach((hidden, index) => {
      scores[GAN_ELEMENTS[hidden]] += index === 0 ? 0.9 : 0.35;
    });
    const hidden = HIDDEN_STEMS[zhi] || [];
    if (name === "月柱" && hidden.length) scores[GAN_ELEMENTS[hidden[0]]] += 1.1;
  });
  return Object.fromEntries(Object.entries(scores).map(([key, value]) => [key, Number(value.toFixed(2))]));
}

function usefulElements(dayElement, scores) {
  const total = Object.values(scores).reduce((sum, value) => sum + value, 0) || 1;
  const resourceElement = inverseLookup(ELEMENT_GENERATES, dayElement);
  const bodyScore = scores[dayElement] + scores[resourceElement];
  const strength = bodyScore / total >= 0.42 ? "偏强" : "偏弱";
  if (strength === "偏强") {
    return {
      useful: [ELEMENT_GENERATES[dayElement], ELEMENT_CONTROLS[dayElement], inverseLookup(ELEMENT_CONTROLS, dayElement)],
      avoid: [dayElement, resourceElement],
      strength
    };
  }
  return {
    useful: [dayElement, resourceElement],
    avoid: [ELEMENT_GENERATES[dayElement], ELEMENT_CONTROLS[dayElement], inverseLookup(ELEMENT_CONTROLS, dayElement)],
    strength
  };
}

function classifyQuestion(question) {
  const text = String(question || "");
  const match = CATEGORY_RULES.find((rule) => rule.keywords.some((keyword) => text.includes(keyword)));
  return match || { key: "general", label: "综合问事", gates: ["开门", "生门"], keywords: [] };
}

function hashString(value) {
  let hash = 2166136261;
  for (let i = 0; i < value.length; i += 1) {
    hash ^= value.charCodeAt(i);
    hash = Math.imul(hash, 16777619);
  }
  return hash >>> 0;
}

function scorePalace(palace, category, useful, dayElement) {
  let score = 50;
  score += GATE_TONE[palace.gate]?.score || 0;
  if (category.gates.includes(palace.gate) || category.gates.includes(palace.deity) || category.gates.includes(palace.star)) score += 14;
  if (useful.includes(palace.element)) score += 8;
  if (ELEMENT_GENERATES[dayElement] === palace.element) score += 3;
  if (palace.deity === "六合" && category.key === "relationship") score += 9;
  if (palace.star === "天辅" && category.key === "study") score += 9;
  if (palace.gate === "生门" && category.key === "wealth") score += 8;
  if (palace.gate === "开门" && category.key === "career") score += 8;
  if (palace.gate === "死门" || palace.deity === "白虎") score -= 7;
  return clamp(score, 10, 95);
}

function buildPlate(now, pillars, question, category, useful, dayElement) {
  const seed = hashString(`${formatDateTime(now)}|${pillars["日柱"]}|${pillars["时柱"]}|${question}`);
  const dayIndex = GAN.indexOf(pillars["日柱"][0]);
  const hourBranchIndex = ZHI.indexOf(pillars["时柱"][1]);
  const gateStart = (seed + dayIndex + hourBranchIndex) % GATES.length;
  const starStart = (Math.floor(seed / 7) + hourBranchIndex) % STARS.length;
  const deityStart = (Math.floor(seed / 13) + dayIndex) % DEITIES.length;
  const stemStart = (dayIndex + Math.floor(seed / 17)) % GAN.length;
  const plate = PALACES.map((palace, index) => {
    const item = {
      ...palace,
      gate: GATES[(index + gateStart) % GATES.length],
      star: STARS[(index + starStart) % STARS.length],
      deity: DEITIES[(index + deityStart) % DEITIES.length],
      stem: GAN[(index + stemStart) % GAN.length]
    };
    return { ...item, score: scorePalace(item, category, useful, dayElement) };
  });
  plate.sort((a, b) => RENDER_ORDER.indexOf(a.key) - RENDER_ORDER.indexOf(b.key));
  const focus = [...plate].sort((a, b) => b.score - a.score)[0];
  const dutyGate = plate.find((item) => item.gate === "开门") || focus;
  const dutyStar = plate.find((item) => item.deity === "值符") || focus;
  return {
    seed,
    rendered: plate,
    focus,
    dutyGate,
    dutyStar
  };
}

function verdictFromScore(score) {
  if (score >= 76) return { label: "宜主动推进", tone: "盘面有可用资源，适合把核心动作提前。", level: "strong" };
  if (score >= 62) return { label: "小步试探", tone: "可以推进，但要用小样、试探和复核降低误判。", level: "good" };
  if (score >= 48) return { label: "先校准信息", tone: "信息不够顺，先查证、补证据、缩小承诺。", level: "watch" };
  return { label: "暂缓硬冲", tone: "阻力偏重，适合止损、改方案或等待更清楚的窗口。", level: "hold" };
}

function categoryActions(category) {
  const bank = {
    career: ["把目标拆成一个 48 小时内能交付的小样。", "先找关键人确认验收口径，再投入大成本。", "把口头承诺转成邮件、文档或排期。"],
    wealth: ["先核现金流、合同边界和回款节点。", "不要因为情绪乐观扩大仓位或压货。", "把可变成本、违约条款和退出条件写清楚。"],
    relationship: ["先澄清对方真实诉求，不急着定性。", "把一次沟通限定在一个核心问题。", "避免冷战和试探，优先给出可验证的边界。"],
    study: ["先定考试/申请的硬截止，再排学习块。", "用错题和样卷校准，不靠泛泛努力。", "优先补最拖分的一类题。"],
    health: ["身体不适以医生诊断为准，工具不替代医疗意见。", "先记录症状、时间和触发因素。", "把休息、复查和专业咨询排进日程。"],
    travel: ["先确认证件、路线、付款和取消政策。", "把出行计划留出缓冲，不压极限时间。", "涉及搬迁时先做试住或短期验证。"],
    general: ["先写下可验证事实和不可验证猜测。", "用一个低成本动作测试局面。", "把最坏损失限制在自己能承受的范围。"]
  };
  return bank[category.key] || bank.general;
}

function timingText(now, focus) {
  const score = focus.score;
  const shortDays = score >= 62 ? 3 : 7;
  const mediumDays = score >= 62 ? 10 : 21;
  const shortDate = formatDateOnly(new Date(now.getTime() + shortDays * DAY_MS));
  const mediumDate = formatDateOnly(new Date(now.getTime() + mediumDays * DAY_MS));
  if (score >= 62) {
    return `先看 ${shortDate} 前后的第一轮反馈，再以 ${mediumDate} 前后的结果决定加码。`;
  }
  return `先把信息补齐到 ${shortDate}，若仍反复卡住，等到 ${mediumDate} 后再做大动作。`;
}

function parseBirth(payload) {
  const time = parseTimeInput(payload.birthTime || "08:00");
  if (payload.calendarType === "lunar") {
    const solar = lunarToSolarDate(payload.lunarYear, payload.lunarMonth, payload.lunarDay, Boolean(payload.lunarLeap));
    const p = partsFromDate(solar);
    return {
      birthDate: makeDate(p.year, p.month, p.day, time.hour, time.minute),
      calendarNote: `输入为农历 ${payload.lunarYear}年${payload.lunarLeap ? "闰" : ""}${payload.lunarMonth}月${payload.lunarDay}日，已换算为公历 ${p.year}-${pad2(p.month)}-${pad2(p.day)}。`
    };
  }
  const solar = parseDateInput(payload.solarDate);
  const date = makeDate(solar.year, solar.month, solar.day, time.hour, time.minute);
  const lunar = solarToLunarDate(date);
  return {
    birthDate: date,
    calendarNote: `输入为公历 ${formatDateTime(date)}，对应农历约为 ${formatLunar(lunar)}。`
  };
}

export function buildReading(payload, options = {}) {
  const question = String(payload.question || "").trim();
  if (question.length < 4) {
    throw new Error("问事内容太短，请至少写清楚一件具体事情。");
  }
  const { birthDate, calendarNote } = parseBirth(payload);
  let trueSolar = null;
  let adjustedBirth = birthDate;
  if (payload.useTrueSolar) {
    trueSolar = trueSolarReport(birthDate, payload.province, payload.city, payload.district);
    adjustedBirth = trueSolar.correctedDate;
  }

  const pillars = buildPillars(adjustedBirth);
  const dayMaster = pillars["日柱"][0];
  const dayElement = GAN_ELEMENTS[dayMaster];
  const scores = elementScores(pillars);
  const elementBalance = usefulElements(dayElement, scores);
  const category = classifyQuestion(question);
  const now = options.now instanceof Date ? options.now : new Date();
  const floatingNow = makeDate(now.getUTCFullYear(), now.getUTCMonth() + 1, now.getUTCDate(), now.getUTCHours(), now.getUTCMinutes());
  const qimen = buildPlate(floatingNow, pillars, question, category, elementBalance.useful, dayElement);
  const outcomeScore = qimen.focus.score;
  const verdict = verdictFromScore(outcomeScore);
  const hidden = Object.fromEntries(Object.entries(pillars).map(([name, pillar]) => [
    name,
    (HIDDEN_STEMS[pillar[1]] || []).map((gan) => `${gan}${relationTenGod(dayMaster, gan)}`).join("、")
  ]));
  const tenGods = Object.fromEntries(Object.entries(pillars).map(([name, pillar]) => [
    name,
    name === "日柱" ? "日主" : relationTenGod(dayMaster, pillar[0])
  ]));
  const direction = (payload.gender === "male" && GAN_POLARITY[pillars["年柱"][0]] === "阳") || (payload.gender === "female" && GAN_POLARITY[pillars["年柱"][0]] === "阴")
    ? "顺行"
    : "逆行";

  const gateTone = GATE_TONE[qimen.focus.gate];
  const sections = [
    {
      title: "事情态势",
      body: `${category.label}取 ${category.gates.join(" / ")} 为主要观察点，本盘焦点落 ${qimen.focus.name}，见 ${qimen.focus.gate}、${qimen.focus.star}、${qimen.focus.deity}。${gateTone.text}`
    },
    {
      title: "命局侧重",
      body: `日主 ${dayMaster}${pillars["日柱"][1]}，五行属${dayElement}，身势${elementBalance.strength}。此局优先借 ${elementBalance.useful.join("、")} 的方式处理，少走 ${elementBalance.avoid.join("、")} 的消耗路线。`
    },
    {
      title: "关键阻力",
      body: qimen.focus.score >= 62
        ? `阻力不是不能动，而是节奏和证据要跟上。${qimen.focus.deity} 临宫，适合把暗处变量摊开核验。`
        : `盘面分数偏谨慎，${qimen.focus.gate} 说明事情容易被旧条件、信息差或情绪牵制，先别把承诺放大。`
    },
    {
      title: "时间窗口",
      body: timingText(floatingNow, qimen.focus)
    }
  ];

  const cautions = [
    "本工具用于传统术数文化娱乐和自我复盘，不构成法律、医疗、投资或人生重大决策建议。",
    "若问题涉及疾病、债务、诉讼、婚姻财产、人身安全，请优先咨询持证专业人士。",
    "排盘采用近似节气与内置农历表；细排时应复核历法、经纬度和出生记录。"
  ];

  return {
    summary: `${verdict.label}：${verdict.tone}`,
    meta: {
      generatedAt: formatDateTime(floatingNow),
      engine: "Bazi fallback pillars + Qimen-style structured plate v1",
      question,
      category: category.label,
      calendarNote,
      birthTime: formatDateTime(birthDate),
      adjustedBirthTime: formatDateTime(adjustedBirth),
      trueSolar,
      privacy: "输入只用于本次计算，默认不保存。"
    },
    bazi: {
      gender: payload.gender === "female" ? "女" : payload.gender === "other" ? "其他/未指定" : "男",
      pillars,
      tenGods,
      hiddenStems: hidden,
      dayMaster,
      dayElement,
      strength: elementBalance.strength,
      usefulElements: elementBalance.useful,
      avoidElements: elementBalance.avoid,
      elementScores: scores,
      luckDirection: direction
    },
    qimen: {
      outcomeScore,
      verdict,
      focusPalace: qimen.focus,
      dutyGate: qimen.dutyGate,
      dutyStar: qimen.dutyStar,
      plate: qimen.rendered
    },
    sections,
    actions: categoryActions(category),
    cautions
  };
}

export function composeReadingFromProfile(payload, profile, options = {}) {
  const question = String(payload.question || "").trim();
  if (question.length < 4) {
    throw new Error("问事内容太短，请至少写清楚一件具体事情。");
  }

  const pillars = profile.pillars;
  const dayMaster = profile.dayMaster || pillars["日柱"][0];
  const dayElement = profile.dayElement || GAN_ELEMENTS[dayMaster];
  const scores = profile.elementScores || elementScores(pillars);
  const elementBalance = {
    useful: profile.usefulElements,
    avoid: profile.avoidElements,
    strength: profile.strength
  };
  if (!elementBalance.useful || !elementBalance.avoid || !elementBalance.strength) {
    const fallback = usefulElements(dayElement, scores);
    elementBalance.useful = elementBalance.useful || fallback.useful;
    elementBalance.avoid = elementBalance.avoid || fallback.avoid;
    elementBalance.strength = elementBalance.strength || fallback.strength;
  }

  const category = classifyQuestion(question);
  const now = options.now instanceof Date ? options.now : new Date();
  const floatingNow = makeDate(now.getUTCFullYear(), now.getUTCMonth() + 1, now.getUTCDate(), now.getUTCHours(), now.getUTCMinutes());
  const qimen = buildPlate(floatingNow, pillars, question, category, elementBalance.useful, dayElement);
  const outcomeScore = qimen.focus.score;
  const verdict = verdictFromScore(outcomeScore);
  const tenGods = profile.tenGods || Object.fromEntries(Object.entries(pillars).map(([name, pillar]) => [
    name,
    name === "日柱" ? "日主" : relationTenGod(dayMaster, pillar[0])
  ]));
  const hidden = profile.hiddenStems || Object.fromEntries(Object.entries(pillars).map(([name, pillar]) => [
    name,
    (HIDDEN_STEMS[pillar[1]] || []).map((gan) => `${gan}${relationTenGod(dayMaster, gan)}`).join("、")
  ]));

  const gateTone = GATE_TONE[qimen.focus.gate];
  const sections = [
    {
      title: "这事现在什么风向",
      body: `${category.label}这类问题，先看 ${category.gates.join(" / ")}。本盘焦点在 ${qimen.focus.name}，见 ${qimen.focus.gate}、${qimen.focus.star}、${qimen.focus.deity}。${gateTone.text}`
    },
    {
      title: "你这张盘怎么借力",
      body: `日主 ${dayMaster}${pillars["日柱"][1]}，五行属${dayElement}，整体${elementBalance.strength}。处理这事更适合走 ${elementBalance.useful.join("、")} 的路子，少在 ${elementBalance.avoid.join("、")} 上硬耗。`
    },
    {
      title: "最容易翻车的点",
      body: qimen.focus.score >= 62
        ? `不是不能冲，是别边冲边漏信息。${qimen.focus.deity} 临宫，先把暗处变量摊开，别靠脑补补剧情。`
        : `盘面偏谨慎，${qimen.focus.gate} 说明事情容易被旧条件、信息差或情绪牵着走。先别把承诺和成本放大。`
    },
    {
      title: "什么时候动比较顺",
      body: timingText(floatingNow, qimen.focus)
    }
  ];

  return {
    summary: `${verdict.label}：${verdict.tone}`,
    meta: {
      generatedAt: formatDateTime(floatingNow),
      engine: profile.engine || "Zi Ping EightChar + Qimen-style structured plate v1",
      llm: profile.llm || null,
      question,
      category: category.label,
      calendarNote: profile.calendarNote,
      birthTime: formatDateTime(profile.birthDate),
      adjustedBirthTime: formatDateTime(profile.adjustedBirth),
      trueSolar: profile.trueSolar,
      privacy: profile.privacy || "输入只用于本次计算，默认不保存。"
    },
    bazi: {
      gender: payload.gender === "female" ? "女" : payload.gender === "other" ? "其他/未指定" : "男",
      pillars,
      tenGods,
      hiddenStems: hidden,
      dayMaster,
      dayElement,
      strength: elementBalance.strength,
      usefulElements: elementBalance.useful,
      avoidElements: elementBalance.avoid,
      elementScores: scores,
      luckDirection: profile.luckDirection || "未计算",
      bigLucks: profile.bigLucks || [],
      methodNote: profile.methodNote || "子平法按节气定年、月柱；时柱按出生时辰。"
    },
    qimen: {
      outcomeScore,
      verdict,
      focusPalace: qimen.focus,
      dutyGate: qimen.dutyGate,
      dutyStar: qimen.dutyStar,
      plate: qimen.rendered
    },
    sections,
    actions: categoryActions(category),
    cautions: [
      "这是一款传统文化娱乐和自我复盘工具，不替代专业建议。",
      "涉及疾病、债务、诉讼、婚姻财产、人身安全，请优先找持证专业人士。",
      "子平四柱由历法库排出，奇门问事部分用于结构化分析，不做绝对预言。"
    ]
  };
}

export function buildTrueSolarOnly(payload) {
  const datePart = parseDateInput(payload.solarDate);
  const time = parseTimeInput(payload.birthTime || "08:00");
  const date = makeDate(datePart.year, datePart.month, datePart.day, time.hour, time.minute);
  const report = trueSolarReport(date, payload.province, payload.city, payload.district);
  return {
    original: formatDateTime(date),
    corrected: formatDateTime(report.correctedDate),
    ...report
  };
}

export function convertSolarLunar(payload) {
  if (payload.mode === "lunar-to-solar") {
    const solar = lunarToSolarDate(payload.lunarYear, payload.lunarMonth, payload.lunarDay, Boolean(payload.lunarLeap));
    return { mode: payload.mode, solar: formatDateOnly(solar), lunar: `${payload.lunarYear}年${payload.lunarLeap ? "闰" : ""}${payload.lunarMonth}月${payload.lunarDay}日` };
  }
  const datePart = parseDateInput(payload.solarDate);
  const date = makeDate(datePart.year, datePart.month, datePart.day);
  return { mode: payload.mode, solar: formatDateOnly(date), lunar: formatLunar(solarToLunarDate(date)) };
}
