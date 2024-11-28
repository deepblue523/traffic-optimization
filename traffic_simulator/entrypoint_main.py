# CUDA_VISIBLE_DEVICES = ''
from datetime import datetime
import pandas as pd
import numpy as np
import os
from neighborhood import Neighborhood
import myconstants
import tensorflow as tf
import model_functions
from sim_context import SimContext

###############################################################################
# This is the highest-level logic for the simulation.  It runs a simulation for
# two consecutive days, day 1 using non-ML logic and day 2 using ML.
###############################################################################
class main(object):
    
    # Keep track of the day number.
    day_to_start = 2
    day_to_end = day_to_start
    current_day = day_to_start

    while current_day <= day_to_end:
        global_ctx = SimContext(datetime(year=2022, month=11, day=current_day, hour=8, minute=0, second=0))

        # Type of intersection to use, either "IntersectionStock" or "IntersectionML".
        print()
        print("Setting up neighborhood...")

        if (current_day == 1):
            print("Intersection type: Stock")
            hood = Neighborhood("IntersectionStock", global_ctx, current_day)
        else:
            print("Intersection type: Enhanced")
            hood = Neighborhood("IntersectionML", global_ctx, current_day)
            
            # List available GPUs.
            print();
            print("Available GPUs:");
            print(tf.config.list_physical_devices('GPU'));
            print()
        
        # Clean out graphic debugger frames at the start of a day.
        # This project features a graphical traffic debugger built in C#.
        # "Frames" are created periodically with current state of the entire
        # neighborhood.  Those frame are drawn graphically by the .NET code.
        print()
        print("Clearing previous run output...")
        hood.clear_all_existing_run_output()

        # An episode is one day.  This loop resembles a reenforcement learning cycle
        # even though, strictly speaking, we are not using a reenforcement learning
        # solution.
        print("Beginning simulation...")

        episode_done = False
        while episode_done == False:
            # Advance the entire environment by one step.
            # The simulation collects stats during its execution as events occur.
            episode_done = hood.step()
    
        # Dump episode stats.
        print()
        print("Car crossing breakdown:")
        hood.dump_stats_to_console(hood.dump_stats_crossing_count)

        print()
        print("Congestion breakdown:")
        hood.dump_stats_to_console(hood.dump_stats_congestion)

        print()
        print("Light change breakdown:")
        hood.dump_stats_to_console(hood.dump_stats_light_change_count)

        print()
        print("Travel time breakdown:")
        hood.dump_stats_to_console(hood.dump_stats_travel_time)
        
        hood.dump_stats_to_file("{0}{1}\\runtime_stats\\day_summary_car_crossings.txt".format(myconstants.runtime_output_base_path, hood.intersection_type_name), hood.dump_stats_crossing_count)
        hood.dump_stats_to_file("{0}{1}\\runtime_stats\\day_summary_car_counts.txt".format(myconstants.runtime_output_base_path, hood.intersection_type_name), hood.dump_stats_car_count)

        # Next episode!
        current_day = current_day + 1

if __name__ == '__main__':
    main()
