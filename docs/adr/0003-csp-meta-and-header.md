# 0003 – Content Security Policy aus Meta-Tag und Header

- Status: angenommen
- Datum: 2026-11-07

## Kontext

KONZEPT 8.3 sieht eine CSP als HTTP-Header in Caddy vor (`script-src 'self'`, keine `unsafe-*`).
SvelteKit fügt in jede vorgerenderte Seite ein kleines Inline-Bootstrap-Skript ein. Ein Header mit
`script-src 'self'` würde dieses Skript blockieren und die Hydration verhindern. Die Hashes ändern sich
mit jedem Build, Caddy kennt sie nicht.

Zusätzlich setzt SvelteKits Route-Announcer (`kit/src/runtime/components/root.svelte`) ein
`style`-Attribut. Das ist mit `style-src 'self'` ohne `unsafe-inline` nicht erlaubt.

## Entscheid

1. Die vollständige CSP wird von SvelteKit im Hash-Modus erzeugt (`csp.mode: 'hash'` in
   `web/vite.config.ts`) und als `<meta http-equiv>` in jede Seite geschrieben. Sie enthält genau die
   Hashes der eigenen Inline-Skripte, sonst nur `'self'`.
2. Caddy sendet zusätzlich einen CSP-Header mit den Direktiven, die ein Meta-Tag nicht ausdrücken kann
   oder die als Absicherung doppelt gelten sollen: `frame-ancestors 'none'; base-uri 'self';
   form-action 'self'; object-src 'none'`. Browser setzen beide Richtlinien durch, es gilt die
   Schnittmenge.
3. Das Inline-Style des Route-Announcers bleibt blockiert. `web/src/routes/layout.css` stellt dieselbe
   «visually hidden»-Darstellung über das eigene Stylesheet her. Der Playwright-Test lässt genau diese
   eine CSP-Meldung zu (über ihren Hash). Jede andere Verletzung lässt den Test scheitern.

## Konsequenzen

- Keine `unsafe-*`-Quellen. Die Policy passt automatisch zu jedem Build.
- Die Browser-Konsole zeigt pro Seitenaufruf eine erwartete CSP-Meldung zum Announcer. Entfernt
  SvelteKit das Inline-Style künftig, kann die Ausnahme im Test entfallen.
- Bei Mozilla Observatory zählt der Header. Weil er kein `script-src` enthält, kann die Bewertung
  tiefer ausfallen als bei einer reinen Header-CSP. In Phase 1 gegen den Live-Build prüfen. Falls nötig,
  die Hashes beim Build in eine Caddy-Datei schreiben (eigener ADR).
