import bpy, os, bmesh
from sys import stdout

def print(*strings):
	for s in strings: stdout.write(f"{s} ")
	stdout.write('\n')
	stdout.flush()

def GetTools(context):
	"""[0] Object\n\n[1] OBJTools\n\n[2] Stream\n\n[3] SceneTools"""
	if not context.object: return None, None, None, None
	return context.object, context.object.FP_ObjectTools, context.object.FP_ObjectTools.ActiveStream, context.scene.FP_SceneTools

@bpy.app.handlers.persistent
def CheckVersion(*_):
	Version = 205
	bpy.context.scene.FP_SceneTools.Updating = False
	bpy.context.scene.FP_SceneTools.Matting = False
	try: bpy.data.brushes.remove(bpy.data.brushes["FPCurveUI"])
	except: pass
	if bpy.context.scene.FP_SceneTools.FPVersion < Version and bpy.context.scene.FP_SceneTools.AllEmitters:
		ClearMat = bpy.context.scene.FP_SceneTools.Material
		bpy.context.scene.FP_SceneTools.Material = bpy.context.scene.FP_SceneTools.FluidSurface.data.materials[0]
		RemakeInstances(bpy.context, Refresh = True)
		Append("Material", "Default Fluid Mat")

		for O in bpy.context.scene.FP_SceneTools.AllEmitters:
			for Stream in O.FP_ObjectTools.MyList:
				P = Stream.VelPoints.add()
				P.x = Stream.VelMidFrame
				P.y = Stream.VelMidStrength

			O.data.materials.clear()

		bpy.context.scene.FP_SceneTools.Material = ClearMat
		ImportSurface(bpy.context)
		ParticleCatcher(bpy.context.scene.FP_SceneTools, bpy.context)
		bpy.ops.fp.recalculate()

	bpy.context.scene.FP_SceneTools.FPVersion = Version

def QuickCheck(context, HasStream:bool = False):
	if not context.object: return True
	if context.object.type != 'MESH': return True
	if HasStream and not context.object.FP_ObjectTools.Enabled: return True

	return False

def SafeAdjust(context):
	if context.scene.FP_SceneTools.Updating: return True
	if QuickCheck(context): return True

	OBJTools = context.object.FP_ObjectTools
	Index = max(0, min(OBJTools.FluidStreamIndex, len(OBJTools.MyList) - 1))
	if Index != OBJTools.FluidStreamIndex: OBJTools.FluidStreamIndex = Index

	bpy.ops.object.mode_set(mode='OBJECT')

	Emitters = context.scene.FP_SceneTools.AllEmitters
	if Emitters:
		Frame = min(min(S.Start for S in O.FP_ObjectTools.MyList) for O in Emitters) - 1
		if context.scene.frame_current != Frame: context.scene.frame_current = Frame

	Links = [S.LinkType for S in OBJTools.MyList]
	if "Self" in Links: context.object.location.x += 0
	if "All" in Links:
		for O in Emitters: O.location.x += 0

	return False

def SetEmitterVisibility(O, Visible:bool):
	O.show_instancer_for_render = Visible
	O.display_type = 'TEXTURED' if Visible else 'WIRE'
	O.visible_camera = Visible
	O.visible_diffuse = Visible
	O.visible_glossy = Visible
	O.visible_transmission = Visible
	O.visible_volume_scatter = Visible
	O.visible_shadow = Visible

def CleanupScene(context):
	"""Remove the fluid surface and catcher once no emitters remain in the scene."""
	SceneTools = context.scene.FP_SceneTools
	if SceneTools.AllEmitters: return
	if SceneTools.FluidSurface: bpy.data.meshes.remove(SceneTools.FluidSurface.data)
	if SceneTools.EnableCatcher:
		try:
			bpy.data.collections.remove(SceneTools.Catcher.users_collection[0])
			bpy.data.meshes.remove(SceneTools.Catcher.data)
		except: pass

def EnsureVizMaterial(O):
	"""Make sure the emitter's first material slot holds a usable material and return it."""
	Name = O.name + " - Fluid Viz"
	if len(O.data.materials) == 0:
		O.data.materials.append(bpy.data.materials.get(Name) or bpy.data.materials.new(name=Name))
	elif not O.data.materials[0] or ("Fluid Viz" in O.data.materials[0].name and O.data.materials[0].name != Name):
		O.data.materials[0] = bpy.data.materials.get(Name) or bpy.data.materials.new(name=Name)
	return O.data.materials[0]

