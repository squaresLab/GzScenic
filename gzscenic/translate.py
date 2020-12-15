"""
We want to translate a Scene
to sdf models.
"""
from typing import List, Tuple
import os
import math
import xml.etree.ElementTree as ET

from scenic.core.scenarios import Scene
from scenic.core.object_types import Object


MODELS_PATH = os.path.join(os.path.dirname(__file__), 'gazebo/models')


def process_object(obj: Object, index: int, ws_root: ET.Element) -> Tuple[str, ET.ElementTree]:
    if not hasattr(obj, 'gz_name'):
        return None, None
    name = obj.gz_name + str(index)
    obj_et = ET.parse(os.path.join(MODELS_PATH, obj.gz_name + '.xml'))
    root = obj_et.getroot().find('model')
    position_txt = " ".join([str(obj.position.x), str(obj.position.y), '0',
                            '0', '-0', str(obj.heading)])
    pose_element = root.find('pose')
    pose_element.text = position_txt
    root.set('name', name)
    include = ET.Element('include')
    uri = ET.Element('uri')
    uri.text = f'model://{name}'
    include.append(uri)
    ws_root.append(include)
    return name + '.sdf', obj_et


def scene_to_sdf(scene: Scene) -> List[Tuple[str, ET.ElementTree]]:
    workspace = ET.parse(os.path.join(MODELS_PATH, 'Workspace.xml'))
    ws_root = workspace.getroot().find('world')
    all_xmls = [('Workspace.world', workspace)]
    for i, obj in enumerate(scene.objects):
        name, obj_et = process_object(obj, i, ws_root)
        if obj_et:
            all_xmls.append((name, obj_et))
    return all_xmls
