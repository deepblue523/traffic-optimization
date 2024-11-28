import numpy as np
import random
import os
import myutils
import keras
from PIL import Image, ImageFilter, ImageDraw
from keras.models import Sequential
from keras.layers import Dense, Conv2D, MaxPooling2D, Dropout, Flatten
from keras.preprocessing.image import img_to_array
from keras.utils import to_categorical
from keras.preprocessing import image
from sklearn.model_selection import train_test_split


outputPath = "C:\\MLCapstone_work\\training_data\\"

# load json and create model
json_file = open(outputPath + 'model.json', 'r')
loaded_model_json = json_file.read()
json_file.close()
model = keras.models.model_from_json(loaded_model_json)

# load weights into new model
model.load_weights(outputPath + "model.h5")
print("Loaded model from disk")

car_data = [[1, 1, 22], [2, 2, 55]]

# Camera will take a picture of the oncoming cars.
raw_bw_road_camera_image = myutils.capture_video_camera_image(car_data)

# Break into proposed bounding boxes.
proposed_box_road_samples = myutils.hack_road_image_into_proposed_boxes(raw_bw_road_camera_image)

# For each bounding box, detect presence of car(s) and tag the corresponding box coordinates.
predicted_samples = myutils.predict_car_presence_in_proposed_boxes(model, proposed_box_road_samples)

# Compute density vector based upon car presence.
density_pattern = myutils.compute_estimated_density_pattern(predicted_samples)

im.show()