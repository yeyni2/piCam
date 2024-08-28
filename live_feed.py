import base64
import os
import time

from flask import Flask, Response, request, send_from_directory
from firebase_connection import get_firestore_ref, initialize_firebase
from facial_req import activate_camera
from firebase_admin import auth
from flask_cors import CORS
import threading
import cv2

# SOKET
from flask_socketio import SocketIO

app = Flask(__name__, static_folder="vueapp")
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")
frame_info = {"frame": "", "user_connections": set()}
frame_info_lock = threading.Lock()


def gen_frames():
    try:
        while True:
            frame = frame_info["frame"]
            if frame is not None:
                _, buffer = cv2.imencode('.jpg', frame)
                frame = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
                time.sleep(1 / frame_info["frame_rate"])
    except GeneratorExit:
        print("disconnect")
        frame_info["user_connection"] = False


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

    frame_info["user_connection"] = True
    frame_info["user_connection_time"] = time.time()
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')


# Socket video:
def gen_frames_sock():
    while True:
        with frame_info_lock:
            if not frame_info["user_connections"]:
                break

        frame = frame_info["frame"]
        if frame is not None:
            _, buffer = cv2.imencode('.jpg', frame)
            frame = base64.b64encode(buffer).decode('utf-8')
            socketio.emit('new_frame', {'frame': frame})
            socketio.sleep(1/frame_info["frame_rate"])


@socketio.on('video_feed')
def handle_request_stream():
    print("user connected")
    with frame_info_lock:
        frame_info["user_connections"].add(request.sid)
    socketio.start_background_task(gen_frames_sock)


@socketio.on('disconnect')
def handle_disconnect():
    with frame_info_lock:
        frame_info["user_connections"].discard(request.sid)
    print(f"user disconnected")


@app.route('/api/set_connection_time')
def set_connection_time():
    frame_info["user_connection_time"] = time.time()


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
    socketio.run(app, host='0.0.0.0', port=3000, allow_unsafe_werkzeug=True)


if __name__ == '__main__':
    main()
