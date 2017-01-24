#!BPY

"""
Name: 'The Movies (.msh) 2009...'
Blender: 246
Group: 'Import'
Tooltip: 'Import from Lionhead Studios The Movies file format. (.msh)'
"""

__author__ = ["Glen Rickey, Nick Hudson, Mark S Andrews"]
__url__ = ("Director's Cut Modding Foundry","http://www.dcmodding.com")
__version__ = "1.03 04-05-2009"
__bpydoc__ = """\

Msh Importer

This script imports a msh file from Lionhead Studio Limited's The Movies
into blender for editing. It is not supported by either Lionhead or
Activision.

It does not currently support 100% of the msh format.

Known Problems:

ConvexHulls are not read.
Duplicate vert removal may not work.


"""

# ***** BEGIN GPL LICENSE BLOCK *****
#
# Script copyright (C) Mark S Andrews, Nick Hudson, Glen Rickey
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
from Blender import Mesh, NMesh, Group
from Blender.Mathutils import Matrix, Vector, LineIntersect, DotVecs, AngleBetweenVecs, TranslationMatrix
import struct, os, math
import tmConst


#***********************************************
# globals
#***********************************************
image_list = []
material_list=[]
neckdata = []
lmuv_list = []

try:
    group_controlmesh = Group.Get('control_meshes') 
except:
    group_controlmesh = Group.New('control_meshes')
try:
    group_room = Group.Get('rooms') 
except:
    group_room = Group.New('rooms')
try:
    group_shapes = Group.Get('shapes')
except:
    group_shapes = Group.New('shapes')
try:
    group_anchors = Group.Get('anchors')
except: 
    group_anchors = Group.New('anchors')

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
        dirs = ["lightmap","props","costumes","accessories",
            "hair","makeup","people","backdrops"]
        for dir in dirs:
            p = os.path.join(basepath, dir, filename)
            if os.path.isfile(p):
                return p

#***********************************************
# class definitions for msh file
#***********************************************

class anchor(decoder):
    _struct = "ffffffffffff"
    _fields = {"m11":0,
        "m12":1,
        "m13":2,
        "m21":3,
        "m22":4,
        "m23":5,
        "m31":6,
        "m32":7,
        "m33":8,
        "offset_x":9,
        "offset_y":10,
        "offset_z":11,
        }
    
    def __init__(self, stream):
        self.anchor_name = read_nts(stream)
        decoder.__init__(self, stream)
        m1 = [self.m11, self.m12, self.m13]
        m2 = [self.m21, self.m22, self.m23]
        m3 = [self.m31, self.m32, self.m33]
        m4 = [self.offset_x, self.offset_y, self.offset_z]
        self.matrix = Matrix(m1, m2, m3, m4).resize4x4()

class bone(decoder):
    _struct = "lffffffffffff"
    _fields = {"parent":0,
        "m11":1,
        "m12":2,
        "m13":3,
        "m21":4,
        "m22":5,
        "m23":6,
        "m31":7,
        "m32":8,
        "m33":9,
        "offset_x":10,
        "offset_y":11,
        "offset_z":12,
        }
    def __init__(self, stream):
        self.bone_name = read_nts(stream)
        decoder.__init__(self, stream)
        m1 = [self.m31, self.m32, self.m33]
        m2 = [self.m11, self.m12, self.m13]
        m3 = [self.m21, self.m22, self.m23]
##        m1 = [self.m11, self.m21, self.m31]
##        m2 = [self.m12, self.m22, self.m32]
##        m3 = [self.m13, self.m23, self.m33]
        m4 = [self.offset_x, self.offset_y, self.offset_z]
        self.matrix = Matrix(m1, m2, m3, m4).resize4x4()
        
        

