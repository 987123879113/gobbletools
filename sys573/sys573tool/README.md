# sys573tool

This is a combination of `dump_sys573_gamefs.py`, `build_sys573_gamefs.py`, and `calc_checksum.py`.

sys573tool requires Cython. Build the required files using `python setup.py build_ext --inplace`.

### Usage

```
usage: sys573tool.py [-h] --mode {dump,build,checksum}

optional arguments:
  -h, --help            show this help message and exit
  --mode {dump,build,checksum}
                        Operation mode
```

Used to dump a game's data from .DATs:
```
usage: dump_sys573_gamefs.py [-h] --input INPUT [--output OUTPUT]

optional arguments:
  -h, --help       show this help message and exit
  --input INPUT    Input folder
  --output OUTPUT  Output folder
```

Used to rebuild a game's .DAT files (experimental, most likely won't work for you without modification for your use case):
```
usage: build_sys573_gamefs.py [-h] --input INPUT [--input-modified-list INPUT_MODIFIED_LIST] --base BASE
                              [--output OUTPUT] --key {EXTREME,EURO2,MAX2,DDR5,MAMBO} [--override-edit-section]
                              [--patch-dir PATCH_DIR]

optional arguments:
  -h, --help            show this help message and exit
  --input INPUT         Input folder
  --input-modified-list INPUT_MODIFIED_LIST
                        Input modified list
  --base BASE           Base file folder
  --output OUTPUT       Output file
  --key {EXTREME,EURO2,MAX2,DDR5,MAMBO}
                        Encryption key
  --override-edit-section
                        Allows use of end of CARD 2 which would otherwise be used for edit data saved to flash card.
                        REQUIRED ENABLE_EDIT_SECTOR_OVERRIDE ENABLED IN ASM PATCHES!
  --patch-dir PATCH_DIR
                        Path to use for patch files
```

Used to fix the checksums in the .DAT file after editing data:
```
usage: calc_checksum.py [-h] --input INPUT [INPUT ...] [--output OUTPUT]

optional arguments:
  -h, --help            show this help message and exit
  --input INPUT [INPUT ...]
                        Input DAT file (list all in order)
  --output OUTPUT       Output folder
```

For a better example of how to use these tools, check out https://github.com/987123879113/ddr5thmix-solo.
