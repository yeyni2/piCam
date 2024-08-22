(function(){"use strict";var e={9596:function(e,t,n){var o=n(5130),i=n(6768);function r(e,t){const n=(0,i.g2)("router-view");return(0,i.uX)(),(0,i.Wv)(n)}var a=n(1241);const c={},s=(0,a.A)(c,[["render",r]]);var l=s,u=n(1387),d=n(7845),f=n(6400),p=n(7530);const v={apiKey:"AIzaSyBByeGSOiAnyZcuyP_jgRgjYoXnzAM-mM4",authDomain:"picam-262bc.firebaseapp.com",projectId:"picam-262bc",storageBucket:"picam-262bc.appspot.com",messagingSenderId:"963842013886",appId:"1:963842013886:web:0ec795658960a996eebcef",measurementId:"G-H2Z212699G"},m=(0,f.Wp)(v),g=(0,d.xI)(m),h=(0,p.dG)(m);(0,p.xD)(h,(e=>{console.log("Message received. ",e);const t=e.notification.title,n={body:e.notification.body,icon:e.notification.icon};"Notification"in window?"granted"===Notification.permission&&new Notification(t,n):alert("This browser does not support desktop notification")}));var b=n(144);const y={class:"live-feed-page"},w=(0,i.Lk)("h1",{class:"pa-3"},"Home Cam Live Feed!",-1),k={class:"ma-6 mb-9"},O=["src"];var _={__name:"LiveFeed",setup(e){const t=(0,b.KR)(""),n=()=>{(0,d.CI)(g),window.location.reload()},o=async()=>{const e=await g.currentUser.getIdToken();t.value=`/api/video_feed?user_id_token=${e}`};return o(),(e,o)=>{const r=(0,i.g2)("v-btn");return(0,i.uX)(),(0,i.CE)("div",y,[w,(0,i.Lk)("div",k,[(0,i.bF)(r,{onClick:n},{default:(0,i.k6)((()=>[(0,i.eW)("sign out")])),_:1})]),(0,i.Lk)("img",{style:{width:"-webkit-fill-available"},src:t.value},null,8,O)])}}};const C=_;var j=C;const x={class:"d-flex flex-column justify-center align-center",style:{height:"100vh"}},L={class:"page"},S=(0,i.Lk)("h3",null,"Enter Your PiCam User Credential",-1);var F={__name:"UserLogin",setup(e){const t=(0,b.KR)(""),n=(0,b.KR)(""),o=(0,b.KR)(!1),r=async()=>{let e="";try{const o=await(0,d.x9)(g,t.value,n.value);e=o.user}catch(o){console.error(o.message),alert("Login faild"),alert(o.message)}await a(e).catch((e=>{alert(e)}))},a=async e=>{"Notification"in window?(alert(Notification.permission),"granted"!=Notification.permission&&await Notification.requestPermission(),"granted"==Notification.permission?await(0,p.gf)(h,{vapidKey:"BCuf1gfQ26ONFqnapY-pXl9khG63_3C_JOdUvC-zFekSAhtmNV6erEY4K3B3725Z48Ch4qr-fv5D8S3xnXlaERs"}).then((async t=>{t?await fetch("/api/set_token",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({token:t,userIdToken:await e.getIdToken(!0)})}):alert("No registration token available")})).catch((e=>{console.error("An error occurred while retrieving token. ",e),alert("An error occurred while retrieving token. ",e)})):alert("Your notification are blocked, you will not get messages when someone is at the door")):alert("your browser doesn't support notification")},c=()=>{o.value=!o.value};return(e,a)=>{const s=(0,i.g2)("v-text-field"),l=(0,i.g2)("v-btn"),u=(0,i.g2)("v-form");return(0,i.uX)(),(0,i.CE)("div",x,[(0,i.Lk)("div",L,[S,(0,i.bF)(u,{class:"form"},{default:(0,i.k6)((()=>[(0,i.bF)(s,{modelValue:t.value,"onUpdate:modelValue":a[0]||(a[0]=e=>t.value=e),label:"Email",type:"email"},null,8,["modelValue"]),(0,i.bF)(s,{modelValue:n.value,"onUpdate:modelValue":a[1]||(a[1]=e=>n.value=e),label:"Password",type:o.value?"text":"password","append-inner-icon":o.value?"mdi-eye":"mdi-eye-off","onClick:appendInner":c},null,8,["modelValue","type","append-inner-icon"]),(0,i.bF)(l,{onClick:r},{default:(0,i.k6)((()=>[(0,i.eW)("Login")])),_:1})])),_:1})])])}}};const N=F;var I=N;const E=[{path:"/",name:"Login",component:I},{path:"/liveFeed",name:"LiveFeed",component:j}],T=(0,u.aE)({history:(0,u.LA)("/"),routes:E});T.beforeEach(((e,t,n)=>{const o=(0,d.xI)();(0,d.hg)(o,(t=>{t?"/"===e.path?n("/LiveFeed"):n():"/"!==e.path?n("/"):n()}))}));var P=T,A=n(782),K=(0,A.y$)({state:{},getters:{},mutations:{},actions:{},modules:{}}),R=(n(5524),n(7768)),V=n(1920),M=n(5741);const U=(0,R.$N)({components:V,directives:M,icons:{iconfont:"mdi",defaultSet:"mdi"}});(0,o.Ef)(l).use(K).use(P).use(U).mount("#app"),navigator.serviceWorker.register("/firebase-messaging-sw.js",{scope:"/"}).then((()=>{console.log("Registerd service worker")})).catch((e=>{console.error("Service worker registration failed:",e)}))}},t={};function n(o){var i=t[o];if(void 0!==i)return i.exports;var r=t[o]={exports:{}};return e[o].call(r.exports,r,r.exports,n),r.exports}n.m=e,function(){var e=[];n.O=function(t,o,i,r){if(!o){var a=1/0;for(u=0;u<e.length;u++){o=e[u][0],i=e[u][1],r=e[u][2];for(var c=!0,s=0;s<o.length;s++)(!1&r||a>=r)&&Object.keys(n.O).every((function(e){return n.O[e](o[s])}))?o.splice(s--,1):(c=!1,r<a&&(a=r));if(c){e.splice(u--,1);var l=i();void 0!==l&&(t=l)}}return t}r=r||0;for(var u=e.length;u>0&&e[u-1][2]>r;u--)e[u]=e[u-1];e[u]=[o,i,r]}}(),function(){n.n=function(e){var t=e&&e.__esModule?function(){return e["default"]}:function(){return e};return n.d(t,{a:t}),t}}(),function(){n.d=function(e,t){for(var o in t)n.o(t,o)&&!n.o(e,o)&&Object.defineProperty(e,o,{enumerable:!0,get:t[o]})}}(),function(){n.g=function(){if("object"===typeof globalThis)return globalThis;try{return this||new Function("return this")()}catch(e){if("object"===typeof window)return window}}()}(),function(){n.o=function(e,t){return Object.prototype.hasOwnProperty.call(e,t)}}(),function(){n.r=function(e){"undefined"!==typeof Symbol&&Symbol.toStringTag&&Object.defineProperty(e,Symbol.toStringTag,{value:"Module"}),Object.defineProperty(e,"__esModule",{value:!0})}}(),function(){var e={524:0};n.O.j=function(t){return 0===e[t]};var t=function(t,o){var i,r,a=o[0],c=o[1],s=o[2],l=0;if(a.some((function(t){return 0!==e[t]}))){for(i in c)n.o(c,i)&&(n.m[i]=c[i]);if(s)var u=s(n)}for(t&&t(o);l<a.length;l++)r=a[l],n.o(e,r)&&e[r]&&e[r][0](),e[r]=0;return n.O(u)},o=self["webpackChunkpicam"]=self["webpackChunkpicam"]||[];o.forEach(t.bind(null,0)),o.push=t.bind(null,o.push.bind(o))}();var o=n.O(void 0,[504],(function(){return n(9596)}));o=n.O(o)})();
//# sourceMappingURL=app.f8478c5e.js.map