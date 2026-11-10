# A literal of the wrong type, a permission given as text: the journal interface
# refuses the instruction when it is placed, and no journal reaches the gate.

def compose(prov ,journal_iface):
  file = journal_iface.declare("file" ,"file")
  journal_iface.open(str(prov.cwd_dpath / "out") ,"unbound_conf" ,"replace_keep" ,prov.process_user ,"0444" ,file)
