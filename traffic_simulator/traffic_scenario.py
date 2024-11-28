from enum import Flag, auto
from math import ceil

# Traffic flow strategies.
TRAFFIC_NONE = 0
TRAFFIC_LOW = 1
TRAFFIC_MODERATE = 2
TRAFFIC_HEAVY = 3

class TrafficScenarioLane():
    def __init__(self, intersection, road_lanes, global_ctx):
        super().__init__()
        
        self.traffic_near = int(0)
        self.traffic_middle = int(0)
        self.traffic_far = int(0)
        self.intersection = intersection
        self.road_lanes = road_lanes
        self.global_ctx = global_ctx
        self.initial_sim_time = global_ctx.current_sim_time
        
    def has_no_traffic(self):

        return (self.traffic_near == 0) and \
               (self.traffic_middle == 0) and \
               (self.traffic_far == 0) 
        
    def has_any_traffic(self):

        return (self.traffic_near != 0) or \
               (self.traffic_middle != 0) or \
               (self.traffic_far != 0) 
        
    def get_total_traffic(self):

        return self.traffic_near + self.traffic_middle + self.traffic_far

    def get_traffic(self, include_near, include_middle, include_far):
        
        total = 0
        
        if include_near:
            total = total + self.traffic_near
        if include_middle:
            total = total + self.traffic_middle
        if include_far:
            total = total + self.traffic_far
                    
        return total
    
    def get_momentum(self):
    
        #return self.traffic_near
    
        momentum = 0      
        momentum += self.traffic_near / 1.5
        momentum += self.traffic_middle / 5.0
        momentum += self.traffic_far / 10

        if self.road_lanes.light_post.light_state_main == "green":
            total_seconds = 0
        else:
            total_seconds = (self.global_ctx.current_sim_time - self.road_lanes.light_post.last_main_stop).total_seconds()

        if self.road_lanes.are_cars_at_main_trip() == True:
            momentum_adj = 1 + total_seconds * 0.050
        else:
            momentum_adj = 1 + total_seconds * 0.040

        momentum *= momentum_adj

        return momentum
    
class TrafficScenario():
    def __init__(self, intersection, road_lanes, global_ctx):
        super().__init__()
        
        self.orientation = ''
        self.intersection = intersection
        self.road_lanes = road_lanes
        self.global_ctx = global_ctx
        self.traffic_left = TrafficScenarioLane(intersection, road_lanes, global_ctx)
        self.traffic_right = TrafficScenarioLane(intersection, road_lanes, global_ctx)
        self.traffic_turn = TrafficScenarioLane(intersection, road_lanes, global_ctx)
       
    def has_no_traffic(self):

        return self.traffic_left.has_no_traffic() and \
               self.traffic_middle.has_no_traffic() and \
               self.traffic_far.has_no_traffic()
        
    def has_any_traffic(self):

        return self.traffic_near.has_any_traffic() or \
               self.traffic_middle.has_any_traffic() or \
               self.traffic_far.has_any_traffic()
        
    def get_total_traffic(self):

        return self.traffic_left.get_total_traffic() + \
               self.traffic_right.get_total_traffic() + \
               self.traffic_turn.get_total_traffic()
        
    def get_main_traffic(self):

        return self.traffic_left.get_total_traffic() + \
               self.traffic_right.get_total_traffic() 
    
    def has_main_traffic(self):
        return self.get_main_traffic() > 0
    
    def has_no_main_traffic(self):
        return self.get_main_traffic() == 0
    
    def has_turn_lane_traffic(self):
        return self.traffic_turn.get_total_traffic() > 0
    
    def get_traffic(self, include_near, include_middle, include_far):
        
        return self.traffic_left.get_traffic(include_near, include_middle, include_far) + \
               self.traffic_right.get_traffic(include_near, include_middle, include_far) + \
               self.traffic_turn.get_traffic(include_near, include_middle, include_far)

                    
        return total
    
    def get_traffic_no_turn(self, include_near, include_middle, include_far):
        
        return self.traffic_right.get_traffic(include_near, include_middle, include_far) + \
               self.traffic_turn.get_traffic(include_near, include_middle, include_far)

                    
        return total

    def get_momentum(self):

        #return self.traffic_left.get_momentum() + self.traffic_right.get_momentum()
        return max(self.traffic_left.get_momentum(), self.traffic_right.get_momentum())
    

def get_combined_momentum(traffic_scenario1, traffic_scenario2):

    return traffic_scenario1.get_momentum() + traffic_scenario2.get_momentum()
    #return max(traffic_scenario1.get_momentum(), traffic_scenario2.get_momentum())
    