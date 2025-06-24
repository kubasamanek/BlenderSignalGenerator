bl_info = {
    "name": "Generátor návěstidel",
    "description": "Generátor návěstidel podle zadaných parametrů.",
    "author": "Jakub Šamánek",
    "version": (1, 0, 0),
    "blender": (3, 6, 0),
    "warning": "",
    "wiki_url": "http://edux.fit.cvut.cz/courses/BI-PGA",
    "category": "Object"
}

import bpy
from bpy.props import *
import math
import sys
import os
import requests

ZAVORA_OBJ_NAME = "ZAVORA"
NAVESTIDLO_OBJ_NAME = "NAVESTIDLO"

KRAKOREC_BOX = "KrakorecBox"

###################################################

class CloudObjectLoader(bpy.types.Operator):
    bl_idname = "object.load_vmck_object"
    bl_label = "Import from VMCK"
    bl_options = {'REGISTER', 'UNDO'}

    model_endpoint: bpy.props.StringProperty()
    object_name: bpy.props.StringProperty()
    
    filepath: bpy.props.StringProperty(default="//VMCK_objects/tmp/")

    def execute(self, context):
        absolute_path = bpy.path.abspath("//VMCK_objects/tmp/")
        if not os.path.exists(f"{absolute_path}{self.object_name}.fbx"):
            print(f"Downloading from {self.model_endpoint}")
            response = requests.get(self.model_endpoint, stream=True)
            file_name = self.model_endpoint.split('/')[-1].split('?')[0]

            os.makedirs(absolute_path, exist_ok=True)
            print(f"Connection response: {response}")

            if response.status_code == 200:
                # Write the file data to a local file
                with open(f"{absolute_path}{self.object_name}.fbx", 'wb') as file:
                    print(f"Opened {absolute_path}/{self.object_name}.fbx")
                    for chunk in response.iter_content(chunk_size=8192):
                        file.write(chunk)
            else:
                print("Failed to retrieve the file, check the URL.")
                return {'CANCELLED'}
        else:
            print(f"Object {self.object_name} already present in the folder, just import.")
        
        # Import the object
        bpy.ops.import_scene.fbx(filepath=f"{absolute_path}{self.object_name}.fbx")
        new_obj = bpy.data.objects.get(self.object_name)
        if new_obj:
            # Move them away
            new_obj.location = (10,10,-10)
        return {'FINISHED'}
        

#####################################################

# Method for exporting an object
def export_object(obj_name, file_path):
    bpy.ops.object.select_all(action='DESELECT')
    obj = bpy.data.objects.get(obj_name)
    if obj:
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        if file_path.lower().endswith('.fbx'):
            bpy.ops.export_scene.fbx(filepath=file_path, use_selection=True)
        elif file_path.lower().endswith('.obj'):
            bpy.ops.export_scene.obj(filepath=file_path, use_selection=True)
        else:
            print("Unsupported file format")
    else:
        print(f"Object '{obj_name}' not found for export.")

# Clears all objects in scene with exceptions
def clear_scene_except(names):
    names.add('Sun')
    names.add('Camera')
    names.add('Sketchfab_model')
    names.add('Plane')
    names.add('Plane.001')
    for obj in bpy.context.scene.objects:
        if obj.name not in names:
            bpy.data.objects.remove(obj, do_unlink=True)

# Creates copy of an object in scene
def duplicate_object(object_name):
    collection = bpy.data.collections.get("ToDuplicate")
    original_obj = bpy.data.objects.get(object_name)
    if original_obj is not None:
        # Duplicate the object (but not its data)
        new_obj = original_obj.copy()
        new_obj.data = original_obj.data.copy()
        bpy.context.collection.objects.link(new_obj)
        bpy.ops.object.select_all(action='DESELECT')
        new_obj.select_set(True)
        bpy.context.view_layer.objects.active = new_obj
        return new_obj
    else:
        print(f"Object '{object_name}' not found.")
        return None

# Create basic color material 
def create_material(name, color):
    # Create a new material
    mat = bpy.data.materials.new(name=name)
    mat.diffuse_color = color
    return mat

# Assign the material to the given object
def assign_material(obj, mat):
    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)
        
def assign_material_by_name(obj, mat_name):
    mat = bpy.data.materials.get(mat_name)
    assign_material(obj, mat)
        
