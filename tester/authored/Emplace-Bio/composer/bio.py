# composer/bio.py - the test's bio page, with every style, text that looks
# like markup, and the PNG picture.

from pathlib import Path

DISPLAY_NAME = "A. Tester <test> & Co"

BIO = [
  [("I write " ,[]) ,("compilers" ,["emphasis"]) ,(" and sail " ,[]) ,("boats" ,["strong" ,"underline"]) ,("." ,[])]
  ,[("Markup in a bio is only text: <script>alert(1)</script> & a < b. " ,[]) ,("This was struck." ,["strikethrough"])]
]

def compose(prov ,journal_iface):
  journal_iface.display_name(DISPLAY_NAME)
  for paragraph in BIO:
    journal_iface.paragraph()
    for content ,style in paragraph:
      journal_iface.text(content ,style)
  journal_iface.picture((Path(prov.composer_dir_dpath).parent / "picture.png").read_bytes())
