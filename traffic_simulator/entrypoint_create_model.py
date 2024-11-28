import numpy as np
import random
import os
import cv2
import myutils
import myconstants
import model_functions
from keras.models import Sequential
from keras.layers import Dense, Conv2D, MaxPooling2D, Dropout, Flatten
from tensorflow.keras.utils import img_to_array
from keras.utils import to_categorical
import keras
from keras.layers import Input
from sklearn.model_selection import train_test_split
from sklearn import preprocessing
from PIL import Image, ImageFilter, ImageDraw

enable_model_weight_weights = True
enable_model_first_positions = False

# Load entire train/test dataset
training_csv_filename = myconstants.training_data_path + "traffic_metadata.csv"
training_image_path_near = myconstants.training_data_path + "images\\"

if enable_model_weight_weights == True:
    trainy_col_names = ['left_near', 'left_middle', 'left_far', 'right_near', 'right_middle', 'right_far', 'turn_near', 'turn_middle', 'turn_far'] 
    imageData, labels_frustration_factor_normalized, labels_left_turn = myutils.load_training_data(training_csv_filename, training_image_path_near, trainy_col_names)
    model_functions.generate_simple_regression_model(imageData, labels_frustration_factor_normalized, "model_traffic_weight")

if enable_model_first_positions == True:
    trainy_col_names = [ 'first_car_pos_left', 'first_car_pos_right', 'first_car_pos_turn' ]

    imageData, labels_frustration_factor_normalized, labels_left_turn = myutils.load_training_data(training_csv_filename, training_image_path_near, trainy_col_names)
    model_functions.generate_simple_regression_model(imageData, labels_frustration_factor_normalized, "model_first_positions")
