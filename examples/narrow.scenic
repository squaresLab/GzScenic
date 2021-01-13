
from gzscenic.gazebo.model import *

ego = TurtleBot at 0 @ -2

# Bottleneck made of two pipes with a rock in between

gap = 4 * ego.width
halfGap = gap / 2

bottleneck = OrientedPoint offset by Range(-1.5, 1.5) @ Range(0.5, 1.5), facing Range(-30, 30) deg

#Box at bottleneck, with length Range(0.5,0.8)

leftEdge = OrientedPoint at bottleneck offset by -halfGap @ 0,
    facing Range(60, 120) deg relative to bottleneck.heading
rightEdge = OrientedPoint at bottleneck offset by halfGap @ 0,
    facing Range(-120, -60) deg relative to bottleneck.heading

#Pipe ahead of leftEdge, with length Range(1, 2)
#Pipe ahead of rightEdge, with length Range(1, 2)

Wall ahead of leftEdge, with length Range(1.5, 2)
Wall ahead of rightEdge, with length Range(1.5, 2)

Table offset by 1 @ 2
Box
ConstructionCone
ConstructionCone

Goal at 2 @ 2
Goal behind ego by 1.2

# Other junk because why not?

#Pipe
#BigRock
#BigRock
#Rock
#Rock
#Rock
