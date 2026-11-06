#!/usr/bin/env -S python3 -B
# -*- mode: python; coding: utf-8; python-indent-offset: 2; indent-tabs-mode: nil -*-
"""
guard_file - the guard of the file command language.

Started by the gate Man_In_Grey_file_gate, under the interpreter account,
with the journal on standard input. It checks the journal against the
constraints, and says what it found on standard error, one line per
finding, as <tag>: <message>; the first two lines are name: and version:.

When every check passes, it writes one line to standard output,

  guard file check passed

and exits 0. That line and that status together are the only verdict the
gate admits a journal on.

Its constraints are constraints_file.json beside it. Through a gate that
is not setuid, other constraints can be given with constraints <file>,
since nothing then runs with more than the gate invoking account's own rights.

Before it imports anything, it checks that its modules, its constraints
file and their directory are owned by root or by the interpreter account,
and writable by no other account. A module runs code when it is imported.

Usage: guard_file <command> [option ...]
  help | -h            print this message (also printed when given no arguments)
  check                check the journal on standard input
Options of check:
  constraints <file>   constraints to use in place of constraints_file.json; refused
                       when the gate changed the account or the interpreter account is root

Exit status: 0 when every check passed, 1 when a check refused the journal,
2 when the journal could not be checked.
"""

import sys ,os
sys.dont_write_bytecode = True

import json ,pwd ,stat
from pathlib import Path

GUARD_NAME = "file"
VERSION = "1"

HERE_DPATH = Path(__file__).resolve().parent
CONSTRAINT_FILE = HERE_DPATH / "constraints_file.json"
MODULE = ("Journal.py" ,"FileLanguage.py" ,"Guard.py" ,"guard_file.py")


def account_changed():
  return os.geteuid() != os.getuid() or os.getegid() != os.getgid()

def trusted_owner_problem(path):
  "None when path is owned by root or the interpreter account and writable by no other account"
  try:
    st = os.lstat(path)
  except OSError as error:
    return f"{path}: {error.strerror}"
  if st.st_uid not in (0 ,os.geteuid()):
    return f"{path} is owned by uid {st.st_uid}, neither root nor the interpreter account"
  if st.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
    return f"{path} is writable by group or other accounts"
  return None

def say(tag ,message):
  print(f"{tag}: {message}" ,file=sys.stderr)

if __name__ == "__main__" and sys.argv[1:2] == ["check"]:
  say("name" ,GUARD_NAME)
  say("version" ,VERSION)

for each in [HERE_DPATH ,CONSTRAINT_FILE] + [HERE_DPATH / m for m in MODULE]:
  problem = trusted_owner_problem(each)
  if problem:
    say("refused_to_start" ,problem)
    sys.exit(2)

try:
  import Journal
  import FileLanguage
  import Guard
except ImportError as error:
  say("cannot_start" ,str(error))
  sys.exit(2)


def report(tag ,message):
  say(tag ,Journal.clean(message))

def load_constraint(given):
  if given is not None:
    if account_changed() or os.geteuid() == 0:
      raise RuntimeError("constraints are refused when the gate changed the account or the interpreter account is root")
    path = Path(given)
    problem = trusted_owner_problem(path)
    if problem:
      raise RuntimeError(problem)
  else:
    path = CONSTRAINT_FILE
  with open(path ,encoding="utf-8") as f:
    constraint = json.load(f)
  report("constraints" ,str(path))
  return constraint

def check(given):
  try:
    constraint = load_constraint(given)
  except (OSError ,ValueError ,RuntimeError) as error:
    report("constraints_unusable" ,str(error))
    return 2
  gate_invoking_account = pwd.getpwuid(os.getuid()).pw_name
  status = Guard.check(sys.stdin.buffer.read() ,FileLanguage ,constraint ,gate_invoking_account ,report)
  if status == 0:
    sys.stdout.write(f"guard {GUARD_NAME} check passed\n")
  return status


# --------------------------------------------------------------------------------
# command line

def print_help():
  print(__doc__.strip())
  return 0

def CLI(argv=None):
  argv = sys.argv[1:] if argv is None else argv
  if not argv or argv[0] in ("help" ,"-h" ,"--help"): return print_help()
  command ,rest = argv[0] ,argv[1:]
  if command != "check":
    say("usage" ,f"unknown command {Journal.clean(repr(command))}; run guard_file with no arguments for its usage")
    return 2
  given = None
  i = 0
  while i < len(rest):
    if rest[i] == "constraints" and i + 1 < len(rest):
      given = rest[i + 1]; i += 2
    else:
      say("usage" ,f"unknown or incomplete option {Journal.clean(repr(rest[i]))}")
      return 2
  return check(given)


if __name__ == "__main__":
  try:
    sys.exit(CLI())
  except Exception as error:
    say("failed" ,Journal.clean(f"{type(error).__name__}: {error}"))
    sys.exit(2)
