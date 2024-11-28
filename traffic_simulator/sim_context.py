import myconstants

class SimContext():
    
    def __init__(self, current_sim_time):
        
        self.current_sim_time = current_sim_time
        self.traffic_model_near = None
        self.traffic_model_far = None
        
        self.road_segment_valid_starting_points_remaining = []
        for starting_point in myconstants.road_segment_valid_starting_points:
            self.road_segment_valid_starting_points_remaining.append(starting_point)
        