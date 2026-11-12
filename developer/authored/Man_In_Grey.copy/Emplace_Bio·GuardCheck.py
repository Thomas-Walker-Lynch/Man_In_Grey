# -*- mode: python; coding: utf-8; python-indent-offset: 2; indent-tabs-mode: nil -*-
"""
Emplace_Bio·GuardCheck - the guard's checks of the Emplace_Bio instruction language: a bio page.

A host publishes one bio page for each permitted account, as
<user_name>.html in a directory its web server serves, with the picture
beside it as <user_name>.png or <user_name>.jpg. The web server's account
owns the directory, so a person cannot write there. He gives his page's
display name, text and picture as instructions, and the Emplace_Bio gate,
owned by the web server's account, places the page.

A journal names no file. The file names come from the user name of
account A, which the gate gives the interpreter, and the directory comes
from page_directory() at the top of the guard. The interpreter writes the
HTML itself, from a fixed form, and escapes every text it is given, so
nothing a person gives becomes markup. Decoration travels out of band, as a
list of styles beside each run of text, and each style becomes one fixed
tag with no attribute.

The instructions and their types are in Emplace_Bio·Language.py. The
journal describes the whole page: a run that gives no picture removes the
picture an earlier run placed.

This module holds the guard's checks of the language, made after the
well-formed guard has checked the journal against the definition. They are
LIST_CHECK:

  language     what the definition cannot say: the display name is given
               once, text comes only within a paragraph and no paragraph is
               empty, at most one picture, every style one of STYLE and none
               twice, and no control character in any text
  constraint   the predicates at the top of the guard, Emplace_Bio·Guard.py:
               is_allowed_account, is_allowed_text_size and
               is_allowed_picture_size, and page_directory(), where the
               pages go
  content      the picture is a PNG or a JPEG
  filesystem   the page directory, and the files the page can occupy

The implementation of the instructions is in Emplace_Bio·LibraryInstruction.py.
"""


import os ,stat

from Journal import has_control ,clean

# each style and its tag, in the order the tags nest, outermost first
STYLE = {
  "strong": "strong"
  ,"emphasis": "em"
  ,"underline": "u"
  ,"strikethrough": "s"
}


DISPLAY_NAME_MAX = 200     # characters

SIGNATURE = (
  (b"\x89PNG\r\n\x1a\n" ,".png")
  ,(b"\xff\xd8\xff" ,".jpg")
)


# --------------------------------------------------------------------------------
# value checks

def display_name_problem(value):
  if not isinstance(value ,str) or not value.strip():
    return "the display name is to be text that is not empty"
  if has_control(value):
    return f"the display name {clean(value)} holds a control character"
  if len(value) > DISPLAY_NAME_MAX:
    return f"the display name is longer than {DISPLAY_NAME_MAX} characters"
  return None

def content_problem(value):
  if not isinstance(value ,str) or not value:
    return "content is to be text that is not empty"
  if has_control(value):
    return f"content {clean(value)} holds a control character; a new paragraph is the instruction paragraph()"
  return None

def style_problem(value):
  if not isinstance(value ,list) or not all(isinstance(s ,str) for s in value):
    return "style is to be a list of style names"
  for s in value:
    if s not in STYLE:
      return f"style {clean(repr(s))} is not one of {', '.join(STYLE)}"
  if len(set(value)) != len(value):
    return "style names a style twice"
  return None

def picture_extension(content):
  "the extension for the picture's format, or None when it is neither PNG nor JPEG"
  for signature ,extension in SIGNATURE:
    if content.startswith(signature):
      return extension
  return None


# --------------------------------------------------------------------------------
# the guard's checks, each given the instructions as Journal.InstructionView

