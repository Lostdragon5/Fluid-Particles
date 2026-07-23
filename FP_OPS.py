import bpy
from .FP_Functions import *

class AddStreamOps(bpy.types.Operator):
	"""Add a stream to the current emitter"""
	bl_idname = "fp.addstream"
	bl_label = "Add"

	bl_options = {'UNDO'}

	def execute(self, context):
		# SafeAdjust rewinds the playhead, so remember where the user actually was.
		Frame = context.scene.frame_current
		if SafeAdjust(context): return {'CANCELLED'}

		O = context.object
		OBJTools = O.FP_ObjectTools
		if not OBJTools.Enabled: SetEmitterVisibility(O, False)

		CreateStream(context, O, OBJTools, Frame)
		SetStreamValues(context, O, OBJTools, OBJTools.ActiveStream)

		if not context.scene.FP_SceneTools.FluidSurface:
			if FS := bpy.data.objects.get("Fluid Surface"): context.scene.FP_SceneTools.FluidSurface = FS
			else: ImportSurface(context)
		RemakeInstances(context)
		SetSurface(context)
		return {'FINISHED'}

class RemoveStreamOps(bpy.types.Operator):
	"""Remove the selected stream"""
	bl_idname = "fp.removestream"
	bl_label = "Remove"

	bl_options = {'UNDO'}

	def execute(self, context):
		if SafeAdjust(context): return {'CANCELLED'}
		if not context.object.FP_ObjectTools.Enabled: return {'CANCELLED'}

		context.scene.FP_SceneTools.Updating = True
		try:
			RemoveStream(context.object, context.object.FP_ObjectTools)
			CreateLinks(context, context.object, context.object.FP_ObjectTools)

			if not context.object.FP_ObjectTools.Enabled: SetEmitterVisibility(context.object, True)

			CleanupScene(context)
			RemakeInstances(context)
		finally:
			context.scene.FP_SceneTools.Updating = False
		return {'FINISHED'}

class Recalculate(bpy.types.Operator):
	"""Delete current cache/bake and reset to start of sim. Useful for fixing any buggy sims or interactions"""
	bl_idname = "fp.recalculate"
	bl_label = "Recalculate"

	bl_options = {'UNDO'}

	def execute(self, context):
		context.scene.FP_SceneTools.Updating = False
		context.scene.FP_SceneTools.Matting = False

		if SafeAdjust(context): return {'CANCELLED'}

		context.scene.FP_SceneTools.Updating = True
		try:
			for O in context.selected_objects:
				for Stream in O.FP_ObjectTools.MyList: ClearCache(Stream, context)
			for O in context.scene.FP_SceneTools.AllEmitters:
				for S in O.FP_ObjectTools.MyList:
					SetStreamValues(context, O, O.FP_ObjectTools, S)
		except Exception as e:
			context.scene.FP_SceneTools.Updating = False
			raise e
		context.scene.FP_SceneTools.Updating = False

		RemakeInstances(context)

		return {'FINISHED'}

class BakeSelf(bpy.types.Operator):
	"""Bake only the currently selected stream"""
	bl_idname = "fp.bakeself"
	bl_label = "BakeSelf"

	bl_options = {'UNDO'}

	def execute(self, context):
		O, OBJTools, Stream, SceneTools = GetTools(context)
		SceneTools.FluidSurface.modifiers["Fluid Surface"].show_viewport = False

		Override = dict(active_object=O, point_cache=O.particle_systems[Stream.name].point_cache)

		with bpy.context.temp_override(**Override):
			if O.particle_systems[Stream.name].point_cache.is_baked: bpy.ops.ptcache.free_bake()
			else: bpy.ops.ptcache.bake('INVOKE_DEFAULT', bake=True)

		SceneTools.FluidSurface.modifiers["Fluid Surface"].show_viewport = True
		return {'FINISHED'}

class BakeCache(bpy.types.Operator):
	"""Save/Delete the fluid cache for all selected objects"""
	bl_idname = "fp.bakecache"
	bl_label = "BakeCache"
	All: bpy.props.BoolProperty()
	bl_options = {'UNDO'}

	def execute(self, context):
		context.scene.FP_SceneTools.FluidSurface.modifiers["Fluid Surface"].show_viewport = False
		Baked = context.object.particle_systems[context.object.FP_ObjectTools.ActiveStream.name].point_cache.is_baked

		for O in context.scene.FP_SceneTools.AllEmitters if self.All else bpy.context.selected_objects:
			if not O.FP_ObjectTools.Enabled: continue

			for Stream in O.FP_ObjectTools.MyList:
				if Baked: ClearCache(Stream, context)
				else: StoreCache(Stream, context)

		context.scene.FP_SceneTools.FluidSurface.modifiers["Fluid Surface"].show_viewport = True
		return {'FINISHED'}

