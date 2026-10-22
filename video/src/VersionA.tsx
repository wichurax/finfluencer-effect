// The clip (English): a newspaper front page asks the question, the method follows as a short story (channels,
// AI reading a real transcript, the price check), then one light chart card per result. Paced by the voice.
import React from "react";
import { AbsoluteFill, Audio, Img, interpolate, staticFile, useCurrentFrame } from "remotion";
import timeline from "./timeline-A.json";
import { Bars, CASLON, Cloud, FPS, FRAKTUR, FRANKLIN, HEADLINE, INTER, PriceChart, SAFE, Timeline, W, clamp,
  data, ease, num, parts, position, thumbs } from "./shared";

const TL = timeline as Timeline;
const CARD = { bg: "#f3efe7", ink: "#141414", muted: "#6b675f", grid: "#cfc9bd", accent: "#d9381e", market: "#b9b4a9",
  band: "#e4dfd4" };
const PAPER = { bg: "#f1ece2", ink: "#161514", muted: "#4f4b45", faint: "#8d877c" };
const DARK = "#101113";
const HL = "#ffcd3c";

/**
 * Captions in short-form video drop the full stop, comma or colon at the end of a line: the line break already
 * ends it. Question marks stay, and so does the dot of an abbreviation such as "U.S.".
 */
const bare = (s: string) => s.replace(/(?<![A-Z]\.[A-Z])[.,:;](?=\**$)/, "");

const Subtitle: React.FC<{ t: number }> = ({ t }) => {
  const { chunk, sentence } = position(TL, t);
  // On the front page the headline is the caption.
  if (sentence.visual === "headline" || t > TL.chunks[TL.chunks.length - 1].end + 0.8) return null;
  return (
    <div style={{ position: "absolute", left: 0, right: 0, top: 1300, display: "flex", justifyContent: "center",
      paddingLeft: SAFE.left, paddingRight: W - SAFE.right }}>
      <div style={{ background: "rgba(12,12,14,0.82)", color: "#fff", fontFamily: INTER, fontWeight: 600, fontSize: 50,
        lineHeight: 1.25, padding: "16px 26px", borderRadius: 14, textAlign: "center", maxWidth: 900, textWrap: "balance" }}>
        {parts(bare(chunk.text)).map((p, i) => (
          <span key={i} style={{ color: p.hl ? HL : "#fff" }}>{p.text}</span>
        ))}
      </div>
    </div>
  );
};

/** Paper grain: static, as on real newsprint. */
const Grain: React.FC = () => (
  <svg width={W} height={1920} style={{ position: "absolute", inset: 0, mixBlendMode: "multiply", opacity: 0.16 }}>
    <filter id="grain">
      <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves={2} seed={7} />
      <feColorMatrix type="saturate" values="0" />
    </filter>
    <rect width="100%" height="100%" filter="url(#grain)" />
  </svg>
);

const body = { fontFamily: CASLON, fontSize: 23, lineHeight: 1.42, color: PAPER.ink, textAlign: "justify",
  hyphens: "auto" } as const;

