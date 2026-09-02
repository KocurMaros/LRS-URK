# ROS 2 cheat sheet for LRS

Everything you need to get from "the simulation is running" to "my C++ node is reading a topic
and publishing setpoints". Written for **ROS 2 Jazzy**.

The worked example referenced throughout is
[`mt_executor_demo`](../mt_executor_demo/README.md) in this repository — a real, buildable
node. Where this page says *"see the demo"*, open that file and read the actual code.

## ROS 2 tutorials worth doing first

- [Understanding nodes](https://docs.ros.org/en/jazzy/Tutorials/Beginner-CLI-Tools/Understanding-ROS2-Nodes/Understanding-ROS2-Nodes.html)
- [Understanding topics](https://docs.ros.org/en/jazzy/Tutorials/Beginner-CLI-Tools/Understanding-ROS2-Topics/Understanding-ROS2-Topics.html)
- [Understanding services](https://docs.ros.org/en/jazzy/Tutorials/Beginner-CLI-Tools/Understanding-ROS2-Services/Understanding-ROS2-Services.html)
- [Writing a simple C++ publisher and subscriber](https://docs.ros.org/en/jazzy/Tutorials/Beginner-Client-Libraries/Writing-A-Simple-Cpp-Publisher-And-Subscriber.html)
- [Writing a simple C++ service client](https://docs.ros.org/en/jazzy/Tutorials/Beginner-Client-Libraries/Writing-A-Simple-Cpp-Service-And-Client.html) — you need this for arming and mode changes

## Preliminary: launch the simulation

Bring up the three terminals **by hand** as described in the [README](../README.md):
`gz sim`, ArduPilot SITL, MAVROS. Nothing below works until MAVROS is connected and
`ros2 topic list` shows `/mavros/...` topics.

---

## Section 1: the ROS 2 workspace

A ROS 2 workspace looks like this:

```
workspace_folder/              # workspace root
├── src/                       # everything you write lives here
│   ├── package_1/
│   │   ├── src/               # .cpp files
│   │   ├── include/           # headers
│   │   ├── msg/               # custom message definitions (if any)
│   │   ├── srv/               # custom service definitions (if any)
│   │   ├── launch/            # launch files
│   │   ├── CMakeLists.txt     # how it builds
│   │   └── package.xml        # what it depends on
│   └── package_2/
│
├── build/                     # build artifacts   ─┐
├── install/                   # installed output   ├─ generated; do not commit
└── log/                       # build/run logs    ─┘
```

Add a `.gitignore` with `build/`, `install/` and `log/` in it. Committing those is the most
common way to make a repository unusable for whoever clones it.

### Creating one and building

```bash
mkdir -p ~/ros2_ws/src
cd ~/ros2_ws/src
# either write your own package:
ros2 pkg create --build-type ament_cmake --dependencies rclcpp geometry_msgs my_drone_control
# or link this repo's example in to try it:
ln -s /path/to/LRS-URK/mt_executor_demo ~/ros2_ws/src/

cd ~/ros2_ws
colcon build                              # always from the workspace root
source install/setup.bash                 # every new terminal needs this
ros2 run mt_executor_demo mt_executor_demo_node
```

Rebuild after **every** code change. `colcon build --packages-select <pkg>` rebuilds just one
package and is much faster once you have several.

If a build error mentions a header or a target that you are sure exists, delete `build/` and
`install/` and build again — stale CMake caches cause errors that look like code problems.

---

## Section 2: console commands

Open a new terminal, `source ~/ros2_ws/install/setup.bash`, then:

### List what exists

```bash
ros2 topic list
ros2 service list
ros2 node list
```

Use `ros2 topic list` to check the system is up and to get the exact spelling of a topic name.
A typo in a topic name is silent — your subscriber just never fires.

### Read a topic

The important one for this course is `/mavros/local_position/pose`, the UAV's local position:

```bash
ros2 topic echo /mavros/local_position/pose
```

```
header:
  stamp:
    sec: 1696755038
    nanosec: 391547345
  frame_id: map
pose:
  position:
    x: 0.013228480704128742
    y: -0.013274122960865498
    z: -0.000252618920058012
  orientation:
    x: -4.2999677455014015e-05
    y: 0.0006802187081805384
    z: -0.6987245170632879
    w: -0.7153905120339602
---
```

Note the orientation is a **quaternion**, not an angle. See
[Quaternion fundamentals](https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Tf2/Quaternion-Fundamentals.html)
for converting it to yaw — and remember MAVROS gives you **ENU**, so that yaw is measured
counter-clockwise from East, not from North.

### Check the rate

```bash
ros2 topic hz /mavros/local_position/pose
```

```
average rate: 30.117
	min: 0.031s max: 0.036s std dev: 0.00121s window: 32
```

If a topic you depend on publishes at 1 Hz, no controller you write on top of it will be
smooth. Check this before blaming your code.

### Find the message type

```bash
ros2 topic info /mavros/local_position/pose
```

```
Type: geometry_msgs/msg/PoseStamped
Publisher count: 1
Subscription count: 1
```

That type tells you which package to depend on (`geometry_msgs`) and which header to include.

### Find the message fields

```bash
ros2 interface show geometry_msgs/msg/PoseStamped
```

```
std_msgs/Header header
Pose pose
```

Then drill down: `ros2 interface show geometry_msgs/msg/Pose`.

This is how you answer "what do I write in the message?" without guessing. It matters most for
`mavros_msgs/msg/PositionTarget`, whose `type_mask` and `coordinate_frame` constants decide
which fields the autopilot actually uses:

```bash
ros2 interface show mavros_msgs/msg/PositionTarget
```

Reference documentation, if you prefer reading it in a browser:
[`geometry_msgs`](https://docs.ros2.org/latest/api/geometry_msgs/index-msg.html),
[`sensor_msgs`](https://docs.ros2.org/latest/api/sensor_msgs/index-msg.html),
[`mavros_msgs`](https://github.com/mavlink/mavros/tree/ros2/mavros_msgs/msg).

### Publish and call from the terminal

Before writing any code, do it by hand:

```bash
ros2 service call /mavros/set_mode mavros_msgs/srv/SetMode "{base_mode: 0, custom_mode: GUIDED}"
ros2 service call /mavros/cmd/arming mavros_msgs/srv/CommandBool "{value: True}"
ros2 service call /mavros/cmd/takeoff mavros_msgs/srv/CommandTOL "{min_pitch: 0, yaw: 0, altitude: 2}"
```

Once those work from the terminal, your node is the same calls in C++.

### Parameters

```bash
ros2 param list /mavros
ros2 param get <node> <name>
ros2 param set <node> <name> <value>
ros2 run <pkg> <node> --ros-args -p my_param:=3.0
```

Use ROS parameters for anything the assignment calls "configurable" — inflation radius,
tolerances, the figure-8 rate. Recompiling to change a number costs you points at the defence.

### Record and replay

```bash
ros2 bag record -a -o run_$(date +%F_%H%M%S)
ros2 bag play <bagdir>
```

Record every mission run. It costs nothing and it is your evidence when the demo machine
misbehaves.

---

## Section 3: topics in C++

### Step 1 — declare the dependency

You found the type is `geometry_msgs/msg/PoseStamped`, so the package is `geometry_msgs`. It
goes in three places:

**`CMakeLists.txt`** — see [the demo's, lines 13–18](../mt_executor_demo/CMakeLists.txt):

```cmake
find_package(rclcpp REQUIRED)
find_package(geometry_msgs REQUIRED)

add_executable(my_node src/my_node.cpp)
ament_target_dependencies(my_node rclcpp geometry_msgs)
```

**`package.xml`** — see [the demo's, lines 11–13](../mt_executor_demo/package.xml):

```xml
<depend>rclcpp</depend>
<depend>geometry_msgs</depend>
```

**Your `.cpp`** — note how the type name converts to a header path
(`geometry_msgs/msg/PoseStamped` → `geometry_msgs/msg/pose_stamped.hpp`):

```cpp
#include <rclcpp/rclcpp.hpp>
#include <geometry_msgs/msg/pose_stamped.hpp>
```

Forgetting `package.xml` or `CMakeLists.txt` gives you a build error that names the header.
That error means "declare the dependency", not "the header is missing".

### Step 2 — subscriber

A subscriber has two parts: the object, and the callback that handles arriving messages.
See [`mt_executor_demo_node.cpp:54`](../mt_executor_demo/src/mt_executor_demo_node.cpp) for
this exact code in context:

```cpp
// member
rclcpp::Subscription<geometry_msgs::msg::PoseStamped>::SharedPtr pose_sub_;

// in the constructor
pose_sub_ = create_subscription<geometry_msgs::msg::PoseStamped>(
  "mavros/local_position/pose", rclcpp::SensorDataQoS(),
  std::bind(&MyNode::pose_cb, this, std::placeholders::_1));

// the callback
void pose_cb(const geometry_msgs::msg::PoseStamped::SharedPtr msg)
{
  RCLCPP_INFO(get_logger(), "z = %.2f", msg->pose.position.z);
}
```

**Use `rclcpp::SensorDataQoS()` for MAVROS sensor topics.** MAVROS publishes them as *best
effort*; a subscriber with the default *reliable* QoS silently receives nothing. This is a
frequent and very confusing failure — the topic is listed, `ros2 topic echo` shows data, and
your callback never runs.

### Step 3 — publisher

```cpp
// member
rclcpp::Publisher<mavros_msgs::msg::PositionTarget>::SharedPtr setpoint_pub_;

// in the constructor
setpoint_pub_ = create_publisher<mavros_msgs::msg::PositionTarget>(
  "mavros/setpoint_raw/local", 10);

// wherever you want to send one
mavros_msgs::msg::PositionTarget sp;
sp.header.stamp     = now();
sp.coordinate_frame = mavros_msgs::msg::PositionTarget::FRAME_LOCAL_NED;
sp.type_mask        = /* the bits for the fields you are NOT using */;
sp.position.x = 1.0;
sp.position.y = 2.0;
sp.position.z = 3.0;
sp.yaw        = 0.0;
setpoint_pub_->publish(sp);
```

Work out the `type_mask` from `ros2 interface show mavros_msgs/msg/PositionTarget` — it is a
bitmask of the fields to **ignore**. Get it wrong and the autopilot quietly discards your yaw,
or your position, with no error anywhere.

### Step 4 — publish on a timer, not in a sleep loop

Setpoints must go out at a steady rate. Use a wall timer — see
[`mt_executor_demo_node.cpp:39`](../mt_executor_demo/src/mt_executor_demo_node.cpp):

```cpp
using namespace std::chrono_literals;

timer_ = create_wall_timer(50ms, std::bind(&MyNode::publish_setpoint, this));  // 20 Hz
```

A `while` loop with `sleep` in the callback blocks the executor and stops everything else in
the node from running. Timers are what you want.

### Step 5 — services

Arming and mode changes are services, not topics:

```cpp
auto client = create_client<mavros_msgs::srv::CommandBool>("mavros/cmd/arming");
client->wait_for_service(5s);

auto req = std::make_shared<mavros_msgs::srv::CommandBool::Request>();
req->value = true;
auto future = client->async_send_request(req);
```

**Do not call `spin_until_future_complete` from inside a callback** — the node is already
spinning and it will deadlock. Handle the response asynchronously, or make the call from a
separate callback group. This is the second most common way a mission node hangs with no error.

---

## Section 4: executors and callback groups

Your node has to do several things at once: publish setpoints at 20 Hz, process incoming pose
messages, and run a planner that may take a second. With the default single-threaded executor,
the planner blocks the setpoint publisher and the drone stops receiving targets.

[`mt_executor_demo`](../mt_executor_demo/README.md) demonstrates the fix — put callbacks that
must not block each other in separate **callback groups** and spin with a
`MultiThreadedExecutor`:

```cpp
auto group = create_callback_group(rclcpp::CallbackGroupType::MutuallyExclusive);

rclcpp::SubscriptionOptions opts;
opts.callback_group = group;
sub_ = create_subscription<...>(topic, qos, callback, opts);

// in main()
rclcpp::executors::MultiThreadedExecutor executor;
executor.add_node(node);
executor.spin();
```

Run the demo, then swap in `SingleThreadedExecutor` and run it again — the difference is
visible in the log output within a second. Further reading:
[About executors](https://docs.ros.org/en/jazzy/Concepts/Intermediate/About-Executors.html).

---

## When something does not work

| Symptom | Look at |
|---|---|
| Callback never fires | QoS mismatch (`SensorDataQoS`), or the topic name is misspelled. Check with `ros2 topic list`. |
| Build error naming a header | Missing entry in `package.xml` / `CMakeLists.txt`. |
| Node hangs on a service call | `spin_until_future_complete` called from inside a callback. |
| Drone ignores part of your setpoint | `type_mask` — read `ros2 interface show mavros_msgs/msg/PositionTarget`. |
| Drone will not arm | Read the **SITL console**. It names the failing pre-arm check. |
| Trajectory is mirrored or rotated 90° | ENU vs NED. See [`assignments/assignment1/useful_links.md`](../assignments/assignment1/useful_links.md#frames--the-thing-that-will-bite-you). |
| Everything stutters | Single-threaded executor with a slow callback. See Section 4. |

More links: [`assignments/assignment1/useful_links.md`](../assignments/assignment1/useful_links.md).
