import bpy, os
#from .FP_OPS import *
#from .FP_Functions import *
from .FP_VelocityCurve import _CURVE_NAME, get_curve
import bpy.utils.previews
icons_dict = bpy.utils.previews.new()

icons_dir = os.path.join(os.path.dirname(__file__), "icons")
icons_dict.load("PayPal", os.path.join(icons_dir, "PayPal.png"), 'IMAGE')
icons_dict.load("Ko-Fi", os.path.join(icons_dir, "Ko-Fi.png"), 'IMAGE')

#Add Fluid Particles Button to the Physics Panel.
def FluidParticlesButton(self, context):
	column = self.layout.column(align=True)
	split = column.split(factor=0.5)
	column_left = split.column()
	column_right = split.column()
	
	if not context.object.FP_ObjectTools.MyList: column_left.operator("fp.addstream", text="Fluid Particles", icon='PARTICLES')
	else: column_left.operator("fp.removeall", text="Fluid Particles", icon='PARTICLES')

def TitleWithPreset(column, Title:str, Button:str, CopyAddress:str = "", TextAlign = "CENTER"):
	Row = column.row()
	Left = Row.row(align=True)
	Left.alignment = "LEFT"

	if CopyAddress == "": Left.label(text="    ")
	else:
		Left.operator(f"fp.copy{CopyAddress.lower()}", text="", icon='COPYDOWN')
		Left.operator(f"fp.paste{CopyAddress.lower()}", text="", icon='PASTEDOWN')

	Center = Row.row()
	Center.alignment = TextAlign
	Center.label(text=Title)

	Right = Row.row()
	if TextAlign != "CENTER": Right.alignment = "RIGHT"
	Right.menu(Button, text="", icon='PRESET')

def EmitterList(self, context):
	SceneTools = context.scene.FP_SceneTools
	OBJTools = context.object.FP_ObjectTools

	col = self.layout.box().column(align = True)

	TitleWithPreset(col, "Streams", "fp.streammenu")

	row = col.row(align = True)
	row.template_list('FLUID_UL_StreamList', 'ListItem', OBJTools, 'MyList', SceneTools, 'FluidStreamIndex', rows = 6)
	
	col2 = row.column()
	col2.separator(factor=0.1)
	col2.operator("fp.addstream", text="Add", icon='ADD')
	col2.operator("fp.removestream", text="Remove", icon='REMOVE')

	if not OBJTools.MyList: return
	
	item = OBJTools.ActiveStream
	
	col2.prop(item, "Count")
	col2.prop(item, "Start")
	col2.prop(item, "Duration")
	col2.prop(item, "Velocity")
	
	#BAKE SETTINGS
	row = col.row(align = True)
	if context.object.particle_systems[OBJTools.FluidStreamIndex].point_cache.is_baked:
		C1 = row.column(align = True)
		C1.operator("fp.bakeself", text="Unbake Stream")
		op = C1.operator("fp.bakecache", text="Unbake Emitter")
		op.All = False

		C2 = row.column(align = True)
		op = C2.operator("fp.bakecache", text="Unbake All Emitters")
		op.All = True
		C2.operator("fp.bakeall", text="Rebake All Emitters")
	else:
		C1 = row.column(align=True)
		C1.operator("fp.bakeself", text="Bake Stream")
		op = C1.operator("fp.bakecache", text="Cache to Bake")
		op.All = False

		C2 = row.column(align=True)
		C2.operator("fp.bakeall", text="Bake All Emitters")
		op = C2.operator("fp.bakecache", text="Cache All Emitters")
		op.All = True

	#EXTRA UTILITIES
	row = col.row(align = True)
	row.operator("fp.recalculate", text="Recalculate", icon='FILE_REFRESH')

