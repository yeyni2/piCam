import tempfile

import imutils
import numpy as np
import face_recognition
import pickle
import cv2
import os

from firebase_connection import get_firestore_ref, get_storage_blob

dir_path = os.path.dirname(os.path.realpath(__file__))
encodingsP = os.path.join(dir_path, 'encodings.pickle')
with open(encodingsP, "rb") as file:
    data = pickle.loads(file.read())
print(data)


def update_pickle():
    update_known()
    with open(encodingsP, "wb") as file:
        file.write(pickle.dumps(data))


def update_known():
    data["known_encodings"] = []
    data["known_users"] = []
    for uid, user_data in data["users"].items():
        data["known_encodings"].extend(user_data.get('encodings').values())
        data["known_users"].extend([uid * len(user_data.get('encodings').values())])


def check_and_create_user(uid: str):
    if "users" not in data:
        data["users"] = {}

    if uid not in data["users"]:
        data_ref = get_firestore_ref(collection="users", document=uid).get()
        name = data_ref.get("name")
        if not name:
            raise Exception("User must have a name")
        data["users"][uid] = {"name": name, "encodings": {}}


def get_image_encodings(blob_path: str) -> list:
    """
    :param blob_path: The path of the image in Firebase Storage
    :return: List of face encodings
    """
    try:
        if not os.path.exists('downloaded_images'):
            os.makedirs("downloaded_images")

        local_filename = os.path.join("downloaded_images", os.path.basename(blob_path))

        blob = get_storage_blob(blob_path)
        blob.download_to_filename(local_filename)

        frame = cv2.imread(local_filename)
        # frame = imutils.resize(frame, width=500)
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        boxes = face_recognition.face_locations(frame)

        if len(boxes) == 0 or len(boxes) > 1:
            os.remove(local_filename)
            return []

        face_encodings = face_recognition.face_encodings(frame, boxes)

        os.remove(local_filename)
        return face_encodings[0]

    except Exception as e:
        print(f"Error retrieving face encodings: {e}")
        return []


def add_new_image(uid: str, firebase_image_paths: list):
    if len(firebase_image_paths) == 0:
        return

    check_and_create_user(uid)
    knownEncodings = list(data["users"][uid]["encodings"].values())

    for image_path in firebase_image_paths:
        if image_path in data["users"][uid]["encodings"]:
            continue

        encoding = get_image_encodings(image_path)
        print(encoding)
        if len(encoding) == 0:
            continue

        if not any(np.array_equal(known_encoding, encoding) for known_encoding in knownEncodings):
            data["users"][uid]["encodings"][image_path] = encoding

    update_pickle()


def remove_image(uid: str, firebase_image_path: list):
    if uid not in data:
        return

    for image_path in firebase_image_path:
        if image_path not in data["users"][uid]["encodings"]:
            continue

        del data["users"][uid]["encodings"][image_path]

    update_pickle()


def update_name(uid: str):
    if uid not in data:
        raise Exception("user doesn't exist")

    data_ref = get_firestore_ref(collection="users", document=uid).get()
    name = data_ref.get("name")
    if not name:
        raise Exception("No name was entered")

    data["users"][uid]["name"] = name
    update_pickle()

# update_pickle()
# with open(encodingsP, "wb") as file:
#     file.write(pickle.dumps({}))
