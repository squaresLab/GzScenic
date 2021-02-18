import typing as t
import importlib
import sys
import os
import collada
import numpy as np
import itertools
import xml.etree.ElementTree as ET
import math as m

from .gazebo.model_types import ModelTypes


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

    for geometry in mesh.scene.objects('geometry'):
        for primitive in geometry.primitives():
            v = primitive.vertex
            min_bounds.append(v.min(axis=0))
            max_bounds.append(v.max(axis=0))

    return np.array(min_bounds), np.array(max_bounds)


def bounding_box(min_bounds: np.array, max_bounds: np.array) -> t.Tuple[np.array, np.array, np.array]:
    
    mesh_min = min_bounds.min(axis=0)
    mesh_max = max_bounds.max(axis=0)

    # Calculate geometric properties
    geom_center = (mesh_min + mesh_max) / 2.0
    bounding_box = mesh_max - mesh_min
    extrema = np.array([mesh_min, mesh_max])
    return geom_center, bounding_box, extrema


def process_sdf(sdf_file_path: str) -> t.Tuple[float, float, float]:

    min_bounds = []
    max_bounds = []

    sdf = ET.parse(sdf_file_path)
    for collision in sdf.findall('.//collision'):
        pose = collision.find('pose').text
        x, y, z, roll, pitch, yaw = tuple(map(float, pose.split(' ')))
        geometry = collision.find('geometry')
        for c in geometry.getchildren():
            if c.tag == 'empty':
                continue
            elif c.tag in ['heightmap', 'image', 'mesh', 'plane', 'polyline']:
                raise Exception(f'geometry {c.tag} is not supported yet')
            elif c.tag == 'box':
                size = c.find('size').text
                size_x, size_y, size_z = tuple(map(lambda x: float(x)/2, size.split(' ')))
                vertices = np.array([[-size_x, -size_y, -size_z],
                                     [-size_x, -size_y, size_z]])
            elif c.tag == 'cylinder' or c.tag == 'sphere':
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
    return measures[0], measures[1], measures[2]


def to_camel_case(snake_str):
    components = snake_str.split('_')
    return ''.join(x.title() for x in components)


def to_annotations(model_desc):
    typ = ModelTypes[model_desc['type']]
    annotations = {'gz_name': model_desc['name'],
                   'type': typ,}
    if typ == ModelTypes.NO_MODEL:
        annotations.update({'width': model_desc['width'],
                            'length': model_desc['length']})

    elif typ == ModelTypes.CUSTOM_MODEL:
        # TODO we need to read .sdf file from model_desc['path']
        # and figure out the size values and whether we can
        # modify the dynamically
        pass
    elif typ == ModelTypes.GAZEBO_MODEL:
        # TODO we need to download files from gazebo repo
        # and do the same as CUSTOM_MODEL
        pass
    return annotations


def generate_model(model_desc):
    import gzscenic.model as base
    model_name = to_camel_case(model_desc['name'])
    print(model_name)
    model = type(model_name, (base.BaseModel,), {'__module__': 'gzscenic.model', '__annotations__': to_annotations(model_desc)})
    setattr(base, model_name, model)
    return model

