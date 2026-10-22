// Shared pieces: fonts, timing from the voice track, and the data visuals (English).
import { loadFont as loadInter } from "@remotion/google-fonts/Inter";
import { loadFont as loadCaslon } from "@remotion/google-fonts/LibreCaslonText";
import { loadFont as loadFranklin } from "@remotion/google-fonts/LibreFranklin";
import { loadFont as loadFrankRuhl } from "@remotion/google-fonts/FrankRuhlLibre";
import { loadFont as loadFraktur } from "@remotion/google-fonts/UnifrakturMaguntia";
import React from "react";
import { Easing, interpolate } from "remotion";
import data from "./data.json";
import thumbs from "./thumbs.json";

const subsets: ("latin" | "latin-ext")[] = ["latin", "latin-ext"];
export const INTER = loadInter("normal", { weights: ["500", "600", "700", "800"], subsets }).fontFamily;
// A heavy, low-contrast news serif for the front-page headline.
export const HEADLINE = loadFrankRuhl("normal", { weights: ["700", "900"], subsets }).fontFamily;
export const CASLON = loadCaslon("normal", { weights: ["400", "700"], subsets }).fontFamily;
loadCaslon("italic", { weights: ["400"], subsets });
export const FRANKLIN = loadFranklin("normal", { weights: ["500", "600", "700"], subsets }).fontFamily;
export const FRAKTUR = loadFraktur("normal", { weights: ["400"], subsets: ["latin"] }).fontFamily;

export const FPS = 30;
export const W = 1080;
export const H = 1920;
// Feeds cover the top ~200 px, the right ~130 px and the bottom ~420 px with their own UI.
export const SAFE = { top: 236, bottom: 1500, left: 70, right: 950 };

export type Timeline = {
  name: string;
  duration: number;
  audio: string;
  sentences: { visual: string; start: number; end: number; until: number }[];
  chunks: { sentence: number; text: string; start: number; end: number }[];
};

export const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
export const ease = (t: number, a: number, b: number) =>
  interpolate(t, [a, b], [0, 1], { ...clamp, easing: Easing.out(Easing.exp) });

/** Where the voice is at time t: the sentence, its local time, and the caption chunk on screen. */
export const position = (tl: Timeline, t: number) => {
  let si = 0;
  tl.sentences.forEach((s, i) => {
    if (s.start - 0.05 <= t) si = i;
  });
  let ci = 0;
  tl.chunks.forEach((c, i) => {
    if (c.start - 0.05 <= t) ci = i;
  });
  const sentence = tl.sentences[si];
  const inSentence = tl.chunks.filter((c) => c.sentence === si);
  return { si, sentence, chunk: tl.chunks[ci], chunkInSentence: inSentence.indexOf(tl.chunks[ci]) };
};

/** "*2,000* random days" -> [{text: "2,000", hl: true}, {text: " random days", hl: false}] */
export const parts = (s: string) =>
  s.split(/(\*[^*]+\*)/).filter(Boolean).map((p) => ({ text: p.replace(/\*/g, ""), hl: p.startsWith("*") }));

export const num = (v: number, digits = 2) => `${v >= 0 ? "+" : "−"}${Math.abs(v).toFixed(digits)}`;

export type ChartColors = { ink: string; muted: string; grid: string; accent: string; market: string; band: string };

/** The example: the stock against the market around the video, 0 at the close before it. */
export const PriceChart: React.FC<{ t: number; from: number; ex: "US" | "PL"; c: ChartColors; width?: number;
  height?: number; font: string }> = ({ t, from, ex, c, width = 900, height = 620, font }) => {
  const { stock, market } = data.examples[ex];
  const lo = Math.min(...stock, ...market) - 0.8;
  const hi = Math.max(...stock, ...market) + 0.8;
  const x = (i: number) => 40 + (i / (stock.length - 1)) * (width - 80);
  const y = (v: number) => 30 + (1 - (v - lo) / (hi - lo)) * (height - 90);
  const line = (vals: number[]) => vals.map((v, i) => `${i ? "L" : "M"}${x(i)},${y(v)}`).join(" ");
  const p = ease(t, from, from + 1.6);
  const len = 2400;
  const show = ease(t, from + 1.0, from + 1.4);
  return (
    <svg width={width} height={height} style={{ overflow: "visible" }}>
      <rect x={x(2)} width={x(3) - x(2)} y={10} height={height - 70} fill={c.band} />
      <line x1={0} x2={width} y1={y(0)} y2={y(0)} stroke={c.grid} strokeWidth={3} strokeDasharray="8 8" />
      <text x={(x(2) + x(3)) / 2} y={height - 14} textAnchor="middle" fill={c.muted} fontSize={30} fontFamily={font}>
        first session after the video
      </text>
      {[{ v: market, col: c.market, w: 7 }, { v: stock, col: c.accent, w: 11 }].map(({ v, col, w }, k) => (
        <path key={k} d={line(v)} fill="none" stroke={col} strokeWidth={w} strokeLinecap="round" strokeLinejoin="round"
          strokeDasharray={len} strokeDashoffset={len * (1 - p)} />
      ))}
      <g opacity={show}>
        {/* Labels sit left of the first-session points, where the lines have not reached yet. */}
        <circle cx={x(3)} cy={y(stock[3])} r={14} fill={c.accent} />
        <text x={x(3) - 26} y={y(stock[3]) - 10} textAnchor="end" fill={c.ink} fontSize={46} fontWeight={800}
          fontFamily={font}>
          stock {num(stock[3], 1)}%
        </text>
        <circle cx={x(3)} cy={y(market[3])} r={10} fill={c.market} />
        <text x={x(3) + 26} y={y(market[3]) + 50} fill={c.muted} fontSize={36} fontWeight={600} fontFamily={font}>
          market {num(market[3], 1)}%
        </text>
      </g>
    </svg>
  );
};

