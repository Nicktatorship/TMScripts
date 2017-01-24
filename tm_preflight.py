#!BPY

"""
Name: 'The Movies Preflight Check'
Blender: 246
Group: 'Misc'
Tooltip: 'Prepares data for export to The Movies format (.msh)'
"""

__author__ = ["Glen Rickey"]
__url__ = ("Director's Cut Modding Foundry","http://www.dcmodding.com")
__version__ = "1.03 04-05-2009"
__bpydoc__ = """\

Msh Preflight Check

This script imports a msh file from Lionhead Studio Limited's The Movies
into blender for editing. It is not supported by either Lionhead or
Activision.

"""

# ***** BEGIN GPL LICENSE BLOCK *****
#
# Script copyright (C) Glen S. Rickey
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
##from Blender import Image, Material, Texture, Window, Armature
##from Blender import Mesh, NMesh, Group
##from Blender.Mathutils import Matrix, Vector, LineIntersect, DotVecs, AngleBetweenVecs, TranslationMatrix
##import struct
import os
import re
import tmConst
#These may be too exotic for standard Blender installs, requires full Python
import webbrowser
import unittest
#requires addition to Python Lib
import TM_HTMLTestRunner


# Define Tests
#Generic Types
def contains_check(has,list,msg):
    def test(self):
        self.assertTrue(has in list,msg)
    return test   

def truth_check(a,b,msg):
    def test(self):
        self.assertTrue(a==b,msg)
    return test 

def untruth_check(a,b,msg):
    def test(self):
        self.assertFalse(a==b,msg)
    return test 

#Groups Tests
def InGroupTest():
    grp_tests = {}   
    groups = Blender.Group.Get()
    objects = filter(lambda x: x.getType() not in  ['Camera', 'Lamp', 'Armature'], Blender.Object.Get()[:])
    all_group_obs=[]
    for gr in groups:
        for o in gr.objects:
            all_group_obs.append(o)
    for obj in objects:
        test_name = 'test_%s_Group' % (obj.name)
        test = contains_check(obj, all_group_obs, "%s \'%s\' is not in a Blender Group.  Add it to a group." % (obj.getType(), obj.name))
        grp_tests[test_name]=test
    testcase = type('InGroupTest: Each Blender Object is in a Blender Group.',(unittest.TestCase,), grp_tests)
    return testcase

def MultiGroupTest():
    grp_tests = {}   
    groups = Blender.Group.Get()      
    all_group_obs=[]
    for gr in groups:
        for o in gr.objects:
            all_group_obs.append(o)
    uniques = set(item for item in all_group_obs)
    check = [(item, all_group_obs.count(item)) for item in uniques]
    for obj,obcount in check:
        test_name = 'test_%s_Groups' % (obj.name)
        test = truth_check(obcount,1,"%s \'%s\' is in multiple Blender Groups.  There should only be in one." % (obj.getType(), obj.name))
        grp_tests[test_name]=test
    testcase = type('MultiGroupTest: Each Blender Object is in only ONE Blender Group.',(unittest.TestCase,), grp_tests)
    return testcase

def GroupHasEmptyTest():
    grp_tests = {}   
    groups = filter(lambda x: x.name not in [ "anchors","control_meshes","shapes", "rooms"], Blender.Group.Get()[:])
    popgrps = filter(lambda x: x.objects > 0 , groups)
    for gr in popgrps:
        typelist = []   
        for o in gr.objects:
            typelist.append(o.getType())
        test_name = 'test_%s_Pivot' % (gr.name)
        test = contains_check("Empty",typelist,"Group \'%s\' contains no Empty object.  Add one if this Group is to be exported." % (gr.name))
        grp_tests[test_name]=test
    testcase = type('GroupHasEmptyTest: Each populated Blender Group has an Empty pivot object.',(unittest.TestCase,), grp_tests)
    return testcase

