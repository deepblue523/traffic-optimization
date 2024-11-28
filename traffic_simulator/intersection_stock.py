from datetime import datetime, timedelta
from random import randint
from light_post import LightPost
import myutils, myconstants
from stats_traffic import TrafficStatistics

#########################################################################################
# This is the 'stock' implementation of an intersection, one that does not leverage ML
# and instead works on timer and stop sensors.  Essentially, it alternates on axis
# and applies a timer to determine when a switch should be made.  Stop line sensors
# are taken advantage of and may trigger the left turn signal.
# 
# Do indefinitely
#     Case(turn lane sensors)
#         Northbound turn lane occupied and southbound empty:
#             Enable northbound’s left green arrow (allowing them to turn west) 
#             Enable northbound’s main green light (allowing movement north)
#              
#         Northbound empty and southbound turn lane occupied:
#             Enable southbound’s left green arrow (allowing them to turn east) 
#             Enable southbound’s main green light (allowing movement south)
# 
#         Turn lanes empty in both directions:
#             Keep lane sensors red in both directions
#             Enable both sets of main green lights (allow north/south traffic)
# 
#         Turn lanes occupied in both directions:
#             Enable green arrows on both sides (but main lights are red)
# 
#     Maintain current state 10 seconds (max left-turn time or base for main green)
#     Turn off any left arrows (set to red)
#     Enable main green lights and allow northbound and southbound travel
#     
#     Maintain state for 15 seconds (minimum for open north/south traffic)
# 
#     Trigger all stop (all lights red in all directions)
#     Continue same logic, this time switching to east-west
# 
#########################################################################################
class IntersectionStock:

    def __init__(self, id, road_on_north, road_on_south, road_on_east, road_on_west, cars, initial_sim_time, stats_rollup, global_ctx):

        self.id = id
        self.cars = cars
        self.global_ctx = global_ctx
        self.initial_sim_time = global_ctx.current_sim_time
        self.car_crossings = 0
        self.minimum_seconds_for_green_light = myconstants.minimum_seconds_for_green_light_stock
        self.dynamic_green_light_ext_seconds = timedelta(seconds=0)
        self.step_aux_data = None
        
        self.most_recent_crossing_time = global_ctx.current_sim_time
        
        self.lanes_active_direction1 = None
        self.lanes_active_direction2 = None
        self.lanes_inactive_direction1 = None
        self.lanes_inactive_direction2 = None
        
        self.road_on_north_side = road_on_north
        self.road_on_south_side = road_on_south
        self.road_on_east_side = road_on_east
        self.road_on_west_side = road_on_west

        self.road_lanes_north_bound = road_on_south.get_lanes_going_direction('north')
        self.road_lanes_south_bound = road_on_north.get_lanes_going_direction('south')
        self.road_lanes_east_bound = road_on_west.get_lanes_going_direction('east')
        self.road_lanes_west_bound = road_on_east.get_lanes_going_direction('west')

        self.road_lanes_by_traffic_direction = { 'south': road_on_south.get_lanes_going_direction('north'),
                                                 'north': road_on_north.get_lanes_going_direction('south'),
                                                 'west': road_on_west.get_lanes_going_direction('east'),
                                                 'east': road_on_east.get_lanes_going_direction('west') }

        self.lanes_active_direction1 = None
        self.lanes_active_direction2 = None
        self.cars_left_until_assessment = 0

        # Not used in 'stock' intersection but placed here to unify logging some code.
        self.traffic_south = None
        self.traffic_north = None
        self.traffic_west = None
        self.traffic_east = None

        self.traffic_weight_northbound = 0
        self.traffic_weight_southbound = 0
        self.traffic_weight_eastbound = 0
        self.traffic_weight_westbound = 0

        # Set up stats.
        self.stats = TrafficStatistics(self.id, [ stats_rollup ], self.global_ctx)
        self.road_on_north_side.stats.rollup_stats = self.stats
        self.road_on_south_side.stats.rollup_stats = self.stats
        self.road_on_east_side.stats.rollup_stats = self.stats
        self.road_on_west_side.stats.rollup_stats = self.stats

        self.all_stop_end_time = datetime(1,1,1,0,0,0)
        self.red_held_by_all_stop = False

        self.light_flow_mode = "NORMAL"
        
    #########################################################################################
    # Called during environment initialization, this completes the linkage between light 
    # posts and the intersection.
    #########################################################################################
    def link_lights_to_lanes(self):
        
        self.road_lanes_north_bound.light_post.intersection = self
        self.road_lanes_south_bound.light_post.intersection = self
        self.road_lanes_east_bound.light_post.intersection = self
        self.road_lanes_west_bound.light_post.intersection = self

    #########################################################################################
    # Return the road on the given side of the intersection.  That is, 'north' returns
    # the road on the north side of the intersection, NOT the northbound lane set (which
    # is actually coming from the south).
    #########################################################################################
    def get_road_segment(self, direction):

        if (direction == "north"):
            return self.road_on_north_side 
        elif (direction == "south"):
            return self.road_on_south_side 
        elif (direction == "east"):
            return self.road_on_east_side 
        else :
            return self.road_on_west_side 

    #########################################################################################
    # Returns the lamp post for traffic traveling in the requested direction.  For example,
    # 'north' will return the lamp post on the south side of the intersection (that is
    # observed by northbound traffic traveling toward the intersection).
    #########################################################################################
    def get_light(self, direction):

        if (direction == "north"):
            return self.light_post_north_bound 
        elif (direction == "south"):
            return self.light_post_south_bound 
        elif (direction == "east"):
            return self.light_post_east_bound 
        else :
            return self.light_post_west_bound 

    #########################################################################################
    # Initiate a stop in all directions.  Cars will automatically react to this based upon
    # their logic (their 'step' functions).
    #########################################################################################
    def all_stop(self):

        self.road_lanes_north_bound.light_post.stop()
        self.road_lanes_south_bound.light_post.stop()
        self.road_lanes_east_bound.light_post.stop()
        self.road_lanes_west_bound.light_post.stop()

    #########################################################################################
    # Tests whether the intersection is currently at all-stop.
    #########################################################################################
    def is_at_all_stop(self):

        return self.road_lanes_north_bound.light_post.is_at_all_stop() and \
               self.road_lanes_south_bound.light_post.is_at_all_stop() and \
               self.road_lanes_east_bound.light_post.is_at_all_stop() and \
               self.road_lanes_west_bound.light_post.is_at_all_stop()

    #########################################################################################
    #
    # VERY IMPORTANT METHOD!!!!
    #
    # This method determines when it is time for the lights to change from one direction 
    # (axis) to the other.  For this 'stock' implementation it is simply a time comparison.
    # Adding ML is a matter of overriding this method and providing ML-based criteria.
    def time_to_trigger_light_change(self, 
                                     current_sim_time, 
                                     time_since_last_state_change,
                                     time_since_last_crossing):

        random_variance = randint(0, myconstants.light_change_variance_stock) * 1000
        final_seconds_light = self.minimum_seconds_for_green_light + random_variance
        
        if (time_since_last_state_change.total_seconds() < final_seconds_light):
            return False
        else:
            return True

    #########################################################################################
    # Helper method to return the current statistics node.  This reference automatically
    # changes once per hour (done by the environment).
    #########################################################################################
    def get_current_intersection_stats(self):
        return self.stats

    #########################################################################################
    # Returns the 'active' and 'inactive' lanes.  These are relative assignments are based
    # upon which directions have the green light.  If north/south are green then they are
    # the 'active' lanes and east/west are 'inactive'.  This is useful for when we switch
    # light directions as we don't need to code for each possibility directly.
    #########################################################################################
    def get_road_laness_green_then_opposite(self):

        #if (self.lanes_active_direction1 == None):
        #    return None, None, None, None

        north_lanes = self.road_lanes_north_bound
        south_lanes = self.road_lanes_south_bound
        east_lanes = self.road_lanes_east_bound
        west_lanes = self.road_lanes_west_bound

        if (north_lanes.is_green_at_all() or south_lanes.is_green_at_all()):
            return north_lanes, south_lanes, east_lanes, west_lanes
        else:
            return east_lanes, west_lanes, north_lanes, south_lanes

    #########################################################################################
    # Captures an image from the intersection's still camera.
    #########################################################################################
    def capture_image_from_camera(self, lane_set):

        # Get car metadata for cars on the road.
        cars_on_this_lanes = lane_set.get_cars_on_this_lanes()

        car_data = []
        for car in cars_on_this_lanes:
            car_data.append([car.style_id, car.lane_id, car.front_bumper_pos])

        # Camera will take a picture of the oncoming cars.
        raw_bw_road_camera_image = myutils.capture_video_camera_image(car_data)
        return raw_bw_road_camera_image

    def has_turn_signal_timed_out(self, lane_set):

        return (self.global_ctx.current_sim_time - self.get_time_of_last_light_change()) >= timedelta(seconds=myconstants.timeout_left_turn_signal)
        
    def get_time_of_last_light_change(self):
        
        last_light_change = datetime(1970, 1, 1)
        
        last_light_change = max(last_light_change, self.road_lanes_by_traffic_direction['north'].light_post.last_light_change)
        last_light_change = max(last_light_change, self.road_lanes_by_traffic_direction['south'].light_post.last_light_change)
        last_light_change = max(last_light_change, self.road_lanes_by_traffic_direction['east'].light_post.last_light_change)
        last_light_change = max(last_light_change, self.road_lanes_by_traffic_direction['west'].light_post.last_light_change)

        return last_light_change
        
    #########################################################################################
    # Step function for the intersection, following the basic logic described above.
    #########################################################################################
    def step(self, current_sim_time):
        
        self.stats.record_congestion(self.road_lanes_north_bound.get_congestion() + \
                                     self.road_lanes_south_bound.get_congestion() + \
                                     self.road_lanes_east_bound.get_congestion() + \
                                     self.road_lanes_west_bound.get_congestion())
                                        
        # How long since we last changed our light state?
        time_since_last_state_change = current_sim_time - self.get_time_of_last_light_change()
        time_since_last_crossing = current_sim_time - self.most_recent_crossing_time 

        # Initially start north/south.
        if (self.lanes_active_direction1 == None):

            self.lanes_active_direction1 = self.road_lanes_north_bound
            self.lanes_active_direction2 = self.road_lanes_south_bound

            self.lanes_active_direction1.light_post.set_light_state_main("green")
            self.lanes_active_direction2.light_post.set_light_state_main("green")

        # Turn off any left arrows (set to red) after a short time.
        if self.lanes_active_direction1.light_post.light_state_left_turn == "green" or \
           self.lanes_active_direction2.light_post.light_state_left_turn == "green":
            if self.has_turn_signal_timed_out(self.lanes_active_direction1) and \
               self.has_turn_signal_timed_out(self.lanes_active_direction2):
                self.lanes_active_direction1.light_post.set_light_state_left_turn("red")
                self.lanes_active_direction2.light_post.set_light_state_left_turn("red")
                self.lanes_active_direction1.light_post.set_light_state_main("green")
                self.lanes_active_direction2.light_post.set_light_state_main("green")
            
        # Maintain current state for a short while (max left-turn time or base for main green).
        if (self.time_to_trigger_light_change(current_sim_time, 
                                              time_since_last_state_change,
                                              time_since_last_crossing) == False):
            return
        
        # Continue same logic, this time switching to east-west.
        self.lanes_active_direction1.light_post.set_light_state_main("red")
        self.lanes_active_direction2.light_post.set_light_state_main("red")
        self.lanes_active_direction1.light_post.set_light_state_left_turn("red")
        self.lanes_active_direction2.light_post.set_light_state_left_turn("red")

        if (self.lanes_active_direction1 == self.road_lanes_north_bound):
            self.lanes_active_direction1 = self.road_lanes_east_bound
            self.lanes_active_direction2 = self.road_lanes_west_bound
        else:
            self.lanes_active_direction1 = self.road_lanes_north_bound
            self.lanes_active_direction2 = self.road_lanes_south_bound

        # Northbound turn lane occupied and southbound empty.
        if (self.are_cars_at_left_turn_trip(self.lanes_active_direction1) == True and 
            self.are_cars_at_left_turn_trip(self.lanes_active_direction2) == False):

            self.lanes_active_direction1.light_post.set_light_state_main("green")
            self.lanes_active_direction1.light_post.set_light_state_left_turn("green")

        # Northbound empty and southbound turn lane occupied.
        elif (self.are_cars_at_left_turn_trip(self.lanes_active_direction1) == False and 
              self.are_cars_at_left_turn_trip(self.lanes_active_direction2) == True):

            self.lanes_active_direction2.light_post.set_light_state_main("green")
            self.lanes_active_direction2.light_post.set_light_state_left_turn("green")

        # Turn lanes empty in both directions.
        elif (self.are_cars_at_left_turn_trip(self.lanes_active_direction1) == False and 
              self.are_cars_at_left_turn_trip(self.lanes_active_direction2) == False):

            self.lanes_active_direction1.light_post.set_light_state_main("green")
            self.lanes_active_direction2.light_post.set_light_state_main("green")
            self.lanes_active_direction1.light_post.set_light_state_left_turn("red")
            self.lanes_active_direction2.light_post.set_light_state_left_turn("red")

        # Turn lanes occupied in both directions.
        elif (self.are_cars_at_left_turn_trip(self.lanes_active_direction1) == True and 
              self.are_cars_at_left_turn_trip(self.lanes_active_direction2) == True):

            self.lanes_active_direction1.light_post.set_light_state_main("red")
            self.lanes_active_direction2.light_post.set_light_state_main("red")
            self.lanes_active_direction1.light_post.set_light_state_left_turn("green")
            self.lanes_active_direction2.light_post.set_light_state_left_turn("green")

        else:

            self.lanes_active_direction1.light_post.set_light_state_main("green")
            self.lanes_active_direction2.light_post.set_light_state_main("green")
            self.lanes_active_direction1.light_post.set_light_state_left_turn("red")
            self.lanes_active_direction2.light_post.set_light_state_left_turn("red")

        self.time_of_last_light_change = self.global_ctx.current_sim_time
        #self.crossing_count_at__light_change = 0
        self.dynamic_green_light_ext_seconds = timedelta(seconds=0)
        
        self.step_aux_data = None
 
        return
    
    def are_cars_at_left_turn_trip(self, lane_set):
        
        return lane_set.are_cars_at_left_turn_trip()
        


