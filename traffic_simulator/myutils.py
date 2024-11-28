import numpy as np
import random
import os
import glob
import cv2
import pandas as pd
import myconstants
from keras.models import Sequential
from keras.layers import Dense, Conv2D, MaxPooling2D, Dropout, Flatten
from tensorflow.keras.utils import img_to_array
from keras.utils import to_categorical
from sklearn.model_selection import train_test_split
from PIL import Image, ImageFilter, ImageDraw

def load_training_data(csvFilename, imagePath, trainy_col_names):

    # Read CSV file into DataFrame df
    print("Reading training data index...")
    df = pd.read_csv(csvFilename, index_col=0)

    # Show dataframe
    print(df)
    
    imageData = []
    frustration_factor_labels = []
    left_turn_labels = []
    
    # loop over the input images
    print("Loading image data...")
    readCount = 0
    
    for index, row in df.iterrows():
        filepath_this_image = imagePath + row['image_filename']

        # load the image, pre-process it, and store it in the data list.
        image = cv2.imread(filepath_this_image)
        image = cv2.resize(image, (400, 400))   

        #image = process_camera_image(image)
        image = img_to_array(image)
        #image = image.flatten()

        #image = img_to_array(image)
        #cv2.imwrite('c:\\work4\\processed_' + row['image_filename'], image)
        #image = image.flatten()
        imageData.append(image)

        # extract the class labels for the image.
        row_values = []
        for col_name in trainy_col_names:
            row_values.append(row[col_name])
            
        frustration_factor_labels.append(row_values)
        left_turn_labels.append(row['car_count'])

        readCount = readCount + 1
        if (readCount % 100) == 0:
            print(f"Images read: {readCount}")
           
        if (readCount % 10000) == 0:
            break
            
    if (readCount % 100) != 0:
        print(f"Images read: {readCount}")

    imageData = np.array(imageData, dtype="float") / 255.0

    # scale the raw pixel intensities to the range [0, 1]
    labels_frustration_factor = np.array(frustration_factor_labels)
    labels_left_turn = np.array(left_turn_labels)

    # convert frustration in %ages.
    #labels_frustration_factor_norm = (labels_frustration_factor-np.min(labels_frustration_factor))/(np.max(labels_frustration_factor)-np.min(labels_frustration_factor))
    
    return imageData, labels_frustration_factor, labels_left_turn

def process_camera_image(image):

        color = (0, 0, 0)
        image = cv2.rectangle(image, (0, 0), (14, 800), color, -1)
        image = cv2.rectangle(image, (121, 0), (138, 800), color, -1)
        image = cv2.rectangle(image, (0, 0), (138, 18), color, -1)

        image = cv2.rectangle(image, (31, 0), (33, 800), color, -1)
        image = cv2.rectangle(image, (52, 0), (54, 800), color, -1)
        image = cv2.rectangle(image, (73, 0), (77, 800), color, -1)
        image = cv2.rectangle(image, (98, 0), (100, 800), color, -1)
                
        image[np.all(image == (54, 52, 46), axis=-1)] = (0,0,0)
        image[np.all(image == (14, 201, 255), axis=-1)] = (0,0,0)
        image[np.all(image == (34, 126, 150), axis=-1)] = (0,0,0)
        image[np.all(image == (24, 164, 203, 150), axis=-1)] = (0,0,0)
        image[np.all(image == (44, 89, 98), axis=-1)] = (0,0,0)
        
        image = image[21:800, 15:98] 
         
        #image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY, dstCn=1)
        #image = cv2.threshold(image, 0, 255,cv2.THRESH_BINARY)[1]
        #image = cv2.resize(image, (200, 200))   

        return image
    
def draw_one_car(background, car_style_id, lane_id, front_bumper_pos):

    # Read image of car in the given style.
    car = Image.open( 'C:\\MLCapstone_work\\images\\up\\Car' + str(car_style_id + 1) + '_Half_Up.png' )

    # Position based upon lane number.
    xpos = 0
    if (lane_id == 1):
        xpos = 56
    elif (lane_id == 2):
        xpos = 78
    else:
        xpos = 100

    offset = xpos, int(front_bumper_pos) #, xpos + im2.width, front_bumper_pos + im2.height

    # Draw into the blank image
    car = car.convert('RGB')

    background = background.paste(car, offset)

def capture_video_camera_image(car_position_data):

    # Read background road image
    background = Image.open( 'C:\\MLCapstone_work\\images\\Oncoming Traffic - Empty - Half.png' )
    #background = cv2.cvtColor(background, cv2.COLOR_BGR2GRAY)

    for style_id, lane_id, front_bumper_pos in car_position_data:
        if (front_bumper_pos < 700):
            draw_one_car(background, style_id, lane_id, front_bumper_pos)

    return background

def hack_road_image_into_proposed_boxes(road_image):

    image_samples = []

    for yPos in range(22, 700, 50):
        box_bounds = [0, yPos, 137, yPos + 50]
        
        image_sample = road_image.copy()
        image_sample = image_sample.crop(box_bounds)
        image_samples.append([box_bounds[0], box_bounds[1], box_bounds[2], box_bounds[3], image_sample])

    return image_samples

def predict_car_presence_in_proposed_boxes(model, road_samples):
    
    predicted_samples = []

    for sample in road_samples:
        work_image = img_to_array(sample[4])
        work_image = np.expand_dims(work_image, axis = 0)

        contains_cars = model.predict(work_image)

        predicted_samples.append([sample, contains_cars[0][0]])

    return predicted_samples

def compute_estimated_density_pattern(predicted_samples):

    density_buckets = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    bucket_size = 750 / len(density_buckets)

    for sample in predicted_samples:

        if sample[1] == 1:
            # Determine which bucket this sample goes into.
            bucket_idx = int((sample[1] - 22) / bucket_size)

            density_buckets[bucket_idx] = density_buckets[bucket_idx] + 1

    return density_buckets

def clear_files_in_path(path_abs):

    fileList = os.listdir(path_abs)
    for fileName in fileList:
        if os.path.isfile(path_abs + fileName):
            os.remove(path_abs + fileName)

def clear_files_in_path_wildcard(path_abs):

    # Get a list of all the marching file paths.
    fileList = glob.glob(path_abs)

    # Iterate over the list of filepaths & remove each file.
    for filePath in fileList:
        try:
            os.remove(filePath)
        except:
            print("Error while deleting file : ", filePath)

def get_reverse_direction(direction):

    if direction == 'east':
        return 'west'
    elif direction == 'west':
        return 'east'
    elif direction == 'north':
        return 'south'
    else:
        return 'north'
    

#########################################################################################
# Return left X position of the lane.
#########################################################################################
def get_lane_leftx_pos(lane_id):
        
    if (lane_id == 1):
        return 100
    elif (lane_id == 2):
        return 77
    else: 
        return 55

#########################################################################################
# Given a direction, produces the opposite direction.  For example, a parameter of 
# 'north'  would return 'south'.
#########################################################################################
def get_opposite_direction(direction):

    if (direction == "north"):
        return "south" 
    elif (direction == "south"):
        return "north"
    elif (direction == "east"):
        return "west"
    else :
        return "east"
