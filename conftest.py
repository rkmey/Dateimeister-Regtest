# -*- coding: utf-8 -*-
"""
conftest.py - zentrale Fixtures für die Dateimeister-Regressionstests.

Verzeichnislayout (relativ zu dieser Datei):

    regtest/
        conftest.py
        test_camera_dialog.py
        test_fsimage.py
        test_fsvideo.py
        artifacts/              <- alles, was die Tests erzeugen
            datadir/
                daten/config/
                daten/cmd/
                daten/temp/
            images/
            xml/
            ini/
            logs/

Die Tests schreiben NIE ins Dateimeister-Programmverzeichnis und nie
in den echten Config-Baum. Alles landet unter artifacts/.

Wichtig für unbeaufsichtigte Läufe (Nachtlauf):
    * messagebox.showinfo / showwarning / showerror werden global gemockt
    * tools.info_box wird global gemockt
    * nach jedem Test wird geprüft, ob noch Tk-Toplevel offen sind
      und ggf. eine Warnung mit Testname + Fenstertitel geloggt

Voraussetzungen:
    pip install pytest pytest-timeout pillow
    Auf Linux: xvfb-run pytest
"""

import os
import sys
import shutil
import textwrap
import tkinter as tk

import pytest


# ----------------------------------------------------------------------
# Pfade
# ----------------------------------------------------------------------
REGTest_DIR    = os.path.dirname(os.path.abspath(__file__))
TESTDATEN_DIR  = os.path.dirname(REGTest_DIR)
ARTIFACTS_DIR  = os.path.join(REGTest_DIR, "artifacts")

PROGRAM_DIR = os.environ.get(
    "DATEIMEISTER_HOME",
    os.path.join(os.path.dirname(TESTDATEN_DIR), "Dateimeister"),
)

if PROGRAM_DIR not in sys.path:
    sys.path.insert(0, PROGRAM_DIR)

print(f"[conftest] PROGRAM_DIR  = {PROGRAM_DIR}")
print(f"[conftest] ARTIFACTS    = {ARTIFACTS_DIR}")


# ----------------------------------------------------------------------
# Globale Mocks: messagebox + tools.info_box
# ----------------------------------------------------------------------
_messagebox_calls = []


def _make_mb_stub(kind):
    def _stub(*args, **kwargs):
        _messagebox_calls.append((kind, args, kwargs))
        return "ok"
    return _stub


@pytest.fixture(autouse=True)
def _global_messagebox_mock(monkeypatch):
    import tkinter.messagebox as mb
    _messagebox_calls.clear()
    monkeypatch.setattr(mb, "showinfo", _make_mb_stub("info"))
    monkeypatch.setattr(mb, "showwarning", _make_mb_stub("warning"))
    monkeypatch.setattr(mb, "showerror", _make_mb_stub("error"))
    yield _messagebox_calls


@pytest.fixture(autouse=True)
def _global_info_box_mock(monkeypatch):
    import tools
    calls = []

    def _stub(nachricht, level="info"):
        calls.append((nachricht, level))

    monkeypatch.setattr(tools, "info_box", _stub)
    yield calls


# ----------------------------------------------------------------------
# Artefakt-Verzeichnisse
# ----------------------------------------------------------------------
@pytest.fixture(scope="session", autouse=True)
def ensure_artifacts_dirs():
    for sub in (
        "datadir/daten/config",
        "datadir/daten/cmd",
        "datadir/daten/temp",
        "images",
        "xml",
        "ini",
        "logs",
    ):
        os.makedirs(os.path.join(ARTIFACTS_DIR, sub), exist_ok=True)
    yield


# ----------------------------------------------------------------------
# Per-Test-Sandbox
# ----------------------------------------------------------------------
class _Sandbox:
    def __init__(self, d):
        self.__dict__.update(d)

    def __getitem__(self, k):
        return self.__dict__[k]

    def __repr__(self):
        return f"<Sandbox {self.root}>"


