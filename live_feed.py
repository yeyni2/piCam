import os

from flask import Flask, Response, request, send_from_directory, render_template
from firebase_connection import get_firestore_ref, initialize_firebase
from facial_req import activate_camera
from firebase_admin import auth
import threading
import cv2
from flask_cors import CORS

app = Flask(__name__, static_folder="vueapp")
CORS(app)
frame_info = {"frame": ""}


def gen_frames():
    while True:
        frame = frame_info["frame"]
        if frame is not None:
            _, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


@app.route('/api/video_feed')
def video_feed():
    user_id = request.args.get('user_id')
    user_ref = get_firestore_ref(collection='users', document=user_id)
    if not user_ref.get().exists:
        return "unauthorised access", 500
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/api/set_token', methods=['POST'])
def set_user_token():
    data = request.get_json()
    user_id = data.get('userId')
    token = data.get('token')
    user_ref = get_firestore_ref(collection='users', document=user_id)
    if not user_ref.get().exists:
        try:
            auth.delete_user(user_id)
        except auth.UserNotFoundError:
            return "", 500
        except Exception as e:
            return "something went wrong", 500
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


# @app.route('/<path:path>')
# def static_proxy(path):
#     return send_from_directory(app.static_folder, path)


def main():
    initialize_firebase()
    t = threading.Thread(target=activate_camera, args=(frame_info,))
    t.daemon = True
    t.start()
    app.run(host='0.0.0.0', port=3000)


if __name__ == '__main__':
    main()