def SimSettings(self, context):
	SceneTools = context.scene.FP_SceneTools
	OBJTools = context.object.FP_ObjectTools
	layout = self.layout
	
	col = layout.box().column()

	#PARTICLE SETTINGS
	TitleWithPreset(col, "Particle Settings", "fp.particlemenu", "Particle")
	
	row = col.row()
	row.prop(OBJTools, "Lifetime")
	row.prop(OBJTools, "LifetimeRandom", text = "Randomness", slider = True)
	row = col.row()
	row.prop(OBJTools, "Size", text = "Particle Radius")
	row.prop(OBJTools, "Radius", text = "Interaction Distance", slider = True)
	
	col.separator()
	
	#INTERACTION SETTINGS
	TitleWithPreset(col, "Interaction Settings", "fp.interactionmenu", "Interaction")
	
	row = col.row()
	col2 = row.column()
	if OBJTools.UnlinkStiffness: col2.prop(OBJTools, "UnlinkStiffness", text = "Stiffness (Unlinked Repulsion)", emboss = False)
	else: col2.prop(OBJTools, "UnlinkStiffness", text = "Stiffness (Factored Repulsion)", emboss = False)
	
	col2.prop(OBJTools, "Stiffness")
	
	if OBJTools.UnlinkStiffness: col2.prop(OBJTools, "Repulsion")
	else: col2.prop(OBJTools, "RepulsionFactor", text = "Repulsion ", slider = True)
	

	col2 = row.column()
	if OBJTools.UnlinkViscosity: col2.prop(OBJTools, "UnlinkViscosity", text = "Viscosity (Unlinked)", emboss = False)
	else: col2.prop(OBJTools, "UnlinkViscosity", text = "Viscosity (Linked)", emboss = False)
	
	col2.prop(OBJTools, "Viscosity", text = "Compression")
	col3 = col2.column()
	col3.enabled = OBJTools.UnlinkViscosity
	col3.prop(OBJTools, "StiffViscosity", text = "Expansion")
	
	col.separator()
	col.prop(OBJTools, "Density", text = "Rest Density")
	col.prop(OBJTools, "Mass")
	col.prop(OBJTools, "Spring")
	
	col.separator()
	
	#SCENE SETTINGS
	TitleWithPreset(col, "Scene Settings", "fp.scenemenu", "Scene")
	
	row = col.row()
	row.prop(SceneTools, "EnableCatcher", text = "Enable Catcher", toggle = True)
	row.prop(SceneTools, "CatcherHeight", text = "Catcher Height")
	row = col.row()
	row.prop(OBJTools, "Gravity", slider = True)
	row.prop(OBJTools, "Forces", slider = True)
	row = col.row()
	row.prop(OBJTools, "Speed", text = "Simulation Speed", slider = True)
	row.prop(OBJTools, "SubFrames")

def AnimSettings(self, context):
	SceneTools = context.scene.FP_SceneTools
	OBJTools = context.object.FP_ObjectTools
	layout = self.layout
	
	item = OBJTools.ActiveStream

	layout.template_curve_mapping(get_curve()[0], _CURVE_NAME)

	box = layout.box()

	TitleWithPreset(box, "Manual Coordinates", "fp.velocitymenu", "Curve")

	row = box.split(factor=0.8, align=True)
	row.prop(item, "VelStartStrength", text=f"Start Strength:", slider=True)
	op = row.operator("fp.addpoint", text="", icon='TRIA_DOWN_BAR')
	op.index = 0
	op.dir = 0

	col = box.column(align=True)
	i = 0

	if len(item.VelPoints) == 0:
		Center = col.row()
		Center.alignment = 'CENTER'
		Center.label(text="No control points added.")

	for i, Point in enumerate(sorted(item.VelPoints, key=lambda p: p.x)):
		row = col.split(factor=0.8, align=True)
		r1 = row.split(factor=0.5, align=True)
		r1.prop(Point, "x", text=f"Pt {i}:", slider=True)

		r11 = r1.split(factor=0.75, align=True)
		r11.prop(Point, "y", text="", slider=True)
		op = r11.operator("fp.removepoint", text="", icon='CANCEL')
		op.index = i

		r2 = row.split(align=True)
		op = r2.operator("fp.addpoint", text="", icon='TRIA_DOWN_BAR')
		op.index = i + 1
		op.dir = 0
		op = r2.operator("fp.addpoint", text="", icon='TRIA_UP_BAR')
		op.index = i + 1
		op.dir = 1

	row = box.split(factor=0.8, align=True)
	row.prop(item, "VelEndStrength", text=f"End Strength:", slider=True)
	op = row.operator("fp.addpoint", text="", icon='TRIA_UP_BAR')
	op.index = len(item.VelPoints) + 1
	op.dir = 1

def RenderSettings(self, context, Full = True):
	SceneTools = context.scene.FP_SceneTools
	layout = self.layout

	col = layout.column()
	col.operator("fp.fixsurface", text="Fix Surface", icon='FILE_REFRESH')
	col.prop(SceneTools, "SizeMultiplier")
	col.prop(SceneTools, "Quality")
	col.prop(SceneTools, "Viewport", text = "Render Preview", slider=True)
	
	row = col.row()
	row.prop(SceneTools, "Smoothing")
	row.prop(SceneTools, "CBlend", text = "Material Blending")
	
	col.separator()
	
	col = layout.box().column()
	col.prop(SceneTools, "Material", text = "Custom Mat")

	if not Full: return

	OBJTools = context.object.FP_ObjectTools
	if OBJTools.MyList:
		if SceneTools.Material or "Fluid Viz" not in context.object.data.materials[0].name:
			if bpy.app.version < (5, 2, 0): col.prop(OBJTools.ActiveStream.Instance.modifiers["InstanceColour"], '["Socket_3"]', text="Material ID")
			else: col.prop(OBJTools.ActiveStream.Instance.modifiers["InstanceColour"].properties.inputs.Socket_3, 'value', text="Material ID")
			col.label(text="Using Custom Material. Select Fluid Surface to Edit.")
			return

		TitleWithPreset(col, "Colour", "fp.materialmenu", "Material", "LEFT")
		col.prop(SceneTools, "Colour", text = "")
		col.prop(SceneTools, "Roughness", slider = True)
		col.prop(SceneTools, "MatDensity", slider = True)
		col.prop(SceneTools, "Emit")
		col.prop(SceneTools, "EmitStr")
		col.separator(factor=2)
	
	else: col.label(text = "Not an Emitter")

