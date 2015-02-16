CPKTools
========

Utilities to pack/unpack a CRI-CPK archive file written in python for linux
use.

Tools
-----

* `cpkunpack.py` unpack a cpk file

  It is recommended that redirect the `stdout` of the script to a file
  (the script print the HEADER, TOC, ITOC and ETOC information to `stdout`)

* `screxport.py` search and extract shift-jis string from script file
  (scr.bin) with tag prefixed

  The search is based on some properties of embedded text, thus **cannot**
  be applied to a compressed or encrypted script file.

* `scrimport.py` replace the edited script string into source script file
  (scr.bin) according to the prefix tag

  A text file with prefix tag can be splitted randomly and the importer will
  accept a splitted clip of files as parameter

Installation
------------

You will need Python 2.x to run scripts.

Extra dependency `bitarray` can be installed from python-pip

```
# python-pip install bitarray
```

Usage
-----

For usage detail, please run

```
$ <Command> --help
```

Extend work to these scripts is appreciative.

Reference
---------

The file description is based on utf_table code by
[Halley's Comet Software](http://hcs64.com/)

And a more systematic description from <http://wrttn.in/04fb3f>

License
-------

(The MIT License)

