# A1.1 — Map processing and path planning (5 points)

Turn a 3D map of the hangar into something you can plan in, and find a collision-free path
through it. Nothing flies in this sub-assignment — the output is a path, and you can develop and
test all of it without the simulator running.

## Specification

### 1. Map loading — 1.5 points

Load the 3D map and convert it into a representation you can query for "is this point free?".

- The map is the point cloud of the hangar, `maps/FEI_LRS_PCD/map.pcd` in this repository.
- Use a library (PCL is the obvious choice — `sudo apt install libpcl-dev`) or write the
  loader yourself. Either is fine, both must be explained in the documentation.
- Downsample it to something you can plan in — a **voxel grid** or an **octree**. Planning
  directly over raw points is not going to finish in reasonable time.
- **Stacked 2D layers are not accepted.** Planning on a set of horizontal slices and stitching
  them together is not 3D planning — it cannot represent an obstacle you have to fly *over* or
  *under* on a diagonal, and it is exactly the shortcut this sub-assignment exists to rule out. Your
  representation and your planner both work in three dimensions.

**Accepted when:** you can load the map, print its bounding box and voxel count, and answer
occupancy queries for arbitrary 3D coordinates.

### 2. Obstacle inflation — 0.5 points

Grow every obstacle by a **configurable safety radius** before planning, so the planned path
keeps the drone's body away from walls instead of routing its centre point along them.

- The radius must be a parameter (ROS parameter, config file or constructor argument) — not a
  number buried in the code.
- Inflate in 3D. A path that clears an obstacle horizontally but flies through its top edge is
  still a crash.
- Think about what value is actually correct: the drone's radius **plus** your position
  controller's tolerance **plus** a margin. Justify your number in the documentation.

**Accepted when:** changing the radius visibly changes the planned path, and you can explain
how you arrived at the value you use.

#### You cannot fly through the shelves

The steel shelving racks in the hangar are **solid obstacles**. Look at the world file and you
will see why this needs saying: the rack's *visual* is an open mesh you can see straight
through, but its *collision* is a single solid box — 6.5 × 3.76 × 5.59 m
(`worlds/fei_lrs_gazebo.world`, the `regal.dae` link). The point cloud only samples the
surfaces it can see, so between the shelf levels there are gaps full of free-looking voxels.

A planner that trusts those gaps will happily route a path between two shelf levels, the path
will look perfectly valid in RViz, and the drone will fly straight into an invisible wall.

Handle it. Fill or close the volume, inflate enough to swallow the gaps, or treat the racks as
known bounding boxes — your choice, but **say which in the documentation**, and your planned
paths must go *around* the racks, never through them.

### 3. Advanced planning algorithm — 2.0 points

Implement or integrate a proper 3D planner. Choose one:

- **A\*** over the voxel grid (with an admissible heuristic — explain which one and why),
- **RRT** or **RRT\***,
- something else of comparable quality, agreed with your teacher first.

Requirements:

- Plans in **3D** — the path can change altitude, not only travel on one horizontal plane.
- Output is a **collision-free** sequence of 3D points from start to goal, checked against the
  **inflated** map.
- Handles the "no path exists" case without crashing or hanging forever.
- Reports how long planning took. You will want this number for the documentation anyway.

A plain BFS or flood-fill does **not** count as advanced — it is a fine way to convince
yourself your occupancy grid works, but it is the starting point, not the answer.

**Accepted when:** the planner finds a path between waypoints given by the teacher during the
defence — including at least one pair you have not tested before.

### 4. Path post-processing — 1.0 point

The raw planner output is not a flight path. A grid search over 25 cm voxels turns a 10 m
route into forty-odd points, most of them lying on a handful of straight lines. **This matters
more than it looks**: in [A1.2](02_indoor_mission_execution.md) your controller has to decide
it has arrived at each point before moving to the next, so forty points means forty
decelerations. The drone will crawl through the hangar in a series of hops. Simplification is
what turns that into smooth flight, which is why it is worth as much as it is here.

- **Minimum requirement:** remove redundant intermediate points — collinear runs (horizontal,
  vertical, diagonal) collapse to their endpoints.
- **Better:** line-of-sight shortcutting — walk the path and skip any point you can fly past in
  a straight collision-free line. This is a handful of lines of code on top of the collision
  checker you already wrote, and it removes far more points than collinearity alone.
- **Better still:** spline or polynomial smoothing, so the path has no sharp corners for the
  controller to overshoot.

Report the point count **before and after**, for at least two different routes. Those numbers
go in the documentation, and they are the evidence that this step did something.

**Accepted when:** the simplified path is still collision-free against the inflated map — check
this, do not assume it. Shortcutting is exactly the operation that can cut a corner through a
shelf, so re-run your collision check on the simplified path.

## Hints

- **Develop this without the simulator.** It is a standalone program that reads a `.pcd` and
  writes a list of points. Debug it as one — that is much faster than restarting Gazebo.
- **Visualise it.** Publish the voxel grid and the path as RViz markers, or dump them to a
  `.pcd`/image. You will find bugs in ten seconds that you would otherwise chase for an
  afternoon. `rviz2` is already installed.
- Watch the **coordinate origin** of the map. Where is (0, 0, 0) in the hangar? Where does the
  drone spawn? Getting the map and the drone into the same frame is half the work, and a
  silent offset here will look like a broken planner later.
- Watch the **units**. Everything you send to MAVROS is in **metres** and **radians**.
- Sanity-check your occupancy grid against the world file. If a query says the middle of a
  shelf is free space, you found the bug before it cost you a drone.

## Deliverables

- Source code of the map loader, inflation and planner.
- A way to run it standalone (a node, an executable, or a launch file) that takes a start and
  goal and prints/publishes the path.
- Timing and point-count numbers for the documentation (A1.4).

## Links

Full list in [`useful_links.md`](useful_links.md). The ones you need here:

- [PCL — reading a PCD file](https://pcl.readthedocs.io/projects/tutorials/en/latest/reading_pcd.html)
- [PCL — voxel grid filter](https://pcl.readthedocs.io/projects/tutorials/en/latest/voxel_grid.html)
- [PCL — octree](https://pcl.readthedocs.io/projects/tutorials/en/latest/octree.html)
- [RRT explained in 2D](https://theclassytim.medium.com/robotic-path-planning-rrt-and-rrt-212319121378)
- [RRT / RRT\* implemented in 3D](https://github.com/motion-planning/rrt-algorithms)
- [PathFinding.js — interactive A\*/Dijkstra/JPS visualiser](https://qiao.github.io/PathFinding.js/visual/)
- [Amit's A\* pages — the best explanation of A\* and its heuristics](https://theory.stanford.edu/~amitp/GameProgramming/)
- [`tutorial/ros2_cheatsheet.md`](../../tutorial/ros2_cheatsheet.md) — ROS 2 workspace and topics
