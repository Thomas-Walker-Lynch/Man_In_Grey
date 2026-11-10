# -*- mode: python; coding: utf-8; python-indent-offset: 2; indent-tabs-mode: nil -*-
"""
Language - what a Man_In_Grey instruction language is, and how its definition is checked.

This module defines no language. An instruction language is defined by its
application developer as data: a map of four sections, written as a literal
value in a module of its own, such as EmplaceBio·Language.py. Account A
cannot change it. The guard, the interpreter and the journal interface all
read the same definition, and a journal carries the hash of the definition
it was composed against.

  list_type     a list of type declarations, each [<name> ,<type expression>].
                A type expression is a primitive, the name of a type declared
                earlier in the list, or a compound:
                  ["dictionary" ,[<key> ,<type expression>] ...]
                  ["list" ,<type expression>]
  list_format   a list of instruction formats, each
                [<format name> ,[<direction> ,<type name>] ...], where the
                direction is in, out or in-out, and the type name is a
                primitive or a declared type. Arguments are given by position.
  list_result   the list of type names a journal's result can have.
  map_instruction
                a map from each operation specifier to its format name. The
                operation specifier is also the name of the function that
                carries out the instruction.

The primitives are text, integer, bytes, boolean and handle. A handle is a
value an instruction produces for later instructions, such as an open file:
no literal can be a handle, and no result can hold one.

Types are compared by name. A variable of the type short_name is not a
variable of the type text, even when short_name is declared as text, so a
reference passes only where the format names its type exactly. A literal is
compared with the type's structure.

This module is a library. is_well_formed_language(data ,report) answers
whether a definition is well formed, reporting each problem;
Definition(name ,data) is a definition that has passed, as the guard, the
interpreter and the journal interface each use it.
"""

import hashlib ,keyword

import cbor2

LIST_PRIMITIVE = ("text" ,"integer" ,"bytes" ,"boolean" ,"handle")
LIST_COMPOUND = ("dictionary" ,"list")
LIST_DIRECTION = ("in" ,"out" ,"in-out")
LIST_SECTION = ("list_type" ,"list_format" ,"list_result" ,"map_instruction")

# operation specifiers the journal interface and the interpreter keep for themselves
LIST_OPERATION_RESERVED = ("declare" ,"result" ,"finish" ,"release")


class DefinitionError(Exception):
  """A language definition is not well formed."""


def is_control(character):
  code = ord(character)
  return code < 0x20 or code == 0x7F or 0x80 <= code <= 0x9F

def is_name(value):
  "True for a name: text that is not empty and holds no space and no control character"
  return type(value) is str and value != "" and not any(c.isspace() or is_control(c) for c in value)

def hash_text(data):
  "the SHA-256 of a definition's canonical CBOR encoding, in hexadecimal"
  return hashlib.sha256(cbor2.dumps(data ,canonical=True)).hexdigest()


# --------------------------------------------------------------------------------
# the well-formed check of a definition

def _type_expression_problem(expression ,map_type ,where):
  "None when expression is a well-formed type expression over the primitives and the types in map_type"
  if type(expression) is str:
    if expression in LIST_PRIMITIVE or expression in map_type:
      return None
    return f"{where}: {expression!r} is neither a primitive nor a type declared before it"
  if type(expression) is not list or not expression:
    return f"{where}: a type expression is a type name or a list beginning with dictionary or list"
  head = expression[0]
  if head == "list":
    if len(expression) != 2:
      return f"{where}: a list type is [\"list\" ,<element type>]"
    return _type_expression_problem(expression[1] ,map_type ,f"{where} list element")
  if head == "dictionary":
    set_key = set()
    for entry in expression[1:]:
      if type(entry) is not list or len(entry) != 2 or not is_name(entry[0]):
        return f"{where}: a dictionary entry is [<key> ,<type expression>]"
      if entry[0] in set_key:
        return f"{where}: the key {entry[0]!r} is given twice"
      set_key.add(entry[0])
      problem = _type_expression_problem(entry[1] ,map_type ,f"{where} key {entry[0]}")
      if problem: return problem
    return None
  return f"{where}: {head!r} is not a compound type; the compounds are {', '.join(LIST_COMPOUND)}"

def _is_handle_holder(expression ,map_type):
  "True when the type expression is, or holds, a handle"
  if type(expression) is str:
    if expression == "handle": return True
    if expression in map_type: return _is_handle_holder(map_type[expression] ,map_type)
    return False
  if expression[0] == "list":
    return _is_handle_holder(expression[1] ,map_type)
  return any(_is_handle_holder(entry[1] ,map_type) for entry in expression[1:])

