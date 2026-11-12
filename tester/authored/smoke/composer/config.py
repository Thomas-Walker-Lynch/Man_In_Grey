# config.py - the smoke test's composer. It writes three files and removes one,
# then makes the counts its result:
#   out/obsolete.conf     unlink: the first run removes it; the second finds nothing to remove
#   out/unbound_conf      replace-keep: the second run keeps the first run's file as a backup
#   out/net/unbound.conf  replace: the second run discards the first run's file; written in two parts
#   out/web/nginx.conf    replace-keep
# Each file is a variable of the type file, which open writes and write reads and writes.

def compose(prov ,journal_iface):
  out = str(prov.cwd__dpath / "out")
  person = prov.process_user
  journal_iface.unlink(out ,"obsolete.conf")

  unbound_conf = journal_iface.declare("unbound_conf" ,"file")
  journal_iface.open(out ,"unbound_conf" ,"replace-keep" ,person ,0o444 ,unbound_conf)
  journal_iface.write(unbound_conf ,b"server:\n  do-ip6: no\n")

  net = journal_iface.declare("net_unbound_conf" ,"file")
  journal_iface.open(out + "/net" ,"unbound.conf" ,"replace" ,person ,0o444 ,net)
  journal_iface.write(net ,b"server:\n")
  journal_iface.write(net ,b"  verbosity: 1\n")

  web = journal_iface.declare("web_nginx_conf" ,"file")
  journal_iface.open(out + "/web" ,"nginx.conf" ,"replace-keep" ,person ,0o644 ,web)
  journal_iface.write(web ,b"events {}\nhttp { server { listen 8080; } }\n")

  summary = journal_iface.declare("summary" ,"summary")
  journal_iface.summary(summary)
  journal_iface.result(summary)
