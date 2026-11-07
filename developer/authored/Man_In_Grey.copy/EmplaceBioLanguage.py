# -*- mode: python; coding: utf-8; python-indent-offset: 2; indent-tabs-mode: nil -*-
"""
EmplaceBioLanguage - the emplace_bio instruction language: a bio page.

A host publishes one bio page for each permitted account, as
<user_name>.html in a directory its web server serves, with the picture
beside it as <user_name>.png or <user_name>.jpg. The web server's account
owns the directory, so a person cannot write there. He gives his page's
display name, text and picture as instructions, and the emplace_bio gate,
owned by the web server's account, places the page.

A journal names no file. The file names come from the user name of
account A, which the gate gives the interpreter, and the directory comes
from page_directory() at the top of the guard. The interpreter writes the
HTML itself, from a fixed form, and escapes every text it is given, so
nothing a person gives becomes markup. Decoration travels out of band, as a
list of styles beside each run of text, and each style becomes one fixed
tag with no attribute.

  display_name(text)       the page's title and heading; required, once
  paragraph()              starts a paragraph
  text(content ,style)     a run of text in the current paragraph, with a list
                           of styles drawn from STYLE; an empty list is plain text
  picture(content)         a PNG or JPEG image; at most once

The journal describes the whole page: a run that gives no picture removes
the picture an earlier run placed.

The module has two halves. The composer half is JournalInterface, which
checks every argument when the call is made and raises JournalError on a
wrong one. The interpreter half holds the checks the guard makes of a
journal received as data, and the execution the interpreter carries out.

The constraints are predicates written at the top of the guard,
guard_emplace_bio.py: is_allowed_account, is_allowed_text_size and
is_allowed_picture_size, and page_directory(), where the pages go.
"""

import html ,os ,stat ,urllib.parse

from Journal import JournalError ,has_control ,clean

NAME = "emplace_bio"

# each style and its tag, in the order the tags nest, outermost first
STYLE = {
  "strong": "strong"
  ,"emphasis": "em"
  ,"underline": "u"
  ,"strikethrough": "s"
}

ARGUMENT = {
  "display_name": ("text" ,)
  ,"paragraph": ()
  ,"text": ("content" ,"style")
  ,"picture": ("content" ,)
}

DISPLAY_NAME_MAX = 200     # characters

SIGNATURE = (
  (b"\x89PNG\r\n\x1a\n" ,".png")
  ,(b"\xff\xd8\xff" ,".jpg")
)

PAGE_PERMISSION = 0o644


# --------------------------------------------------------------------------------
# argument checks, shared by both halves

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
# composer half

class JournalInterface:
  """
  The journal interface of the emplace_bio language. A composer is given
  one, and places instructions with its four functions.
  """

  def __init__(self ,journal ,working_dpath):
    self._journal = journal
    self._in_paragraph = False

  def display_name(self ,text):
    problem = display_name_problem(text)
    if problem: raise JournalError(f"display_name: {problem}")
    self._journal.place("display_name" ,{"text": text})

  def paragraph(self):
    self._journal.place("paragraph" ,{})
    self._in_paragraph = True

  def text(self ,content ,style=()):
    if not self._in_paragraph:
      raise JournalError("text: no paragraph has been started; place paragraph() first")
    problem = content_problem(content)
    if problem: raise JournalError(f"text: {problem}")
    if isinstance(style ,str) or not hasattr(style ,"__iter__"):
      raise JournalError("text: style is to be a list of style names")
    style = list(style)
    problem = style_problem(style)
    if problem: raise JournalError(f"text: {problem}")
    style = [s for s in STYLE if s in style]
    self._journal.place("text" ,{"content": content ,"style": style})

  def picture(self ,content):
    if not isinstance(content ,(bytes ,bytearray)):
      raise JournalError("picture: content is to be the bytes of a PNG or JPEG file")
    content = bytes(content)
    if picture_extension(content) is None:
      raise JournalError("picture: content is neither a PNG nor a JPEG file")
    self._journal.place("picture" ,{"content": content})


# --------------------------------------------------------------------------------
# interpreter half: the guard's checks

