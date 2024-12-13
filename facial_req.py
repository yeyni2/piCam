from firebase_connection import get_firestore_ref, send_message
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
data = pickle.loads(open(encodingsP, "rb").read())
known_names = set(data['names'])

if ENV == "PI":
    from picamera2 import Picamera2

    vs = Picamera2()
    # vs.awb_mode = 'off'
    config = vs.create_still_configuration(main={"format": "RGB888"})
    vs.configure(config)
    vs.start()
    active_user_connection_fps = 20
else:
    vs = VideoStream(src=0, framerate=10).start()
    active_user_connection_fps = 60

time.sleep(2.0)
last_seen_names = {}

# Make an operation only if person wasn't seen for the last 10 minutes or more
notification_time_threshold = 10 * 60


def get_cpu_temp() -> float:
    temp_file_path = '/sys/class/thermal/thermal_zone0/temp'
    if not os.path.exists(temp_file_path):
        return -1
    with open(temp_file_path, 'r') as file:
        temp = float(file.read()) / 1000
    return temp


def check_recently_seen(name: str):
    if name in last_seen_names:
        if time.time() - last_seen_names[name] >= notification_time_threshold:
            last_seen_names[name] = time.time()
            return False
    else:
        last_seen_names[name] = time.time()
        return False
    return True


def get_relevant_names(seen_names: list, expected_faces_count: int = 1) -> list:
    users_at_the_door = filter_names(seen_names, expected_faces_count)
    relevant_names = []
    for name in list(users_at_the_door):
        if not check_recently_seen(name):
            relevant_names.append(name)
    return relevant_names


def get_relevant_msg(relevant_names: list) -> Tuple[bool, List[str]]:
    additional_msg = ""
    if len(relevant_names) == 0:
        return False, []

    last_known_gap = 60 * 2

    if ("last_notification_time" in last_seen_names and
            time.time() - last_seen_names["last_notification_time"] < last_known_gap):
        return False, []

    if len(relevant_names) == 1:
        name = relevant_names[0]
        if name == "unknown":
            msg_title = "Unknown person is at the door"
        else:
            msg_title = f"{name} is at the door"
        return True, [msg_title, " "]

    msg_title = "multiple people spotted at the door"

    if "unknown" in relevant_names:
        relevant_names.remove("unknown")
        additional_msg = ", with unrecognised people"

    connected_names = ', '.join(relevant_names)
    msg_body = f"{connected_names} at the door" + additional_msg

    return True, [msg_title, msg_body]


def notify_relevant_users(seen_names: list, cam_name: str = "piCam", expected_faces_count: int = 1) -> None:
    cam_details = get_firestore_ref(collection="cameras", document=cam_name).get()
    if not cam_details.exists:
        return

    relevant_names = get_relevant_names(seen_names, expected_faces_count)
    should_send, msg = get_relevant_msg(relevant_names)

    if not should_send:
        return

    last_seen_names["last_notification_time"] = time.time()

    for user_id in cam_details.get("usersToNotify"):
        user_info = get_firestore_ref(collection="users", document=user_id).get()
        try:
            user_msg_token = user_info.get("messageToken")
            user_name = user_info.get("name")
        except:
            continue

        if not user_name or user_name not in relevant_names:
            send_message(token=user_msg_token, message_title=msg[0], message_body=msg[1])


def filter_names(names: list, expected_faces_count: int = 1) -> set:
    names_count = {}
    filtered_names = []
    unknown_number = 1

    if len(names) != expected_faces_count * FRAME_NOTIFICATION_THRESHOLD:
        return set()

    for name in names:
        if name is names_count:
            names_count[name] += 1
        else:
            names_count[name] = 1

        if names_count[name] > FRAME_NOTIFICATION_THRESHOLD:
            if name in known_names:
                return set()
            else:
                names_count[name] -= 1
                unknown_name = name + str(unknown_number)

                if unknown_name not in names_count:
                    names_count[unknown_name] = 0
                elif names_count[unknown_name] >= FRAME_NOTIFICATION_THRESHOLD:
                    unknown_number += 1
                    unknown_name = name + str(unknown_number)

                names_count[unknown_name] += 1

    sorted_names = sorted(names_count.keys(), key=lambda face: names_count[face])

    for name_index in range(len(sorted_names)):
        if sorted_names[name_index] in known_names:
            filtered_names.append(sorted_names[name_index])
        else:
            filtered_names.append('unknown')

        if len(filtered_names) == expected_faces_count:
            if name_index + 1 < len(sorted_names):
                current_name_count = names_count[sorted_names[name_index]]
                next_name_count = names_count[sorted_names[name_index + 1]]
                if current_name_count == next_name_count:
                    return set()
            break

    if len(filtered_names) != expected_faces_count:
        return set()

    return set(filtered_names)


def get_fps(is_user_connected: bool = False, expect_face: bool = False) -> float:
    if is_user_connected:
        return active_user_connection_fps
    elif expect_face:
        return FRAME_NOTIFICATION_THRESHOLD
    else:
        temp = get_cpu_temp()
        if temp >= 73:
            return 3
        elif temp >= 70:
            return 7
        elif temp >= 65:
            return 9
        elif temp >= 60:
            return 11
        elif temp >= 55:
            return 13
        else:
            return 15


def match_existing_faces(encodings: list = None, names: list = None) -> list:
    if encodings is None:
        return []
    if names is None:
        names = []

    for encoding in encodings:
        matches = face_recognition.compare_faces(data["encodings"], encoding, tolerance=0.55)
        name = "unknown"

        if True in matches:
            matched_ids = [i for (i, b) in enumerate(matches) if b]
            counts = {}

            for i in matched_ids:
                name = data["names"][i]
                counts[name] = counts.get(name, 0) + 1

            name = max(counts, key=counts.get)
        names.append(name)

    return names


def draw_box_around_faces(boxes: list, names: list, frame):
    for ((top, right, bottom, left), name) in zip(boxes, names):
        cv2.rectangle(frame, (left, top), (right, bottom),
                      (0, 255, 225), 2)
        y = top - 15 if top - 15 > 15 else top + 15
        cv2.putText(frame, name, (left, y), cv2.FONT_HERSHEY_SIMPLEX,
                    .8, (0, 255, 255), 2)
    return frame


def activate_camera(frame_info=None, show_on_screen=False):
    if frame_info is None:
        frame_info = {}

    frames_validate_count = 0
    amount_of_faces = 0
    expect_face = False
    names = []

    while True:
        frames_validate_count += 1

        if ENV == "PI":
            frame = vs.capture_array()
        else:
            frame = vs.read()

        frame = imutils.resize(frame, width=500)
        boxes = face_recognition.face_locations(frame)
        encodings = face_recognition.face_encodings(frame, boxes)
        amount_of_faces = max(amount_of_faces, len(boxes))

        names = match_existing_faces(encodings, names)

        if len(frame_info["user_connections"]) > 0:
            user_connected = True
        else:
            user_connected = False

        if len(names) > 0:
            expect_face = True

        frame_info["frame_rate"] = get_fps(user_connected, expect_face)

        if frames_validate_count == FRAME_NOTIFICATION_THRESHOLD:
            if len(names) == FRAME_NOTIFICATION_THRESHOLD * amount_of_faces:
                notify_relevant_users(seen_names=names,
                                      expected_faces_count=amount_of_faces)
            expect_face = False
            frames_validate_count = 0
            names = []
            amount_of_faces = 0

        if user_connected or show_on_screen:
            frame = draw_box_around_faces(boxes, names, frame)

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
    activate_camera(show_on_screen=True)
