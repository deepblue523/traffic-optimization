import numpy as np
import myconstants
from light_post import LightPost
from stats_traffic import TrafficStatistics

#########################################################################################
# Represents a set of lanes going in the same direction.  Two of them, together comprise
# a single road.  For example, 'east' lanes and 'west' lanes are part of the same road
# but here are broken out.  This segment of lanes also keeps a reference to the light
# post it leads up to.
#########################################################################################
class RoadLanesOneDirection:

    def __init__(self, name, light_post, speed_limit, direction, all_cars, cars_on_this_segment, stats_rollup, global_ctx):

        self.name = name
        self.light_post = light_post
        self.speed_limit = speed_limit
        self.all_cars = all_cars
        self.cars_on_this_segment = cars_on_this_segment
        self.traffic_scenario = None
        self.global_ctx = global_ctx
        self.stats = TrafficStatistics(name, [ stats_rollup ], self.global_ctx, False)

        self.direction = direction
        if (direction == "north"):
            self.x_inc = 0
            self.y_inc = -1

        elif (direction == "south"):
            self.x_inc = 0
            self.y_inc = 1

        elif (direction == "east"):
            self.x_inc = -1
            self.y_inc = 0

        else:
            self.x_inc = 1
            self.y_inc = 0
    
    #########################################################################################
    # Horribly inefficient data collection primitive.  Ran out of time to make it better!
    #########################################################################################
    def get_various_car_stats(self):

        cars_on_lanes = 0
        cars_at_trip = 0

        for car in self.cars_on_this_segment:
            if (car.current_road_lanes.name == self.name):
                cars_on_lanes = cars_on_lanes + 1

            if (car.at_intersection()):
                cars_at_trip = cars_at_trip + 1

        return cars_on_lanes, cars_at_trip
    
    #########################################################################################
    # Horribly inefficient data collection primitive.  Ran out of time to make it better!
    #########################################################################################
    def get_cars_on_this_lanes(self):

        lanes_cars = []
        for car in self.cars_on_this_segment:
            if (car.current_road_lanes.name == self.name):
                lanes_cars.append(car)

        return lanes_cars
    
    #########################################################################################
    # Horribly inefficient data collection primitive.  Ran out of time to make it better!
    #########################################################################################
    def get_cars_on_this_lanes_speed_less_than(self, max_speed):

        lanes_cars = []
        for car in self.cars_on_this_segment:
            if (car.current_road_lanes.name == self.name) and (car.car_speed <= max_speed):
                lanes_cars.append(car)

        return lanes_cars
    
    #########################################################################################
    # Horribly inefficient data collection primitive.  Ran out of time to make it better!
    #########################################################################################
    def count_cars_at_any_trip(self):

        car_count = 0
        lanes_cars = self.get_cars_on_this_lanes()

        for car in lanes_cars:
            if (car.at_intersection()):
                car_count = car_count + 1

        return car_count
    
    #########################################################################################
    # Horribly inefficient data collection primitive.  Ran out of time to make it better!
    #########################################################################################
    def are_cars_at_main_trip(self):

        lanes_cars = self.get_cars_on_this_lanes()
        for car in lanes_cars:
            if (car.lane_id == 1) or (car.lane_id == 2):
                if (car.at_intersection()):
                    return True

        return False

    def are_cars_at_left_lane_trip(self):

        lanes_cars = self.get_cars_on_this_lanes()
        for car in lanes_cars:
            if (car.lane_id == 1):
                if (car.at_intersection()):
                    return True

        return False

    def are_cars_at_right_lane_trip(self):

        lanes_cars = self.get_cars_on_this_lanes()
        for car in lanes_cars:
            if (car.lane_id == 2):
                if (car.at_intersection()):
                    return True

        return False
    
    #########################################################################################
    # Horribly inefficient data collection primitive.  Ran out of time to make it better!
    #########################################################################################
    def are_cars_at_left_turn_trip(self):

        lanes_cars = self.get_cars_on_this_lanes()
        for car in lanes_cars:
            if (car.lane_id == 3):
                if (car.front_bumper_pos < myconstants.left_turn_trip_span):
                    return True

        return False
    
    #########################################################################################
    # Horribly inefficient data collection primitive.  Ran out of time to make it better!
    #########################################################################################
    def get_car_furthest_away_from_intersection(self):

        max_distance = 22
        max_distance_car = None

        for car in self.cars_on_this_segment:
            if (max_distance_car == None):
                max_distance_car = car
                max_distance = car.front_bumper_pos

            elif (car.front_bumper_pos > max_distance):
                max_distance_car = car
                max_distance = car.front_bumper_pos

        return max_distance_car
    
    def get_car_furthest_away_from_intersection_in_lane(self, lane_id):

        max_distance = 22
        max_distance_car = None

        for car in self.cars_on_this_segment:
            if car.current_road_lanes.name == self.name and car.lane_id == lane_id:
                if (max_distance_car == None):
                    max_distance_car = car
                    max_distance = car.front_bumper_pos

                elif (car.front_bumper_pos > max_distance):
                    max_distance_car = car
                    max_distance = car.front_bumper_pos

        return max_distance_car
    
    def get_any_free_lane(self):

        max_distance_car0 = None
        max_distance_car1 = None

        for car in self.cars_on_this_segment:
            if (car.lane_id == 0) and \
               ((max_distance_car0 == None) or \
                (car.front_bumper_pos > max_distance_car0.get_rear_bumper_pos())):
                max_distance_car0 = car
                
            elif (car.lane_id == 1) and \
                 ((max_distance_car1 == None) or \
                  (car.front_bumper_pos > max_distance_car1.get_rear_bumper_pos())):
                max_distance_car1 = car
                
        if (max_distance_car0 != None) and \
           (max_distance_car0.rear_bumper_pos < max_distance_car1.get_rear_bumper_pos()):
            return max_distance_car0.line_id
        else:
            return 2
    
    
    #########################################################################################
    # Horribly inefficient data collection primitive.  Ran out of time to make it better!
    #########################################################################################
    def is_green_at_all(self):
    
        if (self.light_post.light_state_main == 'green') or \
           (self.light_post.light_state_left_turn == 'green'):
            return True
        else:
            return False

    def lanes_have_room_for_more_cars(self):
        # How many cars can fit on the segment?
        car_length_with_some_space = 50
        cars_that_can_fit_in_one_lane = myconstants.road_segment_length / car_length_with_some_space
        cars_that_can_fit_on_segment = cars_that_can_fit_in_one_lane * 2 # For now, ignore the left turn lane/
        
        # See if we're already filled up.
        if (len(self.cars_on_this_segment) < cars_that_can_fit_on_segment):
            return True
        else:
            return False

    def lane_has_room_for_more_cars(self, lane_id):
        
        furthest_car_in_lane = self.get_car_furthest_away_from_intersection_in_lane(lane_id)
        
        # See if we're already filled up.
        if furthest_car_in_lane != None:
            room_in_back_of_next_car = furthest_car_in_lane.get_rear_bumper_pos() < (myconstants.road_segment_length - 500)
            return room_in_back_of_next_car
        else:
            return True

    def is_open(self, lane_id, other_cars_list, startPtToTest, endingPtToTest):
        for car in other_cars_list:
            if (car.lane_id == lane_id):
                if (car.get_front_bumper_pos() in range(startPtToTest, endingPtToTest)):
                    return False
                elif (car.get_rear_bumper_pos() in range(startPtToTest, endingPtToTest)):
                    return False
                
        return True

    def get_congestion(self):
        
        congestion_cutoff = myconstants.global_speed_limit * 0.80
        congested_cars = 0
        for car in self.cars_on_this_segment:
            if car.car_speed < congestion_cutoff:

                '''next_car = car.find_next_car(self.all_cars) 

                if (next_car != None):
                    dist_to_next_car = car.get_front_bumper_pos() - next_car.get_rear_bumper_pos()
                    if (dist_to_next_car < 400):'''
                congested_cars += 1
                
        return congested_cars