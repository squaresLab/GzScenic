"""
We want to translate a Scene
to sdf models.
"""
import logging
from typing import List, Tuple, Dict
import os
import math
import xml.etree.ElementTree as ET
from tempfile import mkstemp
import wget
import shutil
import yaml
import attr

from scenic.core.scenarios import Scene
from scenic.core.object_types import Object

from .gazebo.model_types import ModelTypes
from .utils import gazebo_dir_and_path, handle_path

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'gazebo/model.config')


@attr.s
class ObjectInfo:
    name = attr.ib(type=str)
    orig_dir = attr.ib(type=str, default='')
    orig_sdf_path = attr.ib(type=str, default='')
    new_sdf_path = attr.ib(type=str, default='')


def generate_include(obj: Object, model_name: str, name: str) -> ET.Element:
    include = ET.Element('include')
    uri = ET.Element('uri')
    uri.text = f'model://{model_name}'
    include.append(uri)
    position_txt = " ".join([str(obj.position.x), str(obj.position.y), str(obj.z),
                            '0', '-0', str(obj.heading)])
    pose_element = ET.Element('pose')
    pose_element.text = position_txt
    include.append(pose_element)
    name_element = ET.Element('name')
    name_element.text = name
    include.append(name_element)
    return include


def process_object(obj: Object,
                   index: int,
                   ws_root: ET.Element,
                   input_dir: str,
                   models_dir: str,
                   ) -> ObjectInfo:
    if obj.type == ModelTypes.MISSION_ONLY:
        return None
    name = obj.gz_name + str(index)
    if not obj.dynamic_size:
        model_name = obj.gz_name
    else:
        model_name = name
    ws_root.append(generate_include(obj, model_name, name))

    models_dir = os.path.join(input_dir, models_dir)
    if obj.type == ModelTypes.CUSTOM_MODEL:
        filedir = os.path.join(models_dir, obj.gz_name)
        path = handle_path(filedir)
        filepath = os.path.join(filedir, path)
    elif (obj.type == ModelTypes.GAZEBO_DB_MODEL and obj.dynamic_size) \
        or obj.type == ModelTypes.GAZEBO_MODEL:
        filedir, _ = gazebo_dir_and_path(models_dir, obj.gz_name)
        path = handle_path(filedir)
        filepath = os.path.join(filedir, path)
    else:
        filedir = ''
        filepath = ''

    if obj.dynamic_size:
        model_et = ET.parse(filepath)
        model = model_et.getroot()
#        size_text = f'{obj.width} {obj.length} {obj.height}'
        for c in model.findall('.//geometry/*'):
            if c.tag == 'mesh':
                print(f'orig: {obj.o_length} {obj.o_width}')
                print(f'now: {obj.length} {obj.width}')
                scale = ' '.join([str(obj.width/obj.o_width),
                                  str(obj.length/obj.o_length),
                                  str(obj.height/obj.o_height)])
                scale_node = c.find('scale')
                if scale_node is None:
                    scale_node = ET.Element('scale')
                    c.append(scale_node)

                scale_node.text = scale
            elif c.tag == 'box':
                size = c.find('size')
                size.text = f'{obj.width} {obj.length} {obj.height}'
            elif c.tag in ['cylinder', 'sphere']:
                radius = c.find('radius')
                radius.text = str(obj.length/2)

        model.find('./model').set('name', model_name)
        _, tf = mkstemp(dir='/tmp/', suffix='.sdf')
        model_et.write(tf)
        return ObjectInfo(model_name, filedir, filepath, tf)
    return ObjectInfo(model_name, filedir, filepath) 


def scene_to_sdf(scene: Scene,
                 input_dir: str,
                 empty_world: str,
                 models_dir: str,
                 output: str) -> None:

    if os.path.exists(output):
        shutil.rmtree(output)
    os.makedirs(output)


    no_models = {}
    workspace = ET.parse(os.path.join(input_dir, empty_world))
    ws_root = workspace.getroot().find('world')
    model_files = {}
    for i, obj in enumerate(scene.objects):
        if obj.type == ModelTypes.MISSION_ONLY:
            pose = {'x': obj.position.x,
                    'y': obj.position.y,
                    'z': obj.z,
                    'heading': obj.heading}
            if obj.gz_name in no_models:
                no_models[obj.gz_name].append(pose)
            else:
                no_models[obj.gz_name] = [pose]
        else:
            obj_info = process_object(obj, i, ws_root, input_dir, models_dir)
            if obj_info and obj_info.name not in model_files:
                model_files[obj_info.name] = obj_info
    workspace.write(os.path.join(output, os.path.basename(empty_world)))

    if model_files:
        models_path = os.path.join(output, 'models')
        os.makedirs(models_path, exist_ok=True)
        for model_name, obj_info in model_files.items():
            model_dir = os.path.join(models_path, model_name)
            if obj_info.orig_dir:
                shutil.copytree(obj_info.orig_dir, model_dir)
                conf_file = os.path.join(model_dir, 'model.config')
                if not os.path.exists(conf_file):
                    shutil.copyfile(CONFIG_PATH, conf_file)
                config_et = ET.parse(conf_file)
                conf_name = config_et.getroot().find('./name')
                conf_name.text = model_name
                config_et.write(conf_file)
            if obj_info.new_sdf_path:
                sdf_path = os.path.join(model_dir, os.path.relpath(obj_info.orig_sdf_path, obj_info.orig_dir))
                shutil.copyfile(obj_info.new_sdf_path, sdf_path)

    if no_models:
        pose_file = os.path.join(output, 'poses.yaml')
        with open(pose_file, 'w') as f:
            yaml.dump(no_models, f)