def SetInput(Mod, Name, Value):
	"""Write a geometry nodes modifier input only when it actually changed, to avoid needless re-evaluations.
	Returns False when the modifier hasn't been evaluated yet (its inputs aren't available until the next
	depsgraph pass) so callers can retry later instead of erroring."""
	if bpy.app.version < (5, 2, 0):
		if Mod.get(Name) != Value: Mod[Name] = Value
		return True

	if not Mod.properties: return False
	Socket = getattr(Mod.properties.inputs, Name)
	if Socket.value != Value: Socket.value = Value
	return True

def CreateStream(context, O, OBJTools):
	Frame = context.scene.frame_current
	if OBJTools.Enabled: Frame = max(Frame, OBJTools.MyList[-1].System.frame_end)
	else: O.data.materials.clear()
	Stream = OBJTools.MyList.add()
	Stream.name = f"Stream {len(OBJTools.MyList)}"
	Stream.System = O.particle_systems[O.modifiers.new(Stream.name, type='PARTICLE_SYSTEM').name].settings
	Stream.System.name = f"{O.name} {Stream.name}"
	Stream.Start = int(Frame)
	item_sub_1 = Stream.VelPoints.add()
	item_sub_1.x = 0.2
	item_sub_1.y = 1.0
	OBJTools.ActiveStream = Stream

	OBJTools.FluidStreamIndex = len(OBJTools.MyList) - 1
	bpy.context.scene.FP_SceneTools.FluidStreamIndex = OBJTools.FluidStreamIndex

def RemoveStream(O, OBJTools):
	O.modifiers.remove(O.modifiers[f"Stream {OBJTools.FluidStreamIndex + 1}"])

	OldIndex = OBJTools.FluidStreamIndex
	OBJTools.FluidStreamIndex -= 1
	bpy.context.scene.FP_SceneTools.FluidStreamIndex -= 1

	OBJTools.MyList.remove(OldIndex)
	bpy.data.particles.remove(bpy.data.particles[f"{O.name} Stream {OldIndex + 1}"])

	for i, Mod in enumerate([M for M in O.modifiers if M.type == 'PARTICLE_SYSTEM']):
		OBJTools.MyList[i].name = f"Stream {i + 1}"
		Mod.name = f"Stream {i + 1}"
		Mod.particle_system.name = f"Stream {i + 1}"
		Mod.particle_system.settings.name = f"{O.name} Stream {i + 1}"

def SetStreamValues(context, O, OBJTools, Stream):
	System = Stream.System

	System.physics_type = 'FLUID'
	System.use_size_deflect = True
	System.use_modifier_stack = True
	System.integrator = "VERLET"

	O.modifiers[Stream.name].show_viewport = Stream.Viewport

	System.lifetime = OBJTools.Lifetime
	System.lifetime_random = OBJTools.LifetimeRandom
	System.display_size = (OBJTools.Size * 0.0001 * OBJTools.Radius)
	System.particle_size = OBJTools.Size * 0.001

	System.timestep = OBJTools.Speed * 0.04
	System.subframes = OBJTools.SubFrames

	System.mass = OBJTools.Mass
	System.fluid.stiffness = OBJTools.Stiffness

	if OBJTools.UnlinkStiffness: System.fluid.repulsion = OBJTools.Repulsion
	else: System.fluid.repulsion = OBJTools.RepulsionFactor

	System.fluid.use_factor_repulsion = not OBJTools.UnlinkStiffness

	System.fluid.linear_viscosity = OBJTools.Viscosity
	System.fluid.use_factor_stiff_viscosity = not OBJTools.UnlinkViscosity

	if OBJTools.UnlinkViscosity: System.fluid.stiff_viscosity = OBJTools.StiffViscosity
	else:
		if OBJTools.StiffViscosity != OBJTools.Viscosity: OBJTools.StiffViscosity = OBJTools.Viscosity
		System.fluid.stiff_viscosity = 1

	System.fluid.fluid_radius = OBJTools.Radius
	#Stream.Instance.modifiers["InstanceColour"]["Input_2"] = OBJTools.Radius * OBJTools.Size

	System.fluid.rest_density = OBJTools.Density
	System.fluid.spring_force = OBJTools.Spring

	System.effector_weights.gravity = OBJTools.Gravity
	System.effector_weights.all = OBJTools.Forces

	System.count = Stream.Count

	Stream.Velocity *= 1

def CreateLinks(context, O, OBJTools):
	SceneTools = context.scene.FP_SceneTools

	for S in OBJTools.MyList:
		P = O.particle_systems[S.name]
		Checks = {S:O}
		if S.LinkType != "None": Checks = OBJTools.Links
		if S.LinkType == "All": Checks = Checks | SceneTools.Links
		Checks.pop(S)
		with context.temp_override(particle_system=P):
			for Tar in range(len(P.targets)): bpy.ops.particle.target_remove()

			for System, Object in Checks.items():
				bpy.ops.particle.new_target()
				P.targets[len(P.targets) - 1].object = Object
				P.targets[len(P.targets) - 1].system = [M for M in Object.FP_ObjectTools.MyList].index(System) + 1

