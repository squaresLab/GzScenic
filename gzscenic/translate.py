"""
We want to translate a Scene
to sdf models.
"""
import logging
from typing import List, Tuple
import os
import math
import xml.etree.ElementTree as ET

from scenic.core.scenarios import Scene
from scenic.core.object_types import Object

from .gazebo.model_types import ModelTypes

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

MODELS_PATH = os.path.join(os.path.dirname(__file__), 'gazebo/models')


def process_object(obj: Object, index: int, ws_root: ET.Element) -> str:
    if obj.type == ModelTypes.NO_MODEL:
        return None
    name = obj.gz_name + str(index)
    include = ET.Element('include')
    uri = ET.Element('uri')
    uri.text = f'model://{obj.gz_name}'
    include.append(uri)
    position_txt = " ".join([str(obj.position.x), str(obj.position.y), '0',
                            '0', '-0', str(obj.heading)])
    pose_element = ET.Element('pose')
    pose_element.text = position_txt
    include.append(pose_element)
    name_element = ET.Element('name')
    name_element.text = name
    include.append(name_element)
    ws_root.append(include)
    if obj.type == ModelTypes.CUSTOM_MODEL:
        return os.path.join(MODELS_PATH, obj.gz_name + '.sdf')
    return None


def scene_to_sdf(scene: Scene) -> Tuple[ET.ElementTree, List[str]]:
    workspace = ET.parse(os.path.join(MODELS_PATH, 'Workspace.sdf'))
    ws_root = workspace.getroot().find('world')
    model_files = []
    for i, obj in enumerate(scene.objects):
        filename = process_object(obj, i, ws_root)
        if filename:
            model_files.append(filename)
    return workspace, model_files
