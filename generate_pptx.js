// generate_pptx.js — Whirlpool Production Plan Summary Deck
// Usage: node generate_pptx.js <plan_data.json> <output.pptx>

const pptxgen = require("pptxgenjs");
const fs = require("fs");

const data = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const outPath = process.argv[3];

// ── Palette (Whirlpool: navy + white + gold accent)
const C = {
  navy:     "0D1F4E",
  navyMid:  "1A3370",
  blue:     "1D4ED8",
  gold:     "D4A017",
  white:    "FFFFFF",
  offwhite: "F4F6FA",
  lightBg:  "EEF2FF",
  muted:    "64748B",
  green:    "16A34A",
  greenL:   "DCFCE7",
  red:      "DC2626",
  redL:     "FEE2E2",
  amber:    "D97706",
  amberL:   "FEF3C7",
  text:     "1E293B",
};

function fmt(n) {
  return Number(n).toLocaleString("en-IN");
}
function sign(n) { return n >= 0 ? "+" : ""; }

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";  // 13.33" × 7.5"
pres.title  = `Whirlpool Production Plan — ${data.month}`;
pres.author = "Diwakar | Purchase Dept";

const W = 13.33, H = 7.5;

// ════════════════════════════════════════════════════════
// SLIDE 1 — Title
// ════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: C.navy };

  // Gold accent bar left
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 0.35, h: H, fill: { color: C.gold }, line: { color: C.gold }
  });

  // Whirlpool wordmark area (white box)
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.7, y: 0.5, w: 3.2, h: 0.9,
    fill: { color: C.white }, line: { color: C.white },
    shadow: { type: "outer", blur: 10, offset: 3, angle: 135, color: "000000", opacity: 0.2 }
  });
  s.addText("Whirlpool", {
    x: 0.7, y: 0.5, w: 3.2, h: 0.9,
    fontSize: 28, bold: true, color: C.navy, align: "center", valign: "middle",
    fontFace: "Georgia"
  });

  // Main title
  s.addText("Production Plan Review", {
    x: 0.7, y: 1.7, w: 8, h: 1.1,
    fontSize: 48, bold: true, color: C.white, fontFace: "Georgia", margin: 0
  });

  // Month subtitle
  s.addText(data.month.toUpperCase(), {
    x: 0.7, y: 2.85, w: 5, h: 0.65,
    fontSize: 26, bold: false, color: C.gold, fontFace: "Calibri", charSpacing: 5, margin: 0
  });

  // Divider
  s.addShape(pres.shapes.LINE, {
    x: 0.7, y: 3.65, w: 8.5, h: 0,
    line: { color: C.gold, width: 1.5 }
  });

  // Version dates
  const vDates = data.version_labels.join("  →  ");
  s.addText(`Plan versions: ${vDates}`, {
    x: 0.7, y: 3.85, w: 10, h: 0.4,
    fontSize: 13, color: "AABFE0", fontFace: "Calibri", margin: 0
  });

  // KPI strip at bottom
  const kpis = [
    { label: "Final Volume",      value: fmt(data.total_final), sub: "units" },
    { label: "Drift vs 1st Plan", value: `${sign(data.drift_pct)}${data.drift_pct}%`,
      sub: `${sign(data.total_final - data.total_first)}${fmt(data.total_final - data.total_first)} units`,
      color: data.drift_pct >= 0 ? C.green : C.red },
    { label: "Active SKUs",       value: String(data.n_active), sub: "in final plan" },
    { label: "New SKUs",          value: String(data.n_new),     sub: "added", color: C.green },
    { label: "Dropped SKUs",      value: String(data.n_dropped), sub: "removed", color: C.red },
  ];
  const kpiW = 2.3, kpiGap = 0.22, kpiStartX = 0.7;
  kpis.forEach((k, i) => {
    const x = kpiStartX + i * (kpiW + kpiGap);
    s.addShape(pres.shapes.RECTANGLE, {
      x, y: 4.6, w: kpiW, h: 2.4,
      fill: { color: C.navyMid }, line: { color: "2A4080" },
      shadow: { type: "outer", blur: 6, offset: 2, angle: 135, color: "000000", opacity: 0.25 }
    });
    // Left accent
    s.addShape(pres.shapes.RECTANGLE, {
      x, y: 4.6, w: 0.07, h: 2.4,
      fill: { color: k.color || C.gold }, line: { color: k.color || C.gold }
    });
    s.addText(k.label.toUpperCase(), {
      x: x + 0.18, y: 4.72, w: kpiW - 0.25, h: 0.35,
      fontSize: 9, color: "8BAEE0", fontFace: "Calibri", bold: true, charSpacing: 1, margin: 0
    });
    s.addText(k.value, {
      x: x + 0.18, y: 5.05, w: kpiW - 0.25, h: 1.0,
      fontSize: 26, bold: true, color: k.color || C.white, fontFace: "Georgia", margin: 0
    });
    s.addText(k.sub, {
      x: x + 0.18, y: 5.98, w: kpiW - 0.25, h: 0.35,
      fontSize: 11, color: "8BAEE0", fontFace: "Calibri", margin: 0
    });
  });

  // Footer
  s.addText("Whirlpool India  |  Purchase Department  |  MBA SIP", {
    x: 0.7, y: 7.15, w: 9, h: 0.25,
    fontSize: 10, color: "4A6090", fontFace: "Calibri", margin: 0
  });
}

