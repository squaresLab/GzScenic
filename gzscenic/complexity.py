import logging
from typing import List, Tuple, Dict, Union
import os
import attr
import yaml
import numpy as np
import matplotlib.pyplot as plt

from shapely.geometry import Polygon, LineString
from scenic.core.scenarios import Scene
from scenic.core.object_types import Object
from scenic.core.vectors import Vector

from .gazebo.model_types import ModelTypes

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class Geometry:

    def __init__(self, coords: List[Tuple[float, float]], complexity: int, obj_type:str):
        self.polygon = Polygon(coords)
        self.complexity = complexity
        self.obj_type = obj_type
        self.visited = False

    @property
    def coords(self):
        return list(self.polygon.exterior.coords)

    def to_dict(self):
        d = {'area': self.polygon.area,
             'length': self.polygon.length,
             'centroid': list(self.polygon.centroid.coords)[0],
             'minimum_clearance': self.polygon.minimum_clearance,
             'coords': self.coords,
             'complexity': self.complexity,
             'obj_type': self.obj_type
             }
        return d

    @staticmethod
    def from_dict(d):
        return Geometry(d['coords'], d['complexity'], d['obj_type'])


class Region:

    def __init__(self, shape: Union[Polygon, LineString], included_geometries: List[Geometry]):
        self.shape = shape
        self.included_geometries = included_geometries
        self._is_polygon = isinstance(shape, Polygon)

    @property
    def coords(self):
        if self._is_polygon:
            return list(self.shape.exterior.coords)
        else:
            return list(self.shape.coords)

    def to_dict(self):
        d = {'area': self.shape.area,
             'length': self.shape.length,
             'centroid': list(self.shape.centroid.coords)[0],
             'minimum_clearance': self.shape.minimum_clearance,
             'coords': self.coords,
             'included_geometries': [g.to_dict() for g in self.included_geometries]
             }
        if self._is_polygon:
            mrr = self.shape.minimum_rotated_rectangle
            d['minimum_rotated_rectangle'] = {'area': mrr.area,
                                              'coords': list(mrr.exterior.coords),
                                              'length': mrr.length,
                                              }
        return d

    @staticmethod
    def from_dict(d):
        coords = d['coords']
        if len(coords) <= 2:
            shape = LineString(coords)
        else:
            shape = Polygon(coords)
        return Region(shape, [Geometry.from_dict(g) for g in d['included_geometries']])


def reset_objects(objects: List[Geometry]) -> None:
    for o in objects:
        o.visited = False


def calculate_complexity(region: Region) -> float:
    area = region.shape.area
    if area == 0.0:
        return 0.0
    obj_area = 0.0
    for g in region.included_geometries:
        obj_area += g.polygon.area
    assert obj_area <= area
    return obj_area / area


def plot(region: Region,
         all_points: List[Tuple[float, float]]) -> float:
    ch_points = np.array(region.coords)

    all_points = np.array(all_points)
    logger.info("all_points %s %s", all_points, all_points.shape)
    logger.info("ch_points %s %s", ch_points, ch_points.shape)
    plt.plot(all_points[:,0], all_points[:,1], 'o')
    plt.plot(ch_points[:,0], ch_points[:,1], 'k-')


def scene_regions(scene: Scene) -> List[Region]:
    
    ego = scene.egoObject

    waypoints = []
    objects = []
    for obj in scene.objects:
        if obj.type == ModelTypes.MISSION_ONLY:
            if obj == ego:
                continue
            waypoints.append(obj)
        elif obj.gz_name == 'grey_wall' and obj.room_wall:
            continue
        else:
            hw, hl = obj.hw + ego.hw, obj.hl + ego.hl
            coords = [
                    obj.relativePosition(Vector(hw, hl)).coordinates,
                    obj.relativePosition(Vector(-hw, hl)).coordinates,
                    obj.relativePosition(Vector(-hw, -hl)).coordinates,
                    obj.relativePosition(Vector(hw, -hl)).coordinates
                    ]
            objects.append(Geometry(coords, obj.complexity, obj.gz_name))

    all_regions = []
    start = ego
    for end in waypoints:
        reset_objects(objects)
        all_points = [start.position.coordinates, end.position.coordinates]
        current_poly = LineString(all_points)

        while True:
            exhusted = True
            for g in objects:
                if g.visited:
                    continue
                if current_poly.intersects(g.polygon):
                    exhusted = False
                    all_points.extend(g.coords)
                    g.visited = True
            if exhusted:
                break
            new_poly = Polygon(all_points)
            current_poly = new_poly.convex_hull
        
        region = Region(current_poly, [o for o in objects if o.visited])
        all_regions.append(region)
        plot(region, all_points)
        start = end

    assert len(all_regions) == len(waypoints)

    return all_regions


def scene_complexity(scene: Scene, filename: str) -> None:

    regions = scene_regions(scene)

    with open(filename, 'w') as f:
        yaml.dump([r.to_dict() for r in regions], f)
