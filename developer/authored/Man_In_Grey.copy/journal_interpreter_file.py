#!/usr/bin/env -S python3 -B
# -*- mode: python; coding: utf-8; python-indent-offset: 2; indent-tabs-mode: nil -*-
"""
journal_interpreter_file

The bespoke journal interpreter for the file command language, started by
its gate, Man_In_Grey_file_gate, with the journal on standard input.

Its constraints are the file constraints_file.json beside it. On every run,
that file, this program, the modules it loads, and the directory holding
them are to be owned by root or by the interpreter account, the account
this program runs as, and writable by no other account, or it refuses to
run. Through a gate that was not blessed, the caller can give other
constraints with --constraints, since nothing then runs with more than the
caller's own rights; that file is checked the same way.

Usage: journal_interpreter_file [--constraints <file>] [--print] [--stop-after <check>]
  --constraints <file>   constraints to use in place of constraints_file.json; refused when the
                         gate changed the account or the interpreter account is root
  --print                print the journal as decoded
  --stop-after <check>   stop after decode, wellformed, constraint, validity or filesystem
"""

import sys ,os
sys.dont_write_bytecode = True

import json ,pwd ,stat
from pathlib import Path

HERE_DPATH = Path(__file__).resolve().parent
CONSTRAINT_FILE = HERE_DPATH / "constraints_file.json"
MODULE = ("Journal.py" ,"FileLanguage.py" ,"journal_interpreter.py" ,"journal_interpreter_file.py")


def privileged():
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

# Every file this program loads is checked before any of it is imported, on
# every run: a module runs code when it is imported.
for each in [HERE_DPATH ,CONSTRAINT_FILE] + [HERE_DPATH / m for m in MODULE]:
  problem = trusted_owner_problem(each)
  if problem:
    print(f"error: refusing to run: {problem}" ,file=sys.stderr)
    sys.exit(2)

import journal_interpreter
import FileLanguage


def load_constraint(given):
  if given is not None:
    if privileged() or os.geteuid() == 0:
      raise RuntimeError("--constraints is refused when the gate changed the account or the interpreter account is root")
    path = Path(given)
    problem = trusted_owner_problem(path)
    if problem:
      raise RuntimeError(f"refusing the constraints: {problem}")
  else:
    path = CONSTRAINT_FILE
  with open(path ,encoding="utf-8") as f:
    return json.load(f)

def CLI(argv=None):
  argv = sys.argv[1:] if argv is None else argv
  given ,stop_after ,print_journal = None ,None ,False
  i = 0
  while i < len(argv):
    word = argv[i]
    if word == "--constraints" and i + 1 < len(argv):
      given = argv[i + 1]; i += 2
    elif word == "--stop-after" and i + 1 < len(argv) and argv[i + 1] in journal_interpreter.STOP:
      stop_after = argv[i + 1]; i += 2
    elif word == "--print":
      print_journal = True; i += 1
    else:
      print(f"error: unknown argument {word!r}" ,file=sys.stderr)
      return 2
  try:
    constraint = load_constraint(given)
  except (OSError ,ValueError ,RuntimeError) as error:
    print(f"error: constraints: {error}" ,file=sys.stderr)
    return 2
  caller = pwd.getpwuid(os.getuid()).pw_name
  journal_bytes = sys.stdin.buffer.read()
  return journal_interpreter.interpret(
    journal_bytes ,FileLanguage ,constraint ,caller
    ,stop_after=stop_after ,print_journal=print_journal
  )


if __name__ == "__main__":
  sys.exit(CLI())
