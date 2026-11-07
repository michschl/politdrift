# 0001 – Statisch vorberechnet, kein Backend im Betrieb

- Status: angenommen
- Datum: 2026-11-07

## Kontext

Politdrift zeigt Abstimmungsprofile, die sich höchstens täglich ändern. Die Website soll schnell,
günstig, sicher und vollständig nachvollziehbar sein. Jede publizierte Zahl soll einem
Repository-Stand zugeordnet werden können.

## Entscheid

- Eine Python-Pipeline (`pipeline/`) berechnet alle Profile und schreibt versionierte JSON-Dateien nach
  `data/derived/`. Änderungen kommen als Data-PR ins Repository.
- Das Frontend (`web/`, SvelteKit mit `adapter-static`) wird daraus vollständig vorgerendert.
- Ein unprivilegierter nginx-Container liefert die Dateien read-only aus, Caddy übernimmt TLS und
  Header.
- Im Betrieb gibt es keine Datenbank und keinen Applikationsserver.

## Konsequenzen

- Minimale Angriffsfläche, tiefe Kosten, sehr gute Ladezeiten.
- Jede Datenänderung ist ein Git-Commit und damit auditierbar.
- Suche und Filter laufen clientseitig über vorberechnete Indizes. Das begrenzt die Grösse der
  Indexdateien (Budget in KONZEPT 4.3).
- Ad-hoc-Abfragen oder Embeds mit Parametern brauchen später eine kleine API oder DuckDB-WASM. Das ist
  ein eigener Entscheid.
