#!/usr/bin/env -S python3 -B
# -*- mode: python; coding: utf-8; python-indent-offset: 2; indent-tabs-mode: nil -*-
"""
interpreter_file - the interpreter of the file instruction language.

Started by the gate Man_In_Grey_file_gate, with the gate's real and
effective ids, and with the journal on standard input, once the guard has
passed the journal. It executes the journal's instructions, and writes to
standard output, as <tag>: <message>, a line for each lasting change it
makes, such as a file put in place, and none for an instruction as such.
The gate logs the journal's course itself.

It checks again that the journal is well formed before executing it. It
does not check the constraints; that is the guard's work, and the gate
starts the interpreter only on the guard's verdict. It imports the guard,
guard_file.py, for what execution needs from the constraints at its top.

Before it imports anything, it checks that its modules and their directory
are owned by root or by the effective uid's account, and writable by no
other account.

Usage: interpreter_file <command>
  help | -h   print this message (also printed when given no arguments)
  execute     execute the journal on standard input

Exit status: 0 when the journal was executed, 1 when execution failed,
2 when the journal could not be read or is not well formed.
"""

import sys ,os
sys.dont_write_bytecode = True

import stat
from pathlib import Path

HERE_DPATH = Path(__file__).resolve().parent
MODULE = ("Journal.py" ,"Interpreter.py" ,"Constraint.py" ,"FileLanguage.py" ,"guard_file.py" ,"interpreter_file.py")


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

for each in [HERE_DPATH] + [HERE_DPATH / m for m in MODULE]:
  problem = trusted_owner_problem(each)
  if problem:
    say("refused_to_start" ,problem)
    sys.exit(2)

try:
  import Journal
  import Interpreter
  import FileLanguage as Language
  import guard_file as Guard_program
except ImportError as error:
  say("cannot_start" ,str(error))
  sys.exit(2)


def log(tag ,message):
  print(f"{tag}: {Journal.clean(message)}" ,flush=True)

def execute():
  return Interpreter.interpret(sys.stdin.buffer.read() ,Language ,log ,Guard_program)


# --------------------------------------------------------------------------------
# command line

def print_help():
  print(__doc__.strip())
  return 0

def CLI(argv=None):
  argv = sys.argv[1:] if argv is None else argv
  if not argv or argv[0] in ("help" ,"-h" ,"--help"): return print_help()
  if argv != ["execute"]:
    say("usage" ,f"unknown command {Journal.clean(repr(' '.join(argv)))}; run interpreter_file with no arguments for its usage")
    return 2
  return execute()


if __name__ == "__main__":
  try:
    sys.exit(CLI())
  except Exception as error:
    say("failed" ,Journal.clean(f"{type(error).__name__}: {error}"))
    sys.exit(2)
