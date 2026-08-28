cmake_minimum_required(VERSION 3.5)
project(mt_executor_demo)

if(NOT CMAKE_CXX_STANDARD)
  set(CMAKE_CXX_STANDARD 17)
endif()

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(sensor_msgs REQUIRED)
find_package(geometry_msgs REQUIRED)

add_executable(mt_executor_demo_node src/mt_executor_demo_node.cpp)
ament_target_dependencies(mt_executor_demo_node rclcpp sensor_msgs geometry_msgs)

install(TARGETS mt_executor_demo_node DESTINATION lib/${PROJECT_NAME})

ament_package()
