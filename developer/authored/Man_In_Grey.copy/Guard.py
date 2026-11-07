# -*- mode: python; coding: utf-8; python-indent-offset: 2; indent-tabs-mode: nil -*-
"""
Guard - the general guard of Man_In_Grey.

The guard decides whether a journal can be executed. An instruction language
supplies its checks, in order, as CHECK; check() decodes the journal, runs
the checks, and stops at the first that finds problems. Every finding is
given to report as a tag and a message: <check>_broken for each problem,
check_passed for each check that found none.

This module is a library. An instruction language's guard program calls
check() and writes the verdict; see guard_emplace_bio.py.
"""

import os ,pwd

import Journal


def gate_invoking_account():
  """
  The user name of account A, the account that invoked the gate.

  A setuid gate gives up account A as its real uid before it starts the
  guard and the interpreter, so the kernel no longer says who account A is.
  The gate records account A's uid and user name first, in MIG_REAL_UID and
  MIG_REAL_USER_NAME, having cleared the environment, so what they say is
  what the gate says. The two are checked against each other. Raises
  RuntimeError when they are missing or disagree.
  """
  try:
    uid = int(os.environ["MIG_REAL_UID"])
    user_name = os.environ["MIG_REAL_USER_NAME"]
  except (KeyError ,ValueError):
    raise RuntimeError("MIG_REAL_UID and MIG_REAL_USER_NAME are not set; the guard and the interpreter are started by a gate")
  try:
    recorded = pwd.getpwuid(uid).pw_name
  except KeyError:
    raise RuntimeError(f"MIG_REAL_UID {uid} names no account")
  if recorded != user_name:
    raise RuntimeError(f"MIG_REAL_UID {uid} is the account {recorded!r}, not {user_name!r}")
  return user_name


def check(journal_bytes ,language ,constraint ,gate_invoking_account ,report):
  """
  Given the encoded journal, the instruction language module, its constraint
  module of predicates, the gate invoking account's name, and report(tag
  ,message). Returns 0 when every check passed, 1 when a check found problems, 2 when the journal
  could not be read.
  """
  try:
    data = Journal.decode(journal_bytes)
  except Journal.JournalError as error:
    report("journal_unreadable" ,str(error))
    return 2
  if data["instruction_language"] != language.NAME:
    report("wrong_language" ,f"the journal is in {data['instruction_language']!r}; this guard checks {language.NAME!r}")
    return 1
  report("journal" ,f"{len(data['instruction_list'])} instructions")
  for name ,function in language.CHECK:
    problem_list = function(data ,constraint ,gate_invoking_account)
    for problem in problem_list:
      report(f"{name}_broken" ,problem)
    if problem_list:
      return 1
    report("check_passed" ,name)
  return 0
