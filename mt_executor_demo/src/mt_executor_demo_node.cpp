#include <chrono>
#include <sstream>
#include <string>
#include <thread>

#include <rclcpp/rclcpp.hpp>
#include <sensor_msgs/msg/imu.hpp>
#include <std_srvs/srv/trigger.hpp>

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
//
// The mavros_msgs package isn't needed here: sensor_msgs/Imu is the message
// type MAVROS itself publishes, so this builds and runs standalone, and picks
// up real data automatically if mavros_node is running against the SITL setup.
class MultiThreadedExecutorDemo : public rclcpp::Node
{
public:
  MultiThreadedExecutorDemo() : Node("mt_executor_demo_node")
  {
    imu_sim_group_ = create_callback_group(rclcpp::CallbackGroupType::MutuallyExclusive);
    vision_sim_group_ = create_callback_group(rclcpp::CallbackGroupType::MutuallyExclusive);
    mavros_imu_group_ = create_callback_group(rclcpp::CallbackGroupType::MutuallyExclusive);
    synthetic_imu_group_ = create_callback_group(rclcpp::CallbackGroupType::MutuallyExclusive);
    service_group_ = create_callback_group(rclcpp::CallbackGroupType::MutuallyExclusive);
    client_group_ = create_callback_group(rclcpp::CallbackGroupType::MutuallyExclusive);

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

    synthetic_imu_pub_ = create_publisher<sensor_msgs::msg::Imu>("demo/imu/data", 10);

    rclcpp::SubscriptionOptions synthetic_imu_opts;
    synthetic_imu_opts.callback_group = synthetic_imu_group_;
    synthetic_imu_sub_ = create_subscription<sensor_msgs::msg::Imu>(
      "demo/imu/data", 10,
      std::bind(&MultiThreadedExecutorDemo::synthetic_imu_cb, this, std::placeholders::_1),
      synthetic_imu_opts);

    calibration_service_ = create_service<std_srvs::srv::Trigger>(
      "demo/calibrate_imu",
      std::bind(
        &MultiThreadedExecutorDemo::calibrate_imu_cb, this,
        std::placeholders::_1, std::placeholders::_2),
      rclcpp::ServicesQoS(), service_group_);

    calibration_client_ = create_client<std_srvs::srv::Trigger>(
      "demo/calibrate_imu", rclcpp::ServicesQoS(), client_group_);
    service_request_timer_ = create_wall_timer(
      1s, std::bind(&MultiThreadedExecutorDemo::send_calibration_request, this), client_group_);

    RCLCPP_INFO(get_logger(), "started: timers, mavros IMU, synthetic IMU pub/sub, and calibration service");
  }

private:
  void imu_sim_tick()
  {
    if (++imu_sim_count_ % 100 != 0) {  // log once per second at 100 Hz
      return;
    }
    RCLCPP_INFO(get_logger(), "[imu_sim]    tick %5d  thread=%s",
      imu_sim_count_, thread_id_str().c_str());

    sensor_msgs::msg::Imu msg;
    msg.header.stamp = now();
    msg.header.frame_id = "synthetic_imu";
    msg.linear_acceleration.z = 9.81;
    synthetic_imu_pub_->publish(msg);
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

  void synthetic_imu_cb(const sensor_msgs::msg::Imu::SharedPtr msg)
  {
    RCLCPP_INFO(get_logger(), "[synthetic_imu] accel_z=%.2f  thread=%s",
      msg->linear_acceleration.z, thread_id_str().c_str());
  }

  void calibrate_imu_cb(
    const std_srvs::srv::Trigger::Request::SharedPtr,
    std_srvs::srv::Trigger::Response::SharedPtr response)
  {
    response->success = true;
    response->message = "dummy IMU calibration complete";
    RCLCPP_INFO(get_logger(), "[service]     IMU calibrated  thread=%s",
      thread_id_str().c_str());
  }

  void send_calibration_request()
  {
    if (!calibration_client_->service_is_ready()) {
      RCLCPP_INFO(get_logger(), "[client]      waiting for service");
      return;
    }

    auto request = std::make_shared<std_srvs::srv::Trigger::Request>();
    calibration_client_->async_send_request(
      request,
      [this](rclcpp::Client<std_srvs::srv::Trigger>::SharedFuture future) {
        RCLCPP_INFO(get_logger(), "[client]      response: %s  thread=%s",
          future.get()->message.c_str(), thread_id_str().c_str());
      });
    service_request_timer_->cancel();
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
  rclcpp::CallbackGroup::SharedPtr synthetic_imu_group_;
  rclcpp::CallbackGroup::SharedPtr service_group_;
  rclcpp::CallbackGroup::SharedPtr client_group_;

  rclcpp::TimerBase::SharedPtr imu_sim_timer_;
  rclcpp::TimerBase::SharedPtr vision_sim_timer_;
  rclcpp::Subscription<sensor_msgs::msg::Imu>::SharedPtr imu_sub_;
  rclcpp::Publisher<sensor_msgs::msg::Imu>::SharedPtr synthetic_imu_pub_;
  rclcpp::Subscription<sensor_msgs::msg::Imu>::SharedPtr synthetic_imu_sub_;
  rclcpp::Service<std_srvs::srv::Trigger>::SharedPtr calibration_service_;
  rclcpp::Client<std_srvs::srv::Trigger>::SharedPtr calibration_client_;
  rclcpp::TimerBase::SharedPtr service_request_timer_;

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
