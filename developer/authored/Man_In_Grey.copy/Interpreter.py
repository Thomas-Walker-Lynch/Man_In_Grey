# -*- mode: python; coding: utf-8; python-indent-offset: 2; indent-tabs-mode: nil -*-
"""
Interpreter - the general interpreter of Man_In_Grey.

The interpreter executes a journal the guard has passed. It carries out
instructions and does not judge them, with one exception: it checks again that
the journal is well formed, since it decodes the journal anyway, so that a
malformed journal never reaches execution.

This module is a library. An instruction language's interpreter program calls
interpret(); see interpreter_emplace_bio.py.
"""

import Journal


def interpret(journal_bytes ,language ,log ,constraint ,gate_invoking_account):
  """
  Given the encoded journal, the instruction language module, log(tag
  ,message), the guard program, whose constraints the language reads for
  what execution needs, and the user name of account A. Returns 0 when the journal was executed, 1 when
  execution failed, 2 when the journal could not be read or is not well
  formed.
  """
  try:
    data = Journal.decode(journal_bytes)
  except Journal.JournalError as error:
    log("journal_unreadable" ,str(error))
    return 2
  if data["instruction_language"] != language.NAME:
    log("wrong_language" ,f"the journal is in {data['instruction_language']!r}; this interpreter executes {language.NAME!r}")
    return 2
  problem_list = language.check_wellformed(data)
  for problem in problem_list:
    log("wellformed_broken" ,problem)
  if problem_list:
    return 2
  return language.execute(data ,log ,constraint ,gate_invoking_account)
