(function(){importScripts("https://www.gstatic.com/firebasejs/8.10.1/firebase-app.js"),importScripts("https://www.gstatic.com/firebasejs/8.10.1/firebase-messaging.js"),importScripts("https://storage.googleapis.com/workbox-cdn/releases/6.1.5/workbox-sw.js"),workbox.precaching.precacheAndRoute([{'revision':null,'url':'/css/app.7659cac4.css'},{'revision':null,'url':'/css/chunk-vendors.3d15d497.css'},{'revision':null,'url':'/fonts/materialdesignicons-webfont.0766edc9.eot'},{'revision':null,'url':'/fonts/materialdesignicons-webfont.714a4eee.ttf'},{'revision':null,'url':'/fonts/materialdesignicons-webfont.e659bf56.woff'},{'revision':null,'url':'/fonts/materialdesignicons-webfont.fbaef2a9.woff2'},{'revision':'833e888b6a5f52f936d279b5bfc1e14f','url':'/index.html'},{'revision':null,'url':'/js/app.bae7acc4.js'},{'revision':null,'url':'/js/chunk-vendors.78fcc80d.js'},{'revision':'746d47fb9933ae4added6f4e6c24523d','url':'/manifest.json'},{'revision':'515cc5a62fd651917b7a0fc0e6ca9b2a','url':'/random.png'},{'revision':'b6216d61c03e6ce0c9aea6ca7808f7ca','url':'/robots.txt'}]);const e={apiKey:"AIzaSyBByeGSOiAnyZcuyP_jgRgjYoXnzAM-mM4",authDomain:"picam-262bc.firebaseapp.com",projectId:"picam-262bc",storageBucket:"picam-262bc.appspot.com",messagingSenderId:"963842013886",appId:"1:963842013886:web:0ec795658960a996eebcef",measurementId:"G-H2Z212699G"};firebase.initializeApp(e);const s=firebase.messaging();s.onBackgroundMessage((e=>{e.notification.title,e.notification.body;try{console.log("send a notification")}catch(s){console.error("message Falied: ",s)}}))})();
//# sourceMappingURL=firebase-messaging-sw.js.map