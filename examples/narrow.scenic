from gzscenic.model import *


ego = Turtlebot3 at 0 @ -2


create_room(workspace.region.length, workspace.region.width)

# Bottleneck made of two pipes with a rock in between

gap = 4 * ego.width
halfGap = gap / 2

bottleneck = OrientedPoint offset by Range(-1.5, 1.5) @ Range(0.5, 1.5), facing Range(-30, 30) deg


leftEdge = OrientedPoint at bottleneck offset by -halfGap @ 0,
    facing Range(60, 120) deg relative to bottleneck.heading
rightEdge = OrientedPoint at bottleneck offset by halfGap @ 0,
    facing Range(-120, -60) deg relative to bottleneck.heading


GreyWall ahead of leftEdge, with length Range(1.5, 2)
GreyWall ahead of rightEdge, with length Range(1.5, 2)

WoodenTable offset by 1 @ 2
Box
ConstructionCone
ConstructionCone

Waypoint at 2 @ 2
Waypoint behind ego by 1.2

# Other junk because why not?

#Pipe
#BigRock
#BigRock
#Rock
#Rock
#Rock
