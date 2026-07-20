bl_info = {
	"name": "Fluid Particles",
	"author": "Azzurra Nila",
	"version": (2,5,9),
	"blender": (4, 0, 0),
	"location": "Properties > Physics > Fluid Particles",
	"description": "",
	"warning": "",
	"doc_url": "",
	"category": "Simulation",
}

import bpy, os, shutil
from . import FP_UI, FP_OPS, FP_CopySettings, FP_Presets, FP_Material
from .FP_Functions import ParticleCatcher, GetTools, CheckVersion, EnsureVizMaterial, SetInput
from .FP_Updates import *
from . import FP_VelocityCurve

class Point(bpy.types.PropertyGroup):
	x: bpy.props.FloatProperty(min=0.001, max=0.999, options=set(), update = UpdatePoint)
	y: bpy.props.FloatProperty(min=0, max=1, options=set(), update = UpdatePoint)

class ListItem(bpy.types.PropertyGroup):
	name: bpy.props.StringProperty(name = "name", description = "name Of Stream", default = "New Stream")

	LinkType: bpy.props.EnumProperty(items=[
		('None', "", "No Interaction: Fastest but doesn't react with any other sim from any emitter.", 'UNLINKED', 0),
		('Self', "", "Self Interaction: Moderate and only interacts with sims of this setting from this emitter.", 'LINKED', 1),
		('All', "", "Full Interaction: Slowest but interacts with all other sims of this setting.", 'HAND', 2)
	], name = "Link Type", options=set(), update = UpdateLinks)

	Viewport: bpy.props.BoolProperty(default = True, description = "Display and calculate sim in viewport", options=set(), update = UpdateStream)
	Render: bpy.props.BoolProperty(default = True, description = "Display sim in render", options=set(), update = UpdateRender)

	Count: bpy.props.IntProperty(name = "Count", default = 1000, min = 1, description = "How many particles to use (useful to increase when using higher velocities)", options=set(), update = UpdateStream)
	Start: bpy.props.IntProperty(name = "Start Frame", default = 1, description = "When to start the particle sim", options=set(), update = UpdatePoints)
	Duration: bpy.props.IntProperty(name = "Duration", default = 25, min = 1, description = "How long the particle sim will add new particles", options=set(), update = UpdatePoints)

	Velocity: bpy.props.FloatProperty(name = "Velocity", default = 5, unit = 'VELOCITY', description = "The peak velocity for this particle system (start and end velocities can be adjusted in the \"Animation\" tab)", options=set(), update = UpdatePoints)
	VelStartStrength: bpy.props.FloatProperty(name = "Start Strength", default = 0.5, min = 0, max = 1, description = "The velocity at the start of the sim (relative to the Velocity parameter)", options=set(), update = UpdatePoints)
	VelEndStrength: bpy.props.FloatProperty(name = "End Strength", default = 0.25, min = 0, max = 1, description = "The velocity at the end of the sim (relative to the Velocity parameter)", options=set(), update = UpdatePoints)

	VelPoints: bpy.props.CollectionProperty(type=Point)

	VelMidStrength: bpy.props.FloatProperty(name = "(Deprecated) Peak Strength", default = 1, min = 0, max = 1, description = "Deprecated")
	VelMidFrame: bpy.props.FloatProperty(name = "(Deprecated) Peak Time", default = 0.2, min = 0, max = 1, description = "Deprecated")

	System: bpy.props.PointerProperty(type = bpy.types.ParticleSettings)
	Instance: bpy.props.PointerProperty(type = bpy.types.Object)

class FLUID_UL_StreamList(bpy.types.UIList):
	def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):

		layout.label(text = item.name)

		row = layout.row(align = True)

		row.prop(item, "LinkType", icon_only = True, expand = True)

		row.separator(factor = 2)

		if item.Viewport: row.prop(item, "Viewport", icon_only = True, icon = 'RESTRICT_VIEW_OFF')
		else: row.prop(item, "Viewport", icon_only = True, icon = 'RESTRICT_VIEW_ON')

		if item.Render: row.prop(item, "Render", icon_only = True, icon = 'RESTRICT_RENDER_OFF')
		else: row.prop(item, "Render", icon_only = True, icon = 'RESTRICT_RENDER_ON')

