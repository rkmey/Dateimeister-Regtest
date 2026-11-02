# -*- coding: utf-8 -*-
"""
Tests fuer Dateimeister_exec.MyExecWindow (frueher
Dateimeister_messages.MyMessagesWindow).

Abgedeckt:
    * Aufbau des Fensters (Smoke-Test)
    * Radiobutton-Auswahl und Aktionswechsel (copy / delete / delrelpath)
    * delrelpath-Radiobutton: disabled wenn kein Script, enabled sonst
    * show_messages / show_errors mit und ohne Clear
    * exec_handler: subprocess.Popen wird mit dem richtigen Kommando
      aufgerufen
    * exec_handler: delrelpath-Zusatzlauf nur bei action == "delete"
      und gesetztem cb_delrelpath_var
"""

import pytest

import Dateimeister_exec as DE


# ----------------------------------------------------------------------
# Aufbau
# ----------------------------------------------------------------------
def test_exec_window_builds_without_error(exec_window_factory):
    """Das Fenster baut sich vollstaendig auf (alle Widgets da)."""
    win = exec_window_factory(with_delrelpath=True)
    assert win.root.winfo_exists()
    assert win.Frame_script.winfo_exists()
    assert win.Frame_messages.winfo_exists()
    assert win.Frame_errors.winfo_exists()
    assert win.Button_execute.cget("text") == "copy"


def test_exec_window_without_delrelpath_script(exec_window_factory):
    """Ohne delrelpath-Script: Radiobutton und Checkbutton sind disabled."""
    win = exec_window_factory(with_delrelpath=False)
    assert str(win.Radiobutton_delrelpathscript.cget("state")) == "disabled"
    assert str(win.Checkbutton_delrelpath.cget("state")) == "disabled"


def test_exec_window_with_delrelpath_script(exec_window_factory):
    """Mit delrelpath-Script: Radiobutton ist enabled; Checkbutton bleibt
    disabled, solange 'copy' gewaehlt ist."""
    win = exec_window_factory(with_delrelpath=True)
    assert str(win.Radiobutton_delrelpathscript.cget("state")) != "disabled"
    assert str(win.Checkbutton_delrelpath.cget("state")) == "disabled"


# ----------------------------------------------------------------------
# script_select
# ----------------------------------------------------------------------
def test_script_select_copy(exec_window_factory):
    """action wechselt auf 'copy'; der Button zeigt 'copy'."""
    win = exec_window_factory(with_delrelpath=True)
    win.rb_value.set("copy")
    win.script_select()
    assert win.action == "copy"
    assert win.Button_execute.cget("text") == "copy"
    assert str(win.Button_execute.cget("state")) != "disabled"
    assert str(win.Checkbutton_delrelpath.cget("state")) == "disabled"


def test_script_select_delete(exec_window_factory):
    """action wechselt auf 'delete'; Checkbutton wird aktiv, wenn
    delrelpath-Script vorhanden ist."""
    win = exec_window_factory(with_delrelpath=True)
    win.rb_value.set("delete")
    win.script_select()
    assert win.action == "delete"
    assert win.Button_execute.cget("text") == "delete"
    assert str(win.Button_execute.cget("state")) != "disabled"
    assert str(win.Checkbutton_delrelpath.cget("state")) != "disabled"


def test_script_select_delete_without_delrelpath(exec_window_factory):
    """action wechselt auf 'delete', aber Checkbutton bleibt disabled,
    weil kein delrelpath-Script vorhanden ist."""
    win = exec_window_factory(with_delrelpath=False)
    win.rb_value.set("delete")
    win.script_select()
    assert win.action == "delete"
    assert str(win.Checkbutton_delrelpath.cget("state")) == "disabled"


def test_script_select_delrelpath(exec_window_factory):
    """action wechselt auf 'delrelpath'; der Button ist disabled
    (View-only)."""
    win = exec_window_factory(with_delrelpath=True)
    win.rb_value.set("delrelpath")
    win.script_select()
    assert win.action == "delrelpath"
    assert win.Button_execute.cget("text") == "delrelpath"
    assert str(win.Button_execute.cget("state")) == "disabled"


# ----------------------------------------------------------------------
# show_messages / show_errors
# ----------------------------------------------------------------------
def test_show_messages_with_clear(exec_window_factory):
    win = exec_window_factory(with_delrelpath=True)
    win.show_messages("erste Zeile", True)
    win.show_messages("zweite Zeile", True)   # clear -> nur diese bleibt
    text = win.Text_messages.get("1.0", "end-1c")
    assert "zweite Zeile" in text
    assert "erste Zeile" not in text


def test_show_messages_without_clear(exec_window_factory):
    win = exec_window_factory(with_delrelpath=True)
    win.show_messages("erste Zeile", True)
    win.show_messages("zweite Zeile", False)  # kein clear -> beide
    text = win.Text_messages.get("1.0", "end-1c")
    assert "erste Zeile" in text
    assert "zweite Zeile" in text