// ════════════════════════════════════════════════════════
// SLIDE 2 — Plan Evolution
// ════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: C.offwhite };

  // Header band
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: W, h: 1.1, fill: { color: C.navy }, line: { color: C.navy }
  });
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 0.35, h: H, fill: { color: C.gold }, line: { color: C.gold }
  });
  s.addText("Plan Evolution", {
    x: 0.55, y: 0.15, w: 8, h: 0.75,
    fontSize: 30, bold: true, color: C.white, fontFace: "Georgia", margin: 0
  });
  s.addText(`${data.month}  ·  ${data.version_labels.length} versions`, {
    x: 0.55, y: 0.18, w: 12, h: 0.7,
    fontSize: 13, color: C.gold, fontFace: "Calibri", align: "right", margin: 0
  });

  // Line chart
  const chartLabels = data.version_labels;
  const chartVals   = data.version_totals;
  s.addChart(pres.charts.LINE, [{
    name: "Total Units", labels: chartLabels, values: chartVals
  }], {
    x: 0.5, y: 1.3, w: 8.5, h: 5.6,
    lineSize: 3, lineSmooth: true,
    chartColors: [C.blue],
    chartArea: { fill: { color: C.white }, roundedCorners: true },
    catAxisLabelColor: C.muted, valAxisLabelColor: C.muted,
    valGridLine: { color: "E2E8F0", size: 0.5 }, catGridLine: { style: "none" },
    showValue: true, dataLabelColor: C.text, dataLabelFontSize: 11,
    showLegend: false,
    valAxisNumFmt: '#,##0',
  });

  // Version table on the right
  const tblX = 9.2, tblY = 1.3;
  s.addText("VERSION SUMMARY", {
    x: tblX, y: tblY, w: 3.8, h: 0.4,
    fontSize: 9, bold: true, color: C.muted, charSpacing: 1, margin: 0
  });

  const nonZero = chartVals.map((v, i) => ({ v, l: chartLabels[i] })).filter(x => x.v > 0);
  let ty = tblY + 0.45;
  nonZero.forEach(({ v, l }, i) => {
    const bg = i % 2 === 0 ? C.white : C.lightBg;
    s.addShape(pres.shapes.RECTANGLE, {
      x: tblX, y: ty, w: 3.8, h: 0.52, fill: { color: bg }, line: { color: "E2E8F0" }
    });
    s.addText(l, { x: tblX + 0.12, y: ty, w: 1.6, h: 0.52, fontSize: 12, color: C.text, margin: 0 });
    s.addText(fmt(v), { x: tblX + 1.8, y: ty, w: 2, h: 0.52, fontSize: 12, bold: true, color: C.blue, align: "right", margin: 0 });
    ty += 0.54;
  });

  // Drift callout
  const driftAbs = data.total_final - data.total_first;
  const driftColor = data.drift_pct >= 0 ? C.green : C.red;
  const driftBg    = data.drift_pct >= 0 ? C.greenL : C.redL;
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: tblX, y: ty + 0.3, w: 3.8, h: 1.35,
    fill: { color: driftBg }, line: { color: driftColor }, rectRadius: 0.08
  });
  s.addText("TOTAL DRIFT", {
    x: tblX + 0.2, y: ty + 0.38, w: 3.4, h: 0.3,
    fontSize: 9, bold: true, color: C.muted, charSpacing: 1, margin: 0
  });
  s.addText(`${sign(data.drift_pct)}${data.drift_pct}%`, {
    x: tblX + 0.2, y: ty + 0.68, w: 1.8, h: 0.7,
    fontSize: 36, bold: true, color: driftColor, fontFace: "Georgia", margin: 0
  });
  s.addText(`${sign(driftAbs)}${fmt(driftAbs)} units`, {
    x: tblX + 2.1, y: ty + 0.9, w: 1.6, h: 0.4,
    fontSize: 12, color: driftColor, align: "right", margin: 0
  });
}