def check_language(list_instruction_view ,data ,constraint ,gate_invoking_account):
  """
  What the definition cannot say. No instruction of this language writes a
  variable, so the well-formed guard has already ensured every argument is
  a literal.
  """
  list_problem = []
  count = {"display_name": 0 ,"paragraph": 0 ,"text": 0 ,"picture": 0}
  in_paragraph = False
  run_count = 0
  for view in list_instruction_view:
    index ,name = view.index ,view.operation
    value = [argument.value for argument in view.list_argument]
    count[name] += 1
    if name == "paragraph":
      if in_paragraph and run_count == 0:
        list_problem.append(f"@{index} paragraph: the paragraph before it holds no text")
      in_paragraph ,run_count = True ,0
    elif name == "text":
      if not in_paragraph:
        list_problem.append(f"@{index} text: no paragraph has been started")
      run_count += 1
      for problem in (content_problem(value[0]) ,style_problem(value[1])):
        if problem: list_problem.append(f"@{index} text: {problem}")
    elif name == "display_name":
      problem = display_name_problem(value[0])
      if problem: list_problem.append(f"@{index} display_name: {problem}")
    elif name == "picture" and not value[0]:
      list_problem.append(f"@{index} picture: the picture is empty")
  if count["display_name"] != 1:
    list_problem.append(f"the journal gives the display name {count['display_name']} times; it is given once")
  if count["paragraph"] == 0:
    list_problem.append("the journal has no paragraph")
  elif run_count == 0:
    list_problem.append("the last paragraph holds no text")
  if count["picture"] > 1:
    list_problem.append(f"the journal gives {count['picture']} pictures; it gives at most one")
  return list_problem

def page_directory_problem(directory):
  if not isinstance(directory ,str) or not directory.startswith("/") or os.path.normpath(directory) != directory:
    return f"page_directory() gives {clean(repr(directory))}, not an absolute directory in normal form"
  return None

def check_constraint(list_instruction_view ,data ,constraint ,gate_invoking_account):
  "constraint is the guard, which holds the predicates; a predicate allows only by answering True"
  if constraint.is_allowed_account(gate_invoking_account) is not True:
    return [f"gate invoking account {clean(repr(gate_invoking_account))} is not allowed to give journals to this gate"]
  list_problem = []
  problem = page_directory_problem(constraint.page_directory())
  if problem: list_problem.append(problem)
  text_bytes = 0
  for view in list_instruction_view:
    value = view.list_argument[0].value if view.list_argument else None
    if view.operation in ("display_name" ,"text"):
      text_bytes += len(value.encode("utf-8"))
    elif view.operation == "picture" and constraint.is_allowed_picture_size(len(value)) is not True:
      list_problem.append(f"the picture is {len(value)} bytes, which is not allowed")
  if constraint.is_allowed_text_size(text_bytes) is not True:
    list_problem.append(f"the text is {text_bytes} bytes, which is not allowed")
  return list_problem

def check_content(list_instruction_view ,data ,constraint ,gate_invoking_account):
  list_problem = []
  for view in list_instruction_view:
    if view.operation == "picture" and picture_extension(view.list_argument[0].value) is None:
      list_problem.append(f"@{view.index} picture: the content is neither a PNG nor a JPEG file")
  return list_problem

def list_page_name(user_name):
  "the files a page of this account can occupy"
  return [user_name + ".html"] + [user_name + extension for _ ,extension in SIGNATURE]

def check_filesystem(list_instruction_view ,data ,constraint ,gate_invoking_account):
  list_problem = []
  if has_control(gate_invoking_account) or gate_invoking_account.startswith("."):
    return [f"the account name {clean(repr(gate_invoking_account))} cannot name a page"]
  directory = constraint.page_directory()
  if not os.path.isdir(directory):
    return [f"{directory} is not a directory"]
  if os.path.realpath(directory) != directory:
    return [f"{directory} passes through a symbolic link"]
  # access() alone answers for the real uid; effective_ids asks for the effective uid, which writes
  if not os.access(directory ,os.W_OK | os.X_OK ,effective_ids=os.access in os.supports_effective_ids):
    list_problem.append(f"{directory} cannot be written by the effective uid's account")
  for name in list_page_name(gate_invoking_account):
    try:
      st = os.lstat(os.path.join(directory ,name))
    except FileNotFoundError:
      continue
    if not stat.S_ISREG(st.st_mode):
      list_problem.append(f"{directory}/{name} exists and is not a regular file")
  return list_problem

LIST_CHECK = (
  ("language" ,check_language)
  ,("constraint" ,check_constraint)
  ,("content" ,check_content)
  ,("filesystem" ,check_filesystem)
)
