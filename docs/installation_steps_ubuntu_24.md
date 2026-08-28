Ubuntu 24
1. install ros2-jazzy
```bash
# Locale setup — correct
sudo apt update && sudo apt install locales
sudo locale-gen en_US en_US.UTF-8
sudo update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
export LANG=en_US.UTF-8

# Universe repository — correct
sudo apt install software-properties-common
sudo add-apt-repository universe

# ROS apt repository — correct/current method
sudo apt update && sudo apt install curl -y

export ROS_APT_SOURCE_VERSION=$(curl -s https://api.github.com/repos/ros-infrastructure/ros-apt-source/releases/latest \
  | grep -F "tag_name" | awk -F'"' '{print $4}')

curl -L -o /tmp/ros2-apt-source.deb \
"https://github.com/ros-infrastructure/ros-apt-source/releases/download/${ROS_APT_SOURCE_VERSION}/ros2-apt-source_${ROS_APT_SOURCE_VERSION}.$(. /etc/os-release && echo ${UBUNTU_CODENAME:-${VERSION_CODENAME}})_all.deb"

sudo dpkg -i /tmp/ros2-apt-source.deb

sudo apt update
sudo apt upgrade

sudo apt install ros-jazzy-desktop ros-dev-tools
source /opt/ros/jazzy/setup.bash
```

Useful commands
``` bash
rosdep install --from-paths src --ignore-src -r -y #install deps
colcon build --symlink-install
```
2. install gz-sim harmonic
On Ubuntu 24 run
``` bash
sudo apt-get install ros-${ROS_DISTRO}-ros-gz
```
3. Ardupilot
install branch Copter 4.7.0. - shouldnt matter for ubuntu 22/24
``` bash
git clone --recurse-submodules https://github.com/ArduPilot/ardupilot.git
cd ardupilot
git checkout Copter-4.7.0
git submodule update --init --recursive
Tools/environment_install/install-prereqs-ubuntu.sh -y

. ~/.profile
cd ~/ardupilot/ArduCopter
sim_vehicle.py -w --console --map
```
4. ardupilot gazebo
``` bash
sudo apt update
sudo apt install libgz-sim8-dev rapidjson-dev
sudo apt install libopencv-dev libgstreamer1.0-dev libgstreamer-plugins-base1.0-dev gstreamer1.0-plugins-bad gstreamer1.0-libav gstreamer1.0-gl

export GZ_VERSION=harmonic # or garden or ionic
sudo bash -c 'wget https://raw.githubusercontent.com/osrf/osrf-rosdep/master/gz/00-gazebo.list -O /etc/ros/rosdep/sources.list.d/00-gazebo.list'
rosdep update
rosdep resolve gz-harmonic # or gz-garden or gz-ionic
# Navigate to your ROS workspace before the next command.
rosdep install --from-paths src --ignore-src -y

echo 'export GZ_SIM_SYSTEM_PLUGIN_PATH=$HOME/ardupilot_gazebo/build:${GZ_SIM_SYSTEM_PLUGIN_PATH}' >> ~/.bashrc
echo 'export GZ_SIM_RESOURCE_PATH=$HOME/ardupilot_gazebo/models:$HOME/ardupilot_gazebo/worlds:${GZ_SIM_RESOURCE_PATH}' >> ~/.bashrc

#TODO: ADD CUSTOM WORLDS
```
5. install mavros
```bash
sudo apt install ros-${ROS_DISTRO}-mavros
sudo bash -c "source /opt/ros/$ROS_DISTRO/setup.bash && ros2 run mavros install_geographiclib_datasets.sh"
```
6. lfs
``` bash
sudo apt update
sudo apt install git-lfs
git lfs install

cd ~/LRS-URK
git lfs pull
```
7. add resource paths
```bash
grep -q 'LRS-URK/models' ~/.bashrc || {
  echo '' >> ~/.bashrc
  echo '# LRS-URK Gazebo models' >> ~/.bashrc
  echo 'export GZ_SIM_RESOURCE_PATH="$HOME/repos/LRS-URK/models:$GZ_SIM_RESOURCE_PATH"' >> ~/.bashrc
}

source ~/.bashrc
```

IMPORTANT --- REBOOT
