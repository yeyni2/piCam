import os

from flask import Flask, Response, request, send_from_directory, stream_with_context
from firebase_connection import get_firestore_ref, initialize_firebase
from facial_req import activate_camera
from firebase_admin import auth
import threading
import cv2
from flask_cors import CORS

app = Flask(__name__, static_folder="vueapp")
CORS(app)
frame_info = {"frame": "", "frame_rate": 5}


def gen_frames():
    try:
        while True:
            frame = frame_info["frame"]
            if frame is not None:
                _, buffer = cv2.imencode('.jpg', frame)
                frame = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
    except GeneratorExit:
        frame_info["frame_rate"] = 5


@app.route('/api/video_feed')
def video_feed():
    user_id_token = request.args.get('user_id_token')
    try:
        decoded_token = auth.verify_id_token(user_id_token)
        user_id = decoded_token['uid']
    except auth.InvalidIdTokenError:
        return 'Invalid ID token', 401
    except Exception as e:
        return "something went wrong", 500

    cam_ref = get_firestore_ref(collection="cameras", document="piCam")
    if user_id not in cam_ref.get().get("videoAccess"):
        return "unauthorised access", 500

    frame_info["frame_rate"] = 30

    return Response(stream_with_context(gen_frames()), mimetype='multipart/x-mixed-replace; boundary=frame')



@app.route('/api/set_token', methods=['POST'])
def set_user_token():
    data = request.get_json()
    user_id_token = data.get("userIdToken")
    token = data.get('token')
    try:
        decoded_token = auth.verify_id_token(user_id_token)
        user_id = decoded_token['uid']
    except auth.InvalidIdTokenError:
        return 'Invalid ID token', 401
    except Exception as e:
        return "something went wrong", 500

    user_ref = get_firestore_ref(collection='users', document=user_id)
    if not user_ref.get().exists:
        return "unauthorised access", 500
    user_ref.update({"messageToken": token})
    return "", 200


@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_vue_app(path):
    if path and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, 'index.html')


def main():
    initialize_firebase()
    t = threading.Thread(target=activate_camera, args=(frame_info,))
    t.daemon = True
    t.start()
    app.run(host='0.0.0.0', port=3000)


if __name__ == '__main__':
    main()
