#!BPY

"""
Name: 'The Movies (.msh) 2009...'
Blender: 246
Group: 'Export'
Tooltip: 'Export to Lionhead Studios The Movies file format. (.msh)'
"""

__author__ = ["Glen Rickey, Nick Hudson, Mark S Andrews"]
__url__ = ("Director's Cut Modding Foundry","http://www.dcmodding.com")
__version__ = "1.04 05-07-2009"
__bpydoc__ = """\

Msh Exporter

This script exports a msh file for use with Lionhead Studio Limited's
The Movies. It is not supported by either Lionhead or Activision.

It does not currently support all features of the msh files.

Known Problems:

ConvexHulls are not exported.
Requires very properly formatted file.  Use tm_preflight.py script to condition scene data first.

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
from Blender import Image, Material, Texture, NMesh, Window, Armature, Group
from Blender.Mathutils import Matrix, Vector
from random import randint
import struct, os, re
import tmConst

#***********************************************
# globals
#***********************************************

material_list = []
material_keys = []

unnamed_group = re.compile(r"(\d{2})(\.\d+)?")
static_anim_group = re.compile(r".?_[sc]a_")
#grouped_mesh = re.compile(r'(.+)\.(\d\d)\..+')
#numbered_mesh = re.compile(r'(.+)\.\d+')
#room_mesh = re.compile(r'(.+)\.room\_')


#***********************************************
# helper classes & functions for msh file
#***********************************************

def write_nts(item, stream, length=32):
    if len(item) > length:
        print "ITEM: %s" % (item)
        print "LEN: %d" % (len(item))
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
        self.range = abs(self.max - self.min)
    def adjust(self, value):
        if self.range == 0:
            return 0
        scale = 65535.0 / self.range
        return int((value - self.min) * scale)
    
def getNeckIndex(point, snap_points):
        '''
        Returns the closest vec to snap_points
        '''
        close_dist= 1<<30
        close_vec= None

        x= point[0]
        y= point[1]
        z= point[2]
        for v in snap_points:
                # quick length cmp before a full length comparison.
                if abs(x-v[0]) < close_dist and\
                abs(y-v[1]) < close_dist and\
                abs(z-v[2]) < close_dist:
                        l= (v-point).length
                        if l<close_dist:
                                close_dist= l
                                close_vec= v
        return snap_points.index(close_vec)
    
def adjustBounds(obj):
    mat = obj.mat  
    if obj.getType() == 'Mesh':
        msh = obj.getData(0,1)
        worldverts = [(x.co * mat) for x in msh.verts]
        xMin = min([x[0] for x in worldverts])
        xMax = max([x[0] for x in worldverts])
        yMin = min([y[1] for y in worldverts])
        yMax = max([y[1] for y in worldverts])
        zMin = min([z[2] for z in worldverts])
        zMax = max([z[2] for z in worldverts])
        
        return [
                min([xMin, Bounds[0]]),
                max([xMax, Bounds[1]]), 
                min([yMin, Bounds[2]]),
                max([yMax, Bounds[3]]), 
                min([zMin, Bounds[4]]),
                max([zMax, Bounds[5]])
                ]
        
    elif obj.getType() == 'Empty':
        loc = obj.getLocation('worldspace')
        return [
                min([loc[0], Bounds[0]]),
                max([loc[0], Bounds[1]]), 
                min([loc[1], Bounds[2]]),
                max([loc[1], Bounds[3]]), 
                min([loc[2], Bounds[4]]),
                max([loc[2], Bounds[5]])
                ]
    
def calc_bbox(bounds_list):
    # Compute new extents of bounding box
    xMin = min(map(lambda x: x[0], bounds_list))
    xMax = max(map(lambda x: x[0], bounds_list))
    yMin = min(map(lambda y: y[1], bounds_list))
    yMax = max(map(lambda y: y[1], bounds_list))
    zMin = min(map(lambda z: z[2], bounds_list))
    zMax = max(map(lambda z: z[2], bounds_list))

    return [xMin, xMax, yMin, yMax, zMin, zMax] 


class triface(object):
    def __init__(self, vindex=(0,0,0), faceuvs=None, lmuvs=None):
        self.vertex_index = vindex
        self.faceuvs = faceuvs
        self.lmuvs = lmuvs
    

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
            i[2] = image_list.index(im)
    if texture_list[3]:
        im = texture_list[3].tex.getImage()
        if im:
            i[3] = image_list.index(im)
    
    # *********** write image refs *************
    stream.write(struct.pack("bbbb", i[0], i[1], i[2], i[3]))
    
    #  Material Flags
    matflags0 = 0
    matflags1 = 4 #mesh always has UV
    matflaglist = [1,1,0,0,0,0,0,0,0]
    matscrollU = 0
    matscrollV = 0
    matrotUV = 0
    if mat.properties.has_key('TheMovies'):
        matflags0 |= ((mat.properties['TheMovies']['doublesided'] % 2) * 1)
        matflags0 |= ((mat.properties['TheMovies']['floor_shadow_tex'] % 2) * 2)
        matflags0 |= ((mat.properties['TheMovies']['alpha_separate'] % 2)* 4)
        
        matflaglist[0] = mat.properties['TheMovies']['wrap_U'] % 2
        matflaglist[1] = mat.properties['TheMovies']['wrap_V'] % 2
        matflaglist[2] = use_alpha
        matflaglist[3] = mat.properties['TheMovies']['enable_alpha_test'] % 2
        matflaglist[4] = mat.properties['TheMovies']['glass'] % 2
        matflaglist[5] = mat.properties['TheMovies']['water'] % 2
        matflaglist[6] = mat.properties['TheMovies']['still_water'] % 2
        matflaglist[7] = mat.properties['TheMovies']['alpha_per_vertex'] % 2
        matflaglist[8] = mat.properties['TheMovies']['alphaenvmap'] % 256
        
        matflags1 |= ((mat.properties['TheMovies']['invisible'] % 2) * 1)
        matflags1 |= ((mat.properties['TheMovies']['not_z_write'] % 2) * 2)
        matflags1 |= ((mat.properties['TheMovies']['self_lit'] % 2) * 8)
        matflags1 |= ((mat.properties['TheMovies']['no_floor_shadow'] % 2) * 16)
        matflags1 |= ((mat.properties['TheMovies']['no_delaydraw_transp'] % 2) * 32)
        matflags1 |= ((mat.properties['TheMovies']['tri_sort'] % 2) * 64)
        matflags1 |= ((mat.properties['TheMovies']['additive'] % 2) * 128)

        matscrollU = mat.properties['TheMovies']['scroll_U'] % 256
        matscrollV = mat.properties['TheMovies']['scroll_V'] % 256
        matrotUV = mat.properties['TheMovies']['rot_UV'] % 256
    
    # write Material Flags
    stream.write(struct.pack("B",matflags0))
    for flag in matflaglist:
        stream.write(struct.pack("B", flag))
    stream.write(struct.pack("B", matflags1))
    stream.write("\x00") #padding
    # write material color
    stream.write(struct.pack("BBBB", int(mat.B * 255), int(mat.G * 255), int(mat.R * 255), int(mat.alpha * 255)))
    # write material scroll properties
    stream.write(struct.pack("BBB", matscrollU, matscrollV, matrotUV))
    stream.write("\x00") #padding

#***********************************************
# Write the control meshes in the correct order.
#***********************************************
def write_control_meshes(stream):
    '''This sets the order for writing out a control mesh, since
       we are not sure what order these meshes may come in'''
    if clickable is not None:
        write_basic_mesh(clickable, stream)

    if collision is not None:
        write_basic_mesh(collision, stream)

    if shadow is not None:
        write_basic_mesh(shadow, stream)

    if z_height is not None:
        write_basic_mesh(z_height, stream)

    if neg_space is not None:
        write_basic_mesh(neg_space, stream)

    if min_outline is not None:
        write_basic_mesh(min_outline, stream)

    if lot_boundary is not None:
        write_basic_mesh(lot_boundary, stream)



def write_basic_mesh(mesh, stream):
    '''This is intended for writing out control meshes only, which
       require less data.'''

    meshdata = mesh.getData()
    
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

def write_group(grp, stream):
    meshes = []
    grpflags1 = 0
    grpflags2 = 0
    has_hidden = 0
    hidden_on = 0
    hidden_off = 0
    for ob in grp:
        if ob.getType() == "Empty":
            # get pivot Matrix
            pivot = ob.matrix
            #get ID Properties
            if ob.properties.has_key('TheMovies')==True:
                #flags1
                grpflags1 |= ((ob.properties['TheMovies']['has_transanim'] % 2))
                grpflags1 |= ((ob.properties['TheMovies']['is_a_carbody'] % 2) * 2)
                #flags2
                grpflags2 |= ((ob.properties['TheMovies']['is_land'] % 2) * 4)
                grpflags2 |= ((ob.properties['TheMovies']['hide_reflection'] % 2) * 8)
                has_hidden = ob.properties['TheMovies']['has_hidden'] % 2
                hidden_on = ob.properties['TheMovies']['hidden_on']
                hidden_off = ob.properties['TheMovies']['hidden_off']
            grpflags2 |= (has_hidden * 16)
        if ob.getType() == "Mesh":
            meshes.append(ob)
        
    # *********** write group header ***********
    stream.write(struct.pack("BBBB", len(meshes), 0, grpflags1, grpflags2))
    # ************** write matrix **************
    for p in range(4):
        stream.write(struct.pack("fff", pivot[p][0], pivot[p][1], pivot[p][2]))
    
    if has_hidden:
        stream.write(struct.pack("HH", hidden_on, hidden_off))
        
    for m in meshes:
        write_mesh(m, stream)

def write_mesh(ob, stream):
    # this is the main function for writing a mesh to file. This is for
    # normal meshes only, and should not be used for control meshes 
    # (which don't have textures anyway

    global material_keys
    global bone_list
    # Get ID Properties
    meshflags1 = 32 # all meshes are compressed
    meshflags2 = 0
    is_boned = 0
    has_meshid = 1
    generate_new_id = 1
    has_neckconnect = 0 # we're going to stick to the format, even if Lionhead didn't...
    neckconnect_count = 0
    has_lightmap = 0
    bone_per_vertex = 0
    unkflag = 0
    indexid = 0
    vertexid = -1
    skeletonid = 0
    mesh = ob.getData()
    mobj = ob.getData(False,True)
    if 'LightMap' in mobj.getUVLayerNames():
        has_lightmap = 1
    if len(mesh.getVertGroupNames()) > 0:
        is_boned = 1
        meshflags1 |= 1

    if mesh.properties.has_key('TheMovies')==True:
        #meshflags1
        meshflags1 |= ((mesh.properties['TheMovies']['has_floor_reflections'] % 2) * 2)
        meshflags1 |= ((mesh.properties['TheMovies']['no_outline'] % 2) * 4)
        meshflags1 |= ((mesh.properties['TheMovies']['is_landscape'] % 2) * 8)
        has_meshid = mesh.properties['TheMovies']['has_meshid'] % 2
        generate_new_id = mesh.properties['TheMovies']['generate_new_id'] % 2
        has_neckconnect = mesh.properties['TheMovies']['has_neckconnect'] % 2
        meshflags1 |= ((mesh.properties['TheMovies']['accepts_actor_shadow'] % 2) * 128)
        #meshflags2
        meshflags2 |= has_lightmap
        meshflags2 |= ((mesh.properties['TheMovies']['is_minutehand'] % 2) * 2)
        meshflags2 |= ((mesh.properties['TheMovies']['is_hourhand'] % 2) * 4)
        meshflags2 |= ((mesh.properties['TheMovies']['static_backdrop'] % 2) * 8)
        unkflag = mesh.properties['TheMovies']['unk_flag']
        bone_per_vertex = mesh.properties['TheMovies']['bone_per_vertex']
        if has_meshid:
            if generate_new_id:
                    indexid = randint(0,4294967295)
                    vertexid = -1
                    if is_boned:
                        skeletonid = randint(0,4294967295)
            else:
                indexid = mesh.properties['TheMovies']['indexid']
                vertexid = mesh.properties['TheMovies']['vertexid']
                skeletonid = mesh.properties['TheMovies']['skeletonid']
                
    if 'neckconnect' in mesh.getVertGroupNames():
        has_neckconnect=1
        neckconnect_count = len(mobj.getVertsFromGroup('neckconnect'))
                
    meshflags1 |= has_meshid * 16
    meshflags1 |= has_neckconnect * 64
    mat = mesh.getMaterials()
    # Start Writin' !!
    # ********** write material index **********
    if mat:
        stream.write(struct.pack("L",material_keys.index(mat[0].name)))
    else:
        write_null("L", stream)

    #Get all faces
    face_list = []
    has_uv = mobj.faceUV
    
    if not has_uv:
        face_uv = None
    
    for face in mobj.faces:
        f_v = face.v

        if len(f_v)==3:
            new_face = triface((f_v[0].index, f_v[1].index, f_v[2].index))
            if (has_uv): 
                mobj.activeUVLayer = 'UVTex'
                f_uv = face.uv
                new_face.faceuvs = f_uv[0], f_uv[1],f_uv[2]
            if (has_lightmap):
                mobj.activeUVLayer = 'LightMap'
                f_uv = face.uv
                new_face.lmuvs = f_uv[0], f_uv[1], f_uv[2]
            face_list.append(new_face)
        
        else: #face is a quad, triangulate it!
            new_face = triface((f_v[0].index, f_v[1].index, f_v[2].index))
            new_face_2 = triface((f_v[0].index, f_v[2].index, f_v[3].index))
            
            if (has_uv):
                mobj.activeUVLayer = 'UVTex'
                f_uv = face.uv
                new_face.faceuvs = f_uv[0], f_uv[1], f_uv[2]
                new_face_2.faceuvs = f_uv[0], f_uv[2], f_uv[3]
            if (has_lightmap):
                mobj.activeUVLayer = 'LightMap'
                f_uv = face.uv
                new_face.lmuvs = f_uv[0], f_uv[1], f_uv[2]
                new_face_2.lmuvs = f_uv[0], f_uv[2], f_uv[3]
            
            face_list.append( new_face )
            face_list.append( new_face_2 )
            
    #Process Faces
    vlist = {}
    uvlist  =  {}
    lmuvlist = {}
    dupverts = {}
    new_index = 0
    index_list = []
    
    #calc ranges 

    tx_min = min([f.faceuvs[i][0] for f in face_list for i in range(3)])
    tx_max = max([f.faceuvs[i][0] for f in face_list for i in range(3)])
    ty_min = min([f.faceuvs[i][1] for f in face_list for i in range(3)])
    ty_max = max([f.faceuvs[i][1] for f in face_list for i in range(3)])
    txr = range_adjust(tx_min, tx_max)    
    tyr = range_adjust(ty_min, ty_max)
    if has_lightmap:
        lmx_min = min([f.lmuvs[i][0] for f in face_list for i in range(3)])
        lmx_max = max([f.lmuvs[i][0] for f in face_list for i in range(3)])
        lmy_min = min([f.lmuvs[i][1] for f in face_list for i in range(3)])
        lmy_max = max([f.lmuvs[i][1] for f in face_list for i in range(3)])
        lmxr = range_adjust(lmx_min, lmx_max)
        lmyr = range_adjust(lmy_min, lmy_max)
    else:
        lmxr = range_adjust(0,0)
        lmyr = range_adjust(0,0) 
    xr = range_adjust(Bounds[0], Bounds[1])
    yr = range_adjust(Bounds[2], Bounds[3])
    zr = range_adjust(Bounds[4], Bounds[5])
    nr = range_adjust(-1.0, 1.0)
    
    # first add all the valid verts (those in actual faces)
    goodindx = []
    for tf in mobj.faces:
        for gv in tf.v:
            if gv.index not in goodindx:
                goodindx.append(gv.index)
    goodindx.sort()
                
    for vtex in mobj.verts:
        if vtex.index in goodindx:
            #multiply by objects' 4x4 matrix to get World Coordinates...
            vworld = vtex.co * ob.matrix
            vlist[vtex.index] = [xr.adjust(vworld[0]), \
                yr.adjust(vworld[1]), \
                zr.adjust(vworld[2]), \
                nr.adjust(vtex.no[0]), \
                nr.adjust(vtex.no[1]), \
                nr.adjust(vtex.no[2])]
            #populate the uv / lm lists with spaces
            uvlist[vtex.index] = []
            dupverts[vtex.index] = []
            if (has_lightmap):
                lmuvlist[vtex.index] = []
        
    new_index = max(vlist)+1 #AHA!!
    
    for f in face_list:
        for i in range(3):

            uv = [txr.adjust(f.faceuvs[i][0]),tyr.adjust(f.faceuvs[i][1])]
            v_indx = f.vertex_index[i]
            if (has_lightmap):
                lmuv = [lmxr.adjust(f.lmuvs[i][0]),lmyr.adjust(f.lmuvs[i][1])]
                if uvlist[v_indx] != []:
                    rootindx = dupverts[v_indx][0]
                    matches = []
                    for ckvert in dupverts[v_indx]:
                        if uvlist[ckvert] == uv:
                            matches += [ckvert]
                    if len(matches) == 0:
                    #must be a new UV!
                        #duplicate existing vertex
                        vlist[new_index] = vlist[rootindx]
                        #add its new uv
                        uvlist[new_index] = uv
                        lmuvlist[new_index] = lmuv
                        #add this index to a list so we can find it later
                        dupverts[rootindx] += [new_index]
                        v_indx = new_index
                        new_index += 1
                    else:
                        #Check our lmuvs
                        if lmuvlist[v_indx] != []:
                            matched = False
                            for ckvert in matches:
                                if lmuvlist[ckvert] == lmuv:
                                    matched = True
                                    v_indx = ckvert
                            if matched == False:
                            #Must be a new LMUV!
                                #duplicate this vert/uv
                                vlist[new_index] = vlist[rootindx]
                                #add its uv
                                uvlist[new_index] = uv
                                lmuvlist[new_index] = lmuv
                                #add this index to a list so we can find it later
                                dupverts[rootindx] += [new_index]
                                v_indx = new_index
                                new_index += 1
                        else:
                            #first time we've seen this.  Add it.
                            lmuvlist[v_indx] = lmuv
                        
                else:
                    uvlist[v_indx] = uv
                    dupverts[v_indx] += [v_indx]
                    if lmuvlist[v_indx] != []:
                        if lmuvlist[v_indx] != lmuv:
                        #Must be a new LMUV!
                            #duplicate this vert/uv
                            vlist[new_index] = vlist[v_indx]
                            #add its uv
                            uvlist[new_index] = uv
                            lmuvlist[new_index] = lmuv
                            #add this index to a list so we can find it later
                            dupverts[v_indx] += [new_index]
                            v_indx = new_index
                            new_index += 1
                        #else:  Do nothing, we're all good!
                    else:
                            #first time we've seen this.  Add it.
                            lmuvlist[v_indx] = lmuv
                    
                
            else:
                if uvlist[v_indx] != []:
                    rootindx = dupverts[v_indx][0]
                    matches = []
                    for ckvert in dupverts[v_indx]:
                        if uvlist[ckvert] == uv:
                            matches += [ckvert]
                    if len(matches) == 0:
                    #must be a new UV!
                        #duplicate existing vertex
                        vlist[new_index] = vlist[rootindx]
                        #add its new uv
                        uvlist[new_index] = uv
                        #add this index to a list so we can find it later
                        dupverts[rootindx] += [new_index]
                        v_indx = new_index
                        new_index += 1
                    else:
                        v_indx = min(matches)
                else:
                    uvlist[v_indx] = uv
                    dupverts[v_indx] += [v_indx]
                
            index_list += [v_indx]
            
    #re-key to remove gaps from any dropped/invalid verts
    indexlookup = {}
    newindex = 0
    tempindexlist=[]
    vkeys = vlist.keys()
    vkeys.sort()
    for k in vkeys:
        indexlookup[k]=newindex
        newindex += 1
        
    #reindex index_list
    for i in index_list:
        tempindexlist.append(indexlookup[i])
    index_list = tempindexlist[:]
    
    # ********** write face count **************  
    faces = len(index_list)/3
    stream.write(struct.pack("L", faces))
    # ********** write vertex count ************
    stream.write(struct.pack("L", len(vlist)))
    # ************ write mesh flags ************
    stream.write(struct.pack("BBBB", meshflags1, meshflags2, bone_per_vertex, unkflag))
    if has_meshid:
        stream.write(struct.pack("LlL", indexid, vertexid, skeletonid))

    # ************** write ranges *************
    stream.write(struct.pack("f", xr.min))
    stream.write(struct.pack("f", yr.min))
    stream.write(struct.pack("f", zr.min))
    stream.write(struct.pack("f", xr.max))
    stream.write(struct.pack("f", yr.max))
    stream.write(struct.pack("f", zr.max))
    stream.write(struct.pack("f", txr.min))
    stream.write(struct.pack("f", 1 - tyr.min))
    stream.write(struct.pack("f", txr.max))
    stream.write(struct.pack("f", 1 - tyr.max))
    # ************ write lmap range *************
    stream.write(struct.pack("f", lmxr.min))
    stream.write(struct.pack("f", 1 - lmyr.min))
    stream.write(struct.pack("f", lmxr.max))
    stream.write(struct.pack("f", 1 - lmyr.max))
    # *********** write neckdata count **********
    if has_neckconnect:
        ncpos = stream.tell()
        stream.write(struct.pack("L",neckconnect_count))

    # ****** write face list*******
    for tri in index_list:
        stream.write(struct.pack("H", tri))

    if faces & 1:
        stream.write("\x00\x00")
        
    # ********** write vertices **************
    vkeys = vlist.keys()
    vkeys.sort()
    for k in vkeys:
        v = vlist[k]
        stream.write(struct.pack("HHHHHH", v[0], v[1], v[2], v[3], v[4], v[5]))
        #write uv
        stream.write(struct.pack("HH", uvlist[k][0], uvlist[k][1]))

    # Lightmap UVs
    if has_lightmap:
        for k in vkeys:
            stream.write(struct.pack("HH", lmuvlist[k][0], lmuvlist[k][1]))
            
    if is_boned:
        mobj.activeUVLayer = 'UVTex'
        # build vert weight list
        weights = {}
        for i,dup in dupverts.items():
            for dv in dup:
                weights[dv] = mobj.getVertexInfluences(i)
                
        # ********** write bone weights **************
        # w0,w1,w2,w3, b0,b1,b2,b3
        for k in vkeys:
            # fetch the bone/weight pair
            vinf = weights[k]
            bw_pair = filter(lambda x: x[0] !='neckconnect', vinf)
            bw_pair.sort(key=lambda x:-x[1])
            bonesort = []
            for bw in bw_pair:
                boneref = bone_lookup.index(bw[0])
                bonesort.append([bw[1], boneref, bw[0]])
            bonesort.sort(lambda x,y: cmp(float(y[0]),float(x[0])) or cmp(y[1],x[1]))

            for bw_cnt in range(4):
                if len(bw_pair) > bw_cnt:
                    stream.write(struct.pack("f", bonesort[bw_cnt][0]))
                else:
                    stream.write(struct.pack("f", 0))
                    
            for bw_cnt in range(4):
                if len(bw_pair) > bw_cnt:
                    last_bone = bonesort[bw_cnt][1]
                stream.write(struct.pack("b", last_bone))  
                
    # write Neck Data
    if has_neckconnect:
        if neckconnect_count > 0:
            if mshType == "FemaleCostume":
                neckpts = tmConst.NECK_FEMALE
            elif mshType == "MaleCostume":
                neckpts = tmConst.NECK_MALE
            else:
                print "WARNING: mshType is not set to either \'FemaleCostume\' or \'MaleCostume\' -- defaulting to Male neckpoints."
                neckpts = tmConst.NECK_MALE
            npts = {}
            for n in mobj.getVertsFromGroup('neckconnect'):
                root = dupverts[n][0]
                for pt in dupverts[n]:
                    npts[pt] = getNeckIndex(mobj.verts[root].co, neckpts)
            #backpatch neckpoints count
            cpos = stream.tell()
            stream.seek(ncpos)
            stream.write(struct.pack("L",len(npts)))
            stream.seek(cpos)
            #write it!
            for pt,co in npts.items():
                stream.write(struct.pack("LL", pt, co))

def write_armature(stream):
    if has_bones:
        a = Armature.Get("Bones")
        #bonelist = a.bones.values() -- USE remapped list
        if (len(bone_list)):
            #write_null("L", stream)
            #Skeleton ID
            stream.write(struct.pack("L", rigID))
            stream.write(struct.pack("L", len(bone_list)))
              
            #bp_lookup = []
            for bone in bone_list:
                #bp_lookup.append(bone.name)
                boneparent = -1
                if bone.parent:
                    boneparent = bone_lookup.index(bone.parent.name)
                write_bone(stream, bone, boneparent)


def write_bone(stream, bone, boneparent):
    write_nts(bone.name, stream)
    stream.write(struct.pack("l", boneparent))

    bone_matrix = bone.matrix["ARMATURESPACE"]

    stream.write(struct.pack("fff", bone_matrix[1][0], bone_matrix[1][1], bone_matrix[1][2]))
    stream.write(struct.pack("fff", bone_matrix[2][0], bone_matrix[2][1], bone_matrix[2][2]))
    stream.write(struct.pack("fff", bone_matrix[0][0], bone_matrix[0][1], bone_matrix[0][2]))
    stream.write(struct.pack("fff", bone_matrix[3][0], bone_matrix[3][1], bone_matrix[3][2]))
            
            
def write_anchor(anchor, stream):
    try: 
        ancname = anchor.properties['TheMovies']['ancName']
    except:
        ancname = "anchor"
        print "FAIL: No anchor name property given. Using \'anchor\'"
    write_nts(ancname, stream)
    anc_matrix = anchor.matrixWorld
    
    stream.write(struct.pack("fff", anc_matrix[0][0], anc_matrix[0][1], anc_matrix[0][2]))
    stream.write(struct.pack("fff", anc_matrix[1][0], anc_matrix[1][1], anc_matrix[1][2]))
    stream.write(struct.pack("fff", anc_matrix[2][0], anc_matrix[2][1], anc_matrix[2][2]))
    stream.write(struct.pack("fff", anc_matrix[3][0], anc_matrix[3][1], anc_matrix[3][2]))
    
def write_shape(shape, stream):
    stream.write(struct.pack("L",0))
    sh_matrix = shape.matrixWorld
    stream.write(struct.pack("fff", sh_matrix[0][0], sh_matrix[0][1], sh_matrix[0][2]))
    stream.write(struct.pack("fff", sh_matrix[1][0], sh_matrix[1][1], sh_matrix[1][2]))
    stream.write(struct.pack("fff", sh_matrix[2][0], sh_matrix[2][1], sh_matrix[2][2]))
    stream.write(struct.pack("fff", sh_matrix[3][0], sh_matrix[3][1], sh_matrix[3][2]))
    
    bb = calc_bbox(shape.getBoundBox(1))
    
    Sizex = (0 - bb[0]) + bb[1]
    Sizey = (0 - bb[2]) + bb[3]
    Sizez = (0 - bb[4]) + bb[5]
    
    stream.write(struct.pack("fff", Sizex, Sizey, Sizez))
    
#***********************************************
# main export function
#***********************************************

def save_msh(filename):
    '''This is what writes to the msh file, or at least defines the order.
    '''
    
    global material_list, material_keys, Bounds, mshType, bone_list, bone_lookup, rigID, has_bones
    global clickable, min_outline, z_height, lot_boundary, neg_space, shadow, collision
   
    time1 = Blender.sys.time()  #for timing purposes
    prev_time = time1

    #Get Scene ID Properties
    scn = Blender.Scene.GetCurrent()
    Bounds = [0,0,0,0,0,0] 
    mshflags1 = 0
    mshflags2 = 0 
    has_named_groups = 0
    has_static_anim = 0
    has_childmesh = 0
    has_rooms = 0
    has_shapes = 0 
    if scn.properties.has_key('TheMovies'):
        mshName = scn.properties['TheMovies']['mshName']
        mshType = scn.properties['TheMovies']['mshType']
        mshflags1 |= ((scn.properties['TheMovies']['hide_actor_head'] % 2) * 8)
        mshflags1 |= ((scn.properties['TheMovies']['hide_actor_hair'] % 2) * 16)
        mshflags1 |= ((scn.properties['TheMovies']['is_auto_animated'] % 2) * 32)
        mshflags1 |= ((scn.properties['TheMovies']['tex_replace_mode'] % 2) * 64)
        has_static_anim = scn.properties['TheMovies']['has_static_anim'] % 2
        has_shapes = scn.properties['TheMovies']['has_shapes'] % 2
        has_childmesh = scn.properties['TheMovies']['has_childmesh'] % 2
        has_rooms = scn.properties['TheMovies']['has_rooms'] % 2
    else: 
        mshName = "p_export.msh"
        mshType = "Undefined"
        
    image_list = []
    for i in Image.Get():
       image_list.append(i.getFilename()) # probably need to eliminate textures not referenced in Materials...

    clickable = None
    min_outline = None
    z_height = None
    lot_boundary = None
    neg_space = None
    shadow = None
    collision = None
    
    group_names = []
    group_values = []
    group_orderkeys=[]
    anchor_list = []
    shape_list = []
    room_list = {}
    bone_list = []
    bone_lookup = []
    
    # Groups
    rigID = 0
##    bbox_all=[]
    #sort group order keys
    for g in Blender.Group.Get()[:]:
        group_orderkeys.append(g.name)
    group_orderkeys.sort()
    
    for g in group_orderkeys:
        gr = Blender.Group.Get(g)
        if gr.name == 'control_meshes':
            for m in gr.objects:
                if m.getType() == "Mesh":
                    n = m.name
                    Bounds = adjustBounds(m)
                    if n == "clickable":
                        clickable = m
                    elif n == "collision":
                        mshflags2 |= 16
                        collision = m
                    elif n == "shadow":
                        mshflags2 |= 8
                        shadow = m
                    elif n == "z_height":
                        mshflags1 |= 4
                        z_height = m
                    elif n == "neg_space":
                        mshflags2 |= 4
                        neg_space = m
                    elif n == "min_outline":
                        mshflags1 |= 2
                        min_outline = m
                    elif n == "lot_boundary":
                        mshflags2 |= 1
                        lot_boundary = m
        elif gr.name == 'rooms':
            for m in gr.objects:
                if m.getType() == "Mesh":
                    if m.properties.has_key('TheMovies'):
                        n = m.properties['TheMovies']['roomName']
                    else:
                        n = m.name
                    has_rooms = 1
                    Bounds = adjustBounds(m)
                    room_list[n] = m
        elif gr.name == 'shapes':
            for m in gr.objects:
                if m.getType() == "Mesh":
                    Bounds = adjustBounds(m)
                    has_shapes = 1
                    shape_list.append(m)
        elif gr.name == 'anchors':
            for o in gr.objects:
                if o.getType() == "Empty":
                    if o.name != "Anchors":
                        anchor_list.append(o)
                        Bounds = adjustBounds(o)
        else:
            emptyfound = False
            for o in gr.objects:
                if o.getType() == "Empty":
                    emptyfound = True
                    try:
                        grpname = o.properties['TheMovies']['grpName']
                    except:
                        #great.  Why are you trying to break this??  We'll try to adjust.
                        print "WARNING: No \'grpName\' ID Property found in Empty \'%s\'.  Using Empty name." % (o.name)
                        grpname = o.name.split('.',1)[-1]
                    Bounds = adjustBounds(o)
                if o.getType() == "Mesh":
                    mats = o.getData().getMaterials()
                    if mats:
                        mat = mats[0]
                        if mat.name not in material_keys:
                            material_list.append(mat)
                            material_keys.append(mat.name)
                    Bounds = adjustBounds(o)
                    
            if emptyfound == False:
                grpname = gr.name
                print "FAIL! (Blender Group \'%s\') Contains no Empty pivot!" % grpname
            if has_named_groups == 0:
                r = unnamed_group.match(grpname)
                if not r:
                    has_named_groups = 1
            if has_static_anim == 0 :
                r2 = static_anim_group.match(grpname)
                if r2:
                    has_static_anim = 1
                    
            #group_list[grpname] = gr.objects
            group_names.append(grpname)
            group_values.append(gr.objects)
##    bbox = calc_bbox(bbox_all)
    

    if Blender.Armature.Get() != {} :
        has_bones = 1
        bone_list = []
        
        for ob in scn.objects:
            if ob.type == 'Armature':
                arm = ob
                try:
                    rigID = int(ob.name)
                except:
                    try:
                        skt = ob.properties['TheMovies']['skeletonType']
                        for key in tmConst.RIG_IDS.keys():
                            value = tmConRIG_IDS[key]
                            if not index.has_key(value):
                                index[value] = key
                        try:
                            rigID = index[skt]
                            del(index)
                        except:
                            print "WARNING: skeletonType not recognized. Generating random Skeleton ID"
                            rigID = randint(0,4294967295)
                    except:
                        print "WARNING: skeletonType property missing. Generating random Skeleton ID"
                        rigID = randint(0,4294967295)
             
        if arm.properties.has_key('TheMovies'):
            if arm.properties['TheMovies'].has_key('BoneOrder'):
                bone_lookup = arm.properties['TheMovies']['BoneOrder'].values()
                for bname in bone_lookup:
                    b = Blender.Armature.Get("Bones").bones[bname]
                    bone_list.append(b)
        else:
            # Fallback .. Mesh hasn't got ordered Armature.  We'll give them a fighting chance...
            print "WARNING: Bone Order not found.  Proceeding to output in Undefined order.  Mesh could have issues."
            rootbone = Armature.Get("Bones").bones["root"]
            bonekeys = rootbone.getAllChildren()
            bonekeys.insert(0, rootbone)
            for bone in bonekeys:
                bone_list.append(bone)
            
            # Tarison discovered these rigs need the Headbone to be at the end of the bone list
            # we may need to add other exceptions, maybe for all 'costume' classed meshes too
            # remove headbone (and any children)
            if rigID == 507812352 or rigID == 1094395392 : 
                headstartbone = Armature.Get("Bones").bones["neck"] #get all bones attached to neck.. i.e. head and all childbones
                headchildren = headstartbone.getAllChildren()           
                for hc in headchildren:
                    bone_list.remove(hc)
                for hc in headchildren:
                    bone_list.append(hc)
            
            for bone in bone_list:
                bone_lookup.append(bone.name)
        
    else:
        has_bones = 0
        
    mshflags2 |= (has_shapes * 2)
    mshflags2 |= (has_childmesh * 64)
    mshflags2 |= (has_rooms * 128)
    childmesh_list = [] #never used?

    #*******************************************
    # write header
    #*******************************************
    stream = open(filename, 'wb')
    stream.write(struct.pack("L",10))
    
    # image count 
    stream.write(struct.pack("L", len(image_list)))
    # material count 
    stream.write(struct.pack("L", len(material_keys)))
    # group count 
    stream.write(struct.pack("L",len(group_values)))
    # has bones
    stream.write(struct.pack("B", has_bones))
    # static anims
    stream.write(struct.pack("B", has_static_anim))
    # anchor count
    stream.write(struct.pack("B", len(anchor_list)))
    # clickable mesh
    if clickable is not None:
        stream.write("\x01")
    else:
        stream.write("\x00")
    #  has outline
    stream.write("\x00")
    # flags 1
    stream.write(struct.pack("B", mshflags1))
    # flags 2
    stream.write(struct.pack("B", mshflags2))
    # named groups
    stream.write(struct.pack("B", has_named_groups))
    # shape count
    if has_shapes:
        stream.write(struct.pack("L", len(shape_list)))
    # childmesh (?)
    if has_childmesh:
        stream.write(struct.pack("L", len(childmesh_list))) 
    # room count
    if has_rooms:
        stream.write(struct.pack("L", len(room_list)))
    # end header **************************
    print 'header written : %.4f sec.' % (Blender.sys.time()-prev_time)
    prev_time = Blender.sys.time()
    
    # image list
    for i in image_list:
        im = os.path.split(i)[1]
        write_nts(im, stream)
    print '%d images written : %.4f sec.' % (len(image_list), Blender.sys.time()-prev_time)
    prev_time = Blender.sys.time()
    
        
    # material list
    for mat in material_list:
        write_material(mat, stream)
    print '%d materials written : %.4f sec.' % (len(material_list), Blender.sys.time()-prev_time)
    prev_time = Blender.sys.time()

    # control meshes
    write_control_meshes(stream)
    print 'control_meshes written : %.4f sec.' % (Blender.sys.time()-prev_time)
    prev_time = Blender.sys.time()

    # rooms
    for n in room_list:
        write_nts(n, stream)
        write_basic_mesh(room_list[n], stream)
    print '%d rooms written : %.4f sec.' % (len(room_list), Blender.sys.time()-prev_time)
    prev_time = Blender.sys.time()

    # groups - mesh contents
    for g in group_values:
        write_group(g, stream)
        print 'group written : %.4f sec.' % (Blender.sys.time()-prev_time)
        prev_time = Blender.sys.time()
        

    # bones goes here
    write_armature(stream)
    print 'armatures written : %.4f sec.' % (Blender.sys.time()-prev_time)
    prev_time = Blender.sys.time()

    # group names
    for g in group_names:
        write_nts(g, stream)
    print '%d group_names written : %.4f sec.' % (len(group_names), Blender.sys.time()-prev_time)
    prev_time = Blender.sys.time()
    
    # Anchors
    for a in anchor_list:
        write_anchor(a, stream)
    print '%d anchors written : %.4f sec.' % (len(anchor_list), Blender.sys.time()-prev_time)
    prev_time = Blender.sys.time()
    
    # Convex Hull (We're skipping this piece of crap section for now!)
    
    # Shapes
    # not sure what they're for, but we can write them!
    for s in shape_list:
        write_shape(s, stream)
    print '%d shapes written : %.4f sec.' % (len(shape_list), Blender.sys.time()-prev_time)
    prev_time = Blender.sys.time()
        
    stream.close()

    print 'finished exporting: "%s" in %.4f sec.' % (filename, (Blender.sys.time()-time1))

#***********************************************
# register callback
#***********************************************
def my_callback(filename):
    save_msh(filename)

Blender.Window.FileSelector(my_callback, "Export MSH", '*.msh')
