# A mode the language does not have. Its type, text, is right, so the journal
# reaches the gate, and the guard's language check refuses it.

def compose(prov ,journal_iface):
  file = journal_iface.declare("file" ,"file")
  journal_iface.open(str(prov.dirpa__cwd / "out") ,"unbound_conf" ,"overwrite" ,prov.process_user ,0o444 ,file)
  journal_iface.write(file ,b"not to be written\n")