class BakeAll(bpy.types.Operator):
	"""Bake/Unbake all physics of all kinds all at once"""
	bl_idname = "fp.bakeall"
	bl_label = "BakeAll"
	End: bpy.props.IntProperty()
	Playing: bpy.props.BoolProperty()
	bl_options = {'REGISTER', 'UNDO'}

	def execute(self, context):
		context.scene.FP_SceneTools.FluidSurface.modifiers["Fluid Surface"].show_viewport = False
		Start = [context.scene.frame_end]
		End = [context.scene.frame_start]

		for O in context.scene.FP_SceneTools.AllEmitters:
			for Stream in O.FP_ObjectTools.MyList:
				ClearCache(Stream, context)
				Start.append(Stream.Start)
				End.append(Stream.Start + Stream.Duration + O.FP_ObjectTools.Lifetime)

		self.End = min(max(End), context.scene.frame_end)

		self.Playing = context.screen.is_animation_playing
		bpy.ops.screen.animation_cancel(restore_frame=False)
		bpy.ops.screen.animation_play()

		context.scene.frame_set(min(Start))

		bpy.ops.fp.recalculate()

		context.scene.FP_SceneTools.Updating = True

		wm = context.window_manager
		wm.modal_handler_add(self)

		self.report({'INFO'}, "Modal bake started")
		return {'RUNNING_MODAL'}

	def modal(self, context, event):
		if event.type in {'ESC', 'RIGHTMOUSE'}:
			self.cancel(context)
			self.report({'WARNING'}, "Modal bake cancelled")
			return {'CANCELLED'}

		if context.scene.frame_current >= self.End:
			self.finish(context)
			self.report({'INFO'}, "Modal bake finished")
			return {'FINISHED'}

		return {'RUNNING_MODAL'}

	def finish(self, context):
		context.scene.FP_SceneTools.Updating = False
		bpy.ops.screen.animation_cancel(restore_frame=False)
		context.scene.FP_SceneTools.FluidSurface.modifiers["Fluid Surface"].show_viewport = True

		for O in context.scene.FP_SceneTools.AllEmitters:
			for Stream in O.FP_ObjectTools.MyList: StoreCache(Stream, context)

		if self.Playing: bpy.ops.screen.animation_play()

	def cancel(self, context):
		context.scene.FP_SceneTools.Updating = False
		bpy.ops.screen.animation_cancel(restore_frame=False)
		context.scene.FP_SceneTools.FluidSurface.modifiers["Fluid Surface"].show_viewport = True

class FixSurface(bpy.types.Operator):
	"""Reimport the fluid surface\n\n(Note, will remove any additional modifiers on the "Fluid Surface" object,\nany changes to the "Fluid Surface" and "Fluid Render" nodegroups,\nand any changes to the "Defailt Fluid Mat" material)"""
	bl_idname = "fp.fixsurface"
	bl_label = "FixSurface"

	bl_options = {'UNDO'}

	def execute(self, context):
		MinFrame = min(min(S.Start for S in O.FP_ObjectTools.MyList) for O in bpy.context.scene.FP_SceneTools.AllEmitters) - 1 if bpy.context.scene.FP_SceneTools.AllEmitters else context.scene.frame_start
		context.scene.frame_current = min(context.scene.frame_current, int(MinFrame))

		if bpy.data.objects.get("Fluid Surface"): bpy.data.meshes.remove(bpy.data.objects["Fluid Surface"].data)

		ImportSurface(context)
		RemakeInstances(context, Refresh = True)

		return {'FINISHED'}

class RemoveAll(bpy.types.Operator):
	bl_idname = "fp.removeall"
	bl_label = "Remove All"

	bl_options = {'UNDO'}

	def execute(self, context):
		if SafeAdjust(context): return {'CANCELLED'}

		OBJTools = context.object.FP_ObjectTools
		context.scene.FP_SceneTools.Updating = True
		try:
			while OBJTools.MyList: RemoveStream(context.object, OBJTools)

			CreateLinks(context, context.object, OBJTools)
			SetEmitterVisibility(context.object, True)

			CleanupScene(context)
			RemakeInstances(context)
		finally:
			context.scene.FP_SceneTools.Updating = False
		return {'FINISHED'}


_classes = [
	AddStreamOps,
	RemoveStreamOps,
	Recalculate,
	BakeSelf,
	BakeCache,
	BakeAll,
	FixSurface,
	RemoveAll,
]
