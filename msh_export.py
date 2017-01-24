#!BPY

"""
Name: 'The Movies (.msh)...'
Blender: 242
Group: 'Export'
Tooltip: 'Export to Lionhead Studios The Movies file format. (.msh)'
"""

__author__ = ["Mark S Andrews"]
__url__ = ("http://themovieseditor.com","http://tmws.themoviesplanet.com")
__version__ = "0.02"
__bpydoc__ = """\

Msh Exporter

This script exports a msh file for use with Lionhead Studio Limited's
The Movies. It is not supported by either Lionhead or Activision.

It does not currently support all features of the msh files or even
all features currently imported. It is suitable for static props only.

Changes:

0.02 Mark S Andrews 2006-01-29<br>
- First working version, various fixes
0.01 Mark S Andrews 2006-01-13<br>
- Initial version
"""

# ***** BEGIN GPL LICENSE BLOCK *****
#
# Script copyright (C) Mark S Andrews
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
# ***** END GPL LICENCE BLOCK *****
# --------------------------------------------------------------------------


# Import modules

import Blender
from Blender import Image, Material, Texture, NMesh, Window, Armature
from Blender.Mathutils import Matrix, Vector
from random import getrandbits
import struct, os, re

#***********************************************
# globals
#***********************************************

material_list = []
material_keys = []

#***********************************************
# helper classes & functions for msh file
#***********************************************

grouped_mesh = re.compile(r'(.+)\.(\d\d)\..+')
numbered_mesh = re.compile(r'(.+)\.\d+')
room_mesh = re.compile(r'(.+)\.room\_')

def write_nts(item, stream, length=32):
    if len(item) > length:
        raise ValueError("%s is longer than %d"%(item, length))
    while len(item) < length:
        item += "\x00"
    stream.write(item)

def write_null(struct_type, stream):
    data = ""
    for b in range(struct.calcsize(struct_type)):
        data += "\x00"
    stream.write(data)

class range_adjust(object):
    def __init__(self, min, max):
        self.min = min
        self.max = max
        self.step = (max - min) / 65535
    def adjust(self, value):
        if self.step == 0:
            return 0
        return int((value - self.min) / self.step)

#***********************************************
# writer functions for msh file
#***********************************************

def write_material(mat, stream):
    image_list = Image.Get()
    texture_list = mat.getTextures()
    i = [-1,-1,-1,-1]
    use_alpha = False
    if texture_list[0]:
        im = texture_list[0].tex.getImage()
        if im:
            i[0] = image_list.index(im)
            use_alpha = texture_list[0].mtAlpha
    if texture_list[1]:
        im = texture_list[1].tex.getImage()
        if im:
            i[1] = image_list.index(im)
    if texture_list[2]:
        im = texture_list[2].tex.getImage()
        if im:
            i[3] = image_list.index(im)
    
    # *********** write image refs *************
    stream.write(struct.pack("bbbb", i[0], i[1], i[2], i[3]))
    # *********** too many unknowns!! **********
    stream.write("\x00\x01\x01")
    if use_alpha:
        stream.write("\x01")
    else:
        stream.write("\x00")
    write_null("BBBBBB", stream)
    stream.write("\x04\x00\xee\xa2\x00\xff")
    write_null("BBBB", stream)

def write_control_meshes(stream):

    if binding is not None:
        write_basic_mesh(binding, stream)

    if floor is not None:
        write_basic_mesh(floor, stream)

    if wall is not None:
        write_basic_mesh(wall, stream)

    if land is not None:
        write_basic_mesh(land, stream)

    if mesh1 is not None:
        write_basic_mesh(mesh1, stream)

    if foundation is not None:
        write_basic_mesh(foundation, stream)

    if mesh2 is not None:
        write_basic_mesh(mesh2, stream)



