from __future__ import annotations
import json, tempfile, zipfile
from pathlib import Path
from contextlib import contextmanager

@contextmanager
def raises(exc, match=None):
    try:
        yield
    except exc as caught:
        if match is not None and match not in str(caught):
            raise AssertionError(f"expected exception message to contain {match!r}, got {caught!r}")
        return
    raise AssertionError(f"expected {exc!r} to be raised")

from engine.scenario.errors import ScenarioError
from engine.scenario.manager import ScenarioManager
DEMO=Path(__file__).resolve().parent.parent/'scenarios'/'demo-bootstrap'
def make_zip(root):
 a=root/'demo.rpgscenario.zip'
 with zipfile.ZipFile(a,'w',zipfile.ZIP_DEFLATED) as z:
  for p in DEMO.rglob('*'):
   if p.is_file(): z.write(p,p.relative_to(DEMO).as_posix())
 return a
def test_install_list_load_remove_round_trip():
 root=Path(tempfile.mkdtemp()); a=make_zip(root); m=ScenarioManager(root/'installed'); p=m.install(a)
 assert p.scenario_id=='demo-bootstrap'; assert m.list_installed()[0].chapter_count==1; assert m.load('demo-bootstrap').name=='Demo Bootstrap'; assert m.remove('demo-bootstrap'); assert m.list_installed()==()
def test_duplicate_install_requires_replace():
 root=Path(tempfile.mkdtemp()); a=make_zip(root); m=ScenarioManager(root/'installed'); m.install(a)
 with raises(ScenarioError,match='already installed'): m.install(a)
def test_replace_updates_index():
 root=Path(tempfile.mkdtemp()); a=make_zip(root); m=ScenarioManager(root/'installed'); m.install(a); m.install(a,replace=True); assert len(m.list_installed())==1
def test_zip_traversal_is_rejected_before_install():
 root=Path(tempfile.mkdtemp()); a=root/'evil.zip'
 with zipfile.ZipFile(a,'w') as z:
  z.writestr('../escape.txt','bad'); z.writestr('manifest.json',json.dumps({'pack_format':2,'scenario_id':'evil','name':'Evil','version':'1'})); z.writestr('world.json',json.dumps({'character':{},'locations':{}}))
 m=ScenarioManager(root/'installed')
 with raises(ScenarioError): m.install(a)
 assert not (root/'escape.txt').exists()

def test_save_binds_scenario_configuration(tmp_path):
    from engine.app.controller import AppController
    from engine.scenario.loader import load_scenario
    pack = load_scenario(DEMO)
    app = AppController.demo()
    app.start_scenario(pack, mode="sequential", start_chapter=1)
    app.save("scenario", save_dir=tmp_path)
    app.load("scenario", save_dir=tmp_path)
    assert app.scenario_config is not None
    assert app.scenario_config.scenario_id == pack.scenario_id


def test_replace_keeps_old_installation_when_index_commit_fails(tmp_path):
    root = tmp_path / "root"
    archive = make_zip(tmp_path)
    manager = ScenarioManager(root / "installed")
    manager.install(archive)
    old = manager.list_installed()[0]
    original = manager._write_index_entry
    def fail(*args, **kwargs):
        raise ScenarioError("simulated index write failure")
    manager._write_index_entry = fail
    try:
        with raises(ScenarioError, match="simulated index write failure"):
            manager.install(archive, replace=True)
    finally:
        manager._write_index_entry = original

    current = manager.list_installed()
    assert len(current) == 1
    assert current[0].path == old.path
    assert Path(old.path).exists()


def test_remove_keeps_installation_when_index_commit_fails(tmp_path):
    root = tmp_path / "root"
    archive = make_zip(tmp_path)
    manager = ScenarioManager(root / "installed")
    manager.install(archive)
    old = manager.list_installed()[0]
    original = manager._write_index
    def fail(*args, **kwargs):
        raise ScenarioError("simulated remove index failure")
    manager._write_index = fail
    try:
        with raises(ScenarioError, match="simulated remove index failure"):
            manager.remove("demo-bootstrap")
    finally:
        manager._write_index = original

    assert manager.list_installed()[0].path == old.path
    assert Path(old.path).exists()