def ImportSurface(context = bpy.context):
	SaveActive = context.object
	SaveSelected = context.selected_objects
	SceneTools = context.scene.FP_SceneTools

	SceneTools.AllEmitters[0].particle_systems[0].settings.material = 0

	try: bpy.data.meshes.remove(bpy.data.objects["Fluid Surface"].data)
	except: pass
	try: bpy.data.node_groups.remove(bpy.data.node_groups["Fluid Surface"])
	except: pass
	try: bpy.data.node_groups.remove(bpy.data.node_groups["Fluid Render"])
	except: pass
	try: bpy.data.node_groups.remove(bpy.data.node_groups["Assign Mat Attributes"])
	except: pass

	Append("Object", "Fluid Surface")
	SceneTools.FluidSurface = context.scene.objects["Fluid Surface"]

	Append("NodeTree", "Fluid Surface")
	SceneTools.FluidSurface.modifiers.new(name="Fluid Surface", type='NODES').node_group = bpy.data.node_groups["Fluid Surface"]

	for Col in SceneTools.FluidSurface.users_collection: Col.objects.unlink(SceneTools.FluidSurface)
	context.scene.collection.objects.link(SceneTools.FluidSurface)

	if SaveActive: context.view_layer.objects.active = SaveActive
	for O in SaveSelected: O.select_set(True)

	SetSurface(context)

def Append(section, filename, BlendFile = os.path.join(os.path.dirname(os.path.abspath(__file__)), "FluidSurfaceNodes.blend")):
	filepath  = os.path.join(BlendFile, section, filename)
	directory = os.path.join(BlendFile, section)
	bpy.ops.wm.append(filepath = filepath, filename = filename, directory = directory)

def RemakeInstances(context, Refresh = False):
	"""Sync one instance object per stream. Existing valid instances are reused and only updated in place;
	new ones are copied from an existing instance (or appended once from disk when none exist yet).
	Refresh forces everything (including the InstanceColour node group) to be rebuilt from the bundled blend file."""
	SaveActive = context.object
	SaveSelected = context.selected_objects
	SceneTools = context.scene.FP_SceneTools

	if Refresh:
		try: bpy.data.node_groups.remove(bpy.data.node_groups["InstanceColour"])
		except: pass

	if not bpy.data.node_groups.get("InstanceColour"): Append("NodeTree", "InstanceColour")
	NodeGroup = bpy.data.node_groups["InstanceColour"]

	if not SceneTools.Collection:
		if FPI:= bpy.data.collections.get("Fluid Particle Instances"): SceneTools.Collection = FPI
		else: SceneTools.Collection = bpy.data.collections.new("Fluid Particle Instances")

	Emitters = SceneTools.AllEmitters

	#Drop instances no longer referenced by any stream first, so their names are free for renames below.
	Used = {S.Instance for O in Emitters for S in O.FP_ObjectTools.MyList if S.Instance}
	for Old in [O for O in SceneTools.Collection.objects if O not in Used]:
		try: bpy.data.meshes.remove(Old.data)
		except: pass

	Claimed = set()
	Template = None

	for O in Emitters:
		Mat = EnsureVizMaterial(O)
		for Stream in O.FP_ObjectTools.MyList:
			I = Stream.Instance
			if Refresh or not I or I in Claimed or "ParticleInstance" not in I.modifiers or "InstanceColour" not in I.modifiers:
				if I and I not in Claimed:
					try: bpy.data.meshes.remove(I.data)
					except: pass
				if Template:
					I = Template.copy()
					I.data = Template.data.copy()
				else:
					Append("Object", "Fluid Instance")
					I = context.scene.objects["Fluid Instance"]
				if "InstanceColour" not in I.modifiers: I.modifiers.new(name="InstanceColour", type='NODES')
				Stream.Instance = I

			Claimed.add(I)
			if not Template: Template = I

			I.name = f"{O.name} {Stream.name}"
			I.modifiers["InstanceColour"].node_group = NodeGroup
			I.modifiers["ParticleInstance"].object = O
			I.modifiers["ParticleInstance"].particle_system = O.particle_systems[Stream.name]
			SetInput(I.modifiers["InstanceColour"], "Socket_2", O.FP_ObjectTools.Radius * O.FP_ObjectTools.Size * 0.001)
			SetInput(I.modifiers["InstanceColour"], "Socket_4", Mat)

			if SceneTools.Collection not in I.users_collection:
				for Col in I.users_collection: Col.objects.unlink(I)
				SceneTools.Collection.objects.link(I)

	if SaveActive: context.view_layer.objects.active = SaveActive
	for O in SaveSelected:
		try: O.select_set(True)
		except: pass