def GroupHasOrderNumberTest():
    grp_tests = {}
    numbered_grp = re.compile(r"(\d{2})(\.\d+)?")
    groups = filter(lambda x: x.name not in [ "anchors","control_meshes","shapes", "rooms"], Blender.Group.Get()[:])
    for gr in groups:
        test_name = 'test_%s_GroupNum' % (gr.name)
        test = untruth_check(numbered_grp.match(gr.name),None,"Group \'%s\' has no digits preceeding the name to signify Group export order. Name it 00.Group1, 01.Group2, etc." % (gr.name))
        grp_tests[test_name]=test
    testcase = type('GroupHasOrderNumberTest: Each Group has a number in the name, determining export order.',(unittest.TestCase,), grp_tests)
    return testcase

def GroupParentNameTest():
    grp_tests = {}   
    groups = filter(lambda x: x.name not in [ "anchors","control_meshes","shapes", "rooms"], Blender.Group.Get()[:])
    for gr in groups[:]:
        for obj in gr.objects:
            if obj.getType()=="Empty":
                test_name = 'test_%s_Group-Parent' % (obj.name)
                test = truth_check(obj.name, gr.name, "Empty pivot \'%s\' is named differently than Blender Group %s.  They should be the same." % (obj.name, gr.name))
                grp_tests[test_name]=test
    testcase = type('Group-ParentName: The name of the Group and the parent Empty are the same.',(unittest.TestCase,), grp_tests)
    return testcase


def GroupPropertyNameTest():
    grp_tests = {}   
    groups = filter(lambda x: x.name not in [ "anchors","control_meshes","shapes", "rooms"], Blender.Group.Get()[:])
    for gr in groups[:]:
        for obj in gr.objects:
            if obj.getType()=="Empty":
                if obj.properties.has_key('TheMovies')==True:
                    if obj.properties['TheMovies'].has_key('grpName')==True:
                        grpname = obj.properties['TheMovies']['grpName']
                        test_name = 'test_%s_Group_Property' % (gr.name)
                        test = truth_check(gr.name.split('.',1)[-1], grpname[0:18], "Object %s ID Property 'grpName' is different (%s) than Blender Group name %s.  They should be the same." % (obj.name, grpname, gr.name))
                        grp_tests[test_name]=test
    testcase = type('Group-PropertyName: The name of the Group and the IDProperty \'grpName\' value are the same.',(unittest.TestCase,), grp_tests)
    return testcase

def GroupHierarchyTest():
    grp_tests = {}   
    groups = Blender.Group.Get()[:] 
    for gr in groups[:]:
        for obj in gr.objects:
            if obj.getType()=="Mesh":
                parent = obj.getParent()
                if parent != None:
                    if parent.getType()=='Empty' or parent.getType()=='Armature':
                        #check if there is an armature here.  If mesh has weights and is not parented to armature, consider it a fail...
                        if Blender.Armature.Get()!={}:
                            if 'Bones' in Blender.Armature.Get():
                                arm = Blender.Armature.Get('Bones')
                                msh = obj.getData(0,1)
                                if len(msh.getVertGroupNames())>0:
                                    test_name = 'test_%s_Armature' % (obj.name)
                                    test = truth_check(parent.getType(),"Armature", "Mesh %s has Vertex Groups, but is not parented to Armature.  It is now parented to %s.  It should be Armature %s." % (obj.name, parent.name, arm.name))
                                    grp_tests[test_name]=test
                        else:
                            test_name = 'test_%s_WrongParent' % (obj.name)
                            test = truth_check(parent.getType(),"Empty", "Mesh %s is not parented to an Empty.  It should be." % (obj.name))
                            grp_tests[test_name]=test
                else:
                    test_name = 'test_%s_Orphan' % (obj.name)
                    test = untruth_check(parent,None, "Object %s is not parented to anything.  It should be." % (obj.name))
                    grp_tests[test_name]=test
    testcase = type('GroupHeirarchyTest: Meshes must be children of an Empty or an Armature.',(unittest.TestCase,), grp_tests)
    return testcase

