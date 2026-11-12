# composer_jpeg/bio.py - the test's bio page with the JPEG picture, which
# replaces the PNG an earlier run placed.

from pathlib import Path

def compose(prov ,journal_iface):
  journal_iface.display_name("A. Tester")
  journal_iface.paragraph()
  journal_iface.text("Now with a JPEG." ,[])
  journal_iface.picture((Path(prov.composer_dir_dpath).parent / "picture.jpg").read_bytes())
