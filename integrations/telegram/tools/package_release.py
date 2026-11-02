"""Create a portable ZIP using an explicit public-file allowlist."""
import hashlib
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
FILES = [
    "configure_meta.py", "meta_server.py", "meta_doctor.py", "setup-meta-windows.cmd", "start-meta-windows.cmd",
    "just_ai/meta_config.py", "just_ai/meta_channels.py", "docs/META_CHANNELS.md", "tests/test_meta.py",
    ".env.example", ".gitignore", "requirements.txt", "requirements-dev.txt", "README.md", "VALIDATION.md",
    "bot.py", "configure.py", "doctor.py", "activate.py", "activate-windows.cmd", "setup-termux.sh", "start-termux.sh",
    "just_ai/__init__.py", "just_ai/config.py", "just_ai/catalog.py", "just_ai/store.py",
    "just_ai/provider.py", "just_ai/ui.py", "just_ai/handlers.py", "just_ai/runtime.py", "just_ai/atlas.py", "docs/ATLAS_TELEGRAM.md",
    "tests/test_bot.py", "tests/test_async_smoke.py", "setup-windows.ps1", "start-windows.ps1", "docs/INSTRUCTIONS.md", "docs/BOTFATHER.txt", "tools/package_release.py",
    "just_ai/shopify_config.py", "just_ai/shopify_commands.py", "just_ai/shopify_api.py", "just_ai/shopify_controls.py",
    "configure_shopify.py", "shopify_doctor.py", "activate-shopify-windows.cmd", "docs/SHOPIFY_TELEGRAM.md", "tests/test_shopify.py",
]


def main():
    target = ROOT.parent / "deliverables"
    target.mkdir(exist_ok=True)
    archive = target / "just-ai-bot-v2.zip"
    manifest = []
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        for name in FILES:
            source = ROOT / name
            data = source.read_bytes()
            bundle.writestr("just-ai-bot-v2/" + name, data)
            manifest.append(hashlib.sha256(data).hexdigest() + "  " + name)
        bundle.writestr("just-ai-bot-v2/SHA256SUMS.txt", "\n".join(manifest) + "\n")
    with zipfile.ZipFile(archive) as bundle:
        assert bundle.testzip() is None
        assert len(bundle.namelist()) == len(FILES) + 1
        for name in bundle.namelist():
            assert Path(name).name not in (".env", "telegram.env", "openai.env")
            assert not any(part in ("data", "venv", ".venv", "__pycache__") for part in Path(name).parts)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    (target / "just-ai-bot-v2.sha256").write_text(digest + "  " + archive.name + "\n", encoding="ascii")
    print(f"Archive: {archive}\nPublic entries: {len(FILES) + 1}\nBytes: {archive.stat().st_size}\nSHA256: {digest}")


if __name__ == "__main__":
    main()