def BoneVertexGroupNameTest():
    grp_tests = {}   
    groups = Blender.Group.Get()[:] 
    for gr in groups[:]:
        for obj in gr.objects:
            if obj.getType()=="Mesh":
                parent = obj.getParent()
                if parent != None:
                    if parent.getType()=='Empty' or parent.getType()=='Armature':
                        #check if there is an armature here.  If mesh has weights and is not parented to armature, consider it a fail...
                        if Blender.Armature.Get()!={}:
                            if 'Bones' in Blender.Armature.Get():
                                arm = Blender.Armature.Get('Bones')
                                msh = obj.getData(0,1)
                                if len(msh.getVertGroupNames())>0:
                                    #filter out neckconnect, if we've got one.  It's the only non-match allowed.
                                    vertgrps = filter(lambda x: x!='neckconnect', msh.getVertGroupNames())
                                    unmatched = filter(lambda x: x not in arm.bones.keys(), vertgrps)
                                    test_name = 'test_%s_VertGrpName' % (obj.name)
                                    test = truth_check(len(unmatched),0, "Mesh %s has these Vertex Groups %s that do not match any Bone names.  Each Vertex Group must have a Bone with the same name." % (obj.name, unmatched))
                                    grp_tests[test_name]=test
    testcase = type('BoneVertexGroupName: Vertex Groups must match Bone names.',(unittest.TestCase,), grp_tests)
    return testcase

def ParentPropertyNameTest():
    grp_tests = {}   
    groups = filter(lambda x: x.name not in [ "anchors","control_meshes","shapes", "rooms"], Blender.Group.Get()[:])
    for gr in groups[:]:
        for obj in gr.objects:
            if obj.getType()=="Empty":
                if obj.properties.has_key('TheMovies')==True:
                    if obj.properties['TheMovies'].has_key('grpName')==True:
                        grpname = obj.properties['TheMovies']['grpName']
                        test_name = 'test_%s_Parent-Property' % (obj.name)
                        test = truth_check(obj.name.split('.',1)[-1], grpname[0:18], "Empty \'%s\' ID Property 'grpName' is different than Blender Group name %s.  They should be the same." % (obj.name, grpname))
                        grp_tests[test_name]=test
    testcase = type('Parent-PropertyName: The IDProperty \'grpName\' and the name of the Empty are the same.',(unittest.TestCase,), grp_tests)
    return testcase

def MaterialZeroTest():
    grp_tests = {}
    groups = filter(lambda x: x.name not in [ "anchors","control_meshes","shapes", "rooms"], Blender.Group.Get()[:])
    for gr in groups:
        for obj in gr.objects:
            if obj.getType()=="Mesh":
                msh = obj.getData(0,1)
                if len(msh.materials)> 0 :
                    mat = msh.materials[0]
                    test_name = 'test_%s_Mat0' % (mat.name)
                    test = untruth_check(mat,None,"Mesh \'%s\' has no material in the first slot.  Add a material to this mesh." % (obj.name))
                    grp_tests[test_name]=test
                else:
                    test_name = 'test_%s_Mat0' % (mat.name)
                    test = truth_check(0,1,"Mesh \'%s\' has no material.  Add a material to this mesh." % (obj.name))
                    grp_tests[test_name]=test
    testcase = type('MaterialZeroTest: Each Grouped Mesh has a material in the first slot.',(unittest.TestCase,), grp_tests)
    return testcase


def MaterialTypeTest():
    grp_tests = {}
    groups = filter(lambda x: x.name not in [ "anchors","control_meshes","shapes", "rooms"], Blender.Group.Get()[:])
    for gr in groups:
        for obj in gr.objects:
            if obj.getType()=="Mesh":
                msh = obj.getData(0,1)
                if len(msh.materials)>0:
                    mat = msh.materials[0]
                    for i in range(4):
                        if mat.textures[i] != None:
                            if mat.textures[i].tex != None:
                                if mat.textures[i].tex.getType() != 'None':
                                    tex = mat.textures[i].tex
                                    test_name = 'test_%s_MatType' % (tex.name)
                                    test = truth_check(tex.getType(),'Image',"Texture \'%s\' type is not an Image.  Only <b>Image</b> texture types can be exported, not \'%s.\'" % (tex.name, tex.getType()))
                                    grp_tests[test_name]=test
    testcase = type('MaterialTypeTest: Textures in Materials must be Images.',(unittest.TestCase,), grp_tests)
    return testcase