/** The opening: a broadsheet front page whose banner headline asks the question. Our own masthead, no real paper's. */
const FrontPage: React.FC<{ t: number }> = ({ t }) => {
  const ex = data.examples.US;
  const push = interpolate(t, [0, 3.6], [1, 1.05], clamp);
  // Only the headline asks for attention; everything around it is quiet, readable when paused.
  return (
    <AbsoluteFill style={{ background: PAPER.bg }}>
      <AbsoluteFill style={{ transform: `scale(${push})`, transformOrigin: "50% 37%", color: PAPER.ink }}>
        <div style={{ position: "absolute", top: 238, left: 60, right: 60, display: "flex", justifyContent: "space-between",
          fontFamily: FRANKLIN, fontWeight: 600, fontSize: 15, letterSpacing: 1.5, textTransform: "uppercase",
          color: PAPER.faint }}>
          <span>Vol. I · No. 1</span>
          <span>U.S. &amp; Poland Edition</span>
        </div>
        <div style={{ position: "absolute", top: 256, left: 0, right: 0, textAlign: "center", fontFamily: FRAKTUR,
          fontSize: 56, lineHeight: 1.15, color: PAPER.muted }}>
          The Finfluencer Effect
        </div>
        <div style={{ position: "absolute", top: 334, left: 60, right: 60, color: PAPER.faint }}>
          <div style={{ borderTop: `2px solid ${PAPER.faint}`, borderBottom: `1px solid ${PAPER.faint}`, height: 3 }} />
          <div style={{ display: "flex", justifyContent: "space-between", padding: "6px 4px", fontFamily: FRANKLIN,
            fontWeight: 500, fontSize: 15, letterSpacing: 1.5, textTransform: "uppercase" }}>
            <span>Markets</span>
            <span>October 2026</span>
            <span>Analysis</span>
          </div>
          <div style={{ borderTop: `1px solid ${PAPER.faint}` }} />
        </div>
        <div style={{ position: "absolute", top: 402, left: 30, right: 30, textAlign: "center", fontFamily: HEADLINE,
          fontWeight: 900, fontSize: 168, lineHeight: 0.95, letterSpacing: -2.5, color: "#0b0a09" }}>
          Do Finance<br />YouTubers<br />Move Stock<br />Prices?
        </div>
        <div style={{ position: "absolute", top: 1072, left: 150, right: 150, textAlign: "center", fontFamily: CASLON,
          fontStyle: "italic", fontSize: 29, lineHeight: 1.35, color: PAPER.faint, textWrap: "balance" }}>
          We read {data.videos.toLocaleString("en-US")} videos from the biggest{" "}
          <span style={{ whiteSpace: "nowrap" }}>stock-picking</span> channels in the U.S. and Poland, then checked
          the prices.
        </div>
        <div style={{ position: "absolute", top: 1176, left: 60, right: 60, borderTop: `1px solid ${PAPER.faint}` }} />
        <div style={{ position: "absolute", top: 1200, left: 60, width: 620, display: "flex", flexDirection: "column",
          gap: 10 }}>
          <Img src={staticFile(`thumbs/${ex.video}.jpg`)} style={{ width: "100%", aspectRatio: "16 / 9", objectFit: "cover",
            filter: "grayscale(1) contrast(0.92) brightness(1.06)", mixBlendMode: "multiply", opacity: 0.85 }} />
          <div style={{ fontFamily: FRANKLIN, fontSize: 19, lineHeight: 1.35, color: PAPER.muted }}>
            {ex.channel} on {ex.company}: “You buy it, you hold it.”
          </div>
          <div style={{ ...body, columnCount: 2, columnGap: 30, marginTop: 6 }}>
            A stock can rise for many reasons, so each move is measured against the market as a whole: if the stock
            gains 3.1% on a day the market gains 0.2%, the difference is 2.9 points. The same videos were then moved to
            random dates {data.draws.toLocaleString("en-US")} times, to show how large a result chance alone produces.
            Only a result well outside that range counts. Each country was tested on its own: U.S. channels against
            U.S. stocks, Polish channels against companies listed in Warsaw.
          </div>
        </div>
        <div style={{ position: "absolute", top: 1200, left: 710, right: 60, borderLeft: `1px solid ${PAPER.faint}`,
          paddingLeft: 26, display: "flex", flexDirection: "column", gap: 12 }}>
          <div style={{ fontFamily: HEADLINE, fontWeight: 700, fontSize: 32, lineHeight: 1.1 }}>How the test worked</div>
          <div style={body}>
            Every week, millions of people watch stock pickers on YouTube say what to buy and what to sell. Do prices
            follow? We downloaded the transcripts of {data.videos.toLocaleString("en-US")} videos from the three largest
            channels in each country. An AI model read every one and marked each call on a listed company as bullish
            or bearish.
          </div>
          <div style={body}>
            The videos were published between October 2024 and October 2026. The test looks at the first trading
            session after each one, and at the three that followed.
          </div>
        </div>
      </AbsoluteFill>
      <AbsoluteFill style={{ background: "radial-gradient(ellipse at 50% 40%, transparent 55%, rgba(60,45,20,0.16))" }} />
      <Grain />
    </AbsoluteFill>
  );
};