def SetSurface(context):
	SceneTools = context.scene.FP_SceneTools
	if SceneTools.Updating: return

	Nodes = SceneTools.FluidSurface.modifiers["Fluid Surface"]

	SetInput(Nodes, "Input_8",  SceneTools.Collection)
	SetInput(Nodes, "Input_9",  SceneTools.SizeMultiplier)
	SetInput(Nodes, "Input_10", SceneTools.Quality)
	SetInput(Nodes, "Input_11", SceneTools.Viewport)
	SetInput(Nodes, "Input_12", SceneTools.Smoothing)
	SetInput(Nodes, "Input_15", SceneTools.CBlend)
	SetInput(Nodes, "Socket_2", bpy.app.version < (4, 5, 0))

	for O in SceneTools.AllEmitters:
		Mat = EnsureVizMaterial(O)

		Mat.diffuse_color = list(O.FP_ObjectTools.Colour) + [1]
		if bpy.app.version < (5, 0, 0): Mat.use_nodes = True
		if "Fluid Viz" in Mat.name:
			nodes = Mat.node_tree.nodes
			nodes[[n.bl_idname for n in nodes].index("ShaderNodeBsdfPrincipled")].inputs[0].default_value = list(O.FP_ObjectTools.Colour) + [1]

	if SceneTools.Material:
		if SceneTools.FluidSurface.material_slots[0].material != SceneTools.Material:
			SceneTools.FluidSurface.material_slots[0].material = SceneTools.Material
		return

	if not bpy.data.materials.get("Default Fluid Mat"): Append("Material", "Default Fluid Mat")
	if SceneTools.FluidSurface.material_slots[0].material != bpy.data.materials["Default Fluid Mat"]:
		SceneTools.FluidSurface.material_slots[0].material = bpy.data.materials["Default Fluid Mat"]

def ParticleCatcher(self, context=bpy.context):
	if SafeAdjust(context): return
	for O in context.scene.FP_SceneTools.AllEmitters: O.location.x += 0

	SaveActive = context.object
	SaveSelected = context.selected_objects

	try:
		bpy.data.collections.remove(self.Catcher.users_collection[0])
		bpy.data.meshes.remove(self.Catcher.data)
	except: pass

	if self.EnableCatcher:
		if not self.Catcher:
			BCatcher = bmesh.new()

			Size = 1000000
			V = []
			for v in [
				( 1 * Size,  1 * Size, 0),
				(-1 * Size,  1 * Size, 0),
				(-1 * Size, -1 * Size, 0),
				( 1 * Size, -1 * Size, 0)
			]: V.append(BCatcher.verts.new(v))
			BCatcher.faces.new(V)

			CatcherMesh = bpy.data.meshes.new("FP - Catcher")
			self.Catcher = bpy.data.objects.new("Particle Catcher", CatcherMesh)
			context.scene.collection.objects.link(self.Catcher)

			BCatcher.to_mesh(CatcherMesh)
			BCatcher.free()

			CatcherMesh.update()

			self.Catcher.location[2] = -5

			self.Catcher.modifiers.new(name="Collision", type='COLLISION')
			self.Catcher.collision.use_particle_kill = True

			try: CatcherCol = bpy.data.collections["Particle Catcher Holder"]
			except:
				CatcherCol = bpy.data.collections.new("Particle Catcher Holder")
				context.scene.collection.children.link(CatcherCol)

			for Col in self.Catcher.users_collection: Col.objects.unlink(self.Catcher)
			CatcherCol.objects.link(self.Catcher)

			CatcherCol.hide_render = True
			CatcherCol.hide_select = True
			context.view_layer.layer_collection.children[CatcherCol.name].hide_viewport = True

		self.Catcher.location[2] = self.CatcherHeight

	if SaveActive: context.view_layer.objects.active = SaveActive
	for O in SaveSelected: O.select_set(True)

def StoreCache(self, context):
	with context.temp_override(
		active_object=self.id_data,
		point_cache=self.id_data.particle_systems[self.name].point_cache
	): bpy.ops.ptcache.bake_from_cache()

def ClearCache(self, context):
	with context.temp_override(
			active_object=self.id_data,
			point_cache=self.id_data.particle_systems[self.name].point_cache
	): bpy.ops.ptcache.free_bake()
