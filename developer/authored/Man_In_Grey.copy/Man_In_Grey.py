#!/usr/bin/env -S python3 -B
# -*- mode: python; coding: utf-8; python-indent-offset: 2; indent-tabs-mode: nil -*-
"""
Man_In_Grey

The orchestrator. It runs composers, which place instructions into one journal,
and invokes a gate with the journal on its standard input. The gate starts
the guard, which checks the journal against its constraints, and, when the
guard passes the journal, the interpreter, which executes it.

A composer is a Python file defining compose(prov ,journal_iface). prov
describes where the composer is; journal_iface places instructions of the
gate's instruction language. The orchestrator learns the language from the
gate's flags, and loads the module named for it: the file language from
FileLanguage.py, emplace_bio from EmplaceBioLanguage.py.

Usage: Man_In_Grey <command> <path> [option ...]
  help | -h                  print this message (also printed when given no arguments)
  orchestrate <path>         <path> is a composer file, or a composer directory; every
                             file in a composer directory is a composer, and they run
                             depth first, in order of name at each level

Options:
  gate <file>                the gate to invoke; by default
                             ../Man_In_Grey_gate/Man_In_Grey_file_gate
  print                      print the journal after composing
  compose_only               stop after composing; nothing reaches the gate
  check_only                 have the gate run the guard and not the interpreter

Every composer, and every directory from / down to it, is to be owned by the
gate invoking account or by root, and writable by no other account. Symbolic
links in a composer directory are refused.

Exit status: 0 when the run did what it was asked; 1 when the guard refused
the journal or an instruction failed to execute; 2 when the run could not start,
a composer failed, or the gate, guard or interpreter could not run.
"""

import sys ,os
sys.dont_write_bytecode = True

import datetime ,importlib ,pwd ,re ,runpy ,stat ,subprocess ,traceback
from pathlib import Path

import Journal

# The promoted layout: this file in Man_In_Grey/, beside Man_In_Grey_gate/.
# The same layout is staged in developer/scratchpad/made/ and promoted to consumer/.
HERE_DPATH = Path(__file__).resolve().parent
DEFAULT_GATE = HERE_DPATH.parent / "Man_In_Grey_gate" / "Man_In_Grey_file_gate"

FLAG = ("print" ,"compose_only" ,"check_only")
VALUE = ("gate" ,)
COMMAND = ("orchestrate" ,)


def gate_invoking_account_name():
  return pwd.getpwuid(os.getuid()).pw_name


# --------------------------------------------------------------------------------
# provenance