// ════════════════════════════════════════════════════════
// SLIDE 3 — Segment Drift
// ════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: C.offwhite };

  s.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: W, h: 1.1, fill: { color: C.navy }, line: { color: C.navy }
  });
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 0.35, h: H, fill: { color: C.gold }, line: { color: C.gold }
  });
  s.addText("Segment Analysis", {
    x: 0.55, y: 0.15, w: 8, h: 0.75, fontSize: 30, bold: true, color: C.white, fontFace: "Georgia", margin: 0
  });
  s.addText("1st Tentative → Final Plan", {
    x: 0.55, y: 0.18, w: 12, h: 0.7, fontSize: 13, color: C.gold, fontFace: "Calibri", align: "right", margin: 0
  });

  // Bar chart — grouped first vs final
  const segs     = data.segment_drift.slice().sort((a,b) => b.final - a.final);
  const segNames = segs.map(s => s.segment);
  const firstVals= segs.map(s => s.first);
  const finalVals= segs.map(s => s.final);

  s.addChart(pres.charts.BAR, [
    { name: "1st Tentative", labels: segNames, values: firstVals },
    { name: "Final Plan",    labels: segNames, values: finalVals },
  ], {
    x: 0.5, y: 1.3, w: 8.2, h: 5.7,
    barDir: "col", barGrouping: "clustered",
    chartColors: ["93C5FD", C.blue],
    chartArea: { fill: { color: C.white }, roundedCorners: true },
    catAxisLabelColor: C.muted, valAxisLabelColor: C.muted,
    valGridLine: { color: "E2E8F0", size: 0.5 }, catGridLine: { style: "none" },
    showLegend: true, legendPos: "t", legendFontSize: 11,
    catAxisLabelRotate: 320,
    valAxisNumFmt: '#,##0',
    showValue: false,
  });

  // Drift table on right
  const tx = 8.9, ty0 = 1.3;
  s.addText("DRIFT SUMMARY", {
    x: tx, y: ty0, w: 4.1, h: 0.4, fontSize: 9, bold: true, color: C.muted, charSpacing: 1, margin: 0
  });

  // Header
  s.addShape(pres.shapes.RECTANGLE, {
    x: tx, y: ty0 + 0.42, w: 4.1, h: 0.42, fill: { color: C.navy }, line: { color: C.navy }
  });
  s.addText("Segment", { x: tx + 0.1, y: ty0 + 0.42, w: 2.1, h: 0.42, fontSize: 10, bold: true, color: C.white, margin: 0 });
  s.addText("Drift %",  { x: tx + 2.2, y: ty0 + 0.42, w: 1.8, h: 0.42, fontSize: 10, bold: true, color: C.white, align: "right", margin: 0 });

  // Sort by drift_pct for the table
  const driftSorted = data.segment_drift.slice().sort((a,b) => a.drift_pct - b.drift_pct);
  let ty = ty0 + 0.86;
  const rowH = 0.38;
  driftSorted.forEach(({ segment, drift_pct }, i) => {
    const bg = i % 2 === 0 ? C.white : C.lightBg;
    const col = drift_pct >= 0 ? C.green : C.red;
    s.addShape(pres.shapes.RECTANGLE, {
      x: tx, y: ty, w: 4.1, h: rowH, fill: { color: bg }, line: { color: "E2E8F0" }
    });
    s.addText(segment, { x: tx + 0.1, y: ty, w: 2.1, h: rowH, fontSize: 10, color: C.text, margin: 0 });
    s.addText(`${sign(drift_pct)}${drift_pct}%`, {
      x: tx + 2.2, y: ty, w: 1.8, h: rowH, fontSize: 10, bold: true, color: col, align: "right", margin: 0
    });
    ty += rowH + 0.02;
    if (ty > 7.0) return; // overflow guard
  });
}

