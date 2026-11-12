# One file the constraints allow, and one they do not. The whole journal is refused.

def compose(prov ,journal_iface):
  out = str(prov.cwd__dpath / "out")
  allowed = journal_iface.declare("allowed" ,"file")
  journal_iface.open(out ,"unbound_conf" ,"replace-keep" ,prov.process_user ,0o444 ,allowed)
  journal_iface.write(allowed ,b"this is not to be written\n")
  forbidden = journal_iface.declare("forbidden" ,"file")
  journal_iface.open(out ,"forbidden.conf" ,"replace" ,prov.process_user ,0o644 ,forbidden)
  journal_iface.write(forbidden ,b"nor this\n")
