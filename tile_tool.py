import argparse
import hashlib
import os
import struct
from PIL import Image

def next_tile(img, size):
    """Return the texture image data and the x/y coordinates of the top left."""
    w, h = img.width, img.height
    for j in range(0, h, size):
        for i in range(0, w, size):            
            yield img.crop((i, j, i + size, j + size)), i, j

def is_empty_tile(tile):
    """Return true for an empty tile. An empty tile is completely transparent."""
    alpha = sum([i for i in tile.tostring('raw', 'A')])
    if alpha == 0:
        return True
    return False

def tile_hash(tile):
    return hashlib.sha1(tile.tostring()).hexdigest()

def gen_tex_coords(path):
    """Generate a dictionary of texture coordinates.

    The dictionary key is a hash of the pixels.

    The dictionary values are a tuple of vertex order (monotonically increasing by 4),
    and a list of verticies.
    """
    img = Image.open(path)

    i = 1
    tiles = {}
    for t, x, y in next_tile(img, 16):
        if is_empty_tile(t):
            continue

        # scale x and y to between 0.0 and 1.0
        ox = x / img.width
        oy = 1.0 - (y / img.height)

        #  generate texture coordinates
        bl = (ox, oy - (16 / img.height))
        tl = (ox, oy)
        tr = (ox + (16 / img.width), oy)
        br = (ox + (16 / img.width), oy - (16 / img.height))
        
        tiles[tile_hash(t)] = (i, [bl, tl, tr, br])
        i += 4

    return tiles

def gen_mesh(path, tc):
    """Return a list for verticies and faces respectivley.

    Triangles use clockwise winding.
    """
    img = Image.open(path)

    cur_vert, verts = 0, []
    faces = []
    for t, x, y in next_tile(img, 16):
        if is_empty_tile(t):
            continue

        bl = (x - (img.width / 2.0), -(y + 16) + (img.height / 2.0), 0.0)
        tl = (x - (img.width / 2.0), -y + (img.height / 2.0), 0.0)
        tr = ((x + 16) - (img.width / 2.0), -y + (img.height / 2.0), 0.0)
        br = ((x + 16) - (img.width / 2.0), -(y + 16) + (img.height / 2.0), 0.0)

        cur_vert += 4
        verts.extend([bl, tl, tr, br])

        coords = tc[tile_hash(t)]

        tri_a = [(cur_vert - 3, coords[0]),
                 (cur_vert - 2, coords[0] + 1),
                 (cur_vert - 1, coords[0] + 2)]
        faces.append(tri_a)

        tri_b = [(cur_vert - 3, coords[0]),
                 (cur_vert - 1, coords[0] + 2),
                 (cur_vert,     coords[0] + 3)]
        faces.append(tri_b)

    return verts, faces

def main():
    parser = argparse.ArgumentParser(description='Generate an OBJ file for a given texture atlas and tile map image.')
    parser.add_argument('tile_map', help='The path of the tile map.')
    parser.add_argument('atlas', help='The path of the texture atlas.')
    parser.add_argument('out', help='The name of the output file.')
    args = parser.parse_args()
    
    tc = gen_tex_coords(args.atlas)
    verts, faces = gen_mesh(args.tile_map, tc)

    with open(args.out, 'w') as out:
        out.write('g {}\n'.format(os.path.splitext(os.path.basename(args.tile_map))[0]))

        for v in verts:
            out.write('v {} {} {}\n'.format(*v))

        
        for b in sorted(list(tc.values())):
            for c in b[1]:
                out.write('vt {} {}\n'.format(*c))

        for f in faces:
            out.write('f ')
            for p in f:
                out.write('{}/{}'.format(*p))
                out.write(' ')
            out.write('\n')


if __name__ == '__main__':
    main()
