importScripts("https://www.gstatic.com/firebasejs/8.10.1/firebase-app.js");
importScripts(
  "https://www.gstatic.com/firebasejs/8.10.1/firebase-messaging.js"
);

const firebaseConfig = {
  apiKey: "AIzaSyBByeGSOiAnyZcuyP_jgRgjYoXnzAM-mM4",
  authDomain: "picam-262bc.firebaseapp.com",
  projectId: "picam-262bc",
  storageBucket: "picam-262bc.appspot.com",
  messagingSenderId: "963842013886",
  appId: "1:963842013886:web:0ec795658960a996eebcef",
  measurementId: "G-H2Z212699G",
};

firebase.initializeApp(firebaseConfig);

const messaging = firebase.messaging();

messaging.onBackgroundMessage((payload) => {
  const notificationTitle = payload.notification.title;
  const notificationOptions = {
    body: payload.notification.body,
  };
  try {
    self.registration.showNotification(notificationTitle, notificationOptions);
  } catch (e) {
    console.error(e);
  }
});
