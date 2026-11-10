# -*- mode: python; coding: utf-8; python-indent-offset: 2; indent-tabs-mode: nil -*-
"""
Guard - the general guard of Man_In_Grey.

The guard decides whether a journal can be executed. check() decodes the
journal and makes the checks in order, stopping at the first that finds
problems:

  wellformed   the well-formed guard, Man_In_Grey's own: the journal against
               the language definition, by Guard·WellFormed.is_well_formed_journal
  ...          the language's own checks, in the order its LIST_CHECK gives them:
               what a definition cannot say, such as an order the
               instructions are to come in, the values a literal can take,
               and the constraints

Every finding is given to report as a tag and a message: <check>_broken for
each problem, check_passed for each check that found none.

This module is a library. An instruction language's guard program calls
check() and writes the verdict; see EmplaceBio·Guard.py.
"""

import os ,pwd

import Journal
import Guard·WellFormed


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


def check(journal_bytes ,language_definition ,guard_check ,constraint ,gate_invoking_account ,report):
  """
  Given the encoded journal, the language definition, the language's guard
  check module, the constraint module of predicates, the gate invoking
  account's name, and report(tag ,message). A language check is given the
  instructions as a list of Guard·WellFormed.InstructionView, the decoded
  journal, the constraint module and the gate invoking account, and returns
  a list of problems. Returns 0 when every check passed, 1 when a check found
  problems, 2 when the journal could not be read.
  """
  try:
    data = Journal.decode(journal_bytes)
  except Journal.JournalError as error:
    report("journal_unreadable" ,str(error))
    return 2
  if data["instruction_language"] != language_definition.name:
    report("wrong_language" ,f"the journal is in {data['instruction_language']!r}; this guard checks {language_definition.name!r}")
    return 1
  report("journal" ,f"{len(data['list_variable'])} variables, {len(data['list_instruction'])} instructions"
         + (f", result {data['result']}" if data["result"] is not None else ""))
  if not Guard·WellFormed.is_well_formed_journal(data ,language_definition ,report):
    return 1
  report("check_passed" ,"wellformed")
  list_instruction_view = Guard·WellFormed.make_list_instruction_view(data ,language_definition)
  for name ,function in guard_check.LIST_CHECK:
    list_problem = function(list_instruction_view ,data ,constraint ,gate_invoking_account)
    for problem in list_problem:
      report(f"{name}_broken" ,problem)
    if list_problem:
      return 1
    report("check_passed" ,name)
  return 0
