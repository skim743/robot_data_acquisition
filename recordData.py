import vizier.node as node
import queue
import json
import time
import threading
import vizier.mqttinterface as mqtt
import scipy.io as sio
import numpy as np
import logging
import csv

queue = queue.Queue(maxsize=1)
queue_cv = threading.Condition()

# file_path = "/home/robotarium_matlab_backend/static_data/com_errors_structs.mat"
com_error_file_path = "/Users/gritslab2/Desktop/robotarium-reg/robot_data_acquisition/com_errors_structs.mat"
mat_data = sio.loadmat(com_error_file_path)
com_errors = {x[0][0]: x[1].flatten() for x in mat_data["com_errors_structs"][0]}

def mqtt_handler(msg):

        # We need this lock, otherwise we could have a race condition
        with queue_cv:
            if queue.full():
                queue.get()
                queue.put(msg)
            else:
                queue.put(msg)

            # We're guaranteed to have produced an item at this point
            queue_cv.notify()

def com_error_correct(robot_id, pose):

        # corrected_angle = this.poses(3, i) + this.com_errors(2, i);
        # this.poses(1, i) = this.poses(1, i) - this.com_errors(1, i).*cos(corrected_angle);
        # this.poses(2, i) = this.poses(2, i) - this.com_errors(1, i).*sin(corrected_angle);'

        if robot_id in com_errors:
            corrected_angle = pose[2] + com_errors[robot_id][1]
            pose[0] -= com_errors[robot_id][0] * np.cos(corrected_angle)
            pose[1] -= com_errors[robot_id][0] * np.sin(corrected_angle)

        return pose

def main():
    logger = logging.getLogger('__main__')
    logger.setLevel(10)

    node_descriptor_file = 'config/node_desc_tracker.json'
    try:
        f = open(node_descriptor_file, 'r')
        node_descriptor = json.load(f)
        f.close()
    except Exception as e:
        print("Couldn't open given node file " + node_descriptor)

    print(node_descriptor)

    tracker_node = node.Node('192.168.1.8', 1884, node_descriptor)
    try:
        tracker_node.start()
    except Exception as e:
        print("Couldn't start tracker node.")
        error_bool = True        
        return -1, -1, error_bool
    
    links = list([x for x in tracker_node.gettable_links if 'status' in x])
    client = mqtt.MQTTInterface(host="192.168.1.8", port=1884)
    client.start()
    client.subscribe_with_callback("overhead_tracker/all_robot_pose_data", mqtt_handler)

    # Prepare a CSV file for data recording
    robot_index = list()
    for link in links:
        index = link.split('/')
        index = index[0]
        robot_index.append(index)

    fields = ['Time']
    for index in robot_index:
        fields.append(index+'_x')
        fields.append(index+'_y')
        fields.append(index+'_theta')
        fields.append(index+'_bus_volt')
        fields.append(index+'_bus_current')
        fields.append(index+'_power')
    
    file_name = 'robotData.csv'
    data_names = ['x','y','theta','bus_volt','bus_current','power']

    with open(file_name, 'w') as csvfile:
        csvwriter = csv.writer(csvfile)
        csvwriter.writerow(fields)
        csvfile.close()

    startTime = time.time()
    endTime = startTime + 10 # Hours * Mins * Secs
    previousTime = startTime
    
    while time.time() < endTime:
        currentTime = time.time()
        # Get one message to seed initial data
        # Should really do this more than once.  Otherwise, a bad message
        # will wreck the class
        with queue_cv:
            # Wait on queue
            while queue.empty():
                queue_cv.wait(timeout=5)

            msg = queue.get(timeout=1)

        try:
            decoded_msg = json.loads(msg.decode(encoding="UTF-8"))
        except Exception as e:
            raise
        
        if currentTime - previousTime >= 1:
            poses = np.array(
            [
                com_error_correct(
                    x, [decoded_msg[x]["x"], decoded_msg[x]["y"], decoded_msg[x]["theta"]]
                ) + [decoded_msg[x]["bus_volt"], decoded_msg[x]["bus_current"], decoded_msg[x]["power"]]
                for x in robot_index
                # [decoded_msg[x]["x"], decoded_msg[x]["y"], decoded_msg[x]["theta"], decoded_msg[x]["bus_volt"], decoded_msg[x]["bus_current"], decoded_msg[x]["power"]]
                # for x in robot_index
            ]
            )
            # print(poses)
            poses_formatted = [(currentTime - startTime)]
            for i in range(len(robot_index)):
                poses_formatted = poses_formatted + poses[i,:].tolist()
                # print(type(list(poses[i,:])[1]))
            # print(poses)
            with open(file_name, 'a') as csvfile:
                csvwriter = csv.writer(csvfile)
                csvwriter.writerow(poses_formatted)
            previousTime = time.time()

    tracker_node.stop()
    client.stop()
    return

if __name__ == '__main__':
    main()