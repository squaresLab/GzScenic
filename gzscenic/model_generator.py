import typing as t
import importlib
import sys
import os
import collada
import pywavefront
import numpy as np
import itertools
import xml.etree.ElementTree as ET
import math as m
import pathlib
import attr

from .gazebo.model_types import ModelTypes
from .utils import handle_path, gazebo_dir_and_path, scenic_model_to_str
from scenic.core.distributions import Range
from scenic.core.specifiers import PropertyDefault


@attr.s
class ModelInfo:
    width: float = attr.ib()
    length: float = attr.ib()
    height: float = attr.ib()
    dynamic_size: bool = attr.ib()
    eq_width_length: bool = attr.ib(default=False)
    orig_scale: t.Tuple[float, float, float] = attr.ib(default=(1, 1, 1))


def Rx(theta):
    return np.matrix([[ 1, 0           , 0           ],
                     [ 0, m.cos(theta),-m.sin(theta)],
                     [ 0, m.sin(theta), m.cos(theta)]])


def Ry(theta):
    return np.matrix([[ m.cos(theta), 0, m.sin(theta)],
                     [ 0           , 1, 0           ],
                     [-m.sin(theta), 0, m.cos(theta)]])


def Rz(theta):
    return np.matrix([[ m.cos(theta), -m.sin(theta), 0 ],
                     [ m.sin(theta), m.cos(theta) , 0 ],
                     [ 0           , 0            , 1 ]])


def rotation_matrix(roll, pitch, yaw):
    return Rx(roll) * Ry(pitch) * Rz(yaw)


def load_collada_mesh_file(mesh_file_path: str):
    return collada.Collada(mesh_file_path)


def mesh_min_max_bounds_collada(mesh: collada.Collada) -> t.Tuple[np.array, np.array]:
    # Find the extrema of each components
    min_bounds = []
    max_bounds = []

    unit = 1

    if mesh.assetInfo and mesh.assetInfo.unitmeter:
        unit = float(mesh.assetInfo.unitmeter)

    for geometry in mesh.scene.objects('geometry'):
        for primitive in geometry.primitives():
            v = primitive.vertex
            min_bounds.append(v.min(axis=0))
            max_bounds.append(v.max(axis=0))

    return np.array(min_bounds) * unit, np.array(max_bounds) * unit


def load_obj_mesh_file(mesh_file_path: str):
    return pywavefront.Wavefront(mesh_file_path)


def mesh_min_max_bounds_obj(mesh: pywavefront.Wavefront) -> t.Tuple[np.array, np.array]:
    # Find the extrema of each components

    unit = 1

    vertices = np.array(mesh.vertices)
    min_bounds = [vertices.min(axis=0)]
    max_bounds = [vertices.max(axis=0)]

    return np.array(min_bounds) * unit, np.array(max_bounds) * unit


def bounding_box(min_bounds: np.array, max_bounds: np.array) -> t.Tuple[np.array, np.array, np.array]:
    
    mesh_min = min_bounds.min(axis=0)
    mesh_max = max_bounds.max(axis=0)

    # Calculate geometric properties
    geom_center = (mesh_min + mesh_max) / 2.0
    bounding_box = mesh_max - mesh_min
    extrema = np.array([mesh_min, mesh_max])
    return geom_center, bounding_box, extrema


