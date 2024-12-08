import math

from firebase_connection import get_firestore_ref, send_message, initialize_firebase
from imutils.video import VideoStream
from typing import Tuple, List
from dotenv import load_dotenv

import face_recognition
import imutils
import pickle
import time
import cv2
import os

load_dotenv()

ENV = os.getenv("LOCATION")
FRAME_NOTIFICATION_THRESHOLD = 3

dir_path = os.path.dirname(os.path.realpath(__file__))
encodingsP = os.path.join(dir_path, 'encodings.pickle')
last_time_data_changes = 0

with open(encodingsP, "rb") as file:
    data = pickle.loads(file.read())

known_users = set(data['known_users']) if "known_users" in data else set()

if ENV == "PI":
    from picamera2 import Picamera2

    vs = Picamera2()
    config = vs.create_still_configuration(main={"format": "RGB888"})
    vs.configure(config)
    vs.start()
    active_user_connection_fps = 30
else:
    vs = VideoStream(src=0, framerate=10).start()
    active_user_connection_fps = 60

time.sleep(2.0)
last_seen_users = {}

# Make an operation only if person wasn't seen for the last 10 minutes or more
notification_time_threshold = 10 * 60


def update_data():
    global data, last_time_data_changes

    current_modified_time = os.path.getmtime(encodingsP)
    if current_modified_time != last_time_data_changes:
        with open(encodingsP, "rb") as file:
            data = pickle.loads(file.read())
            last_time_data_changes = current_modified_time


def get_cpu_temp() -> float:
    temp_file_path = '/sys/class/thermal/thermal_zone0/temp'
    if not os.path.exists(temp_file_path):
        return -1
    with open(temp_file_path, 'r') as file:
        temp = float(file.read()) / 1000
    return temp


def check_recently_seen(uid: str):
    if uid in last_seen_users:
        if time.time() - last_seen_users[uid] >= notification_time_threshold:
            last_seen_users[uid] = time.time()
            return False
    else:
        last_seen_users[uid] = time.time()
        return False
    return True


def get_relevant_users(seen_users: list, expected_faces_count: int = 1) -> list:
    users_at_the_door = filter_names(seen_users, expected_faces_count)
    relevant_names = []
    for uid in list(users_at_the_door):
        if not check_recently_seen(uid):
            relevant_names.append(uid)
    return relevant_names


def get_relevant_msg(relevant_users: list, relevant_names: list) -> Tuple[bool, List[str]]:
    additional_msg = ""
    if len(relevant_users) == 0:
        return False, []

    last_known_gap = 60 * 2

    if ("last_notification_time" in last_seen_users and
            time.time() - last_seen_users["last_notification_time"] < last_known_gap):
        return False, []

    if len(relevant_users) == 1:
        if relevant_users[0] == "unknown":
            msg_title = "Unknown person is at the door"
        else:
            name = data["users"][relevant_users[0]]["name"]
            msg_title = f"{name} is at the door"
        return True, [msg_title, " "]

    msg_title = "multiple people spotted at the door"

    if "unknown" in relevant_users:
        if len(relevant_names) == 0:
            return True, ["multiple unknown people spotted at the door", ""]

        additional_msg = ", with unrecognised people"

    connected_names = ', '.join(relevant_names)
    msg_body = f"{connected_names} at the door" + additional_msg

    return True, [msg_title, msg_body]


def notify_relevant_users(seen_users: list, cam_name: str = "piCam", expected_faces_count: int = 1) -> None:
    cam_details = get_firestore_ref(collection="cameras", document=cam_name).get()
    if not cam_details.exists:
        return

    relevant_users = get_relevant_users(seen_users, expected_faces_count)
    relevant_names = [data["users"][user_id]["name"] for user_id in relevant_users if user_id != "unknown"]
    should_send, msg = get_relevant_msg(relevant_users, relevant_names)

    if not should_send:
        return

    last_seen_users["last_notification_time"] = time.time()

    for user_id in cam_details.get("usersToNotify"):
        user_info = get_firestore_ref(collection="users", document=user_id).get()
        try:
            user_msg_token = user_info.get("messageToken")
            user_name = user_info.get("name")
        except:
            continue

        if user_id not in relevant_users:
            pass
            # send_message(token=user_msg_token, message_title=msg[0], message_body=msg[1])


