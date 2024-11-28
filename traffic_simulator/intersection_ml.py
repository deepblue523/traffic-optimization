import numpy as np
from datetime import datetime, timedelta
from light_post import LightPost
from intersection_stock import IntersectionStock
import keras
import random
import ws_functions
import cv2
import model_functions
import traffic_scenario
from keras.models import Sequential
from keras.layers import Dense, Conv2D, MaxPooling2D, Dropout, Flatten
from tensorflow.keras.utils import img_to_array
from keras.utils import to_categorical
from keras.preprocessing import image
from sklearn.model_selection import train_test_split
from camera_interface import prepare_camera_data
from camera import capture_still_image, capture_still_image2
#from math import round
import myutils, myconstants
from traffic_scenario import TrafficScenario
from traffic_scenario import get_combined_momentum

#########################################################################################
# THIS class is the implementation of an intersection that leverages a CNN to interpret
# images from cameras mounted somewhere at the intersection.  There is one camera facing
# in each direction.  Every 15 seconds, a new snapshot is taken and processed.  It is
# interpreted using the CNN and a 'density map' is produced, which is a vector describing
# traffic presence/layout in a more usable form.  The density maps are used to 'weight'
# traffic approaching the intersection, from which decisions can be made regarding when
# to change light states.  In concept, is a class derived from the 'stock' one that
# simply overrides the method that decides when a light change is a good thing.
#########################################################################################
class IntersectionML(IntersectionStock):
    
    #########################################################################################
    # Initialization - basic stuff, then load up the pre-trained CNN.
    #########################################################################################
    def __init__(self, id, segment_north, segment_south, segment_east, segment_west, cars, initial_sim_time, stats_rollup, global_ctx):

        super().__init__(id, segment_north, segment_south, segment_east, segment_west, cars, initial_sim_time, stats_rollup, global_ctx)

        self.time_last_traffic_update = self.global_ctx.current_sim_time
        self.pattern_travel_times = []
        self.minimum_seconds_for_green_light = myconstants.minimum_seconds_for_green_light_ml

        self.predictions_by_orientation = { 'north': None, 'south': None, 'east': None, 'west': None };
        
        self.total_active_lanes_weight = 0
        self.total_inactive_lanes_weight = 0

        self.initial_traffic_prediction_made = False
        self.last_light_changes_since_assessment = 0
        self.time_crossed_threshold_assessed = datetime(year=2001, month=1, day=1, hour=1, minute=1, second=0)
        self.cars_crossed_at_last_snapshot = 0
        myconstants.car_acceleration_factor = myconstants.car_acceleration_factor * 1.05
        
        #print("---[ Setting up ML for intersection " + str(self.id) + " ]---")
        #self.model_cnn = self.init_cnn_model()
        #print("   CNN loaded model for image processing")

    #########################################################################################
    # Instantiate our CNN and load weights from earlier training.
    #########################################################################################
    def init_cnn_model(self):

        # Load up our trained model CNN.
        json_file = open(myconstants.training_model_path + 'model_frustration_factor.json', 'r')
        loaded_model_json = json_file.read()
        json_file.close()
        model = keras.models.model_from_json(loaded_model_json)

        # Load saved weights into the loaded model.
        model.load_weights(myconstants.training_model_path + "model_frustration_factor.h5")

        return model

    #########################################################################################
    # Left turn arrow timeout.
    #########################################################################################
    def get_left_arrow_timeout(self):
        return 120

    def capture_frustration_factor(self, road_orientation):
        
        #print("I{0} -> {1} - Capturing frustration factor".format(self.id, road_orientation))

        # Prepare car data for generating an image.
        road_segment = self.get_road_segment(road_orientation)
        lane_Set = road_segment.get_lanes_going_direction(self.get_opposite_direction(road_orientation))

        # Get data we need to interface with the camera.
        camera_call_data = prepare_camera_data(self.id, road_orientation, road_segment, self.cars)
        
        # Set up a call to the camera WS.  Camera will take a picture of the oncoming cars.
        #print("Calling camera WS")
        if len(camera_call_data['carList']):
            imageData = capture_still_image(myconstants.camera_ws_url, camera_call_data)
        
            # Use our trained model to determine how frustrated the drivers might be.
            model_cnn_near = model_functions.get_camera_model_near(self.global_ctx, False)
            model_cnn_far = model_functions.get_camera_model_far(self.global_ctx, False)
            
            predicted_frustration_level_near = model_cnn_near.predict(imageData, verbose=0)
            predicted_frustration_level_far = model_cnn_far.predict(imageData, verbose=0)
            
            prediction_rounded = round(predicted_frustration_level[0][0])
            
            model_cnn_near = None
            model_cnn_far = None
            
            #print(str(len(camera_call_data['carList'])) + ': ' + str(prediction_rounded))

            return prediction_rounded
        else:
            return 0

        imageData = None

    def capture_all_frustration_factors(self):
        
        camera_call_data_accum = []
        camera_call_data_map = { }
        
        for road_segment_orientation in [ 'north', 'south', 'east', 'west' ]:
            # Prepare car data for generating an image.
            road_segment = self.get_road_segment(road_segment_orientation)

            # Get data we need to interface with the camera.
            camera_call_data = prepare_camera_data(self.id, road_segment_orientation, road_segment.name, self.cars)
            
            #if (len(camera_call_data['carList']) > 0):
            camera_call_data_accum.append(camera_call_data)
            camera_call_data_map[road_segment_orientation] = camera_call_data
        
        self.predictions_by_orientation = { 'north': None, 'south': None, 'east': None, 'west': None };
        
        if (len(camera_call_data_accum) > 0):
            # Capture the images via CameraWS.
            ws_data_wrapper = { 'trafficDetailSet': camera_call_data_accum }

            image_data_map = capture_still_image2(myconstants.camera_ws_url, camera_call_data_accum)

            model_cnn = model_functions.get_camera_model(self.global_ctx, False)
            
            #predict_sample_batch = [ image_data_map['north'], image_data_map['south'], image_data_map['east'], image_data_map['west'] ]
            #predicted_frustration_level = model_cnn.predict(predict_sample_batch, batch_size = 4)
            
            for orientation in image_data_map:
                if orientation in camera_call_data_map:
                    # Use our trained model to determine how frustrated the drivers might be.
                    image = image_data_map[orientation]
                    predicted_frustration_level = model_cnn.predict(image, verbose = 0)
                    
                    road_lanes = self.road_lanes_by_traffic_direction[orientation]

                    traffic_scenario = TrafficScenario(self, road_lanes, self.global_ctx)
                    traffic_scenario.traffic_left.traffic_near = max(0, round(predicted_frustration_level[0][0]))
                    traffic_scenario.traffic_left.traffic_middle = max(0, round(predicted_frustration_level[0][1]))
                    traffic_scenario.traffic_left.traffic_far = max(0, round(predicted_frustration_level[0][2]))
                    traffic_scenario.traffic_right.traffic_near = max(0, round(predicted_frustration_level[0][3]))
                    traffic_scenario.traffic_right.traffic_middle = max(0, round(predicted_frustration_level[0][4]))
                    traffic_scenario.traffic_right.traffic_far = max(0, round(predicted_frustration_level[0][5]))
                    traffic_scenario.traffic_turn.traffic_near = max(0, round(predicted_frustration_level[0][6]))
                    traffic_scenario.traffic_turn.traffic_middle = max(0, round(predicted_frustration_level[0][7]))
                    traffic_scenario.traffic_turn.traffic_far = max(0, round(predicted_frustration_level[0][8]))
                    
                    road_lanes.traffic_scenario = traffic_scenario
                    
                    self.predictions_by_orientation[orientation] = traffic_scenario
                    
                    if myconstants.enable_ml_weight_debug == True:
                        myutils.clear_files_in_path_wildcard(myconstants.runtime_output_model_debug + "\\weights\\" + str(self.id) + "_" + orientation + "*.jpg")
                        myutils.clear_files_in_path_wildcard(myconstants.runtime_output_model_debug + "\\symbols\\" + str(self.id) + "_" + orientation + "*.jpg")
                        
                        image_filename = myconstants.runtime_output_model_debug + "\\weights\\" + str(self.id) + "_" \
                                       + orientation + "__" \
                                       + "LN" + str(traffic_scenario.traffic_left.traffic_near) + "_" \
                                       + "LM" + str(traffic_scenario.traffic_left.traffic_middle) + "_" \
                                       + "LF" + str(traffic_scenario.traffic_left.traffic_far) + "__" \
                                       + "RN" + str(traffic_scenario.traffic_right.traffic_near) + "_" \
                                       + "RM" + str(traffic_scenario.traffic_right.traffic_middle) + "_" \
                                       + "RF" + str(traffic_scenario.traffic_right.traffic_far) + "__" \
                                       + "TN" + str(traffic_scenario.traffic_turn.traffic_near) + "_" \
                                       + "TM" + str(traffic_scenario.traffic_turn.traffic_middle) + "_" \
                                       + "TF" + str(traffic_scenario.traffic_turn.traffic_far) \
                                       + ".jpg"
                        
                        cv2.imwrite(image_filename, image_data_map[orientation + "_raw_image"])
 
                        '''full_symbol = self.get_traffic_pattern_symbol(None, predicted_frustration_level_near, predicted_frustration_level_middle, predicted_frustration_level_far, False)
                        image_filename = myconstants.runtime_output_model_debug + "\\symbols\\" + str(self.id) + "_" \
                                       + orientation + "__" + full_symbol \
                                       
                                       + ".jpg"
                        
                        cv2.imwrite(image_filename, image_data_map[orientation + "_raw_image"])'''
                        
        return self.predictions_by_orientation
    
    #########################################################################################
    # Converts a 'density map' into a simple weight that can be used for direct comparison.
    # The weight is a simple value that represents the amount of oncoming traffic based from
    # the original camera direction.
    #########################################################################################
    def compute_weight_for_lanes(self, lanes):
        
        return self.compute_weight_for_lanes_near(lanes), \
               self.compute_weight_for_lanes_middle(lanes), \
               self.compute_weight_for_lanes_far(lanes)
    
    def rectify_lanes_by_direction(self, direction, lanes1, lanes2, lanes3, lanes4, weights1, weights2, weights3, weights4):
        if (lanes1.direction == direction):
            return lanes1, weights1
        elif (lanes2.direction == direction):
            return lanes2, weights2
        elif (lanes3.direction == direction):
            return lanes3, weights3
        else:
            return lanes4, weights4

    #########################################################################################
    #
    # VERY IMPORTANT METHOD!!!!
    #
    # This overrides the superclass's 'time_to_trigger_main_light_change()' method with an ML
    # implementation.  The stock implementation is a simple timer.
    #########################################################################################
    def time_to_trigger_light_change(self, 
                                     current_sim_time, 
                                     time_since_last_state_change,
                                     time_since_last_crossing):
      
        # ---[ Check if we are past any extension ]---

         
        # ---[ Get traffic data for all sides of the intersection by active/inactive ]---
        active_lanes1, active_lanes2, inactive_lanes1, inactive_lanes2 = \
            self.get_road_laness_green_then_opposite()
        
        # ---[ Keep with the current light setting if we decided to let more through ]---
        # @@@ Make sure the intersection isn't "stuck" due to gridlock.
        #if time_since_last_crossing >= timedelta(seconds=90):
            #self.dynamic_green_light_ext_seconds = timedelta(seconds=60)
        #    return True
        
        '''if inactive_lanes1.lanes_have_room_for_more_cars() == False:
            #self.dynamic_green_light_ext_seconds = timedelta(seconds=15)
            return False'''
        
        #self.update_full_inbound_density_pattern(current_sim_time)
        '''if (active_lanes1.light_post.light_state_left_turn == "green") or \
           (active_lanes2.light_post.light_state_left_turn == "green"):
            self.update_full_inbound_density_pattern(current_sim_time)

            active_lanes1_traffic = self.predictions_by_orientation[active_lanes1.direction]
            active_lanes2_traffic = self.predictions_by_orientation[active_lanes2.direction]

            if (active_lanes1_traffic.has_turn_lane_traffic() == False) and \
               (active_lanes2_traffic.has_turn_lane_traffic() == False):
                active_lanes1.light_post.set_light_state_left_turn("red")
                active_lanes2.light_post.set_light_state_left_turn("red")
                active_lanes1.light_post.set_light_state_main("green")
                active_lanes2.light_post.set_light_state_main("green")
                
            elif (active_lanes1_traffic.has_turn_lane_traffic() == False):
                active_lanes1.light_post.set_light_state_left_turn("green")
                active_lanes2.light_post.set_light_state_left_turn("red")
                active_lanes1.light_post.set_light_state_main("green")
                active_lanes2.light_post.set_light_state_main("red")
                                
            elif (active_lanes2_traffic.has_turn_lane_traffic() == False):
                active_lanes1.light_post.set_light_state_left_turn("red")
                active_lanes2.light_post.set_light_state_left_turn("green")
                active_lanes1.light_post.set_light_state_main("red")
                active_lanes2.light_post.set_light_state_main("green")

            else:
                active_lanes1.light_post.set_light_state_left_turn("red")
                active_lanes2.light_post.set_light_state_left_turn("red")
                active_lanes1.light_post.set_light_state_main("green")
                active_lanes2.light_post.set_light_state_main("green")'''
        
        '''if self.dynamic_green_light_ext_seconds > timedelta(seconds=0):
            green_light_timeout_adj = self.time_crossed_threshold_assessed + \
                                      self.dynamic_green_light_ext_seconds
            
            if current_sim_time < green_light_timeout_adj:
                return False  '''

        
        if (self.cars_left_until_assessment > 0):
            return False
        
        self.update_full_inbound_density_pattern(current_sim_time)
            
        '''if self.dynamic_green_light_ext_seconds.total_seconds() == 0:
        self.update_full_inbound_density_pattern(current_sim_time)
        active_lanes1_traffic = self.predictions_by_orientation[active_lanes1.direction]
        active_lanes2_traffic = self.predictions_by_orientation[active_lanes2.direction]  
            
        self.cars_left_until_assessment = \
            active_lanes1_traffic.get_traffic(True, False, False) + \
            active_lanes2_traffic.get_traffic(True, False, False)  
            
        return self.cars_left_until_assessment <= 0 '''
            
        '''if inactive_lanes1.lanes_have_room_for_more_cars() == False:
            #self.dynamic_green_light_ext_seconds = timedelta(seconds=15)
            return False'''
        
        #if active_lanes1.lanes_have_room_for_more_cars() == False:
            #self.dynamic_green_light_ext_seconds = timedelta(seconds=0)
            #return True

        # ---[ Take a snapshot of the current state of the intersection (camera) ]---
        self.initial_traffic_prediction_made = True
        
        active_lanes1_traffic = self.predictions_by_orientation[active_lanes1.direction]
        active_lanes2_traffic = self.predictions_by_orientation[active_lanes2.direction]
        inactive_lanes1_traffic = self.predictions_by_orientation[inactive_lanes1.direction]
        inactive_lanes2_traffic = self.predictions_by_orientation[inactive_lanes2.direction]

        # Record when we last did all this assessment.
        self.time_crossed_threshold_assessed = current_sim_time
        
        # ---[ Main light change rules ]---
        # @@@ Inactive lanes have no traffic - no need to change lights.
        #if (get_combined_momentum(inactive_lanes1_traffic, inactive_lanes2_traffic) <= 0):
            #self.dynamic_green_light_ext_seconds = timedelta(seconds=15)
        #    return False  
       
        
        # @@@ inactive momentum is higher than active - change lights.  Also
        # Set a reevaluation delay to prevent rapid light changes and let stray
        # cars through.
        #if self.step_aux_data == None:
        combined_momentum_inactive = get_combined_momentum(inactive_lanes1_traffic, inactive_lanes2_traffic) 
        combined_momentum_active = get_combined_momentum(active_lanes1_traffic, active_lanes2_traffic)
        
        if combined_momentum_inactive > combined_momentum_active:
           
            self.step_aux_data = "on extension pass"
            self.cars_left_until_assessment = \
                        inactive_lanes1_traffic.get_traffic(True, True, True) + \
                        inactive_lanes2_traffic.get_traffic(True, True, True)  
            return True
        '''else:
            self.cars_left_until_assessment = \
                       inactive_lanes1_traffic.get_traffic(True, False, False) + \
                       inactive_lanes2_traffic.get_traffic(True, False, False)          

            return self.cars_left_until_assessment > 0 '''

        return False
    
    def get_traffic_scenario(self, weight_symbol):
        
        if weight_symbol == 'L':
            return 'light'
        elif weight_symbol == 'M':
            return 'medium'
        elif weight_symbol == 'H':
            return 'heavy'
        else:
            return 'unknown'
        
    #########################################################################################
    # Takes snapshots from each camera direction and produces an updated density map.
    #########################################################################################
    def update_full_inbound_density_pattern(self, current_sim_time):

        # Compute time since last update.
        time_since_last_update = current_sim_time - self.time_last_traffic_update
        
        if (self.initial_traffic_prediction_made == False) or \
           (time_since_last_update.seconds >= myconstants.seconds_between_camera_snapshots):
            # Get active road axis and inactive road axis.
            self.predictions_by_orientation = self.capture_all_frustration_factors()
                
            self.time_of_last_density_map_computation = self.global_ctx.current_sim_time
        
            self.traffic_north = self.predictions_by_orientation['north']
            self.traffic_south = self.predictions_by_orientation['south']
            self.traffic_east = self.predictions_by_orientation['east']
            self.traffic_west = self.predictions_by_orientation['west']

            # Get weight display values for the visualizer.
            '''
            self.traffic_weight_northbound = str(self.traffic_north.get_traffic(True, True, False))
            self.traffic_weight_southbound = str(self.traffic_south.get_traffic(True, True, False))
            self.traffic_weight_eastbound = str(self.traffic_east.get_traffic(True, True, False))
            self.traffic_weight_westbound = str(self.traffic_west.get_traffic(True, True, False))
            '''
            
            self.traffic_weight_northbound = str(self.traffic_north.get_momentum())
            self.traffic_weight_southbound = str(self.traffic_south.get_momentum())
            self.traffic_weight_eastbound = str(self.traffic_east.get_momentum())
            self.traffic_weight_westbound = str(self.traffic_west.get_momentum())


            self.time_last_traffic_update = current_sim_time
            self.initial_traffic_prediction_made = True

    #########################################################################################
    # All the 'step' function does here is take snapshot (for the CNN) every so often.
    #########################################################################################
    def step(self, current_sim_time):
            
        # print(current_sim_time)

        # Do our main thing!
        super().step(current_sim_time)

    def get_most_recent_camera_results(self):
        
        max_light_changes_for_any_lanes = self.road_on_north_side.light_post1
        self.road_on_south_side = max(max_light_changes_for_any_lanes, self.road_on_south_side.light_post1)
        self.road_on_east_side = max(max_light_changes_for_any_lanes, self.road_on_east_side.light_post1)
        self.road_on_west_side = max(max_light_changes_for_any_lanes, self.road_on_west_side.light_post1)

    '''def are_cars_at_left_turn_trip(self, lane_set):
        
        self.update_full_inbound_density_pattern(self.global_ctx.current_sim_time)
        if (lane_set.traffic_scenario == None):
            return False
        else:
            return lane_set.traffic_scenario.has_turn_lane_traffic()

    def has_turn_signal_timed_out(self, lane_set):

        self.update_full_inbound_density_pattern(self.global_ctx.current_sim_time)
        return lane_set.traffic_scenario.has_turn_lane_traffic()'''
        