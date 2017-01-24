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

__author__ = ["Glen Rickey"]
__url__ = ("Director's Cut Modding Foundry","http://www.dcmodding.com")
__version__ = "1.00 02-28-2008"

from Blender.Mathutils import Vector
# ID Properties and default values

SCENE_DEFS = {          'mshName': 'Export',
                        'mshType': 'Undefined',
                        'hide_actor_head': 0,
                        'hide_actor_hair': 0,
                        'is_auto_animated': 0,
                        'tex_replace_mode': 0,
                        'has_static_anim': 0,
                        'has_shapes': 1,
                        'has_childmesh': 1,
                        'has_rooms': 1}
                                
MESH_DEFS = {           'has_floor_reflections': 0,
                        'no_outline': 0,
                        'is_landscape': 0,
                        'has_neckconnect': 0,
                        'accepts_actor_shadow': 0,
                        'is_minutehand': 0,
                        'is_hourhand': 0,
                        'static_backdrop': 0,
                        'unk_flag': 0,
                        'has_meshid': 1,
                        'bone_per_vertex': 0,
                        'indexid': 0, 
                        'vertexid': -1,
                        'skeletonid': 0,
                        'generate_new_id': 1}
                        
MATERIAL_DEFS = {       'doublesided': 0,
                        'floor_shadow_tex': 0,
                        'alpha_separate':  0,
                        'wrap_U': 1,
                        'wrap_V': 1,
                        'enable_alpha_test': 0,
                        'glass': 0,
                        'water': 0,
                        'still_water': 0,
                        'alpha_per_vertex': 0,
                        'alphaenvmap': 0,       
                        'invisible': 0,
                        'not_z_write': 0,
                        'self_lit': 0,
                        'no_floor_shadow': 0,
                        'no_delaydraw_transp': 0,
                        'tri_sort': 0,
                        'additive': 0,
                        'scroll_U': 0,
                        'scroll_V': 0,
                        'rot_UV': 0}
                            
GROUP_DEFS = {          'has_transanim': 0,
                        'is_land': 0,
                        'is_a_carbody': 0,
                        'hide_reflection': 0,
                        'has_hidden': 0,
                        'hidden_on': 0,
                        'hidden_off': 0}
                        
            #Bone Rig IDs and associated mesh
RIG_IDS =   {           16792576: "fac_catering0",
                        16815616: "MiniatureCar",
                        50345472: "p_barbell",
                        50346752: "fac_postproduction",
                        50382592: "fac_research",
                        50412288: "p_white_flag",
                        50432512: "p_mesuring_tape",
                        50461184: "p_baby",
                        67305984: "p_fake_magnum",
                        67338496: "p_rubbish_bag_skinned",
                        83908096: "p_newspaper",
                        84299264: "p_flyingsaucer_crane",
                        101327872: "p_flyingsaucers_crane",
                        117498624: "p_script",
                        118044416: "p_firehydrant_skinned",
                        118307072: "p_flag",
                        118318336: "fac_casting_office",
                        118335744: "fac_gatehouse",
                        118356736: "fac_wardrobe",
                        134234624: "toplevel_0",
                        134830848: "p_dustbin_skinned",
                        151010560: "p_rope_rappel",
                        151011072: "p_cardboard_boxes_skinned",
                        151044864: "p_umbrella",
                        152633600: "fac_publicity_office",
                        167792640: "p_crashmatt",
                        218106624: "mouth",
                        255528448: "Rat",
                        256829440: "p_reins",
                        268445696: "toplevel_2",
                        285223936: "testbed1",
                        288000512: "Dove",
                        310692608: "p_rope",
                        364778496: "p_skid_01",
                        385932544: "DeformableCar",
                        419484928: "eyes_shape",
                        503337984: "toplevel_1",
                        507812352: "Human",
                        593856256: "Ant",
                        869586944: "Cow",
                        872581632: "Dog",
                        946091264: "p_curtain_",
                        946110464: "ShowerCurtain",
                        994903296: "Horse",
                        1094395392: "generic_facialskin",
                        1718751744: "hat_m_fireman_v00",
                        1811973376: "sm_generic",
                        2123804160: "hat_m_fireman_v01"
                        }
                        
MSH_TYPES = (       "Set",
                    "Facility",
                    "Prop",
                    "Car",
                    "FemaleCostume",
                    "MaleCostume",
                    "Accessory",
                    "Hair",
                    "Hat",
                    "Latex",
                    "Blueprint",
                    "Backdrop")
                    
            # These are the standard points of connection for each gender.
            # The format uses the index of these points to connect the closest 'neckdata' tagged verts to these.  
            #  *** So don't ever change this data! ***
NECK_MALE = [Vector(0.070073, 0.000000, 1.543278),
                           Vector(0.048910, 0.055956, 1.564988),
                           Vector(0.029399, 0.074874, 1.583479),
                           Vector(-0.013411, 0.075498, 1.607305),
                           Vector(-0.043935, 0.043576, 1.611162),
                           Vector(-0.048926, 0.000001, 1.607596),
                           Vector(-0.043935, -0.043576,1.611162),
                           Vector(-0.013411, -0.075498, 1.607305),
                           Vector(0.029399, -0.074873, 1.583479),
                           Vector(0.048910, -0.055956, 1.564988)]
                        
NECK_FEMALE = [Vector(0.074359, 0.000005, 1.549346),
                             Vector(0.049324, 0.049710, 1.573448),
                             Vector(0.028644, 0.064228, 1.590175),
                             Vector(-0.016194, 0.055339, 1.601248),
                             Vector(-0.038122, 0.034884, 1.601856),
                             Vector(-0.048233, -0.000011, 1.601135),
                             Vector(-0.038122, -0.034884, 1.601855),
                             Vector(-0.016193, -0.055339, 1.601248),
                             Vector(0.028644, -0.064228, 1.590175),
                             Vector(0.049324, -0.049706, 1.573445)]

