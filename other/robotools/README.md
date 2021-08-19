# robotools

This tool converts character models used in AC and PS1 (maybe more?) DDR games.

This tool is provided AS-IS. This project was to satisfy my curiosity about the character model format. I don't play Stepmania so I have no interest in making release quality character conversions, but these tools should cover a lot of the work that is required to make the character conversions playable in Stepmania, with some additional tweaks required. Please do not ask me to fix bugs or add new features. If you find a bug and want to fix it, please submit a pull request via Github. Please do not message me telling me how to fix x problem, just submit a pull request.

This tool can output to `.glb`, `.obj`, and Stepmania character folder (`.txt` + template files) formats. The formats `.glb` and `.obj` can be opened with Blender. The Stepmania character folder can be opened with MilkShape 3D and obvious Stepmania.

## Setup

Tested with Python 3.8.10+.

Replace `python3` with `python` in the following commands based on your system configuration.

Install required libraries using the included requirements.txt.
```bash
python3 -m pip install -r requirements.txt
```

## Usage

```
usage: robotools.py [-h] --input-model INPUT_MODEL [--input-texture INPUT_TEXTURE] [--output OUTPUT] [--output-format {stepmania,obj,glb}] [--face-count FACE_COUNT] [--face-width FACE_WIDTH] [--face-height FACE_HEIGHT] [--disable-modify-face-texture] [--verbose]
                    [--input-bones INPUT_BONES]

optional arguments:
  -h, --help            show this help message and exit
  --input-model INPUT_MODEL
                        Input model filename
  --input-texture INPUT_TEXTURE
                        Input texture filename
  --output OUTPUT       Output folder
  --output-format {stepmania,obj,glb}
                        Output format
  --face-count FACE_COUNT
                        Number of faces in texture
  --face-width FACE_WIDTH
                        Width of face texture
  --face-height FACE_HEIGHT
                        Height of face texture
  --disable-modify-face-texture
                        Disables modifying face texture to include vertex colors
  --verbose             Verbose logging
  --input-bones INPUT_BONES
                        Input bones filename (only for stepmania output format). Do not use for Stepmania usage. Useful for testing animations in MilkShape 3D.
```

## Notes
- Some earlier games (DDR Karaoke Mix) use 3 face textures of 85x85 size, so you will need to set `--face-width 85 --face-height 85 --face-count 3` for those character models.
    - But not all characters from DDR Karaoke Mix use those parameters. The exceptions being the `anime` and `animb` characters which have 3 face textures of the size 64x64. The default face width and height are 64 already so you can just specify `--face-count 3` for these characters.
- A few characters use vertex coloring for hair. By default these will be written to the face textures when converting for Stepmania usage. If this causes problems, you can use `--disable-modify-face-texture` and it'll write the color to an unused part of the texture instead.
- The characters rendered for Stepmania use the bones as the old DDR PC rips (_DDRPC_common_Dance0001.bones.txt, etc).
- Some characters like `ringf` and `ringm` in DDR 3rd Mix require special modifications for the face textures. You will also likely need to modify `face.ini` for these characters.
- Textures for older games that use models with 20 meshes instead of 28 seem to be messed up.
