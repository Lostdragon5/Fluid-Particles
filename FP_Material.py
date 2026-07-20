import bpy
from .FP_Functions import print, Append, SetInput

def MaterialToGroup(Material):
	group = bpy.data.node_groups.new(f"{Material.name} (FP Copy)", "ShaderNodeTree")
	group.nodes.clear()
	group.links.clear()
	group.interface.clear()

	Nodes = {}

	for N in Material.node_tree.nodes:
		if N.bl_idname == "ShaderNodeOutputMaterial":
			Nodes[N] = group.nodes.new("NodeGroupOutput")
			Nodes[N].location = N.location.copy()

			for i,I in enumerate(N.inputs):
				if len(I.links) == 0 and i == 1: continue
				if i > 1: continue
				S = group.interface.new_socket(name=I.name, in_out='OUTPUT')
				S.socket_type = I.bl_idname

			continue

		Nodes[N] = group.nodes.new(N.bl_idname)

		for i, P in enumerate(N.bl_rna.properties):
			try: setattr(Nodes[N], P.identifier, getattr(N, P.identifier))
			except: pass

		for i, S in enumerate(N.inputs):
			try: Nodes[N].inputs[i].default_value = S.default_value
			except: pass

		if N.type == 'VALTORGB':
			while True:
				try: Nodes[N].color_ramp.elements.remove(Nodes[N].color_ramp.elements[0])
				except: break

			Nodes[N].color_ramp.color_mode = N.color_ramp.color_mode
			Nodes[N].color_ramp.interpolation = N.color_ramp.interpolation

			for i, E in enumerate(N.color_ramp.elements):
				try: E2 = Nodes[N].color_ramp.elements[i]
				except: E2 = Nodes[N].color_ramp.elements.new(E.position)
				E2.position = E.position
				E2.color = E.color
				E2.alpha = E.alpha

	for link in Material.node_tree.links:
		try:
			group.links.new(
				Nodes[link.from_node].outputs[[o for o in link.from_node.outputs].index(link.from_socket)],
				Nodes[link.to_node].inputs[[i for i in link.to_node.inputs].index(link.to_socket)]
			)
		except: pass

	return group

_MatSig = None

