"""Scenic model for Mars rover scenarios in Webots."""
from .model_types import ModelTypes

class BasicObject:
    type: ModelTypes.NO_MODEL
    dynamic_size: False


class Goal(BasicObject):
    """Flag indicating the goal location."""
    width: 0.14
    length: 0.14
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


class Room(Workspace):

    def __init__(self, region):
        super().__init__(region)
        l2 = self.region.length/2-0.1
        w2 = self.region.width/2-0.1
        Wall at 0 @ l2 relative to self.region.position, facing 90 deg, with length (self.region.width-0.1)
        Wall at 0 @ -l2 relative to self.region.position, facing 90 deg, with length (self.region.width-0.1)
        Wall at w2 @ 0 relative to self.region.position, facing 0 deg, with length (self.region.length-0.4)
        Wall at -w2 @ 0 relative to self.region.position, facing 0 deg, with length (self.region.length-0.4)

# Set up workspace
width = 5
length = 10
heading = 0
workspace = Room(RectangularRegion(0 @ 0, heading, width, length))