class skeleton_header(decoder):
    _struct = "LL"
    _fields = {"rig_id":0,
               "bone_count":1,}

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
    _struct = "bbbbBBBBBBBBBbBxBBBBbbbx"
    _fields = {"map0":0,
        "map1":1,
        "map2":2,
        "map3":3,
        "alphaenvmap":13,
        "color_B":15,
        "color_G":16,
        "color_R":17,
        "color_A":18,
        "scroll_U":19,
        "scroll_V":20,
        "rot_UV":21,
        }
    _flags = {"doublesided":(4,1),
              "floor_shadow_tex":(4,2),
              "alpha_separate":(4,4),
              
              "wrap_U":(5,255),
              "wrap_V":(6,255),
              "use_alpha":(7,255),
              "enable_alpha_test":(8,255),
              "glass":(9,255),
              "water":(10,255),
              "still_water":(11,255),
              "alpha_per_vertex":(12,255),
              
              "invisible":(14,1),
              "not_z_write":(14,2),
              "has_uv":(14,4),
              "self_lit":(14,8),
              "no_floor_shadow":(14,16),
              "no_delaydraw_transp":(14,32),
              "tri_sort":(14,64),
              "additive":(14,128),
              
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
                "has_static_anim":(5,255),
              
                "has_clickable":(7,255),
              
                "Unk":(8,1),
                "has_min_outline":(8,2),
                "has_z_height":(8,4),
                "hide_actor_head":(8,8),
                "hide_actor_hair":(8,16),
                "is_auto_animated":(8,32),
                "tex_replace_mode":(8,64),
                "has_convex_hull":(8,128),
                
                "has_lot_boundary":(9,1),
                "has_shapes":(9,2),
                "has_neg_space":(9,4),
                "has_shadow":(9,8),
                "has_collision":(9,16),
                "has_blueprint":(9,32),
                "has_childmesh":(9,64),
                "has_rooms":(9,128),
                  
                "has_named_groups":(10,255),
        }
    
    def __init__(self, stream):
        decoder.__init__(self, stream)
        if self._value[0] != 10:
            print "FAIL! Not a valid mesh file"
            return
            
        if self.has_shapes:
            self.shape_count = read_item("L", stream)
        else:
            self.shape_count = 0
            
        if self.has_childmesh:
            self.childmesh_count = read_item("L", stream)
        else:
            self.childmesh_count = 0
            
        if self.has_rooms:
            self.room_count = read_item("L", stream)
        else:
            self.room_count = 0

class mesh_header(decoder):
    _struct = "LLLBBBB"
    _fields = {"materialid":0,
               "face_count":1,
               "vertex_count":2,
               "bone_per_vertex":5,
        }
    _flags = {"has_weights":(3,1),
              "has_floor_reflections":(3,2),
              "no_outline":(3,4),
              "is_landscape":(3,8),
              "has_meshid":(3,16),
              "is_compressed":(3,32),
              "has_neckconnect":(3,64),
              "accepts_actor_shadow":(3,128),
              
              "has_lightmap":(4,1),
              "is_minutehand":(4,2),
              "is_hourhand":(4,4),
              "static_backdrop":(4,8),
              
              "unk_flag":(6,255),
        }
    
    def __init__(self, stream):
        decoder.__init__(self, stream)
        # print "Mesh:", self._value
        if self.has_meshid:
            self.indexid = read_item("l", stream)
            self.vertexid = read_item("l", stream)
            self.skeletonid = read_item("l", stream)
        else:
            self.indexid = None
            self.vertexid = None
            self.skeletonid = None
            
        if self.is_compressed:                
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
            min_lm_x = read_item("f", stream)
            min_lm_y = read_item("f", stream)
            max_lm_x = read_item("f", stream)
            max_lm_y = read_item("f", stream)
            x_range = range_adjust(min_x, max_x)
            y_range = range_adjust(min_y, max_y)
            z_range = range_adjust(min_z, max_z)
            tx_range = range_adjust(min_tx, max_tx)
            ty_range = range_adjust(1.0 - min_ty, 1.0 - max_ty)
            lm_x_range = range_adjust(min_lm_x, max_lm_x)
            lm_y_range = range_adjust(1.0 - min_lm_y, 1.0 - max_lm_y) 
            n_range = range_adjust(-1.0, 1.0)
            self.adjust_n = n_range.adjust
            self.adjust_x = x_range.adjust
            self.adjust_y = y_range.adjust
            self.adjust_z = z_range.adjust
            self.adjust_tx = tx_range.adjust
            self.adjust_ty = ty_range.adjust
            self.adjust_lm_x = lm_x_range.adjust
            self.adjust_lm_y = lm_y_range.adjust
        
        if self.has_neckconnect:    
            self.neckconnect_count = read_item("L", stream)
        else:
            self.neckconnect_count = 0

class group_header(decoder):
    _struct = "BBBB"
    _fields = {"mesh_count":0,
        }
    _flags = {"has_transanim":(2,1),
              "is_a_carbody":(2,2),
            
              "is_land":(3,4),
              "hide_reflection":(3,8),
              "has_hidden":(3,16),
              }
    
    def __init__(self, stream):
        decoder.__init__(self, stream)
        #print "Group:", self._value
        matrix = read_item("ffffffffffff", stream) # This had columns.rows reversed... I think that was wrong
        m1 = [matrix[0], matrix[1], matrix[2]]
        m2 = [matrix[3], matrix[4], matrix[5]]
        m3 = [matrix[6], matrix[7], matrix[8]]
        m4 = [matrix[9], matrix[10], matrix[11]]
        self.pivot = Matrix(m1, m2, m3, m4).resize4x4()
        
        
        if self.has_hidden:
            self.hidden_on = read_item("H", stream)
            self.hidden_off = read_item("H", stream)
        else:
            self.hidden_on = 0
            self.hidden_off = 0
        