def process_sdf(input_dir: str, sdf_file_path: str) -> ModelInfo:

    min_bounds = []
    max_bounds = []

    dynamic_size = True
    eq_width_length = False
    orig_scale = (1, 1, 1)
    sdf = ET.parse(os.path.join(input_dir, sdf_file_path))
    for collision in sdf.findall('.//collision'):
        pose = collision.find('pose')
        if pose:
            x, y, z, roll, pitch, yaw = tuple(map(float, pose.text.split(' ')))
        else:
            x, y, z, roll, pitch, yaw = 0, 0, 0, 0, 0, 0
        geometry = collision.find('geometry')
        for c in geometry.getchildren():
            if c.tag == 'empty':
                continue
            elif c.tag in ['heightmap', 'image', 'plane', 'polyline']:
                raise Exception(f'geometry {c.tag} is not supported yet')
            elif c.tag == 'mesh':
                dynamic_size = False
                uri = c.find('uri').text
                if uri.startswith('model://'):
                    uri = uri[len('model://'):]
                scale = c.find('scale')
                if scale is not None:
                    scale = tuple(map(float, scale.text.split(' ')))
                else:
                    scale = (1, 1, 1)
                path = pathlib.Path(uri)
                mesh_path = ''
                for i in range(len(path.parts)):
                    rel_path = pathlib.Path(input_dir, *path.parts[i:])
                    if rel_path.exists():
                        mesh_path = str(rel_path)
                        break
                if not mesh_path:
                    raise Exception("Could not find the mesh file")
                extension = os.path.splitext(mesh_path)[1]

                if extension == '.dae':
                    # Collada format
                    mesh = load_collada_mesh_file(mesh_path)
                    min_b, max_b = mesh_min_max_bounds_collada(mesh)
                elif extension == '.obj' or extension == '.OBJ':
                    mesh = load_obj_mesh_file(mesh_path)
                    min_b, max_b = mesh_min_max_bounds_obj(mesh)
                else:
                    raise Exception(f'Unsupported mesh format {extension}')
                # TODO Handle scale and rotation
                min_bounds.append(min_b * scale)
                max_bounds.append(max_b * scale)
                eq_width_length = True
                orig_scale = scale
                continue
            elif c.tag == 'box':
                size = c.find('size').text
                size_x, size_y, size_z = tuple(map(lambda x: float(x)/2, size.split(' ')))
                vertices = np.array([[-size_x, -size_y, -size_z],
                                     [-size_x, -size_y, size_z]])
            elif c.tag == 'cylinder' or c.tag == 'sphere':
                eq_width_length = True
                radius = float(c.find('radius').text)
                if c.tag == 'cylinder':
                    length = float(c.find('length').text)/2
                else:
                    length = radius
                vertices = np.array([[-radius, -radius, -length],
                                     [-radius, -radius, length]])
            else:
                raise Exception(f'Unknown tag {c.tag}')

            vertices = np.append(vertices, vertices * [1, -1, 1], axis=0)
            vertices = np.append(vertices, vertices * [-1, 1, 1], axis=0)
            vertices = vertices + [x, y, z]
            # apply rotation
            vertices = vertices * rotation_matrix(roll, pitch, yaw)
            min_bounds.append(vertices.min(axis=0))
            max_bounds.append(vertices.max(axis=0))
            break


    measures = (np.max(max_bounds, axis=0) - np.min(min_bounds, axis=0))[0]
    print(measures)
    return ModelInfo(measures[0],
                     measures[1],
                     measures[2],
                     dynamic_size and len(max_bounds) == 1,
                     eq_width_length,
                     orig_scale)


def to_camel_case(snake_str):
    components = snake_str.split('_')
    return ''.join(x.title() for x in components)


def to_annotations(model_desc: t.Dict[str, t.Any], input_dir: str, models_dir: str):
    typ = ModelTypes[model_desc['type']]
    name = model_desc['name']
    annotations = {'gz_name': name,
                   'type': typ,}
    if typ == ModelTypes.MISSION_ONLY:
        annotations.update({'width': model_desc.get('width', 0.00001),
                            'length': model_desc.get('length', 0.00001)})

    elif typ == ModelTypes.CUSTOM_MODEL:
        dir_path = os.path.join(input_dir, models_dir)
        dir_path = os.path.join(dir_path, name)
        url = model_desc.get('url', '')
    elif typ in [ModelTypes.GAZEBO_MODEL, ModelTypes.GAZEBO_DB_MODEL]:
        # TODO we need to download files from gazebo repo
        # and do the same as CUSTOM_MODEL
        dir_path, gazebo_db = gazebo_dir_and_path(os.path.join(input_dir, models_dir), name)
        annotations['type'] = ModelTypes.GAZEBO_DB_MODEL if gazebo_db else ModelTypes.GAZEBO_MODEL
        url = ''
    
    if typ != ModelTypes.MISSION_ONLY:
        sdf_path = handle_path(dir_path, url)
        info = process_sdf(dir_path, sdf_path)
        if not model_desc.get('dynamic_size', info.dynamic_size):
            annotations.update({'length': info.length,
                                'width': info.width,
                                'height': info.height})
        else:
            annotations.update({'length': Range(info.length/2, info.length*2),
                                'width': Range(info.width/2, info.width*2),
                                'height': Range(info.height/2, info.height*2),
                                'dynamic_size': info.dynamic_size,
                                'o_length': info.length/info.orig_scale[1],
                                'o_width': info.width/info.orig_scale[0],
                                'o_height': info.height/info.orig_scale[2]})
            if info.eq_width_length:
                annotations['width'] = PropertyDefault(('length',), {}, lambda self: self.length)

    if 'z' in model_desc:
        annotations['z'] = model_desc['z']
    if 'heading' in model_desc:
        annotations['heading'] = model_desc['heading']
    if 'dynamic_size' in model_desc:
        annotations['dynamic_size'] = model_desc['dynamic_size']
    annotations['allowCollisions'] = model_desc.get('allow_collisions', False)
    return annotations


def generate_model(model_desc: t.Dict[str, t.Any],
                   input_dir: str,
                   models_dir: t.Optional[str] = '',
                   dump_models_path: t.Optional[str] = ''):
    import gzscenic.model as base
    model_name = to_camel_case(model_desc['name'])
    print(model_name)
    annotations = to_annotations(model_desc, input_dir, models_dir)
    model = type(model_name, (base.BaseModel,), {'__module__': 'gzscenic.model', '__annotations__': annotations})
    if dump_models_path:
        model_str = scenic_model_to_str(model_name, annotations)
        with open(dump_models_path, 'a') as f:
            f.write(model_str)
    setattr(base, model_name, model)
    return model

