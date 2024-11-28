#########################################################################################
# Application constants gathered here for convenience.
#########################################################################################

#CUDA_VISIBLE_DEVICES = ''

# Location of the training data (for the CNN).
from datetime import timedelta

training_data_path = "C:\\BWHacker2023\\training_data\\"
training_model_path = "C:\\BWHacker2023\\models\\"

# Location of the output/working data.
runtime_output_base_path = "C:\\BWHacker2023\\runtime_output\\"
runtime_output_camera_path = "C:\\BWHacker2023\\runtime_output\\IntersectionML\\camera\\"
runtime_output_model_debug = "C:\\BWHacker2023\\runtime_output\\IntersectionML\\model_debug\\"

# REST information for the camera service.
#camera_ws_url = "http://localhost:5065/TrafficCameraWS/CaptureWithPerspective"
camera_ws_url = "http://localhost:5065/TrafficCameraWS/Capture"

# Length of a road segment.
road_segment_length = 5500

# Constant allowing us to control the level of traffic at a global level.
traffic_volume_factor = 0.070
fixed_volume_per_hour = 0

# Minimum time a green light should remain green.  We can't just keep switching lights.
minimum_seconds_for_green_light_stock = 180
maximum_seconds_for_green_light_stock = 110
minimum_seconds_for_green_light_ml = 60
maximum_seconds_for_green_light_ml = timedelta(seconds=150)
light_change_variance_stock = 10

timeout_left_turn_signal = 120
left_turn_trip_span = 50
left_turn_speed = 100  # Lower is faster.

all_stop_interval = timedelta(seconds=15)

# Max speed limit.
global_speed_limit = 40
car_acceleration_factor = 0.15

# Number of 'sim seconds' of advancement between each environment 'step'.
sim_timestep_seconds = 2
steps_per_hour = 3600 / sim_timestep_seconds
steps_per_minute = 60 / sim_timestep_seconds

# Time ('sim' seconds) between intersection camera snapshots.
seconds_between_camera_snapshots = sim_timestep_seconds #* 3

# Number of "sim seconds" between debug frame generation.  Basically, the debugger resolution.
sim_seconds_between_debugger_frames = sim_timestep_seconds * 3
enable_ml_weight_debug = False
        
# Other.
one_hour_seconds = 60 * 60
car_length = 41
next_car_id = 1

# Location/road segment map.
road_segment_of_location = {
            "residential1":         6,
            "residential2":         9,
            "residential3":         10,
            "residential4":         13,
            "office1":              9,
            "office2":              12,
            "office3":              17,
            "office4":              13,
            "playground":           5,
            "cityhall":             20,
            "mall":                 19,
            "forestpreserve":       8,
            "through_N1":           22,
            "through_N2":           23,
            "through_N3":           24,
            "through_S1":           1,
            "through_S2":           2,
            "through_S3":           3,
            "through_E1":           4,
            "through_E2":           11,
            "through_E3":           18,
            "through_W1":           7,
            "through_W2":           14,
            "through_W3":           21,
            "through":              100, # Dummy value.
            "R1":                   1,
            "R2":                   2,
            "R3":                   3,
            "R4":                   4,
            "R5":                   5,
            "R6":                   6,
            "R7":                   7,
            "R8":                   8,
            "R9":                   9,
            "R10":                  10,
            "R11":                  11,
            "R12":                  12,
            "R13":                  13,
            "R14":                  14,
            "R15":                  15,
            "R16":                  16,
            "R17":                  17,
            "R18":                  18,
            "R19":                  19,
            "R20":                  20,
            "R21":                  21,
            "R22":                  22,
            "R23":                  23,
            "R24":                  24,
            }

precomputed_routes = []

road_segment_map_exits = {
        "R1/north",  "R2/north",  "R3/north",
        "R22/south", "R23/south", "R24/south",
        "R7/east",   "R14/east",  "R21/east",
        "R4/west",   "R11/west",  "R18/west",
    }

road_segment_valid_starting_points = [
        "R1/south",  
        "R2/south",  
        "R3/south",
        "R4/east",   
        "R5/east", "R5/west",
        "R6/east", "R6/west",
        "R7/west",   
        "R8/north", "R8/south",
        "R9/north", "R9/south",
        "R10/north", "R10/south", 
        "R11/east", 
        "R12/east", "R12/west", 
        "R13/east", "R13/west", 
        "R14/west",  
        "R15/north", "R15/south", 
        "R16/north", "R16/south", 
        "R17/south", 
        "R18/east",
        "R19/east", "R19/west", 
        "R20/east", "R20/west", 
        "R21/west", 
        "R22/north", 
        "R23/north",  
        "R24/north",
]
