from random import randint
import myconstants

#########################################################################################
# Encapsulates directions regarding how a driver can navigate from one point to another.
# The route is handled as a series of turns, with labels such as 'north'/'south'/etc,
# and those turns are applied as a car reaches each intersection.  The array of steps
# ultimately comes from the Neighborhood object __init__() method.
#########################################################################################
class RouteMap:

    def __init__(self, global_ctx, all_road_segments):

        self.id = id
        self.global_ctx = global_ctx
        self.all_road_segments = all_road_segments
        self.road_segment = None
        self.road_lanes = None
        
        self.generateRouteMap()

    def generateRouteMap(self):
        
        turn_probability_pct = 10
        allow_left_turns = True
        allow_right_turns = False
        
        # Create a route map for this volume pattern.
        self.route_map = []
        
        # Get random first starting point
        rnd_idx = randint(0, len(myconstants.road_segment_valid_starting_points) - 1)
        first_segment_name = myconstants.road_segment_valid_starting_points[rnd_idx]
        
        self.road_segment = None
        self.road_lanes = None
        for road_segment in self.all_road_segments:
            for lane_set in road_segment.lane_sets:
                if lane_set.name == first_segment_name:
                    self.road_segment = road_segment
                    self.road_lanes = lane_set
                    break

            if self.road_segment != None:
                break
           
        # Move in random directions.       
        valid_initial_direction = [ ]
        if ('north' in first_segment_name):
            valid_initial_direction.append('north') 
        if ('south' in first_segment_name):
            valid_initial_direction.append('south')
        if ('east' in first_segment_name):
            valid_initial_direction.append('east')
        if ('west' in first_segment_name):
            valid_initial_direction.append('west')
                
        current_direction = valid_initial_direction[randint(0, len(valid_initial_direction) - 1)]
        self.route_map.append(current_direction)
           
        loopIdx = 0
        while loopIdx < 4:
            # Find valid next direction.
            valid_next_direction = [ ]
            
            if ('north' in current_direction):
                if allow_left_turns == True:
                    valid_next_direction.append('west')
                if allow_right_turns == True:
                    valid_next_direction.append('east')
                
            elif ('south' in current_direction):
                if allow_left_turns == True:
                    valid_next_direction.append('east')
                if allow_right_turns == True:
                    valid_next_direction.append('west')

            elif ('west' in current_direction):
                if allow_left_turns == True:
                    valid_next_direction.append('south')
                if allow_right_turns == True:
                    valid_next_direction.append('north')

            elif ('east' in current_direction):
                if allow_left_turns == True:
                    valid_next_direction.append('north')
                if allow_right_turns == True:
                    valid_next_direction.append('south')
                
            # Get random next segment
            next_direction = current_direction
            
            if len(valid_next_direction) > 0:
                if randint(0, 99) < turn_probability_pct:         # Turn?
                    rnd_idx = randint(0, len(valid_next_direction) - 1)
                    next_direction = valid_next_direction[rnd_idx]

            self.route_map.append(next_direction)
            current_direction = next_direction
            loopIdx = loopIdx + 1
        
        self.route_map.append(None)
        self.route_directions = self.route_map
        return self.route_map

    #########################################################################################
    # Returns the initial direction of a car following this route.
    #########################################################################################
    def get_initial_direction(self):

        return self.route_directions[0]

    #########################################################################################
    # Given the "index" of the last turn made, this method returns the next one.  If the
    # we've reached our destination then None is returned.  Otherwise a string such as 
    # 'north'/'south'/etc is sent back.
    #########################################################################################
    def get_next_direction(self, last_direction_idx):

        next_direction = last_direction_idx + 1

        if next_direction >= len(self.route_directions):
            return None
        else:
            return self.route_directions[next_direction]
            
    #########################################################################################
    # Given the current direction, determines if the next turn will be a left turn.  Other
    # possibilities include a right turn or simply going straight (no direction change).
    #########################################################################################
    def is_left_turn(self, starting_direction, new_direction):

        if (starting_direction == "west" and new_direction == "south"):
            return True
        elif (starting_direction == "east" and new_direction == "north"):
            return True
        elif (starting_direction == "north" and new_direction == "west"):
            return True
        elif (starting_direction == "south" and new_direction == "east"):
            return True
        else:
            return False

    def is_right_turn(self, starting_direction, new_direction):

        if (starting_direction == "west" and new_direction == "north"):
            return True
        elif (starting_direction == "east" and new_direction == "south"):
            return True
        elif (starting_direction == "north" and new_direction == "east"):
            return True
        elif (starting_direction == "south" and new_direction == "west"):
            return True
        else:
            return False
