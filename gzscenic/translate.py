"""
We want to translate a Scene
to sdf models.
"""
import logging
from typing import List, Tuple
import os
import math
import xml.etree.ElementTree as ET
from tempfile import mkstemp
import wget
import shutil
import yaml

from scenic.core.scenarios import Scene
from scenic.core.object_types import Object

from .gazebo.model_types import ModelTypes

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

MODELS_PATH = os.path.join(os.path.dirname(__file__), 'gazebo/models')
CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'gazebo/model.config')


def generate_include(obj: Object, model_name: str, name: str) -> ET.Element:
    include = ET.Element('include')
    uri = ET.Element('uri')
    uri.text = f'model://{model_name}'
    include.append(uri)
    position_txt = " ".join([str(obj.position.x), str(obj.position.y), '-1',
                            '0', '-0', str(obj.heading)])
    pose_element = ET.Element('pose')
    pose_element.text = position_txt
    include.append(pose_element)
    name_element = ET.Element('name')
    name_element.text = name
    include.append(name_element)
    return include


def process_object(obj: Object, index: int, ws_root: ET.Element) -> Tuple[str, str]:
    if obj.type == ModelTypes.NO_MODEL:
        return '', ''
    name = obj.gz_name + str(index)
    if not obj.dynamic_size:
        model_name = obj.gz_name
    else:
        model_name = name
    ws_root.append(generate_include(obj, model_name, name))

    if obj.type == ModelTypes.CUSTOM_MODEL:
        filepath = os.path.join(MODELS_PATH, obj.gz_name + '.sdf')
    elif obj.type == ModelTypes.GAZEBO_MODEL and obj.dynamic_size:
        filepath = os.path.join('/tmp/', name + '.sdf')
        url = f'https://raw.githubusercontent.com/osrf/gazebo_models/master/{obj.gz_name}/model.sdf'
        wget.download(url, filepath)
    else:
        filepath = ''

    if obj.dynamic_size:
        model_et = ET.parse(filepath)
        model = model_et.getroot()
        # TODO: assuming it's always a single box
        size_text = f'{obj.width} {obj.length} {obj.height}'
        for s in model.findall('.//geometry/box/size'):
            s.text = size_text
        # end of TODO
        model.find('./model').set('name', model_name)
        _, tf = mkstemp(dir='/tmp/', suffix='.sdf')
        model_et.write(tf)
        return model_name, tf
    return model_name, filepath


def scene_to_sdf(scene: Scene, output: str) -> None:

    if os.path.exists(output):
        shutil.rmtree(output)
    os.makedirs(output)


    no_models = {}
    workspace = ET.parse(os.path.join(MODELS_PATH, 'Workspace.sdf'))
    ws_root = workspace.getroot().find('world')
    model_files = {}
    for i, obj in enumerate(scene.objects):
        if obj.type == ModelTypes.NO_MODEL:
            if obj.gz_name in no_models:
                no_models[obj.gz_name].append({'x': obj.position.x,
                                               'y': obj.position.y,
                                               'z': 0.0,
                                               'heading': obj.heading})
            else:
                no_models[obj.gz_name] = [{'x': obj.position.x,
                                           'y': obj.position.y,
                                           'z': 0.0,
                                           'heading': obj.heading}]
        else:
            model_name, filepath = process_object(obj, i, ws_root)
            if filepath and model_name not in model_files:
                model_files[model_name] = filepath
    workspace.write(os.path.join(output, 'workspace.world'))

    if model_files:
        models_path = os.path.join(output, 'models')
        os.makedirs(models_path, exist_ok=True)
        config_et = ET.parse(CONFIG_PATH)
        conf_name = config_et.getroot().find('./name')
        for model_name, filepath in model_files.items():
            model_dir = os.path.join(models_path, model_name)
            os.makedirs(model_dir)
            conf_name.text = model_name
            config_et.write(os.path.join(model_dir, 'model.config'))
            shutil.copyfile(filepath, os.path.join(model_dir, 'model.sdf'))

    if no_models:
        pose_file = os.path.join(output, 'poses.yaml')
        with open(pose_file, 'w') as f:
            yaml.dump(no_models, f)

