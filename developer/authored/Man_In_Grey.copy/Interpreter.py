# -*- mode: python; coding: utf-8; python-indent-offset: 2; indent-tabs-mode: nil -*-
"""
Interpreter - the general interpreter of Man_In_Grey.

The interpreter plays a journal the guard has passed. It carries out the
instructions and does not judge them, with one exception: it makes the
well-formed check again, since it decodes the journal anyway, so that a
malformed journal never reaches execution.

A language gives the implementation of its instructions as a class,
LibraryInstruction, in its instruction library module, such as
EmplaceBio·LibraryInstruction.py. An instance is made once for each journal, and
holds whatever the instructions build up between them. For each operation
specifier in the definition the class has a function of that name, given the
instruction's arguments by position:

  in       a copy of the value, so the function cannot change a variable
           through it
  out      an empty list, a box, to which the function appends the value
  in-out   a box holding a copy of the variable's value, which the function
           replaces

After each call, every box is to hold exactly one value of the format's
type; the interpreter takes the value out and keeps it as the variable's.
An empty box is evidence that the function wrote nothing, which no stand-in
value could be.

The function reports failure by raising an exception. LibraryInstruction can
also have finish(), called after the last instruction, and release(), called
at the end whatever happened. The functions are found by the operation
specifiers the definition lists, never by a name taken from the journal.

This module is a library. An instruction language's interpreter program
calls interpret(), writes the result to descriptor 3 and then its verdict;
see EmplaceBio·Interpreter.py.
"""

import copy

import Journal
import Guard·WellFormed


def map_operation_function(language_definition ,library_instruction):
  """
  The function for each operation specifier of the definition, from the
  LibraryInstruction instance. Raises RuntimeError when one is missing.
  """
  map_function = {}
  for operation in language_definition.list_operation:
    function = getattr(library_instruction ,operation ,None)
    if not callable(function):
      raise RuntimeError(f"the language's LibraryInstruction has no function {operation}, which its definition lists")
    map_function[operation] = function
  return map_function

def interpret(journal_bytes ,language_definition ,library_instruction_module ,log ,constraint ,gate_invoking_account):
  """
  Given the encoded journal, the language definition, the language's
  instruction library module, log(tag ,message), the guard program, whose
  constraints the language reads for what execution needs, and the user name
  of account A. Returns (status
  ,result), where result is the encoded result record, or None when the
  journal declares no result. The status is 0 when the journal was played, 1
  when execution failed, 2 when the journal could not be read or is not well
  formed, or the language cannot execute it.
  """
  try:
    data = Journal.decode(journal_bytes)
  except Journal.JournalError as error:
    log("journal_unreadable" ,str(error))
    return 2 ,None
  if not Guard·WellFormed.is_well_formed_journal(data ,language_definition ,log):
    return 2 ,None
  list_instruction_view = Guard·WellFormed.make_list_instruction_view(data ,language_definition)

  library_instruction = library_instruction_module.LibraryInstruction(constraint ,gate_invoking_account ,log)
  try:
    map_function = map_operation_function(language_definition ,library_instruction)
  except RuntimeError as error:
    log("cannot_execute" ,str(error))
    return 2 ,None

  map_value = {}   # variable name -> value
  where = "before the first instruction"
  try:
    for view in list_instruction_view:
      where = f"@{view.index} {view.operation}"
      list_value ,list_box = [] ,[]
      for argument ,(direction ,type_name) in zip(view.list_argument ,language_definition.format_of(view.operation)):
        if argument.is_literal():
          list_value.append(copy.deepcopy(argument.value))
        elif direction == "in":
          list_value.append(copy.deepcopy(map_value[argument.name]))
        else:
          box = [] if direction == "out" else [copy.deepcopy(map_value[argument.name])]
          list_value.append(box)
          list_box.append((argument.name ,type_name ,box))
      map_function[view.operation](*list_value)
      for name ,type_name ,box in list_box:
        if type(box) is not list or len(box) != 1:
          raise RuntimeError(f"the box for {name} holds {len(box) if type(box) is list else 'no list of'} values; it is to hold one")
        problem = language_definition.value_problem(box[0] ,type_name ,f"the value written to {name}")
        if problem:
          raise RuntimeError(problem)
        map_value[name] = copy.deepcopy(box[0])
    where = "after the last instruction"
    finish = getattr(library_instruction ,"finish" ,None)
    if callable(finish):
      finish()
  except Exception as error:
    log("execution_failed" ,f"{where}: {error}")
    return 1 ,None
  finally:
    release = getattr(library_instruction ,"release" ,None)
    if callable(release):
      try:
        release()
      except Exception as error:
        log("release_failed" ,str(error))

  if data["result"] is None:
    return 0 ,None
  result_type = dict(map(tuple ,data["list_variable"]))[data["result"]]
  return 0 ,Journal.encode_result(result_type ,map_value[data["result"]])
