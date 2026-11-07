# 0006 – Build-Provenance blockiert den Deploy nicht

- Status: angenommen
- Datum: 2026-11-07

## Kontext

`build-image` erzeugt nach dem Push nach GHCR eine Build-Provenance-Attestation
(`actions/attest-build-provenance`). Diese wird in Sigstores öffentlichem Transparency-Log
(Rekor) eingetragen. Am 7. November 2026 lieferte Rekor wiederholt HTTP 500. Der Job
`build-image` schlug fehl, obwohl Build, Trivy-Scan und Push erfolgreich waren, und der erste
Deploy wurde dadurch blockiert.

`deploy.sh` prüft die Attestation nicht (die Prüfung mit `gh attestation verify` ist in
KONZEPT 8.4 nur optional vorgesehen). Die Attestation dokumentiert heute also nur die Herkunft
des Images, sie schützt den Deploy nicht.

## Entscheid

- Der Attestations-Schritt läuft mit `continue-on-error: true`.
- Schlägt er fehl, schreibt ein Folgeschritt eine Warnung ins Log und in die Job-Zusammenfassung
  (Image-Digest, Hinweis auf erneuten Lauf).
- Trivy-Scan und alle Quality-Checks bleiben blockierend.

## Konsequenzen

- Ein Ausfall von Sigstore verhindert keinen Deploy mehr.
- In seltenen Fällen geht ein Image ohne Provenance live. Die Warnung macht das sichtbar. Ein
  erneuter Lauf des Jobs holt die Attestation nach.
- **Wird die Provenance künftig auf dem VPS vor dem Deploy geprüft**, muss dieser Entscheid
  überarbeitet werden: Dann muss eine fehlende Attestation den Deploy wieder stoppen.
