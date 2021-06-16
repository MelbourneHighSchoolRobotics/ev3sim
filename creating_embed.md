# Creating the python embed folder

First, Ensure you have the matching python installed locally, as you'll need to copy some files over.

1. Download get-pip.py and run `python get-pip.py`.
2. Change the contents of `python39._pth` to

```
python39.zip
.
.\Lib
.\Lib\site-packages

# Uncomment to run site.main() automatically
#import site
```

3. Copy `tcl` to `tcl` (Local install to embed)
4. Copy `Lib/tkinter` to `Lib/tkinter` (Local install to embed)
5. Copy `DLLs/_tkinter.pyd`, `DLLs/tcl86t.dll`, `DLLs/tk86t.dll` to `_tkinter.pyd`, ... (NOT in DLLs folder in embed)

After this, `python -m build_exe` should generate a good installer.