class shape(decoder):
    _struct = "L"
    _fields = {"unknown":0}
    
    def __init__(self,stream):
        decoder.__init__(self, stream)
        matrix = read_item("ffffffffffff", stream)
        m1 = [matrix[0], matrix[1], matrix[2]]
        m2 = [matrix[3], matrix[4], matrix[5]]
        m3 = [matrix[6], matrix[7], matrix[8]]
        m4 = [matrix[9], matrix[10], matrix[11]]
        self.center = Matrix(m1, m2, m3, m4).resize4x4()
        
        self.dimensions = read_item("fff",stream)
            
#***********************************************
# reader functions for msh file
#***********************************************

def add_control_mesh(mesh_name, stream, layer=2):
    try:
        controlmesh = Blender.Object.Get('ControlMeshes')
    except:
        controlmesh = Blender.Scene.getCurrent().objects.new('Empty','ControlMeshes')
        group_controlmesh.objects.link(controlmesh)
    vertex_count = read_item("L", stream)
    face_count = read_item("L", stream)
    mesh = NMesh.New("control")
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
    controlmesh.makeParent([ob],0,1)
    ob.name = mesh_name
    ob.layers = [layer]
    if mesh_name.startswith("room_"):
        group_room.objects.link(ob)
        if ob.properties.has_key('TheMovies')== False:
            ob.properties['TheMovies'] = {}
        ob.properties['TheMovies']['roomName'] = mesh_name #store full name because Blender clips them...
    else:
        group_controlmesh.objects.link(ob)
    ob.dloc = [0,0,0]
    Window.RedrawAll()

def get_mesh(mesh_name, header, stream):
    global material_list, lmuv_list

    face_list = []
    for faceid in range(header.face_count):
        face_list.append(list(read_item("HHH", stream)))
    if header.face_count & 1:
        pad = stream.read(2)

    vertex_list = []
    for vertexid in range(header.vertex_count):
        vertex_list.append(compressed_vertex(stream))
    
    lmuv_list=[]
    if header.has_lightmap:
        for vertexid in range(header.vertex_count):
            lmuv_list.append(list(read_item("HH", stream)))
    
    if header.has_weights:
        for vertexid in range(header.vertex_count):
            vertex_list[vertexid].weights = bone_weights(stream)
  
    
    neckdata = []
    for nid in range(header.neckconnect_count):
        #neckconnect.append(vertex_list[read_item("L",stream)])
        neckdata.append(read_item("L",stream))
        ncindex = read_item("L", stream) #we don't need this, we'll generate new on export
        #we'll generate a vertex group for this after verts are added ;)

    mesh = NMesh.New(mesh_name)
    mesh.hasFaceUV(True)
    mesh.materials.append(material_list[header.materialid])
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

        # This sets the bones/weights
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
        im = Blender.Material.Get()[header.materialid].getTextures()[0].tex.getImage()
        if im != None:
            f.image = im
        mesh.faces.append(f)
    
    #todo - smoothing angle...
    #for face in mesh.faces:
    #    face.smooth = 1
        
    return mesh, bones, neckdata

#***********************************************
# load msh file
#***********************************************

