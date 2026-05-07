const formatMoney = (value) => `$${Math.max(0, value).toLocaleString(undefined, {
  maximumFractionDigits: 0
})}`;

const numberValue = (form, name, fallback = 0) => {
  const field = form.elements[name];
  const value = Number.parseFloat(field ? field.value : "");
  return Number.isFinite(value) ? value : fallback;
};

const getToolLabel = (tool) => ({
  paint: "Paint calculator",
  tile: "Tile calculator",
  curtain: "Curtain calculator"
}[tool] || "Home calculator");

function paintResult(form) {
  const length = numberValue(form, "length", 12);
  const width = numberValue(form, "width", 10);
  const height = numberValue(form, "height", 8);
  const openings = numberValue(form, "openings", 45);
  const coats = numberValue(form, "coats", 2);
  const coverage = numberValue(form, "coverage", 350);
  const bucketGallons = numberValue(form, "bucketGallons", 1);
  const bucketPrice = numberValue(form, "bucketPrice", 42);
  const wallArea = Math.max(0, 2 * (length + width) * height - openings);
  const paintArea = wallArea * coats;
  const gallons = coverage > 0 ? paintArea / coverage : 0;
  const buckets = Math.ceil(gallons / Math.max(bucketGallons, .1));
  const budget = buckets * bucketPrice;
  return {
    title: "Paint estimate",
    metrics: [
      ["Paintable wall area", `${wallArea.toFixed(0)} sq ft`],
      ["Coverage to buy for", `${paintArea.toFixed(0)} sq ft`],
      ["Estimated gallons", `${gallons.toFixed(1)} gal`],
      ["Buckets to buy", `${buckets} bucket${buckets === 1 ? "" : "s"}`],
      ["Material budget", formatMoney(budget)]
    ],
    summary: `Buy about ${buckets} bucket${buckets === 1 ? "" : "s"} for ${coats} coat${coats === 1 ? "" : "s"}. Keep one small reserve if the wall is textured or dark.`
  };
}

function tileResult(form) {
  const area = numberValue(form, "area", 120);
  const tileWidth = numberValue(form, "tileWidth", 12);
  const tileHeight = numberValue(form, "tileHeight", 24);
  const waste = numberValue(form, "waste", 10);
  const boxCount = numberValue(form, "boxCount", 8);
  const boxPrice = numberValue(form, "boxPrice", 36);
  const tileArea = Math.max(.01, tileWidth * tileHeight / 144);
  const adjustedArea = area * (1 + waste / 100);
  const pieces = Math.ceil(adjustedArea / tileArea);
  const boxes = Math.ceil(pieces / Math.max(1, boxCount));
  const budget = boxes * boxPrice;
  return {
    title: "Tile estimate",
    metrics: [
      ["Area with waste", `${adjustedArea.toFixed(1)} sq ft`],
      ["Single tile area", `${tileArea.toFixed(2)} sq ft`],
      ["Tiles needed", `${pieces} pieces`],
      ["Boxes to buy", `${boxes} boxes`],
      ["Material budget", formatMoney(budget)]
    ],
    summary: `Plan for ${pieces} tiles, or ${boxes} boxes. Increase waste to 15% for diagonal layouts or rooms with many cuts.`
  };
}

function curtainResult(form) {
  const windowWidth = numberValue(form, "windowWidth", 72);
  const windowHeight = numberValue(form, "windowHeight", 60);
  const fullness = numberValue(form, "fullness", 2);
  const sideReturn = numberValue(form, "sideReturn", 8);
  const dropExtra = numberValue(form, "dropExtra", 6);
  const panelWidth = numberValue(form, "panelWidth", 54);
  const pricePerYard = numberValue(form, "pricePerYard", 22);
  const rodWidth = windowWidth + sideReturn * 2;
  const fabricWidth = rodWidth * fullness;
  const panelLength = windowHeight + dropExtra;
  const panels = Math.ceil(fabricWidth / Math.max(1, panelWidth));
  const yards = panels * panelLength / 36;
  const budget = yards * pricePerYard;
  return {
    title: "Curtain estimate",
    metrics: [
      ["Suggested rod width", `${rodWidth.toFixed(0)} in`],
      ["Fabric width target", `${fabricWidth.toFixed(0)} in`],
      ["Panel length", `${panelLength.toFixed(0)} in`],
      ["Panels needed", `${panels} panel${panels === 1 ? "" : "s"}`],
      ["Fabric budget", formatMoney(budget)]
    ],
    summary: `Use around ${panels} panel${panels === 1 ? "" : "s"} at ${fullness}x fullness. Round up for pattern matching or shrinkage.`
  };
}