# Joins list of objects
def join_objects(to_join):
    bpy.ops.object.select_all(action='DESELECT')
    # Select the objects and set the last one as the active object
    for obj_name in to_join:
        obj = bpy.data.objects.get(obj_name.name)
        if obj and obj.type == 'MESH':
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj 

    # Join the objects
    if bpy.context.view_layer.objects.active:
        joined = bpy.ops.object.join()
        
    return joined

# Rotates active object around axis
def rotate_object(axis, angle):
    bpy.context.view_layer.objects.active.rotation_euler[axis] -= angle
       
# Properties of the signal
class TrainSignalProperties(bpy.types.PropertyGroup):
    type: bpy.props.EnumProperty(
        name="Typ",
        description="Vyber typ návěstidla",
        items=[
            ('HLAVNI', "Hlavní", "Hlavní návěstidlo."),
            ('SERADOVACI', "Seřaďovací", "Seřaďovací návěstidlo"),
        ],
        default='HLAVNI',
    )
    
    construction: bpy.props.EnumProperty(
        name="Konstrukce",
        description="Vyber typ konstrukce",
        items=[
            ('STOZAR', "Stožárová", "Stožárová konstrukce"),
            ('TRPASLIK', "Trpasličí", "Trpasličí konstrukce"),
            ('KRAKOREC', "Krakorcová", "Krakorcová konstrukce"),
            ('PREJEZD', "Přejezd", "Přejezdová konstrukce"),
        ],
        default='STOZAR',
    )
    
    number_of_lights: bpy.props.IntProperty(
        name="Number of Lights",
        description="Number of lights on the traffic light.",
        min=1, max=10, default=1,
    )

    pole_height: bpy.props.FloatProperty(
        name="Pole Height",
        description="Height of the traffic light pole.",
        min=4.0, max=10.0, default=2.0,
    )
    
    construction_height: bpy.props.IntProperty(
        name="Construction height.",
        description="Construction height.",
        min=3, max=10, default=5,
    )
    
    number_of_lightboxes: bpy.props.IntProperty(
        name="Number of lightboxes",
        description="Number of lightboxes on the construction.",
        min=1, max=3, default=2,
    )
    
    bridge_length: bpy.props.FloatProperty(
        name="Bridge length",
        description="Length of the bridge.",
        min=4, max=16, default=9,
    )
    
    base_size: bpy.props.FloatProperty(
        name="Base size",
        description="Size of the light base",
        min=0.5, max=3.0, default=1.0,
    )
    
    switch_side: bpy.props.BoolProperty(
        name="Switch side of lightboxes",
        description="Switch side of lightboxes.",
    )
    
    vicekolejny_prejezd: bpy.props.BoolProperty(
        name="Multi-rail passing",
        description="Is the passing multi rail?",
    )
    
    delka_zavory: bpy.props.FloatProperty(
        name="Latch length",
        description="Length of the latch.",
        min=5.0, max=10.0, default=10.0,
    )
    
    
    
