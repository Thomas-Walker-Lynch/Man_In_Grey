#!/usr/bin/env -S python3 -B
# -*- mode: python; coding: utf-8; python-indent-offset: 2; indent-tabs-mode: nil -*-
"""
Man_In_Grey

Runs composers, which place commands into one journal, and hands the journal
to a gate, which starts a bespoke journal interpreter. The journal interpreter
checks every command against its constraints, and only then executes the
journal.

A composer is a Python file defining compose(prov ,journal_iface). prov
describes where the composer is; journal_iface places commands of the file
command language: open, write and unlink.

Usage: Man_In_Grey <command> <path> [option ...]
  help | -h | --help         print this message (also printed when given no arguments)
  compose <file>             run the one composer in <file>
  orchestrate <directory>    run every composer in <directory>, breadth first, then
                             by name; the layout of the directory carries no meaning

Options:
  --input_acceptance <file>        orchestrate only: a Python file defining accept(prov),
                                   true for each file that is a composer; by default every
                                   file ending in .py whose name does not begin with a dot
  --gate <file>                    the gate to hand the journal to; by default
                                   ../Man_In_Grey_file_gate/Man_In_Grey_file_gate
  --constraints <file>             constraints for an unprivileged run, given to the
                                   journal interpreter
  --phase-0-then-stop              stop after checking the path and the filter
  --phase-1-print                  print the journal after composing
  --phase-1-then-stop              stop after composing; nothing reaches the gate
  --phase-2-print                  print the journal as the journal interpreter decoded it
  --phase-2-then-stop              stop after decoding, before any check
  --phase-2-wellformed-then-stop   stop after the named check, reporting OK when it passed
  --phase-2-constraint-then-stop
  --phase-2-validity-then-stop
  --phase-2-filesystem-then-stop

Exit status: 0 when the run did what it was asked; 1 when a check refused the
journal or a command failed to execute; 2 when the run could not start or a
composer failed.
"""

import sys ,os
sys.dont_write_bytecode = True

import datetime ,getpass ,runpy ,stat ,subprocess ,traceback
from pathlib import Path

import Journal
import FileLanguage

# The promoted layout: this file in Man_In_Grey/, beside Man_In_Grey_file_gate/.
# The same layout is staged in developer/scratchpad/made/ and promoted to consumer/.
HERE_DPATH = Path(__file__).resolve().parent
DEFAULT_GATE = HERE_DPATH.parent / "Man_In_Grey_file_gate" / "Man_In_Grey_file_gate"

STOP_OPTION = {
  "--phase-2-then-stop": "decode"
  ,"--phase-2-wellformed-then-stop": "wellformed"
  ,"--phase-2-constraint-then-stop": "constraint"
  ,"--phase-2-validity-then-stop": "validity"
  ,"--phase-2-filesystem-then-stop": "filesystem"
}
FLAG = {"--phase-0-then-stop" ,"--phase-1-print" ,"--phase-1-then-stop" ,"--phase-2-print"} | set(STOP_OPTION)
VALUE = {"--input_acceptance" ,"--gate" ,"--constraints"}
COMMAND = ("compose" ,"orchestrate")


# --------------------------------------------------------------------------------
# provenance

class Provenance:
  """
  Where a composer is. Given to the acceptance filter and to compose().
  """
  __slots__ = (
    "composer_root_dpath"
    ,"composer_abs_fpath"
    ,"composer_rel_fpath"
    ,"composer_dir_dpath"
    ,"implied_fname"
    ,"process_user"
    ,"cwd_dpath"
  )

  def __init__(self ,composer_root ,composer_path):
    self.composer_root_dpath = composer_root.resolve()
    self.composer_abs_fpath = composer_path.resolve()
    self.composer_rel_fpath = self.composer_abs_fpath.relative_to(self.composer_root_dpath)
    self.composer_dir_dpath = self.composer_abs_fpath.parent
    name = self.composer_abs_fpath.name
    if name.endswith(".py"):
      name = name[:-3]
    self.implied_fname = name
    self.process_user = getpass.getuser()
    self.cwd_dpath = Path.cwd().resolve()


# --------------------------------------------------------------------------------
# the phases

def default_accept(prov):
  name = prov.composer_rel_fpath.name
  return name.endswith(".py") and not name.startswith(".")

def accept_function(filter_path):
  if filter_path is None:
    return default_accept
  env = runpy.run_path(str(filter_path))
  function = env.get("accept")
  if not callable(function):
    raise RuntimeError(f"{filter_path} defines no accept(prov)")
  return function

def composer_list(composer_root ,accept):
  """The accepted files of the composer directory, breadth first, then by name. Symbolic links to directories are not followed."""
  found = []
  for dirpath ,dirnames ,filenames in os.walk(composer_root):
    dirnames[:] = sorted(d for d in dirnames if not os.path.islink(os.path.join(dirpath ,d)))
    for name in filenames:
      path = Path(dirpath ,name)
      if not stat.S_ISREG(path.stat().st_mode):
        continue
      prov = Provenance(composer_root ,path)
      if accept(prov):
        found.append((len(prov.composer_rel_fpath.parts) ,prov.composer_rel_fpath.as_posix() ,prov))
  found.sort(key=lambda t: (t[0] ,t[1]))
  return [t[2] for t in found]

