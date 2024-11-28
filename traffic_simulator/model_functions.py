import numpy as np
import random
import os
import myutils
import myconstants
import keras

os.environ["TF_GPU_ALLOCATOR"]='cuda_malloc_async'

def generate_simple_regression_model(image_input, labels, model_filename):
    # partition the data into training and testing splits using 75% of
    # the data for training and the remaining 25% for testing
    #image_input = np.reshape(image_input, newshape=(1, ))
 
            
    imageShape = image_input[0].shape
    num_classes = 1

    (trainX, testX, trainY, testY) = train_test_split(image_input, labels, test_size=0.25, random_state=42)
   
        
        
    # convert the labels from integers to vectors
    #trainY = to_categorical(trainY, num_classes=2)
    #testY = to_categorical(testY, num_classes=2)

    # grab the image paths and randomly shuffle them
    model = Sequential()
    
    model.add(Conv2D(32, kernel_size=(4, 4), strides=(2, 2), activation='relu', input_shape=imageShape))
    model.add(MaxPooling2D(pool_size=(2, 2), strides=(2, 2)))
    #model.add(Conv2D(16, kernel_size=(4, 4), strides=(2, 2), activation='relu', input_shape=imageShape))
    #model.add(MaxPooling2D(pool_size=(2, 2), strides=(2, 2)))
    model.add(Flatten())
    #model.add(Dense(300, activation='relu'))
    #model.add(Dense(100, activation='relu'))
    #model.add(Dense(250, activation='relu'))
    model.add(Dense(250, activation='relu'))
    model.add(Dense(trainY.shape[1], activation='linear'))
    
    print(trainX.shape)
    print(trainY.shape)
    #trainX2 = trainX.reshape(len(trainX), 1, 1)
    #print(trainX2.shape)

    opt = keras.optimizers.Adam(learning_rate=0.000025)
    model.compile(loss='mean_squared_error', # one may use 'mean_absolute_error' as mean_squared_error
                  optimizer=opt,
                  metrics=['mean_squared_error'])

    model.summary()
    model.fit(trainX, trainY, batch_size=1, shuffle=True, epochs=50, verbose=1)

    print("Serializing model...")

    # serialize model to JSON
    model_json = model.to_json()
    with open(myconstants.training_model_path + model_filename + ".json", "w") as json_file:
        json_file.write(model_json)
        
    # serialize weights to HDF5
    model.save_weights(myconstants.training_model_path + model_filename + ".h5")
    print("Saved model to disk")

    score = model.evaluate(testX, testY)
    score_text = "%s: %.2f%%" % (model.metrics_names[1], score[1]);
    
    file_object = open(myconstants.training_model_path + model_filename + "_score.txt", "w") 
    print(score_text, file=file_object);

    print(score_text)
    value = input("Please enter a string:\n")

def generate_simple_regression_model_old(image_input, labels, model_filename):
    # partition the data into training and testing splits using 75% of
    # the data for training and the remaining 25% for testing
    #image_input = np.reshape(image_input, newshape=(1, ))
    
    imageShape = image_input[0].shape
    num_classes = 1

    (trainX, testX, trainY, testY) = train_test_split(image_input, labels, test_size=0.25, random_state=42)
   
        
        
    # convert the labels from integers to vectors
    #trainY = to_categorical(trainY, num_classes=2)
    #testY = to_categorical(testY, num_classes=2)

    # grab the image paths and randomly shuffle them
    model = Sequential()
    
    model.add(Conv2D(32, kernel_size=(4, 4), strides=(2, 2), activation='relu', input_shape=imageShape))
    model.add(MaxPooling2D(pool_size=(2, 2), strides=(2, 2)))
    model.add(Conv2D(16, kernel_size=(4, 4), strides=(2, 2), activation='relu', input_shape=imageShape))
    model.add(MaxPooling2D(pool_size=(2, 2), strides=(2, 2)))
    model.add(Flatten())
    model.add(Dense(100, activation='relu'))
    #model.add(Dense(100, activation='relu'))
    #model.add(Dense(750, activation='relu'))
    #model.add(Dense(500, activation='relu'))
    #model.add(Dense(500, activation='relu'))
    #model.add(Dense(500, activation='relu'))
    #model.add(Dense(500, activation='relu'))
    model.add(Dense(1, activation='linear'))
    
    print(trainX.shape)
    #trainX2 = trainX.reshape(len(trainX), 1, 1)
    #print(trainX2.shape)

    opt = keras.optimizers.Adam(learning_rate=0.000025)
    model.compile(loss='mean_squared_error', # one may use 'mean_absolute_error' as mean_squared_error
                  optimizer=opt,
                  metrics=['mean_squared_error'])

    model.summary()
    model.fit(trainX, trainY, batch_size=1, epochs=100, verbose=1)

    print("Serializing model...")

    # serialize model to JSON
    model_json = model.to_json()
    with open(myconstants.training_model_path + model_filename + ".json", "w") as json_file:
        json_file.write(model_json)
        
    # serialize weights to HDF5
    model.save_weights(myconstants.training_model_path + model_filename + ".h5")
    print("Saved model to disk")

    score = model.evaluate(testX, testY)
    score_text = "%s: %.2f%%" % (model.metrics_names[1], score[1]);
    
    file_object = open(myconstants.training_model_path + model_filename + "_score.txt", "w") 
    print(score_text, file=file_object);

    print(score_text)
    value = input("Please enter a string:\n")

def get_camera_model(global_ctx, force_reload):
    if global_ctx.traffic_model_near is None or force_reload:
        # Load up our trained model CNN.
        json_file = open(myconstants.training_model_path + 'model_traffic_weight.json', 'r')
        loaded_model_json = json_file.read()
        json_file.close()
        
        global_ctx.traffic_model_near = keras.models.model_from_json(loaded_model_json)

        # Load saved weights into the loaded model.
        global_ctx.traffic_model_near.load_weights(myconstants.training_model_path + "model_traffic_weight.h5")
        
    #keras.backend.clear_session()    
    return global_ctx.traffic_model_near

def get_camera_model_far(global_ctx, force_reload):
    if global_ctx.traffic_model_far is None or force_reload:
        # Load up our trained model CNN.
        json_file = open(myconstants.training_model_path + 'model_weight_far.json', 'r')
        loaded_model_json = json_file.read()
        json_file.close()
      
        global_ctx.traffic_model_far = keras.models.model_from_json(loaded_model_json)

        # Load saved weights into the loaded model.
        global_ctx.traffic_model_far.load_weights(myconstants.training_model_path + "model_weight_far.h5")
    
    #keras.backend.clear_session()    
    return global_ctx.traffic_model_far