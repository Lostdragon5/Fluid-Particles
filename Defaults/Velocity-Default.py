import bpy
bpy.context.object.FP_ObjectTools.ActiveStream.VelStartStrength = 0.5
bpy.context.object.FP_ObjectTools.ActiveStream.VelPoints.clear()
item_sub_1 = bpy.context.object.FP_ObjectTools.ActiveStream.VelPoints.add()
item_sub_1.name = ''
item_sub_1.x = 0.2
item_sub_1.y = 1.0
bpy.context.object.FP_ObjectTools.ActiveStream.VelEndStrength = 0.25