def write_basic_mesh(mesh, stream):
    meshdata = mesh.getData()
    meshlog.write('\n> write_basic_mesh: "%s"' % meshdata.name)
    
    # ********** write vertex count ************
    stream.write(struct.pack("L",len(meshdata.verts)))
    # stream.write(len(mesh.verts))
    # ********** write face count **************
    stream.write(struct.pack("L",len(meshdata.faces)))
    #stream.write(len(mesh.faces))
    for v in meshdata.verts:
        # ******* write vertex position ********
        stream.write(struct.pack("fff", v.co[0], v.co[1], v.co[2]))
    for f in meshdata.faces:
        v0 = meshdata.verts.index(f.v[0])
        v1 = meshdata.verts.index(f.v[1])
        v2 = meshdata.verts.index(f.v[2])
        # ******** write face vertices *********
        stream.write(struct.pack("HHH", v0, v1, v2))
    if len(meshdata.faces) & 1:
        # ********** write pad bytes ***********
        stream.write("\x00\x00")

def write_group(meshes, stream):
    # A thread on TMWS suggests that it may not be a matrix. So... 
    # this might need to be changed.

    matrix = meshes[0].matrix
    #matrix = [[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]]
    flags = 16
    # *********** write group header ***********
    stream.write(struct.pack("BBBB", len(meshes), 0, 0, flags))
    # ************** write matrix **************
    for p in range(4):
        stream.write(struct.pack("fff", matrix[0][p], \
            matrix[1][p], matrix[2][p]))
    
    if flags & 16:
        write_null("L", stream)
        
    for m in meshes:
        write_mesh(m, stream)

def write_mesh(ob, stream):
    # this is the main function for writing a mesh to file. This is for
    # normal meshes only, and should not be used for control meshes 
    # (which don't have textures anyway

    global material_keys
    mesh = ob.getData()
    meshlog.write('\n> write_mesh: "%s"' % mesh.name)
    mat = mesh.getMaterials()
    # ********** write material index **********
    if mat:
        stream.write(struct.pack("L",material_keys.index(mat[0].name)))
    else:
        write_null("L", stream)
    # ********** write face count **************
    stream.write(struct.pack("L",len(mesh.faces)))
    # ********** write vertex count ************
    vcpos = stream.tell()
    stream.write(struct.pack("L",len(mesh.verts)))
    mf = [0x70,0,0,0]
    if mesh.getVertGroupNames() != []:
        mf[0] |= 1
    # ************ write mesh flags ************
    stream.write(struct.pack("BBBB", mf[0], mf[1], mf[2], mf[3]))
    stream.write(struct.pack("L", getrandbits(32)))
    stream.write("\xff\xff\xff\xff")
    write_null("L", stream)
    xs = []
    ys =[]
    zs = []
    txs = []
    tys = []
    for v in mesh.verts:
        xs.append(v.co[0])
        ys.append(v.co[1])
        zs.append(v.co[2])
    for f in mesh.faces:
        for vertexid in range(3):
            txs.append(f.uv[vertexid][0])
            tys.append(f.uv[vertexid][1])

    xr = range_adjust(min(xs), max(xs))
    yr = range_adjust(min(ys), max(ys))
    zr = range_adjust(min(zs), max(zs))
    nr = range_adjust(-1.0, 1.0)
    txr = range_adjust(min(txs), max(txs))
    tyr = range_adjust(min(tys), max(tys))
    # ************** write ranges *************
    stream.write(struct.pack("f", xr.min))
    stream.write(struct.pack("f", yr.min))
    stream.write(struct.pack("f", zr.min))
    stream.write(struct.pack("f", xr.max))
    stream.write(struct.pack("f", yr.max))
    stream.write(struct.pack("f", zr.max))
    stream.write(struct.pack("f", txr.min))
    stream.write(struct.pack("f", 1 - min(tys)))
    stream.write(struct.pack("f", txr.max))
    stream.write(struct.pack("f", 1 - max(tys)))
    # ************ write unknown4 *************
    write_null("BBBBBBBBBBBBBBBB", stream)
    # *********** write switch count **********
    write_null("L", stream)
    del (xs, ys, zs, txs, tys)
    verts = []
    for f in mesh.faces:
        if len(f.v) != 3:
            stream.close()
            raise ValueError("Incorrect number of vertices. Only triangles are supported.")
        for vertexid in range(3):
            v = f.v[vertexid]
            cv = []
            cv.append(xr.adjust(v.co[0]))
            cv.append(yr.adjust(v.co[1]))
            cv.append(zr.adjust(v.co[2]))
            cv.append(nr.adjust(v.no[0]))
            cv.append(nr.adjust(v.no[1]))
            cv.append(nr.adjust(v.no[2]))
            cv.append(txr.adjust(f.uv[vertexid][0]))
            cv.append(tyr.adjust(f.uv[vertexid][1]))
            if cv in verts:
                newid = verts.index(cv)
            else:
                verts.append(cv)
                newid = len(verts) - 1
            # ****** write face vertexid *******
            stream.write(struct.pack("H", newid))
    if len(mesh.faces) & 1:
        stream.write("\x00\x00")
    vpos = stream.tell()
    stream.seek(vcpos)
    stream.write(struct.pack("L", len(verts)))
    stream.seek(vpos)
    for v in verts:
        # ********** write vertex **************
        stream.write(struct.pack("HHHHHHHH", \
            v[0], v[1], v[2], v[3], v[4], v[5], v[6], v[7]))
    # to be continued - weights!!!

