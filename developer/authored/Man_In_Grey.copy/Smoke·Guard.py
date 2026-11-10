#!/usr/bin/env -S python3 -B
# -*- mode: python; coding: utf-8; python-indent-offset: 2; indent-tabs-mode: nil -*-
"""
Smoke·Guard - the guard of the smoke instruction language.

Started by the gate Man_In_Grey_gate·smoke, with the gate's real and
effective ids, and with the journal on standard input. It checks the
journal: first with the well-formed guard, against the language definition
in Smoke·Language.py, then with the language's own checks in
Smoke·GuardCheck.py, the constraints among them. It says what it found on
standard error, one line per finding, as <tag>: <message>; the first two
lines are name: and version:.

When every check passes, it writes one line to standard output,

  guard smoke check passed

and exits 0. That line and that status together are the only verdict the
gate admits a journal on.

Its constraints are the predicates at the top of this file. The
interpreter imports this file for what execution needs from them.

Before it imports anything, it checks that its modules and their directory
are owned by root or by the effective uid's account, and writable by no
other account. A module runs code when it is imported.

Usage: Smoke·Guard <command>
  help | -h   print this message (also printed when given no arguments)
  check       check the journal on standard input

Exit status: 0 when every check passed, 1 when a check refused the journal,
2 when the journal could not be checked.
"""

# ------------------------------------------------------------------------------
# The constraints: the predicates this guard checks a journal with. They are
# written by whoever installs the gate, between the two marks below, and
# install_gate can put them in from a file and keeps them when it installs
# the guard again. A predicate allows only by answering True. As promoted
# with Man_In_Grey, is_allowed_account refuses every account.
#
# They are called only after the modules below are checked and imported, so
# they can call Guard·LibraryConstraint, the library of predicates that recur,
# as Guard·LibraryConstraint.is_group_member(user_name ,"bio").

# constraints begin

def is_allowed_account(user_name):
  "True when the account, the gate's real uid, can give journals to the gate"
  return False

def is_allowed_open(directory ,name ,mode ,owner ,permission):
  "True when the file can be opened in this mode, to be given this owner and permission"
  return False

def is_allowed_unlink(directory ,name):
  "True when the file can be removed"
  return False

# constraints end
# ------------------------------------------------------------------------------


import sys ,os
sys.dont_write_bytecode = True

import stat
from pathlib import Path

LANGUAGE = "smoke"
VERSION = "4"

HERE_DPATH = Path(__file__).resolve().parent
MODULE = ("Language.py" ,"Journal.py" ,"Guard·WellFormed.py" ,"Guard.py" ,"Guard·LibraryConstraint.py" ,"Smoke·Language.py" ,"Smoke·GuardCheck.py" ,"Smoke·Guard.py")


def trusted_owner_problem(path):
  "None when path is owned by root or the effective uid's account and writable by no other account"
  try:
    st = os.lstat(path)
  except OSError as error:
    return f"{path}: {error.strerror}"
  if st.st_uid not in (0 ,os.geteuid()):
    return f"{path} is owned by uid {st.st_uid}, neither root nor the effective uid's account"
  if st.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
    return f"{path} is writable by group or other accounts"
  return None

def say(tag ,message):
  print(f"{tag}: {message}" ,file=sys.stderr)

if __name__ == "__main__" and sys.argv[1:] == ["check"]:
  say("name" ,LANGUAGE)
  say("version" ,VERSION)

for each in [HERE_DPATH] + [HERE_DPATH / m for m in MODULE]:
  problem = trusted_owner_problem(each)
  if problem:
    say("refused_to_start" ,problem)
    sys.exit(2)

try:
  import Language
  import Journal
  import Guard
  import Guard·LibraryConstraint   # for the constraints at the top, which call it by name
  import Smoke·Language as language_module
  import Smoke·GuardCheck as guard_check
except ImportError as error:
  say("cannot_start" ,str(error))
  sys.exit(2)


def report(tag ,message):
  say(tag ,Journal.clean(message))

def check():
  report("constraints" ,str(Path(__file__).resolve()))
  try:
    gate_invoking_account = Guard.gate_invoking_account()
  except RuntimeError as error:
    report("cannot_check" ,str(error))
    return 2
  try:
    language_definition = Language.Definition(language_module.NAME ,language_module.DEFINITION)
  except Language.DefinitionError as error:
    report("cannot_check" ,str(error))
    return 2
  status = Guard.check(sys.stdin.buffer.read() ,language_definition ,guard_check ,sys.modules[__name__] ,gate_invoking_account ,report)
  if status == 0:
    sys.stdout.write(f"guard {LANGUAGE} check passed\n")
  return status


# --------------------------------------------------------------------------------
# command line

def print_help():
  print(__doc__.strip())
  return 0

def CLI(argv=None):
  argv = sys.argv[1:] if argv is None else argv
  if not argv or argv[0] in ("help" ,"-h" ,"--help"): return print_help()
  if argv != ["check"]:
    say("usage" ,f"unknown command {Journal.clean(repr(' '.join(argv)))}; run Smoke·Guard with no arguments for its usage")
    return 2
  return check()


if __name__ == "__main__":
  try:
    sys.exit(CLI())
  except Exception as error:
    say("failed" ,Journal.clean(f"{type(error).__name__}: {error}"))
    sys.exit(2)