def UnusedMaterialsTest():
    grp_tests = {}
    groups = filter(lambda x: x.name not in [ "anchors","control_meshes","shapes", "rooms"], Blender.Group.Get()[:])
    matlist = []
    for gr in groups:
        for obj in gr.objects:
            if obj.getType()=="Mesh":
                msh = obj.getData(0,1)
                if len(msh.materials)>0:
                    m = msh.materials[0]
                    matlist.append(m)
    for mat in Blender.Material.Get():
            test_name = 'test_%s_UnusedMat' % (mat.name)
            test = contains_check(mat,matlist,"Material \'%s\' is not used by any Meshes.  Remove it for a smaller file." % (mat.name))
            grp_tests[test_name]=test
    testcase = type('UnusedMaterialsTest: Checks for unused Materials.',(unittest.TestCase,), grp_tests)
    return testcase

def UnusedTexturesTest():
    grp_tests = {}
    groups = filter(lambda x: x.name not in [ "anchors","control_meshes","shapes", "rooms"], Blender.Group.Get()[:])
    texlist = []
    for gr in groups:
        for obj in gr.objects:
            if obj.getType()=="Mesh":
                msh = obj.getData(0,1)
                if len(msh.materials)>0:
                    mat = msh.materials[0]
                    for i in range(4):
                        if mat.getTextures()[i] != None:
                            t = mat.getTextures()[i].tex
                            texlist.append(t)
    for tex in Blender.Texture.Get():
            test_name = 'test_%s_UnusedTex' % (tex.name)
            test = contains_check(tex,texlist,"Texture \'%s\' is not used in any Materials.  Remove it for a smaller file." % (tex.name))
            grp_tests[test_name]=test
    testcase = type('UnusedTexturesTest: Checks for unused Textures.',(unittest.TestCase,), grp_tests)
    return testcase

def UnusedImagesTest():
    grp_tests = {}
    groups = filter(lambda x: x.name not in [ "anchors","control_meshes","shapes", "rooms"], Blender.Group.Get()[:])
    imglist = []
    for gr in groups:
        for obj in gr.objects:
            if obj.getType()=="Mesh":
                msh = obj.getData(0,1)
                if len(msh.materials) > 0:
                    mat = msh.materials[0]
                    for i in range(4):
                        if mat.getTextures()[i] != None:
                            img = mat.getTextures()[i].tex.getImage()
                            if img != None:
                                imglist.append(img)
    for img in Blender.Image.Get():
            test_name = 'test_%s_UnusedImg' % (img.name)
            test = contains_check(img,imglist,"Image \'%s\' is not used in any Textures.  Remove it for a smaller file." % (img.name))
            grp_tests[test_name]=test
    testcase = type('UnusedImagesTest: Checks for unused Images.',(unittest.TestCase,), grp_tests)
    return testcase

def UVLayerNameTest():
    grp_tests = {}
    groups = filter(lambda x: x.name not in [ "anchors","control_meshes","shapes", "rooms"], Blender.Group.Get()[:])
    for gr in groups:
        for obj in gr.objects:
            if obj.getType()=="Mesh":
                msh = obj.getData(0,1)
                uvnames = msh.getUVLayerNames()
                test_name = 'test_%s_UVTex' % (obj.name)
                test = contains_check('UVTex',uvnames,"UV Layer 'UVTex' not found in Mesh %s." % (msh.name))
                grp_tests[test_name]=test
                if len(uvnames)>1:
                    test_name = 'test_%s_LightMap' % (obj.name)
                    test = contains_check('LightMap',uvnames,"UV Layer 'LightMap' not found in Mesh %s." % (msh.name))
                    grp_tests[test_name]=test
    testcase = type('UVLayerNameTest: UV Layers must be named \'UVTex\' or \'LightMap\'.',(unittest.TestCase,), grp_tests)
    return testcase