function renderResult(container, result) {
  container.querySelector("[data-result-title]").textContent = result.title;
  container.querySelector("[data-result-summary]").textContent = result.summary;
  const metrics = container.querySelector("[data-result-metrics]");
  metrics.innerHTML = "";
  result.metrics.forEach(([label, value]) => {
    const row = document.createElement("div");
    row.className = "metric";
    row.innerHTML = `<span>${label}</span><strong>${value}</strong>`;
    metrics.appendChild(row);
  });
}

function calculate(form) {
  const tool = form.dataset.tool;
  const result = tool === "paint"
    ? paintResult(form)
    : tool === "tile"
      ? tileResult(form)
      : curtainResult(form);
  const resultCard = document.querySelector(`[data-result-for="${tool}"]`);
  renderResult(resultCard, result);
  window.__lastHomeCalcResult = { tool, result };
}

function downloadResultCard() {
  const last = window.__lastHomeCalcResult;
  if (!last) return;
  const canvas = document.createElement("canvas");
  canvas.width = 1200;
  canvas.height = 630;
  const ctx = canvas.getContext("2d");
  ctx.fillStyle = "#f6f7f2";
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = "#1f7a70";
  ctx.fillRect(0, 0, 1200, 18);
  ctx.fillStyle = "#1c2526";
  ctx.font = "700 42px Arial";
  ctx.fillText(getToolLabel(last.tool), 72, 96);
  ctx.font = "700 58px Arial";
  ctx.fillText(last.result.title, 72, 170);
  ctx.font = "28px Arial";
  ctx.fillStyle = "#40504a";
  wrapText(ctx, last.result.summary, 72, 226, 1010, 38);
  ctx.font = "700 32px Arial";
  ctx.fillStyle = "#1c2526";
  last.result.metrics.slice(0, 5).forEach(([label, value], index) => {
    const y = 360 + index * 48;
    ctx.fillText(label, 72, y);
    ctx.fillStyle = "#1f7a70";
    ctx.fillText(value, 640, y);
    ctx.fillStyle = "#1c2526";
  });
  ctx.font = "22px Arial";
  ctx.fillStyle = "#63716c";
  ctx.fillText("homecalc.xyz", 72, 590);
  const link = document.createElement("a");
  link.download = `${last.tool}-estimate.png`;
  link.href = canvas.toDataURL("image/png");
  link.click();
}

function wrapText(ctx, text, x, y, maxWidth, lineHeight) {
  const words = text.split(" ");
  let line = "";
  words.forEach((word) => {
    const test = line ? `${line} ${word}` : word;
    if (ctx.measureText(test).width > maxWidth) {
      ctx.fillText(line, x, y);
      line = word;
      y += lineHeight;
    } else {
      line = test;
    }
  });
  if (line) ctx.fillText(line, x, y);
}

document.querySelectorAll("form[data-tool]").forEach((form) => {
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    calculate(form);
  });
  calculate(form);
});

document.querySelectorAll("[data-download-result]").forEach((button) => {
  button.addEventListener("click", downloadResultCard);
});

document.querySelectorAll("[data-share-page]").forEach((button) => {
  button.addEventListener("click", async () => {
    const shareData = {
      title: document.title,
      text: "Try this home improvement calculator.",
      url: window.location.href
    };
    if (navigator.share) {
      await navigator.share(shareData);
    } else {
      await navigator.clipboard.writeText(window.location.href);
      button.textContent = "Link copied";
      window.setTimeout(() => { button.textContent = "Copy share link"; }, 1800);
    }
  });
});
