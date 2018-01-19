#!BPY

"""
Name: 'AA The Movies Mesh (.msh)...'
Blender: 245
Group: 'Import'
Tooltip: 'Import MSH File from The Movies. (.msh)'
"""

__author__ = ["Nick Hudson"]
__url__ = ("http://dcmodding.com/main")
__version__ = "0.01"
__bpydoc__ = """\

"""

# Import modules

import Blender
from Blender import Window
import struct, os, math

from tm_structlib import TMMesh

class Fileinfo(object):
	_filename = ''
	_filepath = ''
	_filebase = ''
	_basename = ''
	_basedir = ''
	_imagedir = ''

	def __init__(self):
		self._filename = ""

	def __init__(self, filename):
		self._filename = filename
		self.load_info()

	def load_info(self):
		self._filepath = os.path.dirname(self._filename)
		self._filebase = os.path.basename(self._filename)
		self._basename = os.path.splitext(self._filebase)[0]
		self._basedir = os.path.split(self._filepath)[0]
		self._imagedir = os.path.join(self._basedir, "textures")

	def getFilename(self):
		return self._filename

	def getFilepath(self):
		return self._filepath

	def getFilebase(self):
		return self._filebase

	def getBasename(self):
		return self._basename
			
	def getBasedir(self):
		return self._basedir
			
	def getImagedir(self):
		return self._imagedir
			

def load_msh (filename):
	''' load_msh :

	trigger the mesh file load in the tm_mesh class, so
	that we can get the file we are opening into the 
	proper format, and then trigger the tm_mesh->blender
	conversion.
	'''
	start_time = Blender.sys.time()
	print '>>'

	# If we are in edit mode, get out of it.
	#---------------------------------------
	in_editmode = Window.EditMode()
	if in_editmode:
		Window.EditMode(0)

	fileinfo = Fileinfo(filename)

	# Create the Mesh
	msh_file = TMMesh()
	msh_file.loadFromFile(fileinfo)
	msh_file.saveToBlender()

	# If we were in edit mode, resume
	#--------------------------------
	if in_editmode:
		Window.EditMode(1)

	print 'finished importing: "%s" in %.4f sec.' % (filename, (Blender.sys.time()-start_time))


def my_callback(filename):
	load_msh(filename)

Blender.Window.FileSelector(my_callback, "Import The Movies Mesh", '*.msh')
