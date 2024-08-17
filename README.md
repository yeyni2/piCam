### Note: you may need to install [C++ build tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) to install dlib on windows

---

__Create a venv: `python3 -m venv venv --system-site-packages`__

__Start by running `pip install -r .\requirements.txt`__

<u>**install dlib:**</u>

```commandline
git clone https://github.com/davisking/dlib.git
cd dlib
mkdir build
cd build
cmake ..
cmake --build .
cd ..
python setup.py install
cd ..
```

<u>**install picamera:**</u>

```commandline
git clone https://github.com/waveform80/picamera.git
cd picamera
python setup.py install
cd ..
```

### Now all the dependencies should be installed and we can install face recognition:
`
pip install face_recognition
`

