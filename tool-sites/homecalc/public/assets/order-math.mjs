const numeric = (value) => typeof value === "number" && Number.isFinite(value);
const between = (value, min, max) => numeric(value) && value >= min && value <= max;
const validLabel = (value) => typeof value === "string" && value.trim().length > 0 && value.length <= 80;

export function calculateOrder(project) {
  const { zones, products, allowance } = project;
  if (!Array.isArray(zones) || zones.length < 1 || zones.length > 20 ||
      !Array.isArray(products) || products.length < 1 || products.length > 2 ||
      !between(allowance, 0, 100)) {
    throw new Error("Enter 1 to 20 areas, 1 or 2 products, and an allowance from 0 to 100%.");
  }
  const measured = zones.map((zone, index) => {
    if (!zone || !validLabel(zone.label) || ![1, -1].includes(zone.sign) ||
        !between(zone.length, .001, 10000) || !between(zone.width, .001, 10000)) {
      throw new Error(`Check the name and dimensions on area ${index + 1}.`);
    }
    return { ...zone, area: zone.sign * zone.length * zone.width };
  });
  const net = measured.reduce((total, zone) => total + zone.area, 0);
  if (net <= 0) throw new Error("The total area to cover must be greater than zero. Check your deductions.");
  const adjusted = net * (1 + allowance / 100);
  const options = products.map((product, index) => {
    if (!product || !validLabel(product.label) ||
        !between(product.coverage, .001, 10000) || !between(product.price, 0, 1000000) ||
        typeof product.reference !== "string" || product.reference.length > 160) {
      throw new Error(`Check the name, carton coverage and price on product ${index + 1}.`);
    }
    const ratio = adjusted / product.coverage;
    const nearest = Math.round(ratio);
    const tolerance = Number.EPSILON * 8 * Math.max(1, ratio);
    const cartons = nearest > 0 && Math.abs(ratio - nearest) <= tolerance ? nearest : Math.ceil(ratio);
    const purchased = cartons * product.coverage;
    return { ...product, cartons, purchased, extra: Math.max(0, purchased - adjusted), cost: cartons * product.price };
  });
  return { zones: measured, net, allowance, adjusted, options };
}

export const examples = {
  "tile-bath": {
    zones: [
      { label: "Bathroom floor", sign: 1, length: 7.5, width: 8 },
      { label: "Fixed vanity", sign: -1, length: 2.5, width: 1.75 }
    ],
    allowance: 12,
    products: [
      { label: "Daltile ec1 24 x 24", coverage: 15.49, price: 58, reference: "Illustrative quote. https://digitalassets.daltile.com/content/dam/Daltile/website/resources/products/sales-sheets/ec1/DAL_EC1_SS.pdf" },
      { label: "Daltile ec1 12 x 24", coverage: 11.62, price: 50, reference: "Illustrative quote. https://digitalassets.daltile.com/content/dam/Daltile/website/resources/products/sales-sheets/ec1/DAL_EC1_SS.pdf" }
    ]
  },
  "flooring-rooms": {
    zones: [
      { label: "Bedroom", sign: 1, length: 13.5, width: 11 },
      { label: "Closet", sign: 1, length: 5, width: 2.5 },
      { label: "Hall", sign: 1, length: 9, width: 3.5 }
    ],
    allowance: 10,
    products: [
      { label: "Shaw Distinction Plus 2045V-07065", coverage: 23.64, price: 64, reference: "Illustrative quote. https://shawfloors.com/en-us/vinyl/distinction-plus-ash-oak-7-/2045v-07065" },
      { label: "Shaw Starting Line 3060V-01182", coverage: 23.69, price: 67, reference: "Illustrative quote. https://shawfloors.com/en-us/vinyl/starting-line-moonstone-grey-7-/3060v-01182" }
    ]
  }
};

function csvCell(value) {
  if (typeof value === "number") return String(Number(value.toPrecision(14)));
  const safe = /^[\s\uFEFF]*[=+\-@\t\r\n]/u.test(value) ? "'" + value : value;
  return '"' + safe.replaceAll('"', '""') + '"';
}

export function orderCsv(result) {
  const rows = [
    ["HomeCalc material order", "US dollars", "Material only"],
    ["Area", "Action", "Length (ft)", "Width (ft)", "Signed area (sq ft)"],
    ...result.zones.map(({ label, sign, length, width, area }) => [label, sign > 0 ? "Include" : "Deduct", length, width, area]),
    [],
    ["Net area (sq ft)", result.net],
    ["Layout allowance (%)", result.allowance],
    ["Area including layout allowance (sq ft)", result.adjusted],
    ["Formula", "Net = sum of signed areas; adjusted = net x (1 + allowance / 100); cartons = round up adjusted / coverage"],
    [],
    ["Product", "Coverage per carton (sq ft)", "Price / carton (USD)", "Whole cartons", "Purchased (sq ft)", "Extra from rounding (sq ft)", "Material subtotal (USD)", "Specification or quote reference"],
    ...result.options.map(({ label, coverage, price, cartons, purchased, extra, cost, reference }) =>
      [label, coverage, price, cartons, purchased, extra, cost, reference])
  ];
  return rows.map(row => row.map(csvCell).join(",")).join("\r\n");
}
