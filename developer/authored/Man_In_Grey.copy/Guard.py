# -*- mode: python; coding: utf-8; python-indent-offset: 2; indent-tabs-mode: nil -*-
"""
Guard - the general guard of Man_In_Grey.

The guard decides whether a journal can be executed. An instruction language
supplies its checks, in order, as CHECK; check() decodes the journal, runs
the checks, and stops at the first that finds problems. Every finding is
given to report as a tag and a message: <check>_broken for each problem,
check_passed for each check that found none.

This module is a library. An instruction language's guard program calls check()
and writes the verdict; see guard_file.py and guard_emplace_bio.py.
"""

import Journal


def check(journal_bytes ,language ,constraint ,gate_invoking_account ,report):
  """
  Given the encoded journal, the instruction language module, its constraint
  module of predicates, the gate invoking account's name, and report(tag
  ,message). Returns 0 when
  every check passed, 1 when a check found problems, 2 when the journal
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
