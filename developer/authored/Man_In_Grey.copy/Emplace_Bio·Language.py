# -*- mode: python; coding: utf-8; python-indent-offset: 2; indent-tabs-mode: nil -*-
"""
Emplace_Bio·Language - the language definition of Emplace_Bio, a bio page.

Data only; see Language.py for its form. The composer's journal interface,
the guard and the interpreter all read it, and a journal carries its hash.

  display_name(name_text)          the page's title and heading; once
  paragraph()                      starts a paragraph
  text(run_text ,list__style)       a run of text in the current paragraph,
                                   with a list of style names
  picture(image)                   a PNG or JPEG image; at most once

No instruction produces a value, so every argument is a literal, and a
journal of this language has no result.
"""

NAME = "Emplace_Bio"

DEFINITION = {
  "list__type": [
    ["name_text" ,"text"]
    ,["run_text" ,"text"]
    ,["list__style" ,["list" ,"text"]]
    ,["image" ,"bytes"]
  ]
  ,"list__format": [
    ["format__name" ,["in" ,"name_text"]]
    ,["format__empty"]
    ,["format__run" ,["in" ,"run_text"] ,["in" ,"list__style"]]
    ,["format__image" ,["in" ,"image"]]
  ]
  ,"list__result": []
  ,"map__instruction": {
    "display_name": "format__name"
    ,"paragraph": "format__empty"
    ,"text": "format__run"
    ,"picture": "format__image"
  }
}
