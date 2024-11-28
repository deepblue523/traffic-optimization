import numpy as np
from random import Random, randint, random
from datetime import datetime, timedelta
from stats_traffic import TrafficStatistics
from stats_traffic_registry import stats_registry
import myconstants

#########################################################################################
# This class represents a car!!!  A car has position, speed, a destination, and more.
# It encapsulates the basic driving behaviors that we have all come to know and love:
#
#    - Observing the speed limit.
#    - Slowing and stopping at intersections when lights dictate.
#    - Not crashing into the car in front (slowing down as needed).
#    - Making turns as appropriate to reach the destination.
#########################################################################################
class Car:
    
    def __init__(self, global_ctx, parent_stats, neighborhood_stats):
        
        self.id = myconstants.next_car_id
        myconstants.next_car_id = myconstants.next_car_id + 1
        
        self.global_ctx = global_ctx
        self.style_id = randint(0, 11) # 12 possible styles.
        self.car_length = 8
        self.endpoint_distance = 2500
        self.speed_limit = myconstants.global_speed_limit
        self.one_hour_in_seconds = 60 * 60
        self.neighborhood_stats = neighborhood_stats

        # Initial front bumper position - varies slightly to avoid delays
        # in cars being able to turn onto the road from their starting point.
        road_segment_one_third = int(myconstants.road_segment_length / 3)
        self.set_front_bumper_pos(road_segment_one_third + randint(0, road_segment_one_third))
        
        self.current_road_lanes = None
        self.route_map = None
        self.lane_id = 0
        self.route_map = None
        self.route_idx = 0
        self.current_road_segment = None
        self.initial_sim_time = None
        self.car_speed = 0
        self.time_entering_road = datetime.now()
        self.steps_since_last_move = 0

        self.next_stop_is_left_turn = False
        self.next_stop_is_right_turn = False
        self.currently_turning = False
        self.pct_through_turn = 0
        self.feet_since_turn_started = 0
        self.waiting_to_depart = True

        # Debug.
        self.car_stuck = None

    #########################################################################################
    # This method establishes the route that the car is going to take.  Essentially, the
    # source and destination point as well as information on how to get there for the 
    # "virtual driver" to follow.
    #########################################################################################
    def set_route(self, route_map, initial_road_lanes):

        self.route_map = route_map
        self.current_road_lanes = initial_road_lanes

    def at_stop_line(self):
        
        if (lane_id == 1):
            return front_bumper_pos >= self.road_segment_stop_line_offset2
        elif (lane_id == 2):
            return front_bumper_pos >= self.road_segment_stop_line_offset2
        elif (lane_id == 3):
            return front_bumper_pos <= self.road_segment_stop_line_offset1
        elif (lane_id == 4):
            return front_bumper_pos <= self.road_segment_stop_line_offset1
        else:
            return false
    
    #########################################################################################
    # Return True if the car is at the intersection.
    #########################################################################################
    def at_intersection(self):
        return self.get_front_bumper_pos() <= 22

        #return self.get_front_bumper_pos() <= 22 or \
        #       (self.lane_id == 3 and self.get_front_bumper_pos() < myconstants.left_turn_trip_span)
    
    #########################################################################################
    # Return True if the car is getting near the intersection.  The "near point" is 
    # arbitrary but affects when a car begins to slow if the light is red.
    #########################################################################################
    def approaching_intersection(self):
        return self.get_front_bumper_pos() <= 450

    #########################################################################################
    # Return the position of the car's rear bumper.  This is expressed as distance in feet
    # from the next intersection's stop line.
    #########################################################################################
    def get_rear_bumper_pos(self):
        return self.front_bumper_pos + myconstants.car_length

    #########################################################################################
    # Return the position of the car's front bumper.  This is expressed as distance in feet
    # from the next intersection's stop line.
    #########################################################################################
    def get_front_bumper_pos(self):
        return self.front_bumper_pos 

    #########################################################################################
    # Set the front bumper position of the car, in essence moving the car to the given 
    # location on the lane strip.
    #########################################################################################
    def set_front_bumper_pos(self, newValue):
        self.front_bumper_pos = newValue

    #########################################################################################
    # Finds the position of the back of a line of cars, typically used by the logic that
    # the car uses to position itself in the left turn lane if there is a backup.
    #########################################################################################
    def get_back_of_lane_queue(self, all_cars, current_road_lanes_name, lane_id_filter):

        max_rear_bumper = 22
        for car in all_cars:

            # On same road?
            if (car.current_road_lanes.name == current_road_lanes_name):

                # In the same lanes?
                if (car.lane_id == lane_id_filter):

                    max_rear_bumper = max(max_rear_bumper, car.get_rear_bumper_pos())

        return max_rear_bumper

    #########################################################################################
    # Locates the car directly in front of us.  We need this information to know whether
    # we need to slow down to avoid collision.
    #########################################################################################
    def find_next_car(self, all_cars):

        next_car = None
        next_car_dist = 1000000
        
        cars_besides_ourself = []
        for other_car in self.current_road_segment.cars_on_this_segment:
            if (self.id != other_car.id):
                cars_besides_ourself.append(other_car)
        
        for other_car in cars_besides_ourself:
            # On same road?
            if (self.current_road_lanes.name == other_car.current_road_lanes.name):

                # In the same lanes?
                if (self.lane_id == other_car.lane_id):

                    # Other car is in front of us.
                    if (other_car.get_rear_bumper_pos() < self.get_front_bumper_pos()):

                        # Use the closest car that is in front of us.
                        if (next_car == None):
                            next_car = other_car

                        else:
                            dist = self.get_front_bumper_pos() - other_car.get_rear_bumper_pos()
                            if (dist < next_car_dist):
                                next_car = other_car
                                next_car_dist = dist
        
        return next_car

    #########################################################################################
    # Determines if the cars in front of us are stopped in a traffic backup.  We may need
    # to slow down and stop even if we are not yet at the intsersection.
    #########################################################################################
    def chain_of_cars_in_front_of_us_is_stopped(self, all_cars):

        our_list_idx = all_cars.index(self)
        is_stopped = False

        for idx in range(0, our_list_idx):

            car_possibly_ahead = all_cars[idx]

            if (car_possibly_ahead.current_road_lanes.name == self.current_road_lanes.name) and \
               (car_possibly_ahead.lane_id == car_possibly_ahead.lane_id):

                if (self.id != car_possibly_ahead.id):
                    if (car_possibly_ahead.front_bumper_pos < self.front_bumper_pos):

                        is_stopped = is_stopped or (car_possibly_ahead.car_speed == 0)
                        

        
        return None

    #########################################################################################
    # Records current road speed and adds to a bucket for averaging, optionally emptying
    # the bucket while averaging what is already in it.
    #########################################################################################
    def sample_current_road_speed(self):

        pass
    
        # Update stats for the current road segment.
        #road_seg_fullname = self.current_road_segment.name + '/' + self.current_road_lanes.direction
        #road_seg_stats = stats_registry.get_stats_by_name(road_seg_fullname)
        #road_seg_stats.register_speed_sample(self.car_speed)

    #########################################################################################
    # This is the 'step' function for a car and is the main behavioral logic behind it.  It
    # encapsulates the following types of behavior:
    #
    #    - Speed control to avoid collisions, observe speed limit, and make controlled stops.
    #    - Identifying whether we are at an intersection.
    #    - Determining whether the car needs to turn, what direction, and initiating it.
    #    - Signal when we have reached our destination.
    #########################################################################################
    def step(self, all_cars, current_sim_time):

        this_step_car_pos = self.get_front_bumper_pos()
        
        #if (self.car_stuck != None):
        #    print("Car " + str(self.id) + " is stuck")

        try:
            if self.initial_sim_time == None:
                self.initial_sim_time = current_sim_time

            # Register this car's speed in the various stats areas.
            self.sample_current_road_speed()

            # We may turn at the intersection - let's see what to do.
            next_direction = self.route_map.get_next_direction(self.route_idx)

            # Kick out if we've reached our destination.
            if (next_direction == False): # None):
                #self.hourly_stats.total_cars_reaching_destination = self.hourly_stats.total_cars_reaching_destination + 1
                #road_seg_stats.increment_cars_reaching_destination_count(1)
               # self.neighborhood_stats.register_travel_time(current_sim_time - self.initial_sim_time)
                return False
            
            self.next_stop_is_left_turn = self.route_map.is_left_turn(self.current_road_lanes.direction, next_direction)
            self.next_stop_is_right_turn = self.route_map.is_right_turn(self.current_road_lanes.direction, next_direction)

            # Get ready to record stats for this car, if needed.
            road_seg_fullname = self.current_road_segment.name + '/' + self.current_road_lanes.direction
            road_seg_stats = stats_registry.get_stats_by_name(road_seg_fullname)

            # We're at an intersection...
            if self.at_intersection():

                # Get the intersection we are at.
                if self.current_road_lanes.light_post.intersection == None:
                    return False
                
                intersection = self.current_road_lanes.light_post.intersection
                
                # Exchange road segment for the car.
                next_road_segment = intersection.get_road_segment(next_direction)
                next_road_lanes = next_road_segment.get_lanes_going_direction(next_direction)
                this_was_left_turn = self.next_stop_is_left_turn
                
                # If the target lanes are full then we can't proceed yet.
                desired_new_lane = self.lane_id
                
                if self.next_stop_is_left_turn:
                    if next_road_lanes.lane_has_room_for_more_cars(1) == True:
                        desired_new_lane = 1
                    elif next_road_lanes.lane_has_room_for_more_cars(2) == True:
                        desired_new_lane = 2
                    else:
                        return False
                    
                elif self.next_stop_is_right_turn:
                    if next_road_lanes.lane_has_room_for_more_cars(2) == True:
                        desired_new_lane = 2
                    else:
                        return False
                    
                elif next_road_lanes.lane_has_room_for_more_cars(self.lane_id):
                    desired_new_lane = self.lane_id;  # Stay in same lane if possible.
                    
                else:
                    if randint(0, 1) < 1:
                        first_lane = 1
                        second_lane = 2
                    else:
                        first_lane = 2
                        second_lane = 1
                    
                    if next_road_lanes.lane_has_room_for_more_cars(first_lane):
                        desired_new_lane = first_lane
                    elif next_road_lanes.lane_has_room_for_more_cars(second_lane):
                        desired_new_lane = second_lane
                    else:
                        return False
                
                if next_road_lanes.lane_has_room_for_more_cars(desired_new_lane) == False:
                    return False

                # Kick out if we are stopped at the intersection.
                light_is_green = (self.next_stop_is_left_turn and self.current_road_lanes.light_post.light_state_left_turn == "green") or \
                                 (self.next_stop_is_left_turn == False and self.current_road_lanes.light_post.light_state_main == "green")
                
                if (light_is_green == False):
                    next_car = self.find_next_car(all_cars) 
                
                    if (next_car == None):
                        self.set_front_bumper_pos(22)
                    else:
                        self.set_front_bumper_pos(next_car.get_rear_bumper_pos() + 25)

                    #intersection = self.current_road_lanes.light_post.intersection
                    #intersection.register_car_passing_intersection(self.car_speed, self.current_road_lanes.direction)

                    return False

                # We might have to turn left.
                if self.next_stop_is_left_turn:
                    self.currently_turning = True
                else:
                    self.currently_turning = False

                # Otherwise, make our way across the intersection!

                self.current_road_segment.cars_on_this_segment.remove(self) 

                next_road_segment.cars_on_this_segment.append(self) 
                self.current_road_segment = next_road_segment
                self.current_road_lanes = next_road_lanes
                self.lane_id = desired_new_lane

                # Start traveling down the next segment.
                self.route_idx += 1

                if (self.currently_turning):
                    self.set_front_bumper_pos(5000)
                else:
                    self.set_front_bumper_pos(5300)
            
                intersection.stats.increment_car_crossing_count(1)
                
                #if this_was_left_turn == False:
                intersection.cars_left_until_assessment = intersection.cars_left_until_assessment - 1
                intersection.most_recent_crossing_time = current_sim_time
        
            # Don't bump into the car in front of us.
            next_car = self.find_next_car(all_cars) 

            # See if next car is stopped at the intersection.
            next_car_is_stopped_and_we_are_right_behind_it = False

            if (next_car != None):
                next_car_is_stopped_and_we_are_right_behind_it = \
                    (next_car.car_speed == 0) and abs(next_car.get_rear_bumper_pos() - self.get_front_bumper_pos()) < 250

            # Keep some distance between us and the next car.
            if (next_car != None):
                dist_to_next_car = self.get_front_bumper_pos() - next_car.get_rear_bumper_pos()
                if (dist_to_next_car < 150):
                    return False

            # Kick out if we've reached our destination.
            currently_on_final_segment = self.current_road_lanes.light_post.intersection == None
            if currently_on_final_segment and (self.get_front_bumper_pos() < self.endpoint_distance):
                self.current_road_segment.cars_on_this_segment.remove(self) 
                road_seg_stats.increment_cars_reaching_destination_count(1)
                self.neighborhood_stats.register_travel_time(current_sim_time - self.initial_sim_time)

                return True; 
            
            if (self.next_stop_is_left_turn):
                if (self.lane_id != 3):
                    if (self.get_front_bumper_pos() < 350) or (next_car_is_stopped_and_we_are_right_behind_it == True):
                        back_of_queue = self.get_back_of_lane_queue(all_cars, self.current_road_lanes.name, 3)
                        self.set_front_bumper_pos(back_of_queue + 150) 
                        
                        self.lane_id = 3

            # Stop at red lights.
            upcoming_light = self.current_road_lanes.light_post 
            is_stopped_at_light = False

            if (upcoming_light != None):
           
                # Get state of the relevant light.
                light_is_green = (self.next_stop_is_left_turn and self.current_road_lanes.light_post.light_state_left_turn == "green") or \
                                 (self.next_stop_is_left_turn == False and self.current_road_lanes.light_post.light_state_main == "green")

                # Don't bump into the next car!!!
                if (next_car_is_stopped_and_we_are_right_behind_it):
                    self.car_speed = 0
                    is_stopped_at_light = True

                # We are exactly AT the intersection AND it is RED!
                elif (self.at_intersection() and (light_is_green == False)):
                    self.car_speed = 0
                    self.set_front_bumper_pos(22)
                    is_stopped_at_light = True 

                # Stopped behind car directly in front.
                elif (next_car_is_stopped_and_we_are_right_behind_it and (light_is_green == False)):
                    self.car_speed = 0
                    is_stopped_at_light = True 
                
                # Light is near and it is RED!
                elif self.approaching_intersection() and (light_is_green == False):

                    pct_dist_to_line = min(self.get_front_bumper_pos(), 450) / 450
                    self.car_speed = min(myconstants.global_speed_limit, max(10, abs(self.car_speed) * pct_dist_to_line))

                # Upcoming light is green or we're not there yet anyway!
                elif (light_is_green or (self.at_intersection() == False)):

                    if (self.steps_since_last_move >= 600 and self.get_front_bumper_pos() > 2500):
                        dummy = 1

                    if self.next_stop_is_left_turn and self.at_intersection():
                        self.currently_turning = True
                        self.pct_through_turn = 0
                        self.feet_since_turn_started = 0
                        
                    elif (self.car_speed < self.speed_limit):
                        acceleration_factor = random() * myconstants.car_acceleration_factor
                        self.car_speed = min(self.current_road_segment.speed_limit, self.car_speed + myconstants.car_acceleration_factor)

                    elif (self.car_speed > self.speed_limit):
                        deceleration_factor = 0.60 + random() * 0.15
                        self.car_speed = self.car_speed * deceleration_factor

                else:

                    # Slow to match the guy in front if red.
                    if (next_car != None) and (dist_to_next_car < 30):

                        pct_dist_to_him = dist_to_next_car / 30
                        partway_between_speed = abs((self.car_speed - next_car.car_speed) * (1 - pct_dist_to_him))
                        self.car_speed = self.car_speed - partway_between_speed 

                # Move!
                time_diff_seconds = (current_sim_time - self.initial_sim_time).seconds
                portion_of_hour_this_timeslice = time_diff_seconds / self.one_hour_in_seconds
                movement_in_feet = self.car_speed * portion_of_hour_this_timeslice 

                # No backward movement!
                movement_in_feet = max(0, movement_in_feet)

                if self.currently_turning:
                    self.feet_since_turn_started += self.car_speed * portion_of_hour_this_timeslice
                    self.pct_through_turn = self.feet_since_turn_started / myconstants.left_turn_speed
               
                    if (self.pct_through_turn >= 1.0):
                        self.currently_turning = False

                else:
                    movement_in_feet = self.car_speed * portion_of_hour_this_timeslice
                    self.set_front_bumper_pos(self.get_front_bumper_pos() - movement_in_feet) 

            # If we make it this far then the car is still on its way.
            return False
        
        finally:
            movement_amount = int(this_step_car_pos) - int(self.get_front_bumper_pos())
                
            if (int(self.get_front_bumper_pos()) == int(this_step_car_pos)):
                self.steps_since_last_move = self.steps_since_last_move + 1
            else:
                self.steps_since_last_move = 0

            if (self.front_bumper_pos > 5000) and (self.steps_since_last_move > 100): #(movement_amount == 0):
                if (self.car_stuck == None):
                    next_car = self.find_next_car(all_cars) 
                    if (next_car != None) and ((next_car.get_rear_bumper_pos() - self.front_bumper_pos) > 400):
                        #print("Car " + str(self.id) + " is stuck at " + str(self.front_bumper_pos) + " and speed is " + str(self.car_speed))
                        self.car_stuck = self.id
                