def list_problem_language(data):
  "every problem with a language definition, as a list of messages; empty when it is well formed"
  if type(data) is not dict:
    return ["the definition is not a map"]
  if set(data) != set(LIST_SECTION):
    return [f"the definition has the sections {sorted(data)}; it is to have exactly {list(LIST_SECTION)}"]
  list_problem = []

  map_type = {}
  if type(data["list_type"]) is not list:
    list_problem.append("list_type: is not a list")
  else:
    for index ,entry in enumerate(data["list_type"]):
      where = f"list_type @{index}"
      if type(entry) is not list or len(entry) != 2:
        list_problem.append(f"{where}: a type declaration is [<name> ,<type expression>]"); continue
      name ,expression = entry
      if not is_name(name):
        list_problem.append(f"{where}: {name!r} is not a name"); continue
      if name in LIST_PRIMITIVE or name in LIST_COMPOUND or name in map_type:
        list_problem.append(f"{where}: the type name {name!r} is a primitive, a compound or declared before"); continue
      problem = _type_expression_problem(expression ,map_type ,f"{where} {name}")
      if problem: list_problem.append(problem); continue
      map_type[name] = expression

  set_format_name = set()
  if type(data["list_format"]) is not list:
    list_problem.append("list_format: is not a list")
  else:
    for index ,entry in enumerate(data["list_format"]):
      where = f"list_format @{index}"
      if type(entry) is not list or not entry or not is_name(entry[0]):
        list_problem.append(f"{where}: an instruction format is [<format name> ,[<direction> ,<type name>] ...]"); continue
      name = entry[0]
      if name in set_format_name:
        list_problem.append(f"{where}: the format {name!r} is declared twice"); continue
      set_format_name.add(name)
      for position ,argument in enumerate(entry[1:]):
        if type(argument) is not list or len(argument) != 2:
          list_problem.append(f"{where} {name} argument {position}: an argument is [<direction> ,<type name>]"); continue
        direction ,type_name = argument
        if direction not in LIST_DIRECTION:
          list_problem.append(f"{where} {name} argument {position}: {direction!r} is not one of {', '.join(LIST_DIRECTION)}")
        if type(type_name) is not str or not (type_name in LIST_PRIMITIVE or type_name in map_type):
          list_problem.append(f"{where} {name} argument {position}: {type_name!r} is neither a primitive nor a declared type")

  if type(data["list_result"]) is not list:
    list_problem.append("list_result: is not a list")
  else:
    for type_name in data["list_result"]:
      if type(type_name) is not str or not (type_name in LIST_PRIMITIVE or type_name in map_type):
        list_problem.append(f"list_result: {type_name!r} is neither a primitive nor a declared type"); continue
      if _is_handle_holder(type_name ,map_type):
        list_problem.append(f"list_result: {type_name!r} holds a handle, which has no meaning outside the interpreter")
    if len(set(map(repr ,data["list_result"]))) != len(data["list_result"]):
      list_problem.append("list_result: a type is given twice")

  if type(data["map_instruction"]) is not dict or not data["map_instruction"]:
    list_problem.append("map_instruction: is not a map of at least one operation specifier to its format name")
  else:
    for operation ,format_name in data["map_instruction"].items():
      if type(operation) is not str or not operation.isidentifier() or keyword.iskeyword(operation) or operation.startswith("_"):
        list_problem.append(f"map_instruction: {operation!r} is not an operation specifier; it is a Python function name not beginning with _"); continue
      if operation in LIST_OPERATION_RESERVED:
        list_problem.append(f"map_instruction: {operation!r} is kept by Man_In_Grey; the kept names are {', '.join(LIST_OPERATION_RESERVED)}")
      if format_name not in set_format_name:
        list_problem.append(f"map_instruction: {operation} has the format {format_name!r}, which is not declared")
  return list_problem

def is_well_formed_language(data ,report):
  """
  True when the language definition data is well formed. Each problem found
  is given to report(tag ,message), as definition_broken.
  """
  list_problem = list_problem_language(data)
  for problem in list_problem:
    report("definition_broken" ,problem)
  return not list_problem


# --------------------------------------------------------------------------------
# a checked definition

class Definition:
  """
  A language definition that has passed its well-formed check. Given the
  language's name and the definition data. Raises DefinitionError.
  """

  def __init__(self ,name ,data):
    list_problem = list_problem_language(data)
    if list_problem:
      raise DefinitionError(f"the definition of {name} is not well formed: " + "; ".join(list_problem))
    self.name = name
    self.data = data
    self.hash = hash_text(data)
    self._map_type = {entry[0]: entry[1] for entry in data["list_type"]}
    self._map_format = {entry[0]: [tuple(argument) for argument in entry[1:]] for entry in data["list_format"]}
    self.list_result_type = list(data["list_result"])
    self.list_operation = list(data["map_instruction"])

  def is_type_name(self ,name):
    return type(name) is str and (name in LIST_PRIMITIVE or name in self._map_type)

  def format_of(self ,operation):
    "the arguments of the operation's format, as (direction ,type name) in order; None for an unknown operation"
    format_name = self.data["map_instruction"].get(operation) if type(operation) is str else None
    return None if format_name is None else self._map_format[format_name]

  def is_handle_holder(self ,type_name):
    return _is_handle_holder(type_name ,self._map_type)

  def value_problem(self ,value ,expression ,where="the value"):
    """
    None when value has the structure of the type expression; otherwise what
    is wrong. Checks type() exactly, so that a boolean is never taken for an
    integer, as isinstance(True ,int) would.
    """
    if type(expression) is str:
      if expression in self._map_type:
        return self.value_problem(value ,self._map_type[expression] ,where)
      want = {"text": str ,"integer": int ,"bytes": bytes ,"boolean": bool ,"handle": int}[expression]
      if type(value) is not want:
        return f"{where} is {type(value).__name__}, not {expression}"
      return None
    if expression[0] == "list":
      if type(value) is not list:
        return f"{where} is {type(value).__name__}, not a list"
      for i ,element in enumerate(value):
        problem = self.value_problem(element ,expression[1] ,f"{where}[{i}]")
        if problem: return problem
      return None
    map_key_type = {entry[0]: entry[1] for entry in expression[1:]}
    if type(value) is not dict:
      return f"{where} is {type(value).__name__}, not a dictionary"
    if set(value) != set(map_key_type):
      return f"{where} has the keys {sorted(map(str ,value))}, not {sorted(map_key_type)}"
    for key ,element_type in map_key_type.items():
      problem = self.value_problem(value[key] ,element_type ,f"{where}[{key!r}]")
      if problem: return problem
    return None
