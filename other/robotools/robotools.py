import argparse
import logging
import math
import os
import shutil
import time

import trimesh

import tim2png

from PIL import Image

display_material_warning = True

BLOCK_SIZE = 4 # This fixes a weird coloring issue causing nearby colors to bleed in

def parse_character_model(filename, texture_filename, output_folder=None, output_format="stepmania", face_count=4, face_width=64, face_height=64, disable_modify_face_texture=False, bones_filename=None):
    VERTEX_SCALE = 100

    MESH_NAMES = [
        "Pelvis",
        "R upper leg",
        "R leg",
        "R foot",
        "L upper leg",
        "L leg",
        "L foot",
        "Torso",
        "R upper arm",
        "R arm",
        "L upper arm",
        "L arm",
        "Neck",
        "R hand",
        "R hand 2",
        "R hand 3",
        "R hand 4",
        "R hand 5",
        "L hand",
        "L hand 2",
        "L hand 3",
        "L hand 4",
        "L hand 5",
        "Head",
        "Face",
        "Face 2",
        "Face 3",
        "Face 4",
    ]

    MESH_BONE_LOOKUP = {
        "Pelvis": 2,
        "R upper leg": 7,
        "R leg": 6,
        "R foot": 4,
        "L upper leg": 14,
        "L leg": 13,
        "L foot": 11,
        "Torso": 0,
        "R upper arm": 8,
        "R arm": 3,
        "L upper arm": 15,
        "L arm": 10,
        "Neck": 9,
        "R hand": 5,
        # "R hand 2": 5,
        # "R hand 3": 5,
        # "R hand 4": 5,
        # "R hand 5": 5,
        "L hand": 12,
        # "L hand 2": 12,
        # "L hand 3": 12,
        # "L hand 4": 12,
        # "L hand 5": 12,
        "Head": 1,
        "Face": 1,
        # "Face 2": 1,
        # "Face 3": 1,
        # "Face 4": 1,
    }

    # bones = parse_bones(os.path.join("ddr5th_chara", "chara.pos"))
    all_vertices = []

    vertex_colors = {}

    if texture_filename is None:
        for ext in [".ctx", ".cmt"]:
            texture_filename = os.path.splitext(filename)[0] + ext
            if os.path.exists(texture_filename):
                break

    # Convert texture image
    tex_file = open(texture_filename, "rb")
    tex_file.seek(0, 2)
    tex_file_end = tex_file.tell()
    tex_file.seek(0)

    textures = []
    while tex_file.tell() < tex_file_end:
        texture_image = tim2png.readTimImage(tex_file, disable_transparency=True)[0]
        textures.append(texture_image)

    if len(textures) == 1:
        # DDR 5th, Karaoke Mix
        texture_image = textures[0]

    else:
        # DDR 3rd, 4th
        ycnt = 4
        xcnt = math.ceil(len(textures) / ycnt)
        texture_image = Image.new("RGB", (xcnt * 64, ycnt * 64), (0, 0, 0, 0))

        idx = 0
        for j in range(ycnt):
            for i in range(xcnt):
                if idx < len(textures):
                    texture_image.paste(textures[idx], (j * 64, i * 64))

                idx += 1

    vertex_color_x = texture_image.width
    vertex_color_y = 0

    vertex_color_x_face = face_width - BLOCK_SIZE
    vertex_color_y_face = 0

    img = Image.new("RGB", (texture_image.width + 128, texture_image.height), (0, 0, 0, 0))
    img.paste(texture_image, (0, 0))
    texture_image = img

    def parse_chunk(data, offset, chunk_cnt, mesh_name, cur_mesh_idx):
        global display_material_warning
        nonlocal vertex_color_x, vertex_color_y
        nonlocal vertex_color_x_face, vertex_color_y_face
        nonlocal all_vertices

        local_faces = []
        local_texcoords = []

        def parse_chunk_verts(data, offset, cnt, unique_cnt):
            verts = []
            bones = []

            for i in range(0, cnt * 8, 8):
                vxy = int.from_bytes(data[offset+i:offset+i+4], 'little')
                vz = int.from_bytes(data[offset+i+4:offset+i+6], 'little')
                linked = int.from_bytes(data[offset+i+6:offset+i+8], 'little')

                x = int.from_bytes(data[offset+i:offset+i+2], 'little', signed=True)
                y = int.from_bytes(data[offset+i+2:offset+i+4], 'little', signed=True)
                z = int.from_bytes(data[offset+i+4:offset+i+6], 'little', signed=True)

                x = x / VERTEX_SCALE
                y = (y * -1) / VERTEX_SCALE

                if output_format != "stepmania":
                    z = (z + (cur_mesh_idx * 750)) / VERTEX_SCALE

                else:
                    z = (z * -1) / VERTEX_SCALE

                logging.info("\t\t%d vxy[%08x] vz[%04x] x[%f] y[%f] z[%f] linked[%d]" % (i // 8, vxy, vz, x, y, z, linked))

                bone_name = mesh_name
                if i // 8 >= unique_cnt and output_format == "stepmania":
                    logging.info("\t\t\t%d x[%f] y[%f] z[%f] %s" % (linked, *(all_vertices[linked][0]), all_vertices[linked][1]))
                    x, y, z = all_vertices[linked][0]
                    bone_name = all_vertices[linked][1]

                verts.append((x, y, z))
                bones.append(MESH_BONE_LOOKUP.get(bone_name, -1 if output_format == "stepmania" else 0))

            return verts, bones


        def parse_chunk_faces(data, offset, cnt):
            nonlocal local_faces

            faces = []

            for i in range(0, cnt * 12, 12):
                c1 = int.from_bytes(data[offset+i:offset+i+2], 'little')
                c2 = int.from_bytes(data[offset+i+2:offset+i+4], 'little')
                b1 = int.from_bytes(data[offset+i+4:offset+i+6], 'little')
                b2 = int.from_bytes(data[offset+i+6:offset+i+8], 'little')
                a1 = int.from_bytes(data[offset+i+8:offset+i+10], 'little')
                a2 = int.from_bytes(data[offset+i+10:offset+i+12], 'little')

                logging.info("\t\t%d | %04x %04x %04x %04x %04x %04x" % (i // 12, a1, a2, b1, b2, c1, c2))

                assert(a1 == a2)
                assert(b1 == b2)
                assert(c1 == c2)

                faces.append((
                    (a1, a2),
                    (b1, b2),
                    (c1, c2),
                ))

            return faces


        def parse_chunk_texcoords(data, offset, cnt, material=0):
            nonlocal local_texcoords

            texcoords = []

            for i in range(0, cnt * 12, 12):
                t1 = int.from_bytes(data[offset+i+0:offset+i+4], 'little')
                t2 = int.from_bytes(data[offset+i+4:offset+i+8], 'little')
                t3 = int.from_bytes(data[offset+i+8:offset+i+12], 'little')

                t3x = data[offset+i]
                t3y = data[offset+i+1]
                t3u = int.from_bytes(data[offset+i+2:offset+i+4], 'little')

                t2x = data[offset+i+4]
                t2y = data[offset+i+5]
                t2u = int.from_bytes(data[offset+i+6:offset+i+8], 'little')

                t1x = data[offset+i+8]
                t1y = data[offset+i+9]
                t1u = int.from_bytes(data[offset+i+10:offset+i+12], 'little')

                if output_format != "stepmania":
                    t1y = 255 - t1y
                    t2y = 255 - t2y
                    t3y = 255 - t3y

                t1x += 0.5
                t1y += 0.5

                t2x += 0.5
                t2y += 0.5

                t3x += 0.5
                t3y += 0.5

                texture_width = face_width if material == 1 else texture_image.width
                texture_height = face_height if material == 1 else texture_image.height

                t1x /= texture_width
                t1y /= texture_height

                t2x /= texture_width
                t2y /= texture_height

                t3x /= texture_width
                t3y /= texture_height

                logging.info("\t\t%d | %08x %08x %08x | t1[(%f, %f) %04x] t2[(%f, %f) %04x] t3[(%f, %f) %04x]" % (i // 12, t1, t2, t3, t1x, t1y, t1u, t2x, t2y, t2u, t3x, t3y, t3u))

                for x in [(t1x, t1y), (t2x, t2y), (t3x, t3y)]:
                    if x not in local_texcoords:
                        local_texcoords.append(x)

                    texcoords.append(x)

            return texcoords

        output = {
            'name': mesh_name,
            'material': 1 if output_format == "stepmania" and mesh_name == "Face" else 0
        }

        verts_np = []
        faces_np = []
        uv_np = []
        bones_np = []
        vert_groups = []

        texcoords_total = []

        for i in range(chunk_cnt):
            chunk_type = int.from_bytes(data[offset+(i*0x30):offset+(i*0x30)+4], 'little')

            logging.info("")
            logging.info(mesh_name)
            logging.info("chunk type %04x, %d" % (chunk_type, i))
            assert((chunk_type & 0x30) == 0x30)

            a_offset = int.from_bytes(data[offset+(i*0x30)+4:offset+(i*0x30)+8], 'little') + offset
            a_cnt = int.from_bytes(data[offset+(i*0x30)+8:offset+(i*0x30)+12], 'little')
            a_unique_cnt = int.from_bytes(data[offset+(i*0x30)+12:offset+(i*0x30)+16], 'little')
            a_store_cnt = int.from_bytes(data[offset+(i*0x30)+16:offset+(i*0x30)+20], 'little')

            b_offset = int.from_bytes(data[offset+(i*0x30)+20:offset+(i*0x30)+24], 'little') + offset
            b_cnt = int.from_bytes(data[offset+(i*0x30)+24:offset+(i*0x30)+28], 'little')
            b_unique_cnt = int.from_bytes(data[offset+(i*0x30)+28:offset+(i*0x30)+32], 'little')
            b_store_cnt = int.from_bytes(data[offset+(i*0x30)+32:offset+(i*0x30)+36], 'little')

            c_offset1 = int.from_bytes(data[offset+(i*0x30)+36:offset+(i*0x30)+40], 'little') + offset
            c_offset2 = int.from_bytes(data[offset+(i*0x30)+40:offset+(i*0x30)+44], 'little') + offset
            c_cnt = int.from_bytes(data[offset+(i*0x30)+44:offset+(i*0x30)+48], 'little')

            logging.info("\tverts %08x %08x %08x %08x" % (a_offset, a_cnt, a_unique_cnt, a_store_cnt))
            verts, bones = parse_chunk_verts(data, a_offset, a_cnt, a_unique_cnt)
            all_vertices += [(x, mesh_name) for x in verts[:a_store_cnt]]

            logging.info("\tunk %08x %08x %08x %08x" % (b_offset, b_cnt, b_unique_cnt, b_store_cnt)) # Related to vertices?

            logging.info("\tfaces %08x %08x" % (c_offset2, c_cnt))
            faces = parse_chunk_faces(data, c_offset1, c_cnt)
            local_faces += faces

            if chunk_type & 0x04:
                logging.info("\ttexcoords %08x %08x" % (c_offset2, c_cnt))
                texcoords = parse_chunk_texcoords(data, c_offset2, c_cnt, output['material'])

            elif chunk_type & 0x400:
                if output['material'] == 1 and display_material_warning and disable_modify_face_texture:
                    logging.warning("This character uses vertex coloring on the character's face and may not render properly with modified face textures disabled.")
                    display_material_warning = False

                # Solid color??
                color = int.from_bytes(data[c_offset2:c_offset2+4], 'little')
                rgb_color = ((color & 0xff), (color >> 8) & 0xff, (color >> 16) & 0xff, 255)

                assert((color & 0xf0000000) == 0x30000000)

                if rgb_color not in vertex_colors:
                    texture_width = face_width if output['material'] == 1 and not disable_modify_face_texture else texture_image.width
                    texture_height = face_height if output['material'] == 1 and not disable_modify_face_texture else texture_image.height

                    x = vertex_color_x_face if output['material'] == 1 and not disable_modify_face_texture else vertex_color_x
                    y = vertex_color_y_face if output['material'] == 1 and not disable_modify_face_texture else vertex_color_y

                    for ix in range(BLOCK_SIZE):
                        for iy in range(BLOCK_SIZE):
                            if output['material'] == 1 and not disable_modify_face_texture:
                                # Write the color for every face texture
                                for ic in range(face_count):
                                    texture_image.putpixel((x + ix, y + iy + (face_height * ic)), rgb_color)

                            else:
                                texture_image.putpixel((x + ix, y + iy), rgb_color)

                    ny = y + BLOCK_SIZE
                    nx = x

                    if ny > texture_height:
                        ny = 0
                        nx = x + BLOCK_SIZE

                    if output['material'] == 1 and not disable_modify_face_texture:
                        vertex_color_x_face = nx
                        vertex_color_y_face = ny

                    else:
                        vertex_color_x = nx
                        vertex_color_y = ny

                    # Get next position
                    if nx > texture_width:
                        logging.error("Ran out of space for additional colors!")
                        # exit(1)

                    x += BLOCK_SIZE // 2
                    y += BLOCK_SIZE // 2

                    # print(texture_image.getpixel((x, y)), rgb_color, x, y)

                    if output_format != "stepmania":
                        y = texture_height - y

                    vertex_colors[rgb_color] = [(x / texture_width, y / texture_height), ((x + 0.5) / texture_width, y / texture_height), ((x + 0.5) / texture_width, (y - 0.5) / texture_height)]

                    # print("Found %08x at %d,%d" % (color, x, y), vertex_colors[rgb_color])

                texcoords = [*vertex_colors[rgb_color]] * (len(faces) * 3)

            else:
                logging.error("Unknown chunk type %04x" % chunk_type)
                exit(1)

            texcoords_total += texcoords

            if MESH_BONE_LOOKUP.get(mesh_name, -1 if output_format == "stepmania" else 0) == -1:
                return None

            for j, x in enumerate(faces):
                vert_indexes_np = []

                for k2, x2 in enumerate(x):
                    k = (verts[x2[0]], texcoords[j * len(x) + k2], bones[x2[0]])

                    if k not in vert_groups:
                        vert_groups.append(k)
                        verts_np.append(verts[x2[0]])
                        bones_np.append(bones[x2[0]])
                        uv_np.append(texcoords[j * len(x) + k2])

                    vert_indexes_np.append(vert_groups.index(k))

                faces_np.append(vert_indexes_np)

        mesh = trimesh.Trimesh(
            vertices=verts_np,
            faces=faces_np,
            visual=trimesh.visual.TextureVisuals(
                uv_np,
                trimesh.visual.material.PBRMaterial(
                    baseColorTexture=texture_image,
                    metallicFactor=0,
                    doubleSided=True,
                ),
            ),
            process=False, # Don't process the model because we want better control over bones
        )

        output['mesh'] = mesh
        output['bones'] = bones_np

        return output


    data = bytearray(open(filename, "rb").read())
    mesh_cnt = int.from_bytes(data[8:12], 'little')

    assert(mesh_cnt == 0x1c) # Probably will trigger for any non-character models

    meshes = []
    for i in range(mesh_cnt):
        if output_format == "stepmania" and MESH_NAMES[i] not in MESH_BONE_LOOKUP:
            continue

        offset = int.from_bytes(data[0x20+(0x0c*i):0x20+(0x0c*i)+4], 'little') + 0x20
        chunk_cnt = int.from_bytes(data[0x20+(0x0c*i)+4:0x20+(0x0c*i)+8], 'little')

        mesh = parse_chunk(data, offset, chunk_cnt, MESH_NAMES[i], i)

        if mesh:
            mesh['mesh'].metadata['name'] = MESH_NAMES[i]
            meshes.append(mesh)


    # Save data
    if output_folder is None:
        basename = os.path.splitext(os.path.basename(filename))[0]
        output_folder = "output_" + basename

    if output_format in ["glb" , "obj"]:
        os.makedirs(output_folder, exist_ok=True)

        scene = trimesh.Scene()

        for mesh in meshes:
            scene.add_geometry(mesh['mesh'])

        if output_format == "glb":
            data = scene.export(file_type="glb")
            open(os.path.join(output_folder, "output.glb"), "wb").write(data)

        elif output_format == "obj":
            data = scene.export(file_type="obj", return_texture=True)
            open(os.path.join(output_folder, "output.obj"), "w").write(data)

            _, texture = trimesh.exchange.obj.export_obj(scene, return_texture=True)
            for k in texture:
                open(os.path.join(output_folder, k), "wb").write(texture[k])

    elif output_format == "stepmania":
        # MilkShape 3D ASCII with specific file setup for Stepmania
        # Copy template files
        if os.path.exists("template"):
            # Copy
            shutil.copytree("template", output_folder, dirs_exist_ok=True)

        else:
            logging.error("Couldn't find template folder!")
            os.makedirs(output_folder, exist_ok=True)

        # Save texture
        texture_image.save(os.path.join(output_folder, "texture.png"), "PNG")

        # Save individual faces from texture file
        for i in range(face_count):
            clip = texture_image.crop((0, face_height * i, face_width, face_height * (i + 1)))

            if face_height != 64 or face_width != 64:
                clip = clip.resize((64, 64), Image.LANCZOS)

            clip.save(os.path.join(output_folder, "face%d.bmp" % (i+1)), "BMP")

        # Write out MilkShape 3D ASCII file
        with open(os.path.join(output_folder, "model.txt"), "w") as outfile:
            outfile.write("// Converted using robotools %s\n" % (time.ctime()))

            outfile.write("Frames: 1\n")
            outfile.write("Frame: 1\n")
            outfile.write("Meshes: %d\n" % len(meshes))

            for mesh in meshes:
                outfile.write("\"%s\" %d %d\n" % (mesh['name'], mesh.get('flags', 0), mesh.get('material', 0)))

                # Vertices
                v = mesh['mesh'].vertices
                uvs = mesh['mesh'].visual.uv
                bones = mesh['bones']

                outfile.write("%d\n" % len(v))
                for i, c in enumerate(v):
                    outfile.write("0 %s %s %s %s %s %d\n" % (*[str(x) for x in c], *[str(x) for x in uvs[i]], bones[i]))

                # Normals
                normals = [tuple(x2 for x2 in x) for x in mesh['mesh'].vertex_normals]
                normals_written = []

                for c in normals:
                    if c not in normals_written:
                        normals_written.append(c)

                outfile.write("%d\n" % len(normals_written))
                for c in normals_written:
                    c = [str(x) for x in c]
                    outfile.write("%s %s %s\n" % (c[0], c[1], c[2]))

                # Triangles
                v = mesh['mesh'].faces
                outfile.write("%d\n" % len(v))
                for c in v:
                    outfile.write("0 %d %d %d %d %d %d 1\n" % (*c, normals_written.index(normals[c[0]]), normals_written.index(normals[c[1]]), normals_written.index(normals[c[2]])))


            outfile.write("""\n\nMaterials: 2
"Texture"
0.200000 0.200000 0.200000 1.000000
0.800000 0.800000 0.800000 1.000000
0.000000 0.000000 0.000000 1.000000
1.000000 1.000000 1.000000 1.000000
0.000000
1.000000
"texture.png"
""
"Face"
0.200000 0.200000 0.200000 1.000000
0.800000 0.800000 0.800000 1.000000
0.000000 0.000000 0.000000 1.000000
1.000000 1.000000 1.000000 1.000000
0.000000
1.000000
"face.ini"
""\n\n
""")

            if bones_filename is not None:
                outfile.write(open(bones_filename, "r").read())

            else:
                bone_names = ["torso", "head", "pelvis", "r lower arm", "r foot", "r hand", "r leg", "r thigh", "r upper arm", "neck", "l lower arm", "l foot", "l hand", "l leg", "l thigh", "l upper arm"]
                outfile.write("Bones: %d\n" % len(bone_names))
                for k in bone_names:
                    outfile.write("\"%s\"\n" % k)
                    outfile.write("\"\"\n")
                    outfile.write("8 0.000000 0.000000 0.000000 0.000000 0.000000 0.000000\n")
                    outfile.write("0\n")
                    outfile.write("0\n")



def parse_bones(filename):
    # Expects chara.pos.
    # Bones? The values change how the body parts are place relative to the torso in-game but not quite bones maybe.
    BONE_NAMES = [
        "Unknown", # Has no effect in-game when changed?
        "L upper leg",
        "L leg",
        "L foot",
        "R upper leg",
        "R leg",
        "R foot",
        "Torso",
        "L upper arm",
        "L arm",
        "R upper arm",
        "R arm",
        "Neck",
        "L hand",
        "R hand",
        "Head",
    ]

    data = bytearray(open(filename, "rb").read())

    # First 6 bytes are not read by the game for some reason
    data = data[6:]

    bones = {}

    i = 0
    while data:
        import hexdump
        hexdump.hexdump(data[:6])

        x = int.from_bytes(data[0:2], 'little', signed=True)
        y = int.from_bytes(data[2:4], 'little', signed=True)
        z = int.from_bytes(data[4:6], 'little', signed=True)
        data = data[6:]

        logging.info("%02x" % i, BONE_NAMES[i], x, y, z)

        bones[BONE_NAMES[i]] = (x, y, z)

        i += 1

    return bones

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--input-model', help='Input model filename', default=None, required=True)
    parser.add_argument('--input-texture', help='Input texture filename', default=None)
    parser.add_argument('--output', help='Output folder', default=None)
    parser.add_argument('--output-format', help='Output format', default="stepmania", choices=["stepmania", "obj", "glb"])
    parser.add_argument('--face-count', help='Number of faces in texture', default=4, type=int)
    parser.add_argument('--face-width', help='Width of face texture', default=64, type=int)
    parser.add_argument('--face-height', help='Height of face texture', default=64, type=int)
    parser.add_argument('--disable-modify-face-texture', help='Disables modifying face texture to include vertex colors', default=False, action='store_true')
    parser.add_argument('--verbose', help='Verbose logging', default=False, action='store_true')
    parser.add_argument('--input-bones', help='Input bones filename (only for stepmania output format). Do not use for Stepmania usage. Useful for testing animations in MilkShape 3D.', default=None)

    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(format='%(message)s', level=logging.DEBUG)
        trimesh.util.attach_to_log()

    else:
        logging.basicConfig(format='%(message)s', level=logging.WARNING)

    parse_character_model(args.input_model, args.input_texture, args.output, args.output_format, args.face_count, args.face_width, args.face_height, args.disable_modify_face_texture, args.input_bones)