def UVTest():
    grp_tests = {}
    groups = filter(lambda x: x.name not in [ "anchors","control_meshes","shapes", "rooms"], Blender.Group.Get()[:])
    for gr in groups:
        for obj in gr.objects:
            if obj.getType()=="Mesh":
                msh = obj.getData(0,1)
                test_name = 'test_%s_HasUV' % (obj.name)
                test = truth_check(msh.faceUV,True,"Mesh %s has no UV-mapped faces." % (msh.name))
                grp_tests[test_name]=test
    testcase = type('UVTest: Meshes must have UV mapping.',(unittest.TestCase,), grp_tests)
    return testcase

def ControlMeshNamesTest():
    grp_tests = {}
    ctrl = filter(lambda x: x.name == 'control_meshes', Blender.Group.Get()[:])
    if len(ctrl) > 0:
        names = ["clickable", "collision", "shadow", "z_height", "neg_space", "min_outline", "lot_boundary"]
        #roomck = re.compile(r'(.+)\.room\_')
        for obj in ctrl[-1].objects:
            if obj.getType()=="Mesh":
                test_name = 'test_%s_controls' % (obj.name)
                test = contains_check(obj.name,names,"Control Mesh \'%s\' is not a recognized name.  Expecting one of the following: clickable, collision, shadow, z_height, neg_space, min_outline, lot_boundary." % (obj.name))
                grp_tests[test_name]=test
        testcase = type('ControlMeshNamesTest: Checks control meshes for proper names.',(unittest.TestCase,), grp_tests)
        return testcase
    else:
        return unittest.TestCase

def AnchorsEmptyOnlyTest():
    grp_tests = {}
    anc= filter(lambda x: x.name == 'anchors', Blender.Group.Get()[:])
    if len(anc) > 0 :
        for obj in anc[-1].objects:
            test_name = 'test_%s_AnchorEmpty' % (obj.name)
            test = truth_check(obj.getType(),"Empty","Object \'%s\' is not a Blender Empty.  Anchors group can ONLY contain Blender Empty objects. Remove this object." % (obj.name))
            grp_tests[test_name]=test
        testcase = type('AnchorsEmptyOnlyTest: Checks anchor group for Blender Empty objects.',(unittest.TestCase,), grp_tests)
        return testcase
    else:
        return unittest.TestCase

def AnchorsIDPropertyTest():
    grp_tests = {}
    anc = filter(lambda x: x.name == 'anchors', Blender.Group.Get()[:])
    if len(anc) > 0:
        for obj in anc[-1].objects:
            if obj.properties.has_key('TheMovies')==True:
                if obj.properties['TheMovies'].has_key('ancName'):
                    anc = obj.properties['TheMovies']['ancName']
                    test_name = 'test_%s_AnchorIDProp' % (obj.name)
                    test = untruth_check(anc,None,"Object \'%s\' hasn't got an '\ancName\' ID Property. It requires one." % (obj.name))
                    grp_tests[test_name]=test
        testcase = type('AnchorsIDPropertyTest: Checks anchor Empty for \'ancName\' IDProperty.',(unittest.TestCase,), grp_tests)
        return testcase
    else:
        return unittest.TestCase

def RoomsIDPropertyTest():
    grp_tests = {}
    rooms = filter(lambda x: x.name == 'rooms', Blender.Group.Get()[:])
    if len(rooms) > 0:
        for obj in rooms[-1].objects:
            if obj.properties.has_key('TheMovies')==True:
                if obj.properties['TheMovies'].has_key('roomName'):
                    room = obj.properties['TheMovies']['roomName']
                    test_name = 'test_%s_RoomIDProp' % (obj.name)
                    test = untruth_check(room,'',"Object \'%s\' hasn't got a '\roomName\' ID Property. It requires one." % (obj.name))
                    grp_tests[test_name]=test
        testcase = type('RoomsIDPropertyTest: Checks anchor Empty for \'roomName\' IDProperty.',(unittest.TestCase,), grp_tests)
        return testcase
    else:
        return unittest.TestCase