/** A light chart card: a title, a line under it, and the chart. */
const Card: React.FC<{ title: string; sub?: string; children: React.ReactNode }> = ({ title, sub, children }) => (
  <AbsoluteFill style={{ background: CARD.bg }}>
    <div style={{ position: "absolute", top: SAFE.top + 40, left: 80, right: 130, display: "flex", flexDirection: "column",
      gap: 14, fontFamily: INTER }}>
      <div style={{ fontSize: 62, fontWeight: 800, color: CARD.ink, lineHeight: 1.08, letterSpacing: -1 }}>{title}</div>
      {sub && <div style={{ fontSize: 38, fontWeight: 500, color: CARD.muted }}>{sub}</div>}
    </div>
    <div style={{ position: "absolute", top: 560, left: 80, right: 80 }}>{children}</div>
    <div style={{ position: "absolute", top: 1235, left: 80, fontFamily: INTER, fontSize: 28, color: CARD.muted }}>
      Data: YouTube captions, Yahoo Finance prices, {data.period}
    </div>
  </AbsoluteFill>
);

const channels = (country: string) => data.channels.filter((c) => c.country === country);
const subs = (n: number) => (n >= 1e6 ? `${(n / 1e6).toFixed(2)}M` : `${Math.round(n / 1000)}K`);

const Channels: React.FC<{ t: number; from: number }> = ({ t, from }) => (
  <AbsoluteFill style={{ background: DARK }}>
    <div style={{ position: "absolute", top: SAFE.top + 30, left: 0, right: 0, display: "flex", justifyContent: "center",
      gap: 60, fontFamily: INTER }}>
      {["US", "PL"].map((country, col) => (
        <div key={country} style={{ display: "flex", flexDirection: "column", gap: 18, width: 360 }}>
          <div style={{ fontSize: 40, fontWeight: 800, color: "#fff", opacity: ease(t, from + col * 0.6, from + col * 0.6 + 0.3) }}>
            {country === "US" ? "U.S." : "Poland"}
          </div>
          {channels(country).map((ch, i) => {
            const at = from + col * 0.6 + 0.15 + i * 0.18;
            const id = (thumbs.top as Record<string, { id: string }>)[ch.key].id;
            return (
              <div key={ch.key} style={{ opacity: ease(t, at, at + 0.3), display: "flex", flexDirection: "column", gap: 8 }}>
                <Img src={staticFile(`thumbs/${id}.jpg`)} style={{ width: "100%", aspectRatio: "16 / 9", objectFit: "cover",
                  borderRadius: 12 }} />
                <div style={{ fontSize: 30, fontWeight: 700, color: "#fff" }}>{ch.name}</div>
                <div style={{ fontSize: 26, color: "#a8a8ad" }}>{subs(ch.subscribers)} subscribers</div>
              </div>
            );
          })}
        </div>
      ))}
    </div>
  </AbsoluteFill>
);

