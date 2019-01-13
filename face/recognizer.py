import os
import uuid
import numpy as np
import cv2
import pickle


def recognize(path):
    print("Initializing recognizer...")
    
    data_dir = os.path.join(os.getcwd(), "data")
    trained_data_dir = os.path.join(data_dir, "trained-data")

    faces_cascade = cv2.CascadeClassifier(os.path.join(data_dir, "cascade/haarcascades/haarcascade_frontalface_default.xml"))
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.read(os.path.join(trained_data_dir, "trained_data.yml"))
    
    # hold the results
    res = {}

    print("Reading labels from trained data, reverse key:val...")
    labels = {}
    with open(os.path.join(trained_data_dir, "labels.pickle"), 'rb') as f:
        og_labels = pickle.load(f)
        labels = {v:k for k,v in og_labels.items()}
    print("Reading the image...")
    input_image = cv2.imread(path)
    h, w = input_image.shape[:2]
    print("height", h, "width", w)
    if h > w:
        mxs = (w, w)
    else:
        mxs = (h, h)
    print("maxSize ->", mxs)
    print("Convert to gray...")
    gray = cv2.cvtColor(input_image, cv2.COLOR_BGR2GRAY)
    print("Loading cascade...")
    faces = faces_cascade.detectMultiScale(gray, scaleFactor=1.05, minNeighbors=3, minSize=(20, 20), maxSize=mxs)
    print("Recognizing...")
    for (x, y, w, h) in faces:
        roi_gray = gray[y:y+h, x:x+h]
        id_, conf = recognizer.predict(roi_gray)
        print(labels[id_], conf)
        # print("Drawing frame and name for", labels[id_], "...")
        # color = (204, 51, 0) #BGR
        # stroke = 2
        # end_x = x + w
        # end_y = y + h
        # cv2.rectangle(input_image, (x, y), (end_x, end_y), color, stroke)
        if conf <= 100:
            print("Saving new roi...")
            new_roi_name = 'from_log_' + uuid.uuid4().hex
            print("New roi name:", new_roi_name)
            roi_owner_dir = os.path.join(data_dir, "training-images", labels[id_])
            print("Roi owner dir:", roi_owner_dir)
            cv2.imwrite(os.path.join(roi_owner_dir, new_roi_name + ".jpg"), roi_gray)
        if conf <= 120:
            res[labels[id_]] = conf
            # font = cv2.FONT_HERSHEY_SIMPLEX
            # n_color = (255, 255, 255)
            # n_stroke = 1
            # cv2.putText(input_image, labels[id_], (x, y), font, 1, n_color, n_stroke, cv2.LINE_AA) # endif
        else:
            res["unknown"] = "unknown"

    # print("Writing result image to {}...".format(os.path.join(data_dir, "result.jpg")))
    # cv2.imwrite(os.path.join(data_dir, "result.jpg"), input_image)
    return res
