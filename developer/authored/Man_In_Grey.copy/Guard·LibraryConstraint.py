# -*- mode: python; coding: utf-8; python-indent-offset: 2; indent-tabs-mode: nil -*-
"""
Guard·LibraryConstraint - predicates that recur among guards' constraints.

A guard's constraints are written at the top of the guard itself, as
predicates such as is__allowed_account(user_name). This library holds the
predicates many guards would otherwise each write: membership of a group,
a path within a directory, a permission within a limit. A guard imports it
after its ownership check, as it imports its other modules, and its
constraints call it by name, as
Guard·LibraryConstraint.is__group_member(user_name ,"bio").
"""

import grp ,os ,pwd


def is__group_member(user_name ,group_name):
  """
  True when the account is a member of the group by the group database:
  listed in /etc/group as a member, or having the group as its primary group.
  """
  try:
    group = grp.getgrnam(group_name)
  except KeyError:
    return False
  if user_name in group.gr_mem:
    return True
  try:
    return pwd.getpwnam(user_name).pw_gid == group.gr_gid
  except KeyError:
    return False

def has__real_group(group_name):
  """
  True when the gate's real gid or supplementary groups include the group.
  These are what the program that invoked the gate held, which the kernel
  passes on: a session started before the account joined the group does not
  hold it, though is__group_member already says yes.
  """
  try:
    gid = grp.getgrnam(group_name).gr_gid
  except KeyError:
    return False
  return gid == os.getgid() or gid in os.getgroups()

def is__path_under(path ,directory):
  """
  True when path is directory or lies within it. Both are to be absolute and
  in normal form, as the guard's wellformed check makes a journal's paths.
  """
  if not (isinstance(path ,str) and isinstance(directory ,str)):
    return False
  if not (path.startswith("/") and directory.startswith("/")):
    return False
  if os.path.normpath(path) != path or os.path.normpath(directory) != directory:
    return False
  return path == directory or path.startswith(directory.rstrip("/") + "/")

def has__permission_within(permission ,limit):
  """
  True when permission sets no bit that limit does not: 0o644 and 0o600 are
  within 0o644, and 0o4755, setuid, is within neither 0o644 nor 0o755.
  """
  return isinstance(permission ,int) and not isinstance(permission ,bool) and permission & ~limit == 0
