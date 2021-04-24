# System 573 Multisession Unit Audio Decryption Tool

This tool works on all multisession unit discs.

This is a full recreation of the algorithm used to decrypt data on the real multisession unit device. It does not require access to hardware at all to decrypt anything, or generate any metadata.

## Usage

```
usage: msudecrypt.py [-h] --input INPUT [--output OUTPUT]

optional arguments:
  -h, --help       show this help message and exit
  --input INPUT    Input file
  --output OUTPUT  Output file
```

Without `--output (filename.mp3)` being specified, it will automatically output a file in the same location as input.dat/.mp3 with a .mp3/.dat extension.