class ObjectToolSettings(bpy.types.PropertyGroup):
	@property
	def Links(self):
		return {S: self.id_data for S in self.MyList if S.LinkType != "None"}

	MyList : bpy.props.CollectionProperty(type = ListItem)
	FluidStreamIndex : bpy.props.IntProperty(default = 0, min = 0, name = "Index for MyList", options=set())

	@property
	def Enabled(self): return len(self.MyList) > 0

	@property
	def ActiveStream(self): return self.MyList[self.FluidStreamIndex] if self.Enabled else None
	@ActiveStream.setter
	def ActiveStream(self, stream):
		ML = [s for s in self.MyList]
		if stream not in ML: return
		self.FluidStreamIndex = ML.index(stream) #type: ignore

	Lifetime : bpy.props.IntProperty(default = 250, min = 0, description = "How long the particles live for", options=set(), update = UpdateEmitter)
	LifetimeRandom : bpy.props.FloatProperty(default = 0, min = 0, max = 1, description = "Adds Variation to how long the particles live", options=set(), update = UpdateEmitter)
	Size : bpy.props.FloatProperty(default = 10, soft_min = 1, min = 0.1, unit = 'CAMERA', description = "Diameter of each particle (affects object collisions)", options=set(), update = UpdateEmitter)
	Radius : bpy.props.FloatProperty(default = 2, min = 0, soft_max = 2, description = "How many times larger each particles is than its size (doesn't affect object collisions)", options=set(), update = UpdateEmitter)

	UnlinkStiffness : bpy.props.BoolProperty(default = False, description = "Toggle between using Repulsion as a factor of Stiffness or as it's own separate value", options=set(), update = UpdateStiffness)
	Stiffness : bpy.props.FloatProperty(default = 0.5, min = 0, max = 100, description = "How incompressible the fluid is", options=set(), update = UpdateEmitter)
	Repulsion : bpy.props.FloatProperty(default = 5, min = 0, max = 100, description = "How much the particles repel each other (separate from Stiffness)", options=set(), update = UpdateEmitter)
	RepulsionFactor : bpy.props.FloatProperty(default = 1, min = 0, soft_max = 2, max = 100, description = "How much the particles repel each other (relative to Stiffness)", options=set(), update = UpdateEmitter)

	UnlinkViscosity : bpy.props.BoolProperty(default = False, description = "Toggle between using one value for viscosity or splitting between compressive and expansive viscosity", options=set(), update = UpdateEmitter)
	Viscosity : bpy.props.FloatProperty(default = 25, min = 0, max = 100, description = "How much the particles resist shearing", options=set(), update = UpdateEmitter)
	StiffViscosity : bpy.props.FloatProperty(default = 1, min = 0, max = 100, name = "Stiff Viscosity", description = "How much the particles resist pulling apart", options=set(), update = UpdateEmitter)

	Density : bpy.props.FloatProperty(default = 2, min = 0, max = 10, description = "How much the particles want to overlap (higher values means more overlapping and lower values means gaps between each particle. A value of 1 means the particles rest perfectly against each other)", options=set(), update = UpdateEmitter)
	Mass : bpy.props.FloatProperty(default = 1, min = 0.01, soft_max=10, unit = 'MASS', description = "How heavy each particle is (only changes how particles interacts with other systems)", options=set(), update = UpdateEmitter)
	Spring : bpy.props.FloatProperty(name = "Stickiness", default = 10, min = 0, max = 100, description = "How much the particles stick to each other", options=set(), update = UpdateEmitter)

	Gravity : bpy.props.FloatProperty(name = "Gravity", default = 1, soft_min = 0, soft_max = 2, description = "How much the particles are affected by gravity", options=set(), update = UpdateEmitter)
	Speed : bpy.props.FloatProperty(default = 1, min = 0, soft_max = 2, description = "How fast the particles are (relative to seconds, not frame rate)", options=set(), update = UpdateEmitter)
	Forces : bpy.props.FloatProperty(name = "Force Fields", default = 1, min = 0, soft_max = 2, description = "How much the particles are affected by force fields", options=set(), update = UpdateEmitter)
	SubFrames : bpy.props.IntProperty(default = 5, min = 0, description = "How many times to calculate the fluid between each frame", options=set(), update = UpdateEmitter)

	Colour : bpy.props.FloatVectorProperty(name = "Colour", min = 0, max = 1, default = (0.950000, 0.900000, 1.000000), subtype='COLOR', description = "Sets Colour for all streams from this emitter", options=set())
	Roughness : bpy.props.FloatProperty(name = "Roughness", min = 0, default = 0.1, description = "Sets Roughness for all streams from this emitter", options=set())
	MatDensity : bpy.props.FloatProperty(name = "Density", min = 0, default = 1, description = "Sets how opaque the fluid looks for all streams from this emitter.\n\n(Note, doesn't currently work with Volume shaders, so it'll use the highest density of all streams for Cycles)", options=set())
	Emit : bpy.props.FloatVectorProperty(name = "Emission Colour", min = 0, max = 1, default = (0, 0, 0), subtype='COLOR', description = "Sets Emission Colour for all streams from this emitter", options=set())
	EmitStr : bpy.props.FloatProperty(name = "Emission Strength", min = 0, default = 1, description = "Sets Emission Strength for all streams from this emitter", options=set())
	MatID : bpy.props.IntProperty(name = "Material ID", min = 1, default = 1, description = "Used to blend between fluids in custom materials.\n\nUse attribute \"Fluid 1\" to filter sims with an ID set to 1, \"Fluid 2\" for an ID of 2, etc", options=set())

