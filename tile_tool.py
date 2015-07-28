import argparse
import hashlib
import logging
import os
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

def gen_tex_coords(img, tile_size):
    """Generate a dictionary of texture coordinates.

    The dictionary key is a hash of the pixels.

    The dictionary values are a tuple of vertex order (monotonically increasing by 4),
    and a list of verticies.
    """
    i = 1
    tiles = {}
    for t, x, y in next_tile(img, tile_size):
        if is_empty_tile(t):
            continue

        # scale x and y to between 0.0 and 1.0
        ox = x / img.width
        oy = 1.0 - (y / img.height)

        #  generate texture coordinates
        bl = (ox, oy - (tile_size / img.height))
        tl = (ox, oy)
        tr = (ox + (tile_size / img.width), oy)
        br = (ox + (tile_size / img.width), oy - (tile_size / img.height))

        tiles[tile_hash(t)] = (i, [bl, tl, tr, br])
        i += 4

    return tiles

def gen_mesh(img, tc, tile_size):
    """Return a list for verticies and faces respectivley.

    Triangles use clockwise winding.
    """
    cur_vert, verts = 0, []
    faces = []
    for t, x, y in next_tile(img, tile_size):
        if is_empty_tile(t):
            continue

        # generate verticies
        bl = (-(x - (img.width / 2.0)), -(y + tile_size) + (img.height / 2.0), 0.0)
        tl = (-(x - (img.width / 2.0)), -y + (img.height / 2.0), 0.0)
        tr = (-((x + tile_size) - (img.width / 2.0)), -y + (img.height / 2.0), 0.0)
        br = (-((x + tile_size) - (img.width / 2.0)), -(y + tile_size) + (img.height / 2.0), 0.0)
        verts.extend([bl, tl, tr, br])
        cur_vert += 4

        try:
            coords = tc[tile_hash(t)]
        except KeyError as e:
            logging.warning('Unable to find tile in atlas ({}, {})'.format(int(y / tile_size), int(x / tile_size)))
            continue

        # generate faces using vertex and texture indicies
        tri_a = [(cur_vert - 3, coords[0]),
                 (cur_vert - 2, coords[0] + 1),
                 (cur_vert - 1, coords[0] + 2)]
        faces.append(tri_a)

        tri_b = [(cur_vert - 3, coords[0]),
                 (cur_vert - 1, coords[0] + 2),
                 (cur_vert,     coords[0] + 3)]
        faces.append(tri_b)

    return verts, faces

def break_tile_map(img, tile_size):
    """Break a tile map into rectangular portions/images and return a list of each portion/image.

    This function attempts to break a tile map into the fewest rectangular portions of contiguous tiles.
    This is useful for creating the least amount of geometry for 2D physics calculations.
    The function operates using a greedy method and is not intended to produce optimal geometry.
    """

    # create a 2D array for each tile in the image
    w = int(img.width / tile_size)
    h = int(img.height / tile_size)
    arr = [[0 for i in range(w)] for i in range(h)]

    # set non empty tiles to 1
    for t, x, y in next_tile(img, tile_size):
        if not is_empty_tile(t):
            r = int(y / tile_size)
            c = int(x / tile_size)
            arr[r][c] = 1

    # a list of rect partitions
    broken = []

    # find the minimal rect partitioning for this image
    for r in range(len(arr)):
        for c, tile in enumerate(arr[r]):
            if tile == 1:
                box = _find_max_rect(arr, r, c, tile_size)
                broken.append(img.crop(box))

                # clear this rect from the array
                for i in range(int(box[1] / tile_size), int(box[3] / tile_size)):
                    for j in range(int(box[0] / tile_size), int(box[2] / tile_size)):
                        arr[i][j] = 0

    return broken

def _find_max_rect(arr, r, c, tile_size):
    """Return the box coordinates of the largest contiguous rectangle of tiles in the given array.
    """
    max_so_far = (-1, None)

    for i in range(len(arr)):
        for j, t in enumerate(arr[i]):

            if arr[i][j] == 0:
                continue

            elif _is_rect_full(arr, (r, c), (i, j)):

                tot = (abs(r - i) + 1) * (abs(c - j) + 1)

                if tot > max_so_far[0]:

                    left = min(c, j) * tile_size
                    top = min(r, i) * tile_size
                    right = (max(c, j) + 1) * tile_size
                    bot = (max(r, i) + 1) * tile_size

                    max_so_far = (tot, (left, top, right, bot))

    return max_so_far[1]

def _is_rect_full(arr, a, b):
    """Return true if the given rectangular portion is contiguous.
    Contiguous in this instance means that there are no empty tiles in the portion.
    """
    if a[0] == b[0] and a[1] == b[1]:
        return True

    start_r, end_r = min(a[0], b[0]), max(a[0], b[0])
    start_c, end_c = min(a[1], b[1]), max(a[1], b[1])

    for r in range(start_r, end_r + 1):
        for c in range(start_c, end_c + 1):
            if arr[r][c] == 0:
                return False

    return True

def write_obj_file(name, verts, tc, faces):
    """Write an object file.
    """
    with open(name + '.obj', 'w') as out:
        out.write('g {}\n'.format(name))

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

def main():
    parser = argparse.ArgumentParser(description='Generate OBJ files for a given texture atlas and tile map image.')
    parser.add_argument('tile_map', help='The path of the tile map.')
    parser.add_argument('atlas', help='The path of the texture atlas.')
    parser.add_argument('-s', type=int, default=16, help='The tile size in pixels.')
    parser.add_argument('-b', action='store_true', default=False,
        help='Break the tile map into individual meshes and output a file for each.')
    parser.add_argument('-o', type=str, help='Output directory.')
    args = parser.parse_args()

    if args.s <= 0:
        raise argparse.ArgumentTypeError('invalid tile size {}'.format(args.s))

    name = os.path.splitext(os.path.basename(args.tile_map))[0]
    if args.o:
        name = os.path.join(args.o, name)
    
    map_img = Image.open(args.tile_map)
    atlas_img = Image.open(args.atlas)

    # generate texture coordinates
    tc = gen_tex_coords(atlas_img, args.s)

    # write obj file(s)
    if args.b:
        for i, m in enumerate(break_tile_map(map_img, args.s)):
            verts, faces = gen_mesh(m, tc, args.s)
            write_obj_file('{}_{}'.format(name, i), verts, tc, faces)
    else:
        verts, faces = gen_mesh(map_img, tc, args.s)
        write_obj_file(name, verts, tc, faces)

if __name__ == '__main__':
    main()