# Generation class
class GenerateTrainSignal(bpy.types.Operator):
    bl_idname = "object.generate_signal"
    bl_label = "Generuj návěstidlo"
    bl_options = {'REGISTER', 'UNDO'}
    
    # Constant values
    light_height = 0.37
    light_spacing = 0.15
    
    first_light_y_offset = 0.25
    
    backing_width = 0.8
    backing_depth = 0.3
    backing_height = 0
    
    base_height = 0.6
    base_width = 0.9
    
    pole_radius = 0.05
    
    # Execute the generation
    def execute(self, context):
        props = context.scene.train_traffic_lights_props
        
        # Load needed parts 
        self.load_objects_at_start()
        
        self.base_width = props.base_size
        self.base_height = props.base_size * (2/3)
        
        # Call the right method based on construction type
        if props.construction == 'TRPASLIK':
            self.generate_trpaslik(props)
        if props.construction == 'STOZAR':
            self.generate_stozar(props)
        if props.construction == 'KRAKOREC':
            self.generate_krakorec(props)
        if props.construction == 'PREJEZD':
            self.generate_prejezd(props)
        
        return {'FINISHED'}
    
    # Loads all neccesary objects for the generation
    def load_objects_at_start(self):
        model_data = {
            "1onVBlUfPfCtdQWjRm4z8EliknktxWS1L": "LightObject",
            "1HG4A2J52MZBOa3FrGZ4ByPFt7FRZMuVE" : "PrejezdBox",
            "1OCvQgEzYHSsyzRzwQizWBHfnahuFox31" : "KrakorecBox",
            "1yj6ldjYt749mpeLcEnyy-HJIuYg75amQ" : "Holder",
            "11aBF_ABv2z6CkqayyanjLlDuKjBktAUJ" : "DoubleCross",
            "1_FncyLtXxTX-hoOGi2mAYSIp6M8k-kB9" : "Cross",
        }

        prefix = "https://drive.google.com/uc?export=download&id="
        existing_objects = set(obj.name for obj in bpy.data.objects)
        print(set(obj.name for obj in bpy.data.objects))
        clear_scene_except(set(name for endpoint, name in model_data.items()))

        for endpoint, name in model_data.items():
            if name not in existing_objects:
                print(f"Importing {name}")
                bpy.ops.object.load_vmck_object(model_endpoint=prefix + endpoint, object_name=name)
            else:
                print(f"Object named {name} already exists in the scene. Skipping import.")

    # Generate the base for the signal
    def generate_base(self, coords):
        # Create base
        bpy.ops.mesh.primitive_cube_add(size=1, location=coords)
        base = bpy.context.object
        base.scale = (self.base_width / 2, self.base_width, self.base_height / 2)
        
        # Create and assign grey material to the base
        grey_mat = create_material("GreyMaterial", (0.1, 0.1, 0.1, 1)) 
        assign_material(base, grey_mat)
        return base
    
    # Generate the light box
    def generate_light_box(self, props, z_offset, x_offset = 0, y_offset = 0):
        to_join = []
        
        # Calculate light offset
        first_light_y_offset = self.first_light_y_offset
        light_offset = (self.light_height + self.light_spacing) 
        
        # Duplicate and position lights
        # TODO: import the light from VMCKI
        original_light = bpy.data.objects.get("LightObject")
        if original_light is not None:
            for i in range(props.number_of_lights):
                new_light = original_light.copy()
                new_light.data = original_light.data.copy()
                bpy.context.collection.objects.link(new_light)
                new_light.location = (x_offset, y_offset, first_light_y_offset + z_offset + i * light_offset)
                new_light.name = f"TrafficLight_{i+1}"
                
                to_join.append(new_light)
        else:
            print("LightObject not found in the scene")
        
        # Generate the backing for the lights
        backing_height = props.number_of_lights * (self.light_height + self.light_spacing) + first_light_y_offset
        
        if(props.construction == 'STOZAR'):
            pole_height = props.pole_height
        else:
            pole_height = 0
            
        backing_location = (x_offset, y_offset + self.backing_depth / 2,  z_offset + (backing_height / 2))
        backing = self.generate_backing(props, backing_location, backing_height)
        to_join.append(backing) 
        
        light_box = join_objects(to_join)
        lb = bpy.context.object
        
        # Create and assign grey material to the lightbox
        black_mat = create_material("BlackMaterial", (0.0, 0.0, 0.0, 1))
        assign_material(lb, black_mat)
        
        return light_box
    
    # Backing generation
    def generate_backing(self, props, coords, height):
        # Calculate the total height of the lights and the total spacing
        bpy.ops.mesh.primitive_cube_add(size=1, location=coords)
        backing = bpy.context.object
        backing.scale = (self.backing_width / 2, self.backing_depth / 2, height)
        return backing
    
    # Generate pole object for the pole light
    def generate_pole(self, props, location, pole_radius):
        height = props.pole_height
        bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=pole_radius, location=location)
        pole = bpy.context.object
        pole.scale.z = height / 2
        
        white_mat = create_material("WhiteMaterial", (1, 1, 1, 1))
        assign_material(pole, white_mat)
        return pole

    # Generate trpaslik type
    def generate_trpaslik(self, props):
        
        z_offset = self.base_height / 4
        base = self.generate_base((0, 0, z_offset))
        
        self.generate_light_box(props, self.base_height / 2)
        light_box = bpy.context.object
        
        rotate_object(0, math.radians(10))
        
        join_objects([base, light_box])
        active_obj = bpy.context.active_object
        active_obj.name = NAVESTIDLO_OBJ_NAME
        
    def create_striped_material(self, obj):
        mat = bpy.data.materials.new(name="StripedMaterial")
        obj.data.materials.append(mat)
        
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        
        nodes.clear()

        # Create necessary nodes
        material_output = nodes.new(type='ShaderNodeOutputMaterial')
        bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
        checker = nodes.new(type='ShaderNodeTexChecker')  # Checker texture node

        # Set up the checker texture
        checker.inputs[1].default_value = [1,1,1,1]
        checker.inputs[2].default_value = [1,0,0,1]

        # Link nodes
        texcoord = nodes.new(type='ShaderNodeTexCoord')
        mapping = nodes.new(type='ShaderNodeMapping')
        mat.node_tree.links.new(bsdf.inputs['Base Color'], checker.outputs['Color'])
        mat.node_tree.links.new(material_output.inputs['Surface'], bsdf.outputs['BSDF'])
        mat.node_tree.links.new(mapping.inputs['Vector'], texcoord.outputs['Generated'])
        mat.node_tree.links.new(checker.inputs['Vector'], mapping.outputs['Vector'])
        
        mapping.inputs['Scale'].default_value[0] = 1.0
        mapping.inputs['Scale'].default_value[1] = 0.0
        mapping.inputs['Scale'].default_value[2] = 0.0
        
        return mat
        
    def generate_prejezd(self, props):
        z_offset = self.base_height / 4
        base = self.generate_base((0, 0, z_offset))
        
        pole = self.generate_pole(props, (0, 0, self.base_height / 2 + props.pole_height / 2), self.pole_radius * 2)
        
        duplicate_object("PrejezdBox")
        box = bpy.context.active_object
        box_z_offset = self.base_height / 2 + props.pole_height - 2
        box.location = (0, -4 * self.pole_radius, box_z_offset)
        
        if props.vicekolejny_prejezd:
            duplicate_object("DoubleCross")
        else:
            duplicate_object("Cross")
        
        cross = bpy.context.active_object
        cross.location = (0, -3 * self.pole_radius, box_z_offset + 1)
            
        duplicate_object("Holder")
        holder = bpy.context.active_object
        holder.location = (self.pole_radius, 0, self.base_height)
        
        bpy.ops.mesh.primitive_cube_add()
        holder_box = bpy.context.active_object
        holder_box.location = holder.location
        holder_box.scale /= 2
        holder_box.location.x += holder_box.scale.x
        grey_mat = create_material("GreyMat", (0.11, 0.11, 0.11, 1))
        assign_material(holder_box, grey_mat)
        
        bpy.ops.mesh.primitive_plane_add(location=(0, 0, 0), scale=(1, 1, 1))
        zavora = bpy.context.active_object
        bpy.ops.object.modifier_add(type='SOLIDIFY')
        bpy.ops.object.modifier_apply(modifier="Solidify")
        rotate_object(0, math.radians(90))
        zavora.location.z = holder.location.z
        zavora.scale.y = 0.2
        zavora.scale.x = props.delka_zavory
        zavora.location.x = zavora.location.x - zavora.scale.x
        striped_mat = self.create_striped_material(zavora)
        assign_material(zavora, striped_mat)
        
        join_objects([zavora, holder])
        zavora = bpy.context.active_object
        zavora.name = ZAVORA_OBJ_NAME
        
        bpy.context.scene.cursor.location = holder.location
        bpy.ops.object.origin_set(type='ORIGIN_CURSOR', center='MEDIAN')
        
        start_frame = 1  
        end_frame = 120   
        
        zavora.keyframe_insert(data_path="rotation_euler", frame=start_frame)
        
        rotate_object(1, math.radians(-90))
        
        zavora.keyframe_insert(data_path="rotation_euler", frame=end_frame)
        
        rotate_object(1, math.radians(90))
        
        join_objects([base, pole, cross, box, holder_box])
        active_obj = bpy.context.active_object
        active_obj.name = NAVESTIDLO_OBJ_NAME
        
        
    # Generate stozar type
    def generate_stozar(self, props):
        
        z_offset = self.base_height / 4
        base = self.generate_base((0, 0, z_offset))
        
        pole = self.generate_pole(props, (0, 0, self.base_height / 2 + props.pole_height / 2), self.pole_radius)
        
        self.generate_light_box(props, self.base_height / 2 + props.pole_height)
        
        light_box = bpy.context.object
        light_box.location.y -= self.backing_depth / 2
        
        join_objects([base, pole, light_box])
        active_obj = bpy.context.active_object
        active_obj.name = NAVESTIDLO_OBJ_NAME
        
    def create_fence_poles(self, height, thickness, z_coord, x_coord, y_coord, bridge, bridge_length, space_between, spacing):
        bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, z_coord))
        fence_stick = bpy.context.object
        fence_stick.scale[0] = thickness
        fence_stick.scale[1] = thickness
        fence_stick.scale[2] = height
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        
        fence_stick.location.x += x_coord
        fence_stick.location.y -= y_coord
        
        bpy.ops.object.modifier_add(type='MIRROR')
        bpy.context.object.modifiers["Mirror"].mirror_object = bridge
        bpy.context.object.modifiers["Mirror"].use_axis[0] = True
        
        bpy.ops.object.modifier_add(type='ARRAY')
        bpy.context.object.modifiers["Array"].fit_type = 'FIT_LENGTH'
        bpy.context.object.modifiers["Array"].fit_length = bridge_length
        
        bpy.context.object.modifiers["Array"].relative_offset_displace[0] = 0
        bpy.context.object.modifiers["Array"].relative_offset_displace[1] = spacing
        
        bpy.ops.object.modifier_apply(modifier="Array")
        bpy.ops.object.modifier_apply(modifier="Mirror")
        
        return fence_stick
        
    def create_fence_planks(self, height, thickness, z_coord, x_coord, y_coord, sticking_out, first_offset, bridge, bridge_length, v_spacing): 
        bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, z_coord))
        fence_vertical = bpy.context.object
        fence_vertical.scale[0] = thickness
        fence_vertical.scale[1] = bridge_length + sticking_out
        fence_vertical.scale[2] = thickness
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        
        fence_vertical.location.x += x_coord
        fence_vertical.location.y += y_coord
        
        bpy.ops.object.modifier_add(type='MIRROR')
        bpy.context.object.modifiers["Mirror"].mirror_object = bridge
        bpy.context.object.modifiers["Mirror"].use_axis[0] = True
        
        bpy.ops.object.modifier_add(type='ARRAY')
        bpy.context.object.modifiers["Array"].fit_type = 'FIT_LENGTH'
        bpy.context.object.modifiers["Array"].fit_length = height - first_offset
        
        bpy.context.object.modifiers["Array"].relative_offset_displace[0] = 0
        bpy.context.object.modifiers["Array"].relative_offset_displace[2] = v_spacing
        
        bpy.ops.object.modifier_apply(modifier="Array")
        bpy.ops.object.modifier_apply(modifier="Mirror")
        
        return fence_vertical
        
        
    # Generate krakorec type
    def generate_krakorec(self, props):
        box = duplicate_object(KRAKOREC_BOX)
        box_height = 1.5
        box.location = (0, 0, box_height / 2 + 0.05)
        
        # Select the box
        bpy.ops.object.select_all(action='DESELECT')
        box.select_set(True)
        bpy.context.view_layer.objects.active = box
        
        # Setup array modifier
        bpy.ops.object.modifier_add(type='ARRAY')
        bpy.context.object.modifiers["Array"].relative_offset_displace[0] = 0
        bpy.context.object.modifiers["Array"].relative_offset_displace[1] = 1
        bpy.context.object.modifiers["Array"].count = props.construction_height
        
        bpy.ops.object.modifier_apply(modifier="Array")

        # Most
        bridge_height = 0.3
        bridge_width = 2
        bridge_length = props.bridge_length
        bridge_z_coordinate = props.construction_height * box_height + bridge_height / 2
        bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, bridge_z_coordinate))
        bridge = bpy.context.object
        bridge.scale[0] = bridge_width
        bridge.scale[1] = bridge_length
        bridge.scale[2] = bridge_height
        
        bridge.location.y += bridge_length / 2 - box_height / 2
        
        # Fence
        fence_height = 1.7
        fence_thickness = 0.1
        fence_z_coordinate = bridge_z_coordinate + fence_height / 2 + bridge_height / 2
        
        fence_poles = self.create_fence_poles(
            fence_height, 
            fence_thickness, 
            fence_z_coordinate, 
            bridge_width / 2 - fence_thickness / 2,
            box_height / 2 - fence_thickness / 2,
            bridge,
            bridge_length,
            space_between = 8, 
            spacing = 7
            )

        first_plank_offset = 0.3
        fence_sticking_out = 0.4
        
        fence_planks = self.create_fence_planks(
            fence_height, 
            fence_thickness / 2, 
            bridge_z_coordinate + bridge_height / 2 + first_plank_offset,
            bridge_width / 2 - fence_thickness / 2,
            bridge_length / 2 - box_height / 2 - fence_sticking_out / 4,
            fence_sticking_out,
            first_plank_offset,
            bridge,
            bridge_length,
            v_spacing = 10
        )
        
        
        # Material
        assign_material_by_name(box, "KrakorecMaterial")
        assign_material_by_name(bridge, "KrakorecMaterial")
        assign_material_by_name(fence_poles, "KrakorecMaterial")
        assign_material_by_name(fence_planks, "KrakorecMaterial")

        # Lights 
        light_z_coordinate = fence_z_coordinate
        backing_height = props.number_of_lights * (self.light_height + self.light_spacing) + self.first_light_y_offset
        first_lightbox_offset = 1
        lights = []
        
        switch_index = 1
        if props.switch_side:
            switch_index = -1
        for i in range(props.number_of_lightboxes):    
            y = (bridge_length) / props.number_of_lightboxes * i + first_lightbox_offset 
            self.generate_light_box(props, light_z_coordinate - backing_height / 2, (box_height / 2 + self.backing_width / 2) * switch_index, y)
            bpy.context.object.rotation_euler[2] = 1.5708 * switch_index
            light_box = bpy.context.object
            lights.append(light_box)
        
        to_join = [box, bridge, fence_poles, fence_planks]
        to_join.extend(lights)
        join_objects(to_join)  
        active_obj = bpy.context.active_object
        active_obj.name = NAVESTIDLO_OBJ_NAME

