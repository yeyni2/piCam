(function(){"use strict";var e={4691:function(e,n,t){var o=t(5130),i=t(6768);function r(e,n){const t=(0,i.g2)("router-view");return(0,i.uX)(),(0,i.Wv)(t)}var a=t(1241);const c={},s=(0,a.A)(c,[["render",r]]);var l=s,u=t(1387),d=t(7845),f=t(6400),p=t(7530);const v={apiKey:"AIzaSyBByeGSOiAnyZcuyP_jgRgjYoXnzAM-mM4",authDomain:"picam-262bc.firebaseapp.com",projectId:"picam-262bc",storageBucket:"picam-262bc.appspot.com",messagingSenderId:"963842013886",appId:"1:963842013886:web:0ec795658960a996eebcef",measurementId:"G-H2Z212699G"},m=(0,f.Wp)(v),g=(0,d.xI)(m),h=(0,p.dG)(m);(0,p.xD)(h,(e=>{console.log("Message received. ",e);const n=e.notification.title,t={body:e.notification.body,icon:e.notification.icon};"Notification"in window?"granted"===Notification.permission&&new Notification(n,t):alert("This browser does not support desktop notification")}));var b=t(144);const y={class:"live-feed-page"},k=(0,i.Lk)("h1",{class:"pa-3"},"Home Cam Live Feed!",-1),w={class:"ma-6 mb-9"},O=["src"];var _={__name:"LiveFeed",setup(e){const n=(0,b.KR)(""),t=()=>{(0,d.CI)(g),window.location.reload()},o=async()=>{const e=await g.currentUser.getIdToken();n.value=`/api/video_feed?user_id_token=${e}`};return o(),(e,o)=>{const r=(0,i.g2)("v-btn");return(0,i.uX)(),(0,i.CE)("div",y,[k,(0,i.Lk)("div",w,[(0,i.bF)(r,{onClick:t},{default:(0,i.k6)((()=>[(0,i.eW)("sign out")])),_:1})]),(0,i.Lk)("img",{style:{width:"-webkit-fill-available"},src:n.value},null,8,O)])}}};const C=_;var j=C;t(4114);const x={class:"d-flex flex-column justify-center align-center",style:{height:"100vh"}},F={class:"page"},L=(0,i.Lk)("h3",null,"Enter Your PiCam User Credential",-1);var S={__name:"UserLogin",setup(e){const n=(0,u.rd)(),t=(0,b.KR)(""),o=(0,b.KR)(""),r=(0,b.KR)(!1),a=async()=>{let e="";try{const n=await(0,d.x9)(g,t.value,o.value);e=n.user}catch(i){console.error(i.message),alert("Login faild")}await c(e),n.push("/liveFeed")},c=async e=>{console.log(Notification.permission),"granted"!=Notification.permission&&await Notification.requestPermission(),"granted"==Notification.permission?await(0,p.gf)(h,{vapidKey:"BCuf1gfQ26ONFqnapY-pXl9khG63_3C_JOdUvC-zFekSAhtmNV6erEY4K3B3725Z48Ch4qr-fv5D8S3xnXlaERs"}).then((async n=>{n?await fetch("/api/set_token",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({token:n,userIdToken:await e.getIdToken(!0)})}):alert("No registration token available")})).catch((e=>{console.error("An error occurred while retrieving token. ",e),alert("An error occurred while retrieving token. ",e)})):alert("Your notification are blocked, you will not get messages when someone is at the door")},s=()=>{r.value=!r.value};return(e,n)=>{const c=(0,i.g2)("v-text-field"),l=(0,i.g2)("v-btn"),u=(0,i.g2)("v-form");return(0,i.uX)(),(0,i.CE)("div",x,[(0,i.Lk)("div",F,[L,(0,i.bF)(u,{class:"form"},{default:(0,i.k6)((()=>[(0,i.bF)(c,{modelValue:t.value,"onUpdate:modelValue":n[0]||(n[0]=e=>t.value=e),label:"Email",type:"email"},null,8,["modelValue"]),(0,i.bF)(c,{modelValue:o.value,"onUpdate:modelValue":n[1]||(n[1]=e=>o.value=e),label:"Password",type:r.value?"text":"password","append-inner-icon":r.value?"mdi-eye":"mdi-eye-off","onClick:appendInner":s},null,8,["modelValue","type","append-inner-icon"]),(0,i.bF)(l,{onClick:a},{default:(0,i.k6)((()=>[(0,i.eW)("Login")])),_:1})])),_:1})])])}}};const I=S;var N=I;const E=[{path:"/",name:"Login",component:N},{path:"/liveFeed",name:"LiveFeed",component:j}],T=(0,u.aE)({history:(0,u.LA)("/"),routes:E});T.beforeEach(((e,n,t)=>{const o=(0,d.xI)();(0,d.hg)(o,(n=>{n?"/"===e.path?t("/LiveFeed"):t():"/"!==e.path?t("/"):t()}))}));var P=T,A=t(782),K=(0,A.y$)({state:{},getters:{},mutations:{},actions:{},modules:{}}),R=(t(5524),t(7768)),V=t(1920),M=t(5741);const U=(0,R.$N)({components:V,directives:M,icons:{iconfont:"mdi",defaultSet:"mdi"}});(0,o.Ef)(l).use(K).use(P).use(U).mount("#app"),navigator.serviceWorker.register("/firebase-messaging-sw.js",{scope:"/"}).then((()=>{console.log("Registerd service worker")})).catch((e=>{console.error("Service worker registration failed:",e)}))}},n={};function t(o){var i=n[o];if(void 0!==i)return i.exports;var r=n[o]={exports:{}};return e[o].call(r.exports,r,r.exports,t),r.exports}t.m=e,function(){var e=[];t.O=function(n,o,i,r){if(!o){var a=1/0;for(u=0;u<e.length;u++){o=e[u][0],i=e[u][1],r=e[u][2];for(var c=!0,s=0;s<o.length;s++)(!1&r||a>=r)&&Object.keys(t.O).every((function(e){return t.O[e](o[s])}))?o.splice(s--,1):(c=!1,r<a&&(a=r));if(c){e.splice(u--,1);var l=i();void 0!==l&&(n=l)}}return n}r=r||0;for(var u=e.length;u>0&&e[u-1][2]>r;u--)e[u]=e[u-1];e[u]=[o,i,r]}}(),function(){t.n=function(e){var n=e&&e.__esModule?function(){return e["default"]}:function(){return e};return t.d(n,{a:n}),n}}(),function(){t.d=function(e,n){for(var o in n)t.o(n,o)&&!t.o(e,o)&&Object.defineProperty(e,o,{enumerable:!0,get:n[o]})}}(),function(){t.g=function(){if("object"===typeof globalThis)return globalThis;try{return this||new Function("return this")()}catch(e){if("object"===typeof window)return window}}()}(),function(){t.o=function(e,n){return Object.prototype.hasOwnProperty.call(e,n)}}(),function(){t.r=function(e){"undefined"!==typeof Symbol&&Symbol.toStringTag&&Object.defineProperty(e,Symbol.toStringTag,{value:"Module"}),Object.defineProperty(e,"__esModule",{value:!0})}}(),function(){var e={524:0};t.O.j=function(n){return 0===e[n]};var n=function(n,o){var i,r,a=o[0],c=o[1],s=o[2],l=0;if(a.some((function(n){return 0!==e[n]}))){for(i in c)t.o(c,i)&&(t.m[i]=c[i]);if(s)var u=s(t)}for(n&&n(o);l<a.length;l++)r=a[l],t.o(e,r)&&e[r]&&e[r][0](),e[r]=0;return t.O(u)},o=self["webpackChunkpicam"]=self["webpackChunkpicam"]||[];o.forEach(n.bind(null,0)),o.push=n.bind(null,o.push.bind(o))}();var o=t.O(void 0,[504],(function(){return t(4691)}));o=t.O(o)})();
//# sourceMappingURL=app.17959ec1.js.map