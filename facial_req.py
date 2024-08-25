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

dir_path = os.path.dirname(os.path.realpath(__file__))
encodingsP = os.path.join(dir_path, 'encodings.pickle')
data = pickle.loads(open(encodingsP, "rb").read())

if ENV == "PI":
    from picamera2 import Picamera2

    vs = Picamera2()
    config = vs.create_still_configuration(main={"format": "RGB888"})
    vs.configure(config)
    vs.start()
else:
    vs = VideoStream(src=0, framerate=10).start()

time.sleep(2.0)
last_seen_names = {}

# Make an operation only if person wasn't seen for the last 10 minutes or more
notification_time_threshold = 10 * 60
active_user_connection_fps = 15


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


def get_relevant_msg(seen_names: set) -> Tuple[bool, List[str]]:
    relevant_names = []
    for name in list(seen_names):
        if not check_recently_seen(name):
            relevant_names.append(name)

    if len(relevant_names) == 0:
        return False, []

    if len(relevant_names) == 1 and relevant_names[0] == "unknown":
        last_known_gap = 60 * 5
    else:
        last_known_gap = 60 * 2

    if ("last_notification_time" in last_seen_names and
            time.time() - last_seen_names["last_notification_time"] < last_known_gap):
        return False, []

    if "unknown" in relevant_names and len(relevant_names) >= 2:
        relevant_names.remove("unknown")

    if len(relevant_names) == 1:
        name = relevant_names[0]
        if name == "unknown":
            msg_title = "Unknown person is at the door"
        else:
            msg_title = f"{name} is at the door"
        return True, [msg_title, ""]

    connected_names = ', '.join(relevant_names)
    msg_title = "multiple people spotted at the door"
    msg_body = f"{connected_names} are at the door"

    return True, [msg_title, msg_body]


def notify_relevant_users(seen_names: set, cam_name: str = "piCam") -> None:
    cam_details = get_firestore_ref(collection="cameras", document=cam_name).get()
    if not cam_details.exists:
        return

    should_send, msg = get_relevant_msg(seen_names)

    if not should_send:
        return

    last_seen_names["last_notification_time"] = time.time()

    for user_id in cam_details.get("usersToNotify"):
        user_info = get_firestore_ref(collection="users", document=user_id).get()
        try:
            user_msg_token = user_info.get("messageToken")
        except:
            continue
        send_message(token=user_msg_token, message_title=msg[0], message_body=msg[1])


def get_fps(is_user_connected=False, names=None) -> float:
    if names is None:
        names = []
    if is_user_connected:
        return active_user_connection_fps
    elif len(names) != 0:
        return 3
    else:
        temp = get_cpu_temp()
        if temp >= 73:
            return 0.15
        elif temp >= 70:
            return 0.15
        elif temp >= 65:
            return 0.2
        elif temp >= 60:
            return 0.25
        elif temp >= 55:
            return 0.33
        else:
            return 0.5


def activate_camera(frame_info=None, show_on_screen=False):
    if frame_info is None:
        frame_info = {}

    frames_validate_count = 0
    currentname = "unknown"
    names = []

    while True:
        frames_validate_count += 1

        if ENV == "PI":
            frame = vs.capture_array()
        else:
            frame = vs.read()  # - For PC usage

        frame = imutils.resize(frame, width=500)
        boxes = face_recognition.face_locations(frame)
        encodings = face_recognition.face_encodings(frame, boxes)

        # Separate to find_names
        for encoding in encodings:
            matches = face_recognition.compare_faces(data["encodings"],
                                                     encoding, tolerance=0.65)
            name = "unknown"

            if True in matches:
                matchedIdxs = [i for (i, b) in enumerate(matches) if b]
                counts = {}

                for i in matchedIdxs:
                    name = data["names"][i]
                    counts[name] = counts.get(name, 0) + 1

                name = max(counts, key=counts.get)
                currentname = name

            names.append(name)

        frame_rate = get_fps(frame_info["user_connection"], names)
        frame_info["frame_rate"] = frame_rate

        if frames_validate_count == 3:
            frames_validate_count = 0
            if len(names) != 0:
                notify_relevant_users(seen_names=set(names))
                names = []

        #  Only after all the names where found check by the last time

        if frame_info["user_connection"] or show_on_screen:
            # Separate to draw rectangles around people (need to check how to change the frame from the function)
            for ((top, right, bottom, left), name) in zip(boxes, names):
                cv2.rectangle(frame, (left, top), (right, bottom),
                              (0, 255, 225), 2)
                y = top - 15 if top - 15 > 15 else top + 15
                cv2.putText(frame, name, (left, y), cv2.FONT_HERSHEY_SIMPLEX,
                            .8, (0, 255, 255), 2)

        if show_on_screen:
            cv2.imshow("Facial Recognition is Running", frame)

        frame_info["frame"] = frame
        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break

        time.sleep(1 / frame_rate)

    cv2.destroyAllWindows()
    vs.stop()


if __name__ == '__main__':
    activate_camera(show_on_screen=True)
