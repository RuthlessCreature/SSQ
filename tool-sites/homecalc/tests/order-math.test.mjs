import assert from "node:assert/strict";
import test from "node:test";
import { calculateOrder, examples, orderCsv } from "../public/assets/order-math.mjs";

test("bathroom record preserves a fractional deduction and compares two quotes", () => {
  const result = calculateOrder(examples["tile-bath"]);
  assert.equal(result.net, 55.625);
  assert.equal(result.adjusted.toFixed(2), "62.30");
  assert.deepEqual(result.options.map(({ cartons, cost }) => [cartons, cost]), [[5, 290], [6, 300]]);
  assert.equal(calculateOrder({ ...examples["tile-bath"], allowance: 11 }).options[0].cartons, 4);
});

test("flooring price ranking changes across a carton boundary", () => {
  const project = examples["flooring-rooms"];
  assert.deepEqual(calculateOrder(project).options.map(({ cartons, cost }) => [cartons, cost]), [[9, 576], [9, 603]]);
  assert.deepEqual(calculateOrder({ ...project, allowance: 10.6 }).options.map(({ cartons, cost }) => [cartons, cost]), [[10, 640], [9, 603]]);
});

test("exact boundaries do not add a carton because of floating-point error", () => {
  const zones = [{ label: "Room", sign: 1, length: 16, width: 11 }];
  const project = { zones, allowance: 10, products: [{ label: "Sample", coverage: 24.2, price: 1, reference: "" }] };
  assert.equal(calculateOrder(project).options[0].cartons, 8);
  project.products[0].coverage = 24.18;
  assert.equal(calculateOrder(project).options[0].cartons, 9);
});

test("the worksheet rejects a zero net area, a missing dimension and invalid coverage", () => {
  const project = structuredClone(examples["tile-bath"]);
  assert.throws(() => calculateOrder({ ...project, zones: project.zones.slice(1) }), /greater than zero/);
  assert.throws(() => calculateOrder({ ...project, zones: [{ ...project.zones[0], length: undefined }] }), /area 1/);
  project.products[0].coverage = 0;
  assert.throws(() => calculateOrder(project), /product 1/);
});

test("CSV carries the source, original dimensions and sanitized user-entered text", () => {
  const project = structuredClone(examples["tile-bath"]);
  project.zones[0].label = '=HYPERLINK("example")';
  const csv = orderCsv(calculateOrder(project));
  assert.match(csv, /"'=HYPERLINK\(""example""\)","Include",7\.5,8,60/);
  assert.match(csv, /"Fixed vanity","Deduct",2\.5,1\.75,-4\.375/);
  assert.match(csv, /"Area including layout allowance \(sq ft\)",62\.3\r\n/);
  assert.match(csv, /digitalassets\.daltile\.com/);
});
