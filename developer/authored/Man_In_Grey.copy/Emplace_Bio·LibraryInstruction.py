# -*- mode: python; coding: utf-8; python-indent-offset: 2; indent-tabs-mode: nil -*-
"""
Emplace_Bio·LibraryInstruction - the implementation of the Emplace_Bio instructions.

The interpreter makes one LibraryInstruction for each journal and calls its
functions, one for each operation specifier of the definition,
Emplace_Bio·Language.py, given each instruction's arguments by
position. They build the page up; finish() writes it from a fixed form, and
escapes every text it is given, so nothing a person gives becomes markup.
The page's file names come from the user name of account A, and its
directory from page_directory() among the guard's constraints.
"""

import html ,os ,stat ,urllib.parse

from Emplace_Bio·GuardCheck import STYLE ,picture_extension ,list_page_name

PAGE_PERMISSION = 0o644


# --------------------------------------------------------------------------------
# the interpreter's side: the page

def page(display_name ,list_paragraph ,picture_name):
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
  for list_run in list_paragraph:
    part.append("<p>")
    for content ,style in list_run:
      list_tag = [STYLE[s] for s in STYLE if s in style]
      part += [f"<{tag}>" for tag in list_tag]
      part.append(html.escape(content ,quote=False))
      part += [f"</{tag}>" for tag in reversed(list_tag)]
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

class LibraryInstruction:
  """
  The instructions of one journal: each adds to the page, and finish()
  writes the picture and the page to temporary files in the directory, then
  renames each into place, and removes a picture the page no longer shows.
  On an error, every temporary file not yet put in place is removed.
  """

  def __init__(self ,constraint ,gate_invoking_account ,log):
    self._constraint = constraint
    self._user_name = gate_invoking_account
    self._log = log
    self._display_name = None
    self._list_paragraph = []
    self._picture = None

  def display_name(self ,name_text):
    self._display_name = name_text

  def paragraph(self):
    self._list_paragraph.append([])

  def text(self ,run_text ,list_style):
    self._list_paragraph[-1].append((run_text ,list_style))

  def picture(self ,image):
    self._picture = image

  def finish(self):
    log ,user_name = self._log ,self._user_name
    directory = self._constraint.page_directory()
    picture = self._picture
    picture_name = user_name + picture_extension(picture) if picture is not None else None
    page_name = user_name + ".html"

    dirfd = None
    pending = []   # (temporary ,target)
    try:
      dirfd = os.open(directory ,os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
      if picture_name:
        pending.append((_write_temporary(dirfd ,picture_name ,picture) ,picture_name))
      pending.append((_write_temporary(dirfd ,page_name ,page(self._display_name ,self._list_paragraph ,picture_name).encode("utf-8")) ,page_name))
      while pending:
        tmp ,target = pending[0]
        os.rename(tmp ,target ,src_dir_fd=dirfd ,dst_dir_fd=dirfd)
        pending.pop(0)
        log("emplaced" ,f"{directory}/{target}")
      for name in list_page_name(user_name)[1:]:
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
    finally:
      for tmp ,_ in pending:
        try:
          os.unlink(tmp ,dir_fd=dirfd)
        except OSError:
          pass
      if dirfd is not None:
        os.close(dirfd)
