import typing as t
import importlib
import os
import sys

from scenic.syntax.translator import ScenicLoader


def load_module(scenic_file_path: str) -> None:
        spec = importlib.util.spec_from_file_location('model', scenic_file_path, loader=ScenicLoader(os.path.abspath(scenic_file_path), os.path.basename(scenic_file_path)))
        module = importlib.util.module_from_spec(spec)
        sys.modules['gzscenic.model'] = module
        spec.loader.exec_module(module)


def gazebo_dir_and_path(models_dir: str, name: str) -> t.Tuple[str, str]:
    dir_path = os.path.join(models_dir, name)
    path = f'https://github.com/osrf/gazebo_models/trunk/{name}'
    return dir_path, path


def handle_path(dir_path: str, url: t.Optional[str] = '') -> str:
    if not os.path.exists(dir_path):
        if url.startswith('http'):
            os.system(f'svn export {url} {dir_path}')
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