@pytest.fixture
def sandbox(request):
    test_name = request.node.name
    module_name = request.node.module.__name__
    if module_name.startswith("test_"):
        module_name = module_name[len("test_"):]

    root = os.path.join(ARTIFACTS_DIR, module_name, test_name)
    if os.path.isdir(root):
        shutil.rmtree(root)

    paths = {
        "root":    root,
        "datadir": os.path.join(root, "datadir"),
        "config":  os.path.join(root, "datadir", "daten", "config"),
        "cmd":     os.path.join(root, "datadir", "daten", "cmd"),
        "temp":    os.path.join(root, "datadir", "daten", "temp"),
        "images":  os.path.join(root, "images"),
        "xml":     os.path.join(root, "xml"),
        "ini":     os.path.join(root, "ini"),
        "logs":    os.path.join(root, "logs"),
    }
    for p in paths.values():
        os.makedirs(p, exist_ok=True)

    return _Sandbox(paths)


# ----------------------------------------------------------------------
# Test-XMLs
# ----------------------------------------------------------------------
MINIMAL_XML = textwrap.dedent("""\
    <?xml version="1.0" encoding="iso-8859-1"?>
    <dateimeister>
      <camera name="DIATISCH" usedate="20260101-00:00:00">
        <type name="JPEG">
          <suffix name="JPG"><process_image process="JPEG"/></suffix>
          <suffix name="JPEG"><process_image process="JPEG"/></suffix>
          <subdir subdir="Diatisch"/>
        </type>
      </camera>
    </dateimeister>
""")

INCOMPLETE_XML = textwrap.dedent("""\
    <?xml version="1.0" encoding="iso-8859-1"?>
    <dateimeister>
      <camera name="TESTCAM" usedate="20260101-00:00:00">
        <type name="JPEG">
          <suffix name="JPG"/>
          <subdir subdir="test"/>
        </type>
      </camera>
    </dateimeister>
""")


@pytest.fixture
def tmp_xml(sandbox):
    import tools
    xml_file = os.path.join(sandbox.xml, "dateimeister_configfiles.xml")
    with open(xml_file, "w", encoding="iso-8859-1") as f:
        f.write(MINIMAL_XML)

    old = getattr(tools.Globals, "config_files_xml", None)
    tools.Globals.config_files_xml = xml_file
    try:
        yield xml_file
    finally:
        tools.Globals.config_files_xml = old


@pytest.fixture
def tmp_xml_incomplete(sandbox):
    import tools
    xml_file = os.path.join(sandbox.xml, "dateimeister_configfiles_incomplete.xml")
    with open(xml_file, "w", encoding="iso-8859-1") as f:
        f.write(INCOMPLETE_XML)

    old = getattr(tools.Globals, "config_files_xml", None)
    tools.Globals.config_files_xml = xml_file
    try:
        yield xml_file
    finally:
        tools.Globals.config_files_xml = old


@pytest.fixture
def empty_xml(sandbox):
    import tools
    xml_file = os.path.join(sandbox.xml, "empty_configfiles.xml")
    with open(xml_file, "w", encoding="iso-8859-1") as f:
        f.write('<?xml version="1.0" encoding="iso-8859-1"?>\n<dateimeister/>\n')
    old = getattr(tools.Globals, "config_files_xml", None)
    tools.Globals.config_files_xml = xml_file
    try:
        yield xml_file
    finally:
        tools.Globals.config_files_xml = old


# ----------------------------------------------------------------------
# Testbild, Testvideo, Test-RAW
# ----------------------------------------------------------------------
@pytest.fixture
def test_image(sandbox):
    """Erzeugt ein kleines PNG-Testbild in der Sandbox und liefert den Pfad."""
    from PIL import Image
    img_path = os.path.join(sandbox.images, "test.png")
    img = Image.new("RGB", (64, 48), color=(200, 100, 50))
    img.save(img_path)
    return img_path


@pytest.fixture
def test_video(sandbox):
    """Erzeugt eine leere Datei mit .mp4-Endung. Sie ist nicht abspielbar,
    aber das genuegt, weil subprocess.Popen und MpvIPC im Test gestubbt sind."""
    video_path = os.path.join(sandbox.images, "test.mp4")
    with open(video_path, "wb") as f:
        f.write(b"")
    return video_path


@pytest.fixture
def test_raw(sandbox):
    """Erzeugt eine leere Datei mit .nef-Endung. Sie ist nicht lesbar,
    aber das genuegt, weil rawpy_loader im Test gestubbt wird."""
    raw_path = os.path.join(sandbox.images, "test.nef")
    with open(raw_path, "wb") as f:
        f.write(b"")
    return raw_path


