from enum import Enum


class ModelTypes(Enum):
    MISSION_ONLY = 0
    CUSTOM_MODEL = 1
    GAZEBO_MODEL = 2
    GAZEBO_DB_MODEL = 3
