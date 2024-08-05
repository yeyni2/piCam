from imutils.video import VideoStream
from imutils.video import FPS
import time
import face_recognition
import imutils
import pickle
import time
import cv2

encodingsP = "encodings.pickle"

print("INFO: loading known faces")
data = pickle.loads(open(encodingsP, "rb").read())
vs = VideoStream(src=0, framerate=10).start()
# vs = VideoStream(usePiCamera=True).start()
time.sleep(2.0)
fps = FPS().start()
last_seen_names = {}

# Make an operation only if person wasn't seen for the last 10 minutes or more
notification_time_threshold = 10 * 60


def activate_camera(frame_info=None, show_on_screen=False):
    if frame_info is None:
        frame_info = {}

    currentname = "unknown"

    while True:
        frame = vs.read()
        frame = imutils.resize(frame, width=500)
        # Separate to face_rec function
        boxes = face_recognition.face_locations(frame)
        encodings = face_recognition.face_encodings(frame, boxes)
        names = []
        # Separate to find_names
        for encoding in encodings:
            matches = face_recognition.compare_faces(data["encodings"],
                                                     encoding)
            name = "Unknown"

            if True in matches:
                matchedIdxs = [i for (i, b) in enumerate(matches) if b]
                counts = {}

                for i in matchedIdxs:
                    name = data["names"][i]
                    counts[name] = counts.get(name, 0) + 1

                name = max(counts, key=counts.get)

                if currentname != name:
                    currentname = name

                    if name in last_seen_names:
                        if time.time() - last_seen_names[name] >= notification_time_threshold:
                            last_seen_names[name] = time.time()
                            print(currentname, "is at the door")
                            # TODO: here add any activity like sending a notification.
                    else:
                        last_seen_names[name] = time.time()
                        print(currentname, "is at the door")

            names.append(name)

        #  Only after all the names where found check by the last time

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

        fps.update()

    fps.stop()
    print("INFO: elasped time: {:.2f}".format(fps.elapsed()))
    print("INFO: approx. FPS: {:.2f}".format(fps.fps()))

    cv2.destroyAllWindows()
    vs.stop()


if __name__ == '__main__':
    activate_camera(show_on_screen=True)
