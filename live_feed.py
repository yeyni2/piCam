from flask import Flask, render_template, Response
from facial_req import activate_camera
import threading
import cv2

app = Flask(__name__)

frame_info = {"frame": "",
              "success": ""}


def gen_frames():
    while True:
        frame = frame_info["frame"]
        if frame is not None:
            _, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/')
def index():
    return render_template('index.html')


def main():
    t = threading.Thread(target=activate_camera, args=(frame_info,))
    t.daemon = True
    t.start()
    app.run(host='0.0.0.0', port=5050)


if __name__ == '__main__':
    main()
