import bpy, os
from bl_operators.presets import AddPresetBase
from bpy.path import display_name_from_filepath
from bpy.utils import preset_paths
from abc import ABCMeta

class ExecutePresetWithIndex(bpy.types.Operator):
	bl_idname = "fp.execute_preset"
	bl_label = "Apply Preset (Indexed)"

	bl_options = {'UNDO'}

	filepath: bpy.props.StringProperty()

	def execute(self, context):
		if len(bpy.context.object.FP_ObjectTools.MyList) == 0: return {'FINISHED'}

		with open(self.filepath, "r", encoding="utf-8") as f: text = f.read()

		exec(text, {"bpy": bpy, "context": context})
		return {'FINISHED'}
	
_classes = [ExecutePresetWithIndex]

class PresetBase:
	__name__:str
	PropertyClass:str
	ExportProperties:list

	class AddPreset(AddPresetBase, bpy.types.Operator):
		bl_idname:str
		bl_label:str
		preset_menu:str
		preset_subdir:str
		PropertyClass:str
		ExportProperties:list

		bl_options = {'UNDO'}
		
		@property
		def preset_values(self):
			return [f"bpy.context.{self.PropertyClass}.{Prop}" for Prop in self.ExportProperties]

	class PresetsMenu(bpy.types.Menu):
		bl_label:str
		preset_subdir:str
		Button_Name:str
		preset_operator = "fp.execute_preset"

		def draw(self, context):
			layout = self.layout
			
			layout.operator(self.Button_Name, text="New Preset", icon='ADD')
			
			layout.separator()
			
			presets = []
			for dir in preset_paths(self.preset_subdir):
				presets.extend(os.path.join(dir, file) for file in os.listdir(dir) if os.path.isfile(os.path.join(dir, file)))
			
			if not presets:
				layout.label(text="No Presets")
				return

			for filepath in sorted(presets):
				op = layout.operator(self.preset_operator, text=display_name_from_filepath(filepath))
				op.filepath = filepath

class PresetSuperClass(ABCMeta):
	def __init__(cls:PresetBase,  *args, **kwargs):
		global _classes

		cls.AddPreset.bl_idname = f"fp.add{cls.__name__.lower()}preset"
		cls.AddPreset.bl_label = f"Add {cls.__name__} Preset"
		cls.AddPreset.PropertyClass = cls.PropertyClass
		cls.AddPreset.ExportProperties = cls.ExportProperties
		cls.AddPreset.preset_subdir = os.path.join("Fluid Particles", cls.__name__)
		cls.AddPreset.preset_menu = f"fp.{cls.__name__.lower()}menu"
		_classes.append(cls.AddPreset)

		cls.PresetsMenu.bl_idname = f"fp.{cls.__name__.lower()}menu"
		cls.PresetsMenu.bl_label = f"FP {cls.__name__} Presets"
		cls.PresetsMenu.Button_Name = f"fp.add{cls.__name__.lower()}preset"
		cls.PresetsMenu.preset_subdir = os.path.join("Fluid Particles", cls.__name__)
		_classes.append(cls.PresetsMenu)

class Stream(metaclass = PresetSuperClass):
	class AddPreset(PresetBase.AddPreset): pass
	class PresetsMenu(PresetBase.PresetsMenu): pass
	PropertyClass = "object.FP_ObjectTools.ActiveStream"
	ExportProperties = [
		"LinkType",
		"Count",
		"Duration",
		"Velocity",
	]

class Particle(metaclass = PresetSuperClass):
	class AddPreset(PresetBase.AddPreset): pass
	class PresetsMenu(PresetBase.PresetsMenu): pass
	PropertyClass = "object.FP_ObjectTools"
	ExportProperties = [
		"Lifetime",
		"LifetimeRandom",
		"Size",
		"Radius",
	]

class Interaction(metaclass = PresetSuperClass):
	class AddPreset(PresetBase.AddPreset): pass
	class PresetsMenu(PresetBase.PresetsMenu): pass
	PropertyClass = "object.FP_ObjectTools"
	ExportProperties = [
		"Mass",
		"Density",
		"Spring",
		"Stiffness",

		"UnlinkStiffness",
		"Repulsion",
		"RepulsionFactor",
		
		"UnlinkViscosity",
		"Viscosity",
		"StiffViscosity",
	]

class Scene(metaclass = PresetSuperClass):
	class AddPreset(PresetBase.AddPreset): pass
	class PresetsMenu(PresetBase.PresetsMenu): pass
	PropertyClass = "object.FP_ObjectTools"
	ExportProperties = [
		"Gravity",
		"Speed",
		"Forces",
		"SubFrames",
	]

class Velocity(metaclass = PresetSuperClass):
	class AddPreset(PresetBase.AddPreset): pass
	class PresetsMenu(PresetBase.PresetsMenu): pass
	PropertyClass = "object.FP_ObjectTools.ActiveStream"
	ExportProperties = [
		"VelStartStrength",
		"VelPoints",
		"VelEndStrength",
	]

class Material(metaclass = PresetSuperClass):
	class AddPreset(PresetBase.AddPreset): pass
	class PresetsMenu(PresetBase.PresetsMenu): pass
	PropertyClass = "scene.FP_SceneTools"
	ExportProperties = [
		"Colour",
		"Roughness",
		"MatDensity",
		"Emit",
		"EmitStr",
	]