def check_wellformed(data):
  problem_list = []
  count = {name: 0 for name in ARGUMENT}
  in_paragraph = False
  run_count = 0
  for index ,instruction in enumerate(data["instruction_list"]):
    name ,argument = instruction["name"] ,instruction["argument"]
    if name not in ARGUMENT:
      problem_list.append(f"@{index}: unknown instruction {clean(repr(name))}"); continue
    # the order of the instructions, checked whatever their arguments
    count[name] += 1
    if name == "paragraph":
      if in_paragraph and run_count == 0:
        problem_list.append(f"@{index} paragraph: the paragraph before it holds no text")
      in_paragraph ,run_count = True ,0
    elif name == "text":
      if not in_paragraph:
        problem_list.append(f"@{index} text: no paragraph has been started")
      run_count += 1
    if set(argument) != set(ARGUMENT[name]):
      problem_list.append(f"@{index} {name}: arguments {clean(sorted(argument))}, expected {sorted(ARGUMENT[name])}"); continue
    if name == "display_name":
      problem = display_name_problem(argument["text"])
      if problem: problem_list.append(f"@{index} display_name: {problem}")
    elif name == "text":
      for problem in (content_problem(argument["content"]) ,style_problem(argument["style"])):
        if problem: problem_list.append(f"@{index} text: {problem}")
    elif name == "picture":
      if not isinstance(argument["content"] ,(bytes ,bytearray)) or not argument["content"]:
        problem_list.append(f"@{index} picture: content is not bytes")
  if count["display_name"] != 1:
    problem_list.append(f"the journal gives the display name {count['display_name']} times; it is given once")
  if count["paragraph"] == 0:
    problem_list.append("the journal has no paragraph")
  elif run_count == 0:
    problem_list.append("the last paragraph holds no text")
  if count["picture"] > 1:
    problem_list.append(f"the journal gives {count['picture']} pictures; it gives at most one")
  return problem_list

def page_directory_problem(directory):
  if not isinstance(directory ,str) or not directory.startswith("/") or os.path.normpath(directory) != directory:
    return f"page_directory() gives {clean(repr(directory))}, not an absolute directory in normal form"
  return None

def check_constraint(data ,constraint ,gate_invoking_account):
  "constraint is the guard, which holds the predicates; a predicate allows only by answering True"
  if constraint.is_allowed_account(gate_invoking_account) is not True:
    return [f"gate invoking account {clean(repr(gate_invoking_account))} is not allowed to give journals to this gate"]
  problem_list = []
  problem = page_directory_problem(constraint.page_directory())
  if problem: problem_list.append(problem)
  text_bytes = 0
  for instruction in data["instruction_list"]:
    name ,argument = instruction["name"] ,instruction["argument"]
    if name == "display_name":
      text_bytes += len(argument["text"].encode("utf-8"))
    elif name == "text":
      text_bytes += len(argument["content"].encode("utf-8"))
    elif name == "picture" and constraint.is_allowed_picture_size(len(argument["content"])) is not True:
      problem_list.append(f"the picture is {len(argument['content'])} bytes, which is not allowed")
  if constraint.is_allowed_text_size(text_bytes) is not True:
    problem_list.append(f"the text is {text_bytes} bytes, which is not allowed")
  return problem_list

def check_content(data):
  problem_list = []
  for index ,instruction in enumerate(data["instruction_list"]):
    if instruction["name"] == "picture" and picture_extension(instruction["argument"]["content"]) is None:
      problem_list.append(f"@{index} picture: the content is neither a PNG nor a JPEG file")
  return problem_list

def page_name_list(user_name):
  "the files a page of this account can occupy"
  return [user_name + ".html"] + [user_name + extension for _ ,extension in SIGNATURE]

def check_filesystem(data ,constraint ,gate_invoking_account):
  problem_list = []
  if has_control(gate_invoking_account) or gate_invoking_account.startswith("."):
    return [f"the account name {clean(repr(gate_invoking_account))} cannot name a page"]
  directory = constraint.page_directory()
  if not os.path.isdir(directory):
    return [f"{directory} is not a directory"]
  if os.path.realpath(directory) != directory:
    return [f"{directory} passes through a symbolic link"]
  # access() alone answers for the real uid; effective_ids asks for the effective uid, which writes
  if not os.access(directory ,os.W_OK | os.X_OK ,effective_ids=os.access in os.supports_effective_ids):
    problem_list.append(f"{directory} cannot be written by the effective uid's account")
  for name in page_name_list(gate_invoking_account):
    try:
      st = os.lstat(os.path.join(directory ,name))
    except FileNotFoundError:
      continue
    if not stat.S_ISREG(st.st_mode):
      problem_list.append(f"{directory}/{name} exists and is not a regular file")
  return problem_list

