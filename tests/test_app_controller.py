from engine.ai.fake import FakeAdapter
from engine.app.controller import AppController


def test_controller_uses_engine_for_commands():
    c = AppController.demo(adapter=FakeAdapter())
    out = c.submit("look")
    assert "Sleepy Village" in out


def test_controller_save_load_roundtrip(tmp_path):
    c = AppController.demo(adapter=FakeAdapter())
    c.submit("go forest")
    c.save(save_dir=tmp_path)
    restored = AppController.demo(adapter=FakeAdapter())
    restored.load(save_dir=tmp_path)
    assert restored.location_name == "Whispering Forest"


def test_controller_reports_turn():
    c = AppController.demo(adapter=FakeAdapter())
    assert c.turn == 0
    c.submit("look")
    assert c.turn == 0  # meta commands do not advance the game clock


def test_controller_dirty_tracks_mutating_turns_and_clears_on_save(tmp_path):
    c = AppController.demo(adapter=FakeAdapter())
    assert c.dirty is False
    c.submit("look")
    assert c.dirty is False
    c.submit("go forest")
    assert c.dirty is True
    c.save(save_dir=tmp_path)
    assert c.dirty is False


def test_controller_load_clears_dirty_state(tmp_path):
    c = AppController.demo(adapter=FakeAdapter())
    c.submit("go forest")
    c.save(save_dir=tmp_path)
    c.submit("go village")
    assert c.dirty is True
    c.load(save_dir=tmp_path)
    assert c.dirty is False
    assert c.location_name == "Whispering Forest"


def test_controller_can_select_gemini_provider():
    c = AppController.demo(adapter=FakeAdapter())
    c.set_gemini("secret", model="gemini-test")
    assert c.provider_name == "Gemini"


def test_local_runtime_switch_keeps_previous_until_new_runtime_is_healthy(tmp_path):
    import engine.app.controller as module

    model_a = tmp_path / "a.gguf"
    model_b = tmp_path / "b.gguf"
    payload = b"GGUF" + (3).to_bytes(4, "little") + (0).to_bytes(16, "little") + b"model"
    model_a.write_bytes(payload)
    model_b.write_bytes(payload)
    binary = tmp_path / "llama-server.bin"
    binary.write_bytes(b"x" * 2048)

    class FakeRuntime:
        instances = []
        fail_next = False

        def __init__(self, config):
            self.config = config
            self.stopped = False
            FakeRuntime.instances.append(self)

        def start(self):
            if FakeRuntime.fail_next:
                FakeRuntime.fail_next = False
                raise RuntimeError("boom")
            return f"http://127.0.0.1:{self.config.port}"

        def stop(self):
            self.stopped = True

    originals = {
        "NativeLlamaServer": module.NativeLlamaServer,
        "packaged_llama_server_path": module.packaged_llama_server_path,
        "pick_free_local_port": module.pick_free_local_port,
        "default_runtime_dir": module.default_runtime_dir,
    }
    module.NativeLlamaServer = FakeRuntime
    module.packaged_llama_server_path = lambda: binary
    module.pick_free_local_port = lambda: 18081
    module.default_runtime_dir = lambda: tmp_path / "runtime"
    try:
        c = AppController.demo(adapter=FakeAdapter())
        c.set_local_model(model_a)
        first = c.local_runtime
        assert first is not None
        assert not first.stopped

        FakeRuntime.fail_next = True
        from engine.ai.llama_native_runtime import NativeLlamaRuntimeStartError
        try:
            c.set_local_model(model_b)
        except NativeLlamaRuntimeStartError:
            pass
        else:
            raise AssertionError("expected new runtime startup failure")
        assert c.local_runtime is first
        assert not first.stopped

        c.set_local_model(model_b)
        second = c.local_runtime
        assert second is not first
        assert first.stopped
        assert not second.stopped
    finally:
        module.NativeLlamaServer = originals["NativeLlamaServer"]
        module.packaged_llama_server_path = originals["packaged_llama_server_path"]
        module.pick_free_local_port = originals["pick_free_local_port"]
        module.default_runtime_dir = originals["default_runtime_dir"]