# Panel class
class TrainSignalPanel(bpy.types.Panel):
    bl_label = "Train Traffic Lights Generator"
    bl_idname = "OBJECT_PT_train_traffic_lights"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Tool'

    def draw(self, context):
        layout = self.layout
        props = context.scene.train_traffic_lights_props

        #layout.prop(props, "type")
        layout.prop(props, "construction")
        if props.construction != 'PREJEZD':
            layout.prop(props, "number_of_lights")
        
        if props.construction != 'KRAKOREC':
            layout.prop(props, "base_size")
        
        # Conditionally display the pole height property
        if props.construction == 'STOZAR' or props.construction == 'PREJEZD':
            layout.prop(props, "pole_height")
        elif props.construction == 'KRAKOREC':
            layout.prop(props, "construction_height")
            layout.prop(props, "number_of_lightboxes")
            layout.prop(props, "bridge_length")
            layout.prop(props, "switch_side")
        
        if props.construction == 'PREJEZD':
            layout.prop(props, "delka_zavory")
            layout.prop(props, "vicekolejny_prejezd")
            
        layout.operator(GenerateTrainSignal.bl_idname)

# Classes to register
classes = [CloudObjectLoader, TrainSignalProperties, GenerateTrainSignal, TrainSignalPanel]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)  
    bpy.types.Scene.train_traffic_lights_props = bpy.props.PointerProperty(type=TrainSignalProperties)

