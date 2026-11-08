// Lowie join shaper: a plain-JS port of the font's calt feature (ExitForms then EntryForms).
(function (root) {
  const HIGH = new Set("borvw");
  const ACC = /(acute|grave|circumflex|dieresis|tilde|ring|cedilla)$/;
  function makeShaper(font) {
    const G = font.glyphs;
    const isLower = n => !!G[n + ".medi"];
    const isCap = n => !!G[n + ".init"] && !G[n + ".medi"];
    const baseLetter = n => n.replace(ACC, "");
    const split = n => { const i = n.indexOf("."); return i < 0 ? [n, ""] : [n.slice(0, i), n.slice(i)]; };
    return function shape(text, highJoins = true) {
      const chars = Array.from(text);
      const names = chars.map(c => font.cmap[c] || (c === " " ? "space" : null));
      const g = names.slice();
      // ExitForms: a letter followed by a lowercase letter gets an exit.
      for (let i = 0; i < g.length - 1; i++) {
        const a = names[i], b = names[i + 1];
        if (!a || !b || !isLower(b)) continue;
        if (isLower(a) || isCap(a)) g[i] = a + ".init";
      }
      // EntryForms: a letter after an exiting letter gets an entry matching that exit.
      for (let i = 1; i < g.length; i++) {
        const prev = g[i - 1], cur = g[i];
        if (!prev || !cur) continue;
        const [pb, ps] = split(prev);
        let kind = null;
        if (isLower(pb) && (ps === ".init" || ps === ".medi" || ps === ".medih"))
          kind = highJoins && HIGH.has(baseLetter(pb)) ? "high" : "low";
        else if (isCap(pb) && ps === ".init") kind = "low";
        if (!kind) continue;
        const [cb, cs] = split(cur);
        if (!isLower(cb)) continue;
        if (cs === ".init") g[i] = cb + (kind === "high" ? ".medih" : ".medi");
        else if (cs === "") g[i] = cb + (kind === "high" ? ".finah" : ".fina");
      }
      return chars.map((c, i) => ({ ch: c, base: names[i], glyph: g[i] }));
    };
  }
  if (typeof module !== "undefined") module.exports = { makeShaper };
  else root.makeShaper = makeShaper;
})(this);
