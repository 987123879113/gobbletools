# py573a

A Python recreation of 573a.jar with less Java, less GUI, less obfuscation, and less encryption.

py573a.py requires Cython. Build the required files using `python setup.py build_ext --inplace`.

py573a_native.py contains the decryption algorithm in native Python, in case you want to use the tool in an environment where Cython is inconvenient. Note: This version will be slower, but it should be easier to use without installing Cython and a C compiler, etc.

## Usage

```
usage: py573a.py [-h] [--input INPUT] [--output OUTPUT] [--sha1 SHA1]
                 [--key1 KEY1] [--key2 KEY2] [--key3 KEY3]

optional arguments:
  -h, --help       show this help message and exit
  --input INPUT    Input file
  --output OUTPUT  Output file
  --sha1 SHA1      Force usage of a specific SHA-1 for encryption keys
                   (optional)
  --key1 KEY1      Key 1 (optional)
  --key2 KEY2      Key 2 (optional)
  --key3 KEY3      Key 3 (optional)
```

Without `--output (filename.mp3)` being specified, it will automatically output a file in the same location as input.dat/.mp3 with a .mp3/.dat extension.

### Decryption
Decrypt a DAT file. The correct key is determined by the SHA-1 hash of the file. You can manually specify the SHA-1, or else the program will automatically calculate the SHA-1 hash of the input file. The SHA-1 hash must exist in the database for decryption to be possible.

```
python py573a.py --input input.dat
```

### Database
- Dance Dance Revolution Solo Bass Mix uses a different algorithm for which the key algorithm is not yet known, so the old method is still used for those games. Everything else should work.
- If a song is not in the db.json file, you must manually enter the key information yourself or use the `--key1`, `--key2`, and `--key3` parameters to decrypt the data.