def unregister():
    # Unregister the property
    del bpy.types.Scene.train_traffic_lights_props
    # Unregister each class in reverse order
    for cls in reversed(classes):
        #bpy.utils.unregister_class(cls)
        print("unreg")
    
def main_cli():
    required_number_of_args = 0
    args = sys.argv[sys.argv.index("--") + 1:]  
    
    # Set the properties based on the arguments
    props = bpy.context.scene.train_traffic_lights_props
    props.type = args[0]  
    props.construction = args[1] 
    props.number_of_lights = int(args[2])
    if(props.construction != "KRAKOREC"):
        props.base_size = float(args[3])
    if(props.construction == "STOZAR"):
        props.pole_height = float(args[4])
    if(props.construction == "KRAKOREC"):
        props.construction_height = int(args[3])
        props.number_of_lightboxes = int(args[4])
        props.bridge_length = int(args[5])
        props.switch_side = bool(args[6])
    if(props.construction == 'PREJEZD'):
        props.base_size = float(args[2])
        props.pole_height = float(args[3])
        props.delka_zavory = float(args[4])
        props.vicekolejny_prejezd = bool(args[5])
            
    bpy.ops.object.generate_signal()

    generated_obj_name = NAVESTIDLO_OBJ_NAME
    props = bpy.context.scene.train_traffic_lights_props
    if props.construction == 'PREJEZD':
        bpy.ops.object.select_all(action='DESELECT')
        objs = [generated_obj_name, ZAVORA_OBJ_NAME]
        for obj_name in objs:
            obj = bpy.data.objects.get(obj_name)
            if obj:
                obj.select_set(True)

        bpy.ops.export_scene.fbx(filepath=args[-1], use_selection=True)    
    else:
        export_object(generated_obj_name, args[-1])


if __name__ == "__main__":
    register()
    if "--" in sys.argv:
        main_cli() 
