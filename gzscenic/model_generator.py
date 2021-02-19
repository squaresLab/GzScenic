import typing as t
import importlib
import sys
import os
import collada
import numpy as np
import itertools
import xml.etree.ElementTree as ET
import math as m
import pathlib
import attr

from .gazebo.model_types import ModelTypes
from .utils import handle_path, gazebo_dir_and_path
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


def load_mesh_file(mesh_file_path: str):
    return collada.Collada(mesh_file_path)


def mesh_min_max_bounds(mesh: collada.Collada) -> t.Tuple[np.array, np.array]:
    # Find the extrema of each components
    min_bounds = []
    max_bounds = []

    unit = 1

    if mesh.assetInfo:
        unit = float(mesh.assetInfo.unitmeter)

    for geometry in mesh.scene.objects('geometry'):
        for primitive in geometry.primitives():
            v = primitive.vertex
            min_bounds.append(v.min(axis=0))
            max_bounds.append(v.max(axis=0))

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
                mesh = load_mesh_file(mesh_path)
                min_b, max_b = mesh_min_max_bounds(mesh)
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
                     len(max_bounds) == 1,
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
    if typ == ModelTypes.NO_MODEL:
        annotations.update({'width': model_desc['width'],
                            'length': model_desc['length']})

    elif typ == ModelTypes.CUSTOM_MODEL:
        dir_path = os.path.join(input_dir, models_dir)
        dir_path = os.path.join(dir_path, name)
        url = model_desc.get('url', '')
    elif typ == ModelTypes.GAZEBO_MODEL:
        # TODO we need to download files from gazebo repo
        # and do the same as CUSTOM_MODEL
        dir_path, url = gazebo_dir_and_path(os.path.join(input_dir, models_dir), name)
    
    if typ != ModelTypes.NO_MODEL:
        sdf_path = handle_path(dir_path, url)
        info = process_sdf(dir_path, sdf_path)
        if not info.dynamic_size:
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
    return annotations


def generate_model(model_desc: t.Dict[str, t.Any], input_dir: str, models_dir: t.Optional[str] = ''):
    import gzscenic.model as base
    model_name = to_camel_case(model_desc['name'])
    print(model_name)
    model = type(model_name, (base.BaseModel,), {'__module__': 'gzscenic.model', '__annotations__': to_annotations(model_desc, input_dir, models_dir)})
    setattr(base, model_name, model)
    return model