#***********************************************
# main export function
#***********************************************

def save_msh(filename):
    global material_list, material_keys, meshlog
    global binding, floor, wall, land, mesh1, foundation, mesh2



    time1 = Blender.sys.time()  #for timing purposes

    meshlog = open (filename + '.export.log', 'w')

    image_list = []
    for i in Image.Get():
       image_list.append(i.getFilename())
    
    group_classes = {}
    mesh_list = {}
    mesh_flags = [0,0,0,0,0,0,0,0]
    if Armature.Get() != {}:
        mesh_flags[0] = 1

    binding = None
    floor = None
    wall = None
    land = None
    mesh1 = None
    foundation = None
    mesh2 = None
    transform_list = []
    submesh_list = []
    room_list = {}
    control_list = []
    for m in Blender.Object.Get():
        if not m.getType() == "Mesh":
            continue
	# Either-or. The import script sets the name of the Datagroup, but
	# originally here we were looking at the Mesh group itself.
	# changed to datablock as that's what the import script affects
        n = m.getData().name
	meshlog.write('> Exporting Mesh: "%s"' % (n))
        #n = m.name
#        print 'Mesh: "%s" ' % (n)
#        print 'DB: "%s" ' % (m.getData().name)
        if n.endswith('.binding'):
            binding = m
            mesh_flags[2] |= 1
            control_list.append(m)
        elif n.endswith('.floor'):
            floor = m
#            print ':IsFloor'
            mesh_flags[6] |= 1
            control_list.append(m)
        elif n.endswith('.wall'):
            wall = m
            mesh_flags[6] |= 8
            control_list.append(m)
        elif n.endswith('.land'):
            land = m
#            print ':IsLand'
            mesh_flags[5] |= 2
            control_list.append(m)
        elif n.endswith('.mesh1'):
            mesh1 = m
            mesh_flags[6] |= 4
            control_list.append(m)
        elif n.endswith('.foundation'):
            foundation = m
            mesh_flags[5] |= 4
            control_list.append(m)
        elif n.endswith('.mesh2'):
            mesh2 = m
            mesh_flags[6] |= 16
            control_list.append(m)

	# change to wildcard to hopefully push rooms into correct spot
        elif n.endswith('.room'):
            mesh_flags[6] |= 64
            room_list[n] = m

        elif room_mesh.match(n):
            mesh_flags[6] |= 64
            room_list[n] = m

        else:
	    print '--- ' + n
            r = grouped_mesh.match(n)
            if r:
                group_class, groupid = r.groups()
                group_classes[groupid] = group_class
                if mesh_list.has_key(groupid):
                    mesh_list[groupid].append(m)
                else:
                    mesh_list[groupid] = [m]
            else:
                r = numbered_mesh.match(n)
                if r:
                    mesh_name = r.groups()[0]
                    if mesh_list.has_key(mesh_name):
                        mesh_list[mesh_name].append(m)
                    else:
                        mesh_list[mesh_name] = [m]
                else:
                    if mesh_list.has_key(n):
                        mesh_list[n].append(m)
                    else:
                        mesh_list[n] = [m]
            mats = m.getData().getMaterials()
            if mats:
                mat = mats[0]
                if mat.name not in material_keys:
                    material_list.append(mat)
                    material_keys.append(mat.name)
    
    #*******************************************
    # write header
    #*******************************************
    stream = open(filename, 'wb')
    stream.write(struct.pack("L",10))
    
    # ************ write image count *********** 
    stream.write(struct.pack("L", len(image_list)))
    meshlog.write('\n\n---> msh_header')
    meshlog.write('\nImages: %d' % (len(image_list)))

    # *********** write material count *********
    stream.write(struct.pack("L", len(material_keys)))
    meshlog.write('\nMaterials: %d' % (len(material_keys)))

    # ********** write mesh count *************
    stream.write(struct.pack("L",len(mesh_list)))
    meshlog.write('\nGroups: %d' % (len(mesh_list)))


