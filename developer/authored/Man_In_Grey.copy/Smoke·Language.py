# -*- mode: python; coding: utf-8; python-indent-offset: 2; indent-tabs-mode: nil -*-
"""
Smoke·Language - the language definition of Smoke, the tester's smoke test.

Data only; see Language.py for its form. A constrained form of the POSIX
file interface, made to exercise every part of the journal's form: a handle
an instruction produces, an argument both read and written, and a result.

  open(dirpa ,filen ,mode ,account_name ,permission ,>file)
                       opens a file to be put in place after the last
                       instruction, and writes its handle to the variable file
  write(<>file ,content)
                       appends content to the file; the file is read and
                       written, as the instruction changes it
  unlink(dirpa ,filen)
                       removes a file
  summary(>summary)    writes the counts of the files opened and removed so
                       far, which a journal can make its result
"""

NAME = "Smoke"

DEFINITION = {
  "list__type": [
    ["dirpa" ,"text"]
    ,["filen" ,"text"]
    ,["mode" ,"text"]
    ,["account_name" ,"text"]
    ,["permission" ,"integer"]
    ,["file" ,"handle"]
    ,["content" ,"bytes"]
    ,["summary" ,["dictionary" ,["count_of__open" ,"integer"] ,["count_of__unlink" ,"integer"]]]
  ]
  ,"list__format": [
    ["format__open" ,["in" ,"dirpa"] ,["in" ,"filen"] ,["in" ,"mode"] ,["in" ,"account_name"] ,["in" ,"permission"] ,["out" ,"file"]]
    ,["format__write" ,["in-out" ,"file"] ,["in" ,"content"]]
    ,["format__unlink" ,["in" ,"dirpa"] ,["in" ,"filen"]]
    ,["format__summary" ,["out" ,"summary"]]
  ]
  ,"list__result": ["summary"]
  ,"map__instruction": {
    "open": "format__open"
    ,"write": "format__write"
    ,"unlink": "format__unlink"
    ,"summary": "format__summary"
  }
}