def NonFaceVertsTest():
    grp_tests = {}
    groups = filter(lambda x: x.name not in [ "anchors","control_meshes","shapes", "rooms"], Blender.Group.Get()[:])
    for gr in groups:
        for obj in gr.objects:
            if obj.getType()=="Mesh":
                validverts = []
                msh = obj.getData(0,1)
                for f in msh.faces:
                    for validvert in f.verts:
                        if validvert not in validverts:
                            validverts.append(validvert)
                test_name = 'test_%s_BadVert' % (msh.name)
                test = truth_check(set(msh.verts),set(validverts),"Mesh \'%s\' has vertexes that are not part of valid faces.  Find them and remove them." % (msh.name))
                grp_tests[test_name]=test
    testcase = type('NonFaceVertsTest: Checks for vertexes that are not in any faces.',(unittest.TestCase,), grp_tests)
    return testcase

def VertWeightTest():
    if Blender.Armature.Get()!={}:
        grp_tests = {}
        groups = filter(lambda x: x.name not in [ "anchors","control_meshes","shapes", "rooms"], Blender.Group.Get()[:])
        for gr in groups:
            for obj in gr.objects:
                if obj.getType()=="Mesh":
                    if obj.getParent() != None:
                        if obj.getParent().getType() == 'Armature':
                            msh = obj.getData(0,1)
                            for v in msh.verts:
                                mshvertinf = msh.getVertexInfluences(v.index)
                                test_name = 'test_%s_%s_NoWeights' % (msh.name, v.index)
                                test = untruth_check(mshvertinf,[],"Mesh \'%s\' has vertexes that have no weight assigned. Find them and weight them." % (msh.name))
                                grp_tests[test_name]=test
        testcase = type('VertWeightTest: Checks for vertexes that are not weighted to any Vertex Groups.',(unittest.TestCase,), grp_tests)
        return testcase
    else:
        return unittest.TestCase

class BasicTests(unittest.TestCase):
    """Verifies very basic requirements."""
    def test_HasGroups(self):
        """Scene should have at least one Group."""
        self.assertTrue(len(Blender.Group.Get())>0,"This mesh has no Blender Groups.")
    def test_HasMeshes(self):
        """Scene should have at least one Mesh."""
        self.assertTrue(len(Blender.Mesh.Get())>0,"This mesh has no Blender Meshes.")
    def test_HasMaterials(self):
        """Scene should have at least one Material."""
        self.assertTrue(len(Blender.Material.Get())>0,"This mesh has no Blender Materials.")
    def test_HasTextures(self):
        """Scene should have at least one Texture."""
        self.assertTrue(len(Blender.Texture.Get())>0,"This mesh has no Blender Textures.")

class ArmatureTests(unittest.TestCase):
    """Tests several aspects of any Armatures in this mesh."""
    if len(Blender.Armature.Get())>0:
        def test_HasOnlyOneArmature(self):
            """Scene should only have one Armature."""
            self.assertTrue(len(Blender.Armature.Get())==1,"This mesh has too many armatures.")
        def test_BonesName(self):
            """Armature should be named \'Bones.\'"""
            self.assertTrue("Bones" in Blender.Armature.Get().keys(),"This mesh has no Armature object named \'Bones\'.")
        def test_ArmatureID(self):
            """Armature Object name is a number."""
            for obj in Blender.Object.Get()[:]:
                if obj.getType()=='Armature':
                    self.assertTrue(obj.name.isdigit(),"Armature object name is not a number.  Name must be the SkeletonID of this bone rig.")
        def test_BoneOrderProperty(self):
            """Armature Object has \'BoneOrder\' property."""
            for obj in Blender.Object.Get()[:]:
                if obj.getType()=='Armature':
                    if obj.properties.has_key('TheMovies'):
                        self.assertTrue(obj.properties['TheMovies'].has_key('BoneOrder'),"Armature Object \'%s\' has no \'BoneOrder\' property defined.  Bones will export in an unspecified order." % (obj.name))
                    
            

