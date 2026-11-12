# -*- mode: python; coding: utf-8; python-indent-offset: 2; indent-tabs-mode: nil -*-
"""
Journal·Interface - the composer's side of a journal.

A composer is given a JournalInterface. It has one function for each
operation of the language, named by its operation specifier, given the
instruction's arguments in the order of its format: a Variable where the
format reads or writes a variable, any other value as a literal. Besides
them, declare(name ,type_name) returns a new Variable, and result(variable)
makes a variable the journal's result.

Every declaration and instruction is checked by the well-formed guard's pass
as it is placed, and refused with JournalError when it is not well formed,
so a composer's mistake is an error in the composer, and no journal reaches
the gate.

An application that is its own orchestrator makes a JournalComposed from
the language definition, and a JournalInterface on it, and encodes the
JournalComposed when the composing is done.

This module is a library.
"""

import cbor2

import Journal
from Journal import JournalError
from Guard·WellFormed import Scan


class Variable:
  """A variable of the journal, as a composer holds it: its name and type name."""
  __slots__ = ("name" ,"type_name")

  def __init__(self ,name ,type_name):
    self.name = name
    self.type_name = type_name

  def __repr__(self):
    return f"Variable({self.name!r} ,{self.type_name!r})"


class JournalComposed:
  """
  The journal being composed, for one instruction language. Given the
  language definition.
  """

  def __init__(self ,language_definition):
    self.language_definition = language_definition
    self.meta = {}
    self.list__variable = []
    self.result_name = None
    self.list__instruction = []
    self._scan = Scan(language_definition)

  def declare(self ,name ,type_name):
    list__problem = self._scan.declare(name ,type_name)
    if list__problem: raise JournalError(list__problem[0])
    self.list__variable.append([name ,type_name])
    return Variable(name ,type_name)

  def set_result(self ,variable):
    if not isinstance(variable ,Variable) or self._scan.map__declared.get(variable.name) != variable.type_name:
      raise JournalError("result: give a variable declare returned")
    if variable.type_name not in self.language_definition.list__result_type:
      raise JournalError(f"result: the type {variable.type_name} is not among the result types {self.language_definition.list__result_type}")
    self.result_name = variable.name

  def place(self ,operation ,list__value):
    list__pair = [["variable" ,v.name] if isinstance(v ,Variable) else ["literal" ,v] for v in list__value]
    list__problem = self._scan.instruction(len(self.list__instruction) ,operation ,list__pair)
    if list__problem: raise JournalError(list__problem[0])
    self.list__instruction.append({"operation": operation ,"list__argument": list__pair})

  def as_data(self):
    list__problem = self._scan.result(self.result_name)
    if list__problem: raise JournalError(list__problem[0])
    return {
      "version": Journal.JOURNAL_VERSION
      ,"instruction_language": self.language_definition.name
      ,"definition_hash": self.language_definition.hash
      ,"meta": dict(self.meta)
      ,"list__variable": [list(v) for v in self.list__variable]
      ,"result": self.result_name
      ,"list__instruction": list(self.list__instruction)
    }

  def encode(self):
    return cbor2.dumps(self.as_data() ,canonical=True)

  def print(self ,file=None):
    import sys
    Journal.print_data(self.as_data() ,self.language_definition ,file or sys.stdout)


class JournalInterface:
  """
  The journal interface a composer is given, on a JournalComposed. See the
  module's description.
  """

  def __init__(self ,journal_composed):
    self._journal_composed = journal_composed
    for operation in journal_composed.language_definition.list__operation:
      setattr(self ,operation ,self._placer(operation))

  def _placer(self ,operation):
    def place(*list__value):
      self._journal_composed.place(operation ,list(list__value))
    place.__name__ = operation
    return place

  def declare(self ,name ,type_name):
    return self._journal_composed.declare(name ,type_name)

  def result(self ,variable):
    self._journal_composed.set_result(variable)
