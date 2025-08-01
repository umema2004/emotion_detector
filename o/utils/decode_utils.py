#for base64 frame decoding

import base64
import numpy as np
import cv2

def decode_frame(base64_str):  # base64 image string -> opencv frame
    header, encoded = base64_str.split(",", 1)
    img_data = base64.b64decode(encoded)
    np_arr = np.frombuffer(img_data, np.uint8)
    frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    return frame