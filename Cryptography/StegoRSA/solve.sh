#!/usr/bin/env bash
set -euo pipefail

SHOW_FLAG=0
if [[ "${1:-}" == "--show-flag" ]]; then
  SHOW_FLAG=1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT_DIR="$SCRIPT_DIR/assets/text_outputs"
mkdir -p "$OUT_DIR"

log() {
  printf '[*] %s\n' "$1"
}

fail() {
  printf '[!] %s\n' "$1" >&2
  exit 1
}

need_tool() {
  command -v "$1" >/dev/null 2>&1 || fail "Missing required tool: $1"
}

basename_only() {
  basename "$1"
}

find_first() {
  local pattern
  local dir
  for dir in "$PWD" "$SCRIPT_DIR" "$SCRIPT_DIR/../.." "$SCRIPT_DIR/../../.."; do
    [[ -d "$dir" ]] || continue
    while IFS= read -r pattern; do
      [[ -n "$pattern" ]] && {
        printf '%s\n' "$pattern"
        return 0
      }
    done < <(find "$dir" -maxdepth 1 -type f "$@" | sort)
  done
  return 1
}

redacted_flag() {
  printf 'picoCTF{...redacted...}\n'
}

short_hex() {
  local file="$1"
  local hex
  hex="$(tr -d '[:space:]' < "$file" | cut -c 1-72)"
  printf '%s...\n' "$hex"
}

write_text_outputs() {
  local image_name="$1"
  local enc_name="$2"
  local comment_short="$3"
  local key_head="$4"

  {
    printf '$ ls -la\n'
    printf -- '-rw-r--r--  %s\n' "$image_name"
    printf -- '-rw-r--r--  %s\n' "$enc_name"
  } > "$OUT_DIR/01_files.txt"

  {
    printf '$ exiftool %s\n' "$image_name"
    printf 'File Name                       : %s\n' "$image_name"
    printf 'Comment                         : %s\n' "$comment_short"
  } > "$OUT_DIR/02_metadata.txt"

  {
    printf '$ exiftool -s3 -Comment %s > key.hex\n' "$image_name"
    printf '$ xxd -r -p key.hex > private.pem\n'
  } > "$OUT_DIR/03_hex_extraction.txt"

  {
    printf '$ head private.pem\n'
    printf '%s\n' "$key_head"
    printf 'MIIE...\n'
  } > "$OUT_DIR/04_private_key.txt"

  {
    printf '$ openssl pkeyutl -decrypt -inkey private.pem -in %s -out flag.txt\n' "$enc_name"
    printf '$ echo "decryption successful"\n'
    printf 'decryption successful\n'
  } > "$OUT_DIR/05_decryption.txt"

  {
    printf '$ cat flag.txt\n'
    redacted_flag
  } > "$OUT_DIR/06_flag_redacted.txt"
}

need_tool exiftool
need_tool xxd
need_tool openssl

IMAGE="$(find_first \( -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.png' \))" || fail "No image file found. Supported extensions: jpg, jpeg, png"
ENC_FILE="$(find_first -iname '*.enc')" || fail "No encrypted .enc file found"

IMAGE_NAME="$(basename_only "$IMAGE")"
ENC_NAME="$(basename_only "$ENC_FILE")"

log "Using image: $IMAGE_NAME"
log "Using encrypted file: $ENC_NAME"

log "Inspecting image metadata with exiftool"
exiftool "$IMAGE" >/dev/null

log "Extracting Comment metadata to key.hex"
exiftool -s3 -Comment "$IMAGE" > key.hex
[[ -s key.hex ]] || fail "The Comment metadata field was empty or missing"

log "Converting key.hex to private.pem"
xxd -r -p key.hex > private.pem
[[ -s private.pem ]] || fail "private.pem was not created"

FIRST_LINE="$(head -n 1 private.pem)"
case "$FIRST_LINE" in
  "-----BEGIN PRIVATE KEY-----"|"-----BEGIN RSA PRIVATE KEY-----") ;;
  *) fail "private.pem does not look like a PEM private key" ;;
esac

log "Decrypting $ENC_NAME to flag.txt"
openssl pkeyutl -decrypt -inkey private.pem -in "$ENC_FILE" -out flag.txt
[[ -s flag.txt ]] || fail "Decryption did not produce flag.txt"

COMMENT_SHORT="$(short_hex key.hex)"
write_text_outputs "$IMAGE_NAME" "$ENC_NAME" "$COMMENT_SHORT" "$FIRST_LINE"

log "Decryption complete"
if [[ "$SHOW_FLAG" -eq 1 ]]; then
  cat flag.txt
else
  redacted_flag
  log "Full flag saved locally in flag.txt. Re-run with --show-flag to print it."
fi

log "Sanitized text outputs saved in assets/text_outputs/"
