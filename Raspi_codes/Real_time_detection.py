import tensorflow as tf
from tensorflow.keras.preprocessing.image import img_to_array
from picamera.array import PiRGBArray
from picamera import PiCamera
from subprocess import call 
import numpy as np
import cv2
import time

from notifier import alert_send

# loading the stored model from file
interpreter = tf.lite.Interpreter(model_path="/home/pi/Desktop/Raspi_codes/lite_model.tflite")
interpreter.allocate_tensors()
input_details = interpreter.get_input_details()
output_details= interpreter.get_output_details()
interpreter.resize_tensor_input(input_details[0]['index'],(1,64,64,3))
interpreter.resize_tensor_input(output_details[0]['index'], [1,3])
interpreter.allocate_tensors()

#flags
alert=0
flag=0

# initialize the camera and grab a reference to the raw camera capture
camera = PiCamera()
camera.resolution = (640, 480)
camera.framerate = 30
rawCapture = PiRGBArray(camera, size=(640, 480))
# allow the camera to warmup
time.sleep(0.1)

# capture frames from the camera
for frame in camera.capture_continuous(rawCapture, format="bgr", use_video_port=True): 
	# grab the raw NumPy array representing the image, then initialize the timestamp
	# and occupied/unoccupied text
	image = frame.array
	
	# show the frame
	orig = image.copy()
	
	#process the frame for prediction
	image = cv2.resize(image, (64, 64))
	image = image.astype("float") / 255.0
	image = img_to_array(image)
	image = np.expand_dims(image, axis=0)
	
	#pass the frame to model
	tic = time.time()
	interpreter.set_tensor(input_details[0]['index'], image)
	interpreter.invoke()
	tflite_results = interpreter.get_tensor(output_details[0]['index'])
	toc = time.time()
	
	#prediction results
	fire_prob = tflite_results[0][1] * 100
	smoke_prob = tflite_results[0][2] * 100
	if fire_prob > 90:
		alert=alert+1
		if alert >= 10:
			if flag == 0:
				camera.start_preview()
				camera.start_recording('test.h264')
				time.sleep(10)
				camera.stop_recording()
				camera.stop_preview()
				print("Rasp_Pi => Video Recorded! \r\n")
				command = "MP4Box -add test.h264 test.mp4"
				call([command], shell=True)
				alert_send()
				flag=1
	else:
		alert = 0
	
	#output for each frame
	print("Time taken = ", toc - tic)
	print("FPS: ", 1 / np.float64(toc - tic))
	print("Fire Probability: ", fire_prob)
	print("Smoke Probability: ", smoke_prob)
	print(image.shape)
	
	#output video stream
	label = "Fire Probability: " + str(fire_prob)
	cv2.putText(orig, label, (10, 25),  cv2.FONT_HERSHEY_SIMPLEX,0.7, (0, 255, 0), 2)
	label = "Smoke Probability: " + str(smoke_prob)
	cv2.putText(orig, label, (10, 60),  cv2.FONT_HERSHEY_SIMPLEX,0.7, (0, 255, 0), 2)
	cv2.imshow("Frame", orig)
	key = cv2.waitKey(1) & 0xFF
	# clear the stream in preparation for the next frame
	rawCapture.truncate(0)
	
	# if the `q` key was pressed, break from the loop
	if key == ord("q"):
		break
