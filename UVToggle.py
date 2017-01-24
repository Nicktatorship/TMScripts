#!BPY

"""
Name: 'UVTexture Toggler'
Blender: 246
Group: 'Misc'
Tooltip: 'Toggles all meshes between their UV Textures'
"""

__author__ = ["Glen Rickey"]
__url__ = ("Director's Cut Modding Foundry","http://www.dcmodding.com")
__version__ = "1.00 11-22-2008"
__bpydoc__ = """\

UV Texture Toggler

This script will toggle all meshes between their UVTex and lightmap textures.

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

for m in Blender.Mesh.Get():
	if 'LightMap' in m.getUVLayerNames():
		if m.activeUVLayer == 'UVTex':
			m.activeUVLayer = 'LightMap'
		else:
			m.activeUVLayer = 'UVTex'
		m.update()
		