def load_msh (filename):
    global image_list, material_list, group_controlmesh, lmuv_list
    start_time = Blender.sys.time()
    prev_time = start_time
    in_editmode = Window.EditMode()
    if in_editmode:
        Window.EditMode(0)
    stream = open(filename,"rb")
    filepath = os.path.dirname(filename)
    filebase = os.path.basename(filename)
    fullbase = os.path.splitext(filebase)[0]
    basename = fullbase[0:21] #Blender has a $%$@ 21-char limit!
    basedir = os.path.split(filepath)[0]
    imagedir = os.path.join(basedir,"textures")
    scene = Blender.Scene.GetCurrent()
    scene.setLayers([1])
    header = msh_header(stream)
    
    ##  populate Scene ID Properties    
    mshType = 'Undefined'
    if scene.properties.has_key('TheMovies')== False:
            scene.properties['TheMovies'] = {}
            
    scene.properties['TheMovies']['mshName'] = fullbase
    if fullbase.startswith("set_") or fullbase.startswith("sld_"):
        mshType = 'Set'
    if fullbase.startswith("fac_") or fullbase.startswith("fld_"):
        mshType = 'Facility'
    if fullbase.startswith("p_car_") or fullbase.startswith("lp_car_"):
        mshType = 'Car'
    if fullbase.startswith("p_") or fullbase.startswith("lp_"):
        mshType = 'Prop'
    if fullbase.startswith("cos_f_") :
        mshType = 'FemaleCostume'
    if fullbase.startswith("cos_m_") :
        mshType = 'MaleCostume'
    if fullbase.startswith("acc_") :
        mshType = 'Accessory'
    if fullbase.startswith("hair_") :
        mshType = 'Hair'
    if fullbase.startswith("hat_") :
        mshType = 'Hat'
    if fullbase.startswith("latex_") :
        mshType = 'Latex'
    if fullbase.startswith("blp_") :
        mshType = 'Blueprint'
    if fullbase.startswith("bd_") :
        mshType = 'Backdrop'
    scene.properties['TheMovies']['mshType'] = mshType
            
    scene.properties['TheMovies']['hide_actor_head'] = header.hide_actor_head
    scene.properties['TheMovies']['hide_actor_hair'] =  header.hide_actor_hair
    scene.properties['TheMovies']['is_auto_animated'] = header.is_auto_animated
    scene.properties['TheMovies']['tex_replace_mode'] = header.tex_replace_mode
    scene.properties['TheMovies']['has_static_anim'] = header.has_static_anim
    scene.properties['TheMovies']['has_shapes'] = header.has_shapes
    scene.properties['TheMovies']['has_childmesh'] = header.has_childmesh
    scene.properties['TheMovies']['has_rooms'] = header.has_rooms

    for imageid in range(header.image_count):
        imagefile = read_nts(stream)#.replace(".dds",".png")
        testimage = os.path.join(filepath, imagefile)
        print 'DEBUG: "%s"' % (testimage)
        if os.path.isfile(testimage):
            imageload = testimage
        else:
            imageload = get_image_path(imagedir, imagefile)
        if imageload:
            image = Image.Load(imageload)
        else:
            #imagefile = "%s"%imagefile
            image = Image.New(imagefile,32,32,24)
            print "Image", imagefile
        image_list.append(image)
        #print "Image %s:"%imageid, imagefile
    print 'images loaded: %.4f sec.' % (Blender.sys.time()-prev_time)
    prev_time = Blender.sys.time()
    
    for materialid in range(header.material_count):
        mat = Material.New("Material")
        mat.setSpec(0)
        mat.setMode('TexFace')
        tmat = material(stream)
        mat.setRGBCol(tmat.color_R/255.0,tmat.color_G/255.0,tmat.color_B/255.0)
        mat.setAlpha(tmat.color_A/255.0)
        myMap = Texture.MapTo['COL']           
          
        #Diffuse
        texname ="Diffuse"
        t = Texture.New(texname)
        if tmat.use_alpha:
            t.useAlpha = 1
##            t.imageFlags |= Texture.ImageFlags.USEALPHA
            myMap |= Texture.MapTo['ALPHA']
        else:
            t.useAlpha = 0
        if tmat.map0 != -1:
            t.setType('Image')
            t.image = image_list[tmat.map0]
        else:
            t.setType('None')
