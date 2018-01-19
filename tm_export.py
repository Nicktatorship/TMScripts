#!BPY

"""
Name: 'AA The Movies Mesh (.msh)...'
Blender: 245
Group: 'Export'
Tooltip: 'Export MSH File for The Movies. (.msh)'
"""

__author__ = ["Nick Hudson"]
__url__ = ("http://dcmodding.com/main")
__version__ = "0.01"
__bpydoc__ = """\

"""

# Import modules

import Blender
from Blender import Image, Material, Texture, NMesh, Window, Armature
from Blender.Mathutils import Matrix, Vector
from random import getrandbits
import struct, os, re

from tm_structlib import TMMesh

def save_msh(filename):
    '''This is what writes to the msh file, or at least defines the order.
    '''
    start_time = Blender.sys.time()

	msh_file = TMMesh()
	msh_file.loadFromBlender()
	msh_file.saveToFile(filename)

    print 'finished exporting: "%s" in %.4f sec.' % (filename, (Blender.sys.time()-start_time))

def my_callback(filename):
    save_msh(filename)

Blender.Window.FileSelector(my_callback, "Export TM MESH", '*.msh')
