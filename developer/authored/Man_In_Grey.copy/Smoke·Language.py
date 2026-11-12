# -*- mode: python; coding: utf-8; python-indent-offset: 2; indent-tabs-mode: nil -*-
"""
Smoke·Language - the language definition of Smoke, the tester's smoke test.

Data only; see Language.py for its form. A constrained form of the POSIX
file interface, made to exercise every part of the journal's form: a handle
an instruction produces, an argument both read and written, and a result.

  open(directory ,file_name ,mode ,account_name ,permission ,>file)
                       opens a file to be put in place after the last
                       instruction, and writes its handle to the variable file
  write(<>file ,content)
                       appends content to the file; the file is read and
                       written, as the instruction changes it
  unlink(directory ,file_name)
                       removes a file
  summary(>summary)    writes the counts of the files opened and removed so
                       far, which a journal can make its result
"""

NAME = "Smoke"

DEFINITION = {
  "list_type": [
    ["directory" ,"text"]
    ,["file_name" ,"text"]
    ,["mode" ,"text"]
    ,["account_name" ,"text"]
    ,["permission" ,"integer"]
    ,["file" ,"handle"]
    ,["content" ,"bytes"]
    ,["summary" ,["dictionary" ,["open_count" ,"integer"] ,["unlink_count" ,"integer"]]]
  ]
  ,"list_format": [
    ["format_open" ,["in" ,"directory"] ,["in" ,"file_name"] ,["in" ,"mode"] ,["in" ,"account_name"] ,["in" ,"permission"] ,["out" ,"file"]]
    ,["format_write" ,["in-out" ,"file"] ,["in" ,"content"]]
    ,["format_unlink" ,["in" ,"directory"] ,["in" ,"file_name"]]
    ,["format_summary" ,["out" ,"summary"]]
  ]
  ,"list_result": ["summary"]
  ,"map_instruction": {
    "open": "format_open"
    ,"write": "format_write"
    ,"unlink": "format_unlink"
    ,"summary": "format_summary"
  }
}