class Test_Failer(unittest.TestCase):
    """This will always fail."""
    def test_fail(self):
        self.fail()

def TagProperties():
    """This adds any missing properties to scorrectly grouped meshes, empties, and materials"""
    grp_tests = {} 
    #Adds missing Scene properties
    scene = Blender.Scene.GetCurrent()
    if scene.properties.has_key('TheMovies')== False:
        scene.properties['TheMovies'] = {}
    for prop,val in tmConst.SCENE_DEFS.items():
        if scene.properties['TheMovies'].has_key(prop)==False:
            scene.properties['TheMovies'][prop] = val
            test_name = 'test_Scene_%s' % (prop)
            test = truth_check(0,0,"Scene: Added default property: %s" % (prop))
            grp_tests[test_name]=test     
    #Check for rooms group, add 'roomName' property
    rooms = filter(lambda x: x.name == 'rooms',Blender.Group.Get()[:])
    if len(rooms) > 0 :
        for rm in rooms[-1].objects:
            if rm.getType() == 'Mesh':
                if rm.properties.has_key('TheMovies') == False:
                    rm.properties['TheMovies']={}
                    if rm.properties['TheMovies'].has_key('roomName') == False:
                        rm.properties['TheMovies']['roomName'] = rm.name
                        test_name = 'test_%s_roomName' % (rm.name )
                        test = truth_check(0,0,"Room %s: Added default property: \'roomName\'" % (rm.name))
                        grp_tests[test_name]=test
    #Check for anchors group, add missing 'ancName' property from object name.  Could suffer from Blender Trim Disease :P
    anchors = filter(lambda x: x.name == 'anchors', Blender.Group.Get()[:])
    if len(anchors) > 0:
        for anc in anchors[-1].objects:
            if anc.getType() == 'Empty' and anc.name != 'Anchors':
                if anc.properties.has_key('TheMovies') == False:
                    anc.properties['TheMovies']={}
                    if anc.properties['TheMovies'].has_key('ancName') == False:
                        anc.properties['TheMovies']['ancName'] = anc.name
                        test_name = 'test_%s_ancName' % (anc.name)
                        test = truth_check(0,0,"Anchor %s: Added default property: \'ancName\'" % (anc.name))
                        grp_tests[test_name]=test
    groups = filter(lambda x: x.name not in [ "anchors","control_meshes","shapes", "rooms"], Blender.Group.Get()[:])
    for gr in groups:
        for obj in gr.objects:
            if obj.getType()=="Mesh":
                msh = obj.getData(0,1)
                if msh.properties.has_key('TheMovies') == False:
                    msh.properties['TheMovies']={}
                for prop,val in tmConst.MESH_DEFS.iteritems():
                    if msh.properties['TheMovies'].has_key(prop) == False:
                        msh.properties['TheMovies'][prop] = val
                        test_name = 'test_%s_%s' % (msh.name, prop)
                        test = truth_check(0,0,"Mesh %s: Added default property: %s" % (msh.name, prop))
                        grp_tests[test_name]=test
                if len(msh.materials)>0:
                    if msh.materials[0] != None:
                        mat = msh.materials[0] #we don't care if you've added more materials, dummy.  Only using the first one.
                        if mat.properties.has_key('TheMovies')==False:
                            mat.properties['TheMovies'] = {}
                        for prop,val in tmConst.MATERIAL_DEFS.items():
                            if mat.properties['TheMovies'].has_key(prop)==False:
                                mat.properties['TheMovies'][prop] = val
                                test_name = 'test_%s_%s' % (mat.name, prop)
                                test = truth_check(0,0,"Material %s: Added default property: %s" % (mat.name, prop))
                                grp_tests[test_name]=test
            if obj.getType() =="Empty":
                if obj.properties.has_key('TheMovies')==False:
                    obj.properties['TheMovies'] = {}
                for prop,val in tmConst.GROUP_DEFS.iteritems():
                    if obj.properties['TheMovies'].has_key(prop) == False:
                        obj.properties['TheMovies'][prop] = val
                        test_name = 'test_%s:%s' % (obj.name,prop)
                        test = truth_check(0,0,"Empty %s: Added default property: %s" % (obj.name, prop))
                        grp_tests[test_name]=test
                    if obj.properties['TheMovies'].has_key('grpName') == False:
                        obj.properties['TheMovies']['grpName'] = gr.name.split('.',1)[-1]
                        test_name = 'test_%s:grpName' % (obj.name)
                        test = truth_check(0,0,"Empty %s: Added default property: %s" % (obj.name, 'grpName'))
                        grp_tests[test_name]=test
    testcase = type('AddDefaultGroupIDProperties: Adds default Group ID Properties. ',(unittest.TestCase,), grp_tests)
    return testcase
                
