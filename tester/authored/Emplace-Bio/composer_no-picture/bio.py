# composer_no-picture/bio.py - the test's bio page with no picture, which
# removes the picture an earlier run placed.

def compose(prov ,journal_iface):
  journal_iface.display_name("A. Tester")
  journal_iface.paragraph()
  journal_iface.text("No picture now." ,["emphasis"])
