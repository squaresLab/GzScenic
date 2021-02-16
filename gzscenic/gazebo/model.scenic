"""Scenic model for Mars rover scenarios in Webots."""
from .model_types import ModelTypes

class BasicObject:
    type: ModelTypes.NO_MODEL
    dynamic_size: False


class Goal(BasicObject):
    """Flag indicating the goal location."""
    width: 0.14
    length: 0.14
    heading: Range(0, 360) deg
    gz_name: 'waypoint'


class TurtleBot(BasicObject):
    """The TurtleBot."""
    width: 0.14
    length: 0.14
    height: 0.14
    position: Point in workspace
    gz_name: 'turtlebot3'


class Table(BasicObject):
    """A wooden table."""
    width: 0.8
    length: 1.5
    height: 0.3
    heading: Range(0, 360) deg
    gz_name: 'Table'
    type: ModelTypes.CUSTOM_MODEL


class ConstructionCone(BasicObject):
    """A construction cone"""
    width: 0.40
    length: 0.40
    height: 0.40
    type: ModelTypes.GAZEBO_MODEL
    gz_name: 'construction_cone'
    heading: Range(0, 360) deg
    position: Point in workspace


class Box(BasicObject):
    """A simple box"""
    width: Range(0.1, 1.5)
    length: Range(0.1, 1.5)
    height: 0.5
    type: ModelTypes.CUSTOM_MODEL
    dynamic_size: True
    gz_name: 'Box'
    heading: Range(0, 360) deg
    position: Point in workspace


class Wall(BasicObject):
    """A simple wall"""
    heading: Range(0, 360) deg
    width: 0.1
    height: 1.0
    gz_name: 'grey_wall'
    type: ModelTypes.GAZEBO_MODEL
    dynamic_size: True


def create_room(length, width, x=0, y=0, sides='NSWE'):
    l2 = length/2-0.1
    w2 = width/2-0.1
    if 'N' in sides:
        Wall at x @ l2, facing 90 deg, with length (width-0.1)
    if 'S' in sides:
        Wall at x @ -l2, facing 90 deg, with length (width-0.1)
    if 'E' in sides:
        Wall at w2 @ y, facing 0 deg, with length (length-0.4)
    if 'W' in sides:
        Wall at -w2 @ y, facing 0 deg, with length (length-0.4)

class Room(Workspace):

    def __init__(self, region):
        super().__init__(region)
        create_room(self.region.length, self.region.width)



# Set up workspace
width = 5
length = 10
heading = 0
workspace = Room(RectangularRegion(0 @ 0, heading, width, length))

