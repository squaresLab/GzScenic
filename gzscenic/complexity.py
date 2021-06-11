import logging
from typing import List, Tuple, Dict, Union
import os
import attr
import yaml
import numpy as np
import matplotlib.pyplot as plt

from shapely.geometry import Polygon, LineString, Point
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

    def __init__(self,
                 waypoints: Tuple[Point, Point],
                 shape: Union[Polygon, LineString],
                 included_geometries: List[Geometry],
                 vision_area: Polygon,
                 in_vision_objects: List[Geometry]):
        self.wps = waypoints
        self.shape = shape
        self.included_geometries = included_geometries
        self._is_polygon = isinstance(shape, Polygon)
        self.vision_area = vision_area
        self.in_vision_objects = in_vision_objects

    @property
    def coords(self):
        if self._is_polygon:
            return list(self.shape.exterior.coords)
        else:
            return list(self.shape.coords)

    def to_dict(self):
        d = {'wps': [tuple(p.coords)[0] for p in self.wps],
             'area': self.shape.area,
             'length': self.shape.length,
             'centroid': list(self.shape.centroid.coords)[0],
             'minimum_clearance': self.shape.minimum_clearance,
             'coords': self.coords,
             'vision_area': {
                 'area': self.vision_area.area,
                 'coords': list(self.vision_area.exterior.coords)
                 },
             'included_geometries': [g.to_dict() for g in self.included_geometries],
             'in_vision_objects': [g.to_dict() for g in self.in_vision_objects]
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
        vision_area = Polygon(d['vision_area']['coords'])
        wps = [Point(c) for c in d['wps']]
        return Region(wps,
                      shape,
                      [Geometry.from_dict(g) for g in d['included_geometries']],
                      vision_area,
                      [Geometry.from_dict(g) for g in d['in_vision_objects']])


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
         all_points: List[Tuple[float, float]],
         color: str) -> float:
    ch_points = np.array(region.coords)

    all_points = np.array(all_points)
    vision_points = np.array(list(region.vision_area.exterior.coords))
    #logger.info("all_points %s %s", all_points, all_points.shape)
    #logger.info("ch_points %s %s", ch_points, ch_points.shape)
    #plt.plot(all_points[:,0], all_points[:,1], 'o')
    plt.plot(ch_points[:,0], ch_points[:,1], f'{color}-')
    #plt.plot(vision_points[:,0], vision_points[:,1], f'{color}--')

def scene_regions(scene: Scene, plot_region=True) -> Tuple[List[Region], Tuple[float, float]]:
    
    ego = scene.egoObject

    waypoints = []
    objects = []
    walls = []
    wall_lengths = []
    for obj in scene.objects:
        if obj.type == ModelTypes.MISSION_ONLY:
            if obj == ego:
                continue
            waypoints.append(obj)
        elif obj.gz_name == 'grey_wall' and type(obj).__name__ == 'BorderWall':
            hw, hl = obj.hw, obj.hl
            wall_lengths.append(hl*2)
            coords = [
                    obj.relativePosition(Vector(hw, hl)).coordinates,
                    obj.relativePosition(Vector(-hw, hl)).coordinates,
                    obj.relativePosition(Vector(-hw, -hl)).coordinates,
                    obj.relativePosition(Vector(hw, -hl)).coordinates
                    ]
            walls.append(Geometry(coords, obj.complexity, obj.gz_name))
        else:
            #hw, hl = obj.hw + ego.hw, obj.hl + ego.hl
            hw, hl = obj.hw + 0.05, obj.hl + 0.05
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
        reset_objects(objects + walls)
        all_points = [start.position.coordinates, end.position.coordinates]
        wps = (Point(start.position.coordinates), Point(end.position.coordinates))
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
        
        vision_area = current_poly.buffer(2) # 2 meters around the region
        in_vision_objects = [o for o in objects if not o.visited and vision_area.intersects(o.polygon)]
        in_vision_objects.extend([w for w in walls if vision_area.intersects(w.polygon)])

        region = Region(wps,
                        current_poly,
                        [o for o in objects if o.visited],
                        vision_area,
                        in_vision_objects)
        all_regions.append(region)
        colors = ['k', 'g']
        if plot_region:
            plot(region, all_points, colors[len(all_regions)-1])
        start = end

    assert len(all_regions) == len(waypoints)

    return all_regions, (min(wall_lengths), max(wall_lengths))


def scene_complexity(scene: Scene, filename: str, plot_region=True) -> None:

    regions, (w, l) = scene_regions(scene, plot_region)

    with open(filename, 'w') as f:
        yaml.dump({
            'length': l,
            'width': w,
            'regions': [r.to_dict() for r in regions]
            }, f)


def load_regions_from_file(filename: str) -> Tuple[List[Region], float, float]:

    with open(filename, 'r') as f:
        all_regions = yaml.load(f, Loader=yaml.FullLoader)

    return [Region.from_dict(d) for d in all_regions['regions']], all_regions['width'], all_regions['length']
