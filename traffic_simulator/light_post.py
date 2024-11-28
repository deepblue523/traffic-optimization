from datetime import timedelta
from stats_traffic import TrafficStatistics

#########################################################################################
# This class is a simple state holder for a light post going in one direction.
#########################################################################################
class LightPost:

    def __init__(self, road_segment, stats_rollup, global_ctx):

        self.global_ctx = global_ctx
        self.light_state_main = "red"
        self.light_state_left_turn = "red"
        self.stats = TrafficStatistics("light_" + road_segment, [ ], self.global_ctx, False)
        self.actual_total_light_changes = 0
        self.intersection = None
        self.last_light_change = global_ctx.current_sim_time
        self.last_main_stop = global_ctx.current_sim_time
        self.last_main_green = global_ctx.current_sim_time

    def stop(self):
        
        self.set_light_state_both("red", "red");
        
    def set_light_state_both(self, state_main, state_left_turn):

        self.set_light_state_main(state_main)
        self.set_light_state_left_turn(state_left_turn)

    def set_light_state_main(self, state_main):
        
        if (self.light_state_main != state_main):
            self.light_state_main = state_main
            self.actual_total_light_changes = self.actual_total_light_changes + 1
            self.intersection.dynamic_green_light_ext_seconds = timedelta(seconds=0)
            self.last_light_change = self.global_ctx.current_sim_time

            if (state_main == "red"):
                self.last_main_stop = self.global_ctx.current_sim_time
            elif (state_main == "green"):
                self.last_main_green = self.global_ctx.current_sim_time
                self.intersection.stats.increment_light_change_count(1) # For now, increment only upon 'main' green change.
            
    def set_light_state_left_turn(self, state_left_turn):

        if (self.light_state_left_turn != state_left_turn):
            self.light_state_left_turn = state_left_turn
            self.actual_total_light_changes = self.actual_total_light_changes + 1
            self.intersection.dynamic_green_light_ext_seconds = timedelta(seconds=0)
            self.last_light_change = self.global_ctx.current_sim_time

    def is_at_all_stop(self):

        return (self.light_state_main == "red") and (self.light_state_left_turn == "red")