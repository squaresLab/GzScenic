"""Scenic model for Mars rover scenarios in Webots."""

# Set up workspace
width = 5
length = 5
workspace = Workspace(RectangularRegion(0 @ 0, 0, width, length))

# types of objects

class Goal:
    """Flag indicating the goal location."""
    width: 0.3
    length: 0.3

class TurtleBot:
    """The TurtleBot."""
    width: 0.14
    length: 0.14
    height: 0.14
    position: Point in workspace

class Table:
    """A wooden table."""
    width: 0.8
    length: 1.5
    height: 0.3
    heading: Range(0, 360) deg
    gz_name: 'Table'
