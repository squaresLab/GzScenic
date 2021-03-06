
from gzscenic.model import *

width = 8
length = 8
heading = 0
workspace = Workspace(RectangularRegion(0 @ 0, heading, width, length))

create_room(workspace.region.length, workspace.region.width)

ego = Fetch at 0 @ 0


table = CafeTable offset by 0 @ 1, facing 0 deg

#cube = DemoCube at table.position, with z (table.height + cube.height +  0.01)
#cube.z = table.height + cube.height +  0.01

create_room(3, 2.5, x=-2, y=2, sides='NSE')
table2 = CafeTable at -2 @ 2

Bookshelf at Range(-4,4) @ -3.5, facing 180 deg


back_right_region = RectangularRegion(-2 @ -2, 0, 3.5, 3.5)

Lampandstand in back_right_region

Waypoint in back_right_region
Waypoint ahead of table2 by 1
