#!/usr/bin/env bash
# Each check passes the exit status of the [[ … ]] test right before it to check().
# shellcheck disable=SC2319
# Live acceptance checks for https://politdrift.org (KONZEPT 9, phase 1).
# Usage: check-live.sh [expected-short-sha]
# Prints one line per check and a Markdown table to $GITHUB_STEP_SUMMARY (if set).
# Exit code: number of failed checks (0 = all passed).
set -uo pipefail

HOST="${HOST:-politdrift.org}"
BASE="https://${HOST}"
EXPECTED_SHA="${1:-}"
fails=0
rows=()

check() { # name, result(0/1), detail
  local name="$1" ok="$2" detail="$3" mark="✅"
  if [[ "$ok" != 0 ]]; then mark="❌"; fails=$((fails + 1)); fi
  printf '%s %-38s %s\n' "$mark" "$name" "$detail"
  rows+=("| $mark | $name | ${detail//|/\\|} |")
}

headers="$(curl -sS -D - -o /dev/null --max-time 15 "$BASE/" || true)"
hdr() { printf '%s\n' "$headers" | tr -d '\r' | awk -v k="$(echo "$1" | tr '[:upper:]' '[:lower:]')" 'BEGIN{FS=": "} tolower($1)==k {sub(/^[^:]*: /,""); print; exit}'; }

status="$(printf '%s\n' "$headers" | head -1 | tr -d '\r')"
[[ "$status" =~ \ 200 ]]; check "HTTPS / returns 200" $? "$status"

health="$(curl -fsS --max-time 10 "$BASE/healthz" 2>&1)"
[[ "$health" == "ok" ]]; check "/healthz" $? "$health"

live_sha="$(curl -fsS --max-time 10 "$BASE/version.json" | jq -r .sha 2>/dev/null || echo "?")"
if [[ -n "$EXPECTED_SHA" ]]; then
  [[ "$live_sha" == "$EXPECTED_SHA" ]]; check "version.json = main" $? "live $live_sha, main $EXPECTED_SHA"
else
  [[ "$live_sha" =~ ^[0-9a-f]{7}$ ]]; check "version.json" $? "live $live_sha"
fi

hsts="$(hdr Strict-Transport-Security)"
[[ "$hsts" == *"max-age=31536000"* && "$hsts" == *includeSubDomains* && "$hsts" == *preload* ]]
check "HSTS (1y, subdomains, preload)" $? "${hsts:-missing}"

csp="$(hdr Content-Security-Policy)"
[[ "$csp" == *"frame-ancestors 'none'"* && "$csp" != *unsafe* ]]; check "CSP header (frame-ancestors, no unsafe)" $? "${csp:-missing}"

page="$(curl -fsS --max-time 15 "$BASE/" || true)"
meta="$(printf '%s' "$page" | grep -o '<meta http-equiv="content-security-policy"[^>]*>' | head -1)"
[[ -n "$meta" && "$meta" == *"script-src 'self' 'sha256-"* && "$meta" != *unsafe* ]]
check "CSP meta (hashes, no unsafe)" $? "${meta:0:90}…"

for h in X-Frame-Options:DENY X-Content-Type-Options:nosniff Referrer-Policy:strict-origin-when-cross-origin \
  Cross-Origin-Opener-Policy:same-origin Cross-Origin-Resource-Policy:same-origin; do
  name="${h%%:*}" want="${h#*:}" got="$(hdr "$name")"
  [[ "$got" == "$want" ]]; check "$name" $? "${got:-missing}"
done

pp="$(hdr Permissions-Policy)"
[[ "$pp" == *"camera=()"* && "$pp" == *"microphone=()"* && "$pp" == *"geolocation=()"* ]]
check "Permissions-Policy" $? "${pp:-missing}"

server="$(hdr Server)$(hdr Via)"
[[ -z "$server" ]]; check "No Server/Via header" $? "${server:-absent}"

altsvc="$(hdr Alt-Svc)"
[[ "$altsvc" == *h3* ]]; check "HTTP/3 advertised (Alt-Svc)" $? "${altsvc:-missing}"

redir="$(curl -sS -o /dev/null -w '%{http_code} %{redirect_url}' --max-time 10 "http://${HOST}/methodik")"
[[ "$redir" =~ ^30[178]\ https://${HOST}/methodik$ ]]; check "HTTP → HTTPS redirect" $? "$redir"

www="$(curl -sS -o /dev/null -w '%{http_code} %{redirect_url}' --max-time 10 "https://www.${HOST}/methodik")"
[[ "$www" =~ ^30[18]\ https://${HOST}/methodik$ ]]; check "www → apex redirect" $? "$www"

cert="$(echo | openssl s_client -connect "${HOST}:443" -servername "$HOST" 2>/dev/null | openssl x509 -noout -issuer -enddate 2>/dev/null | tr '\n' ' ')"
[[ -n "$cert" ]]; check "TLS certificate" $? "$cert"

if echo | openssl s_client -connect "${HOST}:443" -servername "$HOST" -tls1_1 >/dev/null 2>&1; then
  check "TLS 1.1 rejected" 1 "TLS 1.1 handshake succeeded"
else
  check "TLS 1.1 rejected" 0 "handshake refused"
fi

nf="$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 "$BASE/does-not-exist")"
[[ "$nf" == 404 ]]; check "Unknown path → 404" $? "$nf"

sec="$(curl -fsS --max-time 10 "$BASE/.well-known/security.txt" | grep -c '^Contact:' || true)"
[[ "$sec" -ge 1 ]]; check "security.txt" $? "Contact lines: $sec"

if [[ -n "${GITHUB_STEP_SUMMARY:-}" ]]; then
  {
    echo "### Live checks: $HOST"
    echo
    echo "| | Check | Result |"
    echo "|---|---|---|"
    printf '%s\n' "${rows[@]}"
  } >>"$GITHUB_STEP_SUMMARY"
fi

echo "failed: $fails"
exit "$fails"
