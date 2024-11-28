from asyncio.windows_events import CONNECT_PIPE_INIT_DELAY
from operator import length_hint
import pandas as pd
import random
import sys
import myutils
from datetime import datetime, timedelta
from intersection_stock import IntersectionStock
from intersection_ml import IntersectionML
from road_segment import RoadSegment
from volume_pattern import VolumePattern
from route import RouteMap
import myconstants
from stats_traffic import TrafficStatistics
from stats_traffic_registry import stats_registry
from sim_context import SimContext

###############################################################################
# The Neighborhood class encompasses the whole "environment" - roads, 
# intersections, cars, lights, etc.  It is responsible for setting up the layout 
# of the neighborhood as well as dumping statistics upon demand.
###############################################################################
class Neighborhood:

    #########################################################################################
    # This method initializes the simulation by setting up the following:
    #
    #    - Traffic volume broken out by hour.
    #    - Start/End points representing common routes to drive.
    #    - Instructions for cars on how to get from point A to point B (expressed as turns)
    #
    # It then set up the actual roads and intersections, weaving them into a
    # square 3x3 grid.
    #########################################################################################
    def __init__(self, intersection_type_name, sim_context, day_number):
        
        self.global_ctx = sim_context

        self.all_cars = []
        self.intersection_type_name = intersection_type_name
        self.last_debug_dump_time = self.global_ctx.current_sim_time

        self.current_running_stats = None # HourlyStatistics(self.global_ctx.current_sim_time.hour, None)
        self.sim_stats_last_collected = self.global_ctx.current_sim_time
        self.stats_ever_collected = False
        self.step_count = 0
        self.stats = TrafficStatistics("Neighborhood", [ ], self.global_ctx)

        # Set up road segments.
        self.road_segments = []
       
        self.road_segments.append(RoadSegment("R1", "north/south", 45, self.all_cars, self.stats, self.global_ctx))   # R1
        self.road_segments.append(RoadSegment("R2", "north/south", 45, self.all_cars, self.stats, self.global_ctx)) # R2
        self.road_segments.append(RoadSegment("R3", "north/south", 45, self.all_cars, self.stats, self.global_ctx)) # R3
        self.road_segments.append(RoadSegment("R4", "east/west", 45, self.all_cars, self.stats, self.global_ctx)) # R4
        self.road_segments.append(RoadSegment("R5", "east/west", 45, self.all_cars, self.stats, self.global_ctx)) # R5
        self.road_segments.append(RoadSegment("R6", "east/west", 45, self.all_cars, self.stats, self.global_ctx)) # R6
        self.road_segments.append(RoadSegment("R7", "east/west", 45, self.all_cars, self.stats, self.global_ctx)) # R7
        self.road_segments.append(RoadSegment("R8", "north/south", 45, self.all_cars, self.stats, self.global_ctx)) # R8
        self.road_segments.append(RoadSegment("R9", "north/south", 45, self.all_cars, self.stats, self.global_ctx)) # R9
        self.road_segments.append(RoadSegment("R10", "north/south", 45, self.all_cars, self.stats, self.global_ctx)) # R10
        self.road_segments.append(RoadSegment("R11", "east/west", 45, self.all_cars, self.stats, self.global_ctx)) # R11
        self.road_segments.append(RoadSegment("R12", "east/west", 45, self.all_cars, self.stats, self.global_ctx)) # R12
        self.road_segments.append(RoadSegment("R13", "east/west", 45, self.all_cars, self.stats, self.global_ctx)) # R13
        self.road_segments.append(RoadSegment("R14", "east/west", 45, self.all_cars, self.stats, self.global_ctx)) # R14
        self.road_segments.append(RoadSegment("R15", "north/south", 45, self.all_cars, self.stats, self.global_ctx)) # R15
        self.road_segments.append(RoadSegment("R16", "north/south", 45, self.all_cars, self.stats, self.global_ctx)) # R16
        self.road_segments.append(RoadSegment("R17", "north/south", 45, self.all_cars, self.stats, self.global_ctx)) # R17
        self.road_segments.append(RoadSegment("R18", "east/west", 45, self.all_cars, self.stats, self.global_ctx)) # R18
        self.road_segments.append(RoadSegment("R19", "east/west", 45, self.all_cars, self.stats, self.global_ctx)) # R19
        self.road_segments.append(RoadSegment("R20", "east/west", 45, self.all_cars, self.stats, self.global_ctx)) # R20
        self.road_segments.append(RoadSegment("R21", "east/west", 45, self.all_cars, self.stats, self.global_ctx)) # R21
        self.road_segments.append(RoadSegment("R22", "north/south", 45, self.all_cars, self.stats, self.global_ctx)) # R22
        self.road_segments.append(RoadSegment("R23", "north/south", 45, self.all_cars, self.stats, self.global_ctx)) # R23
        self.road_segments.append(RoadSegment("R24", "north/south", 45, self.all_cars, self.stats, self.global_ctx)) # R24

        # Intersections and attached road segments.
        self.intersections = []

        self.intersections.append(self.spawn_intersection(1, 
                                        segment_north = self.road_segments[0],  segment_south = self.road_segments[7], 
                                        segment_east  = self.road_segments[4],  segment_west  = self.road_segments[3], 
                                        cars = self.all_cars))
        
        self.intersections.append(self.spawn_intersection(2, 
                                        segment_north = self.road_segments[1],  segment_south = self.road_segments[8],
                                        segment_east  = self.road_segments[5],  segment_west  = self.road_segments[4], 
                                        cars = self.all_cars))

        self.intersections.append(self.spawn_intersection(3, 
                                        segment_north = self.road_segments[2],  segment_south = self.road_segments[9],
                                        segment_east  = self.road_segments[6],  segment_west  = self.road_segments[5], 
                                        cars = self.all_cars))

        self.intersections.append(self.spawn_intersection(4, 
                                        segment_north = self.road_segments[7],  segment_south = self.road_segments[14],
                                        segment_east  = self.road_segments[11], segment_west  = self.road_segments[10], 
                                        cars = self.all_cars))

        self.intersections.append(
                self.spawn_intersection(5, 
                                        segment_north = self.road_segments[8],  segment_south = self.road_segments[15],
                                        segment_east  = self.road_segments[12], segment_west  = self.road_segments[11], 
                                        cars = self.all_cars))

        self.intersections.append(self.spawn_intersection(6, 
                                        segment_north = self.road_segments[9],  segment_south = self.road_segments[16],
                                        segment_east  = self.road_segments[13], segment_west  = self.road_segments[12], 
                                        cars = self.all_cars))

        self.intersections.append(self.spawn_intersection(7, 
                                        segment_north = self.road_segments[14], segment_south = self.road_segments[21],
                                        segment_east  = self.road_segments[18], segment_west  = self.road_segments[17], 
                                        cars = self.all_cars))

        self.intersections.append(self.spawn_intersection(8, 
                                        segment_north = self.road_segments[15], segment_south = self.road_segments[22],
                                        segment_east  = self.road_segments[19], segment_west  = self.road_segments[18], 
                                        cars = self.all_cars))

        self.intersections.append(self.spawn_intersection(9, 
                                        segment_north = self.road_segments[16], segment_south = self.road_segments[23],
                                        segment_east  = self.road_segments[20], segment_west  = self.road_segments[19], 
                                        cars = self.all_cars))

        # Tie intersection to lanes in each direction
        for this_intersection in self.intersections:
            this_intersection.link_lights_to_lanes()

        # For performance, precompute some GPS routes.
        self.precomputed_routes = []
        for _ in range(0, 1000):
            route_map = RouteMap(self.global_ctx, self.road_segments)
            myconstants.precomputed_routes.append(route_map)
            
        # Set up traffic patterns and routes.
        self.volume_patterns = []

        for idx in range(0, len(myconstants.road_segment_valid_starting_points) - 1):
            
            self.volume_patterns.append(VolumePattern(
                        self.road_segments,
                        self.global_ctx, 
                        self.global_ctx, 
                        self.stats,
                        self.stats))

        self.sim_stats_all = []
        self.sim_stats_current_hour = None

    #########################################################################################
    # Creates an intersection instance of the correct type, either "stock" or "ML, based
    # upon what was specified for the neighborhood.
    #########################################################################################
    def spawn_intersection(self, id, segment_north, segment_south, segment_east, segment_west, cars):

        if (self.intersection_type_name == "IntersectionStock"):
            return IntersectionStock('I' + str(id), segment_north, segment_south, segment_east, segment_west, cars, self.global_ctx, self.stats, self.global_ctx)
        else:
            return IntersectionML('I' + str(id), segment_north, segment_south, segment_east, segment_west, cars, self.global_ctx, self.stats, self.global_ctx)

    #########################################################################################
    # Performance stats are kept by the hour.  This method looks for an hour change and
    # changes the number "holders" if it detects such an event.
    #########################################################################################
    def advance_stats_node(self, current_time):

        # See if we need to generate a new global stats instance.
        if (self.current_running_stats == None) or \
           (self.global_ctx.current_sim_time.hour != self.sim_stats_last_collected.hour) or \
           (self.stats_ever_collected == False):

            # Create a node.
            self.stats_ever_collected = True

            # Re-point the node in the dependent objects.
            for intersection in self.intersections: 
                intersection.hourly_stats = self.current_running_stats

            for pattern in self.volume_patterns: 
                pattern.hourly_stats = self.current_running_stats

        self.sim_stats_last_collected = self.global_ctx.current_sim_time

    #########################################################################################
    # Dump stats to the console.
    #########################################################################################
    def dump_stats_to_console(self, dump_function):

        dump_function(sys.stdout)

    #########################################################################################
    # Dump stats to a file with the given name.
    #########################################################################################
    def dump_stats_to_file(self, filename, dump_function):

        file_object = open(filename, "w") 
        dump_function(file_object)

    #########################################################################################
    # Dump stats to any file object.
    #########################################################################################
    def dump_stats_crossing_count(self, file_object):

        # Crossing stats per intersection
        #print("", file=file_object);
        print("ID Cum   8am  9am  10am 11am 12pm 1pm  2pm  3pm  4pm  5pm  6pm  7pm ", file=file_object);
        print("== ===== ==== ==== ==== ==== ==== ==== ==== ==== ==== ==== ==== ====", file=file_object);

        for intersection in self.intersections:
            work_str = "{0} {1:<5} ".format(intersection.id, intersection.stats.car_crossing_count)

            for hour in range(8, 20):

                hour_stats = stats_registry.get_stats_by_name_and_hour(intersection.id, hour)

                if (hour_stats != None):
                    work_str = work_str +  "{0:<4} ".format(hour_stats.car_crossing_count)
                else:
                    work_str = work_str +  "       "

            print(work_str, file=file_object);

        print("   ----- ---- ---- ---- ---- ---- ---- ---- ---- ---- ---- ---- ----", file=file_object);
        work_str = "   {0:<5} ".format(self.stats.car_crossing_count)

        for hour in range(8, 20):
            hour_stats = self.stats.get_bucket_for_hour(hour)
            
            if (hour_stats != None):
                work_str = work_str +  "{0:<4} ".format(hour_stats.car_crossing_count)
            else:
                work_str = work_str +  "      "

        print(work_str, file=file_object);
    
    def dump_stats_light_change_count(self, file_object):

        # Crossing stats per intersection
        #print("", file=file_object);
        print("ID Cum   8am  9am  10am 11am 12pm 1pm  2pm  3pm  4pm  5pm  6pm  7pm ", file=file_object);
        print("== ===== ==== ==== ==== ==== ==== ==== ==== ==== ==== ==== ==== ====", file=file_object);

        for intersection in self.intersections:
            work_str = "{0} {1:<5} ".format(intersection.id, intersection.stats.light_change_count)

            for hour in range(8, 20):

                hour_stats = stats_registry.get_stats_by_name_and_hour(intersection.id, hour)

                if (hour_stats != None):
                    work_str = work_str +  "{0:<4} ".format(hour_stats.light_change_count)
                else:
                    work_str = work_str +  "       "

            print(work_str, file=file_object);

        print("   ----- ---- ---- ---- ---- ---- ---- ---- ---- ---- ----- ---- ----", file=file_object);
        work_str = "   {0:<5} ".format(self.stats.light_change_count)

        for hour in range(8, 20):
            hour_stats = self.stats.get_bucket_for_hour(hour)
            
            if (hour_stats != None):
                work_str = work_str +  "{0:<4} ".format(hour_stats.light_change_count)
            else:
                work_str = work_str +  "      "

        print(work_str, file=file_object);
    
    def dump_stats_congestion(self, file_object):

        # Crossing stats per intersection
        #print("", file=file_object);
        print("ID Cum   8am  9am  10am 11am 12pm 1pm  2pm  3pm  4pm  5pm  6pm  7pm ", file=file_object);
        print("== ===== ==== ==== ==== ==== ==== ==== ==== ==== ==== ==== ==== ====", file=file_object);
        
        for intersection in self.intersections:

            work_str = "{0} {1:<5} ".format(intersection.id, intersection.stats.get_congestion())

            for hour in range(8, 20):
                hour_stats = stats_registry.get_stats_by_name_and_hour(intersection.id, hour)

                if (hour_stats != None):
                    work_str = work_str +  "{0:<4} ".format(hour_stats.get_congestion())
                else:
                    work_str = work_str +  "       "

            print(work_str, file=file_object);

        print("   ----- ---- ---- ---- ---- ---- ---- ---- ---- ---- ---- ---- ----", file=file_object);
        work_str = "   {0:<5} ".format(self.stats.get_congestion())

        for hour in range(8, 20):
            hour_stats = self.stats.get_bucket_for_hour(hour)
            
            if (hour_stats != None):
                work_str = work_str +  "{0:<4} ".format(hour_stats.get_congestion())
            else:
                work_str = work_str +  "       "

        print(work_str, file=file_object);
        
    def dump_stats_car_count(self, file_object):

        # Crossing stats per intersection
        #print("", file=file_object);
        print("8am  9am  10am 11am 12pm 1pm  2pm  3pm  4pm  5pm  6pm  7pm ", file=file_object);
        print("==== ==== ==== ==== ==== ==== ==== ==== ==== ==== ==== ====", file=file_object);
        
        work_str = ""
        for hour in range(8, 20):
            stats_hour_bucket = self.stats.hour_buckets[str(hour)]
            work_str = work_str +  "{0:<4} ".format(stats_hour_bucket.get_car_count_average())
            
        work_str = work_str + "\n\nTotal: {0:<9} ".format(self.stats.get_car_count_average())

        print(work_str, file=file_object);
        
    def dump_stats_cars_on_road(self, file_object):

        # Crossing stats per intersection
        #print("", file=file_object);
        print("8am  9am  10am 11am 12pm 1pm  2pm  3pm  4pm  5pm  6pm  7pm ", file=file_object);
        print("==== ==== ==== ==== ==== ==== ==== ==== ==== ==== ==== ====", file=file_object);
        
        work_str = ""
        for hour in range(8, 20):
            stats_hour_bucket = self.stats.hour_buckets[str(hour)]
            work_str = work_str +  "{0:<4} ".format(int(stats_hour_bucket.get_car_count_average()))
            
        work_str = work_str + "\n\nTotal: {0:<9} ".format(int(self.stats.get_car_count_average()))

        print(work_str, file=file_object);
       
    def dump_stats_travel_time(self, file_object):

        # Crossing stats per intersection
        #print("", file=file_object);
        print("8am  9am  10am 11am 12pm 1pm  2pm  3pm  4pm  5pm  6pm  7pm ", file=file_object);
        print("==== ==== ==== ==== ==== ==== ==== ==== ==== ==== ==== ====", file=file_object);
        
        work_str = ""
        for hour in range(8, 20):
            stats_hour_bucket = self.stats.hour_buckets[str(hour)]
            
            val = stats_hour_bucket.get_travel_time_average().total_seconds() / 60         
            work_str = work_str +  "{0:<4} ".format(int(val))
        
        val2 = self.stats.get_travel_time_average().total_seconds() / 60         
        work_str = work_str + "\n\nTotal: {0:<9} ".format(int(val2))

        print(work_str, file=file_object);
        
    def dump_stats_cars_to_let_cross(self, file_object):

        print("I1   I2   I3   I4   I5   I6   I7   I8   I9  ", file=file_object);
        print("==== ==== ==== ==== ==== ==== ==== ==== ====", file=file_object);
        work_str = ""

        for intersection in self.intersections:        
            work_str = work_str +  "{0:<4} ".format(intersection.cars_left_until_assessment)

        print(work_str, file=file_object);

    #########################################################################################
    # This method drives the simulation by implementing the "step".  Every step advances by
    # a given number of seconds, currently defined as 3 but configurable.  The main logic
    # of this method is to pass the "step" even down to child objects like the traffic
    # volume controllers and intersections.
    #########################################################################################
    def step(self):

        # Move 1 step.
        self.global_ctx.current_sim_time += timedelta(seconds=myconstants.sim_timestep_seconds)
        
        '''if self.step_count == 0:
            print("")
        
        unpadded_hour_str = str(self.global_ctx.current_sim_time.hour)
        time_str = unpadded_hour_str + self.global_ctx.current_sim_time.strftime(":%M:%S%p").lower()
        print(self.intersection_type_name + ': ' +  time_str, end="\r")'''

        # Collect metrics.
        self.advance_stats_node(self.global_ctx.current_sim_time)

        # Let cars do their thing.
        cars_to_remove = []
        for car in self.all_cars:
            if (car.step(self.all_cars, self.global_ctx.current_sim_time) == True):
                cars_to_remove.append(car)
        
        for car in cars_to_remove:
            self.all_cars.remove(car)

        self.stats.register_cars_on_road(len(self.all_cars)
                                         )
        # Generate volume as appropriate.
        #self.volume_patterns[6].step(self.all_cars, self.global_ctx.current_sim_time)
        
        for volume_pattern in self.volume_patterns:
            volume_pattern.step(self.all_cars, self.global_ctx.current_sim_time)

        # Advance each intersection by one step.
        for intersection in self.intersections:
            intersection.step(self.global_ctx.current_sim_time)
        
        if self.step_count == 0:
            print("")
            print("---[ Simulation Running (8am -> 8pm) ]---")           
        
        unpadded_hour_str = str(self.global_ctx.current_sim_time.hour)
        time_str = unpadded_hour_str + self.global_ctx.current_sim_time.strftime(":%M:%S%p").lower()
        print(self.intersection_type_name + ': ' +  time_str, end="\r")
        
        # Write all car metadata out to a flat file periodically.
        time_since_last_debug_dump = self.global_ctx.current_sim_time - self.last_debug_dump_time

        if (time_since_last_debug_dump.seconds >= myconstants.sim_seconds_between_debugger_frames):
            metadata_filename = "debug_frame_{0:02}{1:02}{2:02}_{3:02}{4:02}_{5}.neighborhood.txt".format(self.global_ctx.current_sim_time.month, 
                                                                            self.global_ctx.current_sim_time.day, 
                                                                            self.global_ctx.current_sim_time.hour, 
                                                                            self.global_ctx.current_sim_time.minute, 
                                                                            self.global_ctx.current_sim_time.second,
                                                                            random.randint(1, 1000000))

            metadata_filename_abs = myconstants.runtime_output_base_path + self.intersection_type_name + "\\runtime_stats\\sim_snapshot_animation_data\\" + metadata_filename
            with open(metadata_filename_abs, "w") as text_file:
                print(str(f'{self.global_ctx.current_sim_time.month}/' \
                          f'{self.global_ctx.current_sim_time.day}/' \
                          f'{self.global_ctx.current_sim_time.year} ' \
                          f'{self.global_ctx.current_sim_time.hour}:' \
                          f'{self.global_ctx.current_sim_time.minute}:' \
                          f'{self.global_ctx.current_sim_time.second}'), file=text_file)

                for intersection in self.intersections:
                    print(f'{intersection.id}, ' \
                          f'{intersection.road_on_north_side.name}, ' \
                          f'{intersection.road_on_south_side.name}, ' \
                          f'{intersection.road_on_east_side.name}, ' \
                          f'{intersection.road_on_west_side.name}, ' \
                          f'{intersection.road_lanes_north_bound.light_post.light_state_main}, ' \
                          f'{intersection.road_lanes_north_bound.light_post.light_state_left_turn}, ' \
                          f'{intersection.road_lanes_south_bound.light_post.light_state_main}, ' \
                          f'{intersection.road_lanes_south_bound.light_post.light_state_left_turn}, ' \
                          f'{intersection.road_lanes_east_bound.light_post.light_state_main}, ' \
                          f'{intersection.road_lanes_east_bound.light_post.light_state_left_turn}, ' \
                          f'{intersection.road_lanes_west_bound.light_post.light_state_main}, ' \
                          f'{intersection.road_lanes_west_bound.light_post.light_state_left_turn}, ' \
                          f"0," \
                          f"0," \
                          f"0," \
                          f"0," \
                          f'0,0,0,0,' \
                          f'{intersection.traffic_weight_northbound},' \
                          f'{intersection.traffic_weight_southbound},' \
                          f'{intersection.traffic_weight_eastbound},' \
                          f'{intersection.traffic_weight_westbound},' \
                          f'{intersection.traffic_weight_northbound},' \
                          f'{intersection.traffic_weight_southbound},' \
                          f'{intersection.traffic_weight_eastbound},' \
                          f'{intersection.traffic_weight_westbound},' \
                          f'0,' \
                          f'{intersection.cars_left_until_assessment}'
                          , file=text_file)

                print(f"[End_Lights]", file=text_file)

                for car in self.all_cars:
                    print(f'{car.id}, ' \
                          f'{car.style_id}, ' \
                          f'{car.current_road_lanes.name}, ' \
                          f'{car.car_speed}, ' \
                          f'{car.car_length}, ' \
                          f'{car.front_bumper_pos}, ' \
                          f'{car.lane_id}, ' \
                          f'{car.car_speed}, ' \
                          f'{car.currently_turning}, ' \
                          f'{car.pct_through_turn}, ' + str(car.at_intersection()), \
                          file=text_file)

                # Occassionally dump out the stats for the debugger.
                self.dump_stats_to_file("{0}{1}\\runtime_stats\\sim_snapshot_car_crossings\\day_summary_{2}_{3}_{4}.txt"
                                            .format(myconstants.runtime_output_base_path, 
                                                    self.intersection_type_name,
                                                    self.global_ctx.current_sim_time.hour, 
                                                    self.global_ctx.current_sim_time.minute,
                                                    self.global_ctx.current_sim_time.second),
                                            self.dump_stats_crossing_count)

                self.dump_stats_to_file("{0}{1}\\runtime_stats\\sim_snapshot_car_counts\\day_summary_{2}_{3}_{4}.txt"
                                            .format(myconstants.runtime_output_base_path, 
                                                    self.intersection_type_name,
                                                    self.global_ctx.current_sim_time.hour, 
                                                    self.global_ctx.current_sim_time.minute,
                                                    self.global_ctx.current_sim_time.second),
                                            self.dump_stats_car_count)

                self.dump_stats_to_file("{0}{1}\\runtime_stats\\sim_snapshot_cars_to_let_cross\\day_summary_{2}_{3}_{4}.txt"
                                            .format(myconstants.runtime_output_base_path, 
                                                    self.intersection_type_name,
                                                    self.global_ctx.current_sim_time.hour, 
                                                    self.global_ctx.current_sim_time.minute,
                                                    self.global_ctx.current_sim_time.second),
                                            self.dump_stats_cars_to_let_cross)

                self.dump_stats_to_file("{0}{1}\\runtime_stats\\sim_congestion\\day_summary_{2}_{3}_{4}.txt"
                                            .format(myconstants.runtime_output_base_path, 
                                                    self.intersection_type_name,
                                                    self.global_ctx.current_sim_time.hour, 
                                                    self.global_ctx.current_sim_time.minute,
                                                    self.global_ctx.current_sim_time.second),
                                            self.dump_stats_congestion)

                self.dump_stats_to_file("{0}{1}\\runtime_stats\\sim_snapshot_cars_on_road\\day_summary_{2}_{3}_{4}.txt"
                                            .format(myconstants.runtime_output_base_path, 
                                                    self.intersection_type_name,
                                                    self.global_ctx.current_sim_time.hour, 
                                                    self.global_ctx.current_sim_time.minute,
                                                    self.global_ctx.current_sim_time.second),
                                            self.dump_stats_cars_on_road)

                self.dump_stats_to_file("{0}{1}\\runtime_stats\\sim_snapshot_travel_time\\day_summary_{2}_{3}_{4}.txt"
                                            .format(myconstants.runtime_output_base_path, 
                                                    self.intersection_type_name,
                                                    self.global_ctx.current_sim_time.hour, 
                                                    self.global_ctx.current_sim_time.minute,
                                                    self.global_ctx.current_sim_time.second),
                                            self.dump_stats_travel_time)

                self.dump_stats_to_file("{0}{1}\\runtime_stats\\sim_snapshot_light_change_count\\day_summary_{2}_{3}_{4}.txt"
                                            .format(myconstants.runtime_output_base_path, 
                                                    self.intersection_type_name,
                                                    self.global_ctx.current_sim_time.hour, 
                                                    self.global_ctx.current_sim_time.minute,
                                                    self.global_ctx.current_sim_time.second),
                                            self.dump_stats_light_change_count)
                
            self.last_debug_dump_time = self.global_ctx.current_sim_time
        
        self.step_count = self.step_count + 1
            
        # Return TRUE if the episode should end now.
        #return self.global_ctx.current_sim_time.minute == 30
        return self.global_ctx.current_sim_time.hour == 20
        #return self.global_ctx.current_sim_time.hour == 8 and self.global_ctx.current_sim_time.minute == 30

    def clear_all_existing_run_output(self):

        myutils.clear_files_in_path(myconstants.runtime_output_base_path + self.intersection_type_name + "\\runtime_stats\\")
        myutils.clear_files_in_path(myconstants.runtime_output_base_path + self.intersection_type_name + "\\runtime_stats\\sim_snapshot_car_crossings\\")
        myutils.clear_files_in_path(myconstants.runtime_output_base_path + self.intersection_type_name + "\\runtime_stats\\sim_snapshot_cars_to_let_cross\\")
        myutils.clear_files_in_path(myconstants.runtime_output_base_path + self.intersection_type_name + "\\runtime_stats\\sim_snapshot_car_counts\\")
        myutils.clear_files_in_path(myconstants.runtime_output_base_path + self.intersection_type_name + "\\runtime_stats\\sim_snapshot_animation_data\\")
        myutils.clear_files_in_path(myconstants.runtime_output_base_path + self.intersection_type_name + "\\runtime_stats\\sim_snapshot_cars_on_road\\")
        myutils.clear_files_in_path(myconstants.runtime_output_base_path + self.intersection_type_name + "\\runtime_stats\\sim_snapshot_travel_time")
        myutils.clear_files_in_path(myconstants.runtime_output_base_path + self.intersection_type_name + "\\runtime_stats\\sim_snapshot_light_change_count")
        myutils.clear_files_in_path(myconstants.runtime_output_base_path + self.intersection_type_name + "\\runtime_stats\\sim_congestion\\")
        myutils.clear_files_in_path(myconstants.runtime_output_base_path + self.intersection_type_name + "\\runtime_stats\\visualizer_animation_frames\\")
       
        if (self.intersection_type_name == 'IntersectionML'):
            myutils.clear_files_in_path(myconstants.runtime_output_model_debug)
            myutils.clear_files_in_path(myconstants.runtime_output_model_debug + "\\weights\\")
            myutils.clear_files_in_path(myconstants.runtime_output_model_debug + "\\symbols\\")
