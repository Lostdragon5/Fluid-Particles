import bpy
from abc import ABCMeta

_classes = []

class CopyBase:
	__name__: str
	PropertyClass: str
	Target: str
	ExportProperties: list

	class Copy(bpy.types.Operator):
		"""Copy current settings to all selected emitters"""
		bl_idname: str
		bl_label: str

		Target: str
		ExportProperties: list

		bl_options = {'UNDO'}

		def Extras(self, context, Target) -> dict: return {}

		def execute(self, context):
			if not context.object: return {'FINISHED'}

			Target = eval(self.Target)

			Data = {}
			for E in self.ExportProperties: Data[E] = eval(self.Target + "." + E)

			Dict = eval(context.scene.FP_SceneTools.CopyVel)
			Dict[self.bl_label] = Data | dict(Extras = self.Extras(context, Target))
			context.scene.FP_SceneTools.CopyVel = str(Dict)
			return {'FINISHED'}

	class Paste(bpy.types.Operator):
		"""Copy current settings to all selected emitters"""
		bl_idname:str
		bl_label:str

		Target: str

		bl_options = {'UNDO'}

		def Extras(self, context, Target, Extras): pass

		def execute(self, context):
			if not context.object: return {'FINISHED'}
			if not context.scene.FP_SceneTools.CopyVel: return {'FINISHED'}
			if context.scene.FP_SceneTools.CopyVel.strip() == "": return {'FINISHED'}
			print(context.scene.FP_SceneTools.CopyVel)
			Dict = eval(context.scene.FP_SceneTools.CopyVel)
			if self.bl_label not in Dict: return {'CANCELLED'}
			Data:dict = Dict[self.bl_label]
			Extras = Data.pop("Extras")

			for N,V in Data.items():
				Path:str = ".".join([self.Target, N])
				setattr(eval(Path[:Path.rfind(".")]), Path[Path.rfind(".") + 1:], V)

			self.Extras(context, eval(self.Target), Extras)

			return {'FINISHED'}

class CopySuperClass(ABCMeta):
	def __init__(cls:CopyBase,  *args, **kwargs):
		global _classes

		cls.Copy.bl_idname = f"fp.copy{cls.__name__.lower()}"
		cls.Copy.bl_label = cls.__name__
		cls.Copy.Target = cls.Target
		cls.Copy.ExportProperties = cls.ExportProperties
		_classes.append(cls.Copy)

		cls.Paste.bl_idname = f"fp.paste{cls.__name__.lower()}"
		cls.Paste.bl_label = cls.__name__
		cls.Paste.Target = cls.Target
		_classes.append(cls.Paste)

class Particle(metaclass=CopySuperClass):
	class Copy(CopyBase.Copy): pass

	class Paste(CopyBase.Paste): pass

	Target = "context.object.FP_ObjectTools"

	ExportProperties = [
		"Lifetime",
		"LifetimeRandom",
		"Size",
		"Radius",
	]

class Interaction(metaclass=CopySuperClass):
	class Copy(CopyBase.Copy): pass

	class Paste(CopyBase.Paste): pass

	Target = "context.object.FP_ObjectTools"

	ExportProperties = [
		"UnlinkStiffness",
		"Stiffness",
		"Repulsion",
		"RepulsionFactor",
		"UnlinkViscosity",
		"Viscosity",
		"StiffViscosity",
		"Density",
		"Mass",
		"Spring",
	]

class Scene(metaclass=CopySuperClass):
	class Copy(CopyBase.Copy): pass

	class Paste(CopyBase.Paste): pass

	Target = "context"

	ExportProperties = [
		"scene.FP_SceneTools.EnableCatcher",
		"scene.FP_SceneTools.CatcherHeight",
		"object.FP_ObjectTools.Gravity",
		"object.FP_ObjectTools.Forces",
		"object.FP_ObjectTools.Speed",
		"object.FP_ObjectTools.SubFrames",
	]

class Curve(metaclass=CopySuperClass):
	class Copy(CopyBase.Copy):
		def Extras(self, context, Stream): return dict(Points = [[P.x, P.y] for P in Stream.VelPoints])

	class Paste(CopyBase.Paste):
		def Extras(self, context, Stream, Extras):
			Stream.VelPoints.clear()

			for X, Y in Extras["Points"]:
				NewP = Stream.VelPoints.add()
				NewP.x = X
				NewP.y = Y

	Target = "context.object.FP_ObjectTools.ActiveStream"

	ExportProperties = [
		"VelStartStrength",
		"VelEndStrength",
	]

class Material(metaclass=CopySuperClass):
	class Copy(CopyBase.Copy):
		def Extras(self, context, SceneTools) -> dict: return dict(
			Colour = [SceneTools.Colour.r, SceneTools.Colour.g, SceneTools.Colour.b],
			Emit = [SceneTools.Emit.r, SceneTools.Emit.g, SceneTools.Emit.b],
		)
	class Paste(CopyBase.Paste):
		def Extras(self, context, SceneTools, Extras):
			SceneTools.Colour = Extras["Colour"]
			SceneTools.Emit = Extras["Emit"]

	Target = "context.scene.FP_SceneTools"
	ExportProperties = [
		"Roughness",
		"MatDensity",
		"EmitStr",
	]
