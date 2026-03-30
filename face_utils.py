import face_recognition  # High-level face recognition library
import numpy as np       # For number array operations
import json              # To convert the encoding list to/from text for storage
import cv2               # OpenCV for reading the webcam image


def encode_face(image_path):
    """
    Read a student photo from disk and compute its face encoding.
    The encoding is a list of 128 numbers that mathematically
    describes the unique features of the face.
    Returns:
        list: 128-number face encoding, or None if no face is found
    """
    # Load the image file from disk
    image = face_recognition.load_image_file(image_path)

    # Find all faces in the image and get their encodings
    encodings = face_recognition.face_encodings(image)

    if encodings:
        # Return the first face encoding as a plain Python list
        # (so it can be saved as JSON text in the database)
        return encodings[0].tolist()

    # If no face was found in the photo, return None
    return None


def verify_face(stored_encoding_json, frame):
    """
    Compare a stored face encoding against a live webcam frame.
    Parameters:
        stored_encoding_json (str): JSON string from database
        frame (numpy array):        Webcam image captured by OpenCV
    Returns:
        bool: True if the face matches, False if not
    """

    # If no encoding is stored, verification cannot proceed
    if not stored_encoding_json:
        return False

    # Convert the JSON string back into a numpy number array
    stored = np.array(json.loads(stored_encoding_json))

    # OpenCV reads images as BGR, but face_recognition needs RGB
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # Find face encodings in the live webcam frame
    live_encodings = face_recognition.face_encodings(rgb_frame)

    # If no face is visible in the webcam, fail the check
    if not live_encodings:
        return False

    # Compare stored encoding with the live encoding
    # tolerance=0.5 means strict matching (lower = stricter, 0.6 = more lenient)
    results = face_recognition.compare_faces(
        [stored], live_encodings[0], tolerance=0.5
    )

    return results[0]  # True if match, False if not