def compose_all(composer_root ,prov_list):
  """Run each composer into one journal. Raises RuntimeError naming the composer that failed."""
  journal = Journal.Journal(FileLanguage.NAME)
  journal_iface = FileLanguage.JournalInterface(journal ,Path.cwd())
  for prov in prov_list:
    rel = prov.composer_rel_fpath.as_posix()
    journal.composer = rel
    try:
      env = runpy.run_path(str(prov.composer_abs_fpath))
      compose = env.get("compose")
      if not callable(compose):
        raise RuntimeError("defines no compose(prov ,journal_iface)")
      compose(prov ,journal_iface)
    except Journal.JournalError as error:
      raise RuntimeError(f"{rel}: {error}")
    except RuntimeError as error:
      raise RuntimeError(f"{rel}: {error}")
    except Exception:
      raise RuntimeError(f"{rel}: the composer raised an error\n{traceback.format_exc()}")
  journal.composer = None
  journal.meta = {
    "composed_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
    ,"process_user": getpass.getuser()
    ,"host": os.uname().nodename
    ,"composer_root": str(composer_root.resolve())
    ,"composer_list": [p.composer_rel_fpath.as_posix() for p in prov_list]
  }
  return journal

def run(command ,path ,input_acceptance ,gate ,constraints ,flag ,stop_after):
  path = Path(path)
  if command == "compose":
    if input_acceptance:
      print("error: --input_acceptance is for orchestrate; compose runs the one file it is given" ,file=sys.stderr)
      return 2
    if not path.is_file():
      print(f"error: the composer {path} is not a file" ,file=sys.stderr)
      return 2
    composer_root = path.resolve().parent
  else:
    if not path.is_dir():
      print(f"error: {path} is not a directory" ,file=sys.stderr)
      return 2
    composer_root = path
  try:
    accept = accept_function(Path(input_acceptance) if input_acceptance else None)
  except Exception as error:
    print(f"error: acceptance filter: {error}" ,file=sys.stderr)
    return 2
  if "--phase-0-then-stop" in flag:
    print(f"phase 0: OK, {command} {path.resolve()}")
    return 0

  try:
    if command == "compose":
      prov_list = [Provenance(composer_root ,path)]
    else:
      prov_list = composer_list(composer_root ,accept)
    journal = compose_all(composer_root ,prov_list)
  except Exception as error:
    print(f"error: {error}" ,file=sys.stderr)
    return 2
  if "--phase-1-print" in flag:
    journal.print()
  if "--phase-1-then-stop" in flag:
    return 0

  gate_path = Path(gate) if gate else DEFAULT_GATE
  if not os.access(gate_path ,os.X_OK):
    print(f"error: the gate {gate_path} is missing; in the developer role, build and promote it" ,file=sys.stderr)
    return 2
  command = [str(gate_path)]
  if constraints:
    command += ["--constraints" ,str(Path(constraints).resolve())]
  if "--phase-2-print" in flag:
    command.append("--print")
  if stop_after:
    command += ["--stop-after" ,stop_after]
  return subprocess.run(command ,input=journal.encode()).returncode


# --------------------------------------------------------------------------------
# command line

def print_help():
  print(__doc__.strip())
  return 0

def CLI(argv=None):
  argv = sys.argv[1:] if argv is None else argv
  if not argv or argv[0] in ("help" ,"-h" ,"--help"): return print_help()
  command ,rest = argv[0] ,argv[1:]
  if command not in COMMAND:
    print(f"Error: unknown command '{command}'." ,file=sys.stderr)
    print_help()
    return 2
  if not rest or rest[0].startswith("--"):
    print(f"Error: {command} is given a {'file' if command == 'compose' else 'directory'} first." ,file=sys.stderr)
    return 2
  path ,rest = rest[0] ,rest[1:]
  value ,flag = {} ,set()
  i = 0
  while i < len(rest):
    word = rest[i]
    if word in VALUE and i + 1 < len(rest):
      value[word] = rest[i + 1]; i += 2
    elif word in FLAG:
      flag.add(word); i += 1
    else:
      print(f"Error: unknown or incomplete option '{word}'." ,file=sys.stderr)
      return 2
  stop = [STOP_OPTION[f] for f in flag if f in STOP_OPTION]
  if len(stop) > 1:
    print("Error: give at most one --phase-2-...-then-stop option." ,file=sys.stderr)
    return 2
  return run(
    command ,path ,value.get("--input_acceptance") ,value.get("--gate") ,value.get("--constraints")
    ,flag ,stop[0] if stop else None
  )


if __name__ == "__main__":
  sys.exit(CLI())
