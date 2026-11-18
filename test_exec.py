# -*- coding: utf-8 -*-
"""
Tests fuer Dateimeister_exec.MyExecWindow (frueher
Dateimeister_messages.MyMessagesWindow).

Abgedeckt:
    * Aufbau des Fensters (Smoke-Test)
    * Radiobutton-Auswahl und Aktionswechsel (copy / delete / delrelpath)
    * delrelpath-Radiobutton: disabled wenn kein Script, enabled sonst
    * show_messages / show_errors mit und ohne Clear
    * exec_handler: die Kommandos aus dem Script werden einzeln an eine
      laufende cmd.exe geschickt (process.stdin), die Ausgabe wird aus
      process.stdout gelesen
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
# Fake-Popen fuer den neuen exec_handler
#
# Der neue exec_handler startet EINE cmd.exe und schickt die Kommandos
# aus dem Script einzeln an process.stdin. Nach jedem Kommando folgt
# die Zeile '@echo __RESULT__%ERRORLEVEL%', und der Handler liest aus
# process.stdout, bis er '__RESULT__<n>' sieht.
#
# _FakeStdin sammelt alle geschriebenen Zeilen. _FakeStdout liefert pro
# '@echo __RESULT__'-Zeile eine Ausgabezeile ('fake-output\r\n') und
# danach '__RESULT__0\r\n', damit der Handler die Schleife verlaesst.
#
# Der delrelpath-Zusatzlauf am Ende benutzt weiterhin Popen mit
# shell=True und communicate(); der Fake unterstuetzt beides.
# ----------------------------------------------------------------------
class _FakeStdin:
    def __init__(self):
        self.lines = []
        self.closed = False

    def write(self, s):
        self.lines.append(s)

    def flush(self):
        pass

    def close(self):
        self.closed = True


class _FakeStdout:
    """Liefert fuer jedes '@echo __RESULT__' eine Ausgabe- und eine
    Ergebniszeile. Alles andere (echo-Ausgaben etc.) wird als eine
    Zeile zurueckgegeben."""
    def __init__(self, stdin):
        self._stdin = stdin
        self._queue = []

    def readline(self):
        # Sind noch Antworten aus vorherigen Writes da? -> ausgeben
        if self._queue:
            return self._queue.pop(0)

        # Sonst: die zuletzt geschriebene Zeile betrachten
        if not self._stdin.lines:
            return ""
        last = self._stdin.lines[-1]
        if last.startswith("@echo __RESULT__"):
            # Handler erwartet: erst irgendeine Zeile, dann __RESULT__0
            # (die erste Zeile ist die echo-Ausgabe des Kommandos, die
            # zweite das Ergebnis; beide werden nacheinander gelesen)
            self._queue.append("fake-output\r\n")
            self._queue.append("__RESULT__0\r\n")
            return self._queue.pop(0)
        return "\r\n"


class _FakePopen:
    """Ersetzt subprocess.Popen.

    Unterstuetzt zwei Modi, die der neue exec_handler braucht:
      1. cmd.exe mit stdin=PIPE: Skript-Kommandos einzeln ausfuehren.
         -> instances[0].stdin.lines enthaelt die Kommandos.
      2. call <delrelpathscript> mit shell=True (Zusatzlauf):
         -> communicate() liefert (output, error).
    """
    instances = []

    def __init__(self, cmd, stdout=None, stderr=None, shell=False,
                 cwd=None, stdin=None, text=None, encoding=None,
                 errors=None, bufsize=None, **kwargs):
        self.cmd = cmd
        self.cwd = cwd
        self.shell = shell
        self.stdin = _FakeStdin()
        self.stdout = _FakeStdout(self.stdin)
        self.stderr = None
        self.returncode = 0
        _FakePopen.instances.append(self)

    def communicate(self):
        # Nur fuer den delrelpath-Zusatzlauf mit shell=True benutzt
        return ("fake-delrelpath-output\n", "")

    def wait(self, timeout=None):
        return 0

    def poll(self):
        return 0

    def terminate(self):
        pass

    def kill(self):
        pass


@pytest.fixture
def fake_popen(monkeypatch):
    """Stubbt subprocess.Popen in Dateimeister_exec."""
    _FakePopen.instances = []
    monkeypatch.setattr(DE.subprocess, "Popen", _FakePopen)
    yield _FakePopen
    _FakePopen.instances = []


def _written_commands(instance):
    """Alle Kommandos, die der Handler an stdin geschickt hat,
    ohne das @echo __RESULT__-Protokoll."""
    return [
        line for line in instance.stdin.lines
        if line.strip() and not line.startswith("@echo __RESULT__")
    ]


# ----------------------------------------------------------------------
# exec_handler (neuer Ansatz: eine cmd.exe, Kommandos einzeln)
# ----------------------------------------------------------------------
def test_exec_handler_copy_runs_copyscript(
        exec_window_factory, fake_popen):
    """Bei action == 'copy' wird genau eine cmd.exe gestartet und das
    copyscript Zeile fuer Zeile ausgefuehrt."""
    win = exec_window_factory(with_delrelpath=True)
    win.rb_value.set("copy")
    win.script_select()
    win.exec_handler()

    assert len(fake_popen.instances) == 1
    instance = fake_popen.instances[0]
    # cmd.exe als Kommando, kein shell=True
    assert instance.cmd[0].lower().endswith("cmd.exe")
    assert instance.shell is False
    # Es wurden Kommandos an stdin geschickt (die Fake-Skripte enthalten
    # mindestens ein 'echo'-Kommando).
    commands = _written_commands(instance)
    assert any("echo" in c.lower() for c in commands)
    # Label_script zeigt das copyscript
    assert win.copyscript in win.Label_script.cget("text")


def test_exec_handler_delete_without_delrelpath_runs_once(
        exec_window_factory, fake_popen):
    """action == 'delete', cb_delrelpath_var == 0: keine zusaetzliche
    delrelpath-Ausfuehrung, Label zeigt nur das deletescript."""
    win = exec_window_factory(with_delrelpath=True)
    win.rb_value.set("delete")
    win.script_select()
    win.cb_delrelpath_var.set(0)
    win.exec_handler()

    # Erste cmd.exe: deletescript
    assert len(fake_popen.instances) == 1
    assert fake_popen.instances[0].cmd[0].lower().endswith("cmd.exe")
    label_text = win.Label_script.cget("text")
    assert win.deletescript in label_text
    assert win.delrelpathscript not in label_text


def test_exec_handler_delete_with_delrelpath_runs_twice(
        exec_window_factory, fake_popen):
    """action == 'delete', cb_delrelpath_var == 1: nach der cmd.exe
    laeuft der delrelpath-Zusatzlauf per Popen(shell=True)."""
    win = exec_window_factory(with_delrelpath=True)
    win.rb_value.set("delete")
    win.script_select()
    win.cb_delrelpath_var.set(1)
    win.exec_handler()

    # Zwei Popen-Instanzen: erst cmd.exe, dann delrelpath-Shell-Aufruf
    assert len(fake_popen.instances) == 2
    first, second = fake_popen.instances
    assert first.cmd[0].lower().endswith("cmd.exe")
    assert second.shell is True
    assert win.delrelpathscript in " ".join(
        second.cmd if isinstance(second.cmd, list) else [second.cmd]
    )
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

    assert len(fake_popen.instances) == 1
    assert fake_popen.instances[0].cmd[0].lower().endswith("cmd.exe")
    label_text = win.Label_script.cget("text")
    assert win.copyscript in label_text
    assert win.delrelpathscript not in label_text


def test_exec_handler_show_messages_after_run(
        exec_window_factory, fake_popen):
    """Nach exec_handler stehen die Erfolgsmeldungen im Text_messages;
    das Text_errors bleibt leer (Fake liefert __RESULT__0)."""
    win = exec_window_factory(with_delrelpath=True)
    win.rb_value.set("copy")
    win.script_select()
    win.exec_handler()

    msgs = win.Text_messages.get("1.0", "end-1c")
    errs = win.Text_errors.get("1.0", "end-1c")
    # Der Handler schreibt pro erfolgreichem Kommando "<command>: 0"
    assert "echo" in msgs.lower()
    # Bei errorlevel 0 wird nichts in die Fehlerliste uebernommen
    assert errs.strip() == ""


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