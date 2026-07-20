import bpy
from .FP_Functions import SafeAdjust, QuickCheck, GetTools, print
_BRUSH_NAME = "FPCurveUI"
_CURVE_NAME = "curve" if bpy.app.version < (5,0,0) else "curve_size"
_LAST_CURVE = []

@bpy.app.handlers.persistent
def RedrawCurve(*_):
	global _LAST_CURVE
	if QuickCheck(bpy.context, True): return
	Stream = GetTools(bpy.context)[2]
	if not Stream: return

	#Only rebuild the curve UI when the stream's velocity data actually changed.
	Sig = [Stream.id_data.name, Stream.name, Stream.VelStartStrength, Stream.VelEndStrength] + [(P.x, P.y) for P in Stream.VelPoints]
	if Sig == _LAST_CURVE: return

	brush,c = get_curve()
	rebuild_curve(None, bpy.context)
	getattr(brush, _CURVE_NAME).curves[0].points.update()
	getattr(brush, _CURVE_NAME).update()
	_LAST_CURVE = Sig

def UpdateCurve():
	if QuickCheck(bpy.context, True): return
	Stream = GetTools(bpy.context)[2]
	brush, c = get_curve()

	points = [(p.location[0], p.location[1]) for p in c.points]

	Skippable = len(points) == len(Stream.VelPoints) +2
	if Stream.VelStartStrength != points[0][1]: Skippable = False
	elif Stream.VelEndStrength != points[-1][1]: Skippable = False
	if Skippable:
		for i, P in enumerate(Stream.VelPoints):
			if P.x != points[i+1][0]: Skippable = False; break
			if P.y != points[i+1][1]: Skippable = False; break

	if Skippable: return
	SafeAdjust(bpy.context)
	bpy.context.scene.FP_SceneTools.Updating = True
	try:
		Stream.VelStartStrength = points.pop(0)[1]
		Stream.VelEndStrength = points.pop(-1)[1]

		Stream.VelPoints.clear()

		for x, y in points:
			P = Stream.VelPoints.add()
			P.x = x
			P.y = y
	except: pass
	bpy.context.scene.FP_SceneTools.Updating = False

def subscribe_to_curve_changes(brush):
	"""Subscribe to curve changes using msgbus."""
	def on_curve_msgbus_notify(): UpdateCurve()

	bpy.msgbus.clear_by_owner("FPCurveBus")
	bpy.msgbus.subscribe_rna(key=brush, owner="FPCurveBus", args=(), notify=on_curve_msgbus_notify)

def get_curve():
	global _LAST_CURVE
	brush = bpy.data.brushes.get(_BRUSH_NAME)

	if not brush:
		brush = bpy.data.brushes.new(name=_BRUSH_NAME, mode='SCULPT')
		subscribe_to_curve_changes(brush)
		_LAST_CURVE = [] #Fresh brush starts with a default curve, so force the next redraw to sync it.

	return brush, getattr(brush, _CURVE_NAME).curves[0]

def rebuild_curve(self, context):
	if QuickCheck(context, True): return
	Stream = GetTools(bpy.context)[2]

	brush, c = get_curve()

	A = [(P.location[0], P.location[1]) for P in c.points[1:-1]]
	B = [(P.x, P.y) for P in Stream.VelPoints]

	i = 1
	for _ in range(len(c.points) - 2):
		if tuple(c.points[i].location) in B: i += 1
		else: c.points.remove(c.points[i])

	for P in Stream.VelPoints:
		if (P.x, P.y) in A: continue
		c.points.new(P.x, P.y)

	c.points[0].location[0] = 0
	c.points[0].location[1] = Stream.VelStartStrength
	c.points[-1].location[0] = 1
	c.points[-1].location[1] = Stream.VelEndStrength

	for p in c.points: p.handle_type = 'AUTO_CLAMPED'

def SortPoints(Points):
	Buffer = [(p.x, p.y) for p in sorted(Points, key=lambda p: p.x)]
	if Buffer == [(p.x, p.y) for p in Points]: return
	Points.clear()

	for x, y in Buffer:
		P = Points.add()
		P.x = x
		P.y = y

class AddPoint(bpy.types.Operator):
	bl_idname = "fp.addpoint"
	bl_label = "Add Point"
	index: bpy.props.IntProperty()
	dir: bpy.props.IntProperty()

	bl_options = {'UNDO'}

	def execute(self, context):
		Stream = context.object.FP_ObjectTools.ActiveStream

		SortPoints(Stream.VelPoints)

		Refs = [(0, Stream.VelStartStrength)] + [(P.x, P.y) for P in Stream.VelPoints] + [(1, Stream.VelEndStrength)]

		i1 = self.index
		i2 = i1 - 1 if self.dir == 1 else i1 + 1

		P = Stream.VelPoints.add()
		P.x = (Refs[i1][0] + Refs[i2][0]) * 0.5
		P.y = (Refs[i1][1] + Refs[i2][1]) * 0.5

		SortPoints(Stream.VelPoints)

		return {'FINISHED'}

class RemovePoint(bpy.types.Operator):
	bl_idname = "fp.removepoint"
	bl_label = "Remove Point"
	index: bpy.props.IntProperty()

	bl_options = {'UNDO'}

	def execute(self, context):
		Stream = context.object.FP_ObjectTools.ActiveStream
		SortPoints(Stream.VelPoints)
		Stream.VelPoints.remove(self.index)
		Stream.Velocity *= 1

		return {'FINISHED'}

_classes = [
	AddPoint,
	RemovePoint,
]

_registerFunctions = [
	lambda:([bpy.app.handlers.depsgraph_update_post.remove(h) for h in list(bpy.app.handlers.depsgraph_update_post) if h.__name__ == "RedrawCurve"]),
	lambda:bpy.app.handlers.depsgraph_update_post.append(RedrawCurve),
]
_unregisterFunctions = [
	lambda:([bpy.app.handlers.depsgraph_update_post.remove(h) for h in list(bpy.app.handlers.depsgraph_update_post) if h.__name__ == "RedrawCurve"]),
	lambda:bpy.msgbus.clear_by_owner("FPCurveBus"),
]