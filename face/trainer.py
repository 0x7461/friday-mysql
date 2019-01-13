import os
import sys
import uuid
import numpy as np
import cv2
from PIL import Image
import pickle


def train():
    print("Trainer is warming up...")
    
    data_dir = os.path.join(os.getcwd(), "data")
    training_images_dir = os.path.join(data_dir, "training-images")
    trained_data_dir = os.path.join(data_dir, "trained-data")

    print("Checking necessary directories...")
    if not os.path.exists(trained_data_dir):
        os.makedirs(trained_data_dir)
    if not os.path.exists(training_images_dir):
        print("No training images! Exiting...")
        sys.exit()


    faces_cascade = cv2.CascadeClassifier(os.path.join(data_dir, "cascade/haarcascades/haarcascade_frontalface_default.xml"))
    recognizer = cv2.face.LBPHFaceRecognizer_create()

    current_id = 0
    label_ids = {}
    roi_s = []
    id_s = []

    print("Prepare data for training...")
    print("Working data directory ->", training_images_dir)
    for root, dirs, files in os.walk(training_images_dir):
        for file in files:
            if file.endswith("png") or file.endswith("jpg") or file.endswith("jpeg"):
                path = os.path.join(root, file)
                label = os.path.basename(root).replace(" ", "-").lower()
                print("Processing", path, "with label", label)
                if not label in label_ids:
                    label_ids[label] = current_id
                    current_id += 1
                id_ = label_ids[label]
                # print("Converting to gray and resizing...")
                pil_image = Image.open(path).convert("L")
                size = (500, 500)
                final_image = pil_image.resize(size, Image.ANTIALIAS)
                # print("Converting to numpy array...")
                image_array = np.array(final_image, "uint8")
                h, w = image_array.shape[:2]
                if h > w:
                    mxs = (w, w)
                else:
                    mxs = (h, h)
                # print("Detecing faces in images...")
                faces = faces_cascade.detectMultiScale(
                    image_array, scaleFactor=1.1, minNeighbors=3, minSize=(20, 20), maxSize=mxs)
                # print("Adding roi and id to their list...")
                for (x, y, w, h) in faces:
                    roi = image_array[y:y+h, x:x+h]
                    # print("save roi...")
                    roi_name = uuid.uuid4().hex
                    cv2.imwrite(os.path.join(root, roi_name + ".jpg"), roi)
                    roi_s.append(roi)
                    id_s.append(id_)
                # print("remove og image...")
                if os.path.exists(path):
                    os.remove(path)

    #print("Result ->", label_ids)
    #print("ROIs ->", roi_s)
    #print("IDs ->", id_s)
    print("Write labels with their ids to {}...".format(os.path.join(trained_data_dir, "labels.pickle")))
    with open(os.path.join(trained_data_dir, "labels.pickle"), 'wb') as f:
        pickle.dump(label_ids, f)
    print("Training with roi and id lists...")
    recognizer.train(roi_s, np.array(id_s))
    print("Saving trained data to {}...".format(os.path.join(trained_data_dir, "trained_data.yml")))
    recognizer.save(os.path.join(trained_data_dir, "trained_data.yml"))
    print("Finish training!")
