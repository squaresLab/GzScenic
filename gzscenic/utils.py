import typing as t
import importlib
import os
import sys
import urllib
import requests

from scenic.syntax.translator import ScenicLoader
from scenic.core.specifiers import PropertyDefault


def load_module(scenic_file_path: str) -> None:
        spec = importlib.util.spec_from_file_location('model', scenic_file_path, loader=ScenicLoader(os.path.abspath(scenic_file_path), os.path.basename(scenic_file_path)))
        module = importlib.util.module_from_spec(spec)
        sys.modules['gzscenic.model'] = module
        spec.loader.exec_module(module)


def build_file_tree(parent_path: str, file_tree: t.Dict, url: str):

    for f in file_tree:
        path = os.path.join(parent_path, f['name'])
        children = f.get('children', None)
        if children:
            os.makedirs(path)
            build_file_tree(path, children, url)
        else:
            extension = os.path.splitext(path)[1]
            if extension in ['.jpg', '.png']:
                continue
            res = requests.get(url + f['path'])
            res.raise_for_status()
            with open(path, 'wb') as f:
                f.write(res.content)


def gazebo_dir_and_path(models_dir: str, name: str) -> t.Tuple[str, bool]:
    dir_path = os.path.join(models_dir, name)
    osrf_models = 'https://github.com/osrf/gazebo_models/tree/master/'
    quoted_name = urllib.parse.quote(name)
    res = requests.get(osrf_models + quoted_name)
    gazebo_db = res.status_code == 200
    if os.path.exists(dir_path):
        return dir_path, gazebo_db
    if gazebo_db:
        path = f'https://github.com/osrf/gazebo_models/trunk/{name}'
        os.system(f'svn export {path} {dir_path}')
        return dir_path, gazebo_db
    ignition_api = "https://fuel.ignitionrobotics.org/1.0/"
    res = requests.get(ignition_api + 'models', params={'q': name})
    res.raise_for_status()
    the_model = None
    for e in res.json():
        if e['name'] == name:
            the_model = e
            break
    if not the_model:
        raise Exception(f"Model {name} not found.")
    owner = urllib.parse.quote(the_model['owner'])
    res = requests.get(ignition_api + f'{owner}/models/{quoted_name}/{{version}}/{quoted_name}')
    res.raise_for_status()
    the_model = res.json()
    version = the_model['version']
    files_url = ignition_api + f"{owner}/models/{quoted_name}/{version}/files"
    res = requests.get(files_url)
    res.raise_for_status()
    os.makedirs(dir_path)
    build_file_tree(dir_path, res.json()['file_tree'], files_url)
    return dir_path, gazebo_db


def handle_path(dir_path: str, url: t.Optional[str] = '') -> str:
    if not os.path.exists(dir_path):
        if url.startswith('http'):
            os.system(f'wget {url} {dir_path}')
        else:
            raise Exception(f"{dir_path} does not exist")
    for root, subFolders, files in os.walk(dir_path):
        for f in files:
            if f == 'model.sdf':
                if root != dir_path:
                    rel_path = os.path.rel_path(root, dir_path)
                    return os.path.join(rel_path, f)
                else:
                    return f
    raise Exception("No models.sdf in the directory")


def scenic_model_to_str(model_name: str, annotations: t.Dict[str, t.Any]) -> str:

    s = f'class {model_name}(BaseModel):\n'
    for k, v in annotations.items():
        if type(v) == str:
            s += f'    {k}: "{v}"\n'
        elif isinstance(v, PropertyDefault):
            props = tuple(v.requiredProperties)
            s += f'    {k}: self.{str(props[0])}\n'
        else:
            s += f'    {k}: {str(v)}\n'
    return s