#    meshlog.write('\nBones: %s' % self.has_bones)
#    meshlog.write('\nDeform: %d' % self.has_deform_groups)
#    meshlog.write('\nAnchor: %d' % self.anchor_count)
#     meshlog.write('\nBinding: %d' % self.has_binding)

#    meshlog.write('\nFlags1:')
#    meshlog.write('\n    HasLand (2): %s' % self.has_land)
#    meshlog.write('\n    HasFoundation (4): %s' % self.has_foundation)
#    meshlog.write('\n    HasLast (128): %s' % self.has_last)
#    meshlog.write('\nFlags2:')
#    meshlog.write('\n    HasFloor (1): %s' % self.has_floor)
#    meshlog.write('\n    HasTransform (2): %s' % self.has_transform)
#    meshlog.write('\n    HasMesh1 (4): %s' % self.has_mesh1)
#    meshlog.write('\n    HasWall (8): %s' % self.has_wall)
#    meshlog.write('\n    HasMesh2 (16): %s' % self.has_mesh2)
#    meshlog.write('\n    HasRooms (64): %s' % self.has_rooms)
#    meshlog.write('\n    HasSubmesh (128): %s' % self.has_submesh)
#    meshlog.write('\nUnknown: %d' % self.unknown1)

    # why is all this commented? - ~T
    if group_classes != {}:
        mesh_flags[7] = 1
    
    if submesh_list != []:
        mesh_flags[6] |= 128
        
    if room_list != []:
        mesh_flags[6] |= 64
    
    if transform_list != []:
        mesh_flags[6] |= 2
    
    # ************* write flags ***************
    for flag in mesh_flags:
	meshlog.write('\n   Field: %d' % (flag))
        stream.write(struct.pack("B", flag))
        
    if transform_list != []:
	# ******* write transform count *******
	stream.write(struct.pack("L", len(transform_list)))
	meshlog.write('\nTransform: %d' % (len(transform_list)))

    if submesh_list != []:
	# ******** write submesh count ********
	stream.write(struct.pack("L", len(submesh_list)))
	meshlog.write('\nSubmesh: %d' % (len(submesh_list)))

    if room_list != []:
	# ********** write room count *********
	stream.write(struct.pack("L", len(room_list)))
	meshlog.write('\nRooms: %d' % (len(room_list)))

    meshlog.write('\n<--- msh_header\n\n')


    for i in image_list:
        fn = os.path.basename(i).replace(".png",".dds")
        write_nts(fn, stream)

    for mat in material_list:
        write_material(mat, stream)

    meshlog.write('\n>> Control Meshes')

    write_control_meshes(stream)

# This could potentially be in the wrong order.
#    for c in control_list:
#        write_basic_mesh(c, stream)

    meshlog.write('\n>> Room List')
    for n in room_list:
        write_nts(n, stream)
        write_basic_mesh(room_list[n], stream)

    meshlog.write('\n>> Mesh List')
    for g in mesh_list:
        write_group(mesh_list[g], stream)

    # bones goes here
    for g in mesh_list:
        write_nts(g, stream)
        
    stream.close()
    meshlog.close()

    print 'finished exporting: "%s" in %.4f sec.' % (filename, (Blender.sys.time()-time1))

#***********************************************
# register callback
#***********************************************
def my_callback(filename):
    save_msh(filename)

Blender.Window.FileSelector(my_callback, "Export MSH", '*.msh')