import numpy as np
import cv2
import ws_functions
from multiprocessing import Pool
from tensorflow.keras.utils import img_to_array
import re
import myutils

def capture_still_image(camera_ws_url, camera_input):

    # Camera will take a picture of the oncoming cars.
    ws_response = ws_functions.make_rest_call_post(camera_ws_url, camera_input)

    # Process the resulting image.
    imageData = []
    image = cv2.imread(camera_input["desiredOutputFilename"])
    #image = cv2.resize(image, (200, 200))    
    image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY, dstCn=1)
    image = img_to_array(image)
    imageData.append(image)
    imageData = np.array(imageData, dtype="float") / 255.0

    return imageData

def capture_still_image2(camera_ws_url, camera_input):

    # Camera will take a picture of the oncoming cars.
    ws_functions.make_rest_call_post(camera_ws_url, camera_input)

    # Process the resulting images.
    image_data_map = { }
    
    if len(camera_input) > 0:
        for car_set in camera_input:
            filename = car_set["desiredOutputFilename"]
            match = re.search(r".*(north|south|east|west).*", filename)
            direction = match.group(1)
        
            imageData = []
            image = cv2.imread(filename)
            image = cv2.resize(image, (400, 400))
            image_as_array = img_to_array(image)
            imageData.append(image_as_array)
            imageData = np.array(imageData, dtype="float") / 255.0

            image_data_map[direction] = imageData
            image_data_map[direction + "_raw_image"] = image

    return image_data_map
 
if __name__ == '__main__':
            
    with Pool(processes=8, maxtasksperchild=10) as pool:
        results = pool.map(capture_still_image, road_orientation)
        print(results)