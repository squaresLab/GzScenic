from gzscenic.gazebo.model_types import ModelTypes



class BaseModel:
    type: ModelTypes.NO_MODEL
    dynamic_size: False
    width: 0.0
    length: 0.0
    height: 0.0
    position: Point in workspace
    gz_name: 'base'
    heading: Range(0, 360) deg
    z: 0.0


class Wall(BasicObject):
    """A simple wall"""
    heading: Range(0, 360) deg
    length: Range(0.01, workspace.region.length*2)
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


# Set up workspace
width = 5
length = 10
heading = 0
workspace = Workspace(RectangularRegion(0 @ 0, heading, width, length))


