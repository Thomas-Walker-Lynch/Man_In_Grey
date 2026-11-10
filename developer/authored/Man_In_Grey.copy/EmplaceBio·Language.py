# -*- mode: python; coding: utf-8; python-indent-offset: 2; indent-tabs-mode: nil -*-
"""
EmplaceBio·Language - the language definition of emplace_bio, a bio page.

Data only; see Language.py for its form. The composer's journal interface,
the guard and the interpreter all read it, and a journal carries its hash.

  display_name(name_text)          the page's title and heading; once
  paragraph()                      starts a paragraph
  text(run_text ,list_style)       a run of text in the current paragraph,
                                   with a list of style names
  picture(image)                   a PNG or JPEG image; at most once

No instruction produces a value, so every argument is a literal, and a
journal of this language has no result.
"""

NAME = "emplace_bio"

DEFINITION = {
  "list_type": [
    ["name_text" ,"text"]
    ,["run_text" ,"text"]
    ,["list_style" ,["list" ,"text"]]
    ,["image" ,"bytes"]
  ]
  ,"list_format": [
    ["format_name" ,["in" ,"name_text"]]
    ,["format_empty"]
    ,["format_run" ,["in" ,"run_text"] ,["in" ,"list_style"]]
    ,["format_image" ,["in" ,"image"]]
  ]
  ,"list_result": []
  ,"map_instruction": {
    "display_name": "format_name"
    ,"paragraph": "format_empty"
    ,"text": "format_run"
    ,"picture": "format_image"
  }
}
