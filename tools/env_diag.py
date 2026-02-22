from pathlib import Path

p = Path(".env")
b = p.read_bytes()
print("env_path=", str(p.resolve()))
print("bytes_len=", len(b))
print("starts_with_BOM=", b.startswith(b"\xef\xbb\xbf"))

txt = b.decode("utf-8", errors="replace")
lines = [ln for ln in txt.splitlines() if ln.strip() and not ln.strip().startswith("#")]
keys = [ln.split("=", 1)[0] for ln in lines if "=" in ln]

print("keys=", keys)
print("has_TELEGRAM_BOT_TOKEN=", "TELEGRAM_BOT_TOKEN" in keys)
print("has_DATABASE_URL=", "DATABASE_URL" in keys)