def filter_names(users: list, expected_faces_count: int = 1) -> set:
    users_count = {}
    filtered_names = []
    unknown_number = 1

    if len(users) != expected_faces_count * (FRAME_NOTIFICATION_THRESHOLD - 1):
        return set()

    for uid in users:
        if uid in users_count:
            users_count[uid] += 1
        else:
            users_count[uid] = 1

        if users_count[uid] > FRAME_NOTIFICATION_THRESHOLD:
            if uid in known_users:
                return set()
            else:
                users_count[uid] -= 1
                unknown_name = uid + str(unknown_number)

                if unknown_name not in users_count:
                    users_count[unknown_name] = 0
                elif users_count[unknown_name] >= FRAME_NOTIFICATION_THRESHOLD:
                    unknown_number += 1
                    unknown_name = uid + str(unknown_number)

                users_count[unknown_name] += 1

    filtered_users_count = {}
    for uid, count in users_count.items():
        if count > 1:
            filtered_users_count[uid] = count

    sorted_users = sorted(filtered_users_count.keys(), key=lambda user: filtered_users_count[user])

    for user_index in range(len(sorted_users)):
        if sorted_users[user_index] in known_users:
            filtered_names.append(sorted_users[user_index])
        else:
            filtered_names.append('unknown')

        if len(filtered_names) == expected_faces_count:
            if user_index + 1 < len(sorted_users):
                current_name_count = filtered_users_count[sorted_users[user_index]]
                next_name_count = filtered_users_count[sorted_users[user_index + 1]]
                if current_name_count == next_name_count:
                    return set()
            break

    if len(filtered_names) != expected_faces_count:
        return set()

    return set(filtered_names)


def convert_temp_to_fps(temp: float) -> float:
    fps = 19.98277 / (1 + math.exp(0.124135 * temp - 7.37577))
    fps = max(0.15, fps)
    return fps


def get_fps(is_user_connected: bool = False, expect_face: bool = False) -> float:
    temp = get_cpu_temp()
    if is_user_connected:
        if temp >= 75:
            return 15
        return active_user_connection_fps
    elif expect_face:
        return FRAME_NOTIFICATION_THRESHOLD * 3
    else:
        return convert_temp_to_fps(temp)


def match_existing_faces(encodings: list = None, users: list = None) -> list:
    if encodings is None:
        return []
    if users is None:
        users = []

    for encoding in encodings:
        if "known_encodings" not in data:
            known_encodings = []
        else:
            known_encodings = data["known_encodings"]

        matches = face_recognition.compare_faces(known_encodings, encoding, tolerance=0.55)
        uid = "unknown"

        if True in matches:
            matched_ids = [i for (i, b) in enumerate(matches) if b]
            counts = {}

            for i in matched_ids:
                uid = data["known_users"][i]
                counts[uid] = counts.get(uid, 0) + 1
                # TODO: Only one problem, if an image matches two or more users even if the score on one is better it
                #  wont show, meaning only the amount of images the user have will affect. if i have 2 but dad has 5
                #  its likely that i would show as dad... Find a way to take into account images count and distance.

            uid = max(counts, key=counts.get)

        users.append(uid)

    return users


def draw_box_around_faces(boxes: list, users: list, frame):
    for ((top, right, bottom, left), uid) in zip(boxes, users):
        cv2.rectangle(frame, (left, top), (right, bottom),
                      (0, 255, 225), 2)
        y = top - 15 if top - 15 > 15 else top + 15
        name = uid if uid == "unknown" else data["users"][uid]["name"]
        cv2.putText(frame, name, (left, y), cv2.FONT_HERSHEY_SIMPLEX,
                    .8, (0, 255, 255), 2)
    return frame


def activate_camera(frame_info=None, show_on_screen=False):
    if frame_info is None:
        frame_info = {}

    frames_validate_count = 0
    amount_of_faces = 0
    expect_face = False
    users = []

    while True:
        update_data()

        if ENV == "PI":
            frame = vs.capture_array()
        else:
            frame = vs.read()

        frame = imutils.resize(frame, width=500)
        boxes = face_recognition.face_locations(frame)
        encodings = face_recognition.face_encodings(frame, boxes)
        amount_of_faces = max(amount_of_faces, len(boxes))

        users = match_existing_faces(encodings, users)

        if show_on_screen or "user_connections" in frame_info and len(frame_info["user_connections"]) > 0:
            user_connected = True
        else:
            user_connected = False

        if len(users) > 0 or expect_face:
            expect_face = True
            frames_validate_count += 1

        frame_info["frame_rate"] = get_fps(user_connected, expect_face)

        if user_connected or show_on_screen:
            frame = draw_box_around_faces(boxes, users, frame)

        if frames_validate_count == FRAME_NOTIFICATION_THRESHOLD:
            if len(users) > 0:
                notify_relevant_users(seen_users=users, expected_faces_count=amount_of_faces)

            expect_face = False
            frames_validate_count = 0
            users = []
            amount_of_faces = 0

        if show_on_screen:
            cv2.imshow("Facial Recognition is Running", frame)

        frame_info["frame"] = frame

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break

        time.sleep(1 / frame_info["frame_rate"])

    cv2.destroyAllWindows()
    vs.stop()


if __name__ == '__main__':
    initialize_firebase()
    activate_camera(show_on_screen=True)

