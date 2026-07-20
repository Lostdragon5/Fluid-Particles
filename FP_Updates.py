import bpy
from .FP_Functions import print, SafeAdjust, SetStreamValues, CreateLinks, SetSurface, RemakeInstances, StoreCache, ClearCache
from .FP_VelocityCurve import RedrawCurve

def UpdateStream(self, context):
	if SafeAdjust(context): return
	context.scene.FP_SceneTools.Updating = True
	try: SetStreamValues(context, self.id_data, self.id_data.FP_ObjectTools, self)
	finally: context.scene.FP_SceneTools.Updating = False

def UpdateEmitter(self, context):
	if SafeAdjust(context): return
	context.scene.FP_SceneTools.Updating = True
	try:
		for S in self.MyList: SetStreamValues(context, self.id_data, self, S)
		RemakeInstances(context)
	finally:
		context.scene.FP_SceneTools.Updating = False

def UpdateStiffness(self, context):
	if SafeAdjust(context): return

	if self.UnlinkStiffness: self.Repulsion = self.RepulsionFactor * self.Stiffness
	else: self.RepulsionFactor = self.Repulsion / self.Stiffness

def UpdateLinks(self, context):
	if SafeAdjust(context): return
	context.scene.FP_SceneTools.Updating = True
	try: CreateLinks(context, self.id_data, self.id_data.FP_ObjectTools)
	finally: context.scene.FP_SceneTools.Updating = False

def StaticUpdate(self, context):
	for L in context.object.FP_ObjectTools.MyList:
		L.System.material = 0

def UpdateRender(self, context):
	self.System.material = 0
	self.id_data.modifiers[self.name].show_render = self.Render

def UpdatePoint(self, context):
	if SafeAdjust(context): return
	UpdatePoints(context.object.FP_ObjectTools.ActiveStream, context)

def UpdatePoints(self, context):
	SafeAdjust(context)

	self.System.frame_start = self.Start
	self.System.frame_end = self.Start + self.Duration

	if self.System.animation_data and self.System.animation_data.action:
		if bpy.app.version < (5, 0, 0): curves = self.System.animation_data.action.fcurves
		else: curves = self.System.animation_data.action.layers[0].strips[0].channelbags[0].fcurves
		for curve in [c for c in curves if c.data_path == "normal_factor"]: curves.remove(curve)

	for x, y in [(0, self.VelStartStrength)] + [(P.x, P.y) for P in self.VelPoints] + [
		(1, self.VelEndStrength)]:
		self.System.normal_factor = self.Velocity * y
		self.System.keyframe_insert("normal_factor", frame=self.Duration * x + self.Start)

	RedrawCurve()

def UpdateSurface(self, context):
	SetSurface(context)
	context.scene.FP_SceneTools.FluidSurface.modifiers["Fluid Surface"].show_viewport = True