# ----------------------------------------------------------------------
# Mini-Thumbnail fuer MyFSImage / MyFSVideo
#
# process_type ist die einzige Typinformation. Sie entspricht dem
# <process_image process="..."/> aus der Kamera-Konfiguration:
#     "JPEG"     -> STILL
#     "USE_JPEG" -> STILL (mit Fallback auf RAW in der Detailansicht)
#     "VIDEO"    -> VIDEO
#     "RAW"      -> RAW
# ----------------------------------------------------------------------
class MiniThumbnail:
    """Minimaler Ersatz fuer tools.MyThumbnail.

    MyFSImage und MyFSVideo rufen im Konstruktor und in den
    Event-Handlern nur diese Methoden auf:
        - getState / setState
        - get_process_type / set_process_type
        - is_video / is_raw
        - getShowfile / getFile
        - get_filectime
        - get_filesize
        - metadata (Attribut)
    """
    def __init__(self, file, process_type=None, state=1, metadata=None,
                 showfile=None):
        from datetime import datetime
        self._file = file
        self._showfile = showfile
        self._state = state
        self._process_type = process_type.upper() if process_type else None
        mts = os.stat(file).st_mtime
        self._ctime = datetime.fromtimestamp(mts).strftime('%Y-%m-%d %H:%M')
        self._size = os.stat(file).st_size / (1024.0 * 1024.0)
        if metadata is not None:
            self.metadata = metadata
        else:
            self.metadata = {
                "EXIF": {"Camera Model": "TestCam"},
                "File": {"Size": str(os.stat(file).st_size)},
                "Video": {},
                "GPS": {},
                "General": {},
            }
        self.state_setter_calls = []

    def getState(self):
        return self._state

    def setState(self, state, caller=None):
        changed = (state != self._state)
        self._state = state
        self.state_setter_calls.append(state)
        return changed

    def getFile(self):
        return self._file

    def getShowfile(self):
        return self._showfile if self._showfile is not None else self._file

    def is_video(self):
        return self._process_type == "VIDEO"

    def is_raw(self):
        return self._process_type == "RAW"

    def get_process_type(self):
        return self._process_type

    def set_process_type(self, t):
        self._process_type = t.upper() if t else None

    def get_filectime(self):
        return self._ctime

    def get_filesize(self):
        return self._size


@pytest.fixture
def mini_thumbnail(test_image):
    """STILL-Thumbnail (process_type=JPEG)."""
    import tools
    return MiniThumbnail(test_image, process_type="JPEG",
                         state=tools.INCLUDE)


@pytest.fixture
def mini_thumbnail_no_imagetype(test_image):
    """MiniThumbnail ohne process_type (weder RAW noch VIDEO noch USE_JPEG)."""
    import tools
    return MiniThumbnail(test_image, process_type=None,
                         state=tools.INCLUDE)


@pytest.fixture
def video_thumbnail(test_video):
    """MiniThumbnail fuer eine Videodatei, mit Video-Metadaten."""
    import tools
    metadata = {
        "Format": {"duration": "10.0", "size": "0"},
        "Video 0": {"codec_name": "h264", "width": "1920", "height": "1080"},
        "Audio 0": {"codec_name": "aac", "channels": "2"},
    }
    return MiniThumbnail(test_video, process_type="VIDEO",
                         state=tools.INCLUDE, metadata=metadata)


@pytest.fixture
def video_thumbnail_empty_metadata(test_video):
    """MiniThumbnail fuer ein Video, mit leeren Metadaten."""
    import tools
    return MiniThumbnail(test_video, process_type="VIDEO",
                         state=tools.INCLUDE, metadata={})


@pytest.fixture
def raw_thumbnail(test_raw):
    """MiniThumbnail fuer eine RAW-Datei, mit RAW-Metadaten."""
    import tools
    metadata = {
        "RAW": {"Camera": "Nikon Z7", "ISO": "400"},
        "File": {"Size": "0"},
    }
    return MiniThumbnail(test_raw, process_type="RAW",
                         state=tools.INCLUDE, metadata=metadata)