const BIN = 0.025;
const XMIN = -0.6;
const XMAX = 1.0;
const histogram = (values: number[]) => {
  const n = Math.round((XMAX - XMIN) / BIN);
  const counts = new Array(n).fill(0);
  values.forEach((v) => {
    const i = Math.floor((v - XMIN) / BIN);
    if (i >= 0 && i < n) counts[i] += 1;
  });
  return counts;
};
const CLOUDS = Object.fromEntries(Object.entries(data.clouds).map(([k, v]) => [k, histogram(v.random)])) as Record<
  keyof typeof data.clouds, number[]>;
const PEAK = Math.max(...Object.values(CLOUDS).flat());

/**
 * What chance gives: a histogram of average results on random days (grey), and the real result (a line).
 * `from`/`to` morph between clouds; `marker` 0..1 slides the real result in.
 */
export const Cloud: React.FC<{ from: keyof typeof data.clouds; to: keyof typeof data.clouds; mix: number;
  grow: number; marker: number; label: string; c: ChartColors; font: string; width?: number; height?: number }> = ({
  from,
  to,
  mix,
  grow,
  marker,
  label,
  c,
  font,
  width = 920,
  height = 560,
}) => {
  const a = CLOUDS[from];
  const b = CLOUDS[to];
  const x = (v: number) => ((v - XMIN) / (XMAX - XMIN)) * width;
  const base = height - 80;
  const barW = (BIN / (XMAX - XMIN)) * width;
  const real = data.clouds[from].real + (data.clouds[to].real - data.clouds[from].real) * mix;
  const shown = Math.ceil(a.length * grow);
  return (
    <svg width={width} height={height} style={{ overflow: "visible" }}>
      {a.map((ca, i) => {
        const h = ((ca + (b[i] - ca) * mix) / PEAK) * (base - 60);
        return i < shown ? <rect key={i} x={i * barW + 1} width={barW - 2} y={base - h} height={h} fill={c.market} /> : null;
      })}
      <line x1={0} x2={width} y1={base} y2={base} stroke={c.grid} strokeWidth={3} />
      <text x={x(0)} y={base + 44} textAnchor="middle" fill={c.muted} fontSize={32} fontFamily={font}>0</text>
      <text x={x(-0.55)} y={base + 44} fill={c.muted} fontSize={30} fontFamily={font}>worse</text>
      <text x={x(0.95)} y={base + 44} textAnchor="end" fill={c.muted} fontSize={30} fontFamily={font}>better</text>
      {/* Left of the cloud, where its tails are flat. */}
      <text x={x(-0.48)} y={base - 230} textAnchor="middle" fill={c.muted} fontSize={34} fontWeight={600} fontFamily={font}
        opacity={grow}>
        random
      </text>
      <text x={x(-0.48)} y={base - 190} textAnchor="middle" fill={c.muted} fontSize={34} fontWeight={600} fontFamily={font}
        opacity={grow}>
        days
      </text>
      {marker > 0 && (
        <g opacity={marker}>
          <line x1={x(real * marker)} x2={x(real * marker)} y1={40} y2={base} stroke={c.accent} strokeWidth={8} />
          <text x={x(real * marker)} y={22} textAnchor={real > 0.6 ? "end" : "middle"} fill={c.ink} fontSize={46}
            fontWeight={800} fontFamily={font}>
            {label}
          </text>
        </g>
      )}
    </svg>
  );
};

/** Two horizontal bars with values (percentage points), growing from zero. */
export const Bars: React.FC<{ items: { label: string; value: number; strong?: boolean }[]; t: number; from: number;
  c: ChartColors; font: string; width?: number; max?: number }> = ({ items, t, from, c, font, width = 900, max = 2 }) => (
  <div style={{ display: "flex", flexDirection: "column", gap: 44, width }}>
    {items.map((it, i) => {
      const p = ease(t, from + i * 0.25, from + i * 0.25 + 0.8);
      return (
        <div key={it.label} style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <div style={{ fontFamily: font, fontSize: 40, fontWeight: 700, color: c.ink }}>{it.label}</div>
          <div style={{ display: "flex", alignItems: "center", gap: 22 }}>
            <div style={{ height: 70, width: (it.value / max) * (width - 230) * p, background: it.strong ? c.accent : c.market,
              borderRadius: 6 }} />
            <div style={{ fontFamily: font, fontSize: 56, fontWeight: 800, color: c.ink, opacity: p }}>
              {num(it.value)}
            </div>
          </div>
        </div>
      );
    })}
  </div>
);

export { data, thumbs };
