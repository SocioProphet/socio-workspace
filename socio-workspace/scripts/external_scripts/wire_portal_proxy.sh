#!/usr/bin/env bash
set -euo pipefail
ROOT="$(pwd)"
VITE_TS="$ROOT/socioprophet-web/vite.config.ts"
VITE_JS="$ROOT/socioprophet-web/vite.config.js"

TARGET=""
if [ -f "$VITE_TS" ]; then TARGET="$VITE_TS"; fi
if [ -z "$TARGET" ] && [ -f "$VITE_JS" ]; then TARGET="$VITE_JS"; fi

if [ -z "$TARGET" ]; then
  echo "vite.config.ts/js not found under socioprophet-web/; skipping."
  exit 0
fi

cp "$TARGET" "${TARGET}.bak"

# If the file already contains /api proxy, do nothing.
if grep -q "/api" "$TARGET" && grep -q "/ws" "$TARGET"; then
  echo "Proxy appears present; nothing to do."
  exit 0
fi

# Insert a server.proxy block if missing, or augment existing one.
if grep -q "server:" "$TARGET"; then
  # naive augmentation: add /api and /ws entries after 'server:' line
  awk '
    BEGIN{added=0}
    /server:\s*\{/ && added==0 {
      print;
      print "    proxy: {";
      print "      \x27/api\x27: { target: \x27http://localhost:5175\x27, changeOrigin: true, rewrite: p => p.replace(/^\\/api/, \x27\x27) },";
      print "      \x27/ws\x27:  { target: \x27ws://localhost:5175\x27, ws: true, changeOrigin: true }";
      print "    },";
      added=1;
      next
    }
    {print}
  ' "$TARGET" > "${TARGET}.tmp"
else
  # add a full server block near top-level export
  awk '
    /defineConfig\(\{/ && added==0 {
      print;
      print "  server: {";
      print "    proxy: {";
      print "      \x27/api\x27: { target: \x27http://localhost:5175\x27, changeOrigin: true, rewrite: p => p.replace(/^\\/api/, \x27\x27) },";
      print "      \x27/ws\x27:  { target: \x27ws://localhost:5175\x27, ws: true, changeOrigin: true }";
      print "    }";
      print "  },";
      added=1;
      next
    }
    {print}
  ' "$TARGET" > "${TARGET}.tmp"
fi

mv "${TARGET}.tmp" "$TARGET"
echo "✓ Patched $TARGET with /api and /ws proxies → :5175"