@pytest.fixture
def raw_thumbnail_use_jpeg(test_raw):
    """MiniThumbnail, das aussieht wie STILL, aber process_type=USE_JPEG
    hat. Entspricht dem Fall, in dem der Canvas keinen Begleit-JPEG
    gefunden hat und ein blaues Rechteck gezeichnet wurde. is_raw() ist
    False; MyFSImage soll anhand von process_type selbst herausfinden,
    dass die Datei eigentlich RAW ist."""
    import tools
    return MiniThumbnail(test_raw, process_type="USE_JPEG",
                         state=tools.INCLUDE)


# ----------------------------------------------------------------------
# Fake rawpy_loader
# ----------------------------------------------------------------------
class FakeRawpyLoader:
    """Ersetzt das Modul rawpy_loader in sys.modules.

    Zeichnet Aufrufe auf und liefert einfache PIL-Images.
    """
    def __init__(self, fail_full=False, embedded_returns_none=False):
        from PIL import Image
        self._Image = Image
        self.fail_full = fail_full
        self.embedded_returns_none = embedded_returns_none
        self.embedded_calls = []
        self.full_calls = []
        self.metadata_calls = []
        self.all_exif_calls = []

    def load_raw_embedded(self, file):
        self.embedded_calls.append(file)
        if self.embedded_returns_none:
            return None
        return self._Image.new("RGB", (32, 24), color=(100, 150, 200))

    def load_raw_full(self, file):
        self.full_calls.append(file)
        if self.fail_full:
            raise RuntimeError("Fake failure in load_raw_full")
        return self._Image.new("RGB", (400, 300), color=(200, 100, 50))

    def load_raw_metadata(self, file):
        self.metadata_calls.append(file)
        return {"RAW": {"Camera": "Nikon Z7", "ISO": "400"}}

    def load_raw_all_exif(self, file):
        self.all_exif_calls.append(file)
        return {"EXIF": {"Model": "Nikon Z7",
                         "DateTimeOriginal": "2026:01:01 12:00:00"}}


@pytest.fixture
def fake_rawpy_loader(monkeypatch):
    """Setzt ein Fake-Modul rawpy_loader in sys.modules."""
    fake = FakeRawpyLoader()
    monkeypatch.setitem(sys.modules, "rawpy_loader", fake)
    return fake


@pytest.fixture
def fake_rawpy_loader_failing(monkeypatch):
    """Wie fake_rawpy_loader, aber load_raw_full wirft eine Exception."""
    fake = FakeRawpyLoader(fail_full=True)
    monkeypatch.setitem(sys.modules, "rawpy_loader", fake)
    return fake


@pytest.fixture
def fake_rawpy_loader_no_embedded(monkeypatch):
    """Wie fake_rawpy_loader, aber load_raw_embedded liefert None.

    Fuer den Test, dass MyFSImage bei USE_JPEG ohne Begleit-JPEG und
    ohne RAW eine Warnung zeigt und das Fenster nicht oeffnet.
    """
    fake = FakeRawpyLoader(embedded_returns_none=True)
    monkeypatch.setitem(sys.modules, "rawpy_loader", fake)
    return fake


# ----------------------------------------------------------------------
# Globals
# ----------------------------------------------------------------------
@pytest.fixture
def globals_event_manager():
    import tools
    old = tools.Globals.eventManager
    tools.Globals.eventManager = tools.EventManager()
    try:
        yield tools.Globals.eventManager
    finally:
        tools.Globals.eventManager = old


@pytest.fixture
def globals_screen():
    import tools
    old_w = tools.Globals.screen_width
    old_h = tools.Globals.screen_height
    tools.Globals.screen_width = 1280
    tools.Globals.screen_height = 1024
    try:
        yield (1280, 1024)
    finally:
        tools.Globals.screen_width = old_w
        tools.Globals.screen_height = old_h


