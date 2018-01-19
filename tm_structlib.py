
__author__ = ["Nick Hudson"]
__url__    = ("http://dcmodding.com/main")
__version__ = "0.01"
__pydoc__ = """\

"""

import Blender

from Blender import Mesh, NMesh
from Blender import Image, Material, Armature
from Blender.Mathutils import Matrix, Vector
import struct, os, math

"""
"""

class TMMesh:
	name=""

	def __init__(self):
		self.name=""

	def setObjectName(self, name):
		self.name = name

	def getObjectName(self):
		return self.name

	def setBlockName(self, name):
		self.name = name

	def getBlockName(self):
		return self.name

	def readFromFile(self, struct_type):
		value = struct.unpack(struct_type, 
			self.filestream.read(struct.calcsize(struct_type)))
		if len(value) == 1:
			value = value[0]
		return value

	def loadFromFile(self, fileinfo):
		# initialise
		#-----------
		self.filename = fileinfo.getFilename()
		self.filestream = open(self.filename,"rb")
		self.name = self.filename

		scene = Blender.Scene.GetCurrent()

		self.header_init = self.readFromFile("L")

	def saveToBlender(self):
		self.printTMMesh()

	def saveToFile(self, filename):
		self.printTMMesh()

	def loadFromBlender(self):
		self.data = ""

	def printTMMesh(self):
		print self.filename
		print self.header_init

