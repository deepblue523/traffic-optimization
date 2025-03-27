# Traffic Optimization Using Machine Learning

**Making intersections smarter to reduce driver frustration**  
*By Joe Kessler – Principal Software Developer*

## 🚦 Overview

This project implements a machine learning-driven traffic simulation for optimizing signal timing in a small city grid. The goal: reduce travel times and improve traffic flow using a Convolutional Neural Network (CNN) and real-time image data from simulated traffic cameras.

## 🧠 Motivation

- Traffic lights often use simplistic or rigid logic.
- Drivers get stuck at red lights unnecessarily.
- Poor traffic flow increases fuel usage and stress.

**Can we do better?**  
Yes—by simulating intersections that “see” traffic via cameras and respond intelligently.

---

## 🏙️ Simulation Environment

- 3×3 grid of intersections (9 total)
- Each intersection equipped with 4 cameras (North, South, East, West)
- Real-time image processing to detect traffic and make decisions
- Cars behave like agents with basic GPS routing and 40 MPH max speed

---

## 🧩 Components

| Component | Language/Tech | Description |
|----------|----------------|-------------|
| `Simulator` | Python | Core traffic simulation environment |
| `CNN Model` | Python (Keras/TensorFlow) | Detects cars and zones from camera images |
| `Training Data Generator` | C#/WinForms | Creates labeled traffic image data for training |
| `Traffic Visualizer` | C#/WinForms | Visual display of traffic activity |
| `CameraWS` | C#/ASP.NET | Simulated camera feed for intersections |

---

## 📷 Neural Network: CNN for Traffic Vision

The CNN processes images from simulated cameras to:

- Count vehicles in each lane
- Estimate vehicle distance in three zones: **Far**, **Middle**, **Near**
- Output 9 values per image (3 lanes × 3 distance zones)

### Sample Model Code

```python
model = Sequential()
model.add(Conv2D(32, (5, 5), activation='relu', input_shape=imageShape))
model.add(MaxPooling2D((2, 2)))
model.add(Conv2D(32, (5, 5), activation='relu'))
model.add(MaxPooling2D((2, 2)))
model.add(Flatten())
model.add(Dense(100, activation='relu'))
model.add(Dense(100, activation='relu'))
model.add(Dense(9, activation='sigmoid'))

model.compile(optimizer='rmsprop', loss='mean_squared_error', metrics=['accuracy'])
model.fit(trainX, trainY, batch_size=1, epochs=250, verbose=1)
```

---

## 🏃 Running the Simulation

Once the CNN is trained, it integrates seamlessly into the simulator:

1. Capture images from all 4 directions via `CameraWS`.
2. Predict vehicle presence using CNN.
3. Use simple logic to decide if a light should switch.

Example (simplified):

```python
images = capture_image(myconstants.camera_ws_url)
for direction in images:
    prediction = model_cnn.predict(images[direction])
    traffic_scenario = TrafficScenario(self, prediction, road_lanes, self.global_ctx)
    predictions[direction] = traffic_scenario
```

---

## 📊 Results

- **Same car throughput**
- **~50% fewer signal changes**
- **~14% lower congestion**
- **~11% lower travel times**
- Drivers maintain momentum better—fewer “stop-and-go” scenarios

---

## 🛠️ Hardware Used

- Intel Core i7-12700K
- 128GB DDR4-3600 RAM
- NVIDIA RTX 3090 Ti (24GB VRAM)

---

## 🙋 Questions?

This was originally a video presentation!  
For questions/comments, reach out to **Joe Kessler**.  
There’s no complaint box… yet.