@pytest.fixture
def globals_datadir(sandbox):
    import tools
    old = {
        "datadir": getattr(tools.Globals, "datadir", None),
        "config_files_subdir": getattr(tools.Globals, "config_files_subdir", None),
        "cmd_files_subdir": getattr(tools.Globals, "cmd_files_subdir", None),
        "temp_files_subdir": getattr(tools.Globals, "temp_files_subdir", None),
        "temp_files_path": getattr(tools.Globals, "temp_files_path", None),
        "uncomment": getattr(tools.Globals, "uncomment", None),
    }
    tools.Globals.datadir = sandbox.datadir
    tools.Globals.config_files_subdir = "daten/config"
    tools.Globals.cmd_files_subdir = "daten/cmd"
    tools.Globals.temp_files_subdir = "daten/temp"
    tools.Globals.temp_files_path = sandbox.temp
    tools.Globals.uncomment = "@REM"
    try:
        yield sandbox.datadir
    finally:
        for k, v in old.items():
            setattr(tools.Globals, k, v)


# ----------------------------------------------------------------------
# Tk-Root (Session-Scope)
# ----------------------------------------------------------------------
@pytest.fixture(scope="session")
def tk_root():
    try:
        root = tk.Tk()
    except tk.TclError as e:
        pytest.skip(f"Kein Display verfügbar: {e}")
    root.withdraw()
    try:
        yield root
    finally:
        try:
            root.destroy()
        except tk.TclError:
            pass


# ----------------------------------------------------------------------
# Undo/Redo-Mock
# ----------------------------------------------------------------------
class FakeUndoRedoCamera:
    def __init__(self, debug=False):
        self.debug = debug
        self.processid_akt = 0
        self.processid_high = 0
        self.processid_incr = 10
        self.list_processids = []
        self.stack_processids = []

    def reset(self):
        self.processid_akt = 0
        self.processid_high = 0
        self.list_processids = []
        self.stack_processids = []

    def historize_process(self, text=None):
        self.processid_high += self.processid_incr
        self.processid_akt = self.processid_high
        self.list_processids.append(self.processid_akt)

    def get_processid_akt(self):
        return self.processid_akt

    def process_undo(self):
        if len(self.list_processids) <= 1:
            return False, self.processid_akt, -1
        undone = self.list_processids[-1]
        self.stack_processids.append(undone)
        self.list_processids.pop()
        self.processid_akt = self.list_processids[-1]
        return True, self.processid_akt, undone

    def process_redo(self):
        if len(self.stack_processids) < 1:
            return False, self.processid_akt, -1
        predecessor = self.list_processids[-1]
        redone = self.stack_processids[-1]
        self.list_processids.append(redone)
        self.stack_processids.pop()
        self.processid_akt = self.list_processids[-1]
        return True, self.processid_akt, predecessor

    def endis_buttons(self):
        return (1 if len(self.list_processids) > 1 else 0,
                1 if len(self.stack_processids) > 0 else 0)


@pytest.fixture
def fake_ur(monkeypatch):
    import Undo_Redo
    monkeypatch.setattr(Undo_Redo, "Undo_Redo_Camera", FakeUndoRedoCamera)
    return FakeUndoRedoCamera


# ----------------------------------------------------------------------
# Dummy-Main
# ----------------------------------------------------------------------
class DummyMain:
    def __init__(self):
        self.debug_p = False
        self.dict_cameras = {}
        self.dict_subdirs = {}
        self.dict_process_image = {}
        self.get_camera_xml_calls = []

    def get_camera_xml(self, camera=None):
        import dateimeister_config_xml as DX
        import tools
        self.get_camera_xml_calls.append(camera)
        cam = (camera or "").upper()
        dict_cameras = DX.get_cameras_types_suffixes(tools.Globals.config_files_xml)
        dict_s = dict(DX.get_subdirs_per_camera(tools.Globals.config_files_xml).get(cam, {}))
        dict_pi = {}
        for type_name, suffix_dict in DX.get_process_image_per_camera(
                tools.Globals.config_files_xml).get(cam, {}).items():
            for suffix_name, process in suffix_dict.items():
                dict_pi[suffix_name] = process
        return dict_cameras, dict_s, dict_pi


@pytest.fixture
def dummy_main():
    return DummyMain()


# ----------------------------------------------------------------------
# Silence-Fixtures
# ----------------------------------------------------------------------
@pytest.fixture
def silence_messageboxes(_global_messagebox_mock):
    return _global_messagebox_mock


