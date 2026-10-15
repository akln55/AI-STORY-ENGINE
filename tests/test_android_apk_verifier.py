from io import BytesIO
from pathlib import Path
import tarfile
import zipfile

from tools.verify_android_apk import verify_apk

NATIVE_SOURCE = "android_native/arm64-v8a/libllama-server.so"
NATIVE_ENTRY = "lib/arm64-v8a/libllama-server.so"


def _elf(*, machine: int = 183, elf_type: int = 3) -> bytes:
    header = bytearray(2048)
    header[:4] = bytes((0x7F, 0x45, 0x4C, 0x46))
    header[4] = 2
    header[5] = 1
    header[16:18] = elf_type.to_bytes(2, "little")
    header[18:20] = machine.to_bytes(2, "little")
    return bytes(header)


def _make_source(root: Path, *, native: bytes | None = None) -> None:
    payloads = {
        "main.py": b"from rpg_android_app import RPGEngineApp\n",
        "rpg_android_app.py": b"print('app')\n",
        "rpg_android_file_picker.py": b"print('picker')\n",
        NATIVE_SOURCE: native if native is not None else _elf(),
    }
    for rel, data in payloads.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)


def _write_apk(source: Path, apk: Path, *, private_tar: bool = False, include_native: bool = True, duplicate_private_native: bool = False) -> None:
    private_files = [
        "main.py",
        "rpg_android_app.py",
        "rpg_android_file_picker.py",
    ]
    with zipfile.ZipFile(apk, "w") as archive:
        if private_tar:
            tar_bytes = BytesIO()
            with tarfile.open(fileobj=tar_bytes, mode="w") as payload:
                for rel in private_files:
                    payload.add(source / rel, arcname=rel)
                if duplicate_private_native:
                    payload.add(source / NATIVE_SOURCE, arcname=NATIVE_SOURCE)
            archive.writestr("assets/private.tar", tar_bytes.getvalue())
        else:
            for rel in private_files:
                archive.writestr("assets/private/" + rel, (source / rel).read_bytes())
            if duplicate_private_native:
                archive.writestr("assets/private/" + NATIVE_SOURCE, (source / NATIVE_SOURCE).read_bytes())
        if include_native:
            archive.writestr(NATIVE_ENTRY, (source / NATIVE_SOURCE).read_bytes())


def test_static_verifier_accepts_expected_apk_without_aapt(tmp_path: Path):
    source = tmp_path / "source"
    _make_source(source)
    apk = tmp_path / "app.apk"
    _write_apk(source, apk)
    assert verify_apk(source, apk) == []


def test_static_verifier_rejects_wrong_native_architecture(tmp_path: Path):
    source = tmp_path / "source"
    _make_source(source, native=_elf(machine=62))
    apk = tmp_path / "app.apk"
    _write_apk(source, apk)
    errors = verify_apk(source, apk)
    assert any("not AArch64" in item for item in errors)


def test_static_verifier_accepts_python_for_android_private_tar(tmp_path: Path):
    source = tmp_path / "source"
    _make_source(source)
    apk = tmp_path / "app.apk"
    _write_apk(source, apk, private_tar=True)
    assert verify_apk(source, apk) == []


def test_static_verifier_rejects_native_server_inside_private_payload(tmp_path: Path):
    source = tmp_path / "source"
    _make_source(source)
    apk = tmp_path / "app.apk"
    _write_apk(source, apk, private_tar=True, duplicate_private_native=True)
    errors = verify_apk(source, apk)
    assert any("incorrectly packaged in writable app-private payload" in item for item in errors)


def test_static_verifier_requires_native_library_entry(tmp_path: Path):
    source = tmp_path / "source"
    _make_source(source)
    apk = tmp_path / "app.apk"
    _write_apk(source, apk, include_native=False)
    errors = verify_apk(source, apk)
    assert any(NATIVE_ENTRY in item for item in errors)
