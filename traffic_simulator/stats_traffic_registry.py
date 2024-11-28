class TrafficStatisticsRegistry():
    
    def __init__(self):

        self.stats_map_by_name = { }
        
    def register(self, stats_name, stats):

        self.stats_map_by_name[stats_name] = stats
        
    def get_stats_by_name(self, stats_name):

        return self.stats_map_by_name[stats_name]
        
    def get_stats_by_name_and_hour(self, stats_name, hour):

        fullname = stats_name + '_hour' + str(hour)
        return self.stats_map_by_name[fullname]

stats_registry = TrafficStatisticsRegistry()