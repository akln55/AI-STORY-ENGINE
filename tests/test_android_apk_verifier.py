from pathlib import Path
import zipfile

from tools.verify_android_apk import verify_apk


def _make_source(root: Path) -> None:
    payloads = {
        "main.py": "from rpg_android_app import RPGEngineApp\n",
        "rpg_android_app.py": "print('app')\n",
        "rpg_android_file_picker.py": "print('picker')\n",
        "android_native/arm64-v8a/llama-server.bin": (
            b"\x7fELF" + bytes([2, 1]) + b"\x00" * 10 +
            (2).to_bytes(2, "little") + (183).to_bytes(2, "little")
        ),
    }
    for rel, data in payloads.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data if isinstance(data, bytes) else data.encode())


def test_static_verifier_accepts_expected_apk_without_aapt(tmp_path: Path):
    source = tmp_path / "source"
    _make_source(source)
    apk = tmp_path / "app.apk"
    with zipfile.ZipFile(apk, "w") as archive:
        for rel in (
            "main.py",
            "rpg_android_app.py",
            "rpg_android_file_picker.py",
            "android_native/arm64-v8a/llama-server.bin",
        ):
            archive.writestr("assets/private/" + rel, (source / rel).read_bytes())
    assert verify_apk(source, apk) == []


def test_static_verifier_rejects_wrong_native_architecture(tmp_path: Path):
    source = tmp_path / "source"
    _make_source(source)
    (source / "android_native/arm64-v8a/llama-server.bin").write_bytes(
        b"\x7fELF" + bytes([2, 1]) + b"\x00" * 10 +
        (2).to_bytes(2, "little") + (62).to_bytes(2, "little")
    )
    apk = tmp_path / "app.apk"
    with zipfile.ZipFile(apk, "w") as archive:
        for path in source.rglob("*"):
            if path.is_file():
                archive.writestr("assets/private/" + path.relative_to(source).as_posix(), path.read_bytes())
    errors = verify_apk(source, apk)
    assert any("not AArch64" in item for item in errors)