_Checks = ("FluidStreamIndex", "Colour", "Roughness", "MatDensity", "Emit", "EmitStr", "MatID")
_SceneSig = None

def _SceneSignature(O, SceneTools):
	MatName = O.data.materials[0].name if len(O.data.materials) and O.data.materials[0] else None
	Values = tuple(tuple(V) if hasattr(V, "__len__") else V for V in (getattr(SceneTools, C) for C in _Checks))
	return (O.name, MatName, Values)

@bpy.app.handlers.persistent
def SceneSurface(self, _):
	global _SceneSig
	O, OBJTools, Stream, SceneTools = GetTools(bpy.context)
	if not O: return
	if SceneTools.Updating: return
	if not OBJTools.Enabled: return

	#Detect emitters that were duplicated (their streams still share particle settings with the original).
	Broken = [(o, S) for o in SceneTools.AllEmitters for S in o.FP_ObjectTools.MyList
		if S.System.users > 2 and S.System.name != f"{o.name} {S.name}"]

	#Fast path: nothing changed since the last pass, leave without touching anything
	#(writing to the scene here would immediately queue another depsgraph update).
	if not Broken and O.name == SceneTools.LastObject and _SceneSignature(O, SceneTools) == _SceneSig: return

	SceneTools.Updating = True
	try:
		for o, S in Broken:
			S.System = o.particle_systems[S.name].settings = bpy.data.particles.new(name="ParticleSettings")
			S.System.name = f"{o.name} {S.name}"
			SetStreamValues(bpy.context, o, o.FP_ObjectTools, S)
			UpdatePoints(S, bpy.context)
			for L in o.FP_ObjectTools.MyList: L.System.material = 0

		if Broken: RemakeInstances(bpy.context)

		if O.name == SceneTools.LastObject:
			for C in _Checks: setattr(OBJTools, C, getattr(SceneTools, C))

			Mat = EnsureVizMaterial(O)

			Synced = True
			for I in [S.Instance for S in OBJTools.MyList]:
				try:
					if not I or "InstanceColour" not in I.modifiers: continue
					if not SetInput(I.modifiers["InstanceColour"], "Socket_4", Mat): Synced = False
				except: pass

			Mat.diffuse_color = list(OBJTools.Colour) + [1]
			if bpy.app.version < (5, 0, 0): Mat.use_nodes = True
			if "Fluid Viz" in Mat.name and Mat.node_tree:
				Mat.node_tree.nodes["Principled BSDF"].inputs[0].default_value = list(OBJTools.Colour) + [OBJTools.MatDensity]

			#Only mark this state as handled once every instance could be written, so unready ones get retried.
			_SceneSig = _SceneSignature(O, SceneTools) if Synced else None
		else:
			SceneTools.LastObject = O.name
			for C in _Checks: setattr(SceneTools, C, getattr(OBJTools, C))
			_SceneSig = None #Let the branch above run once for the newly active object.
	finally:
		SceneTools.Updating = False