// ════════════════════════════════════════════════════════
// SLIDE 4 — Color & Star Mix
// ════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: C.offwhite };

  s.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: W, h: 1.1, fill: { color: C.navy }, line: { color: C.navy }
  });
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 0.35, h: H, fill: { color: C.gold }, line: { color: C.gold }
  });
  s.addText("Product Mix", {
    x: 0.55, y: 0.15, w: 8, h: 0.75, fontSize: 30, bold: true, color: C.white, fontFace: "Georgia", margin: 0
  });
  s.addText("Color & Weekly Loading  ·  Final Plan", {
    x: 0.55, y: 0.18, w: 12, h: 0.7, fontSize: 13, color: C.gold, fontFace: "Calibri", align: "right", margin: 0
  });

  // Color donut
  const colorLabels = data.color_mix.map(c => c.color);
  const colorVals   = data.color_mix.map(c => c.qty);
  const colorHex    = { WINE:"8B1A1A", BLUE:C.blue, GREY:"9CA3AF", BLACK:"1F2937", PURPLE:"7C3AED" };
  const pieColors   = colorLabels.map(l => colorHex[l] || "888888");

  s.addChart(pres.charts.DOUGHNUT, [{
    name: "Color Mix", labels: colorLabels, values: colorVals
  }], {
    x: 0.5, y: 1.3, w: 5.5, h: 5.5,
    chartColors: pieColors,
    chartArea: { fill: { color: C.offwhite } },
    showLabel: true, showPercent: true, showValue: false,
    showLegend: true, legendPos: "b", legendFontSize: 12,
    holeSize: 55,
    dataLabelFontSize: 12,
  });

  // Section label
  s.addText("COLOR MIX", {
    x: 0.5, y: 1.2, w: 5.5, h: 0.3,
    fontSize: 9, bold: true, color: C.muted, charSpacing: 1, align: "center", margin: 0
  });

  // Weekly loading bar chart
  s.addText("WEEKLY LOADING", {
    x: 6.3, y: 1.2, w: 6.6, h: 0.3,
    fontSize: 9, bold: true, color: C.muted, charSpacing: 1, align: "center", margin: 0
  });

  const wkAvg  = data.weekly.reduce((a,b)=>a+b,0) / 4;
  const wkCols = data.weekly.map(v => (wkAvg > 0 && v < wkAvg * 0.9) ? C.amber : C.blue);

  s.addChart(pres.charts.BAR, [{
    name: "Units", labels: ["Wk 1","Wk 2","Wk 3","Wk 4"], values: data.weekly
  }], {
    x: 6.3, y: 1.5, w: 6.6, h: 3.5,
    barDir: "col",
    chartColors: wkCols,
    chartArea: { fill: { color: C.white }, roundedCorners: true },
    catAxisLabelColor: C.muted, valAxisLabelColor: C.muted,
    valGridLine: { color: "E2E8F0", size: 0.5 }, catGridLine: { style: "none" },
    showValue: true, dataLabelColor: C.text, dataLabelFontSize: 12,
    showLegend: false,
    valAxisNumFmt: '#,##0',
  });

  // SKU status cards
  const statuses = [
    { label: "New",       val: data.n_new,       bg: C.greenL, col: C.green },
    { label: "Increased", val: data.n_increased, bg: "DCFCE7",  col: "15803D" },
    { label: "Unchanged", val: data.n_unchanged, bg: "F1F5F9",  col: C.muted },
    { label: "Decreased", val: data.n_decreased, bg: C.amberL, col: C.amber },
    { label: "Dropped",   val: data.n_dropped,   bg: C.redL,   col: C.red },
  ];
  const cw = 1.18, cg = 0.15, cx0 = 6.3;
  statuses.forEach(({ label, val, bg, col }, i) => {
    const x = cx0 + i * (cw + cg);
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x, y: 5.25, w: cw, h: 1.8,
      fill: { color: bg }, line: { color: col }, rectRadius: 0.08
    });
    s.addText(String(val), {
      x, y: 5.4, w: cw, h: 0.85,
      fontSize: 28, bold: true, color: col, fontFace: "Georgia", align: "center", margin: 0
    });
    s.addText(label, {
      x, y: 6.28, w: cw, h: 0.35,
      fontSize: 10, color: col, align: "center", bold: true, margin: 0
    });
  });
  s.addText("SKU STATUS BREAKDOWN", {
    x: cx0, y: 5.08, w: (cw + cg) * 5, h: 0.25,
    fontSize: 9, bold: true, color: C.muted, charSpacing: 1, align: "center", margin: 0
  });
}

