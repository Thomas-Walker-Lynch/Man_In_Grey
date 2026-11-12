# -*- mode: python; coding: utf-8; python-indent-offset: 2; indent-tabs-mode: nil -*-
"""
Smoke·LibraryInstruction - the implementation of the Smoke instructions.

The interpreter makes one LibraryInstruction for each journal and calls its
functions, one for each operation specifier of the definition,
Smoke·Language.py, given each instruction's arguments by position.
Each opened file is written to a temporary file in its directory, and
finish() puts every opened file in place, each in one step.
"""

import os ,pwd ,time

from Smoke·GuardCheck import is_absent


# --------------------------------------------------------------------------------
# the interpreter's side

def _backup_name(dirfd ,name):
  stamp = time.strftime("%Y%m%dT%H%M%SZ" ,time.gmtime())
  candidate ,n = f"{name}.{stamp}" ,1
  while True:
    try:
      os.lstat(candidate ,dir_fd=dirfd)
    except FileNotFoundError:
      return candidate
    candidate ,n = f"{name}.{stamp}.{n}" ,n + 1

class LibraryInstruction:
  """
  The instructions of one journal. open makes a temporary file in its directory and
  writes the file's handle, a number standing for the open file, to its box;
  write appends to the file the handle stands for; finish() puts every opened
  file in place, each in one step; release() closes what is open and removes
  every temporary file not put in place. The Smoke language needs nothing
  from its guard's constraints to execute.
  """

  def __init__(self ,constraint ,gate_invoking_account ,log):
    self._log = log
    self._opened = []   # by handle: {dirfd ,fd ,tmp ,directory ,name ,mode ,owner ,permission}
    self._unlink_count = 0

  def open(self ,directory ,file_name ,mode ,account_name ,permission ,file):
    handle = len(self._opened)
    dirfd = os.open(directory ,os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    record = {"dirfd": dirfd ,"fd": None ,"tmp": None ,"directory": directory ,"name": file_name
              ,"mode": mode ,"owner": account_name ,"permission": permission}
    self._opened.append(record)
    tmp = f".{file_name}.Man_In_Grey.{os.getpid()}.{handle}"
    record["fd"] = os.open(tmp ,os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW ,0o600 ,dir_fd=dirfd)
    record["tmp"] = tmp
    file.append(handle)

  def write(self ,file ,content):
    fd ,view = self._opened[file[0]]["fd"] ,memoryview(content)
    while view:
      view = view[os.write(fd ,view):]

  def unlink(self ,directory ,file_name):
    dirfd = os.open(directory ,os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
      if not is_absent(dirfd ,file_name):
        os.unlink(file_name ,dir_fd=dirfd)
        os.fsync(dirfd)
        self._log("unlinked" ,f"{directory}/{file_name}")
    finally:
      os.close(dirfd)
    self._unlink_count += 1

  def summary(self ,summary):
    summary.append({"open_count": len(self._opened) ,"unlink_count": self._unlink_count})

  def finish(self):
    for record in self._opened:
      dirfd ,fd ,tmp ,target = record["dirfd"] ,record["fd"] ,record["tmp"] ,record["name"]
      where = f"{record['directory']}/{target}"
      account = pwd.getpwnam(record["owner"])
      os.fsync(fd)
      # Only root can give a file away. Any other interpreter account makes
      # files it already owns, so the owner is changed only when it differs.
      st = os.fstat(fd)
      if (st.st_uid ,st.st_gid) != (account.pw_uid ,account.pw_gid):
        try:
          os.fchown(fd ,account.pw_uid ,account.pw_gid)
        except OSError as error:
          raise OSError(error.errno ,f"{where}: cannot give it the owner {record['owner']} and that account's group: {error.strerror}")
      os.fchmod(fd ,record["permission"])
      os.fsync(fd)
      os.close(fd); record["fd"] = None
      if record["mode"] == "create":
        os.link(tmp ,target ,src_dir_fd=dirfd ,dst_dir_fd=dirfd ,follow_symlinks=False)
        os.unlink(tmp ,dir_fd=dirfd)
        self._log("created" ,where)
      else:
        kept = None
        if record["mode"] == "replace_keep" and not is_absent(dirfd ,target):
          kept = _backup_name(dirfd ,target)
          os.link(target ,kept ,src_dir_fd=dirfd ,dst_dir_fd=dirfd ,follow_symlinks=False)
        os.rename(tmp ,target ,src_dir_fd=dirfd ,dst_dir_fd=dirfd)
        self._log("replaced" ,where + (f" (kept as {kept})" if kept else ""))
      record["tmp"] = None
      os.fsync(dirfd)

  def release(self):
    for record in self._opened:
      if record["fd"] is not None:
        os.close(record["fd"])
      if record["tmp"] is not None:
        try:
          os.unlink(record["tmp"] ,dir_fd=record["dirfd"])
        except OSError:
          pass
      os.close(record["dirfd"])