def CleanUpdate(self, context):
	try:
		Mod = self.FluidSurface.modifiers["Fluid Surface"]
		if Mod.show_viewport == self.Updating: Mod.show_viewport = not self.Updating
	except: pass

class SceneSettings(bpy.types.PropertyGroup):
	FPVersion : bpy.props.IntProperty()
	Collection : bpy.props.PointerProperty(type = bpy.types.Collection)

	LastObject : bpy.props.StringProperty()
	FluidStreamIndex: bpy.props.IntProperty(default=0, min=0, name="Index for MyList", options=set())
	Colour : bpy.props.FloatVectorProperty(name = "Colour", min = 0, max = 1, default = (0.950000, 0.900000, 1.000000), subtype='COLOR', description = "Sets Colour for all streams from this emitter", options=set())
	Roughness : bpy.props.FloatProperty(name = "Roughness", min = 0, default = 0.1, max = 1, description = "Sets Roughness for all streams from this emitter", options=set())
	MatDensity : bpy.props.FloatProperty(name = "Density", min = 0, default = 1, max = 1, description = "Sets how opaque the fluid looks for all streams from this emitter.\n\n(Note, doesn't currently work with Volume shaders, so it'll use the highest density of all streams for Cycles)", options=set())
	Emit : bpy.props.FloatVectorProperty(name = "Emission Colour", min = 0, max = 1, default = (0, 0, 0), subtype='COLOR', description = "Sets Emission Colour for all streams from this emitter", options=set())
	EmitStr : bpy.props.FloatProperty(name = "Emission Strength", min = 0, default = 1, description = "Sets Emission Strength for all streams from this emitter", options=set())
	MatID : bpy.props.IntProperty(name = "Material ID", min = 1, default = 1, description = "Used to blend between fluids in custom materials.\n\nUse attribute \"Fluid 1\" to filter sims with an ID set to 1, \"Fluid 2\" for an ID of 2, etc", options=set())

	@property
	def AllEmitters(self):
		AE = []
		for o in self.id_data.objects:
			if not o.FP_ObjectTools.Enabled: continue
			if o.type != 'MESH':
				o.FP_ObjectTools.MyList.clear()
				continue
			AE.append(o)

		return AE

	@property
	def Links(self):
		AS = []
		for O in self.AllEmitters:
			AS.extend([S,O] for S in O.FP_ObjectTools.MyList if S.LinkType == "All")

		return dict(AS)

	FluidSurface : bpy.props.PointerProperty(type = bpy.types.Object)

	Catcher : bpy.props.PointerProperty(type = bpy.types.Object)
	EnableCatcher : bpy.props.BoolProperty(default = False, description = "Adds a floor that deletes all particles that hit it", update = ParticleCatcher, options=set())
	CatcherHeight : bpy.props.FloatProperty(default = -0.1, unit = 'LENGTH', description = "At what height shall particles get deleted at (doesn't delete particles that spawn below this height)", update = ParticleCatcher, options=set())

	SettingsTabs : bpy.props.EnumProperty(items=[
		('SimSettings', "Sim Settings", "Particle System settings", "", 0),
		('AnimSettings', "Animation", "Velocity curve settings for each stream", "", 1),
		('RenderSettings', "Render Settings", "Fluid Surface and Material settings", "", 2)
	], options=set())

	SizeMultiplier : bpy.props.FloatProperty(default = 2, min = 0, name = "Size Multiplier", description = "How many times thicker the fluid should be compared to the particles (helps get rid of air pockets between particles)", update = UpdateSurface, options=set())
	Quality : bpy.props.IntProperty(default = 2, min = 1, description = "Resolution of the fluid surface (relative to the size multiplier)", update = UpdateSurface, options=set())
	Viewport : bpy.props.FloatProperty(default = 0, min = 0, max = 1, description = "Quality of the fluid surface in the viewport (0 disables the fluid surface). **Does not affect the render**", update = UpdateSurface, options=set())
	Smoothing : bpy.props.IntProperty(default = 10, min = 0, description = "Smooths out the fluid surface, getting rid of unwanted bumps and creating a sense of surface tension", update = UpdateSurface, options=set())
	CBlend : bpy.props.IntProperty(default = 25, min = 0, description = "Blends between the materials of each fluid where they interact", update = UpdateSurface, options=set())
	Material : bpy.props.PointerProperty(type = bpy.types.Material, description = "Set a custom material to use instead of the default one. \nYou can use the \"Fluid #\" attributes to mix shaders based on an emitter's \"Material ID\"", update = UpdateSurface, options=set())

	Updating : bpy.props.BoolProperty(default = False, update = CleanUpdate, options={'SKIP_SAVE'})

	Matting : bpy.props.BoolProperty(default = False, update = CleanUpdate, options={'SKIP_SAVE'})

	CopyVel : bpy.props.StringProperty(default = "{}")

	CallCount : bpy.props.IntProperty(default = 0, min = 0)

