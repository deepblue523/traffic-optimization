import myconstants
import numpy as np
import math
import bisect
import random
from datetime import date
from datetime import time
from datetime import datetime
from datetime import timedelta
from car import Car
from route import RouteMap
from stats_traffic import TrafficStatistics
import myconstants

#########################################################################################
# This class represents traffic volumes from specific point-to-point, broken out by hour.
# It is the 'car generator' that adds cars to the model based upon how many are expected.
# There is a constant that is used to 'right size' the overall traffic in the simulation
# to match what the program can achieve practically.
#########################################################################################
class VolumePattern:

    def __init__(self, 
                 all_road_segments,
                 current_sim_time,
                 global_ctx,
                 parent_stats,
                 neighborhood_stats):
        
        self.id = id
        self.all_road_segments = all_road_segments
        self.time_of_last_step = current_sim_time
        self.one_hour_in_seconds = 60 * 60
        self.cars_generated_this_hour = 0
        self.time_of_last_hour_change = global_ctx.current_sim_time
        self.cars_generated = 0
        self.time_of_last_turnout = global_ctx.current_sim_time
        self.number_cars_to_generate_accum = 0
        self.global_ctx = global_ctx
        self.steps_per_hour = myconstants.one_hour_seconds / myconstants.sim_timestep_seconds
        self.neighborhood_stats = neighborhood_stats
        
        stats_name = "Pattern (?)"
        self.stats = TrafficStatistics(stats_name, [ parent_stats ], global_ctx, False)
        
        # ---------------------[ 8am    9am     10am    11am    12pm    1pm     2pm     3pm     4pm     5pm     6pm     7pm     8pm ]---
        self.traffic_volumes = [ 450,	400,	300, 	250,	350,	250,	250,	300,	350,	450, 	400,	250,    150 ] 
        
    #########################################################################################
    # Resets statistics when a new hour begins.
    #########################################################################################
    def reset(self, current_sim_time):

        self.time_of_last_step = current_sim_time
        self.cars_generated_this_hour = 0
        
    #########################################################################################
    # Generates a car instance and sets it to its initial position in the neighborhood.
    #########################################################################################
    def generate_new_car(self, all_cars):

        # Set up the car's route.
        route_map = myconstants.precomputed_routes[random.randint(0, len(myconstants.precomputed_routes) - 1)]
        road_segment = route_map.road_segment
        road_lanes = route_map.road_lanes

        initial_road_lanes = road_segment.get_lanes_going_direction(route_map.get_initial_direction())

        # Find a good insertion spot if we can.
        road_segment_half_length = int(myconstants.road_segment_length / 2)
        road_segment_third_length = int(myconstants.road_segment_length / 3)
        
        spot = None
        lane_1_open = True
        lane_2_open = True
        
        if self.global_ctx.current_sim_time == 8 and self.global_ctx.current_sim_time.minute <= 5:
            min_pos = 500
        else:
            min_pos = 1000
        
        #min_pos = 500
            
        attemptCnt = 0
        while attemptCnt < 5:
            lane_1_open = False
            lane_2_open = False

            #test_spot = random.randint(road_segment_half_length - road_segment_third_length, 
            #                           road_segment_half_length + road_segment_third_length)
            test_spot = random.randint(min_pos, \
                                       myconstants.road_segment_length - 1000)
                                       
            if initial_road_lanes.is_open(1, all_cars, test_spot - 20, test_spot + myconstants.car_length + 100):
                spot = test_spot
                lane_1_open = True
            
            if initial_road_lanes.is_open(2, all_cars, test_spot - 20, test_spot + myconstants.car_length + 100):
                spot = test_spot
                lane_2_open = True
            
                if (lane_1_open or lane_2_open):
                    break
                
            attemptCnt = attemptCnt + 1

        chosen_lane_id = 1
        if (lane_1_open and lane_2_open):
            chosen_lane_id = random.randint(1, 2)
        elif (lane_1_open):
            chosen_lane_id = 1
        elif (lane_2_open):
            chosen_lane_id = 2

        if (spot == None):
            return None

        # Allocate the car.
        new_car = Car(self.global_ctx, [ self.stats ], self.neighborhood_stats)
        new_car.lane_id = chosen_lane_id
        new_car.set_route(route_map, initial_road_lanes)
        new_car.current_road_segment = road_segment
        new_car.road_segment = road_segment
        new_car.road_lanes = road_lanes
        new_car.hourly_stats = self.hourly_stats
        new_car.route_map = route_map
       
        # Return the car.
        new_car.front_bumper_pos = spot

        return new_car

    #########################################################################################
    # Inserts a car into the global list, sorted by front bumper position.  Keeping them
    # ordered makes some computations in the simulation more efficient.
    #########################################################################################
    def insort_left(self, a, x, lo=0, hi=None):
        """Insert item x in list a, and keep it sorted assuming a is sorted.

        If x is already in a, insert it to the left of the leftmost x.

        Optional args lo (default 0) and hi (default len(a)) bound the
        slice of a to be searched.
        """

        if lo < 0:
            raise ValueError('lo must be non-negative')

        if hi is None:
            hi = len(a)

        while lo < hi:
            mid = (lo+hi)//2

            if a[mid].get_front_bumper_pos() < x.get_front_bumper_pos(): 
                lo = mid+1
            else: 
                hi = mid

        a.insert(lo, x)
        return x

    def insert_car_ordered(self, all_cars, new_car):

        return self.insort_left(all_cars, new_car)

    #########################################################################################
    # Main 'step' function driving car generation based upon traffic patterns.
    #########################################################################################
    def step(self, all_cars, current_sim_time):
        
        # Throttle car generation.
        if myconstants.fixed_volume_per_hour == 0:
            sim_hours_adj_volume_idx = min(11, current_sim_time.hour - 8)
            expected_volume_at_this_step = self.traffic_volumes[sim_hours_adj_volume_idx]
        else:
            expected_volume_at_this_step = myconstants.fixed_volume_per_hour

        inside_initial_population = current_sim_time.hour == 8 and current_sim_time.minute < 5
        if inside_initial_population:
            expected_volume_at_this_step = expected_volume_at_this_step * 10
            
        steps_per_hour = self.one_hour_in_seconds / myconstants.sim_timestep_seconds
        step_cars_to_generate = expected_volume_at_this_step / steps_per_hour * myconstants.traffic_volume_factor
        self.number_cars_to_generate_accum += step_cars_to_generate

        # Nothing to generate this step?  Short circuit car generation.
        if self.number_cars_to_generate_accum < 1:
            return 
        
        # Introduce some slight variability.
        min_seconds_between_turnouts = 6 + random.randint(0, 10)

        # Generate enough cars to fill "quota" up until this point in the hour.
        cars_processed = 0
        for i in range(0, int(self.number_cars_to_generate_accum)):
            cars_processed += 1

            new_car = self.generate_new_car(all_cars)

            if (new_car != None):
                self.insert_car_ordered(all_cars, new_car)

                next_car = new_car.find_next_car(all_cars)
                if (next_car != None):
                    new_car.car_speed = next_car.car_speed
                else:
                    new_car.car_speed = 40

                new_car.current_road_segment.cars_on_this_segment.append(new_car)                 
                new_car.time_entering_road = current_sim_time
                
                self.cars_generated = self.cars_generated + 1
                self.cars_generated_this_hour = self.cars_generated_this_hour + 1
                self.time_of_last_turnout = current_sim_time
                self.number_cars_to_generate_accum = 0

                self.stats.increment_cars_generated_count(1)

                #print("C{0} - Car generated on {1} coming from {2}".format(new_car.id, self.road_segment.name, self.begin_point_name))

        # Remember our last step time.
        self.time_of_last_step = current_sim_time
        self.number_cars_to_generate_accum -= cars_processed

            