def test_show_errors_with_clear(exec_window_factory):
    win = exec_window_factory(with_delrelpath=True)
    win.show_errors("error eins", True)
    win.show_errors("error zwei", True)
    text = win.Text_errors.get("1.0", "end-1c")
    assert "error zwei" in text
    assert "error eins" not in text


def test_show_errors_without_clear(exec_window_factory):
    win = exec_window_factory(with_delrelpath=True)
    win.show_errors("error eins", True)
    win.show_errors("error zwei", False)
    text = win.Text_errors.get("1.0", "end-1c")
    assert "error eins" in text
    assert "error zwei" in text


# ----------------------------------------------------------------------
# exec_handler
# ----------------------------------------------------------------------
class _FakePopen:
    """Ersetzt subprocess.Popen. Zeichnet Aufrufe auf, liefert
    plausible (output, error)-Paare, damit exec_handler durchlaeuft."""
    calls = []

    def __init__(self, cmd, stdout=None, stderr=None, shell=False,
                 cwd=None, **kwargs):
        self.cmd = cmd
        self.cwd = cwd
        self.shell = shell
        _FakePopen.calls.append({
            "cmd": cmd, "cwd": cwd, "shell": shell,
        })

    def communicate(self):
        return (b"fake-output", b"")


@pytest.fixture
def fake_popen(monkeypatch):
    """Stubbt subprocess.Popen in Dateimeister_exec."""
    _FakePopen.calls = []
    monkeypatch.setattr(DE.subprocess, "Popen", _FakePopen)
    yield _FakePopen
    _FakePopen.calls = []


def test_exec_handler_copy_runs_copyscript(
        exec_window_factory, fake_popen):
    """Bei action == 'copy' wird genau ein Popen mit dem copyscript
    aufgerufen."""
    win = exec_window_factory(with_delrelpath=True)
    win.rb_value.set("copy")
    win.script_select()
    win.exec_handler()

    assert len(fake_popen.calls) == 1
    call = fake_popen.calls[0]
    assert win.copyscript in call["cmd"]
    assert call["shell"] is True


def test_exec_handler_delete_without_delrelpath_runs_once(
        exec_window_factory, fake_popen):
    """action == 'delete', cb_delrelpath_var == 0: nur ein Popen-Aufruf
    (deletescript), kein delrelpath-Zusatzlauf."""
    win = exec_window_factory(with_delrelpath=True)
    win.rb_value.set("delete")
    win.script_select()
    win.cb_delrelpath_var.set(0)
    win.exec_handler()

    assert len(fake_popen.calls) == 1
    assert win.deletescript in fake_popen.calls[0]["cmd"]


def test_exec_handler_delete_with_delrelpath_runs_twice(
        exec_window_factory, fake_popen):
    """action == 'delete', cb_delrelpath_var == 1: zwei Popen-Aufrufe
    (deletescript + delrelpathscript)."""
    win = exec_window_factory(with_delrelpath=True)
    win.rb_value.set("delete")
    win.script_select()
    win.cb_delrelpath_var.set(1)
    win.exec_handler()

    assert len(fake_popen.calls) == 2
    assert win.deletescript in fake_popen.calls[0]["cmd"]
    assert win.delrelpathscript in fake_popen.calls[1]["cmd"]
    label_text = win.Label_script.cget("text")
    assert win.deletescript in label_text
    assert win.delrelpathscript in label_text


def test_exec_handler_delrelpath_flag_ignored_for_copy(
        exec_window_factory, fake_popen):
    """cb_delrelpath_var gesetzt, aber action == 'copy': kein
    delrelpath-Zusatzlauf (der ist nur fuer 'delete' gedacht)."""
    win = exec_window_factory(with_delrelpath=True)
    win.rb_value.set("copy")
    win.script_select()
    win.cb_delrelpath_var.set(1)
    win.exec_handler()

    assert len(fake_popen.calls) == 1
    assert win.copyscript in fake_popen.calls[0]["cmd"]


def test_exec_handler_show_messages_after_run(
        exec_window_factory, fake_popen):
    """Nach exec_handler stehen Output und Error im jeweiligen Textfeld."""
    win = exec_window_factory(with_delrelpath=True)
    win.rb_value.set("copy")
    win.script_select()
    win.exec_handler()

    msgs = win.Text_messages.get("1.0", "end-1c")
    errs = win.Text_errors.get("1.0", "end-1c")
    assert "fake-output" in msgs
    assert "fake-output" not in errs
    
def test_close_handler_destroys_window(exec_window_factory):
    win = exec_window_factory(with_delrelpath=True)
    win.close_handler()
    # Nach destroy() wirft winfo_exists() bei den meisten Tk-Versionen
    # einen TclError; wir behandeln beides als "weg".
    try:
        exists = win.root.winfo_exists()
    except Exception:
        exists = 0
    assert not exists

    