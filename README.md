tile_tool
=========
Generate an OBJ file for a provided texture atlas and tile map image. The tile map and the tile atlas must each be PNG files with alpha channels.

* The tool builds meshes to render 2D tile maps in Unity.
* It does not generate an optimal OBJ file as there are redundant verticies, faces, and texture coordinates. However, Unity can optimize the mesh when its imported.
