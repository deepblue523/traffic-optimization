import numpy as np
from road_lanes_one_direction import RoadLanesOneDirection
from light_post import LightPost
from stats_traffic import TrafficStatistics
    
#########################################################################################
# Represent a stretch of road, ecapsulating two instances of 'RoadLanesOneDirection'
# objects going in opposite directions.
#########################################################################################
class RoadSegment:

    def __init__(self, name, orientation, speed_limit, cars, stats_rollup, global_ctx):

        self.name = name
        self.orientation = orientation
        self.speed_limit = speed_limit
        self.cars = cars
        self.cars_on_this_segment = []
        self.global_ctx = global_ctx

        if (orientation == "north/south"):
            self.direction1 = "north"
            self.direction2 = "south"
        else:
            self.direction1 = "east"
            self.direction2 = "west"

        name1 = self.name + "/" + self.direction1
        name2 = self.name + "/" + self.direction2
        
        # Set up light posts and road lanes.
        self.stats = TrafficStatistics(name + " " + self.direction1 + "/" + self.direction2, [ stats_rollup ], self.global_ctx, False)
        light_post1 = LightPost(self.name + "/" + self.direction1, self.stats, self.global_ctx)
        light_post2 = LightPost(self.name + "/" + self.direction2, self.stats, self.global_ctx)
        
        self.lane_set1 = RoadLanesOneDirection(name1, light_post1, self.speed_limit, self.direction1, self.cars, self.cars_on_this_segment, self.stats, self.global_ctx)
        self.lane_set2 = RoadLanesOneDirection(name2, light_post2, self.speed_limit, self.direction2, self.cars, self.cars_on_this_segment, self.stats, self.global_ctx)
        self.lane_sets = [ self.lane_set1, self.lane_set2 ]
        
        # Relink the light posts to to the correct lanes.
        light_post1.stats.rollup_stats = self.lane_set1.stats 
        light_post2.stats.rollup_stats = self.lane_set2.stats 

    def get_lanes_going_direction(self, direction):

        if (direction == "north"):
            return self.lane_set1 
        elif (direction == "south"):
            return self.lane_set2 
        elif (direction == "east"):
            return self.lane_set1
        else :
            return self.lane_set2 