#########################################################################################
# Finds an unoccupied lane for this car to use given its current front bumper position.
#########################################################################################
def get_start_lane(proposed_road_lanes_name, 
                   proposed_front_bumper_pos, 
                   current_road_segment):
    if current_road_segment == None:
        return 1

    collision_in_lane_1 = False
    collision_in_lane_2 = False

    for other_car in current_road_segment.cars_on_this_segment:
        
        if rect_collides_with_car(proposed_road_lanes_name, 
                                  proposed_front_bumper_pos, 
                                  other_car, 
                                  True):
            if (other_car.lane_id == 1):
                collision_in_lane_1 = True;
            elif (other_car.lane_id == 2):
                collision_in_lane_2 = True;

    if (collision_in_lane_1 == False) and (collision_in_lane_2 == False):
        return 1 + randint(0, 10) % 2
        
    elif (collision_in_lane_1 == False):
        return 1
        
    elif (collision_in_lane_2 == False):
        return 2
        
    else:
        return 0

#########################################################################################
# Tests whether another given car collides with this one, and returns True if so.
#########################################################################################
def rect_collides_with_car(proposed_road_lanes_name, 
                            proposed_front_bumper_pos, 
                            other_car, 
                            ignore_lanes):
        
    # Not even on same road.
    if (proposed_road_lanes_name != other_car.current_road_lanes.name):
        return False

    # In different lanes
    if (ignore_lanes == False) and (proposed_road_lanes_name != other_car.lane_id):
        return False

    # Far enough away in front of us.
    if (proposed_front_bumper_pos - other_car.get_rear_bumper_pos()) > 150:
        return False

    # Far enough away in back of us.
    elif (proposed_front_bumper_pos - self.get_rear_bumper_pos()) > 150:
        return False

    else:
        return True
