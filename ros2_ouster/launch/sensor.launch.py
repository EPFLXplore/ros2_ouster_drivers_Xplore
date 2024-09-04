#!/usr/bin/python3
# Copyright 2020, Steve Macenski
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from ament_index_python.packages import get_package_share_directory
import launch_ros
from launch import LaunchDescription
from launch_ros.actions import LifecycleNode
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch.actions import EmitEvent
from launch.actions import RegisterEventHandler
from launch_ros.events.lifecycle import ChangeState
from launch_ros.events.lifecycle import matches_node_name
from launch_ros.event_handlers import OnStateTransition
from launch.actions import LogInfo
from launch.events import matches_action
from launch.event_handlers.on_shutdown import OnShutdown

import lifecycle_msgs.msg
import os


def generate_launch_description():
    share_dir = get_package_share_directory('ros2_ouster')
    parameter_file = LaunchConfiguration('params_file')
    node_name = 'ouster_driver'

    use_rviz_arg = DeclareLaunchArgument(
        "use_rviz",
        default_value="true",
    )
    use_rviz = LaunchConfiguration("use_rviz", default="true")


    description_pkg_share_dir = get_package_share_directory('xplore_description')
    rviz_config_file = ''
    rviz_config_path = os.path.join(description_pkg_share_dir, "rviz", rviz_config_file)

    # Acquire the driver param file
    params_declare = DeclareLaunchArgument('params_file',
                                           default_value=os.path.join(
                                               share_dir, 'params', 'driver_config.yaml'),
                                           description='FPath to the ROS2 parameters file to use.')

    driver_node = LifecycleNode(package='ros2_ouster',
                                executable='ouster_driver',
                                name=node_name,
                                output='screen',
                                emulate_tty=True,
                                parameters=[parameter_file],
                                arguments=['--ros-args', '--log-level', 'INFO'],
                                namespace='/',
                                )
    imu_node = launch_ros.actions.Node(
        package="imu_pub",
        executable="imu_node",
        name="imu_node",
    )

    robot_state_launch_cmd = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(description_pkg_share_dir, "launch", "xplore_real.launch.py")
        ),
        launch_arguments={
            "use_rviz": use_rviz,
            "rviz_config": rviz_config_path,
        }.items(),
    )


    configure_event = EmitEvent(
        event=ChangeState(
            lifecycle_node_matcher=matches_action(driver_node),
            transition_id=lifecycle_msgs.msg.Transition.TRANSITION_CONFIGURE,
        )
    )

    activate_event = RegisterEventHandler(
        OnStateTransition(
            target_lifecycle_node=driver_node, goal_state='inactive',
            entities=[
                LogInfo(
                    msg="[LifecycleLaunch] Ouster driver node is activating."),
                EmitEvent(event=ChangeState(
                    lifecycle_node_matcher=matches_action(driver_node),
                    transition_id=lifecycle_msgs.msg.Transition.TRANSITION_ACTIVATE,
                )),
            ],
        )
    )

    # TODO make lifecycle transition to shutdown before SIGINT
    shutdown_event = RegisterEventHandler(
        OnShutdown(
            on_shutdown=[
                EmitEvent(event=ChangeState(
                  lifecycle_node_matcher=matches_node_name(node_name=node_name),
                  transition_id=lifecycle_msgs.msg.Transition.TRANSITION_ACTIVE_SHUTDOWN,
                )),
                LogInfo(
                    msg="[LifecycleLaunch] Ouster driver node is exiting."),
            ],
        )
    )

    return LaunchDescription([
        use_rviz_arg,
        params_declare,
        driver_node,
        robot_state_launch_cmd,
        imu_node,
        activate_event,
        configure_event,
        shutdown_event,
    ])
