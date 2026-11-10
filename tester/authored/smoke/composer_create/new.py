# create: allowed once; a second run is refused, as the file then exists.

def compose(prov ,journal_iface):
  file = journal_iface.declare("new_conf" ,"file")
  journal_iface.open(str(prov.cwd_dpath / "out") ,"new.conf" ,"create" ,prov.process_user ,0o600 ,file)
  journal_iface.write(file ,b"made once\n")
