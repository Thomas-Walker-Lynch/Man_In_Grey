# -*- mode: python; coding: utf-8; python-indent-offset: 2; indent-tabs-mode: nil -*-
"""
Journal - the journal of Man_In_Grey, independent of any instruction language.

A composer places instructions into a journal. An instruction is data: the name of
the instruction, its arguments, and the composer that placed it. An instruction whose
execution produces a value, such as an open file, is given a symbol when it
is placed. A later instruction names that symbol where it needs the value. The
value does not exist until the journal interpreter executes the instruction, so
the composer holds the symbol and nothing more.

The journal travels to the journal interpreter encoded in CBOR. CBOR carries
strings and byte strings with their lengths, so content is never scanned for
marks, and decoding it makes maps, lists, strings and bytes, never code.

An instruction language is defined elsewhere, as a module with a composer half,
its journal interface, and an interpreter half, its guard and executor.
"""

import cbor2

JOURNAL_VERSION = 3


def is_control(character):
  "C0 controls, DEL and C1 controls: the characters a gate refuses in what the guard and interpreter write"
  code = ord(character)
  return code < 0x20 or code == 0x7F or 0x80 <= code <= 0x9F

def has_control(text):
  return any(is_control(c) for c in text)

def clean(text):
  "text with each control character written as \\u{XXXX}, for a message that quotes a journal"
  return "".join(f"\\u{{{ord(c):04X}}}" if is_control(c) else c for c in str(text))


class JournalError(Exception):
  """A journal interface call was given a wrong argument, or a journal is malformed."""


class Symbol:
  """
  The value an instruction will produce when it is executed. A symbol is the
  index of the instruction that produces it, counted from 0. It is encoded in the
  journal as {"symbol": index}.
  """
  __slots__ = ("index" ,)

  def __init__(self ,index):
    self.index = index

  def as_data(self):
    return {"symbol": self.index}

  def __repr__(self):
    return f"Symbol({self.index})"

  @staticmethod
  def is_data(value):
    return isinstance(value ,dict) and set(value) == {"symbol"} and isinstance(value["symbol"] ,int)


class Instruction:
  __slots__ = ("name" ,"argument" ,"composer")

  def __init__(self ,name ,argument ,composer):
    self.name = name
    self.argument = argument
    self.composer = composer

  def as_data(self):
    return {
      "name": self.name
      ,"argument": {k: (v.as_data() if isinstance(v ,Symbol) else v) for k ,v in self.argument.items()}
      ,"composer": self.composer
    }


class Journal:
  """
  The instructions of one run, in order, for one instruction language.
  """

  def __init__(self ,instruction_language):
    self.instruction_language = instruction_language
    self.meta = {}
    self.instruction_list = []
    self.composer = None

  def place(self ,name ,argument):
    """Place an instruction; returns its symbol."""
    self.instruction_list.append(Instruction(name ,dict(argument) ,self.composer))
    return Symbol(len(self.instruction_list) - 1)

  def as_data(self):
    data = {
      "version": JOURNAL_VERSION
      ,"instruction_language": self.instruction_language
      ,"meta": dict(self.meta)
      ,"instruction_list": [c.as_data() for c in self.instruction_list]
    }
    return data

  def encode(self):
    return cbor2.dumps(self.as_data() ,canonical=True)

  def print(self ,file=None):
    import sys
    file = file or sys.stdout
    if not self.instruction_list:
      print("(the journal is empty)" ,file=file)
    for index ,instruction in enumerate(self.instruction_list):
      print(instruction_line(index ,instruction.as_data()) ,file=file)


def decode(journal_bytes):
  """
  Decode a journal from CBOR into its data, checking only the shape common to
  every instruction language. Raises JournalError.
  """
  try:
    data = cbor2.loads(journal_bytes)
  except Exception as error:
    raise JournalError(f"the journal is not valid CBOR: {error}")
  if not isinstance(data ,dict):
    raise JournalError("the journal is not a map")
  if data.get("version") != JOURNAL_VERSION:
    raise JournalError(f"journal version {data.get('version')!r}; this Man_In_Grey reads version {JOURNAL_VERSION}")
  if not isinstance(data.get("instruction_language") ,str):
    raise JournalError("the journal names no instruction language")
  instruction_list = data.get("instruction_list")
  if not isinstance(instruction_list ,list):
    raise JournalError("the journal has no instruction list")
  for index ,instruction in enumerate(instruction_list):
    if not (isinstance(instruction ,dict) and isinstance(instruction.get("name") ,str) and isinstance(instruction.get("argument") ,dict)):
      raise JournalError(f"instruction {index} is not an instruction")
    for name ,value in instruction["argument"].items():
      if isinstance(value ,dict) and not Symbol.is_data(value):
        raise JournalError(f"instruction {index}: argument {name} is neither a value nor a symbol")
      if Symbol.is_data(value) and not (0 <= value["symbol"] < index):
        raise JournalError(f"instruction {index}: argument {name} names symbol {value['symbol']}, which no earlier instruction produces")
  return data


def instruction_line(index ,instruction):
  """One line describing an instruction, for printing a journal."""
  part = []
  for name ,value in instruction["argument"].items():
    if Symbol.is_data(value):
      part.append(f"{name}=@{value['symbol']}")
    elif isinstance(value ,(bytes ,bytearray)):
      part.append(f"{name}=<{len(value)} bytes>")
    elif name == "permission" and isinstance(value ,int):
      part.append(f"{name}={value:04o}")
    else:
      part.append(f"{name}={value!r}")
  composer = instruction.get("composer")
  return f"@{index:<3} {instruction['name']:<8} {' '.join(part)}" + (f"   ({composer})" if composer else "")