/** AI reading a real transcript: the words light up as it reads, the call gets marked, then tagged. */
const AiRead: React.FC<{ t: number; from: number }> = ({ t, from }) => {
  const ex = data.examples.US;
  const own = TL.chunks.filter((c) => c.sentence === TL.sentences.findIndex((s) => s.visual === "aiRead"));
  const marked = own[1].start;
  const words = ex.transcript.before.split(" ");
  const read = interpolate(t, [from + 0.3, marked - 0.2], [0, words.length], clamp);
  const mark = ease(t, marked, marked + 0.6);
  // Each tag lights up as the voice says it: a word's place in its caption's text, applied to the caption's time.
  const said = own[2];
  const plain = said.text.replace(/\*/g, "");
  const saidAt = (word: string) => said.start + ((said.end - said.start) * plain.indexOf(word)) / plain.length;
  const tags = [
    { label: "▲ BULLISH", rgb: "95,211,141", at: saidAt("bullish"), company: true },
    { label: "▼ BEARISH", rgb: "255,107,91", at: saidAt("bearish"), company: false },
  ];
  return (
    <AbsoluteFill style={{ background: DARK, fontFamily: INTER }}>
      <div style={{ position: "absolute", top: SAFE.top + 24, left: 80, right: 130, display: "flex", gap: 30,
        alignItems: "center", opacity: ease(t, from, from + 0.4) }}>
        <Img src={staticFile(`thumbs/${ex.video}.jpg`)} style={{ width: 300, aspectRatio: "16 / 9", objectFit: "cover",
          borderRadius: 10 }} />
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <div style={{ fontSize: 24, fontWeight: 700, color: "#8d8d93", letterSpacing: 2, textTransform: "uppercase" }}>
            Transcript
          </div>
          <div style={{ fontSize: 36, fontWeight: 700, color: "#fff" }}>{ex.channel}</div>
        </div>
      </div>
      <div style={{ position: "absolute", top: 500, left: 80, right: 100, fontSize: 44, fontWeight: 500, lineHeight: 1.45,
        WebkitMaskImage: "linear-gradient(to bottom, transparent 0, #000 140px)" }}>
        {words.map((w, i) => (
          <span key={i} style={{ color: i < read ? "#e4e4e8" : "#4a4b50" }}>{w} </span>
        ))}
        <span style={{ color: mark > 0.4 ? "#111" : read >= words.length ? "#fff" : "#4a4b50", fontWeight: 700,
          background: `linear-gradient(${HL}, ${HL}) no-repeat`, backgroundSize: `${mark * 100}% 100%`,
          whiteSpace: "nowrap", padding: "0 6px", borderRadius: 4 }}>
          {ex.transcript.call}
        </span>
        <span style={{ color: "#4a4b50" }}> …</span>
      </div>
      <div style={{ position: "absolute", top: 1085, left: 80, display: "flex", gap: 22, alignItems: "flex-start",
        opacity: ease(t, marked + 0.3, marked + 0.7) }}>
        {tags.map((p) => {
          const pop = ease(t, p.at, p.at + 0.35);
          return (
            <div key={p.label} style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 14 }}>
              <div style={{ fontSize: 40, fontWeight: 800, letterSpacing: 1, padding: "12px 26px", borderRadius: 999,
                border: `4px solid ${pop > 0 ? `rgb(${p.rgb})` : "#3a3b40"}`, background: `rgba(${p.rgb},${0.18 * pop})`,
                color: pop > 0 ? `rgb(${p.rgb})` : "#5c5d63", transform: `scale(${1 + 0.12 * Math.sin(Math.PI * pop)})` }}>
                {p.label}
              </div>
              {/* The example's own tag: the company sits under the one it got, so lighting both stays unambiguous. */}
              {p.company && (
                <div style={{ fontSize: 36, fontWeight: 700, color: "#fff", opacity: pop }}>{ex.company}</div>
              )}
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

const End: React.FC<{ t: number; from: number }> = ({ t, from }) => (
  <AbsoluteFill style={{ background: DARK }}>
    <div style={{ position: "absolute", top: SAFE.top + 120, left: 80, right: 130, fontFamily: INTER, display: "flex",
      flexDirection: "column", gap: 34 }}>
      <div style={{ opacity: ease(t, from, from + 0.4), fontSize: 76, fontWeight: 800, color: "#fff", lineHeight: 1.08 }}>
        U.S.: it's the news
      </div>
      <div style={{ opacity: ease(t, from + 0.5, from + 0.9), fontSize: 76, fontWeight: 800, color: HL, lineHeight: 1.08 }}>
        Poland: about{" "}{num(data.clean.PL.effect, 1)}{" "}pp
      </div>
      <div style={{ opacity: ease(t, from + 1.2, from + 1.6), fontSize: 34, color: "#a8a8ad", marginTop: 20 }}>
        Correlation, not proof · {data.videos.toLocaleString("en-US")} videos ·{" "}
        <span style={{ whiteSpace: "nowrap" }}>{data.period}</span>
      </div>
      <div style={{ opacity: ease(t, from + 1.8, from + 2.2), fontSize: 34, fontWeight: 600, color: "#fff",
        marginTop: 26, paddingTop: 26, borderTop: "2px solid #2c2d31" }}>
        Report &amp; code: link in the comments
      </div>
      {/* ElevenLabs' free plan requires this credit wherever the voice is published. */}
      <div style={{ opacity: ease(t, from + 1.8, from + 2.2), fontSize: 28, color: "#8d8d93", marginTop: -14 }}>
        Voice: elevenlabs.io
      </div>
    </div>
  </AbsoluteFill>
);

const pp = (v: number) => `${num(v)} pp`;

export const VersionA: React.FC = () => {
  const t = useCurrentFrame() / FPS;
  const { sentence } = position(TL, t);
  const from = sentence.start;
  let visual: React.ReactNode = null;
  switch (sentence.visual) {
    case "headline":
      visual = <FrontPage t={t} />;
      break;
    case "channels":
      visual = <Channels t={t} from={from} />;
      break;
    case "aiRead":
      visual = <AiRead t={t} from={from} />;
      break;
    case "priceChart":
      visual = (
        <Card title={`${data.examples.US.company} after the video`} sub={`${data.examples.US.channel} · bullish call`}>
          <PriceChart t={t} from={from + 0.2} ex="US" c={CARD} font={INTER} />
        </Card>
      );
      break;
    case "chanceCloud":
      visual = (
        <Card title="What chance looks like" sub="the same videos, moved to random days">
          <Cloud from="US" to="US" mix={0} grow={ease(t, from, from + 2)} marker={0} label="" c={CARD} font={INTER} />
        </Card>
      );
      break;
    case "usRaw":
      visual = (
        <Card title="U.S.: the real video dates" sub="stock minus market, first session after">
          <Cloud from="US" to="US" mix={0} grow={1} marker={ease(t, from + 0.3, from + 1.3)} label={pp(data.raw.US.effect)}
            c={CARD} font={INTER} />
        </Card>
      );
      break;
    case "earnings":
      visual = (
        <Card title="U.S.: where the effect sits" sub="stock minus market, in percentage points">
          <Bars t={t} from={from + 0.2} c={CARD} font={INTER} items={[
            { label: "Near quarterly earnings", value: data.earnings.near.effect, strong: true },
            { label: "Other days", value: data.earnings.away.effect },
          ]} />
        </Card>
      );
      break;
    case "usClean":
      visual = (
        <Card title="U.S. without news days" sub="within chance">
          <Cloud from="US" to="USclean" mix={ease(t, from + 0.2, from + 1.4)} grow={1} marker={1}
            label={pp(data.clean.US.effect)} c={CARD} font={INTER} />
        </Card>
      );
      break;
    case "plClean":
      visual = (
        <Card title="Poland without news days" sub="the effect stays">
          <Cloud from="USclean" to="PLclean" mix={ease(t, from + 0.1, from + 1.2)} grow={1} marker={1}
            label={pp(data.clean.PL.effect)} c={CARD} font={INTER} />
        </Card>
      );
      break;
    case "plSmall":
      visual = (
        <Card title="Poland: where it's bigger" sub="stock minus market, in percentage points">
          <Bars t={t} from={from + 0.1} c={CARD} font={INTER} max={1} items={[
            { label: "Small companies (least traded)", value: data.liquidity.small.effect, strong: true },
            { label: "Large companies (most traded)", value: data.liquidity.large.effect },
          ]} />
        </Card>
      );
      break;
    case "end":
      visual = <End t={t} from={from} />;
      break;
  }
  return (
    <AbsoluteFill style={{ background: DARK }}>
      <Audio src={staticFile(TL.audio)} />
      {visual}
      <Subtitle t={t} />
    </AbsoluteFill>
  );
};

export const DURATION_A = Math.ceil(TL.duration * FPS);
