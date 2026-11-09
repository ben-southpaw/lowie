#!/usr/bin/env bash
# Copy Lowie Worn into the specimen site, at release/site/worn/.
# The page in worn/ is written for the artifact host, which adds the document shell;
# GitHub Pages does not, so this adds it.
#   bash worn/build-site.sh [out-dir]
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
out="${1:-$here/../release/site/worn}"
mkdir -p "$out"
{
  printf '%s\n' '<!doctype html>' '<html lang="en"><head>' \
    '<meta charset="utf-8">' \
    '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">' \
    '<meta name="description" content="One font. Everyone types on it. Each letter you type knocks dots out of it, for everybody.">' \
    '<meta property="og:title" content="Lowie Worn">' \
    '<meta property="og:description" content="One font. Everyone types on it. Each letter you type knocks dots out of it, for everybody.">' \
    '<style>:root{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}body{margin:0}img{max-width:100%}[hidden]{display:none!important}</style>' \
    '</head><body>'
  cat "$here/index.html"
  printf '\n%s\n' '</body></html>'
} > "$out/index.html"
cp "$here/shaper.js" "$here/lowie-poke.json" "$out/"
echo "built $out"
