import { calculateOrder, examples, orderCsv } from "./order-math.mjs";

const byId = (id) => document.getElementById(id);
const form = byId("order-form");
const zones = byId("order-zones");
const products = byId("order-products");
const status = byId("order-status");
const results = byId("order-results");
const shareField = byId("share-field");
const area = new Intl.NumberFormat("en-US", { maximumFractionDigits: 4 });
const usd = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" });
let lastProject;
let lastResult;
let nextId = 0;

const zoneFields = [
  ["label", "Area name", "text", 'maxlength="80" required'],
  ["sign", "Action", "select", ""],
  ["length", "Length (ft)", "number", 'min=".001" max="10000" step="any" required'],
  ["width", "Width (ft)", "number", 'min=".001" max="10000" step="any" required']
];
const productFields = [
  ["label", "Product or SKU", "text", 'maxlength="80" required'],
  ["coverage", "Carton coverage (sq ft)", "number", 'min=".001" max="10000" step="any" required'],
  ["price", "Price per carton (USD)", "number", 'min="0" max="1000000" step=".01" required'],
  ["reference", "Spec or quote reference (optional)", "text", 'maxlength="160"']
];

function toggleRowButtons() {
  byId("add-zone").disabled = zones.children.length >= 20;
  byId("add-product").disabled = products.children.length >= 2;
  for (const container of [zones, products]) {
    container.querySelectorAll("button").forEach(button => {
      button.disabled = container.children.length === 1;
    });
  }
}

function invalidate() {
  results.hidden = true;
  shareField.hidden = true;
  lastProject = undefined;
  lastResult = undefined;
  status.textContent = "";
}

function addRow(container, fields, values = {}) {
  const type = container === zones ? "Area" : "Product";
  const serial = ++nextId;
  const row = document.createElement("fieldset");
  row.className = "order-row";
  row.innerHTML = "<legend></legend><div class='order-fields'></div>";
  row.querySelector("legend").textContent = type;
  const grid = row.querySelector(".order-fields");
  for (const [key, label, inputType, attrs] of fields) {
    const id = "order-" + serial + "-" + key;
    const field = document.createElement("div");
    field.className = "field";
    const control = inputType === "select"
      ? '<select id="' + id + '" name="' + key + '"><option value="1">Include</option><option value="-1">Deduct</option></select>'
      : '<input id="' + id + '" name="' + key + '" type="' + inputType + '" ' + attrs + '>';
    field.innerHTML = '<label for="' + id + '">' + label + '</label>' + control;
    const input = field.lastElementChild;
    if (key in values) input.value = values[key];
    grid.append(field);
  }
  const remove = document.createElement("button");
  remove.type = "button";
  remove.className = "secondary order-remove";
  remove.textContent = "Remove " + type.toLowerCase();
  remove.addEventListener("click", () => {
    row.remove();
    toggleRowButtons();
    invalidate();
    (container.querySelector("input") || byId(container === zones ? "add-zone" : "add-product")).focus();
  });
  row.append(remove);
  container.append(row);
  toggleRowButtons();
  return row;
}

function buildForm(project) {
  zones.replaceChildren();
  products.replaceChildren();
  for (const zone of project.zones) addRow(zones, zoneFields, zone);
  for (const product of project.products) addRow(products, productFields, product);
  byId("allowance").value = project.allowance;
  invalidate();
}

function readForm() {
  const readRows = (container, fields) => Array.from(container.children, row =>
    Object.fromEntries(fields.map(([key, , type]) => {
      const field = row.querySelector('[name="' + key + '"]');
      return [key, type === "text" ? field.value.trim() : Number(field.value)];
    })));
  return {
    zones: readRows(zones, zoneFields),
    products: readRows(products, productFields),
    allowance: byId("allowance").valueAsNumber
  };
}

function showResult(project, moveFocus = false) {
  invalidate();
  try {
    lastResult = calculateOrder(project);
  } catch (error) {
    status.textContent = error.message;
    return;
  }
  lastProject = project;
  byId("order-area").textContent = area.format(lastResult.net) + " sq ft net; " +
    area.format(lastResult.adjusted) + " sq ft including " + area.format(lastResult.allowance) + "% layout allowance.";
  byId("order-options").replaceChildren(...lastResult.options.map(option => {
    const row = document.createElement("tr");
    const columns = [option.label, option.cartons, area.format(option.purchased) + " sq ft",
      area.format(option.extra) + " sq ft", usd.format(option.cost)];
    columns.forEach((value, index) => {
      const cell = document.createElement(index === 0 ? "th" : "td");
      if (index === 0) cell.scope = "row";
      cell.textContent = value;
      row.append(cell);
    });
    return row;
  }));
  results.hidden = false;
  if (moveFocus) byId("result-heading").focus();
}

function loadFromLocation() {
  const fragment = window.location.hash.slice(1);
  if (Object.hasOwn(examples, fragment)) {
    buildForm(examples[fragment]);
    showResult(examples[fragment]);
    return;
  }
  if (!fragment.startsWith("order=")) return;
  try {
    if (fragment.length > 32000) throw new Error("Long link");
    const project = JSON.parse(decodeURIComponent(fragment.slice(6)));
    calculateOrder(project);
    buildForm(project);
    showResult(readForm());
  } catch {
    status.textContent = "This estimate link could not be opened. Enter your measurements or load an example.";
  }
}

document.querySelectorAll("[data-example]").forEach(button => {
  button.addEventListener("click", () => {
    const example = button.dataset.example;
    history.replaceState(null, "", "#" + example);
    loadFromLocation();
    zones.querySelector("input").focus();
    status.textContent = "Example loaded. Edit any value and recalculate.";
  });
});
window.addEventListener("hashchange", loadFromLocation);
form.addEventListener("submit", event => {
  event.preventDefault();
  showResult(readForm(), true);
});
form.addEventListener("input", invalidate);
form.addEventListener("change", invalidate);
byId("add-zone").addEventListener("click", () => {
  invalidate();
  addRow(zones, zoneFields).querySelector("input").focus();
});
byId("add-product").addEventListener("click", () => {
  invalidate();
  addRow(products, productFields).querySelector("input").focus();
});
byId("order-csv").addEventListener("click", () => {
  if (!lastResult) return;
  const url = URL.createObjectURL(new Blob([orderCsv(lastResult)], { type: "text/csv;charset=utf-8" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = "homecalc-material-order.csv";
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
});
byId("order-share").addEventListener("click", async () => {
  if (!lastProject) return;
  const url = new URL(location.href);
  url.search = "";
  url.hash = "order=" + encodeURIComponent(JSON.stringify(lastProject));
  try {
    await navigator.clipboard.writeText(url.href);
    status.textContent = "Estimate link copied.";
  } catch {
    shareField.hidden = false;
    byId("share-url").value = url.href;
    byId("share-url").select();
    status.textContent = "Copy the estimate link from the field below.";
  }
});

buildForm({ zones: [{ label: "Main area", sign: 1 }], products: [{ label: "Product A" }], allowance: 10 });
loadFromLocation();