// ════════════════════════════════════════════════════════
// SLIDE 5 — Conclusion / Takeaways
// ════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: C.navy };

  s.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 0.35, h: H, fill: { color: C.gold }, line: { color: C.gold }
  });

  s.addText("Key Takeaways", {
    x: 0.7, y: 0.5, w: 10, h: 0.9,
    fontSize: 40, bold: true, color: C.white, fontFace: "Georgia", margin: 0
  });
  s.addText(data.month.toUpperCase(), {
    x: 0.7, y: 1.45, w: 5, h: 0.45,
    fontSize: 16, color: C.gold, charSpacing: 4, margin: 0
  });

  // Build takeaway bullets dynamically from data
  const driftAbs = data.total_final - data.total_first;
  const topGainer = [...data.segment_drift].sort((a,b)=>b.drift_pct - a.drift_pct)[0];
  const topLoser  = [...data.segment_drift].sort((a,b)=>a.drift_pct - b.drift_pct)[0];
  const topColor  = data.color_mix[0];
  const wkMin     = Math.min(...data.weekly.filter(w=>w>0));
  const wkMinIdx  = data.weekly.indexOf(wkMin);
  const wkLabels  = ["Week 1","Week 2","Week 3","Week 4"];

  const bullets = [
    `Final plan volume: ${fmt(data.total_final)} units (${sign(data.drift_pct)}${data.drift_pct}% vs first tentative of ${fmt(data.total_first)}).`,
    `Highest segment uptick: ${topGainer.segment} (+${topGainer.drift_pct}%), strongest demand signal.`,
    `Biggest cut: ${topLoser.segment} (${topLoser.drift_pct}%) — may warrant supply chain review.`,
    `Dominant color: ${topColor.color} at ${fmt(topColor.qty)} units (${Math.round(topColor.qty/data.total_final*100)}% of final plan).`,
    data.weekly.some(w=>w>0)
      ? `Lightest production week: ${wkLabels[wkMinIdx]} at ${fmt(wkMin)} units — capacity available for re-load.`
      : `Weekly breakdown not yet released for this plan version.`,
    `${data.n_new} new SKUs introduced; ${data.n_dropped} dropped — net mix churn of ${data.n_new + data.n_dropped} SKUs.`,
  ];

  bullets.forEach((text, i) => {
    const y = 2.1 + i * 0.78;
    // Bullet circle
    s.addShape(pres.shapes.OVAL, {
      x: 0.7, y: y + 0.08, w: 0.28, h: 0.28,
      fill: { color: C.gold }, line: { color: C.gold }
    });
    s.addText(String(i + 1), {
      x: 0.7, y: y + 0.04, w: 0.28, h: 0.35,
      fontSize: 11, bold: true, color: C.navy, align: "center", margin: 0
    });
    s.addText(text, {
      x: 1.15, y: y, w: 11.5, h: 0.62,
      fontSize: 14, color: C.white, fontFace: "Calibri", valign: "middle", margin: 0
    });
  });

  // Footer
  s.addShape(pres.shapes.LINE, {
    x: 0.7, y: 7.05, w: 12.2, h: 0, line: { color: "2A4080", width: 1 }
  });
  s.addText("Whirlpool India  ·  Purchase Department  ·  MBA SIP  ·  Diwakar", {
    x: 0.7, y: 7.12, w: 12, h: 0.28,
    fontSize: 10, color: "4A6090", fontFace: "Calibri", margin: 0
  });
}

// ── Write file
pres.writeFile({ fileName: outPath }).then(() => {
  console.log(`✅  Saved: ${outPath}`);
});