@pytest.fixture
def silence_tooltips(monkeypatch):
    import Tooltip as TT

    class _FakeToolTip:
        def __init__(self, *a, **kw):
            pass

        def update(self, *a, **kw):
            pass

    monkeypatch.setattr(TT, "ToolTip", _FakeToolTip)
    return _FakeToolTip


# ----------------------------------------------------------------------
# mpv-Stubs fuer MyFSVideo
# ----------------------------------------------------------------------
class FakePopen:
    """Ersetzt subprocess.Popen. Tut so, als waere ein Prozess gestartet."""
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.terminated = False

    def terminate(self):
        self.terminated = True

    def poll(self):
        return None   # laeuft noch


class FakeMpvIPC:
    """Ersetzt MpvIPC. Liefert plausible Werte und zeichnet Kommandos auf."""
    def __init__(self, pipe_name=None, timeout_connect=8.0):
        self.pipe_name = pipe_name
        self.commands = []
        self.properties = {
            "time-pos": 0.0,
            "pause": False,
            "duration": 10.0,
            "volume": 100,
            "mute": False,
        }

    def command(self, cmd_list, timeout=3.0):
        self.commands.append(cmd_list)
        if len(cmd_list) >= 1 and cmd_list[0] == "screenshot-to-file":
            if len(cmd_list) >= 2:
                path = cmd_list[1]
                try:
                    with open(path, "wb") as f:
                        f.write(b"\x89PNG\r\n\x1a\n")
                except OSError:
                    pass
        return {"error": "success"}

    def get_property(self, name):
        return self.properties.get(name)

    def set_property(self, name, value):
        self.properties[name] = value
        return {"error": "success"}

    def toggle_pause(self):
        self.properties["pause"] = not self.properties.get("pause", False)
        return self.command(["cycle", "pause"])

    def seek(self, amount, mode="relative"):
        return self.command(["seek", amount, mode])

    def close(self):
        pass


@pytest.fixture
def fake_mpv(monkeypatch):
    """Ersetzt subprocess.Popen und MpvIPC in Dateimeister_FSVideo."""
    import subprocess
    import Dateimeister_FSVideo as FSV

    monkeypatch.setattr(subprocess, "Popen", FakePopen)
    monkeypatch.setattr(FSV, "MpvIPC", FakeMpvIPC)

    def fake_generate_thumbnails(self, n, thumb_height):
        self.duration = 10.0
        return []

    monkeypatch.setattr(FSV.MyFSVideo, "generate_thumbnails",
                        fake_generate_thumbnails)

    def fake_poll_position(self):
        return

    monkeypatch.setattr(FSV.MyFSVideo, "_poll_position", fake_poll_position)

    return FakeMpvIPC


# ----------------------------------------------------------------------
# Window-Cleanup-Hook
# ----------------------------------------------------------------------
def pytest_runtest_teardown(item, nextitem):
    try:
        root = tk._default_root
        if root is None:
            return
        leftovers = []
        for child in root.winfo_children():
            if isinstance(child, tk.Toplevel):
                try:
                    title = child.title()
                except Exception:
                    title = "<unknown>"
                leftovers.append((title, child))
        if leftovers:
            titles = ", ".join(repr(t) for t, _ in leftovers)
            print(f"\n[teardown-warning] {item.nodeid}: offene Toplevel-Fenster: {titles}")
    except Exception:
        pass
        
        
# ----------------------------------------------------------------------
# MiniThumbnail: is_broken / set_broken ergaenzen
#
# display_duplicate() in Dateimeister_Duplicates.py ruft
# thumbnail.is_broken() und myimage.set_broken(...) auf.
# Die Basisklasse MiniThumbnail (oben) hat diese Methoden nicht.
# Wir ergaenzen sie hier zentral, damit alle bestehenden Fixtures
# (mini_thumbnail, raw_thumbnail, video_thumbnail, ...) sie erben.
# ----------------------------------------------------------------------
def _mini_thumbnail_is_broken(self):
    return self._broken

def _mini_thumbnail_set_broken(self, b):
    self._broken = bool(b)

# Bei jeder neuen Instanz _broken initialisieren. Wir haengen uns an
# __init__ der bestehenden Klasse, damit wir MiniThumbnail oben nicht
# anfassen muessen.
_MiniThumbnail_orig_init = MiniThumbnail.__init__

