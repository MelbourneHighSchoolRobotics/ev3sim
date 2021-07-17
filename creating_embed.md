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

3. Copy `pythonw.exe` to `pythonww.exe` (Don't ask why)
4. Pip install `python-ev3dev2`.

After this, `python -m build_exe` should generate a good installer.
