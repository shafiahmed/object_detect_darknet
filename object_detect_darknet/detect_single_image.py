"""
Script to perform object detection on all images in a directory. Images will be
displayed including detection bounding boxes.

Example usage:

$ python3 detect_single_image.py --images_dir \
    --weights /home/james/darknet/yolov3/20190927/yolov3.weights \
    --config /home/james/darknet/yolov3/20190927/yolov3.cfg \
    --labels /home/james/darknet/yolov3/20190927/labels.txt \
    --confidence 0.6
"""

import argparse
import os
from typing import List

import cv2
import numpy as np

# non-maximum suppression threshold
_NMS_THRESHOLD = 0.3


# ------------------------------------------------------------------------------
def detect_objects(
        img_file_path: str,
        darknet,
        class_labels: List[str],
        class_label_colors: List[tuple],
        confidence_threshold: float,
):
    """
    Detect objects in an image and return an image object with all detections
    annotated with labelled bounding boxes.

    :param img_file_path:
    :param darknet:
    :param class_labels:
    :param class_label_colors:
    :param confidence_threshold:
    :return:
    """

    # read image into BLOB (assuming model resolution is 416x416)
    img = cv2.imread(img_file_path)
    (height, width) = img.shape[:2]
    blob = cv2.dnn.blobFromImage(
        img,
        1 / 255.0,
        (416, 416),
        swapRB=True,
        crop=False,
    )

    # pass the BLOB through the model to get detections
    darknet.setInput(blob)
    layer_outputs = darknet.forward(layer_names)

    # get the detection details
    boxes = []
    confidences = []
    class_ids = []
    for output in layer_outputs:
        for detection in output:
            # extract the class ID and confidence
            # of the current object detection
            scores = detection[5:]
            class_id = np.argmax(scores)
            confidence = scores[class_id]

            # filter out weak predictions by ensuring the detected
            # probability is greater than the minimum probability
            if confidence > confidence_threshold:

                # scale the bounding box coordinates back relative to the
                # size of the image, keeping in mind that YOLO actually
                # returns the center (x, y)-coordinates of the bounding
                # box followed by the boxes' width and height
                box = detection[0:4] * np.array([width, height, width, height])
                (centerX, centerY, box_width, box_height) = box.astype("int")

                # use the center (x, y)-coordinates to derive the top and
                # and left corner of the bounding box
                x = int(centerX - (box_width / 2))
                y = int(centerY - (box_height / 2))

                # update our list of bounding box coordinates,
                # confidences, and class IDs
                boxes.append([x, y, int(box_width), int(box_height)])
                confidences.append(float(confidence))
                class_ids.append(class_id)

    # apply non-maximum suppression to suppress weak, overlapping bounding boxes
    idxs = cv2.dnn.NMSBoxes(boxes, confidences, confidence_threshold, _NMS_THRESHOLD)

    # ensure at least one detection exists
    if len(idxs) > 0:

        # loop over the indexes we are keeping
        for i in idxs.flatten():
            # extract the bounding box coordinates
            (x, y) = (boxes[i][0], boxes[i][1])
            (w, h) = (boxes[i][2], boxes[i][3])

            # draw a bounding box rectangle and label on the image
            color = [int(c) for c in class_label_colors[class_ids[i]]]
            cv2.rectangle(img, (x, y), (x + w, y + h), color, 2)
            text = f"{class_labels[class_ids[i]]}: {confidences[i]:.4f}"
            cv2.putText(
                img,
                text,
                (x, y - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                color,
                2,
            )

    return img


# ------------------------------------------------------------------------------
if __name__ == '__main__':

    # parse the command line arguments
    args_parser = argparse.ArgumentParser()
    args_parser.add_argument(
        "--images_dir",
        required=True,
        type=str,
        help="Directory containing one or more images to be used as input",
    )
    args_parser.add_argument(
        "--weights",
        required=True,
        type=str,
        help="Path to Darknet model weights file",
    )
    args_parser.add_argument(
        "--config",
        required=True,
        type=str,
        help="Path to Darknet model configuration file",
    )
    args_parser.add_argument(
        "--labels",
        required=True,
        type=str,
        help="Path to file specifying the labels used for Darknet model training",
    )
    args_parser.add_argument(
        "--confidence",
        type=float,
        default=0.5,
        help="Minimum probability required for detections",
    )
    args = vars(args_parser.parse_args())

    # load the model from weights/configuration
    darknet = cv2.dnn.readNetFromDarknet(args["config"], args["weights"])

    # get the output layer names
    layer_names = darknet.getLayerNames()
    layer_names = [layer_names[i[0] - 1] for i in darknet.getUnconnectedOutLayers()]

    # read labels into a list, get colors to represent each
    labels = open(args["labels"]).read().strip().split("\n")
    np.random.seed(42)
    label_colors = np.random.randint(0, 255, size=(len(labels), 3), dtype="uint8")

    # loop over each image file in the specified images directory
    image_file_names = os.listdir(args["images_dir"])
    for image_file_name in image_file_names:

        # find any images with unexpected dimensions
        image_file_path = os.path.join(args["images_dir"], image_file_name)

        # perform object detection on the image, get the image annotated with bounding boxes
        image = detect_objects(image_file_path, darknet, args["confidence"])

        # show the output image
        cv2.imshow("Image", image)
        cv2.waitKey(0)

    # successful completion
    exit(0)