def _mini_thumbnail_init(self, *args, **kwargs):
    self._broken = False
    _MiniThumbnail_orig_init(self, *args, **kwargs)

MiniThumbnail.__init__ = _mini_thumbnail_init
MiniThumbnail.is_broken = _mini_thumbnail_is_broken
MiniThumbnail.set_broken = _mini_thumbnail_set_broken


# ----------------------------------------------------------------------
# Dummy-Support-Caller fuer MyDuplicates
# ----------------------------------------------------------------------
class DummySupportCaller:
    """Minimaler Ersatz fuer Dateimeister_support im MyDuplicates-Test.

    MyDuplicates ruft:
        caller.button_duplicates.config(state=...)
        caller.win_duplicates = None
        caller.stop_all_players()
    """
    def __init__(self, tk_root):
        self.win_duplicates = None
        self.stop_all_players_calls = 0
        # echtes Tk-Widget, damit .config(state=...) funktioniert
        self.button_duplicates = tk.Button(tk_root, text="duplicates")

    def stop_all_players(self):
        self.stop_all_players_calls += 1


@pytest.fixture
def dummy_support_caller(tk_root):
    return DummySupportCaller(tk_root)


# ----------------------------------------------------------------------
# Globals fuer MyDuplicates
# ----------------------------------------------------------------------
@pytest.fixture
def duplicates_globals(sandbox):
    """Setzt Globals.imagetype, dict_duplicates, dict_thumbnails, outdir.

    Liefert ein dict mit den Quelldateien einer synthetischen Dublette,
    damit der Test weiss, welche Dateien er in Globals.dict_thumbnails
    erwarten kann:

        {
            "target": "CALL_IMG_0001.JPG",
            "sources": [path1, path2, path3],
        }
    """
    import tools

    # drei Testbilder erzeugen (JPEG-Thumbnails)
    from PIL import Image
    sources = []
    for i in range(3):
        p = os.path.join(sandbox.images, f"src_{i}.jpg")
        Image.new("RGB", (32, 24), color=(i * 80, 100, 50)).save(p)
        sources.append(p)

    target = "CALL_IMG_0001.JPG"
    imagetype = "JPEG"

    old = {
        "imagetype": tools.Globals.imagetype,
        "dict_duplicates": tools.Globals.dict_duplicates,
        "dict_thumbnails": tools.Globals.dict_thumbnails,
        "outdir": tools.Globals.outdir,
    }

    tools.Globals.imagetype = imagetype
    tools.Globals.dict_duplicates = {imagetype: {target: list(sources)}}
    tools.Globals.dict_thumbnails = {imagetype: {}}
    tools.Globals.outdir = "/tmp/duplicates_target"

    # Fuer jede Quelldatei ein MiniThumbnail in dict_thumbnails legen.
    for p in sources:
        tools.Globals.dict_thumbnails[imagetype][p] = MiniThumbnail(
            p, process_type="JPEG", state=tools.INCLUDE
        )

    try:
        yield {"target": target, "sources": sources, "imagetype": imagetype}
    finally:
        tools.Globals.imagetype = old["imagetype"]
        tools.Globals.dict_duplicates = old["dict_duplicates"]
        tools.Globals.dict_thumbnails = old["dict_thumbnails"]
        tools.Globals.outdir = old["outdir"]


# ----------------------------------------------------------------------
# Duplicates-Fenster
# ----------------------------------------------------------------------
@pytest.fixture
def duplicates_window(
        tk_root, dummy_support_caller, duplicates_globals, globals_event_manager,
        silence_tooltips):
    """Baut ein MyDuplicates-Fenster mit vorbereiteten Globals.

    Cleanup via close_handler(). Die Fixture liefert ein Tupel
    (window, caller, duplicates_info):

        window           - das MyDuplicates-Objekt
        caller           - der DummySupportCaller
        duplicates_info  - dict aus duplicates_globals (target, sources, imagetype)
    """
    import Dateimeister_Duplicates as DD
    window = DD.MyDuplicates(caller=dummy_support_caller, debug=False)
    try:
        yield window, dummy_support_caller, duplicates_globals
    finally:
        try:
            window.close_handler()
        except Exception:
            pass
            
            