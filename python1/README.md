# Python1 Tools

### python1_dumper.py

This tool lets you dump data from pop'n music Python 1 HDDs. It can be modified to work on other Python 1 games but the filename pattern matching is for pop'n music. It will not find all filenames, and if used on other games, it will just output filenames based on the filename hash.

```
usage: python1_dumper.py [-h] -i INPUT [-o OUTPUT] [-d]

optional arguments:
  -h, --help            show this help message and exit
  -i INPUT, --input INPUT
                        Input folder
  -o OUTPUT, --output OUTPUT
                        Output folder
  -d, --decrypt         Decryption for pop'n 13 and 14
```
