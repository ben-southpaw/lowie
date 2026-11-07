# Lowie

A connected serif drawn as hand-poke tattoo dots. Every letter joins the next.

Free and open source under the [SIL Open Font License 1.1](../release/OFL.txt): use it for anything, personal or commercial, and modify it. The one thing you can't do is sell the font files on their own.

![Lowie demos](../release/images/demos-sheet.png)

**[Download Lowie 0.7](https://github.com/ben-southpaw/lowie/releases/latest)** · **[Try it in your browser](https://ben-southpaw.github.io/lowie/)**

## Styles

- **Poke**: loose, mostly round dots in mixed sizes with a ragged edge; the odd one oval or doubled.
- **Poke Shaded**: a loose dotted edge with sparse, smaller dots inside.
- **Poke Line**: the outline only.

## Joins

Joins happen by themselves as you type. b, o, r, v and w hand over along the top, as in handwriting; the rest join from the foot. To make every letter join from the foot, turn on stylistic set 1, "All low joins":

- Figma: Type details > Stylistic sets
- CSS: `font-feature-settings: "ss01";`

Capitals join into the lowercase letter after them, never to each other.

## Install

- Mac: double-click a `.ttf` file from the download and choose Install.
- Windows: right-click a `.ttf` file and choose Install.
- Web: use the `.woff2` files.

```css
@font-face {
  font-family: "Lowie";
  src: url("Lowie-Poke.woff2") format("woff2");
}
```

Lowie has one weight. On headings set `font-weight: 400; font-synthesis: none;`, or the browser fakes a bold and the dots merge.

## Good to know

- Lowie is a display font. The dots read as dots from about 150px; at 30 to 150px they give a chalky, stippled texture; below 30px they merge into grey.
- Files are large (0.8 to 1 MB per style as WOFF2), because every dot is its own shape. Fine for headings and print, heavy for body text on a website.

## Characters

a to z, A to Z, accented letters for Dutch, French, German, Spanish and Portuguese, 0 to 9, punctuation and common symbols. Not yet: { } § ¢ ¥, fractions, Polish, Czech and other Central European letters.

## Source

The fonts are built from code in [`source/`](../source) (Python, fontTools, skia-pathops, Pillow).

```bash
pip install fonttools skia-pathops pillow brotli
python source/build.py --release   # writes release/fonts/
```

See [FONTLOG.txt](../release/FONTLOG.txt) for the history.

Copyright 2026 Ben Dryden.