@bpy.app.handlers.persistent
def UpdateFluidMaterial(scene, _):
	global _MatSig
	SceneTools = scene.FP_SceneTools
	if not SceneTools.FluidSurface:	return
	if SceneTools.Matting: return
	if SceneTools.Material: return
	Emitters = SceneTools.AllEmitters
	if len(Emitters) == 0: return

	#Skip the (expensive) node tree rebuild when nothing that feeds it has changed.
	#Emitters using their own custom material always rebuild, so edits to that material keep syncing live.
	Custom = False
	Sig = [bpy.data.materials.get("Default Fluid Mat") is not None]
	for O in Emitters:
		if len(O.data.materials) == 0 or not O.data.materials[0]: return
		M = O.data.materials[0]
		if "Fluid Viz" not in M.name: Custom = True
		T = O.FP_ObjectTools
		Sig.append((O.name, M.name, tuple(T.Colour), T.Roughness, T.MatDensity, tuple(T.Emit), T.EmitStr,
			tuple(S.Instance.name if S.Instance else "" for S in T.MyList)))

	if not Custom and Sig == _MatSig: return

	SceneTools.Matting = True

	if not bpy.data.materials.get("Default Fluid Mat"):
		SaveActive = bpy.context.object
		SaveSelected = bpy.context.selected_objects
		Append("Material", "Default Fluid Mat")
		if SaveActive: bpy.context.view_layer.objects.active = SaveActive
		for O in SaveSelected: O.select_set(True)

	if not bpy.data.node_groups.get("Default Fluid"):
		SaveActive = bpy.context.object
		SaveSelected = bpy.context.selected_objects
		Append("NodeTree", "Default Fluid")
		if SaveActive: bpy.context.view_layer.objects.active = SaveActive
		for O in SaveSelected: O.select_set(True)

	Mat = bpy.data.materials["Default Fluid Mat"]
	Nodes = Mat.node_tree.nodes
	Links = Mat.node_tree.links
	[bpy.data.node_groups.remove(N.node_tree) for N in Nodes if N.bl_idname == "ShaderNodeGroup" and N.node_tree and N.node_tree.name != "Default Fluid"]
	Nodes.clear()

	Mats = []
	Objects = []
	for O in Emitters:
		if len(O.data.materials) == 0 or not O.data.materials[0]:
			SceneTools.Matting = False
			return

		M = O.data.materials[0]
		if M not in Mats:
			Mats.append(M)
			Objects.append([O.FP_ObjectTools, None if "Fluid Viz" in O.data.materials[0].name else MaterialToGroup(M)])

		for Stream in O.FP_ObjectTools.MyList:
			if not Stream.Instance:
				SceneTools.Matting = False
				return
			try:
				if bpy.app.version < (5, 2, 0): Stream.Instance.modifiers["InstanceColour"]["Socket_3"] = Mats.index(M)
				else: Stream.Instance.modifiers["InstanceColour"].properties.inputs.Socket_3.value = Mats.index(M)
			except: pass
			Stream.Instance.data.update()


	OutputE = Nodes.new("ShaderNodeOutputMaterial")
	OutputE.location = 160, 120
	OutputE.target = "EEVEE"
	for S in OutputE.inputs: S.hide = True

	Output = Nodes.new("ShaderNodeOutputMaterial")
	Output.location = 160, 40
	Output.target = "CYCLES"
	for S in Output.inputs: S.hide = True

	LinkedMats = []
	LastAdd = None
	for i, O in enumerate(Objects):
		Attr = Nodes.new("ShaderNodeAttribute")
		Attr.location = i * -160, 220
		for S in Attr.outputs: S.hide = True
		Attr.attribute_name = f"Fluid {i}"

		Add = Nodes.new("ShaderNodeAddShader")
		Add.location = i * -160, 100
		Add.hide = True

		Mix = Nodes.new("ShaderNodeMixShader")
		Mix.location = i * -160, 60
		Mix.hide = True

		Links.new(Mix.outputs[0], Add.inputs[1])
		Links.new(Attr.outputs[2], Mix.inputs[0])

		Group = Nodes.new("ShaderNodeGroup")
		Group.location = i * -160, 20
		if O[1]:
			Group.node_tree = O[1]
		else:
			Group.node_tree = bpy.data.node_groups["Default Fluid"]
			Group.inputs["Base Color"].default_value = list(O[0].Colour) + [1]
			Group.inputs["Roughness"].default_value = O[0].Roughness
			Group.inputs["Alpha"].default_value = O[0].MatDensity
			Group.inputs["Emission Color"].default_value = list(O[0].Emit) + [1]
			Group.inputs["Emission Strength"].default_value = O[0].EmitStr

		Links.new(Group.outputs[0], Mix.inputs[2])
		LinkedMats.append(Group)

		if LastAdd:
			Links.new(Add.outputs[0], LastAdd.inputs[0])
		else:
			Links.new(Add.outputs[0], Output.inputs[0])
			Links.new(Add.outputs[0], OutputE.inputs[0])

		if len(Group.outputs) == 2: Links.new(Group.outputs[1], Output.inputs[1])

		LastAdd = Add

	for n in Nodes: n.select = False

	_MatSig = Sig
	SceneTools.Matting = False

_registerFunctions = [
	lambda:([bpy.app.handlers.depsgraph_update_post.remove(h) for h in list(bpy.app.handlers.depsgraph_update_post) if h.__name__ == "UpdateFluidMaterial"]),
	lambda:bpy.app.handlers.depsgraph_update_post.append(UpdateFluidMaterial),
]
_unregisterFunctions = [
	lambda:([bpy.app.handlers.depsgraph_update_post.remove(h) for h in list(bpy.app.handlers.depsgraph_update_post) if h.__name__ == "UpdateFluidMaterial"]),
]