class Provenance:
  """
  Where a composer is. Given to compose().
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
    self.composer_root_dpath = composer_root
    self.composer_abs_fpath = composer_path
    self.composer_rel_fpath = composer_path.relative_to(composer_root)
    self.composer_dir_dpath = composer_path.parent
    name = composer_path.name
    if name.endswith(".py"):
      name = name[:-3]
    self.implied_fname = name
    self.process_user = gate_invoking_account_name()
    self.cwd_dpath = Path.cwd().resolve()


# --------------------------------------------------------------------------------
# finding the composers, and the ownership check

def trusted_owner_problem(path):
  "None when path is owned by the gate invoking account or root and writable by no other account"
  try:
    st = os.lstat(path)
  except OSError as error:
    return f"{path}: {error.strerror}"
  if st.st_uid not in (0 ,os.getuid()):
    return f"{path} is owned by uid {st.st_uid}, neither root nor the gate invoking account"
  if st.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
    return f"{path} is writable by group or other accounts"
  return None

def chain_problem(path):
  "the ownership check over path and every directory above it"
  for each in [path] + list(path.parents):
    problem = trusted_owner_problem(each)
    if problem:
      return problem
  return None

def composer_list(path):
  """
  Given a composer file or a composer directory, absolute. Returns the
  composers in the order they run, each as a Provenance. Raises RuntimeError
  on a symbolic link, a file that is not regular, or a failed ownership check.
  """
  problem = chain_problem(path)
  if problem:
    raise RuntimeError(f"refusing to run composers: {problem}")
  if path.is_symlink():
    raise RuntimeError(f"{path} is a symbolic link")
  if stat.S_ISREG(path.lstat().st_mode):
    return [Provenance(path.parent ,path)]
  if not path.is_dir():
    raise RuntimeError(f"{path} is neither a composer file nor a composer directory")
  found = []
  def walk(directory):
    for entry in sorted(os.scandir(directory) ,key=lambda e: e.name):
      each = Path(entry.path)
      if entry.is_symlink():
        raise RuntimeError(f"{each} is a symbolic link; a composer directory holds composers and directories")
      problem = trusted_owner_problem(each)
      if problem:
        raise RuntimeError(f"refusing to run composers: {problem}")
      if entry.is_dir(follow_symlinks=False):
        walk(each)
      elif entry.is_file(follow_symlinks=False):
        found.append(Provenance(path ,each))
      else:
        raise RuntimeError(f"{each} is neither a file nor a directory")
  walk(path)
  return found


# --------------------------------------------------------------------------------
# the gate's language

def gate_flag(gate_path):
  """The gate's flags as a dict. Raises RuntimeError."""
  if not os.access(gate_path ,os.X_OK):
    raise RuntimeError(f"the gate {gate_path} is missing; in the developer role, build and promote it")
  result = subprocess.run([str(gate_path) ,"flags"] ,capture_output=True ,text=True)
  if result.returncode != 0:
    raise RuntimeError(f"the gate {gate_path} did not report its flags")
  return dict(line.split("=" ,1) for line in result.stdout.splitlines() if "=" in line)

def language_module(name):
  """The module of an instruction language: emplace_bio is EmplaceBioLanguage.py. Raises RuntimeError."""
  if not re.fullmatch(r"[a-z][a-z0-9_]*" ,name or ""):
    raise RuntimeError(f"the gate names the language {name!r}, which names no module")
  module = "".join(part.capitalize() for part in name.split("_")) + "Language"
  if not (HERE_DPATH / f"{module}.py").is_file():
    raise RuntimeError(f"the gate's language is {name}, and {module}.py is not beside {Path(__file__).name}")
  language = importlib.import_module(module)
  if getattr(language ,"NAME" ,None) != name:
    raise RuntimeError(f"{module}.py is not the module of the language {name}")
  return language


# --------------------------------------------------------------------------------
# composing, and invoking the gate

def compose_all(composer_root ,prov_list ,language):
  """Run each composer into one journal. Raises RuntimeError naming the composer that failed."""
  journal = Journal.Journal(language.NAME)
  journal_iface = language.JournalInterface(journal ,Path.cwd())
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
    ,"process_user": gate_invoking_account_name()
    ,"host": os.uname().nodename
    ,"composer_root": str(composer_root)
    ,"composer_list": [p.composer_rel_fpath.as_posix() for p in prov_list]
  }
  return journal

def orchestrate(path ,gate ,flag):
  path = Path(path).absolute()
  gate_path = Path(gate).absolute() if gate else DEFAULT_GATE
  try:
    language = language_module(gate_flag(gate_path).get("language"))
    prov_list = composer_list(path)
    composer_root = path if path.is_dir() else path.parent
    journal = compose_all(composer_root ,prov_list ,language)
  except (OSError ,RuntimeError) as error:
    print(f"error: {error}" ,file=sys.stderr)
    return 2
  if "print" in flag:
    journal.print()
  if "compose_only" in flag:
    return 0

  command = [str(gate_path) ,"admit"]
  if "check_only" in flag:
    command.append("check_only")
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
  if not rest:
    print(f"Error: {command} is given a composer file or a composer directory." ,file=sys.stderr)
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
  return orchestrate(path ,value.get("gate") ,flag)


if __name__ == "__main__":
  sys.exit(CLI())
