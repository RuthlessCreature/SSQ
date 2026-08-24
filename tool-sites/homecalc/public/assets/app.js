const formatMoney = (value) => `$${Math.max(0, value).toLocaleString(undefined, {
  maximumFractionDigits: 0
})}`;

const numberValue = (form, name, fallback = 0) => {
  const field = form.querySelector(`[name="${name}"]`);
  const value = Number.parseFloat(field ? field.value : "");
  return Number.isFinite(value) ? value : fallback;
};

const ceilUnits = (value, unit = 1) => Math.ceil((value - 1e-9) / Math.max(unit, 1e-9));

const getToolLabel = (tool) => ({
  paint: "Paint calculator",
  tile: "Tile calculator",
  curtain: "Curtain calculator",
  flooring: "Flooring calculator",
  drywall: "Drywall calculator",
  wallpaper: "Wallpaper calculator",
  concrete: "Concrete calculator",
  mulch: "Mulch calculator",
  deck: "Deck board calculator",
  baseboard: "Baseboard trim calculator"
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
  const buckets = ceilUnits(gallons, Math.max(bucketGallons, .1));
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
  const boxCoverage = numberValue(form, "boxCoverage", 16);
  const boxPrice = numberValue(form, "boxPrice", 36);
  const tileArea = Math.max(.01, tileWidth * tileHeight / 144);
  const adjustedArea = area * (1 + waste / 100);
  const pieces = ceilUnits(adjustedArea, tileArea);
  const boxes = ceilUnits(adjustedArea, Math.max(.1, boxCoverage));
  const budget = boxes * boxPrice;
  return {
    title: "Tile estimate",
    metrics: [
      ["Area with waste", `${adjustedArea.toFixed(1)} sq ft`],
      ["Tiles needed", `${pieces} pieces`],
      ["Carton coverage", `${boxCoverage.toFixed(1)} sq ft`],
      ["Boxes to buy", `${boxes} boxes`],
      ["Material budget", formatMoney(budget)]
    ],
    summary: `Plan for ${pieces} tiles, or ${boxes} boxes at the selected carton coverage. Revisit the allowance when the layout, cuts, or product changes.`
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
  const panels = ceilUnits(fabricWidth, Math.max(1, panelWidth));
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

function flooringResult(form) {
  const length = numberValue(form, "length", 15);
  const width = numberValue(form, "width", 12);
  const waste = numberValue(form, "waste", 10);
  const boxCoverage = numberValue(form, "boxCoverage", 22);
  const boxPrice = numberValue(form, "boxPrice", 58);
  const baseArea = Math.max(0, length * width);
  const adjustedArea = baseArea * (1 + waste / 100);
  const boxes = ceilUnits(adjustedArea, Math.max(.1, boxCoverage));
  const purchasedCoverage = boxes * boxCoverage;
  const budget = boxes * boxPrice;
  return {
    title: "Flooring estimate",
    metrics: [
      ["Room floor area", `${baseArea.toFixed(1)} sq ft`],
      ["Area with waste", `${adjustedArea.toFixed(1)} sq ft`],
      ["Box coverage", `${boxCoverage.toFixed(1)} sq ft`],
      ["Boxes to buy", `${boxes} box${boxes === 1 ? "" : "es"}`],
      ["Material budget", formatMoney(budget)]
    ],
    summary: `Buy about ${boxes} box${boxes === 1 ? "" : "es"} for ${purchasedCoverage.toFixed(1)} sq ft of listed coverage. Increase waste for diagonal layouts, narrow closets, or products that may be hard to reorder.`
  };
}

function drywallResult(form) {
  const length = numberValue(form, "length", 12);
  const width = numberValue(form, "width", 10);
  const height = numberValue(form, "height", 8);
  const openings = numberValue(form, "openings", 45);
  const waste = numberValue(form, "waste", 10);
  const sheetWidth = numberValue(form, "sheetWidth", 4);
  const sheetHeight = numberValue(form, "sheetHeight", 8);
  const sheetPrice = numberValue(form, "sheetPrice", 15);
  const wallArea = Math.max(0, 2 * (length + width) * height - openings);
  const adjustedArea = wallArea * (1 + waste / 100);
  const sheetArea = Math.max(.1, sheetWidth * sheetHeight);
  const sheets = ceilUnits(adjustedArea, sheetArea);
  const budget = sheets * sheetPrice;
  return {
    title: "Drywall estimate",
    metrics: [
      ["Wall area", `${wallArea.toFixed(0)} sq ft`],
      ["Area with waste", `${adjustedArea.toFixed(0)} sq ft`],
      ["Sheet coverage", `${sheetArea.toFixed(0)} sq ft`],
      ["Sheets to buy", `${sheets} sheet${sheets === 1 ? "" : "s"}`],
      ["Panel budget", formatMoney(budget)]
    ],
    summary: `Plan for about ${sheets} sheet${sheets === 1 ? "" : "s"}. Add separate budget for joint compound, tape, corner bead, screws, sanding supplies, and primer.`
  };
}

function wallpaperResult(form) {
  const wallLength = numberValue(form, "wallLength", 36);
  const wallHeight = numberValue(form, "wallHeight", 8);
  const openings = numberValue(form, "openings", 45);
  const waste = numberValue(form, "waste", 15);
  const rollCoverage = numberValue(form, "rollCoverage", 56);
  const rollPrice = numberValue(form, "rollPrice", 38);
  const wallArea = Math.max(0, wallLength * wallHeight - openings);
  const adjustedArea = wallArea * (1 + waste / 100);
  const rolls = ceilUnits(adjustedArea, Math.max(.1, rollCoverage));
  const budget = rolls * rollPrice;
  return {
    title: "Wallpaper estimate",
    metrics: [
      ["Wall area", `${wallArea.toFixed(0)} sq ft`],
      ["Area with pattern waste", `${adjustedArea.toFixed(0)} sq ft`],
      ["Roll coverage", `${rollCoverage.toFixed(0)} sq ft`],
      ["Rolls to buy", `${rolls} roll${rolls === 1 ? "" : "s"}`],
      ["Wallpaper budget", formatMoney(budget)]
    ],
    summary: `Buy about ${rolls} roll${rolls === 1 ? "" : "s"}. Increase waste for large pattern repeats, half-drop patterns, short walls, or discontinued wallpaper.`
  };
}

function concreteResult(form) {
  const length = numberValue(form, "length", 10);
  const width = numberValue(form, "width", 8);
  const thickness = numberValue(form, "thickness", 4);
  const waste = numberValue(form, "waste", 10);
  const bagYield = numberValue(form, "bagYield", .6);
  const bagPrice = numberValue(form, "bagPrice", 6);
  const volume = Math.max(0, length * width * thickness / 12);
  const adjustedVolume = volume * (1 + waste / 100);
  const bags = ceilUnits(adjustedVolume, Math.max(.01, bagYield));
  const budget = bags * bagPrice;
  return {
    title: "Concrete estimate",
    metrics: [
      ["Concrete volume", `${volume.toFixed(1)} cu ft`],
      ["Volume with waste", `${adjustedVolume.toFixed(1)} cu ft`],
      ["Cubic yards", `${(adjustedVolume / 27).toFixed(2)} cu yd`],
      ["Bags to buy", `${bags} bag${bags === 1 ? "" : "s"}`],
      ["Bag budget", formatMoney(budget)]
    ],
    summary: `Plan for about ${bags} bag${bags === 1 ? "" : "s"} using the listed bag yield. For larger pours, compare bag cost against ready-mix delivery.`
  };
}

function mulchResult(form) {
  const area = numberValue(form, "area", 240);
  const depth = numberValue(form, "depth", 3);
  const bagVolume = numberValue(form, "bagVolume", 2);
  const bagPrice = numberValue(form, "bagPrice", 4);
  const volume = Math.max(0, area * depth / 12);
  const bags = ceilUnits(volume, Math.max(.01, bagVolume));
  const budget = bags * bagPrice;
  return {
    title: "Mulch estimate",
    metrics: [
      ["Bed area", `${area.toFixed(0)} sq ft`],
      ["Mulch volume", `${volume.toFixed(1)} cu ft`],
      ["Cubic yards", `${(volume / 27).toFixed(2)} cu yd`],
      ["Bags to buy", `${bags} bag${bags === 1 ? "" : "s"}`],
      ["Mulch budget", formatMoney(budget)]
    ],
    summary: `Buy about ${bags} bag${bags === 1 ? "" : "s"} for ${depth.toFixed(1)} in depth. Keep mulch away from siding, stems, trunks, and weep holes.`
  };
}

function deckResult(form) {
  const deckLength = numberValue(form, "deckLength", 16);
  const deckWidth = numberValue(form, "deckWidth", 12);
  const boardWidth = numberValue(form, "boardWidth", 5.5);
  const gap = numberValue(form, "gap", .125);
  const boardLength = numberValue(form, "boardLength", 16);
  const waste = numberValue(form, "waste", 10);
  const boardPrice = numberValue(form, "boardPrice", 22);
  const rows = ceilUnits(deckWidth * 12, Math.max(.1, boardWidth + gap));
  const linearFeet = rows * deckLength;
  const adjustedLinearFeet = linearFeet * (1 + waste / 100);
  const boards = ceilUnits(adjustedLinearFeet, Math.max(.1, boardLength));
  const budget = boards * boardPrice;
  return {
    title: "Deck board estimate",
    metrics: [
      ["Board rows", `${rows} row${rows === 1 ? "" : "s"}`],
      ["Base linear footage", `${linearFeet.toFixed(0)} ft`],
      ["Linear footage with waste", `${adjustedLinearFeet.toFixed(0)} ft`],
      ["Boards to buy", `${boards} board${boards === 1 ? "" : "s"}`],
      ["Board budget", formatMoney(budget)]
    ],
    summary: `Plan for about ${boards} board${boards === 1 ? "" : "s"}. Add framing, fasteners, railing, stairs, blocking, flashing, and delivery separately.`
  };
}

function baseboardResult(form) {
  const length = numberValue(form, "length", 12);
  const width = numberValue(form, "width", 10);
  const openings = numberValue(form, "openings", 6);
  const waste = numberValue(form, "waste", 10);
  const pieceLength = numberValue(form, "pieceLength", 8);
  const piecePrice = numberValue(form, "piecePrice", 14);
  const perimeter = Math.max(0, 2 * (length + width) - openings);
  const adjustedLength = perimeter * (1 + waste / 100);
  const pieces = ceilUnits(adjustedLength, Math.max(.1, pieceLength));
  const budget = pieces * piecePrice;
  return {
    title: "Baseboard estimate",
    metrics: [
      ["Net perimeter", `${perimeter.toFixed(1)} ft`],
      ["Length with waste", `${adjustedLength.toFixed(1)} ft`],
      ["Piece length", `${pieceLength.toFixed(0)} ft`],
      ["Pieces to buy", `${pieces} piece${pieces === 1 ? "" : "s"}`],
      ["Trim budget", formatMoney(budget)]
    ],
    summary: `Buy about ${pieces} piece${pieces === 1 ? "" : "s"} of trim. Add extra for scarf joints, outside corners, mistakes, and future repairs.`
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
  const calculators = {
    paint: paintResult,
    tile: tileResult,
    curtain: curtainResult,
    flooring: flooringResult,
    drywall: drywallResult,
    wallpaper: wallpaperResult,
    concrete: concreteResult,
    mulch: mulchResult,
    deck: deckResult,
    baseboard: baseboardResult
  };
  const result = (calculators[tool] || flooringResult)(form);
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
