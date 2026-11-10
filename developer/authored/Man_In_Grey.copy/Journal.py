# -*- mode: python; coding: utf-8; python-indent-offset: 2; indent-tabs-mode: nil -*-
"""
Journal - the data form of a Man_In_Grey journal, independent of any instruction language.

A journal is a CBOR map of seven entries:

  version              the version of the journal's form, now 4
  instruction_language the name of the instruction language
  definition_hash      the hash of the language definition it was composed
                       against; see Language.py
  meta                 when, where and by which account it was composed, and
                       the composer that ran; a note, never evidence
  list_variable        the variables, each [<name> ,<type name>], the type
                       one the language definition declares
  result               the name of the variable whose value is the journal's
                       result, or null for a journal with no result
  list_instruction     the instructions, each {"operation": <operation
                       specifier> ,"list_argument": [<argument> ...]}

An argument is a pair whose first element says how to read the second:

  ["literal" ,<value>]      the value itself, whatever it is, a map included
  ["variable" ,<name>]      a variable, which the instruction reads, writes,
                            or both, as its format's direction says

The kind of an argument is never inferred from its value, so no literal can
be mistaken for a variable.

This module decodes a journal into its data, checking only the shape every
journal has; prints a journal; and encodes and decodes the result record.
The well-formed guard, Guard·WellFormed.py, checks a journal against its
language definition; Journal·Interface.py is the composer's side.

CBOR carries strings and byte strings with their lengths, so content is
never scanned for marks, and decoding it makes maps, lists, strings and
bytes, never code.
"""

import cbor2

JOURNAL_VERSION = 4
LIST_ENTRY = ("version" ,"instruction_language" ,"definition_hash" ,"meta" ,"list_variable" ,"result" ,"list_instruction")
LIST_KIND = ("literal" ,"variable")


def is_control(character):
  "True for C0 controls, DEL and C1 controls: the characters a gate refuses in what the guard and interpreter write"
  code = ord(character)
  return code < 0x20 or code == 0x7F or 0x80 <= code <= 0x9F

def has_control(text):
  return any(is_control(c) for c in text)

def clean(text):
  "text with each control character written as \\u{XXXX}, for a message that quotes a journal"
  return "".join(f"\\u{{{ord(c):04X}}}" if is_control(c) else c for c in str(text))


class JournalError(Exception):
  """A journal interface call was given a wrong argument, or a journal is malformed."""


# --------------------------------------------------------------------------------
# decoding and printing

def decode(journal_bytes):
  """
  Decode a journal from CBOR into its data, checking only the shape common to
  every instruction language. Raises JournalError.
  """
  try:
    data = cbor2.loads(journal_bytes)
  except Exception as error:
    raise JournalError(f"the journal is not valid CBOR: {error}")
  if type(data) is not dict:
    raise JournalError("the journal is not a map")
  if data.get("version") != JOURNAL_VERSION:
    raise JournalError(f"journal version {clean(repr(data.get('version')))}; this Man_In_Grey reads version {JOURNAL_VERSION}")
  if set(data) != set(LIST_ENTRY):
    raise JournalError(f"the journal has the entries {clean(sorted(map(str ,data)))}; it is to have exactly {list(LIST_ENTRY)}")
  if type(data["instruction_language"]) is not str or type(data["definition_hash"]) is not str:
    raise JournalError("the journal names no instruction language or no definition hash")
  if type(data["meta"]) is not dict or type(data["list_variable"]) is not list or type(data["list_instruction"]) is not list:
    raise JournalError("the journal's meta is not a map, or its variables or instructions are not a list")
  if data["result"] is not None and type(data["result"]) is not str:
    raise JournalError("the journal's result is neither a variable name nor null")
  for index ,instruction in enumerate(data["list_instruction"]):
    if type(instruction) is not dict or set(instruction) != {"operation" ,"list_argument"} \
       or type(instruction["operation"]) is not str or type(instruction["list_argument"]) is not list:
      raise JournalError(f"instruction {index} is not {{\"operation\": <text> ,\"list_argument\": [...]}}")
  return data

MAP_DIRECTION_MARK = {"in": "<" ,"out": ">" ,"in-out": "<>"}

def argument_text(pair ,direction):
  kind ,payload = pair
  if kind == "variable":
    return f"{MAP_DIRECTION_MARK.get(direction ,'?')}{payload}"
  if type(payload) is bytes:
    return f"<{len(payload)} bytes>"
  return clean(repr(payload))

def print_data(data ,language_definition ,file):
  """
  A journal, one line for each declaration and instruction. A variable is
  shown as <name when the instruction reads it, >name when it writes it, and
  <>name when it does both.
  """
  for name ,type_name in data["list_variable"]:
    print(f"variable     {clean(name)}  {clean(type_name)}" ,file=file)
  if data["result"] is not None:
    print(f"result       {clean(data['result'])}" ,file=file)
  if not data["list_instruction"]:
    print("(the journal has no instructions)" ,file=file)
  for index ,instruction in enumerate(data["list_instruction"]):
    format_ = language_definition.format_of(instruction["operation"]) or []
    list_direction = [d for d ,_ in format_] + ["?"] * len(instruction["list_argument"])
    list_part = [argument_text(p ,d) for p ,d in zip(instruction["list_argument"] ,list_direction)]
    print(f"@{index:<3} {clean(instruction['operation']):<12} {' '.join(list_part)}" ,file=file)


# --------------------------------------------------------------------------------
# the result

def encode_result(type_name ,value):
  "the record an interpreter writes on descriptor 3: the result's type name and its value"
  return cbor2.dumps({"type": type_name ,"value": value} ,canonical=True)

def decode_result(result_bytes):
  "the (type name ,value) of a result record. Raises JournalError."
  try:
    data = cbor2.loads(result_bytes)
  except Exception as error:
    raise JournalError(f"the result is not valid CBOR: {error}")
  if type(data) is not dict or set(data) != {"type" ,"value"} or type(data["type"]) is not str:
    raise JournalError("the result is not {\"type\": <type name> ,\"value\": <value>}")
  return data["type"] ,data["value"]
