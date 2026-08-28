#include <chrono>
#include <sstream>
#include <string>
#include <thread>

#include <rclcpp/rclcpp.hpp>
#include <sensor_msgs/msg/imu.hpp>
#include <geometry_msgs/msg/pose_stamped.hpp>

using namespace std::chrono_literals;

// Demonstrates rclcpp::executors::MultiThreadedExecutor: four independent
// workloads, each pinned to its own callback group, run concurrently on
// separate threads instead of queuing behind one another as they would
// under a SingleThreadedExecutor.
//
//  - imu_sim_timer_    : fast (100 Hz) synthetic workload, no external deps
//  - vision_sim_timer_ : slow (10 Hz) synthetic workload with an artificial
//                        30 ms delay per call, to make blocking visible
//  - imu_sub_          : real telemetry, same topic/type MAVROS publishes
//                        on mavros/imu/data (sensor_msgs/Imu)
//  - pose_sub_         : real telemetry, same topic/type MAVROS publishes
//                        on mavros/local_position/pose (geometry_msgs/PoseStamped)
//
// The mavros_msgs package isn't needed here: sensor_msgs/Imu and
// geometry_msgs/PoseStamped are the message types MAVROS itself publishes
// on those topics, so this builds and runs standalone, and picks up real
// data automatically if mavros_node is running against the SITL setup.
class MultiThreadedExecutorDemo : public rclcpp::Node
{
public:
  MultiThreadedExecutorDemo() : Node("mt_executor_demo_node")
  {
    imu_sim_group_ = create_callback_group(rclcpp::CallbackGroupType::MutuallyExclusive);
    vision_sim_group_ = create_callback_group(rclcpp::CallbackGroupType::MutuallyExclusive);
    mavros_imu_group_ = create_callback_group(rclcpp::CallbackGroupType::MutuallyExclusive);
    mavros_pose_group_ = create_callback_group(rclcpp::CallbackGroupType::MutuallyExclusive);

    imu_sim_timer_ = create_wall_timer(
      10ms, std::bind(&MultiThreadedExecutorDemo::imu_sim_tick, this), imu_sim_group_);

    vision_sim_timer_ = create_wall_timer(
      100ms, std::bind(&MultiThreadedExecutorDemo::vision_sim_tick, this), vision_sim_group_);

    rclcpp::SubscriptionOptions imu_opts;
    imu_opts.callback_group = mavros_imu_group_;
    imu_sub_ = create_subscription<sensor_msgs::msg::Imu>(
      "mavros/imu/data", rclcpp::SensorDataQoS(),
      std::bind(&MultiThreadedExecutorDemo::mavros_imu_cb, this, std::placeholders::_1),
      imu_opts);

    rclcpp::SubscriptionOptions pose_opts;
    pose_opts.callback_group = mavros_pose_group_;
    pose_sub_ = create_subscription<geometry_msgs::msg::PoseStamped>(
      "mavros/local_position/pose", rclcpp::SensorDataQoS(),
      std::bind(&MultiThreadedExecutorDemo::mavros_pose_cb, this, std::placeholders::_1),
      pose_opts);

    RCLCPP_INFO(get_logger(), "started: 2 synthetic timers + 2 mavros subscriptions, 4 callback groups");
  }

private:
  void imu_sim_tick()
  {
    if (++imu_sim_count_ % 100 != 0) {  // log once per second at 100 Hz
      return;
    }
    RCLCPP_INFO(get_logger(), "[imu_sim]    tick %5d  thread=%s",
      imu_sim_count_, thread_id_str().c_str());
  }

  void vision_sim_tick()
  {
    // Simulated per-frame processing cost. Under a SingleThreadedExecutor
    // this would stall imu_sim_tick() for 30ms every call; here it doesn't,
    // because it runs on its own thread.
    std::this_thread::sleep_for(30ms);
    RCLCPP_INFO(get_logger(), "[vision_sim] tick %5d  thread=%s",
      ++vision_sim_count_, thread_id_str().c_str());
  }

  void mavros_imu_cb(const sensor_msgs::msg::Imu::SharedPtr msg)
  {
    RCLCPP_INFO(get_logger(), "[mavros_imu] accel=(%.2f, %.2f, %.2f)  thread=%s",
      msg->linear_acceleration.x, msg->linear_acceleration.y, msg->linear_acceleration.z,
      thread_id_str().c_str());
  }

  void mavros_pose_cb(const geometry_msgs::msg::PoseStamped::SharedPtr msg)
  {
    RCLCPP_INFO(get_logger(), "[mavros_pos] z=%.2f  thread=%s",
      msg->pose.position.z, thread_id_str().c_str());
  }

  static std::string thread_id_str()
  {
    std::ostringstream oss;
    oss << std::this_thread::get_id();
    return oss.str();
  }

  rclcpp::CallbackGroup::SharedPtr imu_sim_group_;
  rclcpp::CallbackGroup::SharedPtr vision_sim_group_;
  rclcpp::CallbackGroup::SharedPtr mavros_imu_group_;
  rclcpp::CallbackGroup::SharedPtr mavros_pose_group_;

  rclcpp::TimerBase::SharedPtr imu_sim_timer_;
  rclcpp::TimerBase::SharedPtr vision_sim_timer_;
  rclcpp::Subscription<sensor_msgs::msg::Imu>::SharedPtr imu_sub_;
  rclcpp::Subscription<geometry_msgs::msg::PoseStamped>::SharedPtr pose_sub_;

  int imu_sim_count_ = 0;
  int vision_sim_count_ = 0;
};

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);

  auto node = std::make_shared<MultiThreadedExecutorDemo>();

  rclcpp::executors::MultiThreadedExecutor executor;
  executor.add_node(node);
  executor.spin();

  rclcpp::shutdown();
  return 0;
}
