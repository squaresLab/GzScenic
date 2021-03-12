import logging
from typing import List, Tuple, Dict, Union
import os
import attr
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

    def __init__(self, coords: List[Tuple[float, float]]):
        self.polygon = Polygon(coords)
        self.coords = coords
        self.visited = False


def reset_objects(objects: List[Geometry]) -> None:
    for o in objects:
        o.visited = False


def calculate_complexity(convex_hull: Union[Polygon, LineString],
                         objects: List[Geometry]) -> float:
    area = convex_hull.area
    if area == 0.0:
        return 0.0
    obj_area = 0.0
    for g in objects:
        if g.visited:
            obj_area += g.polygon.area
    assert obj_area <= area
    return obj_area / area


def plot(convex_hull: Union[Polygon, LineString],
         all_points: List[Tuple[float, float]]) -> float:
    ch_points = []
    if isinstance(convex_hull, Polygon):
        for p in convex_hull.boundary.coords:
            ch_points.append(tuple(p))
    else: 
        for p in convex_hull.coords:
            ch_points.append(tuple(p))
    ch_points = np.array(ch_points)

    all_points = np.array(all_points)
    logger.info("all_points %s %s", all_points, all_points.shape)
    logger.info("ch_points %s %s", ch_points, ch_points.shape)
    plt.plot(all_points[:,0], all_points[:,1], 'o')
    plt.plot(ch_points[:,0], ch_points[:,1], 'k-')


def scene_complexity(scene: Scene) -> float:
    
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
            objects.append(Geometry(coords))

    complexities = []
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
        
        complexities.append(calculate_complexity(current_poly, objects))
        plot(current_poly, all_points)
        start = end

    assert len(complexities) == len(waypoints)
    logger.info("Complexities: %s", complexities)

    return max(complexities)

