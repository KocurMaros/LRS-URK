from glob import glob
from setuptools import find_packages, setup


package_name = 'localization_sensor_sim'


setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
         ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/config', glob('config/*.yaml')),
        ('share/' + package_name + '/launch', glob('launch/*.launch.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='LRS teaching team',
    maintainer_email='lrs@fei.stuba.sk',
    description='Seeded localisation sensor simulation for Assignment 2.',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'sensor_simulator = localization_sensor_sim.sensor_simulator:main',
        ],
    },
)