##            img = None
        mat.setTexture(0, t, Blender.Texture.TexCo.UV, myMap)
            
        #Reflection
        texname ="Reflection"
        t = Texture.New(texname)
        mat.mode |= Material.Modes.RAYMIRROR
        myMap = Texture.MapTo['RAYMIR']
        t.imageFlags |= Texture.ImageFlags.USEALPHA
        if tmat.map1 != -1:
            t.setType('Image') 
            t.image = image_list[tmat.map1]
        else:
            t.setType('None')
        mat.setTexture(1, t, Blender.Texture.TexCo.REFL, myMap)
            
        #Lightmap
        texname = "Lightmap"
        t = Texture.New(texname)
        myMap = Texture.MapTo['COL']
        if tmat.map2 != -1:
            t.setType('Image')
            t.image = image_list[tmat.map2]
        else:
            t.setType('None')
        mat.setTexture(2, t, Blender.Texture.TexCo.UV, myMap)
        
        #Specular
        texname ="Specular"
        t = Texture.New(texname)
        myMap = Texture.MapTo['SPEC'] | Texture.MapTo['CSP']
        t.imageFlags |= Texture.ImageFlags.USEALPHA
        if tmat.map3 != -1:
            t.setType('Image')
            t.image = image_list[tmat.map3]
        else:
            t.setType('None')
        mat.setTexture(3, t, Blender.Texture.TexCo.UV, myMap)
        
        if tmat.use_alpha:
            mat.mode |= Material.Modes['ZTRANSP']
            mat.setAlpha(0)
            
        #Enable or Disable unused Texture Channels
        enabledChans=[]
        if tmat.map0 != -1:
            enabledChans.append(0)
        if tmat.map1 != -1:
            enabledChans.append(1)
        if tmat.map2 != -1:
            enabledChans.append(2)
        if tmat.map3 != -1:
            enabledChans.append(3)
        mat.enabledTextures = []
        mat.enabledTextures = enabledChans
            
        mTx = mat.getTextures()[:]
        mbaseTex = mTx[0]
        mbaseTex.uvlayer = 'UVTex'
        mbaseRf = mTx[1]
        mbaseRf.blendmode = Blender.Texture.BlendModes['DIFFERENCE']
        mbaseLM = mTx[2]
        mbaseLM.blendmode = Blender.Texture.BlendModes['MULTIPLY']
        mbaseLM.uvlayer = 'LightMap'
        mbaseSp = mTx[3]
        mbaseSp.blendmode = Blender.Texture.BlendModes['DIFFERENCE']

        
        if tmat.invisible:
            mat.setMode('Wire')
        
        ## Populate Material ID Properties
        if mat.properties.has_key('TheMovies')== False:
            mat.properties['TheMovies'] = {}
        mat.properties['TheMovies']['doublesided'] = tmat.doublesided
        mat.properties['TheMovies']['floor_shadow_tex'] = tmat.floor_shadow_tex
        mat.properties['TheMovies']['alpha_separate'] =  tmat.alpha_separate
        mat.properties['TheMovies']['wrap_U'] = tmat.wrap_U
        mat.properties['TheMovies']['wrap_V'] = tmat.wrap_V
        mat.properties['TheMovies']['enable_alpha_test'] = tmat.enable_alpha_test
        mat.properties['TheMovies']['glass'] = tmat.glass
        mat.properties['TheMovies']['water'] = tmat.water
        mat.properties['TheMovies']['still_water'] = tmat.still_water
        mat.properties['TheMovies']['alpha_per_vertex'] = tmat.alpha_per_vertex
        mat.properties['TheMovies']['alphaenvmap'] = tmat.alphaenvmap        
        mat.properties['TheMovies']['invisible'] = tmat.invisible
        mat.properties['TheMovies']['not_z_write'] = tmat.not_z_write
        mat.properties['TheMovies']['self_lit'] = tmat.self_lit
        mat.properties['TheMovies']['no_floor_shadow'] = tmat.no_floor_shadow
        mat.properties['TheMovies']['no_delaydraw_transp'] = tmat.no_delaydraw_transp
        mat.properties['TheMovies']['tri_sort'] = tmat.tri_sort
        mat.properties['TheMovies']['additive'] = tmat.additive
        mat.properties['TheMovies']['scroll_U'] = tmat.scroll_U
        mat.properties['TheMovies']['scroll_V'] = tmat.scroll_V
        mat.properties['TheMovies']['rot_UV'] = tmat.rot_UV
        
        material_list.append(mat)
    
    print 'materials processed: %.4f sec.' % (Blender.sys.time()-prev_time)
    prev_time = Blender.sys.time()
    
    if header.has_clickable:
        n = "clickable"
        add_control_mesh(n, stream, 2)
    
    if header.has_collision:
        n = "collision"
        add_control_mesh(n, stream, 2)
    
    if header.has_shadow:
        n = "shadow"
        add_control_mesh(n, stream, 2)

    if header.has_z_height:
        n = "z_height"
        add_control_mesh(n, stream, 2)
    
    if header.has_neg_space:
        n = "neg_space"
        add_control_mesh(n, stream, 2)
    
    if header.has_min_outline:
        n = "min_outline"
        add_control_mesh(n, stream, 2)
    
    if header.has_lot_boundary:
        n = "lot_boundary"
        add_control_mesh(n, stream, 2)
    
    for roomid in range(header.room_count):
        roomname = read_nts(stream)
        n = roomname
        add_control_mesh(n, stream, 3)
        
    print 'controlmeshes done: %.4f sec.' % (Blender.sys.time()-prev_time)
    prev_time = Blender.sys.time()

    object_names = []
    group_names = []
    bones = {}
    for groupid in range(header.group_count):
        h = group_header(stream)
        group_name = "%02d"%groupid
        piv = scene.objects.new('Empty',group_name)
        piv.setMatrix(h.pivot)
        group_names.append(group_name)
        #scene.objects.link(piv)
        
        try:
            group_obj = Group.Get(group_name) 
        except:
            group_obj = Group.New(group_name)
            
        group_obj.objects.link(piv)
        
        ## Populate Group ID Properties
        if piv.properties.has_key('TheMovies')==False:
            piv.properties['TheMovies'] = {}
        piv.properties['TheMovies']['has_transanim'] = h.has_transanim
        piv.properties['TheMovies']['is_land'] = h.is_land
        piv.properties['TheMovies']['is_a_carbody'] = h.is_a_carbody
        piv.properties['TheMovies']['hide_reflection'] = h.hide_reflection
        piv.properties['TheMovies']['has_hidden'] = h.has_hidden
        piv.properties['TheMovies']['hidden_on'] = h.hidden_on
        piv.properties['TheMovies']['hidden_off'] = h.hidden_off

        for meshid in range(h.mesh_count):
            mh = mesh_header(stream)
            m, b, nd = get_mesh("Mesh.%03d"%meshid, mh, stream)
            ob = NMesh.PutRaw(m)
            
            mn = "%s.%03d"%(group_name,meshid)
            ob.setName(mn)
            object_names.append(mn)
            m2 = Mesh.Get(ob.data.name)
            m2.remDoubles(0.0)
            
            ## Populate Mesh ID Properties
            if m2.properties.has_key('TheMovies')==False:
                m2.properties['TheMovies']={}
            m2.properties['TheMovies']['has_floor_reflections'] = mh.has_floor_reflections
            m2.properties['TheMovies']['no_outline'] = mh.no_outline
            m2.properties['TheMovies']['is_landscape'] = mh.is_landscape
            m2.properties['TheMovies']['has_neckconnect'] = mh.has_neckconnect #user has to change this to override
            m2.properties['TheMovies']['accepts_actor_shadow'] = mh.accepts_actor_shadow
            #m2.properties['TheMovies']['has_lightmap'] = mh.has_lightmap
            m2.properties['TheMovies']['is_minutehand'] = mh.is_minutehand
            m2.properties['TheMovies']['is_hourhand'] = mh.is_hourhand
            m2.properties['TheMovies']['static_backdrop'] = mh.static_backdrop
            m2.properties['TheMovies']['unk_flag'] = mh.unk_flag
            m2.properties['TheMovies']['has_meshid'] = mh.has_meshid
            m2.properties['TheMovies']['bone_per_vertex'] = mh.bone_per_vertex
            if mh.has_meshid:
                m2.properties['TheMovies']['indexid'] = mh.indexid
                m2.properties['TheMovies']['vertexid'] = mh.vertexid
                m2.properties['TheMovies']['skeletonid'] = mh.skeletonid
                m2.properties['TheMovies']['generate_new_id'] = 1
            else:
                m2.properties['TheMovies']['indexid'] = 0
                m2.properties['TheMovies']['vertexid'] = 0
                m2.properties['TheMovies']['skeletonid'] = 0
                m2.properties['TheMovies']['generate_new_id'] = 0
            
            if b != {}:
                if not bones.has_key(group_name):
                    bones[group_name] = {}
                bones[group_name][ob.name] = b
            
            # Add lightmap UV
            if Blender.Get('version')>=243:
                if mh.has_lightmap:
                    MNewUV = ob.getData(False,True)
                    #MNewUV = MList[ob.name]
                    MNewUV.addUVLayer('LightMap')
                    MNewUV.activeUVLayer = 'LightMap'
                    for f in MNewUV.faces:
                        lmx0 = mh.adjust_lm_x(lmuv_list[f.verts[0].index][0])
                        lmy0 = mh.adjust_lm_y(lmuv_list[f.verts[0].index][1])
                        lmx1 = mh.adjust_lm_x(lmuv_list[f.verts[1].index][0])
                        lmy1 = mh.adjust_lm_y(lmuv_list[f.verts[1].index][1])
                        lmx2 = mh.adjust_lm_x(lmuv_list[f.verts[2].index][0])
                        lmy2 = mh.adjust_lm_y(lmuv_list[f.verts[2].index][1])
                        v0 = Blender.Mathutils.Vector(lmx0,lmy0)
                        v1 = Blender.Mathutils.Vector(lmx1,lmy1)
                        v2 = Blender.Mathutils.Vector(lmx2,lmy2)
                        f.uv = [v0,v1,v2]
                        im = Blender.Material.Get()[mh.materialid].getTextures()[2].tex.getImage()
                        if im != None:
                            f.image = im
                    MNewUV.update
                    MNewUV.activeUVLayer = 'UVTex'
            else:
                print "FAIL! This version of Blender doesn't support lightmaps.  You need 2.43 or greater.  Skipping!"
            #Create NeckConnect vertex Group
            
            print 'mesh %s: %.4f sec.' % (mn, Blender.sys.time()-prev_time)
            prev_time = Blender.sys.time()
            Window.RedrawAll()
            
            if mh != None:
                if mh.has_neckconnect:
                    if mh.neckconnect_count > 0:
                        MVGr = ob.getData(False, True)
                        MVGr.addVertGroup('neckconnect')
                        MVGr.assignVertsToGroup('neckconnect',nd, 0.0,Blender.Mesh.AssignModes.ADD)
                        MVGr.update    

    if header.has_bones:
        h = skeleton_header(stream)
        arm = Blender.Object.New('Armature',str(h.rig_id))
        scene.objects.link(arm)
        
        ## Populate Skeleton ID Properties
        if arm.properties.has_key('TheMovies')==False:
                arm.properties['TheMovies']={}
        if tmConst.RIG_IDS.has_key(h.rig_id):
            arm.properties['TheMovies']['skeletonType'] = tmConst.RIG_IDS[h.rig_id]
        else: 
            arm.properties['TheMovies']['skeletonType'] = 'Unknown'
        a = arm.getData()
        a.name = 'Bones'
        #arm.link(a) #< - deprecated
        a.makeEditable()
        a.envelopes = False
        a.autoIK = True
        a.drawType = Armature.STICK
        
        bone_list=[]
        safebones = []

        for boneid in range(h.bone_count):
            tmb = bone(stream)
            #Store bone-order data...
            if arm.properties['TheMovies'].has_key('BoneOrder')==False:
                arm.properties['TheMovies']['BoneOrder']={}
            arm.properties['TheMovies']['BoneOrder'][str(boneid)]=tmb.bone_name
            b = Armature.Editbone()
            b.name = tmb.bone_name
            b.matrix = tmb.matrix 
            b.matrix = b.matrix * Blender.Mathutils.ScaleMatrix(.125,3)
            bone_list.append(b)
            safebones.append(b.name)
            
            if tmb.parent != -1:
                bparent = bone_list[tmb.parent]
                if bparent.tail != b.head:
                    bangle = AngleBetweenVecs(bparent.tail - bparent.head, bparent.tail - b.head)
                    if bangle <0.0009 or (180-bangle)<.0009:
                        if (bparent.head-b.head).magnitude >.0009:
                            bone_list[tmb.parent].tail = b.head
                            b.options = Blender.Armature.CONNECTED
                else:
                    b.options = Blender.Armature.CONNECTED
