#!/bin/sh

# Regenerates /config.js from the container environment on every start.
#
# The frontend is shipped as a prebuilt image, so VITE_* variables are baked in at build time by CI
# and an operator who pulls the image cannot change them. This writes the same settings to a small
# file the SPA reads at boot, making them configurable through `environment:` in docker-compose
# without rebuilding anything.
#
# A variable that is unset emits no key, so the frontend keeps its compiled-in default.

set -e

CONFIG_FILE="${CONFIG_FILE:-/var/www/copilot/config.js}"

# Escape for embedding in a double-quoted JS string literal.
js_escape() {
    printf '%s' "$1" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g' | tr -d '\n\r'
}

emit_entry() {
    # $1 = key, $2 = value. Skips unset/empty values so the default survives.
    [ -n "$2" ] || return 0
    printf '\t%s: "%s",\n' "$1" "$(js_escape "$2")" >> "$CONFIG_FILE"
}

printf 'window.__COPILOT_CONFIG__ = {\n' > "$CONFIG_FILE"
emit_entry documentationLabel "${VITE_DOCUMENTATION_LABEL}"
emit_entry documentationUrl "${VITE_DOCUMENTATION_URL}"
emit_entry contactLabel "${VITE_CONTACT_LABEL}"
emit_entry contactUrl "${VITE_CONTACT_URL}"
printf '}\n' >> "$CONFIG_FILE"

echo "Runtime config written to ${CONFIG_FILE}"
