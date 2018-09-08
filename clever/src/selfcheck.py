#!/usr/bin/env python

import math
import rospy
from std_srvs.srv import Trigger
from sensor_msgs.msg import Image, CameraInfo, NavSatFix, Imu
from mavros_msgs.msg import State
from geometry_msgs.msg import PoseStamped, TwistStamped


# TODO: roscore is running
# TODO: CPU usage
# TODO: local_origin, fcu, fcu_horiz
# TODO: rc service
# TODO: perform commander check in PX4
# TODO: selfcheck ROS service


rospy.init_node('selfcheck')


failures = []


def failure(text, *args):
    failures.append(text % args)


def check(name):
    def inner(fn):
        def wrapper(*args, **kwargs):
            failures[:] = []
            fn(*args, **kwargs)
            if not failures:
                rospy.loginfo('%s: OK', name)
            else:
                for f in failures:
                    rospy.logwarn('%s: %s', name, f)
        return wrapper
    return inner


@check('FCU')
def check_fcu():
    try:
        state = rospy.wait_for_message('mavros/state', State, timeout=3)
        if not state.connected:
            failure('No connection to the FCU')
    except rospy.ROSException:
        failure('No MAVROS state')


@check('Camera')
def check_camera(name):
    try:
        rospy.wait_for_message(name + '/image_raw', Image, timeout=1)
    except rospy.ROSException:
        failure('No %s camera images' % name)
    try:
        rospy.wait_for_message(name + '/camera_info', CameraInfo, timeout=3)
    except rospy.ROSException:
        failure('No %s camera camera info' % name)


@check('Aruco detector')
def check_aruco():
    try:
        rospy.wait_for_message('aruco_pose/debug', Image, timeout=1)
    except rospy.ROSException:
        failure('No aruco_pose/debug messages')


@check('Simple offboard node')
def check_simpleoffboard():
    try:
        rospy.wait_for_service('navigate', timeout=3)
        rospy.wait_for_service('get_telemetry', timeout=3)
        rospy.wait_for_service('land', timeout=3)
    except rospy.ROSException:
        failure('No simple_offboard services')


@check('IMU')
def check_imu():
    try:
        rospy.wait_for_message('mavros/imu/data', Imu, timeout=1)
    except rospy.ROSException:
        failure('No IMU data')


@check('Local position')
def check_local_position():
    try:
        rospy.wait_for_message('mavros/local_position/pose', PoseStamped, timeout=1)
    except rospy.ROSException:
        failure('No local position')


@check('Velocity estimation')
def check_velocity():
    try:
        velocity = rospy.wait_for_message('mavros/local_position/velocity', TwistStamped, timeout=1)
        horiz = math.hypot(velocity.twist.linear.x, velocity.twist.linear.y)
        vert = velocity.twist.linear.z
        if abs(horiz) > 0.1:
            failure('Horizontal velocity estimation is %s m/s; is the copter staying still?' % horiz)
        if abs(vert) > 0.1:
            failure('Vertical velocity estimation is %s m/s; is the copter staying still?' % vert)
    except rospy.ROSException:
        failure('No velocity estimation')


@check('Global position (GPS)')
def check_global_position():
    try:
        rospy.wait_for_message('mavros/global_position/global', PoseStamped, timeout=3)
    except rospy.ROSException:
        failure('No global position')


def selfcheck():
    # check('roscore', check_roscore)
    check_fcu()
    check_imu()
    check_local_position()
    check_velocity()
    check_global_position()
    check_camera('main_camera')
    check_aruco()
    check_simpleoffboard()


if __name__ == '__main__':
    rospy.loginfo('Performing selfcheck...')
    selfcheck()