_classes = [
	FLUID_UL_StreamList,
	Point,
	ListItem,
	ObjectToolSettings,
	SceneSettings,
]

_registerFunctions = [
	lambda:setattr(bpy.types.Scene, "FP_SceneTools", bpy.props.PointerProperty(type = SceneSettings)),
	lambda:setattr(bpy.types.Object, "FP_ObjectTools", bpy.props.PointerProperty(type = ObjectToolSettings)),
	lambda:([bpy.app.handlers.depsgraph_update_post.remove(h) for h in list(bpy.app.handlers.depsgraph_update_post) if h.__name__ == "SceneSurface"]),
	lambda:bpy.app.handlers.depsgraph_update_post.append(SceneSurface),
]

_unregisterFunctions = [
	lambda:([bpy.app.handlers.depsgraph_update_post.remove(h) for h in list(bpy.app.handlers.depsgraph_update_post) if h.__name__ == "SceneSurface"]),
	lambda:([bpy.app.handlers.load_post.remove(h) for h in list(bpy.app.handlers.load_post) if h.__name__ == "CheckVersion"]),
]

def JoinRegistries(*classes):
	global _classes, _registerFunctions, _unregisterFunctions
	for cls in classes:
		try:_classes += cls._classes
		except:pass
		try:_registerFunctions += cls._registerFunctions
		except:pass
		try:_unregisterFunctions += cls._unregisterFunctions
		except:pass

JoinRegistries(FP_UI, FP_OPS, FP_VelocityCurve, FP_CopySettings, FP_Presets, FP_Material)

def register():

	for C in _classes: bpy.utils.register_class(C)

	for RF in _registerFunctions: RF()

	bpy.app.timers.register(CheckVersion)
	for h in [h for h in bpy.app.handlers.load_post if h.__name__ == "CheckVersion"]: bpy.app.handlers.load_post.remove(h)
	bpy.app.handlers.load_post.append(CheckVersion)

	DefaultsFolder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Defaults")
	PresetFolder = os.path.join(bpy.utils.user_resource("SCRIPTS"), "presets", "Fluid Particles")

	for Original, File in [(os.path.join(DefaultsFolder, f), os.path.join(PresetFolder, f[:f.rfind("-")], f[f.rfind("-")+1:])) for f in os.listdir(DefaultsFolder)]:
		os.makedirs(os.path.dirname(File), exist_ok=True)
		shutil.copyfile(Original, File)

def unregister():
	for UF in _unregisterFunctions: UF()
	for C in reversed(_classes): bpy.utils.unregister_class(C)

if __name__ == "__main__":
	register()