from gzscenic.gazebo.model_types import ModelTypes

# Set up workspace
width = 5
length = 10
heading = 0
workspace = Workspace(RectangularRegion(0 @ 0, heading, width, length))



class BaseModel:
    type: ModelTypes.NO_MODEL
    dynamic_size: False
    width: 0.0
    length: 0.0
    position: Point in workspace
    gz_name: 'base'
    heading: Range(0, 360) deg
    z: 0.0