##                bintersect = LineIntersect(b.head, b.tail, bparent.head, bparent.tail)
##                if bintersect != None:
##                    #checkdistance = abs((bintersect[0][0] - b.head[0]) + (bintersect[0][1] - b.head[1]) + (bintersect[0][2] - b.head[2]))
##                    checkdistance = (bintersect[0] - b.head).magnitude
##                    
##                else:
##                    #lines are parallel, time to get tricksy
##                    pa = bparent.head
##                    pb = b.head
##                    pc = pb * (DotVecs(pa,pb)/DotVecs(pb,pb))
##                    if pa > pb:
##                        checkdistance = (pb - pc).magnitude
##                    else:
##                        checkdistance = (pa - pc).magnitude
##                    #checkdistance = abs((b.head[0]-bparent.head[0])+(b.head[1]-bparent.head[1])+(b.head[2]-bparent.head[2])) 
##                if checkdistance < .0095:
##                    if (bparent.head - b.head).magnitude > .006 :
##                        bone_list[tmb.parent].tail = b.head
                b.parent = bone_list[tmb.parent]
            a.bones[b.name] = b
        a.update()
        
        print 'bones added: %.4f sec.' % (Blender.sys.time()-prev_time)
        prev_time = Blender.sys.time()
        
        # Since (for some unknown reason), the bone_list was being corrupted,
        # I've changed this to save the names, as that's the only bit we
        # seem to be using here.
        for gn in bones.keys():
            for mn in bones[gn].keys():
                for boneid in bones[gn][mn].keys():
                    bname = safebones[boneid]
                    ob = Blender.Object.Get(mn)
                    m = ob.getData()
                    m.addVertGroup(bname)
                    for w in bones[gn][mn][boneid].keys():
                        if w < 0 or w > 1:
                            print "FAIL! Weight out of range:", w
                        v_list = bones[gn][mn][boneid][w]
                        m.assignVertsToGroup(bname, v_list, w, 'add')
                    arm.makeParentDeform([ob])
                    
        print 'bones weighted: %.4f sec.' % (Blender.sys.time()-prev_time)
        prev_time = Blender.sys.time()
                    
    # Groups
    name_trans = {}
    for groupid in range(header.group_count):
        group_name = "%02d"%groupid
        gread = group_name
        if header.has_static_anim or header.has_named_groups: 
            gread = read_nts(stream)
        name_trans[group_name] = gread
        gr = Blender.Object.Get(group_names[groupid])
        gr.setName(group_name + "." + gread)
        gr.properties['TheMovies']['grpName'] = gread
        group_obj = Blender.Group.Get(group_names[groupid])
        group_obj.name = group_name + "." + gread
        name_trans[group_name] = gr.getName()
        
        
    for mn in object_names:
        gn, tail = mn.split(".",1)
        if name_trans.has_key(gn):
            gr = Blender.Object.Get(name_trans[gn])
            group_obj = Blender.Group.Get(name_trans[gn])
            mesh = Blender.Object.Get(mn)
            new_name = "Object.%s"%( tail)
            mesh.setName(new_name)
            # if mesh is child of Armature, make Armature the child of Group, otherwise
            # make mesh child of Group
            if mesh.parentType == Blender.Object.ParentTypes.ARMATURE:
                gr.makeParent([mesh.parent],0,1)
            else:
                gr.makeParent([mesh],0,1)
            #mesh.setMatrix(gr.getMatrix("localspace").invert())
            group_obj.objects.link(mesh)
    
    print 'Groups finalized: %.4f sec.' % (Blender.sys.time()-prev_time)
    prev_time = Blender.sys.time()
                
    
    if header.anchor_count > 0 :
        anchors = []
        try:
            anchParent = Blender.Object.Get('Anchors')
        except:
            anchParent = scene.objects.new('Empty',"Anchors")
            #scene.objects.link(anchParent)
            group_anchors.objects.link(anchParent)
        for anchorid in range(header.anchor_count):
            ca = anchor(stream)
            anch = scene.objects.new('Empty',ca.anchor_name)
            anch.setMatrix (ca.matrix)
            #scene.objects.link(anch)
            group_anchors.objects.link(anch)

            ## Populate Anchor ID Properties
            if anch.properties.has_key('TheMovies')==False:
                anch.properties['TheMovies'] = {}
            anch.properties['TheMovies']['ancName'] = ca.anchor_name
            
            anchors.append(anch)
        anchParent.makeParent(anchors,0,1)
        
    print 'anchors processed: %.4f sec.' % (Blender.sys.time()-prev_time)
    prev_time = Blender.sys.time()
    
    #Convex Hull goes here -- but...we're skipping it...    
    if header.has_convex_hull:
        chullsize = read_item("L", stream)
        print 'convex hull: %s bytes, skipping.' %chullsize
        stream.seek(chullsize-4,1)
        
    if header.has_shapes:
        if header.shape_count > 0:
            scene.layers.append(4)
            scene.setLayers([4])
            try:
                shParent = Blender.Object.Get('Shapes')
            except:
                shParent = scene.objects.new('Empty','Shapes')
