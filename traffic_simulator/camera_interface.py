import numpy as np
import cv2
import myconstants
import myutils
from multiprocessing import Pool

def prepare_camera_data(intersectionId, road_orientation, road_segment_name, cars_to_consider):
    
    # Traffic on this side of the intersection is coming towards us (right side of oncoming road).
    traffic_direction = myutils.get_opposite_direction(road_orientation)
                                                       
    # Prepare car data for generating an image.
    car_positions = []
    for this_car in cars_to_consider:
        if (this_car.current_road_segment.name == road_segment_name) and \
           (this_car.current_road_lanes.direction == traffic_direction):
            front_bumper_pos_adj = int(this_car.front_bumper_pos / float(3.35))

            if front_bumper_pos_adj <= 800:
                left_lane_pos_x = myutils.get_lane_leftx_pos(this_car.lane_id)
                
                this_car_pos = {
                                    'carImageIdx': this_car.style_id + 1,      # 1-based inside the camera image generator.
                                    'x1' : int(left_lane_pos_x),
                                    'x2' : int(left_lane_pos_x + 20),          # Desired WIDTH of car image, must be same as data generator to match model's training.
                                    'y1' : int(front_bumper_pos_adj), 
                                    'y2' : int(front_bumper_pos_adj + 41) # Desired HEIGHT of car image, must be same as data generator to match model's training.
                                }
            
                car_positions.append(this_car_pos)

    imageFilePath = "{0}intersection_{1}_{2}.png".format(myconstants.runtime_output_camera_path, 
                                                            intersectionId, 
                                                            road_orientation)

    ws_input = { "roadOrientation": road_orientation, "desiredOutputFilename" : imageFilePath, "carList" : car_positions } 
    
    return ws_input 
