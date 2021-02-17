import importlib
import sys
import os

from .gazebo.model_types import ModelTypes


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