##                shParent.Layer = 0x08
                #scene.objects.link(shParent)
                group_shapes.objects.link(shParent)
            shapes = []
            for shapeid in range(header.shape_count):
                sh = shape(stream)
                shcube = Mesh.Primitives.Cube(1.0)
                shcube.transform(TranslationMatrix(Vector([0,0,0.5])),1,0)
                shapeobj = scene.objects.new(shcube,'Shape')
                shapeobj.setMatrix(sh.center)
                shapeobj.size = sh.dimensions
                shapeobj.dloc = [0,0,0]
                group_shapes.objects.link(shapeobj)
                shapes.append(shapeobj)
                Window.RedrawAll()
##                shapeobj.Layer = 0x08
            shParent.makeParent(shapes,0,1)
            
    print 'shapes processed: %.4f sec.' % (Blender.sys.time()-prev_time)
    prev_time = Blender.sys.time()
                
    stream.close()
    
    if in_editmode:
        Window.EditMode(1)
    scene.setLayers([1])
    Blender.Redraw()

    
    print 'finished importing: "%s" in %.4f sec.' % (filename, (Blender.sys.time()-start_time))
    

#***********************************************
# register callback
#***********************************************
def my_callback(filename):
    load_msh(filename)

Blender.Window.FileSelector(my_callback, "Import MSH", '*.msh')