#Set up report file
filename = 'msh_test_report.html'
datapath = Blender.Get('datadir')
fpath = datapath + "\\" + filename
fp = open(fpath,'wb')
#Set up Tests
testrun = TM_HTMLTestRunner.HTMLTestRunner(
    stream=fp, 
    verbosity = 4,
    title='The Movies MSH Export Preflight Tests',
    description='Results for checking validitiy and integrity of mesh to be exported to The Movies game format.'
    )

suite = unittest.TestSuite()
suite.addTests([
    unittest.defaultTestLoader.loadTestsFromTestCase(BasicTests),
    unittest.defaultTestLoader.loadTestsFromTestCase(ArmatureTests),
    unittest.defaultTestLoader.loadTestsFromTestCase(InGroupTest()),
    unittest.defaultTestLoader.loadTestsFromTestCase(MultiGroupTest()),
    unittest.defaultTestLoader.loadTestsFromTestCase(GroupHasEmptyTest()),
    unittest.defaultTestLoader.loadTestsFromTestCase(GroupHasOrderNumberTest()),
    unittest.defaultTestLoader.loadTestsFromTestCase(GroupParentNameTest()),
    unittest.defaultTestLoader.loadTestsFromTestCase(GroupPropertyNameTest()),
    unittest.defaultTestLoader.loadTestsFromTestCase(GroupHierarchyTest()),
    unittest.defaultTestLoader.loadTestsFromTestCase(BoneVertexGroupNameTest()),
    unittest.defaultTestLoader.loadTestsFromTestCase(ParentPropertyNameTest()),
    unittest.defaultTestLoader.loadTestsFromTestCase(MaterialZeroTest()),
    unittest.defaultTestLoader.loadTestsFromTestCase(MaterialTypeTest()),
    unittest.defaultTestLoader.loadTestsFromTestCase(UnusedMaterialsTest()),
    unittest.defaultTestLoader.loadTestsFromTestCase(UnusedTexturesTest()),
    unittest.defaultTestLoader.loadTestsFromTestCase(UnusedImagesTest()),
    unittest.defaultTestLoader.loadTestsFromTestCase(UVTest()),
    unittest.defaultTestLoader.loadTestsFromTestCase(UVLayerNameTest()),
    unittest.defaultTestLoader.loadTestsFromTestCase(ControlMeshNamesTest()),
    unittest.defaultTestLoader.loadTestsFromTestCase(AnchorsEmptyOnlyTest()),
    unittest.defaultTestLoader.loadTestsFromTestCase(AnchorsIDPropertyTest()),
    unittest.defaultTestLoader.loadTestsFromTestCase(RoomsIDPropertyTest()),
    unittest.defaultTestLoader.loadTestsFromTestCase(NonFaceVertsTest()),
    unittest.defaultTestLoader.loadTestsFromTestCase(VertWeightTest()),
    unittest.defaultTestLoader.loadTestsFromTestCase(TagProperties())
    ])
#Run tests!
testrun.run(suite)
fp.close()
#Display results
webbrowser.open(fpath)
