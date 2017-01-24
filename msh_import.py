#!BPY

"""
Name: 'The Movies (.msh)...'
Blender: 242
Group: 'Import'
Tooltip: 'Import from Lionhead Studios The Movies file format. (.msh)'
"""

__author__ = ["Mark S Andrews"]
__url__ = ("http://themovieseditor.com","http://tmws.themoviesplanet.com")
__version__ = "0.11"
__bpydoc__ = """\

Msh Importer

This script imports a msh file from Lionhead Studio Limited's The Movies
into blender for editing. It is not supported by either Lionhead or
Activision.

It does not currently support 100% of the msh format.

Known Problems:

Group names can be truncated and the id scheme to help with exports is thus
broken.
Duplicate vert removal may be over zealous.

Changes:

0.11 Mark S Andrews 2006-01-31<br>
- Duplicate verts removal added
0.10 Mark S Andrews 2006-01-29<br>
- Added path support for MED
- groupid named
0.09 Mark S Andrews 2006-01-18<br>
- flag for deform_groups changed
0.08 Mark S Andrews 2006-01-15<br>
- Normal range fixed
0.07 Mark S Andrews 2006-01-11<br>
- Cleaned naming convention up
0.06 Mark S Andrews 2006-01-10<br>
- Added mesh deforms
0.05 Mark S Andrews 2006-01-07<br>
- Added bone handling
0.04 Mark S Andrews 2006-01-06<br>
- Refactored
0.03 Mark S Andrews 2006-01-05<br>
- Added alpha handling
0.02 Mark S Andrews 2006-01-04<br>
- Added texture handling
0.01 Mark S Andrews 2006-01-03<br>
- Initial Version

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
from Blender import Image, Material, Texture, Window, Armature
from Blender import Mesh, NMesh
from Blender.Mathutils import Matrix, Vector
import struct, os, math

#***********************************************
# globals
#***********************************************
image_list = []
material_list=[]

#***********************************************
# helper classes & functions for msh file
#***********************************************

def read_item(struct_type, stream):
    value = struct.unpack(struct_type,
        stream.read(struct.calcsize(struct_type)))
    if len(value) == 1:
        value = value[0]
    return value

def read_nts(stream, length=32):
    s = stream.read(length)
    return s.rstrip("\x00")

class decoder(object):
    _struct = ''
    _fields = {}
    _flags = {}
    
    def __init__(self, stream):
        self._value = struct.unpack(self._struct,
            stream.read(struct.calcsize(self._struct)))
    
    def __getattr__(self, item):
        if item in self._fields.keys():
            keyid = self._fields[item]
            return self._value[keyid]
        elif item in self._flags.keys():
            flag, bit = self._flags[item]
            return bool(self._value[flag] & bit)
        else:
            raise AttributeError(item)

    def __repr__(self):
        return repr(self._value)

class range_adjust(object):
    def __init__(self, min, max):
        self.min = min
        self.max = max
        self.step = (max - min) / 65535.0
        object.__init__(self)
    def adjust(self, value):
        return self.min + (value * self.step)

def get_image_path(basepath, filename):
    p = os.path.join(basepath, filename)
    if os.path.isfile(p):
        return p
    else:
        dirs = ["accessories","backdrops", "costumes", "hair", "lightmap",
            "makeup", "people", "props"]
        for dir in dirs:
            p = os.path.join(basepath, dir, filename)
            if os.path.isfile(p):
                return p

#***********************************************
# class definitions for msh file
#***********************************************

class anchor(decoder):
    _struct = "ffffffffffff"
    
    def __init__(self, stream):
        self.anchor_name = read_nts(stream)
        decoder.__init__(self, stream)

class bone(decoder):
    _struct = "lffffffffffff"
    _fields = {"parent":0,
        "x_rest":1,
        "y_rest":2,
        "z_rest":3,
        "x_min":4,
        "y_min":5,
        "z_min":6,
        "x_max":7,
        "y_max":8,
        "z_max":9,
        "x":10,
        "y":11,
        "z":12,
        }
    def __init__(self, stream):
        self.bone_name = read_nts(stream)
        decoder.__init__(self, stream)

class bone_header(decoder):
    _struct = "BBBBL"
    _fields = {"bone_count":4,}

class bone_weights(decoder):
    _struct = "ffffbbbb"
    _fields = {"w0":0,
        "w1":1,
        "w2":2,
        "w3":3,
        "b0":4,
        "b1":5,
        "b2":6,
        "b3":7,
        }

class material(decoder):
    _struct = "bbbbBBBBBBBBBBBBBBBBBBBB"
    _fields = {"map0":0,
        "map1":1,
        "map2":2,
        "map3":3,
        }
    _flags = {"use_alpha":(7,255),
        }

class compressed_vertex(decoder):
    _struct = "HHHHHHHH"
    _fields = {"x":0,
        "y":1,
        "z":2,
        "nx":3,
        "ny":4,
        "nz":5,
        "tx":6,
        "ty":7,
        }

class msh_header(decoder):
    _struct = "LLLLBBBBxBBB"
    _fields = {"image_count":1,
        "material_count":2,
        "group_count":3,
        "anchor_count":6,
        }
    _flags = {"has_bones":(4,255),
        "unknown1":(10,255),
        "has_binding":(7,255),
        "has_land":(8,2),
        "has_foundation":(8,4),
        "has_last":(8,128),
        "has_floor":(9,1),
        "has_transform":(9,2),
        "has_mesh1":(9,4),
        "has_wall":(9,8),
        "has_mesh2":(9,16),
        "has_rooms":(9,64),
        "has_submesh":(9,128),
        "has_deform_groups":(5,255),
        }
    
    def __init__(self, stream):
        decoder.__init__(self, stream)
        if self._value[0] != 10:
            print "Not a valid mesh file"
            return
            
	meshlog.write('Stream: "%s"' % (stream))
        if self.has_transform:
            self.transform_count = read_item("L", stream)
        else:
            self.transform_count = 0
            
        if self.has_submesh:
            self.submesh_count = read_item("L", stream)
        else:
            self.submesh_count = 0
            
        if self.has_rooms:
            self.room_count = read_item("L", stream)
        else:
            self.room_count = 0

class mesh_header(decoder):
    _struct = "LLLBBBB"
    _fields = {"materialid":0,
        "face_count":1,
        "vertex_count":2,
        }
    _flags = {"has_groupid":(3,16),
        "has_unknown2":(3,32),
        "has_unknown3":(3,64),
        "has_lightmap":(4,255),
        "has_weights":(3,1),
        }
    
    def __init__(self, stream):
        decoder.__init__(self, stream)
        # print "Mesh:", self._value
        if self.has_groupid:
            self.groupid = struct.unpack("f", stream.read(4))[0]
        else:
            self.groupid = None
            
        if self.has_unknown2:
            self.unknown2 = read_item("BBBB", stream)
            # print "Mesh.unknown2=", self.unknown2
        else:
            self.unknown2 = None
            
        if self.has_unknown3:
            self.unknown3 = read_item("BBBB", stream)
            # print "Mesh.unknown3=", self.unknown3
        else:
            self.unknown3 = None
        
        min_x = read_item("f", stream)
        min_y = read_item("f", stream)
        min_z = read_item("f", stream)
        max_x = read_item("f", stream)
        max_y = read_item("f", stream)
        max_z = read_item("f", stream)
        min_tx = read_item("f", stream)
        min_ty = read_item("f", stream)
        max_tx = read_item("f", stream)
        max_ty = read_item("f", stream)
        x_range = range_adjust(min_x, max_x)
        y_range = range_adjust(min_y, max_y)
        z_range = range_adjust(min_z, max_z)
        tx_range = range_adjust(min_tx, max_tx)
        ty_range = range_adjust(1.0 - min_ty, 1.0 - max_ty)
        n_range = range_adjust(-1.0, 1.0)
        self.adjust_n = n_range.adjust
        self.adjust_x = x_range.adjust
        self.adjust_y = y_range.adjust
        self.adjust_z = z_range.adjust
        self.adjust_tx = tx_range.adjust
        self.adjust_ty = ty_range.adjust
        
        self.unknown4 = read_item("BBBBBBBBBBBBBBBB", stream)
        #print self.unknown4
        self.switch_count = read_item("L", stream)

class group_header(decoder):
    _struct = "BBBB"
    _fields = {"mesh_count":0,
        }
    _flags = {"has_unknown":(3,16),
        }
    
    def __init__(self, stream):
        decoder.__init__(self, stream)
        #print "Group:", self._value
        matrix = read_item("fffffffff", stream)
        m1 = [matrix[0], matrix[3], matrix[6]]
        m2 = [matrix[1], matrix[4], matrix[7]]
        m3 = [matrix[2], matrix[5], matrix[8]]
        self.matrix = Matrix(m1, m2, m3)
        self.pos = read_item("fff", stream)
        
        if self.has_unknown:
            self.unknown = read_item("L", stream)
        else:
            self.unknown = -1
        
#***********************************************
# reader functions for msh file
#***********************************************

def add_basic_mesh(mesh_name, stream, layer=2):
    meshlog.write('\n>> add_basic_mesh: %s' % (mesh_name))
    vertex_count = read_item("L", stream)
    face_count = read_item("L", stream)
    mesh = NMesh.New(mesh_name)
    for vertexid in range(vertex_count):
        p = read_item("fff", stream)
        v = NMesh.Vert(p[0],p[1],p[2])
        mesh.verts.append(v)
    for faceid in range(face_count):
        face_keys = read_item("HHH", stream)
        v0 = mesh.verts[face_keys[0]]
        v1 = mesh.verts[face_keys[1]]
        v2 = mesh.verts[face_keys[2]]
        f= NMesh.Face([v0, v1, v2])
        mesh.faces.append(f)
    if face_count & 1:
        pad = stream.read(2)
    ob = NMesh.PutRaw(mesh)
    ob.layers = [layer]

def get_mesh(mesh_name, header, stream):
    global material_list
    
    meshlog.write('\n>> get_mesh: %s' % (mesh_name))

    face_list = []
    for faceid in range(header.face_count):
        face_list.append(list(read_item("HHH", stream)))
    if header.face_count & 1:
        pad = stream.read(2)

    vertex_list = []
    for vertexid in range(header.vertex_count):
        vertex_list.append(compressed_vertex(stream))
    
    if header.has_lightmap:
        for vertexid in range(header.vertex_count):
            vertex_list[vertexid].lightmap_u = read_item("H", stream)
            vertex_list[vertexid].lightmap_v = read_item("H", stream)
    
    if header.has_weights:
        for vertexid in range(header.vertex_count):
            vertex_list[vertexid].weights = bone_weights(stream)
    
    switch = {}
    for switchid in range(header.switch_count):
        switch[read_item("L", stream)] = read_item("L", stream)
    #if header.switch_count:
    #    print "Switch:", switch

    mesh = NMesh.New(mesh_name)
    mesh.hasFaceUV(True)
    mesh.materials.append(material_list[header.materialid][0])
    mesh.setMode("TwoSided", "AutoSmooth")
    
    # add mesh vertices
    vertex_index = []
    bones = {}
    for cv in vertex_list:
        x = header.adjust_x(cv.x)
        y = header.adjust_y(cv.y)
        z = header.adjust_z(cv.z)
        nx = header.adjust_n(cv.nx)
        ny = header.adjust_n(cv.ny)
        nz = header.adjust_n(cv.nz)
        v = NMesh.Vert(x, y, z)
        v.no[0] = nx
        v.no[1] = ny
        v.no[2] = nz
        mesh.verts.append(v)
        vertex_id = len(mesh.verts) - 1
        if "weights" in dir(cv):
            if cv.weights.b0 != -1:
                if bones.has_key(cv.weights.b0):
                    if bones[cv.weights.b0].has_key(cv.weights.w0):
                        bones[cv.weights.b0][cv.weights.w0].append(vertex_id)
                    else:
                        bones[cv.weights.b0][cv.weights.w0]= [vertex_id]
                else:
                        bones[cv.weights.b0] = {cv.weights.w0:[vertex_id],}
            if cv.weights.b1 != -1:
                if bones.has_key(cv.weights.b1):
                    if bones[cv.weights.b1].has_key(cv.weights.w1):
                        bones[cv.weights.b1][cv.weights.w1].append(vertex_id)
                    else:
                        bones[cv.weights.b1][cv.weights.w1]= [vertex_id]
                else:
                    bones[cv.weights.b1] = {cv.weights.w1:[vertex_id],}
            if cv.weights.b2 != -1:
                if bones.has_key(cv.weights.b2):
                    if bones[cv.weights.b2].has_key(cv.weights.w2):
                        bones[cv.weights.b2][cv.weights.w2].append(vertex_id)
                    else:
                        bones[cv.weights.b2][cv.weights.w2]= [vertex_id]
                else:
                    bones[cv.weights.b2] = {cv.weights.w2:[vertex_id],}
            if cv.weights.b3 != -1:
                if bones.has_key(cv.weights.b3):
                    if bones[cv.weights.b3].has_key(cv.weights.w3):
                        bones[cv.weights.b3][cv.weights.w3].append(vertex_id)
                    else:
                        bones[cv.weights.b3][cv.weights.w3]= [vertex_id]
                else:
                    bones[cv.weights.b3] = {cv.weights.w3:[vertex_id],}
        
        vertex_index.append(mesh.verts[-1])
                        
    # add textured faces
    for face in face_list:
        v0 = vertex_index[face[0]]
        tx0 = header.adjust_tx(vertex_list[face[0]].tx)
        ty0 = header.adjust_ty(vertex_list[face[0]].ty)
        v1 = vertex_index[face[1]]
        tx1 = header.adjust_tx(vertex_list[face[1]].tx)
        ty1 = header.adjust_ty(vertex_list[face[1]].ty)
        v2 = vertex_index[face[2]]
        tx2 = header.adjust_tx(vertex_list[face[2]].tx)
        ty2 = header.adjust_ty(vertex_list[face[2]].ty)
        f = NMesh.Face([v0, v1, v2])
        f.mode |= NMesh.FaceModes["TEX"]
        f.uv = [(tx0, ty0), (tx1,ty1), (tx2,ty2)]
        if material_list[header.materialid][1]:
            f.image = material_list[header.materialid][1]
        mesh.faces.append(f)
    #todo - smoothing angle...
    #for face in mesh.faces:
    #    face.smooth = 1
    return mesh, bones

#***********************************************
# load msh file
#***********************************************

def load_msh (filename):
    global image_list, material_list, meshlog
    meshlog = open (filename + '.import.log', 'w')
    start_time = Blender.sys.time()
    in_editmode = Window.EditMode()
    if in_editmode:
        Window.EditMode(0)
    stream = open(filename,"rb")
    filepath = os.path.dirname(filename)
    filebase = os.path.basename(filename)
    basename = os.path.splitext(filebase)[0]
    basedir = os.path.split(filepath)[0]
    imagedir = os.path.join(basedir,"textures")
    scene = Blender.Scene.getCurrent()

    meshlog.write('> msh_header\n')
    header = msh_header(stream)

    meshlog.write('\n===========================\n')
    meshlog.write('"%s"' % (header))
    for imageid in range(header.image_count):
        imagefile = read_nts(stream).replace(".dds",".png")
        testimage = os.path.join(filepath, imagefile)
	print 'DEBUG: "%s"' % (testimage)
        if os.path.isfile(testimage):
            imageload = testimage
        else:
            imageload = get_image_path(imagedir, imagefile)
        if imageload:
            image = Image.Load(imageload)
        else:
            imagefile = "Missing: %s"%imagefile
            image = Image.New(imagefile,32,32,24)
            print "Image", imagefile
        image_list.append(image)
        #print "Image %s:"%imageid, imagefile

    for materialid in range(header.material_count):
        mat = Material.New("Material")
        mat.setSpec(0)
        mat.setMode('TexFace')
        tmat = material(stream)
        myMap = Texture.MapTo['COL']
        if tmat.use_alpha:
            myMap |= Texture.MapTo['ALPHA']
        if tmat.map0 != -1:
            texname ="Diffuse"
            t = Texture.New(texname)
            t.setType('Image')
            if tmat.use_alpha:
                t.imageFlags |= Texture.ImageFlags['USEALPHA']
            img = t.image = image_list[tmat.map0]
            mat.setTexture(0, t, Texture.TexCo['UV'], myMap)
        else:
            img = None
            
        if tmat.map1 != -1:
            texname ="Reflection"
            t = Texture.New(texname)
            t.setType('Image')
            myMap = Texture.MapTo['CMIR']
            t.imageFlags |= Texture.ImageFlags['USEALPHA']
            t.image = image_list[tmat.map1]
            mat.setTexture(1, t, Texture.TexCo['GLOB'], myMap)
            
        if tmat.map2 != -1:
            print "Lightmap Skipped: ",image_list[tmat.map2].getFilename()
            
        if tmat.map3 != -1:
            texname ="Specular"
            t = Texture.New(texname)
            myMap = Texture.MapTo['SPEC']
            t.setType('Image')
            t.imageFlags |= Texture.ImageFlags['USEALPHA']
            t.image = image_list[tmat.map3]
            mat.setTexture(2, t, Texture.TexCo['UV'], myMap)
        
        if tmat.use_alpha:
            mat.mode |= Material.Modes['ZTRANSP']
            mat.setAlpha(0)
        material_list.append([mat,img])
        #print "Material %s:"%materialid, tmat._value
    
    if header.has_binding:
        n = "%s.binding"%basename
        add_basic_mesh(n, stream, 2)
    
    if header.has_floor:
        n = "%s.floor"%basename
        add_basic_mesh(n, stream, 3)
    
    if header.has_wall:
        n = "%s.wall"%basename
        add_basic_mesh(n, stream, 4)

    if header.has_land:
        n = "%s.land"%basename
        add_basic_mesh(n, stream, 5)
    
    if header.has_mesh1:
        n = "%s.mesh1"%basename
        add_basic_mesh(n, stream, 6)
    
    if header.has_foundation:
        n = "%s.foundation"%basename
        add_basic_mesh(n, stream, 7)
    
    if header.has_mesh2:
        n = "%s.mesh2"%basename
        add_basic_mesh(n, stream, 8)
    
    for roomid in range(header.room_count):
        room = read_nts(stream)
        n = "%s.%s"%(basename, room)
        add_basic_mesh(n, stream, 9)

    object_names = []
    bones = {}
    for groupid in range(header.group_count):
        h = group_header(stream)
        group_name = "Group%02d"%groupid
        for meshid in range(h.mesh_count):
            mh = mesh_header(stream)
            m, b = get_mesh("Mesh", mh, stream)
            ob = NMesh.PutRaw(m)
            #ob.setMatrix(h.matrix)
            #ob.setLocation(h.pos[0], h.pos[1], h.pos[2])
            mn = "%s.%03d"%(group_name,meshid)
            ob.setName(mn)
            object_names.append(mn)
            m2 = Mesh.Get(m.name)
            m2.remDoubles(0.0)
            if b != {}:
                if not bones.has_key(group_name):
                    bones[group_name] = {}
                bones[group_name][ob.name] = b
    
    if header.has_bones:
        arm = Blender.Object.New('Armature',basename)
        scene.link(arm)
        a = Armature.Armature('Bones')
        arm.link(a)
        a.makeEditable()
        h = bone_header(stream)
        bone_list=[]
        for boneid in range(h.bone_count):
            tmb = bone(stream)
            b = Armature.Editbone()
            b.name = tmb.bone_name
            b.head = Vector(tmb.x, tmb.y, tmb.z)
            b.tail = Vector(tmb.x + tmb.x_rest, \
                tmb.y + tmb.y_rest, \
                tmb.z + tmb.z_rest)
            bone_list.append(b)
            if tmb.parent != -1:
                b.parent = bone_list[tmb.parent]
            a.bones[b.name] = b
        a.update()
        for gn in bones.keys():
            for mn in bones[gn].keys():
                for boneid in bones[gn][mn].keys():
                    b = bone_list[boneid].name
                    ob = Blender.Object.Get(mn)
                    m = ob.getData()
                    m.addVertGroup(b)
                    for w in bones[gn][mn][boneid].keys():
                        if w < 0 or w > 1:
                            print "Weight out of range:", w
                        v_list = bones[gn][mn][boneid][w]
                        m.assignVertsToGroup(b, v_list, w, 'add')
                    arm.makeParentDeform([ob])
        
    if header.has_deform_groups:
        name_trans = {}
        for groupid in range(header.group_count):
            group_name = "Group%02d"%groupid
            name_trans[group_name] = read_nts(stream)
        for mn in object_names:
            gn, tail = mn.split(".",1)
            if name_trans.has_key(gn):
                mesh = Blender.Object.Get(mn)
                new_name = "%s.%s.%s"%(name_trans[gn], gn[-2:], tail)
                mesh.setName(new_name)
    
    #anchors = []
    #for anchorid in range(header.anchor_count):
    #    anchors.append(anchor(stream))
    #print "Anchors:", len(anchors)

    #leftovers = stream.read()
    #if leftovers != "":
    #    print "Incomplete parsing"
    stream.close()
    meshlog.close()
    
    if in_editmode:
        Window.EditMode(1)
    
    print 'finished importing: "%s" in %.4f sec.' % (filename, (Blender.sys.time()-start_time))
    

#***********************************************
# register callback
#***********************************************
def my_callback(filename):
    load_msh(filename)

Blender.Window.FileSelector(my_callback, "Import MSH", '*.msh')