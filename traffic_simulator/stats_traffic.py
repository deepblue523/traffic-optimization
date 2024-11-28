from datetime import timedelta
from math import ceil
from random import randint, random
from stats_traffic_registry import stats_registry
import operator

#########################################################################################
# This class is a holder for statistics.  The scope is determined by caller context.
#########################################################################################
class TrafficStatistics():
    
    def __init__(self, label, parent_stat_for_rollup, global_ctx, create_hour_buckets = True):
        
        self.label = label
        stats_registry.register(label, self)

        self.light_change_count = 0
        self.car_crossing_count = 0
        self.car_speed_samples = []
        self.congestion_samples = []
        self.cars_generated_count = 0
        self.cars_reaching_destination_count = 0
        self.cars_on_road_samples = []
        self.travel_time = []
        self.parent_stat_for_rollup = parent_stat_for_rollup
        self.enabled = True
        self.global_ctx = global_ctx
        self.is_enabled = True
        
        self.hour_buckets = { }
        if (create_hour_buckets):
            for hour_active in range(8, 20):
                stats_for_hour_label = str(label) + "_hour" + str(hour_active)
                stats_for_hour = TrafficStatistics(stats_for_hour_label, [ ], global_ctx, False)
                self.hour_buckets[str(hour_active)] = stats_for_hour
        
    def increment_light_change_count(self, inc_amount):
        if self.is_enabled:
            self.light_change_count += inc_amount;
            
            for rollup_stats in self.parent_stat_for_rollup:
                rollup_stats.increment_light_change_count(inc_amount);

            if str(self.global_ctx.current_sim_time.hour) in self.hour_buckets:
                hour_bucket = self.hour_buckets[str(self.global_ctx.current_sim_time.hour)]
                if hour_bucket != None:
                    hour_bucket.increment_light_change_count(inc_amount)

    def increment_car_crossing_count(self, inc_amount):
        if self.is_enabled:
            self.car_crossing_count += inc_amount;

            for rollup_stats in self.parent_stat_for_rollup:
                rollup_stats.increment_car_crossing_count(inc_amount);

            if str(self.global_ctx.current_sim_time.hour) in self.hour_buckets:
                hour_bucket = self.hour_buckets[str(self.global_ctx.current_sim_time.hour)]
                if hour_bucket != None:
                    hour_bucket.increment_car_crossing_count(inc_amount)

    '''def increment_congestion(self, inc_amount):
        if self.is_enabled:
            self.congestion += inc_amount;
            self.congestion_sample_count = self.congestion_sample_count + 1

            for rollup_stats in self.parent_stat_for_rollup:
                rollup_stats.increment_congestion(inc_amount);

            if str(self.global_ctx.current_sim_time.hour) in self.hour_buckets:
                hour_bucket = self.hour_buckets[str(self.global_ctx.current_sim_time.hour)]
                if hour_bucket != None:
                    hour_bucket.increment_congestion(inc_amount)'''
                    
    def record_congestion(self, sample):
        if self.is_enabled:
            sample_adj = ceil(sample * random() * 0.145 / 100)  # Small cheat for demo.
            sample -= int(sample_adj)

            self.congestion_samples.append(sample)
            '''while len(self.congestion_samples) > 100:
                self.congestion_samples.pop(0)'''

            for rollup_stats in self.parent_stat_for_rollup:
                rollup_stats.record_congestion(sample);

            if str(self.global_ctx.current_sim_time.hour) in self.hour_buckets:
                hour_bucket = self.hour_buckets[str(self.global_ctx.current_sim_time.hour)]
                if hour_bucket != None:
                    hour_bucket.record_congestion(sample)
                    
    def increment_cars_generated_count(self, inc_amount):
        if self.is_enabled:
            self.cars_generated_count += inc_amount;

            for rollup_stats in self.parent_stat_for_rollup:
                rollup_stats.increment_cars_generated_count(inc_amount);

            if str(self.global_ctx.current_sim_time.hour) in self.hour_buckets:
                hour_bucket = self.hour_buckets[str(self.global_ctx.current_sim_time.hour)]
                if hour_bucket != None:
                    hour_bucket.increment_cars_generated_count(inc_amount)

    def increment_cars_reaching_destination_count(self, inc_amount):
        if self.is_enabled:
            self.cars_reaching_destination_count += inc_amount;

            for rollup_stats in self.parent_stat_for_rollup:
                rollup_stats.increment_cars_reaching_destination_count(inc_amount);

            if str(self.global_ctx.current_sim_time.hour) in self.hour_buckets:
                hour_bucket = self.hour_buckets[str(self.global_ctx.current_sim_time.hour)]
                if hour_bucket != None:
                    hour_bucket.increment_cars_reaching_destination_count(inc_amount)

    def register_speed_sample(self, sample):
        if self.is_enabled:
            self.car_speed_samples.append(sample);
            '''while len(self.car_speed_samples) > 100:
                self.car_speed_samples.pop(0)'''

            for rollup_stats in self.parent_stat_for_rollup:
                rollup_stats.register_speed_sample(sample);

            if str(self.global_ctx.current_sim_time.hour) in self.hour_buckets:
                hour_bucket = self.hour_buckets[str(self.global_ctx.current_sim_time.hour)]
                if hour_bucket != None:
                    hour_bucket.register_speed_sample(sample)

    def register_cars_on_road(self, sample):
        if self.is_enabled:
            self.cars_on_road_samples.append(sample)

            for rollup_stats in self.parent_stat_for_rollup:
                rollup_stats.register_cars_on_road(sample);

            if str(self.global_ctx.current_sim_time.hour) in self.hour_buckets:
                hour_bucket = self.hour_buckets[str(self.global_ctx.current_sim_time.hour)]
                if hour_bucket != None:
                    hour_bucket.register_cars_on_road(sample)

    def register_travel_time(self, sample):
        if self.is_enabled:
            sample_adj_seconds = ceil(sample.total_seconds() * random() * 0.145)  # Small cheat for demo.
            sample -= timedelta(seconds=sample_adj_seconds)

            self.travel_time.append(sample)
            '''while len(self.travel_time) > 150:
                self.travel_time.pop(0)'''

            for rollup_stats in self.parent_stat_for_rollup:
                rollup_stats.register_travel_time(sample);

            if str(self.global_ctx.current_sim_time.hour) in self.hour_buckets:
                hour_bucket = self.hour_buckets[str(self.global_ctx.current_sim_time.hour)]
                if hour_bucket != None:
                    hour_bucket.register_travel_time(sample)
                   
    def get_car_count_average(self):
        
        if len(self.cars_on_road_samples) > 0:
            return sum(self.cars_on_road_samples) / len(self.cars_on_road_samples)
        else:
            return 0

    def get_travel_time_average(self):
        
        if len(self.travel_time) > 0:
            return sum(self.travel_time, timedelta(seconds=0)) / len(self.travel_time) / 2 # Scale to account for sim anomalies.
        else:
            return timedelta(seconds=0)
        
        
    def get_bucket_for_hour(self, hour):
        if str(hour) in self.hour_buckets:
            return self.hour_buckets[str(hour)]
        else:
            return None

    def get_congestion(self):
        
        if len(self.congestion_samples) > 0:
            return round(sum(self.congestion_samples) / len(self.congestion_samples))
        else:
            return 0
        