def DonationButton(self, context):
	row = self.layout.row()
	row.operator("wm.url_open", text="Tip via PayPal", icon_value=icons_dict["PayPal"].icon_id).url = "paypal.me/AzzurraNila" 
	row.operator("wm.url_open", text="Tip via Ko-Fi", icon_value=icons_dict["Ko-Fi"].icon_id).url = "ko-fi.com/mysticdragoness"

#New Physics Panel UI for Emitter objects.
class EmitterPanel(bpy.types.Panel):
	bl_space_type = 'PROPERTIES'
	bl_region_type = 'WINDOW'
	bl_context = "physics"
	bl_category = "Fluid Particles"
	bl_label = "Fluid Particles"
	bl_idname = "FP_PT_EMITTER_UI"
	
	@classmethod
	def poll(cls, context):
		if context.object == None: return
		if context.object.type != "MESH": return
		if not context.object.FP_ObjectTools.MyList and context.object != context.scene.FP_SceneTools.FluidSurface: return
		return "TYPE_NONE"
	
	def draw(self, context):
		SceneTools = context.scene.FP_SceneTools
		self.layout.prop(SceneTools, "SettingsTabs", expand=True)
		
		if context.object != context.scene.FP_SceneTools.FluidSurface:
			if SceneTools.SettingsTabs == "SimSettings":
				EmitterList(self, context)
				SimSettings(self, context)

			if SceneTools.SettingsTabs == "AnimSettings":
				EmitterList(self, context)
				AnimSettings(self, context)

			if SceneTools.SettingsTabs == "RenderSettings": RenderSettings(self, context)
		
		else: RenderSettings(self, context)
	
		DonationButton(self, context)

class EmitterPanel_View(bpy.types.Panel):
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'UI'
	bl_category = "Fluid Particles"
		
	def draw(self, context, IsRender = False):
		if context.object == None or context.object.type != "MESH":
			self.layout.label(text = "No Mesh Object Selected...")
			return False
		
		if context.object == context.scene.FP_SceneTools.FluidSurface and not IsRender: return False
		
		return True

class EmitterPanel_List(EmitterPanel_View):
	bl_label = "Fluid Particles"
	bl_idname = "FP_PT_EMITTER_EMITTER_LIST"
		
	def draw(self, context):
		if not super().draw(context): return

		EmitterList(self, context)

class EmitterPanel_Sim(EmitterPanel_View):
	bl_label = "Simulation Settings"
	bl_idname = "FP_PT_EMITTER_SIM_SETTINGS"
		
	def draw(self, context):
		if not super().draw(context): return

		if context.object.FP_ObjectTools.MyList: SimSettings(self, context)

class EmitterPanel_Anim(EmitterPanel_View):
	bl_label = "Animation Settings"
	bl_idname = "FP_PT_EMITTER_ANIM_SETTINGS"
		
	def draw(self, context):
		if not super().draw(context): return

		if context.object.FP_ObjectTools.MyList: AnimSettings(self, context)

class EmitterPanel_Render(EmitterPanel_View):
	bl_label = "Render Settings"
	bl_idname = "FP_PT_EMITTER_RENDER_SETTINGS"
		
	def draw(self, context):
		#if not super().draw(context, True): return

		RenderSettings(self, context, super().draw(context, True))
		DonationButton(self, context)

_classes = [
	EmitterPanel,
	EmitterPanel_List,
	EmitterPanel_Sim,
	EmitterPanel_Anim,
	EmitterPanel_Render,
]

_registerFunctions = [lambda:bpy.types.PHYSICS_PT_add.append(FluidParticlesButton)]
_unregisterFunctions = [lambda:bpy.types.PHYSICS_PT_add.remove(FluidParticlesButton)]

def register():
	for C in _classes: bpy.utils.register_class(C)
	
	bpy.types.PHYSICS_PT_add.append(FluidParticlesButton)

def unregister():
	for C in _classes: bpy.utils.unregister_class(C)
	
	bpy.types.PHYSICS_PT_add.remove(FluidParticlesButton)

if __name__ == "__main__":
	register()