CHECK = (
  ("wellformed" ,lambda data ,constraint ,gate_invoking_account: check_wellformed(data))
  ,("constraint" ,check_constraint)
  ,("content" ,lambda data ,constraint ,gate_invoking_account: check_content(data))
  ,("filesystem" ,check_filesystem)
)


# --------------------------------------------------------------------------------
# interpreter half: the page

def page(display_name ,paragraph_list ,picture_name):
  """
  The HTML of a page. Every text given is escaped; every tag comes from this
  function or from STYLE.
  """
  name = html.escape(display_name ,quote=True)
  part = [
    "<!DOCTYPE html>\n"
    ,"<html>\n<head>\n"
    ,'<meta charset="utf-8">\n'
    ,'<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; img-src \'self\'">\n'
    ,'<meta name="viewport" content="width=device-width, initial-scale=1">\n'
    ,"<title>" ,name ,"</title>\n"
    ,"</head>\n<body>\n"
    ,"<h1>" ,name ,"</h1>\n"
  ]
  if picture_name:
    part += ['<img src="' ,html.escape(urllib.parse.quote(picture_name) ,quote=True) ,'" alt="' ,name ,'">\n']
  for run_list in paragraph_list:
    part.append("<p>")
    for content ,style in run_list:
      tag_list = [STYLE[s] for s in STYLE if s in style]
      part += [f"<{tag}>" for tag in tag_list]
      part.append(html.escape(content ,quote=False))
      part += [f"</{tag}>" for tag in reversed(tag_list)]
    part.append("</p>\n")
  part.append("</body>\n</html>\n")
  return "".join(part)

def _write_temporary(dirfd ,target ,content):
  tmp = f".{target}.Man_In_Grey.{os.getpid()}"
  fd = os.open(tmp ,os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW ,0o600 ,dir_fd=dirfd)
  try:
    view = memoryview(content)
    while view:
      view = view[os.write(fd ,view):]
    os.fchmod(fd ,PAGE_PERMISSION)
    os.fsync(fd)
  finally:
    os.close(fd)
  return tmp

def execute(data ,log ,constraint ,gate_invoking_account):
  """
  Write the picture and the page to temporary files in the directory, then
  rename each into place, and remove a picture the page no longer shows.
  log is given a tag and a message for each thing done. Returns 0, or 1 on
  an error, removing every temporary file not yet put in place.
  """
  user_name = gate_invoking_account
  directory = constraint.page_directory()
  display_name ,paragraph_list ,picture = None ,[] ,None
  for instruction in data["instruction_list"]:
    name ,argument = instruction["name"] ,instruction["argument"]
    if name == "display_name":
      display_name = argument["text"]
    elif name == "paragraph":
      paragraph_list.append([])
    elif name == "text":
      paragraph_list[-1].append((argument["content"] ,argument["style"]))
    elif name == "picture":
      picture = argument["content"]
  picture_name = user_name + picture_extension(picture) if picture is not None else None
  page_name = user_name + ".html"

  dirfd = None
  pending = []   # (temporary ,target)
  try:
    dirfd = os.open(directory ,os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    if picture_name:
      pending.append((_write_temporary(dirfd ,picture_name ,picture) ,picture_name))
    pending.append((_write_temporary(dirfd ,page_name ,page(display_name ,paragraph_list ,picture_name).encode("utf-8")) ,page_name))
    while pending:
      tmp ,target = pending[0]
      os.rename(tmp ,target ,src_dir_fd=dirfd ,dst_dir_fd=dirfd)
      pending.pop(0)
      log("emplaced" ,f"{directory}/{target}")
    for name in page_name_list(user_name)[1:]:
      if name == picture_name:
        continue
      try:
        st = os.lstat(name ,dir_fd=dirfd)
      except FileNotFoundError:
        continue
      if stat.S_ISREG(st.st_mode):
        os.unlink(name ,dir_fd=dirfd)
        log("removed" ,f"{directory}/{name}")
    os.fsync(dirfd)
    return 0
  except OSError as error:
    log("execution_failed" ,str(error))
    for tmp ,_ in pending:
      try:
        os.unlink(tmp ,dir_fd=dirfd)
      except OSError:
        pass
    return 1
  finally:
    if dirfd is not None:
      os.close(dirfd)
