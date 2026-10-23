var top="top",bottom="bottom",right="right",left="left",auto="auto",basePlacements=[top,bottom,right,left],start="start",end="end",clippingParents="clippingParents",viewport="viewport",popper="popper",reference="reference",variationPlacements=basePlacements.reduce(function(n,e){return n.concat([e+"-"+start,e+"-"+end])},[]),placements=[].concat(basePlacements,[auto]).reduce(function(n,e){return n.concat([e,e+"-"+start,e+"-"+end])},[]),beforeRead="beforeRead",read="read",afterRead="afterRead",beforeMain="beforeMain",main="main",afterMain="afterMain",beforeWrite="beforeWrite",write="write",afterWrite="afterWrite",modifierPhases=[beforeRead,read,afterRead,beforeMain,main,afterMain,beforeWrite,write,afterWrite];function getNodeName(n){return n?(n.nodeName||"").toLowerCase():null}function getWindow(n){if(n==null)return window;if(n.toString()!=="[object Window]"){var e=n.ownerDocument;return e&&e.defaultView||window}return n}function isElement$1(n){var e=getWindow(n).Element;return n instanceof e||n instanceof Element}function isHTMLElement(n){var e=getWindow(n).HTMLElement;return n instanceof e||n instanceof HTMLElement}function isShadowRoot(n){if(typeof ShadowRoot>"u")return!1;var e=getWindow(n).ShadowRoot;return n instanceof e||n instanceof ShadowRoot}function applyStyles(n){var e=n.state;Object.keys(e.elements).forEach(function(t){var r=e.styles[t]||{},a=e.attributes[t]||{},o=e.elements[t];!isHTMLElement(o)||!getNodeName(o)||(Object.assign(o.style,r),Object.keys(a).forEach(function(s){var l=a[s];l===!1?o.removeAttribute(s):o.setAttribute(s,l===!0?"":l)}))})}function effect$2(n){var e=n.state,t={popper:{position:e.options.strategy,left:"0",top:"0",margin:"0"},arrow:{position:"absolute"},reference:{}};return Object.assign(e.elements.popper.style,t.popper),e.styles=t,e.elements.arrow&&Object.assign(e.elements.arrow.style,t.arrow),function(){Object.keys(e.elements).forEach(function(r){var a=e.elements[r],o=e.attributes[r]||{},s=Object.keys(e.styles.hasOwnProperty(r)?e.styles[r]:t[r]),l=s.reduce(function(c,f){return c[f]="",c},{});!isHTMLElement(a)||!getNodeName(a)||(Object.assign(a.style,l),Object.keys(o).forEach(function(c){a.removeAttribute(c)}))})}}const applyStyles$1={name:"applyStyles",enabled:!0,phase:"write",fn:applyStyles,effect:effect$2,requires:["computeStyles"]};function getBasePlacement(n){return n.split("-")[0]}var max=Math.max,min=Math.min,round$1=Math.round;function getUAString(){var n=navigator.userAgentData;return n!=null&&n.brands&&Array.isArray(n.brands)?n.brands.map(function(e){return e.brand+"/"+e.version}).join(" "):navigator.userAgent}function isLayoutViewport(){return!/^((?!chrome|android).)*safari/i.test(getUAString())}function getBoundingClientRect(n,e,t){e===void 0&&(e=!1),t===void 0&&(t=!1);var r=n.getBoundingClientRect(),a=1,o=1;e&&isHTMLElement(n)&&(a=n.offsetWidth>0&&round$1(r.width)/n.offsetWidth||1,o=n.offsetHeight>0&&round$1(r.height)/n.offsetHeight||1);var s=isElement$1(n)?getWindow(n):window,l=s.visualViewport,c=!isLayoutViewport()&&t,f=(r.left+(c&&l?l.offsetLeft:0))/a,d=(r.top+(c&&l?l.offsetTop:0))/o,p=r.width/a,_=r.height/o;return{width:p,height:_,top:d,right:f+p,bottom:d+_,left:f,x:f,y:d}}function getLayoutRect(n){var e=getBoundingClientRect(n),t=n.offsetWidth,r=n.offsetHeight;return Math.abs(e.width-t)<=1&&(t=e.width),Math.abs(e.height-r)<=1&&(r=e.height),{x:n.offsetLeft,y:n.offsetTop,width:t,height:r}}function contains(n,e){var t=e.getRootNode&&e.getRootNode();if(n.contains(e))return!0;if(t&&isShadowRoot(t)){var r=e;do{if(r&&n.isSameNode(r))return!0;r=r.parentNode||r.host}while(r)}return!1}function getComputedStyle$2(n){return getWindow(n).getComputedStyle(n)}function isTableElement(n){return["table","td","th"].indexOf(getNodeName(n))>=0}function getDocumentElement(n){return((isElement$1(n)?n.ownerDocument:n.document)||window.document).documentElement}function getParentNode(n){return getNodeName(n)==="html"?n:n.assignedSlot||n.parentNode||(isShadowRoot(n)?n.host:null)||getDocumentElement(n)}function getTrueOffsetParent(n){return!isHTMLElement(n)||getComputedStyle$2(n).position==="fixed"?null:n.offsetParent}function getContainingBlock(n){var e=/firefox/i.test(getUAString()),t=/Trident/i.test(getUAString());if(t&&isHTMLElement(n)){var r=getComputedStyle$2(n);if(r.position==="fixed")return null}var a=getParentNode(n);for(isShadowRoot(a)&&(a=a.host);isHTMLElement(a)&&["html","body"].indexOf(getNodeName(a))<0;){var o=getComputedStyle$2(a);if(o.transform!=="none"||o.perspective!=="none"||o.contain==="paint"||["transform","perspective"].indexOf(o.willChange)!==-1||e&&o.willChange==="filter"||e&&o.filter&&o.filter!=="none")return a;a=a.parentNode}return null}function getOffsetParent(n){for(var e=getWindow(n),t=getTrueOffsetParent(n);t&&isTableElement(t)&&getComputedStyle$2(t).position==="static";)t=getTrueOffsetParent(t);return t&&(getNodeName(t)==="html"||getNodeName(t)==="body"&&getComputedStyle$2(t).position==="static")?e:t||getContainingBlock(n)||e}function getMainAxisFromPlacement(n){return["top","bottom"].indexOf(n)>=0?"x":"y"}function within(n,e,t){return max(n,min(e,t))}function withinMaxClamp(n,e,t){var r=within(n,e,t);return r>t?t:r}function getFreshSideObject(){return{top:0,right:0,bottom:0,left:0}}function mergePaddingObject(n){return Object.assign({},getFreshSideObject(),n)}function expandToHashMap(n,e){return e.reduce(function(t,r){return t[r]=n,t},{})}var toPaddingObject=function(e,t){return e=typeof e=="function"?e(Object.assign({},t.rects,{placement:t.placement})):e,mergePaddingObject(typeof e!="number"?e:expandToHashMap(e,basePlacements))};function arrow(n){var e,t=n.state,r=n.name,a=n.options,o=t.elements.arrow,s=t.modifiersData.popperOffsets,l=getBasePlacement(t.placement),c=getMainAxisFromPlacement(l),f=[left,right].indexOf(l)>=0,d=f?"height":"width";if(!(!o||!s)){var p=toPaddingObject(a.padding,t),_=getLayoutRect(o),b=c==="y"?top:left,y=c==="y"?bottom:right,E=t.rects.reference[d]+t.rects.reference[c]-s[c]-t.rects.popper[d],C=s[c]-t.rects.reference[c],D=getOffsetParent(o),M=D?c==="y"?D.clientHeight||0:D.clientWidth||0:0,F=E/2-C/2,P=p[b],H=M-_[d]-p[y],B=M/2-_[d]/2+F,g=within(P,B,H),q=c;t.modifiersData[r]=(e={},e[q]=g,e.centerOffset=g-B,e)}}function effect$1(n){var e=n.state,t=n.options,r=t.element,a=r===void 0?"[data-popper-arrow]":r;a!=null&&(typeof a=="string"&&(a=e.elements.popper.querySelector(a),!a)||contains(e.elements.popper,a)&&(e.elements.arrow=a))}const arrow$1={name:"arrow",enabled:!0,phase:"main",fn:arrow,effect:effect$1,requires:["popperOffsets"],requiresIfExists:["preventOverflow"]};function getVariation(n){return n.split("-")[1]}var unsetSides={top:"auto",right:"auto",bottom:"auto",left:"auto"};function roundOffsetsByDPR(n,e){var t=n.x,r=n.y,a=e.devicePixelRatio||1;return{x:round$1(t*a)/a||0,y:round$1(r*a)/a||0}}function mapToStyles(n){var e,t=n.popper,r=n.popperRect,a=n.placement,o=n.variation,s=n.offsets,l=n.position,c=n.gpuAcceleration,f=n.adaptive,d=n.roundOffsets,p=n.isFixed,_=s.x,b=_===void 0?0:_,y=s.y,E=y===void 0?0:y,C=typeof d=="function"?d({x:b,y:E}):{x:b,y:E};b=C.x,E=C.y;var D=s.hasOwnProperty("x"),M=s.hasOwnProperty("y"),F=left,P=top,H=window;if(f){var B=getOffsetParent(t),g="clientHeight",q="clientWidth";if(B===getWindow(t)&&(B=getDocumentElement(t),getComputedStyle$2(B).position!=="static"&&l==="absolute"&&(g="scrollHeight",q="scrollWidth")),B=B,a===top||(a===left||a===right)&&o===end){P=bottom;var G=p&&B===H&&H.visualViewport?H.visualViewport.height:B[g];E-=G-r.height,E*=c?1:-1}if(a===left||(a===top||a===bottom)&&o===end){F=right;var Z=p&&B===H&&H.visualViewport?H.visualViewport.width:B[q];b-=Z-r.width,b*=c?1:-1}}var te=Object.assign({position:l},f&&unsetSides),ne=d===!0?roundOffsetsByDPR({x:b,y:E},getWindow(t)):{x:b,y:E};if(b=ne.x,E=ne.y,c){var Q;return Object.assign({},te,(Q={},Q[P]=M?"0":"",Q[F]=D?"0":"",Q.transform=(H.devicePixelRatio||1)<=1?"translate("+b+"px, "+E+"px)":"translate3d("+b+"px, "+E+"px, 0)",Q))}return Object.assign({},te,(e={},e[P]=M?E+"px":"",e[F]=D?b+"px":"",e.transform="",e))}function computeStyles(n){var e=n.state,t=n.options,r=t.gpuAcceleration,a=r===void 0?!0:r,o=t.adaptive,s=o===void 0?!0:o,l=t.roundOffsets,c=l===void 0?!0:l,f={placement:getBasePlacement(e.placement),variation:getVariation(e.placement),popper:e.elements.popper,popperRect:e.rects.popper,gpuAcceleration:a,isFixed:e.options.strategy==="fixed"};e.modifiersData.popperOffsets!=null&&(e.styles.popper=Object.assign({},e.styles.popper,mapToStyles(Object.assign({},f,{offsets:e.modifiersData.popperOffsets,position:e.options.strategy,adaptive:s,roundOffsets:c})))),e.modifiersData.arrow!=null&&(e.styles.arrow=Object.assign({},e.styles.arrow,mapToStyles(Object.assign({},f,{offsets:e.modifiersData.arrow,position:"absolute",adaptive:!1,roundOffsets:c})))),e.attributes.popper=Object.assign({},e.attributes.popper,{"data-popper-placement":e.placement})}const computeStyles$1={name:"computeStyles",enabled:!0,phase:"beforeWrite",fn:computeStyles,data:{}};var passive={passive:!0};function effect(n){var e=n.state,t=n.instance,r=n.options,a=r.scroll,o=a===void 0?!0:a,s=r.resize,l=s===void 0?!0:s,c=getWindow(e.elements.popper),f=[].concat(e.scrollParents.reference,e.scrollParents.popper);return o&&f.forEach(function(d){d.addEventListener("scroll",t.update,passive)}),l&&c.addEventListener("resize",t.update,passive),function(){o&&f.forEach(function(d){d.removeEventListener("scroll",t.update,passive)}),l&&c.removeEventListener("resize",t.update,passive)}}const eventListeners={name:"eventListeners",enabled:!0,phase:"write",fn:function(){},effect,data:{}};var hash$1={left:"right",right:"left",bottom:"top",top:"bottom"};function getOppositePlacement(n){return n.replace(/left|right|bottom|top/g,function(e){return hash$1[e]})}var hash={start:"end",end:"start"};function getOppositeVariationPlacement(n){return n.replace(/start|end/g,function(e){return hash[e]})}function getWindowScroll(n){var e=getWindow(n),t=e.pageXOffset,r=e.pageYOffset;return{scrollLeft:t,scrollTop:r}}function getWindowScrollBarX(n){return getBoundingClientRect(getDocumentElement(n)).left+getWindowScroll(n).scrollLeft}function getViewportRect(n,e){var t=getWindow(n),r=getDocumentElement(n),a=t.visualViewport,o=r.clientWidth,s=r.clientHeight,l=0,c=0;if(a){o=a.width,s=a.height;var f=isLayoutViewport();(f||!f&&e==="fixed")&&(l=a.offsetLeft,c=a.offsetTop)}return{width:o,height:s,x:l+getWindowScrollBarX(n),y:c}}function getDocumentRect(n){var e,t=getDocumentElement(n),r=getWindowScroll(n),a=(e=n.ownerDocument)==null?void 0:e.body,o=max(t.scrollWidth,t.clientWidth,a?a.scrollWidth:0,a?a.clientWidth:0),s=max(t.scrollHeight,t.clientHeight,a?a.scrollHeight:0,a?a.clientHeight:0),l=-r.scrollLeft+getWindowScrollBarX(n),c=-r.scrollTop;return getComputedStyle$2(a||t).direction==="rtl"&&(l+=max(t.clientWidth,a?a.clientWidth:0)-o),{width:o,height:s,x:l,y:c}}function isScrollParent(n){var e=getComputedStyle$2(n),t=e.overflow,r=e.overflowX,a=e.overflowY;return/auto|scroll|overlay|hidden/.test(t+a+r)}function getScrollParent(n){return["html","body","#document"].indexOf(getNodeName(n))>=0?n.ownerDocument.body:isHTMLElement(n)&&isScrollParent(n)?n:getScrollParent(getParentNode(n))}function listScrollParents(n,e){var t;e===void 0&&(e=[]);var r=getScrollParent(n),a=r===((t=n.ownerDocument)==null?void 0:t.body),o=getWindow(r),s=a?[o].concat(o.visualViewport||[],isScrollParent(r)?r:[]):r,l=e.concat(s);return a?l:l.concat(listScrollParents(getParentNode(s)))}function rectToClientRect(n){return Object.assign({},n,{left:n.x,top:n.y,right:n.x+n.width,bottom:n.y+n.height})}function getInnerBoundingClientRect(n,e){var t=getBoundingClientRect(n,!1,e==="fixed");return t.top=t.top+n.clientTop,t.left=t.left+n.clientLeft,t.bottom=t.top+n.clientHeight,t.right=t.left+n.clientWidth,t.width=n.clientWidth,t.height=n.clientHeight,t.x=t.left,t.y=t.top,t}function getClientRectFromMixedType(n,e,t){return e===viewport?rectToClientRect(getViewportRect(n,t)):isElement$1(e)?getInnerBoundingClientRect(e,t):rectToClientRect(getDocumentRect(getDocumentElement(n)))}function getClippingParents(n){var e=listScrollParents(getParentNode(n)),t=["absolute","fixed"].indexOf(getComputedStyle$2(n).position)>=0,r=t&&isHTMLElement(n)?getOffsetParent(n):n;return isElement$1(r)?e.filter(function(a){return isElement$1(a)&&contains(a,r)&&getNodeName(a)!=="body"}):[]}function getClippingRect(n,e,t,r){var a=e==="clippingParents"?getClippingParents(n):[].concat(e),o=[].concat(a,[t]),s=o[0],l=o.reduce(function(c,f){var d=getClientRectFromMixedType(n,f,r);return c.top=max(d.top,c.top),c.right=min(d.right,c.right),c.bottom=min(d.bottom,c.bottom),c.left=max(d.left,c.left),c},getClientRectFromMixedType(n,s,r));return l.width=l.right-l.left,l.height=l.bottom-l.top,l.x=l.left,l.y=l.top,l}function computeOffsets(n){var e=n.reference,t=n.element,r=n.placement,a=r?getBasePlacement(r):null,o=r?getVariation(r):null,s=e.x+e.width/2-t.width/2,l=e.y+e.height/2-t.height/2,c;switch(a){case top:c={x:s,y:e.y-t.height};break;case bottom:c={x:s,y:e.y+e.height};break;case right:c={x:e.x+e.width,y:l};break;case left:c={x:e.x-t.width,y:l};break;default:c={x:e.x,y:e.y}}var f=a?getMainAxisFromPlacement(a):null;if(f!=null){var d=f==="y"?"height":"width";switch(o){case start:c[f]=c[f]-(e[d]/2-t[d]/2);break;case end:c[f]=c[f]+(e[d]/2-t[d]/2);break}}return c}function detectOverflow(n,e){e===void 0&&(e={});var t=e,r=t.placement,a=r===void 0?n.placement:r,o=t.strategy,s=o===void 0?n.strategy:o,l=t.boundary,c=l===void 0?clippingParents:l,f=t.rootBoundary,d=f===void 0?viewport:f,p=t.elementContext,_=p===void 0?popper:p,b=t.altBoundary,y=b===void 0?!1:b,E=t.padding,C=E===void 0?0:E,D=mergePaddingObject(typeof C!="number"?C:expandToHashMap(C,basePlacements)),M=_===popper?reference:popper,F=n.rects.popper,P=n.elements[y?M:_],H=getClippingRect(isElement$1(P)?P:P.contextElement||getDocumentElement(n.elements.popper),c,d,s),B=getBoundingClientRect(n.elements.reference),g=computeOffsets({reference:B,element:F,placement:a}),q=rectToClientRect(Object.assign({},F,g)),G=_===popper?q:B,Z={top:H.top-G.top+D.top,bottom:G.bottom-H.bottom+D.bottom,left:H.left-G.left+D.left,right:G.right-H.right+D.right},te=n.modifiersData.offset;if(_===popper&&te){var ne=te[a];Object.keys(Z).forEach(function(Q){var Ee=[right,bottom].indexOf(Q)>=0?1:-1,re=[top,bottom].indexOf(Q)>=0?"y":"x";Z[Q]+=ne[re]*Ee})}return Z}function computeAutoPlacement(n,e){e===void 0&&(e={});var t=e,r=t.placement,a=t.boundary,o=t.rootBoundary,s=t.padding,l=t.flipVariations,c=t.allowedAutoPlacements,f=c===void 0?placements:c,d=getVariation(r),p=d?l?variationPlacements:variationPlacements.filter(function(y){return getVariation(y)===d}):basePlacements,_=p.filter(function(y){return f.indexOf(y)>=0});_.length===0&&(_=p);var b=_.reduce(function(y,E){return y[E]=detectOverflow(n,{placement:E,boundary:a,rootBoundary:o,padding:s})[getBasePlacement(E)],y},{});return Object.keys(b).sort(function(y,E){return b[y]-b[E]})}function getExpandedFallbackPlacements(n){if(getBasePlacement(n)===auto)return[];var e=getOppositePlacement(n);return[getOppositeVariationPlacement(n),e,getOppositeVariationPlacement(e)]}function flip(n){var e=n.state,t=n.options,r=n.name;if(!e.modifiersData[r]._skip){for(var a=t.mainAxis,o=a===void 0?!0:a,s=t.altAxis,l=s===void 0?!0:s,c=t.fallbackPlacements,f=t.padding,d=t.boundary,p=t.rootBoundary,_=t.altBoundary,b=t.flipVariations,y=b===void 0?!0:b,E=t.allowedAutoPlacements,C=e.options.placement,D=getBasePlacement(C),M=D===C,F=c||(M||!y?[getOppositePlacement(C)]:getExpandedFallbackPlacements(C)),P=[C].concat(F).reduce(function(Fe,He){return Fe.concat(getBasePlacement(He)===auto?computeAutoPlacement(e,{placement:He,boundary:d,rootBoundary:p,padding:f,flipVariations:y,allowedAutoPlacements:E}):He)},[]),H=e.rects.reference,B=e.rects.popper,g=new Map,q=!0,G=P[0],Z=0;Z<P.length;Z++){var te=P[Z],ne=getBasePlacement(te),Q=getVariation(te)===start,Ee=[top,bottom].indexOf(ne)>=0,re=Ee?"width":"height",de=detectOverflow(e,{placement:te,boundary:d,rootBoundary:p,altBoundary:_,padding:f}),le=Ee?Q?right:left:Q?bottom:top;H[re]>B[re]&&(le=getOppositePlacement(le));var $e=getOppositePlacement(le),xe=[];if(o&&xe.push(de[ne]<=0),l&&xe.push(de[le]<=0,de[$e]<=0),xe.every(function(Fe){return Fe})){G=te,q=!1;break}g.set(te,xe)}if(q)for(var Ve=y?3:1,Re=function(He){var ge=P.find(function(Me){var Pe=g.get(Me);if(Pe)return Pe.slice(0,He).every(function(st){return st})});if(ge)return G=ge,"break"},Te=Ve;Te>0;Te--){var je=Re(Te);if(je==="break")break}e.placement!==G&&(e.modifiersData[r]._skip=!0,e.placement=G,e.reset=!0)}}const flip$1={name:"flip",enabled:!0,phase:"main",fn:flip,requiresIfExists:["offset"],data:{_skip:!1}};function getSideOffsets(n,e,t){return t===void 0&&(t={x:0,y:0}),{top:n.top-e.height-t.y,right:n.right-e.width+t.x,bottom:n.bottom-e.height+t.y,left:n.left-e.width-t.x}}function isAnySideFullyClipped(n){return[top,right,bottom,left].some(function(e){return n[e]>=0})}function hide(n){var e=n.state,t=n.name,r=e.rects.reference,a=e.rects.popper,o=e.modifiersData.preventOverflow,s=detectOverflow(e,{elementContext:"reference"}),l=detectOverflow(e,{altBoundary:!0}),c=getSideOffsets(s,r),f=getSideOffsets(l,a,o),d=isAnySideFullyClipped(c),p=isAnySideFullyClipped(f);e.modifiersData[t]={referenceClippingOffsets:c,popperEscapeOffsets:f,isReferenceHidden:d,hasPopperEscaped:p},e.attributes.popper=Object.assign({},e.attributes.popper,{"data-popper-reference-hidden":d,"data-popper-escaped":p})}const hide$1={name:"hide",enabled:!0,phase:"main",requiresIfExists:["preventOverflow"],fn:hide};function distanceAndSkiddingToXY(n,e,t){var r=getBasePlacement(n),a=[left,top].indexOf(r)>=0?-1:1,o=typeof t=="function"?t(Object.assign({},e,{placement:n})):t,s=o[0],l=o[1];return s=s||0,l=(l||0)*a,[left,right].indexOf(r)>=0?{x:l,y:s}:{x:s,y:l}}function offset(n){var e=n.state,t=n.options,r=n.name,a=t.offset,o=a===void 0?[0,0]:a,s=placements.reduce(function(d,p){return d[p]=distanceAndSkiddingToXY(p,e.rects,o),d},{}),l=s[e.placement],c=l.x,f=l.y;e.modifiersData.popperOffsets!=null&&(e.modifiersData.popperOffsets.x+=c,e.modifiersData.popperOffsets.y+=f),e.modifiersData[r]=s}const offset$1={name:"offset",enabled:!0,phase:"main",requires:["popperOffsets"],fn:offset};function popperOffsets(n){var e=n.state,t=n.name;e.modifiersData[t]=computeOffsets({reference:e.rects.reference,element:e.rects.popper,placement:e.placement})}const popperOffsets$1={name:"popperOffsets",enabled:!0,phase:"read",fn:popperOffsets,data:{}};function getAltAxis(n){return n==="x"?"y":"x"}function preventOverflow(n){var e=n.state,t=n.options,r=n.name,a=t.mainAxis,o=a===void 0?!0:a,s=t.altAxis,l=s===void 0?!1:s,c=t.boundary,f=t.rootBoundary,d=t.altBoundary,p=t.padding,_=t.tether,b=_===void 0?!0:_,y=t.tetherOffset,E=y===void 0?0:y,C=detectOverflow(e,{boundary:c,rootBoundary:f,padding:p,altBoundary:d}),D=getBasePlacement(e.placement),M=getVariation(e.placement),F=!M,P=getMainAxisFromPlacement(D),H=getAltAxis(P),B=e.modifiersData.popperOffsets,g=e.rects.reference,q=e.rects.popper,G=typeof E=="function"?E(Object.assign({},e.rects,{placement:e.placement})):E,Z=typeof G=="number"?{mainAxis:G,altAxis:G}:Object.assign({mainAxis:0,altAxis:0},G),te=e.modifiersData.offset?e.modifiersData.offset[e.placement]:null,ne={x:0,y:0};if(B){if(o){var Q,Ee=P==="y"?top:left,re=P==="y"?bottom:right,de=P==="y"?"height":"width",le=B[P],$e=le+C[Ee],xe=le-C[re],Ve=b?-q[de]/2:0,Re=M===start?g[de]:q[de],Te=M===start?-q[de]:-g[de],je=e.elements.arrow,Fe=b&&je?getLayoutRect(je):{width:0,height:0},He=e.modifiersData["arrow#persistent"]?e.modifiersData["arrow#persistent"].padding:getFreshSideObject(),ge=He[Ee],Me=He[re],Pe=within(0,g[de],Fe[de]),st=F?g[de]/2-Ve-Pe-ge-Z.mainAxis:Re-Pe-ge-Z.mainAxis,Qe=F?-g[de]/2+Ve+Pe+Me+Z.mainAxis:Te+Pe+Me+Z.mainAxis,xt=e.elements.arrow&&getOffsetParent(e.elements.arrow),tt=xt?P==="y"?xt.clientTop||0:xt.clientLeft||0:0,vt=(Q=te?.[P])!=null?Q:0,jt=le+st-vt-tt,Vt=le+Qe-vt,St=within(b?min($e,jt):$e,le,b?max(xe,Vt):xe);B[P]=St,ne[P]=St-le}if(l){var dt,Je=P==="x"?top:left,Ct=P==="x"?bottom:right,lt=B[H],At=H==="y"?"height":"width",qe=lt+C[Je],nt=lt-C[Ct],it=[top,left].indexOf(D)!==-1,ue=(dt=te?.[H])!=null?dt:0,We=it?qe:lt-g[At]-q[At]-ue+Z.altAxis,kt=it?lt+g[At]+q[At]-ue-Z.altAxis:nt,Wt=b&&it?withinMaxClamp(We,lt,kt):within(b?We:qe,lt,b?kt:nt);B[H]=Wt,ne[H]=Wt-lt}e.modifiersData[r]=ne}}const preventOverflow$1={name:"preventOverflow",enabled:!0,phase:"main",fn:preventOverflow,requiresIfExists:["offset"]};function getHTMLElementScroll(n){return{scrollLeft:n.scrollLeft,scrollTop:n.scrollTop}}function getNodeScroll(n){return n===getWindow(n)||!isHTMLElement(n)?getWindowScroll(n):getHTMLElementScroll(n)}function isElementScaled(n){var e=n.getBoundingClientRect(),t=round$1(e.width)/n.offsetWidth||1,r=round$1(e.height)/n.offsetHeight||1;return t!==1||r!==1}function getCompositeRect(n,e,t){t===void 0&&(t=!1);var r=isHTMLElement(e),a=isHTMLElement(e)&&isElementScaled(e),o=getDocumentElement(e),s=getBoundingClientRect(n,a,t),l={scrollLeft:0,scrollTop:0},c={x:0,y:0};return(r||!r&&!t)&&((getNodeName(e)!=="body"||isScrollParent(o))&&(l=getNodeScroll(e)),isHTMLElement(e)?(c=getBoundingClientRect(e,!0),c.x+=e.clientLeft,c.y+=e.clientTop):o&&(c.x=getWindowScrollBarX(o))),{x:s.left+l.scrollLeft-c.x,y:s.top+l.scrollTop-c.y,width:s.width,height:s.height}}function order(n){var e=new Map,t=new Set,r=[];n.forEach(function(o){e.set(o.name,o)});function a(o){t.add(o.name);var s=[].concat(o.requires||[],o.requiresIfExists||[]);s.forEach(function(l){if(!t.has(l)){var c=e.get(l);c&&a(c)}}),r.push(o)}return n.forEach(function(o){t.has(o.name)||a(o)}),r}function orderModifiers(n){var e=order(n);return modifierPhases.reduce(function(t,r){return t.concat(e.filter(function(a){return a.phase===r}))},[])}function debounce$2(n){var e;return function(){return e||(e=new Promise(function(t){Promise.resolve().then(function(){e=void 0,t(n())})})),e}}function mergeByName(n){var e=n.reduce(function(t,r){var a=t[r.name];return t[r.name]=a?Object.assign({},a,r,{options:Object.assign({},a.options,r.options),data:Object.assign({},a.data,r.data)}):r,t},{});return Object.keys(e).map(function(t){return e[t]})}var DEFAULT_OPTIONS={placement:"bottom",modifiers:[],strategy:"absolute"};function areValidElements(){for(var n=arguments.length,e=new Array(n),t=0;t<n;t++)e[t]=arguments[t];return!e.some(function(r){return!(r&&typeof r.getBoundingClientRect=="function")})}function popperGenerator(n){n===void 0&&(n={});var e=n,t=e.defaultModifiers,r=t===void 0?[]:t,a=e.defaultOptions,o=a===void 0?DEFAULT_OPTIONS:a;return function(l,c,f){f===void 0&&(f=o);var d={placement:"bottom",orderedModifiers:[],options:Object.assign({},DEFAULT_OPTIONS,o),modifiersData:{},elements:{reference:l,popper:c},attributes:{},styles:{}},p=[],_=!1,b={state:d,setOptions:function(D){var M=typeof D=="function"?D(d.options):D;E(),d.options=Object.assign({},o,d.options,M),d.scrollParents={reference:isElement$1(l)?listScrollParents(l):l.contextElement?listScrollParents(l.contextElement):[],popper:listScrollParents(c)};var F=orderModifiers(mergeByName([].concat(r,d.options.modifiers)));return d.orderedModifiers=F.filter(function(P){return P.enabled}),y(),b.update()},forceUpdate:function(){if(!_){var D=d.elements,M=D.reference,F=D.popper;if(areValidElements(M,F)){d.rects={reference:getCompositeRect(M,getOffsetParent(F),d.options.strategy==="fixed"),popper:getLayoutRect(F)},d.reset=!1,d.placement=d.options.placement,d.orderedModifiers.forEach(function(Z){return d.modifiersData[Z.name]=Object.assign({},Z.data)});for(var P=0;P<d.orderedModifiers.length;P++){if(d.reset===!0){d.reset=!1,P=-1;continue}var H=d.orderedModifiers[P],B=H.fn,g=H.options,q=g===void 0?{}:g,G=H.name;typeof B=="function"&&(d=B({state:d,options:q,name:G,instance:b})||d)}}}},update:debounce$2(function(){return new Promise(function(C){b.forceUpdate(),C(d)})}),destroy:function(){E(),_=!0}};if(!areValidElements(l,c))return b;b.setOptions(f).then(function(C){!_&&f.onFirstUpdate&&f.onFirstUpdate(C)});function y(){d.orderedModifiers.forEach(function(C){var D=C.name,M=C.options,F=M===void 0?{}:M,P=C.effect;if(typeof P=="function"){var H=P({state:d,name:D,instance:b,options:F}),B=function(){};p.push(H||B)}})}function E(){p.forEach(function(C){return C()}),p=[]}return b}}var defaultModifiers=[eventListeners,popperOffsets$1,computeStyles$1,applyStyles$1,offset$1,flip$1,preventOverflow$1,arrow$1,hide$1],createPopper=popperGenerator({defaultModifiers});const Popper=Object.freeze(Object.defineProperty({__proto__:null,afterMain,afterRead,afterWrite,applyStyles:applyStyles$1,arrow:arrow$1,auto,basePlacements,beforeMain,beforeRead,beforeWrite,bottom,clippingParents,computeStyles:computeStyles$1,createPopper,detectOverflow,end,eventListeners,flip:flip$1,hide:hide$1,left,main,modifierPhases,offset:offset$1,placements,popper,popperGenerator,popperOffsets:popperOffsets$1,preventOverflow:preventOverflow$1,read,reference,right,start,top,variationPlacements,viewport,write},Symbol.toStringTag,{value:"Module"}));const elementMap=new Map,Data={set(n,e,t){elementMap.has(n)||elementMap.set(n,new Map);const r=elementMap.get(n);if(!r.has(e)&&r.size!==0){console.error(`Bootstrap doesn't allow more than one instance per element. Bound instance: ${Array.from(r.keys())[0]}.`);return}r.set(e,t)},get(n,e){return elementMap.has(n)&&elementMap.get(n).get(e)||null},remove(n,e){if(!elementMap.has(n))return;const t=elementMap.get(n);t.delete(e),t.size===0&&elementMap.delete(n)}},MAX_UID=1e6,MILLISECONDS_MULTIPLIER=1e3,TRANSITION_END="transitionend",parseSelector=n=>(n&&window.CSS&&window.CSS.escape&&(n=n.replace(/#([^\s"#']+)/g,(e,t)=>`#${CSS.escape(t)}`)),n),toType=n=>n==null?`${n}`:Object.prototype.toString.call(n).match(/\s([a-z]+)/i)[1].toLowerCase(),getUID=n=>{do n+=Math.floor(Math.random()*MAX_UID);while(document.getElementById(n));return n},getTransitionDurationFromElement=n=>{if(!n)return 0;let{transitionDuration:e,transitionDelay:t}=window.getComputedStyle(n);const r=Number.parseFloat(e),a=Number.parseFloat(t);return!r&&!a?0:(e=e.split(",")[0],t=t.split(",")[0],(Number.parseFloat(e)+Number.parseFloat(t))*MILLISECONDS_MULTIPLIER)},triggerTransitionEnd=n=>{n.dispatchEvent(new Event(TRANSITION_END))},isElement=n=>!n||typeof n!="object"?!1:(typeof n.jquery<"u"&&(n=n[0]),typeof n.nodeType<"u"),getElement=n=>isElement(n)?n.jquery?n[0]:n:typeof n=="string"&&n.length>0?document.querySelector(parseSelector(n)):null,isVisible=n=>{if(!isElement(n)||n.getClientRects().length===0)return!1;const e=getComputedStyle(n).getPropertyValue("visibility")==="visible",t=n.closest("details:not([open])");if(!t)return e;if(t!==n){const r=n.closest("summary");if(r&&r.parentNode!==t||r===null)return!1}return e},isDisabled=n=>!n||n.nodeType!==Node.ELEMENT_NODE||n.classList.contains("disabled")?!0:typeof n.disabled<"u"?n.disabled:n.hasAttribute("disabled")&&n.getAttribute("disabled")!=="false",findShadowRoot=n=>{if(!document.documentElement.attachShadow)return null;if(typeof n.getRootNode=="function"){const e=n.getRootNode();return e instanceof ShadowRoot?e:null}return n instanceof ShadowRoot?n:n.parentNode?findShadowRoot(n.parentNode):null},noop$1=()=>{},reflow=n=>{n.offsetHeight},getjQuery=()=>window.jQuery&&!document.body.hasAttribute("data-bs-no-jquery")?window.jQuery:null,DOMContentLoadedCallbacks=[],onDOMContentLoaded=n=>{document.readyState==="loading"?(DOMContentLoadedCallbacks.length||document.addEventListener("DOMContentLoaded",()=>{for(const e of DOMContentLoadedCallbacks)e()}),DOMContentLoadedCallbacks.push(n)):n()},isRTL=()=>document.documentElement.dir==="rtl",defineJQueryPlugin=n=>{onDOMContentLoaded(()=>{const e=getjQuery();if(e){const t=n.NAME,r=e.fn[t];e.fn[t]=n.jQueryInterface,e.fn[t].Constructor=n,e.fn[t].noConflict=()=>(e.fn[t]=r,n.jQueryInterface)}})},execute=(n,e=[],t=n)=>typeof n=="function"?n.call(...e):t,executeAfterTransition=(n,e,t=!0)=>{if(!t){execute(n);return}const a=getTransitionDurationFromElement(e)+5;let o=!1;const s=({target:l})=>{l===e&&(o=!0,e.removeEventListener(TRANSITION_END,s),execute(n))};e.addEventListener(TRANSITION_END,s),setTimeout(()=>{o||triggerTransitionEnd(e)},a)},getNextActiveElement=(n,e,t,r)=>{const a=n.length;let o=n.indexOf(e);return o===-1?!t&&r?n[a-1]:n[0]:(o+=t?1:-1,r&&(o=(o+a)%a),n[Math.max(0,Math.min(o,a-1))])},namespaceRegex=/[^.]*(?=\..*)\.|.*/,stripNameRegex=/\..*/,stripUidRegex=/::\d+$/,eventRegistry={};let uidEvent=1;const customEvents={mouseenter:"mouseover",mouseleave:"mouseout"},nativeEvents=new Set(["click","dblclick","mouseup","mousedown","contextmenu","mousewheel","DOMMouseScroll","mouseover","mouseout","mousemove","selectstart","selectend","keydown","keypress","keyup","orientationchange","touchstart","touchmove","touchend","touchcancel","pointerdown","pointermove","pointerup","pointerleave","pointercancel","gesturestart","gesturechange","gestureend","focus","blur","change","reset","select","submit","focusin","focusout","load","unload","beforeunload","resize","move","DOMContentLoaded","readystatechange","error","abort","scroll"]);function makeEventUid(n,e){return e&&`${e}::${uidEvent++}`||n.uidEvent||uidEvent++}function getElementEvents(n){const e=makeEventUid(n);return n.uidEvent=e,eventRegistry[e]=eventRegistry[e]||{},eventRegistry[e]}function bootstrapHandler(n,e){return function t(r){return hydrateObj(r,{delegateTarget:n}),t.oneOff&&EventHandler.off(n,r.type,e),e.apply(n,[r])}}function bootstrapDelegationHandler(n,e,t){return function r(a){const o=n.querySelectorAll(e);for(let{target:s}=a;s&&s!==this;s=s.parentNode)for(const l of o)if(l===s)return hydrateObj(a,{delegateTarget:s}),r.oneOff&&EventHandler.off(n,a.type,e,t),t.apply(s,[a])}}function findHandler(n,e,t=null){return Object.values(n).find(r=>r.callable===e&&r.delegationSelector===t)}function normalizeParameters(n,e,t){const r=typeof e=="string",a=r?t:e||t;let o=getTypeEvent(n);return nativeEvents.has(o)||(o=n),[r,a,o]}function addHandler(n,e,t,r,a){if(typeof e!="string"||!n)return;let[o,s,l]=normalizeParameters(e,t,r);e in customEvents&&(s=(y=>function(E){if(!E.relatedTarget||E.relatedTarget!==E.delegateTarget&&!E.delegateTarget.contains(E.relatedTarget))return y.call(this,E)})(s));const c=getElementEvents(n),f=c[l]||(c[l]={}),d=findHandler(f,s,o?t:null);if(d){d.oneOff=d.oneOff&&a;return}const p=makeEventUid(s,e.replace(namespaceRegex,"")),_=o?bootstrapDelegationHandler(n,t,s):bootstrapHandler(n,s);_.delegationSelector=o?t:null,_.callable=s,_.oneOff=a,_.uidEvent=p,f[p]=_,n.addEventListener(l,_,o)}function removeHandler(n,e,t,r,a){const o=findHandler(e[t],r,a);o&&(n.removeEventListener(t,o,!!a),delete e[t][o.uidEvent])}function removeNamespacedHandlers(n,e,t,r){const a=e[t]||{};for(const[o,s]of Object.entries(a))o.includes(r)&&removeHandler(n,e,t,s.callable,s.delegationSelector)}function getTypeEvent(n){return n=n.replace(stripNameRegex,""),customEvents[n]||n}const EventHandler={on(n,e,t,r){addHandler(n,e,t,r,!1)},one(n,e,t,r){addHandler(n,e,t,r,!0)},off(n,e,t,r){if(typeof e!="string"||!n)return;const[a,o,s]=normalizeParameters(e,t,r),l=s!==e,c=getElementEvents(n),f=c[s]||{},d=e.startsWith(".");if(typeof o<"u"){if(!Object.keys(f).length)return;removeHandler(n,c,s,o,a?t:null);return}if(d)for(const p of Object.keys(c))removeNamespacedHandlers(n,c,p,e.slice(1));for(const[p,_]of Object.entries(f)){const b=p.replace(stripUidRegex,"");(!l||e.includes(b))&&removeHandler(n,c,s,_.callable,_.delegationSelector)}},trigger(n,e,t){if(typeof e!="string"||!n)return null;const r=getjQuery(),a=getTypeEvent(e),o=e!==a;let s=null,l=!0,c=!0,f=!1;o&&r&&(s=r.Event(e,t),r(n).trigger(s),l=!s.isPropagationStopped(),c=!s.isImmediatePropagationStopped(),f=s.isDefaultPrevented());const d=hydrateObj(new Event(e,{bubbles:l,cancelable:!0}),t);return f&&d.preventDefault(),c&&n.dispatchEvent(d),d.defaultPrevented&&s&&s.preventDefault(),d}};function hydrateObj(n,e={}){for(const[t,r]of Object.entries(e))try{n[t]=r}catch{Object.defineProperty(n,t,{configurable:!0,get(){return r}})}return n}function normalizeData(n){if(n==="true")return!0;if(n==="false")return!1;if(n===Number(n).toString())return Number(n);if(n===""||n==="null")return null;if(typeof n!="string")return n;try{return JSON.parse(decodeURIComponent(n))}catch{return n}}function normalizeDataKey(n){return n.replace(/[A-Z]/g,e=>`-${e.toLowerCase()}`)}const Manipulator={setDataAttribute(n,e,t){n.setAttribute(`data-bs-${normalizeDataKey(e)}`,t)},removeDataAttribute(n,e){n.removeAttribute(`data-bs-${normalizeDataKey(e)}`)},getDataAttributes(n){if(!n)return{};const e={},t=Object.keys(n.dataset).filter(r=>r.startsWith("bs")&&!r.startsWith("bsConfig"));for(const r of t){let a=r.replace(/^bs/,"");a=a.charAt(0).toLowerCase()+a.slice(1),e[a]=normalizeData(n.dataset[r])}return e},getDataAttribute(n,e){return normalizeData(n.getAttribute(`data-bs-${normalizeDataKey(e)}`))}};let Config$1=class{static get Default(){return{}}static get DefaultType(){return{}}static get NAME(){throw new Error('You have to implement the static method "NAME", for each component!')}_getConfig(e){return e=this._mergeConfigObj(e),e=this._configAfterMerge(e),this._typeCheckConfig(e),e}_configAfterMerge(e){return e}_mergeConfigObj(e,t){const r=isElement(t)?Manipulator.getDataAttribute(t,"config"):{};return{...this.constructor.Default,...typeof r=="object"?r:{},...isElement(t)?Manipulator.getDataAttributes(t):{},...typeof e=="object"?e:{}}}_typeCheckConfig(e,t=this.constructor.DefaultType){for(const[r,a]of Object.entries(t)){const o=e[r],s=isElement(o)?"element":toType(o);if(!new RegExp(a).test(s))throw new TypeError(`${this.constructor.NAME.toUpperCase()}: Option "${r}" provided type "${s}" but expected type "${a}".`)}}};const VERSION="5.3.8";class BaseComponent extends Config$1{constructor(e,t){super(),e=getElement(e),e&&(this._element=e,this._config=this._getConfig(t),Data.set(this._element,this.constructor.DATA_KEY,this))}dispose(){Data.remove(this._element,this.constructor.DATA_KEY),EventHandler.off(this._element,this.constructor.EVENT_KEY);for(const e of Object.getOwnPropertyNames(this))this[e]=null}_queueCallback(e,t,r=!0){executeAfterTransition(e,t,r)}_getConfig(e){return e=this._mergeConfigObj(e,this._element),e=this._configAfterMerge(e),this._typeCheckConfig(e),e}static getInstance(e){return Data.get(getElement(e),this.DATA_KEY)}static getOrCreateInstance(e,t={}){return this.getInstance(e)||new this(e,typeof t=="object"?t:null)}static get VERSION(){return VERSION}static get DATA_KEY(){return`bs.${this.NAME}`}static get EVENT_KEY(){return`.${this.DATA_KEY}`}static eventName(e){return`${e}${this.EVENT_KEY}`}}const getSelector=n=>{let e=n.getAttribute("data-bs-target");if(!e||e==="#"){let t=n.getAttribute("href");if(!t||!t.includes("#")&&!t.startsWith("."))return null;t.includes("#")&&!t.startsWith("#")&&(t=`#${t.split("#")[1]}`),e=t&&t!=="#"?t.trim():null}return e?e.split(",").map(t=>parseSelector(t)).join(","):null},SelectorEngine={find(n,e=document.documentElement){return[].concat(...Element.prototype.querySelectorAll.call(e,n))},findOne(n,e=document.documentElement){return Element.prototype.querySelector.call(e,n)},children(n,e){return[].concat(...n.children).filter(t=>t.matches(e))},parents(n,e){const t=[];let r=n.parentNode.closest(e);for(;r;)t.push(r),r=r.parentNode.closest(e);return t},prev(n,e){let t=n.previousElementSibling;for(;t;){if(t.matches(e))return[t];t=t.previousElementSibling}return[]},next(n,e){let t=n.nextElementSibling;for(;t;){if(t.matches(e))return[t];t=t.nextElementSibling}return[]},focusableChildren(n){const e=["a","button","input","textarea","select","details","[tabindex]",'[contenteditable="true"]'].map(t=>`${t}:not([tabindex^="-"])`).join(",");return this.find(e,n).filter(t=>!isDisabled(t)&&isVisible(t))},getSelectorFromElement(n){const e=getSelector(n);return e&&SelectorEngine.findOne(e)?e:null},getElementFromSelector(n){const e=getSelector(n);return e?SelectorEngine.findOne(e):null},getMultipleElementsFromSelector(n){const e=getSelector(n);return e?SelectorEngine.find(e):[]}},enableDismissTrigger=(n,e="hide")=>{const t=`click.dismiss${n.EVENT_KEY}`,r=n.NAME;EventHandler.on(document,t,`[data-bs-dismiss="${r}"]`,function(a){if(["A","AREA"].includes(this.tagName)&&a.preventDefault(),isDisabled(this))return;const o=SelectorEngine.getElementFromSelector(this)||this.closest(`.${r}`);n.getOrCreateInstance(o)[e]()})},NAME$f="alert",DATA_KEY$a="bs.alert",EVENT_KEY$b=`.${DATA_KEY$a}`,EVENT_CLOSE=`close${EVENT_KEY$b}`,EVENT_CLOSED=`closed${EVENT_KEY$b}`,CLASS_NAME_FADE$5="fade",CLASS_NAME_SHOW$8="show";class Alert extends BaseComponent{static get NAME(){return NAME$f}close(){if(EventHandler.trigger(this._element,EVENT_CLOSE).defaultPrevented)return;this._element.classList.remove(CLASS_NAME_SHOW$8);const t=this._element.classList.contains(CLASS_NAME_FADE$5);this._queueCallback(()=>this._destroyElement(),this._element,t)}_destroyElement(){this._element.remove(),EventHandler.trigger(this._element,EVENT_CLOSED),this.dispose()}static jQueryInterface(e){return this.each(function(){const t=Alert.getOrCreateInstance(this);if(typeof e=="string"){if(t[e]===void 0||e.startsWith("_")||e==="constructor")throw new TypeError(`No method named "${e}"`);t[e](this)}})}}enableDismissTrigger(Alert,"close");defineJQueryPlugin(Alert);const NAME$e="button",DATA_KEY$9="bs.button",EVENT_KEY$a=`.${DATA_KEY$9}`,DATA_API_KEY$6=".data-api",CLASS_NAME_ACTIVE$3="active",SELECTOR_DATA_TOGGLE$5='[data-bs-toggle="button"]',EVENT_CLICK_DATA_API$6=`click${EVENT_KEY$a}${DATA_API_KEY$6}`;class Button extends BaseComponent{static get NAME(){return NAME$e}toggle(){this._element.setAttribute("aria-pressed",this._element.classList.toggle(CLASS_NAME_ACTIVE$3))}static jQueryInterface(e){return this.each(function(){const t=Button.getOrCreateInstance(this);e==="toggle"&&t[e]()})}}EventHandler.on(document,EVENT_CLICK_DATA_API$6,SELECTOR_DATA_TOGGLE$5,n=>{n.preventDefault();const e=n.target.closest(SELECTOR_DATA_TOGGLE$5);Button.getOrCreateInstance(e).toggle()});defineJQueryPlugin(Button);const NAME$d="swipe",EVENT_KEY$9=".bs.swipe",EVENT_TOUCHSTART=`touchstart${EVENT_KEY$9}`,EVENT_TOUCHMOVE=`touchmove${EVENT_KEY$9}`,EVENT_TOUCHEND=`touchend${EVENT_KEY$9}`,EVENT_POINTERDOWN=`pointerdown${EVENT_KEY$9}`,EVENT_POINTERUP=`pointerup${EVENT_KEY$9}`,POINTER_TYPE_TOUCH="touch",POINTER_TYPE_PEN="pen",CLASS_NAME_POINTER_EVENT="pointer-event",SWIPE_THRESHOLD=40,Default$c={endCallback:null,leftCallback:null,rightCallback:null},DefaultType$c={endCallback:"(function|null)",leftCallback:"(function|null)",rightCallback:"(function|null)"};class Swipe extends Config$1{constructor(e,t){super(),this._element=e,!(!e||!Swipe.isSupported())&&(this._config=this._getConfig(t),this._deltaX=0,this._supportPointerEvents=!!window.PointerEvent,this._initEvents())}static get Default(){return Default$c}static get DefaultType(){return DefaultType$c}static get NAME(){return NAME$d}dispose(){EventHandler.off(this._element,EVENT_KEY$9)}_start(e){if(!this._supportPointerEvents){this._deltaX=e.touches[0].clientX;return}this._eventIsPointerPenTouch(e)&&(this._deltaX=e.clientX)}_end(e){this._eventIsPointerPenTouch(e)&&(this._deltaX=e.clientX-this._deltaX),this._handleSwipe(),execute(this._config.endCallback)}_move(e){this._deltaX=e.touches&&e.touches.length>1?0:e.touches[0].clientX-this._deltaX}_handleSwipe(){const e=Math.abs(this._deltaX);if(e<=SWIPE_THRESHOLD)return;const t=e/this._deltaX;this._deltaX=0,t&&execute(t>0?this._config.rightCallback:this._config.leftCallback)}_initEvents(){this._supportPointerEvents?(EventHandler.on(this._element,EVENT_POINTERDOWN,e=>this._start(e)),EventHandler.on(this._element,EVENT_POINTERUP,e=>this._end(e)),this._element.classList.add(CLASS_NAME_POINTER_EVENT)):(EventHandler.on(this._element,EVENT_TOUCHSTART,e=>this._start(e)),EventHandler.on(this._element,EVENT_TOUCHMOVE,e=>this._move(e)),EventHandler.on(this._element,EVENT_TOUCHEND,e=>this._end(e)))}_eventIsPointerPenTouch(e){return this._supportPointerEvents&&(e.pointerType===POINTER_TYPE_PEN||e.pointerType===POINTER_TYPE_TOUCH)}static isSupported(){return"ontouchstart"in document.documentElement||navigator.maxTouchPoints>0}}const NAME$c="carousel",DATA_KEY$8="bs.carousel",EVENT_KEY$8=`.${DATA_KEY$8}`,DATA_API_KEY$5=".data-api",ARROW_LEFT_KEY$1="ArrowLeft",ARROW_RIGHT_KEY$1="ArrowRight",TOUCHEVENT_COMPAT_WAIT=500,ORDER_NEXT="next",ORDER_PREV="prev",DIRECTION_LEFT="left",DIRECTION_RIGHT="right",EVENT_SLIDE=`slide${EVENT_KEY$8}`,EVENT_SLID=`slid${EVENT_KEY$8}`,EVENT_KEYDOWN$1=`keydown${EVENT_KEY$8}`,EVENT_MOUSEENTER$1=`mouseenter${EVENT_KEY$8}`,EVENT_MOUSELEAVE$1=`mouseleave${EVENT_KEY$8}`,EVENT_DRAG_START=`dragstart${EVENT_KEY$8}`,EVENT_LOAD_DATA_API$3=`load${EVENT_KEY$8}${DATA_API_KEY$5}`,EVENT_CLICK_DATA_API$5=`click${EVENT_KEY$8}${DATA_API_KEY$5}`,CLASS_NAME_CAROUSEL="carousel",CLASS_NAME_ACTIVE$2="active",CLASS_NAME_SLIDE="slide",CLASS_NAME_END="carousel-item-end",CLASS_NAME_START="carousel-item-start",CLASS_NAME_NEXT="carousel-item-next",CLASS_NAME_PREV="carousel-item-prev",SELECTOR_ACTIVE=".active",SELECTOR_ITEM=".carousel-item",SELECTOR_ACTIVE_ITEM=SELECTOR_ACTIVE+SELECTOR_ITEM,SELECTOR_ITEM_IMG=".carousel-item img",SELECTOR_INDICATORS=".carousel-indicators",SELECTOR_DATA_SLIDE="[data-bs-slide], [data-bs-slide-to]",SELECTOR_DATA_RIDE='[data-bs-ride="carousel"]',KEY_TO_DIRECTION={[ARROW_LEFT_KEY$1]:DIRECTION_RIGHT,[ARROW_RIGHT_KEY$1]:DIRECTION_LEFT},Default$b={interval:5e3,keyboard:!0,pause:"hover",ride:!1,touch:!0,wrap:!0},DefaultType$b={interval:"(number|boolean)",keyboard:"boolean",pause:"(string|boolean)",ride:"(boolean|string)",touch:"boolean",wrap:"boolean"};class Carousel extends BaseComponent{constructor(e,t){super(e,t),this._interval=null,this._activeElement=null,this._isSliding=!1,this.touchTimeout=null,this._swipeHelper=null,this._indicatorsElement=SelectorEngine.findOne(SELECTOR_INDICATORS,this._element),this._addEventListeners(),this._config.ride===CLASS_NAME_CAROUSEL&&this.cycle()}static get Default(){return Default$b}static get DefaultType(){return DefaultType$b}static get NAME(){return NAME$c}next(){this._slide(ORDER_NEXT)}nextWhenVisible(){!document.hidden&&isVisible(this._element)&&this.next()}prev(){this._slide(ORDER_PREV)}pause(){this._isSliding&&triggerTransitionEnd(this._element),this._clearInterval()}cycle(){this._clearInterval(),this._updateInterval(),this._interval=setInterval(()=>this.nextWhenVisible(),this._config.interval)}_maybeEnableCycle(){if(this._config.ride){if(this._isSliding){EventHandler.one(this._element,EVENT_SLID,()=>this.cycle());return}this.cycle()}}to(e){const t=this._getItems();if(e>t.length-1||e<0)return;if(this._isSliding){EventHandler.one(this._element,EVENT_SLID,()=>this.to(e));return}const r=this._getItemIndex(this._getActive());if(r===e)return;const a=e>r?ORDER_NEXT:ORDER_PREV;this._slide(a,t[e])}dispose(){this._swipeHelper&&this._swipeHelper.dispose(),super.dispose()}_configAfterMerge(e){return e.defaultInterval=e.interval,e}_addEventListeners(){this._config.keyboard&&EventHandler.on(this._element,EVENT_KEYDOWN$1,e=>this._keydown(e)),this._config.pause==="hover"&&(EventHandler.on(this._element,EVENT_MOUSEENTER$1,()=>this.pause()),EventHandler.on(this._element,EVENT_MOUSELEAVE$1,()=>this._maybeEnableCycle())),this._config.touch&&Swipe.isSupported()&&this._addTouchEventListeners()}_addTouchEventListeners(){for(const r of SelectorEngine.find(SELECTOR_ITEM_IMG,this._element))EventHandler.on(r,EVENT_DRAG_START,a=>a.preventDefault());const t={leftCallback:()=>this._slide(this._directionToOrder(DIRECTION_LEFT)),rightCallback:()=>this._slide(this._directionToOrder(DIRECTION_RIGHT)),endCallback:()=>{this._config.pause==="hover"&&(this.pause(),this.touchTimeout&&clearTimeout(this.touchTimeout),this.touchTimeout=setTimeout(()=>this._maybeEnableCycle(),TOUCHEVENT_COMPAT_WAIT+this._config.interval))}};this._swipeHelper=new Swipe(this._element,t)}_keydown(e){if(/input|textarea/i.test(e.target.tagName))return;const t=KEY_TO_DIRECTION[e.key];t&&(e.preventDefault(),this._slide(this._directionToOrder(t)))}_getItemIndex(e){return this._getItems().indexOf(e)}_setActiveIndicatorElement(e){if(!this._indicatorsElement)return;const t=SelectorEngine.findOne(SELECTOR_ACTIVE,this._indicatorsElement);t.classList.remove(CLASS_NAME_ACTIVE$2),t.removeAttribute("aria-current");const r=SelectorEngine.findOne(`[data-bs-slide-to="${e}"]`,this._indicatorsElement);r&&(r.classList.add(CLASS_NAME_ACTIVE$2),r.setAttribute("aria-current","true"))}_updateInterval(){const e=this._activeElement||this._getActive();if(!e)return;const t=Number.parseInt(e.getAttribute("data-bs-interval"),10);this._config.interval=t||this._config.defaultInterval}_slide(e,t=null){if(this._isSliding)return;const r=this._getActive(),a=e===ORDER_NEXT,o=t||getNextActiveElement(this._getItems(),r,a,this._config.wrap);if(o===r)return;const s=this._getItemIndex(o),l=b=>EventHandler.trigger(this._element,b,{relatedTarget:o,direction:this._orderToDirection(e),from:this._getItemIndex(r),to:s});if(l(EVENT_SLIDE).defaultPrevented||!r||!o)return;const f=!!this._interval;this.pause(),this._isSliding=!0,this._setActiveIndicatorElement(s),this._activeElement=o;const d=a?CLASS_NAME_START:CLASS_NAME_END,p=a?CLASS_NAME_NEXT:CLASS_NAME_PREV;o.classList.add(p),reflow(o),r.classList.add(d),o.classList.add(d);const _=()=>{o.classList.remove(d,p),o.classList.add(CLASS_NAME_ACTIVE$2),r.classList.remove(CLASS_NAME_ACTIVE$2,p,d),this._isSliding=!1,l(EVENT_SLID)};this._queueCallback(_,r,this._isAnimated()),f&&this.cycle()}_isAnimated(){return this._element.classList.contains(CLASS_NAME_SLIDE)}_getActive(){return SelectorEngine.findOne(SELECTOR_ACTIVE_ITEM,this._element)}_getItems(){return SelectorEngine.find(SELECTOR_ITEM,this._element)}_clearInterval(){this._interval&&(clearInterval(this._interval),this._interval=null)}_directionToOrder(e){return isRTL()?e===DIRECTION_LEFT?ORDER_PREV:ORDER_NEXT:e===DIRECTION_LEFT?ORDER_NEXT:ORDER_PREV}_orderToDirection(e){return isRTL()?e===ORDER_PREV?DIRECTION_LEFT:DIRECTION_RIGHT:e===ORDER_PREV?DIRECTION_RIGHT:DIRECTION_LEFT}static jQueryInterface(e){return this.each(function(){const t=Carousel.getOrCreateInstance(this,e);if(typeof e=="number"){t.to(e);return}if(typeof e=="string"){if(t[e]===void 0||e.startsWith("_")||e==="constructor")throw new TypeError(`No method named "${e}"`);t[e]()}})}}EventHandler.on(document,EVENT_CLICK_DATA_API$5,SELECTOR_DATA_SLIDE,function(n){const e=SelectorEngine.getElementFromSelector(this);if(!e||!e.classList.contains(CLASS_NAME_CAROUSEL))return;n.preventDefault();const t=Carousel.getOrCreateInstance(e),r=this.getAttribute("data-bs-slide-to");if(r){t.to(r),t._maybeEnableCycle();return}if(Manipulator.getDataAttribute(this,"slide")==="next"){t.next(),t._maybeEnableCycle();return}t.prev(),t._maybeEnableCycle()});EventHandler.on(window,EVENT_LOAD_DATA_API$3,()=>{const n=SelectorEngine.find(SELECTOR_DATA_RIDE);for(const e of n)Carousel.getOrCreateInstance(e)});defineJQueryPlugin(Carousel);const NAME$b="collapse",DATA_KEY$7="bs.collapse",EVENT_KEY$7=`.${DATA_KEY$7}`,DATA_API_KEY$4=".data-api",EVENT_SHOW$6=`show${EVENT_KEY$7}`,EVENT_SHOWN$6=`shown${EVENT_KEY$7}`,EVENT_HIDE$6=`hide${EVENT_KEY$7}`,EVENT_HIDDEN$6=`hidden${EVENT_KEY$7}`,EVENT_CLICK_DATA_API$4=`click${EVENT_KEY$7}${DATA_API_KEY$4}`,CLASS_NAME_SHOW$7="show",CLASS_NAME_COLLAPSE="collapse",CLASS_NAME_COLLAPSING="collapsing",CLASS_NAME_COLLAPSED="collapsed",CLASS_NAME_DEEPER_CHILDREN=`:scope .${CLASS_NAME_COLLAPSE} .${CLASS_NAME_COLLAPSE}`,CLASS_NAME_HORIZONTAL="collapse-horizontal",WIDTH="width",HEIGHT="height",SELECTOR_ACTIVES=".collapse.show, .collapse.collapsing",SELECTOR_DATA_TOGGLE$4='[data-bs-toggle="collapse"]',Default$a={parent:null,toggle:!0},DefaultType$a={parent:"(null|element)",toggle:"boolean"};class Collapse extends BaseComponent{constructor(e,t){super(e,t),this._isTransitioning=!1,this._triggerArray=[];const r=SelectorEngine.find(SELECTOR_DATA_TOGGLE$4);for(const a of r){const o=SelectorEngine.getSelectorFromElement(a),s=SelectorEngine.find(o).filter(l=>l===this._element);o!==null&&s.length&&this._triggerArray.push(a)}this._initializeChildren(),this._config.parent||this._addAriaAndCollapsedClass(this._triggerArray,this._isShown()),this._config.toggle&&this.toggle()}static get Default(){return Default$a}static get DefaultType(){return DefaultType$a}static get NAME(){return NAME$b}toggle(){this._isShown()?this.hide():this.show()}show(){if(this._isTransitioning||this._isShown())return;let e=[];if(this._config.parent&&(e=this._getFirstLevelChildren(SELECTOR_ACTIVES).filter(l=>l!==this._element).map(l=>Collapse.getOrCreateInstance(l,{toggle:!1}))),e.length&&e[0]._isTransitioning||EventHandler.trigger(this._element,EVENT_SHOW$6).defaultPrevented)return;for(const l of e)l.hide();const r=this._getDimension();this._element.classList.remove(CLASS_NAME_COLLAPSE),this._element.classList.add(CLASS_NAME_COLLAPSING),this._element.style[r]=0,this._addAriaAndCollapsedClass(this._triggerArray,!0),this._isTransitioning=!0;const a=()=>{this._isTransitioning=!1,this._element.classList.remove(CLASS_NAME_COLLAPSING),this._element.classList.add(CLASS_NAME_COLLAPSE,CLASS_NAME_SHOW$7),this._element.style[r]="",EventHandler.trigger(this._element,EVENT_SHOWN$6)},s=`scroll${r[0].toUpperCase()+r.slice(1)}`;this._queueCallback(a,this._element,!0),this._element.style[r]=`${this._element[s]}px`}hide(){if(this._isTransitioning||!this._isShown()||EventHandler.trigger(this._element,EVENT_HIDE$6).defaultPrevented)return;const t=this._getDimension();this._element.style[t]=`${this._element.getBoundingClientRect()[t]}px`,reflow(this._element),this._element.classList.add(CLASS_NAME_COLLAPSING),this._element.classList.remove(CLASS_NAME_COLLAPSE,CLASS_NAME_SHOW$7);for(const a of this._triggerArray){const o=SelectorEngine.getElementFromSelector(a);o&&!this._isShown(o)&&this._addAriaAndCollapsedClass([a],!1)}this._isTransitioning=!0;const r=()=>{this._isTransitioning=!1,this._element.classList.remove(CLASS_NAME_COLLAPSING),this._element.classList.add(CLASS_NAME_COLLAPSE),EventHandler.trigger(this._element,EVENT_HIDDEN$6)};this._element.style[t]="",this._queueCallback(r,this._element,!0)}_isShown(e=this._element){return e.classList.contains(CLASS_NAME_SHOW$7)}_configAfterMerge(e){return e.toggle=!!e.toggle,e.parent=getElement(e.parent),e}_getDimension(){return this._element.classList.contains(CLASS_NAME_HORIZONTAL)?WIDTH:HEIGHT}_initializeChildren(){if(!this._config.parent)return;const e=this._getFirstLevelChildren(SELECTOR_DATA_TOGGLE$4);for(const t of e){const r=SelectorEngine.getElementFromSelector(t);r&&this._addAriaAndCollapsedClass([t],this._isShown(r))}}_getFirstLevelChildren(e){const t=SelectorEngine.find(CLASS_NAME_DEEPER_CHILDREN,this._config.parent);return SelectorEngine.find(e,this._config.parent).filter(r=>!t.includes(r))}_addAriaAndCollapsedClass(e,t){if(e.length)for(const r of e)r.classList.toggle(CLASS_NAME_COLLAPSED,!t),r.setAttribute("aria-expanded",t)}static jQueryInterface(e){const t={};return typeof e=="string"&&/show|hide/.test(e)&&(t.toggle=!1),this.each(function(){const r=Collapse.getOrCreateInstance(this,t);if(typeof e=="string"){if(typeof r[e]>"u")throw new TypeError(`No method named "${e}"`);r[e]()}})}}EventHandler.on(document,EVENT_CLICK_DATA_API$4,SELECTOR_DATA_TOGGLE$4,function(n){(n.target.tagName==="A"||n.delegateTarget&&n.delegateTarget.tagName==="A")&&n.preventDefault();for(const e of SelectorEngine.getMultipleElementsFromSelector(this))Collapse.getOrCreateInstance(e,{toggle:!1}).toggle()});defineJQueryPlugin(Collapse);const NAME$a="dropdown",DATA_KEY$6="bs.dropdown",EVENT_KEY$6=`.${DATA_KEY$6}`,DATA_API_KEY$3=".data-api",ESCAPE_KEY$2="Escape",TAB_KEY$1="Tab",ARROW_UP_KEY$1="ArrowUp",ARROW_DOWN_KEY$1="ArrowDown",RIGHT_MOUSE_BUTTON=2,EVENT_HIDE$5=`hide${EVENT_KEY$6}`,EVENT_HIDDEN$5=`hidden${EVENT_KEY$6}`,EVENT_SHOW$5=`show${EVENT_KEY$6}`,EVENT_SHOWN$5=`shown${EVENT_KEY$6}`,EVENT_CLICK_DATA_API$3=`click${EVENT_KEY$6}${DATA_API_KEY$3}`,EVENT_KEYDOWN_DATA_API=`keydown${EVENT_KEY$6}${DATA_API_KEY$3}`,EVENT_KEYUP_DATA_API=`keyup${EVENT_KEY$6}${DATA_API_KEY$3}`,CLASS_NAME_SHOW$6="show",CLASS_NAME_DROPUP="dropup",CLASS_NAME_DROPEND="dropend",CLASS_NAME_DROPSTART="dropstart",CLASS_NAME_DROPUP_CENTER="dropup-center",CLASS_NAME_DROPDOWN_CENTER="dropdown-center",SELECTOR_DATA_TOGGLE$3='[data-bs-toggle="dropdown"]:not(.disabled):not(:disabled)',SELECTOR_DATA_TOGGLE_SHOWN=`${SELECTOR_DATA_TOGGLE$3}.${CLASS_NAME_SHOW$6}`,SELECTOR_MENU=".dropdown-menu",SELECTOR_NAVBAR=".navbar",SELECTOR_NAVBAR_NAV=".navbar-nav",SELECTOR_VISIBLE_ITEMS=".dropdown-menu .dropdown-item:not(.disabled):not(:disabled)",PLACEMENT_TOP=isRTL()?"top-end":"top-start",PLACEMENT_TOPEND=isRTL()?"top-start":"top-end",PLACEMENT_BOTTOM=isRTL()?"bottom-end":"bottom-start",PLACEMENT_BOTTOMEND=isRTL()?"bottom-start":"bottom-end",PLACEMENT_RIGHT=isRTL()?"left-start":"right-start",PLACEMENT_LEFT=isRTL()?"right-start":"left-start",PLACEMENT_TOPCENTER="top",PLACEMENT_BOTTOMCENTER="bottom",Default$9={autoClose:!0,boundary:"clippingParents",display:"dynamic",offset:[0,2],popperConfig:null,reference:"toggle"},DefaultType$9={autoClose:"(boolean|string)",boundary:"(string|element)",display:"string",offset:"(array|string|function)",popperConfig:"(null|object|function)",reference:"(string|element|object)"};class Dropdown extends BaseComponent{constructor(e,t){super(e,t),this._popper=null,this._parent=this._element.parentNode,this._menu=SelectorEngine.next(this._element,SELECTOR_MENU)[0]||SelectorEngine.prev(this._element,SELECTOR_MENU)[0]||SelectorEngine.findOne(SELECTOR_MENU,this._parent),this._inNavbar=this._detectNavbar()}static get Default(){return Default$9}static get DefaultType(){return DefaultType$9}static get NAME(){return NAME$a}toggle(){return this._isShown()?this.hide():this.show()}show(){if(isDisabled(this._element)||this._isShown())return;const e={relatedTarget:this._element};if(!EventHandler.trigger(this._element,EVENT_SHOW$5,e).defaultPrevented){if(this._createPopper(),"ontouchstart"in document.documentElement&&!this._parent.closest(SELECTOR_NAVBAR_NAV))for(const r of[].concat(...document.body.children))EventHandler.on(r,"mouseover",noop$1);this._element.focus(),this._element.setAttribute("aria-expanded",!0),this._menu.classList.add(CLASS_NAME_SHOW$6),this._element.classList.add(CLASS_NAME_SHOW$6),EventHandler.trigger(this._element,EVENT_SHOWN$5,e)}}hide(){if(isDisabled(this._element)||!this._isShown())return;const e={relatedTarget:this._element};this._completeHide(e)}dispose(){this._popper&&this._popper.destroy(),super.dispose()}update(){this._inNavbar=this._detectNavbar(),this._popper&&this._popper.update()}_completeHide(e){if(!EventHandler.trigger(this._element,EVENT_HIDE$5,e).defaultPrevented){if("ontouchstart"in document.documentElement)for(const r of[].concat(...document.body.children))EventHandler.off(r,"mouseover",noop$1);this._popper&&this._popper.destroy(),this._menu.classList.remove(CLASS_NAME_SHOW$6),this._element.classList.remove(CLASS_NAME_SHOW$6),this._element.setAttribute("aria-expanded","false"),Manipulator.removeDataAttribute(this._menu,"popper"),EventHandler.trigger(this._element,EVENT_HIDDEN$5,e)}}_getConfig(e){if(e=super._getConfig(e),typeof e.reference=="object"&&!isElement(e.reference)&&typeof e.reference.getBoundingClientRect!="function")throw new TypeError(`${NAME$a.toUpperCase()}: Option "reference" provided type "object" without a required "getBoundingClientRect" method.`);return e}_createPopper(){if(typeof Popper>"u")throw new TypeError("Bootstrap's dropdowns require Popper (https://popper.js.org/docs/v2/)");let e=this._element;this._config.reference==="parent"?e=this._parent:isElement(this._config.reference)?e=getElement(this._config.reference):typeof this._config.reference=="object"&&(e=this._config.reference);const t=this._getPopperConfig();this._popper=createPopper(e,this._menu,t)}_isShown(){return this._menu.classList.contains(CLASS_NAME_SHOW$6)}_getPlacement(){const e=this._parent;if(e.classList.contains(CLASS_NAME_DROPEND))return PLACEMENT_RIGHT;if(e.classList.contains(CLASS_NAME_DROPSTART))return PLACEMENT_LEFT;if(e.classList.contains(CLASS_NAME_DROPUP_CENTER))return PLACEMENT_TOPCENTER;if(e.classList.contains(CLASS_NAME_DROPDOWN_CENTER))return PLACEMENT_BOTTOMCENTER;const t=getComputedStyle(this._menu).getPropertyValue("--bs-position").trim()==="end";return e.classList.contains(CLASS_NAME_DROPUP)?t?PLACEMENT_TOPEND:PLACEMENT_TOP:t?PLACEMENT_BOTTOMEND:PLACEMENT_BOTTOM}_detectNavbar(){return this._element.closest(SELECTOR_NAVBAR)!==null}_getOffset(){const{offset:e}=this._config;return typeof e=="string"?e.split(",").map(t=>Number.parseInt(t,10)):typeof e=="function"?t=>e(t,this._element):e}_getPopperConfig(){const e={placement:this._getPlacement(),modifiers:[{name:"preventOverflow",options:{boundary:this._config.boundary}},{name:"offset",options:{offset:this._getOffset()}}]};return(this._inNavbar||this._config.display==="static")&&(Manipulator.setDataAttribute(this._menu,"popper","static"),e.modifiers=[{name:"applyStyles",enabled:!1}]),{...e,...execute(this._config.popperConfig,[void 0,e])}}_selectMenuItem({key:e,target:t}){const r=SelectorEngine.find(SELECTOR_VISIBLE_ITEMS,this._menu).filter(a=>isVisible(a));r.length&&getNextActiveElement(r,t,e===ARROW_DOWN_KEY$1,!r.includes(t)).focus()}static jQueryInterface(e){return this.each(function(){const t=Dropdown.getOrCreateInstance(this,e);if(typeof e=="string"){if(typeof t[e]>"u")throw new TypeError(`No method named "${e}"`);t[e]()}})}static clearMenus(e){if(e.button===RIGHT_MOUSE_BUTTON||e.type==="keyup"&&e.key!==TAB_KEY$1)return;const t=SelectorEngine.find(SELECTOR_DATA_TOGGLE_SHOWN);for(const r of t){const a=Dropdown.getInstance(r);if(!a||a._config.autoClose===!1)continue;const o=e.composedPath(),s=o.includes(a._menu);if(o.includes(a._element)||a._config.autoClose==="inside"&&!s||a._config.autoClose==="outside"&&s||a._menu.contains(e.target)&&(e.type==="keyup"&&e.key===TAB_KEY$1||/input|select|option|textarea|form/i.test(e.target.tagName)))continue;const l={relatedTarget:a._element};e.type==="click"&&(l.clickEvent=e),a._completeHide(l)}}static dataApiKeydownHandler(e){const t=/input|textarea/i.test(e.target.tagName),r=e.key===ESCAPE_KEY$2,a=[ARROW_UP_KEY$1,ARROW_DOWN_KEY$1].includes(e.key);if(!a&&!r||t&&!r)return;e.preventDefault();const o=this.matches(SELECTOR_DATA_TOGGLE$3)?this:SelectorEngine.prev(this,SELECTOR_DATA_TOGGLE$3)[0]||SelectorEngine.next(this,SELECTOR_DATA_TOGGLE$3)[0]||SelectorEngine.findOne(SELECTOR_DATA_TOGGLE$3,e.delegateTarget.parentNode),s=Dropdown.getOrCreateInstance(o);if(a){e.stopPropagation(),s.show(),s._selectMenuItem(e);return}s._isShown()&&(e.stopPropagation(),s.hide(),o.focus())}}EventHandler.on(document,EVENT_KEYDOWN_DATA_API,SELECTOR_DATA_TOGGLE$3,Dropdown.dataApiKeydownHandler);EventHandler.on(document,EVENT_KEYDOWN_DATA_API,SELECTOR_MENU,Dropdown.dataApiKeydownHandler);EventHandler.on(document,EVENT_CLICK_DATA_API$3,Dropdown.clearMenus);EventHandler.on(document,EVENT_KEYUP_DATA_API,Dropdown.clearMenus);EventHandler.on(document,EVENT_CLICK_DATA_API$3,SELECTOR_DATA_TOGGLE$3,function(n){n.preventDefault(),Dropdown.getOrCreateInstance(this).toggle()});defineJQueryPlugin(Dropdown);const NAME$9="backdrop",CLASS_NAME_FADE$4="fade",CLASS_NAME_SHOW$5="show",EVENT_MOUSEDOWN=`mousedown.bs.${NAME$9}`,Default$8={className:"modal-backdrop",clickCallback:null,isAnimated:!1,isVisible:!0,rootElement:"body"},DefaultType$8={className:"string",clickCallback:"(function|null)",isAnimated:"boolean",isVisible:"boolean",rootElement:"(element|string)"};class Backdrop extends Config$1{constructor(e){super(),this._config=this._getConfig(e),this._isAppended=!1,this._element=null}static get Default(){return Default$8}static get DefaultType(){return DefaultType$8}static get NAME(){return NAME$9}show(e){if(!this._config.isVisible){execute(e);return}this._append();const t=this._getElement();this._config.isAnimated&&reflow(t),t.classList.add(CLASS_NAME_SHOW$5),this._emulateAnimation(()=>{execute(e)})}hide(e){if(!this._config.isVisible){execute(e);return}this._getElement().classList.remove(CLASS_NAME_SHOW$5),this._emulateAnimation(()=>{this.dispose(),execute(e)})}dispose(){this._isAppended&&(EventHandler.off(this._element,EVENT_MOUSEDOWN),this._element.remove(),this._isAppended=!1)}_getElement(){if(!this._element){const e=document.createElement("div");e.className=this._config.className,this._config.isAnimated&&e.classList.add(CLASS_NAME_FADE$4),this._element=e}return this._element}_configAfterMerge(e){return e.rootElement=getElement(e.rootElement),e}_append(){if(this._isAppended)return;const e=this._getElement();this._config.rootElement.append(e),EventHandler.on(e,EVENT_MOUSEDOWN,()=>{execute(this._config.clickCallback)}),this._isAppended=!0}_emulateAnimation(e){executeAfterTransition(e,this._getElement(),this._config.isAnimated)}}const NAME$8="focustrap",DATA_KEY$5="bs.focustrap",EVENT_KEY$5=`.${DATA_KEY$5}`,EVENT_FOCUSIN$2=`focusin${EVENT_KEY$5}`,EVENT_KEYDOWN_TAB=`keydown.tab${EVENT_KEY$5}`,TAB_KEY="Tab",TAB_NAV_FORWARD="forward",TAB_NAV_BACKWARD="backward",Default$7={autofocus:!0,trapElement:null},DefaultType$7={autofocus:"boolean",trapElement:"element"};class FocusTrap extends Config$1{constructor(e){super(),this._config=this._getConfig(e),this._isActive=!1,this._lastTabNavDirection=null}static get Default(){return Default$7}static get DefaultType(){return DefaultType$7}static get NAME(){return NAME$8}activate(){this._isActive||(this._config.autofocus&&this._config.trapElement.focus(),EventHandler.off(document,EVENT_KEY$5),EventHandler.on(document,EVENT_FOCUSIN$2,e=>this._handleFocusin(e)),EventHandler.on(document,EVENT_KEYDOWN_TAB,e=>this._handleKeydown(e)),this._isActive=!0)}deactivate(){this._isActive&&(this._isActive=!1,EventHandler.off(document,EVENT_KEY$5))}_handleFocusin(e){const{trapElement:t}=this._config;if(e.target===document||e.target===t||t.contains(e.target))return;const r=SelectorEngine.focusableChildren(t);r.length===0?t.focus():this._lastTabNavDirection===TAB_NAV_BACKWARD?r[r.length-1].focus():r[0].focus()}_handleKeydown(e){e.key===TAB_KEY&&(this._lastTabNavDirection=e.shiftKey?TAB_NAV_BACKWARD:TAB_NAV_FORWARD)}}const SELECTOR_FIXED_CONTENT=".fixed-top, .fixed-bottom, .is-fixed, .sticky-top",SELECTOR_STICKY_CONTENT=".sticky-top",PROPERTY_PADDING="padding-right",PROPERTY_MARGIN="margin-right";class ScrollBarHelper{constructor(){this._element=document.body}getWidth(){const e=document.documentElement.clientWidth;return Math.abs(window.innerWidth-e)}hide(){const e=this.getWidth();this._disableOverFlow(),this._setElementAttributes(this._element,PROPERTY_PADDING,t=>t+e),this._setElementAttributes(SELECTOR_FIXED_CONTENT,PROPERTY_PADDING,t=>t+e),this._setElementAttributes(SELECTOR_STICKY_CONTENT,PROPERTY_MARGIN,t=>t-e)}reset(){this._resetElementAttributes(this._element,"overflow"),this._resetElementAttributes(this._element,PROPERTY_PADDING),this._resetElementAttributes(SELECTOR_FIXED_CONTENT,PROPERTY_PADDING),this._resetElementAttributes(SELECTOR_STICKY_CONTENT,PROPERTY_MARGIN)}isOverflowing(){return this.getWidth()>0}_disableOverFlow(){this._saveInitialAttribute(this._element,"overflow"),this._element.style.overflow="hidden"}_setElementAttributes(e,t,r){const a=this.getWidth(),o=s=>{if(s!==this._element&&window.innerWidth>s.clientWidth+a)return;this._saveInitialAttribute(s,t);const l=window.getComputedStyle(s).getPropertyValue(t);s.style.setProperty(t,`${r(Number.parseFloat(l))}px`)};this._applyManipulationCallback(e,o)}_saveInitialAttribute(e,t){const r=e.style.getPropertyValue(t);r&&Manipulator.setDataAttribute(e,t,r)}_resetElementAttributes(e,t){const r=a=>{const o=Manipulator.getDataAttribute(a,t);if(o===null){a.style.removeProperty(t);return}Manipulator.removeDataAttribute(a,t),a.style.setProperty(t,o)};this._applyManipulationCallback(e,r)}_applyManipulationCallback(e,t){if(isElement(e)){t(e);return}for(const r of SelectorEngine.find(e,this._element))t(r)}}const NAME$7="modal",DATA_KEY$4="bs.modal",EVENT_KEY$4=`.${DATA_KEY$4}`,DATA_API_KEY$2=".data-api",ESCAPE_KEY$1="Escape",EVENT_HIDE$4=`hide${EVENT_KEY$4}`,EVENT_HIDE_PREVENTED$1=`hidePrevented${EVENT_KEY$4}`,EVENT_HIDDEN$4=`hidden${EVENT_KEY$4}`,EVENT_SHOW$4=`show${EVENT_KEY$4}`,EVENT_SHOWN$4=`shown${EVENT_KEY$4}`,EVENT_RESIZE$1=`resize${EVENT_KEY$4}`,EVENT_CLICK_DISMISS=`click.dismiss${EVENT_KEY$4}`,EVENT_MOUSEDOWN_DISMISS=`mousedown.dismiss${EVENT_KEY$4}`,EVENT_KEYDOWN_DISMISS$1=`keydown.dismiss${EVENT_KEY$4}`,EVENT_CLICK_DATA_API$2=`click${EVENT_KEY$4}${DATA_API_KEY$2}`,CLASS_NAME_OPEN="modal-open",CLASS_NAME_FADE$3="fade",CLASS_NAME_SHOW$4="show",CLASS_NAME_STATIC="modal-static",OPEN_SELECTOR$1=".modal.show",SELECTOR_DIALOG=".modal-dialog",SELECTOR_MODAL_BODY=".modal-body",SELECTOR_DATA_TOGGLE$2='[data-bs-toggle="modal"]',Default$6={backdrop:!0,focus:!0,keyboard:!0},DefaultType$6={backdrop:"(boolean|string)",focus:"boolean",keyboard:"boolean"};class Modal extends BaseComponent{constructor(e,t){super(e,t),this._dialog=SelectorEngine.findOne(SELECTOR_DIALOG,this._element),this._backdrop=this._initializeBackDrop(),this._focustrap=this._initializeFocusTrap(),this._isShown=!1,this._isTransitioning=!1,this._scrollBar=new ScrollBarHelper,this._addEventListeners()}static get Default(){return Default$6}static get DefaultType(){return DefaultType$6}static get NAME(){return NAME$7}toggle(e){return this._isShown?this.hide():this.show(e)}show(e){this._isShown||this._isTransitioning||EventHandler.trigger(this._element,EVENT_SHOW$4,{relatedTarget:e}).defaultPrevented||(this._isShown=!0,this._isTransitioning=!0,this._scrollBar.hide(),document.body.classList.add(CLASS_NAME_OPEN),this._adjustDialog(),this._backdrop.show(()=>this._showElement(e)))}hide(){!this._isShown||this._isTransitioning||EventHandler.trigger(this._element,EVENT_HIDE$4).defaultPrevented||(this._isShown=!1,this._isTransitioning=!0,this._focustrap.deactivate(),this._element.classList.remove(CLASS_NAME_SHOW$4),this._queueCallback(()=>this._hideModal(),this._element,this._isAnimated()))}dispose(){EventHandler.off(window,EVENT_KEY$4),EventHandler.off(this._dialog,EVENT_KEY$4),this._backdrop.dispose(),this._focustrap.deactivate(),super.dispose()}handleUpdate(){this._adjustDialog()}_initializeBackDrop(){return new Backdrop({isVisible:!!this._config.backdrop,isAnimated:this._isAnimated()})}_initializeFocusTrap(){return new FocusTrap({trapElement:this._element})}_showElement(e){document.body.contains(this._element)||document.body.append(this._element),this._element.style.display="block",this._element.removeAttribute("aria-hidden"),this._element.setAttribute("aria-modal",!0),this._element.setAttribute("role","dialog"),this._element.scrollTop=0;const t=SelectorEngine.findOne(SELECTOR_MODAL_BODY,this._dialog);t&&(t.scrollTop=0),reflow(this._element),this._element.classList.add(CLASS_NAME_SHOW$4);const r=()=>{this._config.focus&&this._focustrap.activate(),this._isTransitioning=!1,EventHandler.trigger(this._element,EVENT_SHOWN$4,{relatedTarget:e})};this._queueCallback(r,this._dialog,this._isAnimated())}_addEventListeners(){EventHandler.on(this._element,EVENT_KEYDOWN_DISMISS$1,e=>{if(e.key===ESCAPE_KEY$1){if(this._config.keyboard){this.hide();return}this._triggerBackdropTransition()}}),EventHandler.on(window,EVENT_RESIZE$1,()=>{this._isShown&&!this._isTransitioning&&this._adjustDialog()}),EventHandler.on(this._element,EVENT_MOUSEDOWN_DISMISS,e=>{EventHandler.one(this._element,EVENT_CLICK_DISMISS,t=>{if(!(this._element!==e.target||this._element!==t.target)){if(this._config.backdrop==="static"){this._triggerBackdropTransition();return}this._config.backdrop&&this.hide()}})})}_hideModal(){this._element.style.display="none",this._element.setAttribute("aria-hidden",!0),this._element.removeAttribute("aria-modal"),this._element.removeAttribute("role"),this._isTransitioning=!1,this._backdrop.hide(()=>{document.body.classList.remove(CLASS_NAME_OPEN),this._resetAdjustments(),this._scrollBar.reset(),EventHandler.trigger(this._element,EVENT_HIDDEN$4)})}_isAnimated(){return this._element.classList.contains(CLASS_NAME_FADE$3)}_triggerBackdropTransition(){if(EventHandler.trigger(this._element,EVENT_HIDE_PREVENTED$1).defaultPrevented)return;const t=this._element.scrollHeight>document.documentElement.clientHeight,r=this._element.style.overflowY;r==="hidden"||this._element.classList.contains(CLASS_NAME_STATIC)||(t||(this._element.style.overflowY="hidden"),this._element.classList.add(CLASS_NAME_STATIC),this._queueCallback(()=>{this._element.classList.remove(CLASS_NAME_STATIC),this._queueCallback(()=>{this._element.style.overflowY=r},this._dialog)},this._dialog),this._element.focus())}_adjustDialog(){const e=this._element.scrollHeight>document.documentElement.clientHeight,t=this._scrollBar.getWidth(),r=t>0;if(r&&!e){const a=isRTL()?"paddingLeft":"paddingRight";this._element.style[a]=`${t}px`}if(!r&&e){const a=isRTL()?"paddingRight":"paddingLeft";this._element.style[a]=`${t}px`}}_resetAdjustments(){this._element.style.paddingLeft="",this._element.style.paddingRight=""}static jQueryInterface(e,t){return this.each(function(){const r=Modal.getOrCreateInstance(this,e);if(typeof e=="string"){if(typeof r[e]>"u")throw new TypeError(`No method named "${e}"`);r[e](t)}})}}EventHandler.on(document,EVENT_CLICK_DATA_API$2,SELECTOR_DATA_TOGGLE$2,function(n){const e=SelectorEngine.getElementFromSelector(this);["A","AREA"].includes(this.tagName)&&n.preventDefault(),EventHandler.one(e,EVENT_SHOW$4,a=>{a.defaultPrevented||EventHandler.one(e,EVENT_HIDDEN$4,()=>{isVisible(this)&&this.focus()})});const t=SelectorEngine.findOne(OPEN_SELECTOR$1);t&&Modal.getInstance(t).hide(),Modal.getOrCreateInstance(e).toggle(this)});enableDismissTrigger(Modal);defineJQueryPlugin(Modal);const NAME$6="offcanvas",DATA_KEY$3="bs.offcanvas",EVENT_KEY$3=`.${DATA_KEY$3}`,DATA_API_KEY$1=".data-api",EVENT_LOAD_DATA_API$2=`load${EVENT_KEY$3}${DATA_API_KEY$1}`,ESCAPE_KEY="Escape",CLASS_NAME_SHOW$3="show",CLASS_NAME_SHOWING$1="showing",CLASS_NAME_HIDING="hiding",CLASS_NAME_BACKDROP="offcanvas-backdrop",OPEN_SELECTOR=".offcanvas.show",EVENT_SHOW$3=`show${EVENT_KEY$3}`,EVENT_SHOWN$3=`shown${EVENT_KEY$3}`,EVENT_HIDE$3=`hide${EVENT_KEY$3}`,EVENT_HIDE_PREVENTED=`hidePrevented${EVENT_KEY$3}`,EVENT_HIDDEN$3=`hidden${EVENT_KEY$3}`,EVENT_RESIZE=`resize${EVENT_KEY$3}`,EVENT_CLICK_DATA_API$1=`click${EVENT_KEY$3}${DATA_API_KEY$1}`,EVENT_KEYDOWN_DISMISS=`keydown.dismiss${EVENT_KEY$3}`,SELECTOR_DATA_TOGGLE$1='[data-bs-toggle="offcanvas"]',Default$5={backdrop:!0,keyboard:!0,scroll:!1},DefaultType$5={backdrop:"(boolean|string)",keyboard:"boolean",scroll:"boolean"};class Offcanvas extends BaseComponent{constructor(e,t){super(e,t),this._isShown=!1,this._backdrop=this._initializeBackDrop(),this._focustrap=this._initializeFocusTrap(),this._addEventListeners()}static get Default(){return Default$5}static get DefaultType(){return DefaultType$5}static get NAME(){return NAME$6}toggle(e){return this._isShown?this.hide():this.show(e)}show(e){if(this._isShown||EventHandler.trigger(this._element,EVENT_SHOW$3,{relatedTarget:e}).defaultPrevented)return;this._isShown=!0,this._backdrop.show(),this._config.scroll||new ScrollBarHelper().hide(),this._element.setAttribute("aria-modal",!0),this._element.setAttribute("role","dialog"),this._element.classList.add(CLASS_NAME_SHOWING$1);const r=()=>{(!this._config.scroll||this._config.backdrop)&&this._focustrap.activate(),this._element.classList.add(CLASS_NAME_SHOW$3),this._element.classList.remove(CLASS_NAME_SHOWING$1),EventHandler.trigger(this._element,EVENT_SHOWN$3,{relatedTarget:e})};this._queueCallback(r,this._element,!0)}hide(){if(!this._isShown||EventHandler.trigger(this._element,EVENT_HIDE$3).defaultPrevented)return;this._focustrap.deactivate(),this._element.blur(),this._isShown=!1,this._element.classList.add(CLASS_NAME_HIDING),this._backdrop.hide();const t=()=>{this._element.classList.remove(CLASS_NAME_SHOW$3,CLASS_NAME_HIDING),this._element.removeAttribute("aria-modal"),this._element.removeAttribute("role"),this._config.scroll||new ScrollBarHelper().reset(),EventHandler.trigger(this._element,EVENT_HIDDEN$3)};this._queueCallback(t,this._element,!0)}dispose(){this._backdrop.dispose(),this._focustrap.deactivate(),super.dispose()}_initializeBackDrop(){const e=()=>{if(this._config.backdrop==="static"){EventHandler.trigger(this._element,EVENT_HIDE_PREVENTED);return}this.hide()},t=!!this._config.backdrop;return new Backdrop({className:CLASS_NAME_BACKDROP,isVisible:t,isAnimated:!0,rootElement:this._element.parentNode,clickCallback:t?e:null})}_initializeFocusTrap(){return new FocusTrap({trapElement:this._element})}_addEventListeners(){EventHandler.on(this._element,EVENT_KEYDOWN_DISMISS,e=>{if(e.key===ESCAPE_KEY){if(this._config.keyboard){this.hide();return}EventHandler.trigger(this._element,EVENT_HIDE_PREVENTED)}})}static jQueryInterface(e){return this.each(function(){const t=Offcanvas.getOrCreateInstance(this,e);if(typeof e=="string"){if(t[e]===void 0||e.startsWith("_")||e==="constructor")throw new TypeError(`No method named "${e}"`);t[e](this)}})}}EventHandler.on(document,EVENT_CLICK_DATA_API$1,SELECTOR_DATA_TOGGLE$1,function(n){const e=SelectorEngine.getElementFromSelector(this);if(["A","AREA"].includes(this.tagName)&&n.preventDefault(),isDisabled(this))return;EventHandler.one(e,EVENT_HIDDEN$3,()=>{isVisible(this)&&this.focus()});const t=SelectorEngine.findOne(OPEN_SELECTOR);t&&t!==e&&Offcanvas.getInstance(t).hide(),Offcanvas.getOrCreateInstance(e).toggle(this)});EventHandler.on(window,EVENT_LOAD_DATA_API$2,()=>{for(const n of SelectorEngine.find(OPEN_SELECTOR))Offcanvas.getOrCreateInstance(n).show()});EventHandler.on(window,EVENT_RESIZE,()=>{for(const n of SelectorEngine.find("[aria-modal][class*=show][class*=offcanvas-]"))getComputedStyle(n).position!=="fixed"&&Offcanvas.getOrCreateInstance(n).hide()});enableDismissTrigger(Offcanvas);defineJQueryPlugin(Offcanvas);const ARIA_ATTRIBUTE_PATTERN=/^aria-[\w-]*$/i,DefaultAllowlist={"*":["class","dir","id","lang","role",ARIA_ATTRIBUTE_PATTERN],a:["target","href","title","rel"],area:[],b:[],br:[],col:[],code:[],dd:[],div:[],dl:[],dt:[],em:[],hr:[],h1:[],h2:[],h3:[],h4:[],h5:[],h6:[],i:[],img:["src","srcset","alt","title","width","height"],li:[],ol:[],p:[],pre:[],s:[],small:[],span:[],sub:[],sup:[],strong:[],u:[],ul:[]},uriAttributes=new Set(["background","cite","href","itemtype","longdesc","poster","src","xlink:href"]),SAFE_URL_PATTERN=/^(?!javascript:)(?:[a-z0-9+.-]+:|[^&:/?#]*(?:[/?#]|$))/i,allowedAttribute=(n,e)=>{const t=n.nodeName.toLowerCase();return e.includes(t)?uriAttributes.has(t)?!!SAFE_URL_PATTERN.test(n.nodeValue):!0:e.filter(r=>r instanceof RegExp).some(r=>r.test(t))};function sanitizeHtml(n,e,t){if(!n.length)return n;if(t&&typeof t=="function")return t(n);const a=new window.DOMParser().parseFromString(n,"text/html"),o=[].concat(...a.body.querySelectorAll("*"));for(const s of o){const l=s.nodeName.toLowerCase();if(!Object.keys(e).includes(l)){s.remove();continue}const c=[].concat(...s.attributes),f=[].concat(e["*"]||[],e[l]||[]);for(const d of c)allowedAttribute(d,f)||s.removeAttribute(d.nodeName)}return a.body.innerHTML}const NAME$5="TemplateFactory",Default$4={allowList:DefaultAllowlist,content:{},extraClass:"",html:!1,sanitize:!0,sanitizeFn:null,template:"<div></div>"},DefaultType$4={allowList:"object",content:"object",extraClass:"(string|function)",html:"boolean",sanitize:"boolean",sanitizeFn:"(null|function)",template:"string"},DefaultContentType={entry:"(string|element|function|null)",selector:"(string|element)"};class TemplateFactory extends Config$1{constructor(e){super(),this._config=this._getConfig(e)}static get Default(){return Default$4}static get DefaultType(){return DefaultType$4}static get NAME(){return NAME$5}getContent(){return Object.values(this._config.content).map(e=>this._resolvePossibleFunction(e)).filter(Boolean)}hasContent(){return this.getContent().length>0}changeContent(e){return this._checkContent(e),this._config.content={...this._config.content,...e},this}toHtml(){const e=document.createElement("div");e.innerHTML=this._maybeSanitize(this._config.template);for(const[a,o]of Object.entries(this._config.content))this._setContent(e,o,a);const t=e.children[0],r=this._resolvePossibleFunction(this._config.extraClass);return r&&t.classList.add(...r.split(" ")),t}_typeCheckConfig(e){super._typeCheckConfig(e),this._checkContent(e.content)}_checkContent(e){for(const[t,r]of Object.entries(e))super._typeCheckConfig({selector:t,entry:r},DefaultContentType)}_setContent(e,t,r){const a=SelectorEngine.findOne(r,e);if(a){if(t=this._resolvePossibleFunction(t),!t){a.remove();return}if(isElement(t)){this._putElementInTemplate(getElement(t),a);return}if(this._config.html){a.innerHTML=this._maybeSanitize(t);return}a.textContent=t}}_maybeSanitize(e){return this._config.sanitize?sanitizeHtml(e,this._config.allowList,this._config.sanitizeFn):e}_resolvePossibleFunction(e){return execute(e,[void 0,this])}_putElementInTemplate(e,t){if(this._config.html){t.innerHTML="",t.append(e);return}t.textContent=e.textContent}}const NAME$4="tooltip",DISALLOWED_ATTRIBUTES=new Set(["sanitize","allowList","sanitizeFn"]),CLASS_NAME_FADE$2="fade",CLASS_NAME_MODAL="modal",CLASS_NAME_SHOW$2="show",SELECTOR_TOOLTIP_INNER=".tooltip-inner",SELECTOR_MODAL=`.${CLASS_NAME_MODAL}`,EVENT_MODAL_HIDE="hide.bs.modal",TRIGGER_HOVER="hover",TRIGGER_FOCUS="focus",TRIGGER_CLICK="click",TRIGGER_MANUAL="manual",EVENT_HIDE$2="hide",EVENT_HIDDEN$2="hidden",EVENT_SHOW$2="show",EVENT_SHOWN$2="shown",EVENT_INSERTED="inserted",EVENT_CLICK$1="click",EVENT_FOCUSIN$1="focusin",EVENT_FOCUSOUT$1="focusout",EVENT_MOUSEENTER="mouseenter",EVENT_MOUSELEAVE="mouseleave",AttachmentMap={AUTO:"auto",TOP:"top",RIGHT:isRTL()?"left":"right",BOTTOM:"bottom",LEFT:isRTL()?"right":"left"},Default$3={allowList:DefaultAllowlist,animation:!0,boundary:"clippingParents",container:!1,customClass:"",delay:0,fallbackPlacements:["top","right","bottom","left"],html:!1,offset:[0,6],placement:"top",popperConfig:null,sanitize:!0,sanitizeFn:null,selector:!1,template:'<div class="tooltip" role="tooltip"><div class="tooltip-arrow"></div><div class="tooltip-inner"></div></div>',title:"",trigger:"hover focus"},DefaultType$3={allowList:"object",animation:"boolean",boundary:"(string|element)",container:"(string|element|boolean)",customClass:"(string|function)",delay:"(number|object)",fallbackPlacements:"array",html:"boolean",offset:"(array|string|function)",placement:"(string|function)",popperConfig:"(null|object|function)",sanitize:"boolean",sanitizeFn:"(null|function)",selector:"(string|boolean)",template:"string",title:"(string|element|function)",trigger:"string"};let Tooltip$1=class li extends BaseComponent{constructor(e,t){if(typeof Popper>"u")throw new TypeError("Bootstrap's tooltips require Popper (https://popper.js.org/docs/v2/)");super(e,t),this._isEnabled=!0,this._timeout=0,this._isHovered=null,this._activeTrigger={},this._popper=null,this._templateFactory=null,this._newContent=null,this.tip=null,this._setListeners(),this._config.selector||this._fixTitle()}static get Default(){return Default$3}static get DefaultType(){return DefaultType$3}static get NAME(){return NAME$4}enable(){this._isEnabled=!0}disable(){this._isEnabled=!1}toggleEnabled(){this._isEnabled=!this._isEnabled}toggle(){if(this._isEnabled){if(this._isShown()){this._leave();return}this._enter()}}dispose(){clearTimeout(this._timeout),EventHandler.off(this._element.closest(SELECTOR_MODAL),EVENT_MODAL_HIDE,this._hideModalHandler),this._element.getAttribute("data-bs-original-title")&&this._element.setAttribute("title",this._element.getAttribute("data-bs-original-title")),this._disposePopper(),super.dispose()}show(){if(this._element.style.display==="none")throw new Error("Please use show on visible elements");if(!(this._isWithContent()&&this._isEnabled))return;const e=EventHandler.trigger(this._element,this.constructor.eventName(EVENT_SHOW$2)),r=(findShadowRoot(this._element)||this._element.ownerDocument.documentElement).contains(this._element);if(e.defaultPrevented||!r)return;this._disposePopper();const a=this._getTipElement();this._element.setAttribute("aria-describedby",a.getAttribute("id"));const{container:o}=this._config;if(this._element.ownerDocument.documentElement.contains(this.tip)||(o.append(a),EventHandler.trigger(this._element,this.constructor.eventName(EVENT_INSERTED))),this._popper=this._createPopper(a),a.classList.add(CLASS_NAME_SHOW$2),"ontouchstart"in document.documentElement)for(const l of[].concat(...document.body.children))EventHandler.on(l,"mouseover",noop$1);const s=()=>{EventHandler.trigger(this._element,this.constructor.eventName(EVENT_SHOWN$2)),this._isHovered===!1&&this._leave(),this._isHovered=!1};this._queueCallback(s,this.tip,this._isAnimated())}hide(){if(!this._isShown()||EventHandler.trigger(this._element,this.constructor.eventName(EVENT_HIDE$2)).defaultPrevented)return;if(this._getTipElement().classList.remove(CLASS_NAME_SHOW$2),"ontouchstart"in document.documentElement)for(const a of[].concat(...document.body.children))EventHandler.off(a,"mouseover",noop$1);this._activeTrigger[TRIGGER_CLICK]=!1,this._activeTrigger[TRIGGER_FOCUS]=!1,this._activeTrigger[TRIGGER_HOVER]=!1,this._isHovered=null;const r=()=>{this._isWithActiveTrigger()||(this._isHovered||this._disposePopper(),this._element.removeAttribute("aria-describedby"),EventHandler.trigger(this._element,this.constructor.eventName(EVENT_HIDDEN$2)))};this._queueCallback(r,this.tip,this._isAnimated())}update(){this._popper&&this._popper.update()}_isWithContent(){return!!this._getTitle()}_getTipElement(){return this.tip||(this.tip=this._createTipElement(this._newContent||this._getContentForTemplate())),this.tip}_createTipElement(e){const t=this._getTemplateFactory(e).toHtml();if(!t)return null;t.classList.remove(CLASS_NAME_FADE$2,CLASS_NAME_SHOW$2),t.classList.add(`bs-${this.constructor.NAME}-auto`);const r=getUID(this.constructor.NAME).toString();return t.setAttribute("id",r),this._isAnimated()&&t.classList.add(CLASS_NAME_FADE$2),t}setContent(e){this._newContent=e,this._isShown()&&(this._disposePopper(),this.show())}_getTemplateFactory(e){return this._templateFactory?this._templateFactory.changeContent(e):this._templateFactory=new TemplateFactory({...this._config,content:e,extraClass:this._resolvePossibleFunction(this._config.customClass)}),this._templateFactory}_getContentForTemplate(){return{[SELECTOR_TOOLTIP_INNER]:this._getTitle()}}_getTitle(){return this._resolvePossibleFunction(this._config.title)||this._element.getAttribute("data-bs-original-title")}_initializeOnDelegatedTarget(e){return this.constructor.getOrCreateInstance(e.delegateTarget,this._getDelegateConfig())}_isAnimated(){return this._config.animation||this.tip&&this.tip.classList.contains(CLASS_NAME_FADE$2)}_isShown(){return this.tip&&this.tip.classList.contains(CLASS_NAME_SHOW$2)}_createPopper(e){const t=execute(this._config.placement,[this,e,this._element]),r=AttachmentMap[t.toUpperCase()];return createPopper(this._element,e,this._getPopperConfig(r))}_getOffset(){const{offset:e}=this._config;return typeof e=="string"?e.split(",").map(t=>Number.parseInt(t,10)):typeof e=="function"?t=>e(t,this._element):e}_resolvePossibleFunction(e){return execute(e,[this._element,this._element])}_getPopperConfig(e){const t={placement:e,modifiers:[{name:"flip",options:{fallbackPlacements:this._config.fallbackPlacements}},{name:"offset",options:{offset:this._getOffset()}},{name:"preventOverflow",options:{boundary:this._config.boundary}},{name:"arrow",options:{element:`.${this.constructor.NAME}-arrow`}},{name:"preSetPlacement",enabled:!0,phase:"beforeMain",fn:r=>{this._getTipElement().setAttribute("data-popper-placement",r.state.placement)}}]};return{...t,...execute(this._config.popperConfig,[void 0,t])}}_setListeners(){const e=this._config.trigger.split(" ");for(const t of e)if(t==="click")EventHandler.on(this._element,this.constructor.eventName(EVENT_CLICK$1),this._config.selector,r=>{const a=this._initializeOnDelegatedTarget(r);a._activeTrigger[TRIGGER_CLICK]=!(a._isShown()&&a._activeTrigger[TRIGGER_CLICK]),a.toggle()});else if(t!==TRIGGER_MANUAL){const r=t===TRIGGER_HOVER?this.constructor.eventName(EVENT_MOUSEENTER):this.constructor.eventName(EVENT_FOCUSIN$1),a=t===TRIGGER_HOVER?this.constructor.eventName(EVENT_MOUSELEAVE):this.constructor.eventName(EVENT_FOCUSOUT$1);EventHandler.on(this._element,r,this._config.selector,o=>{const s=this._initializeOnDelegatedTarget(o);s._activeTrigger[o.type==="focusin"?TRIGGER_FOCUS:TRIGGER_HOVER]=!0,s._enter()}),EventHandler.on(this._element,a,this._config.selector,o=>{const s=this._initializeOnDelegatedTarget(o);s._activeTrigger[o.type==="focusout"?TRIGGER_FOCUS:TRIGGER_HOVER]=s._element.contains(o.relatedTarget),s._leave()})}this._hideModalHandler=()=>{this._element&&this.hide()},EventHandler.on(this._element.closest(SELECTOR_MODAL),EVENT_MODAL_HIDE,this._hideModalHandler)}_fixTitle(){const e=this._element.getAttribute("title");e&&(!this._element.getAttribute("aria-label")&&!this._element.textContent.trim()&&this._element.setAttribute("aria-label",e),this._element.setAttribute("data-bs-original-title",e),this._element.removeAttribute("title"))}_enter(){if(this._isShown()||this._isHovered){this._isHovered=!0;return}this._isHovered=!0,this._setTimeout(()=>{this._isHovered&&this.show()},this._config.delay.show)}_leave(){this._isWithActiveTrigger()||(this._isHovered=!1,this._setTimeout(()=>{this._isHovered||this.hide()},this._config.delay.hide))}_setTimeout(e,t){clearTimeout(this._timeout),this._timeout=setTimeout(e,t)}_isWithActiveTrigger(){return Object.values(this._activeTrigger).includes(!0)}_getConfig(e){const t=Manipulator.getDataAttributes(this._element);for(const r of Object.keys(t))DISALLOWED_ATTRIBUTES.has(r)&&delete t[r];return e={...t,...typeof e=="object"&&e?e:{}},e=this._mergeConfigObj(e),e=this._configAfterMerge(e),this._typeCheckConfig(e),e}_configAfterMerge(e){return e.container=e.container===!1?document.body:getElement(e.container),typeof e.delay=="number"&&(e.delay={show:e.delay,hide:e.delay}),typeof e.title=="number"&&(e.title=e.title.toString()),typeof e.content=="number"&&(e.content=e.content.toString()),e}_getDelegateConfig(){const e={};for(const[t,r]of Object.entries(this._config))this.constructor.Default[t]!==r&&(e[t]=r);return e.selector=!1,e.trigger="manual",e}_disposePopper(){this._popper&&(this._popper.destroy(),this._popper=null),this.tip&&(this.tip.remove(),this.tip=null)}static jQueryInterface(e){return this.each(function(){const t=li.getOrCreateInstance(this,e);if(typeof e=="string"){if(typeof t[e]>"u")throw new TypeError(`No method named "${e}"`);t[e]()}})}};defineJQueryPlugin(Tooltip$1);const NAME$3="popover",SELECTOR_TITLE=".popover-header",SELECTOR_CONTENT=".popover-body",Default$2={...Tooltip$1.Default,content:"",offset:[0,8],placement:"right",template:'<div class="popover" role="tooltip"><div class="popover-arrow"></div><h3 class="popover-header"></h3><div class="popover-body"></div></div>',trigger:"click"},DefaultType$2={...Tooltip$1.DefaultType,content:"(null|string|element|function)"};class Popover extends Tooltip$1{static get Default(){return Default$2}static get DefaultType(){return DefaultType$2}static get NAME(){return NAME$3}_isWithContent(){return this._getTitle()||this._getContent()}_getContentForTemplate(){return{[SELECTOR_TITLE]:this._getTitle(),[SELECTOR_CONTENT]:this._getContent()}}_getContent(){return this._resolvePossibleFunction(this._config.content)}static jQueryInterface(e){return this.each(function(){const t=Popover.getOrCreateInstance(this,e);if(typeof e=="string"){if(typeof t[e]>"u")throw new TypeError(`No method named "${e}"`);t[e]()}})}}defineJQueryPlugin(Popover);const NAME$2="scrollspy",DATA_KEY$2="bs.scrollspy",EVENT_KEY$2=`.${DATA_KEY$2}`,DATA_API_KEY=".data-api",EVENT_ACTIVATE=`activate${EVENT_KEY$2}`,EVENT_CLICK=`click${EVENT_KEY$2}`,EVENT_LOAD_DATA_API$1=`load${EVENT_KEY$2}${DATA_API_KEY}`,CLASS_NAME_DROPDOWN_ITEM="dropdown-item",CLASS_NAME_ACTIVE$1="active",SELECTOR_DATA_SPY='[data-bs-spy="scroll"]',SELECTOR_TARGET_LINKS="[href]",SELECTOR_NAV_LIST_GROUP=".nav, .list-group",SELECTOR_NAV_LINKS=".nav-link",SELECTOR_NAV_ITEMS=".nav-item",SELECTOR_LIST_ITEMS=".list-group-item",SELECTOR_LINK_ITEMS=`${SELECTOR_NAV_LINKS}, ${SELECTOR_NAV_ITEMS} > ${SELECTOR_NAV_LINKS}, ${SELECTOR_LIST_ITEMS}`,SELECTOR_DROPDOWN=".dropdown",SELECTOR_DROPDOWN_TOGGLE$1=".dropdown-toggle",Default$1={offset:null,rootMargin:"0px 0px -25%",smoothScroll:!1,target:null,threshold:[.1,.5,1]},DefaultType$1={offset:"(number|null)",rootMargin:"string",smoothScroll:"boolean",target:"element",threshold:"array"};class ScrollSpy extends BaseComponent{constructor(e,t){super(e,t),this._targetLinks=new Map,this._observableSections=new Map,this._rootElement=getComputedStyle(this._element).overflowY==="visible"?null:this._element,this._activeTarget=null,this._observer=null,this._previousScrollData={visibleEntryTop:0,parentScrollTop:0},this.refresh()}static get Default(){return Default$1}static get DefaultType(){return DefaultType$1}static get NAME(){return NAME$2}refresh(){this._initializeTargetsAndObservables(),this._maybeEnableSmoothScroll(),this._observer?this._observer.disconnect():this._observer=this._getNewObserver();for(const e of this._observableSections.values())this._observer.observe(e)}dispose(){this._observer.disconnect(),super.dispose()}_configAfterMerge(e){return e.target=getElement(e.target)||document.body,e.rootMargin=e.offset?`${e.offset}px 0px -30%`:e.rootMargin,typeof e.threshold=="string"&&(e.threshold=e.threshold.split(",").map(t=>Number.parseFloat(t))),e}_maybeEnableSmoothScroll(){this._config.smoothScroll&&(EventHandler.off(this._config.target,EVENT_CLICK),EventHandler.on(this._config.target,EVENT_CLICK,SELECTOR_TARGET_LINKS,e=>{const t=this._observableSections.get(e.target.hash);if(t){e.preventDefault();const r=this._rootElement||window,a=t.offsetTop-this._element.offsetTop;if(r.scrollTo){r.scrollTo({top:a,behavior:"smooth"});return}r.scrollTop=a}}))}_getNewObserver(){const e={root:this._rootElement,threshold:this._config.threshold,rootMargin:this._config.rootMargin};return new IntersectionObserver(t=>this._observerCallback(t),e)}_observerCallback(e){const t=s=>this._targetLinks.get(`#${s.target.id}`),r=s=>{this._previousScrollData.visibleEntryTop=s.target.offsetTop,this._process(t(s))},a=(this._rootElement||document.documentElement).scrollTop,o=a>=this._previousScrollData.parentScrollTop;this._previousScrollData.parentScrollTop=a;for(const s of e){if(!s.isIntersecting){this._activeTarget=null,this._clearActiveClass(t(s));continue}const l=s.target.offsetTop>=this._previousScrollData.visibleEntryTop;if(o&&l){if(r(s),!a)return;continue}!o&&!l&&r(s)}}_initializeTargetsAndObservables(){this._targetLinks=new Map,this._observableSections=new Map;const e=SelectorEngine.find(SELECTOR_TARGET_LINKS,this._config.target);for(const t of e){if(!t.hash||isDisabled(t))continue;const r=SelectorEngine.findOne(decodeURI(t.hash),this._element);isVisible(r)&&(this._targetLinks.set(decodeURI(t.hash),t),this._observableSections.set(t.hash,r))}}_process(e){this._activeTarget!==e&&(this._clearActiveClass(this._config.target),this._activeTarget=e,e.classList.add(CLASS_NAME_ACTIVE$1),this._activateParents(e),EventHandler.trigger(this._element,EVENT_ACTIVATE,{relatedTarget:e}))}_activateParents(e){if(e.classList.contains(CLASS_NAME_DROPDOWN_ITEM)){SelectorEngine.findOne(SELECTOR_DROPDOWN_TOGGLE$1,e.closest(SELECTOR_DROPDOWN)).classList.add(CLASS_NAME_ACTIVE$1);return}for(const t of SelectorEngine.parents(e,SELECTOR_NAV_LIST_GROUP))for(const r of SelectorEngine.prev(t,SELECTOR_LINK_ITEMS))r.classList.add(CLASS_NAME_ACTIVE$1)}_clearActiveClass(e){e.classList.remove(CLASS_NAME_ACTIVE$1);const t=SelectorEngine.find(`${SELECTOR_TARGET_LINKS}.${CLASS_NAME_ACTIVE$1}`,e);for(const r of t)r.classList.remove(CLASS_NAME_ACTIVE$1)}static jQueryInterface(e){return this.each(function(){const t=ScrollSpy.getOrCreateInstance(this,e);if(typeof e=="string"){if(t[e]===void 0||e.startsWith("_")||e==="constructor")throw new TypeError(`No method named "${e}"`);t[e]()}})}}EventHandler.on(window,EVENT_LOAD_DATA_API$1,()=>{for(const n of SelectorEngine.find(SELECTOR_DATA_SPY))ScrollSpy.getOrCreateInstance(n)});defineJQueryPlugin(ScrollSpy);const NAME$1="tab",DATA_KEY$1="bs.tab",EVENT_KEY$1=`.${DATA_KEY$1}`,EVENT_HIDE$1=`hide${EVENT_KEY$1}`,EVENT_HIDDEN$1=`hidden${EVENT_KEY$1}`,EVENT_SHOW$1=`show${EVENT_KEY$1}`,EVENT_SHOWN$1=`shown${EVENT_KEY$1}`,EVENT_CLICK_DATA_API=`click${EVENT_KEY$1}`,EVENT_KEYDOWN=`keydown${EVENT_KEY$1}`,EVENT_LOAD_DATA_API=`load${EVENT_KEY$1}`,ARROW_LEFT_KEY="ArrowLeft",ARROW_RIGHT_KEY="ArrowRight",ARROW_UP_KEY="ArrowUp",ARROW_DOWN_KEY="ArrowDown",HOME_KEY="Home",END_KEY="End",CLASS_NAME_ACTIVE="active",CLASS_NAME_FADE$1="fade",CLASS_NAME_SHOW$1="show",CLASS_DROPDOWN="dropdown",SELECTOR_DROPDOWN_TOGGLE=".dropdown-toggle",SELECTOR_DROPDOWN_MENU=".dropdown-menu",NOT_SELECTOR_DROPDOWN_TOGGLE=`:not(${SELECTOR_DROPDOWN_TOGGLE})`,SELECTOR_TAB_PANEL='.list-group, .nav, [role="tablist"]',SELECTOR_OUTER=".nav-item, .list-group-item",SELECTOR_INNER=`.nav-link${NOT_SELECTOR_DROPDOWN_TOGGLE}, .list-group-item${NOT_SELECTOR_DROPDOWN_TOGGLE}, [role="tab"]${NOT_SELECTOR_DROPDOWN_TOGGLE}`,SELECTOR_DATA_TOGGLE='[data-bs-toggle="tab"], [data-bs-toggle="pill"], [data-bs-toggle="list"]',SELECTOR_INNER_ELEM=`${SELECTOR_INNER}, ${SELECTOR_DATA_TOGGLE}`,SELECTOR_DATA_TOGGLE_ACTIVE=`.${CLASS_NAME_ACTIVE}[data-bs-toggle="tab"], .${CLASS_NAME_ACTIVE}[data-bs-toggle="pill"], .${CLASS_NAME_ACTIVE}[data-bs-toggle="list"]`;class Tab extends BaseComponent{constructor(e){super(e),this._parent=this._element.closest(SELECTOR_TAB_PANEL),this._parent&&(this._setInitialAttributes(this._parent,this._getChildren()),EventHandler.on(this._element,EVENT_KEYDOWN,t=>this._keydown(t)))}static get NAME(){return NAME$1}show(){const e=this._element;if(this._elemIsActive(e))return;const t=this._getActiveElem(),r=t?EventHandler.trigger(t,EVENT_HIDE$1,{relatedTarget:e}):null;EventHandler.trigger(e,EVENT_SHOW$1,{relatedTarget:t}).defaultPrevented||r&&r.defaultPrevented||(this._deactivate(t,e),this._activate(e,t))}_activate(e,t){if(!e)return;e.classList.add(CLASS_NAME_ACTIVE),this._activate(SelectorEngine.getElementFromSelector(e));const r=()=>{if(e.getAttribute("role")!=="tab"){e.classList.add(CLASS_NAME_SHOW$1);return}e.removeAttribute("tabindex"),e.setAttribute("aria-selected",!0),this._toggleDropDown(e,!0),EventHandler.trigger(e,EVENT_SHOWN$1,{relatedTarget:t})};this._queueCallback(r,e,e.classList.contains(CLASS_NAME_FADE$1))}_deactivate(e,t){if(!e)return;e.classList.remove(CLASS_NAME_ACTIVE),e.blur(),this._deactivate(SelectorEngine.getElementFromSelector(e));const r=()=>{if(e.getAttribute("role")!=="tab"){e.classList.remove(CLASS_NAME_SHOW$1);return}e.setAttribute("aria-selected",!1),e.setAttribute("tabindex","-1"),this._toggleDropDown(e,!1),EventHandler.trigger(e,EVENT_HIDDEN$1,{relatedTarget:t})};this._queueCallback(r,e,e.classList.contains(CLASS_NAME_FADE$1))}_keydown(e){if(![ARROW_LEFT_KEY,ARROW_RIGHT_KEY,ARROW_UP_KEY,ARROW_DOWN_KEY,HOME_KEY,END_KEY].includes(e.key))return;e.stopPropagation(),e.preventDefault();const t=this._getChildren().filter(a=>!isDisabled(a));let r;if([HOME_KEY,END_KEY].includes(e.key))r=t[e.key===HOME_KEY?0:t.length-1];else{const a=[ARROW_RIGHT_KEY,ARROW_DOWN_KEY].includes(e.key);r=getNextActiveElement(t,e.target,a,!0)}r&&(r.focus({preventScroll:!0}),Tab.getOrCreateInstance(r).show())}_getChildren(){return SelectorEngine.find(SELECTOR_INNER_ELEM,this._parent)}_getActiveElem(){return this._getChildren().find(e=>this._elemIsActive(e))||null}_setInitialAttributes(e,t){this._setAttributeIfNotExists(e,"role","tablist");for(const r of t)this._setInitialAttributesOnChild(r)}_setInitialAttributesOnChild(e){e=this._getInnerElement(e);const t=this._elemIsActive(e),r=this._getOuterElement(e);e.setAttribute("aria-selected",t),r!==e&&this._setAttributeIfNotExists(r,"role","presentation"),t||e.setAttribute("tabindex","-1"),this._setAttributeIfNotExists(e,"role","tab"),this._setInitialAttributesOnTargetPanel(e)}_setInitialAttributesOnTargetPanel(e){const t=SelectorEngine.getElementFromSelector(e);t&&(this._setAttributeIfNotExists(t,"role","tabpanel"),e.id&&this._setAttributeIfNotExists(t,"aria-labelledby",`${e.id}`))}_toggleDropDown(e,t){const r=this._getOuterElement(e);if(!r.classList.contains(CLASS_DROPDOWN))return;const a=(o,s)=>{const l=SelectorEngine.findOne(o,r);l&&l.classList.toggle(s,t)};a(SELECTOR_DROPDOWN_TOGGLE,CLASS_NAME_ACTIVE),a(SELECTOR_DROPDOWN_MENU,CLASS_NAME_SHOW$1),r.setAttribute("aria-expanded",t)}_setAttributeIfNotExists(e,t,r){e.hasAttribute(t)||e.setAttribute(t,r)}_elemIsActive(e){return e.classList.contains(CLASS_NAME_ACTIVE)}_getInnerElement(e){return e.matches(SELECTOR_INNER_ELEM)?e:SelectorEngine.findOne(SELECTOR_INNER_ELEM,e)}_getOuterElement(e){return e.closest(SELECTOR_OUTER)||e}static jQueryInterface(e){return this.each(function(){const t=Tab.getOrCreateInstance(this);if(typeof e=="string"){if(t[e]===void 0||e.startsWith("_")||e==="constructor")throw new TypeError(`No method named "${e}"`);t[e]()}})}}EventHandler.on(document,EVENT_CLICK_DATA_API,SELECTOR_DATA_TOGGLE,function(n){["A","AREA"].includes(this.tagName)&&n.preventDefault(),!isDisabled(this)&&Tab.getOrCreateInstance(this).show()});EventHandler.on(window,EVENT_LOAD_DATA_API,()=>{for(const n of SelectorEngine.find(SELECTOR_DATA_TOGGLE_ACTIVE))Tab.getOrCreateInstance(n)});defineJQueryPlugin(Tab);const NAME="toast",DATA_KEY="bs.toast",EVENT_KEY=`.${DATA_KEY}`,EVENT_MOUSEOVER=`mouseover${EVENT_KEY}`,EVENT_MOUSEOUT=`mouseout${EVENT_KEY}`,EVENT_FOCUSIN=`focusin${EVENT_KEY}`,EVENT_FOCUSOUT=`focusout${EVENT_KEY}`,EVENT_HIDE=`hide${EVENT_KEY}`,EVENT_HIDDEN=`hidden${EVENT_KEY}`,EVENT_SHOW=`show${EVENT_KEY}`,EVENT_SHOWN=`shown${EVENT_KEY}`,CLASS_NAME_FADE="fade",CLASS_NAME_HIDE="hide",CLASS_NAME_SHOW="show",CLASS_NAME_SHOWING="showing",DefaultType={animation:"boolean",autohide:"boolean",delay:"number"},Default={animation:!0,autohide:!0,delay:5e3};class Toast extends BaseComponent{constructor(e,t){super(e,t),this._timeout=null,this._hasMouseInteraction=!1,this._hasKeyboardInteraction=!1,this._setListeners()}static get Default(){return Default}static get DefaultType(){return DefaultType}static get NAME(){return NAME}show(){if(EventHandler.trigger(this._element,EVENT_SHOW).defaultPrevented)return;this._clearTimeout(),this._config.animation&&this._element.classList.add(CLASS_NAME_FADE);const t=()=>{this._element.classList.remove(CLASS_NAME_SHOWING),EventHandler.trigger(this._element,EVENT_SHOWN),this._maybeScheduleHide()};this._element.classList.remove(CLASS_NAME_HIDE),reflow(this._element),this._element.classList.add(CLASS_NAME_SHOW,CLASS_NAME_SHOWING),this._queueCallback(t,this._element,this._config.animation)}hide(){if(!this.isShown()||EventHandler.trigger(this._element,EVENT_HIDE).defaultPrevented)return;const t=()=>{this._element.classList.add(CLASS_NAME_HIDE),this._element.classList.remove(CLASS_NAME_SHOWING,CLASS_NAME_SHOW),EventHandler.trigger(this._element,EVENT_HIDDEN)};this._element.classList.add(CLASS_NAME_SHOWING),this._queueCallback(t,this._element,this._config.animation)}dispose(){this._clearTimeout(),this.isShown()&&this._element.classList.remove(CLASS_NAME_SHOW),super.dispose()}isShown(){return this._element.classList.contains(CLASS_NAME_SHOW)}_maybeScheduleHide(){this._config.autohide&&(this._hasMouseInteraction||this._hasKeyboardInteraction||(this._timeout=setTimeout(()=>{this.hide()},this._config.delay)))}_onInteraction(e,t){switch(e.type){case"mouseover":case"mouseout":{this._hasMouseInteraction=t;break}case"focusin":case"focusout":{this._hasKeyboardInteraction=t;break}}if(t){this._clearTimeout();return}const r=e.relatedTarget;this._element===r||this._element.contains(r)||this._maybeScheduleHide()}_setListeners(){EventHandler.on(this._element,EVENT_MOUSEOVER,e=>this._onInteraction(e,!0)),EventHandler.on(this._element,EVENT_MOUSEOUT,e=>this._onInteraction(e,!1)),EventHandler.on(this._element,EVENT_FOCUSIN,e=>this._onInteraction(e,!0)),EventHandler.on(this._element,EVENT_FOCUSOUT,e=>this._onInteraction(e,!1))}_clearTimeout(){clearTimeout(this._timeout),this._timeout=null}static jQueryInterface(e){return this.each(function(){const t=Toast.getOrCreateInstance(this,e);if(typeof e=="string"){if(typeof t[e]>"u")throw new TypeError(`No method named "${e}"`);t[e](this)}})}}enableDismissTrigger(Toast);defineJQueryPlugin(Toast);(function(){const htmx={onLoad:null,process:null,on:null,off:null,trigger:null,ajax:null,find:null,findAll:null,closest:null,values:function(n,e){return getInputValues(n,e||"post").values},remove:null,addClass:null,removeClass:null,toggleClass:null,takeClass:null,swap:null,defineExtension:null,removeExtension:null,logAll:null,logNone:null,logger:null,config:{historyEnabled:!0,historyCacheSize:10,refreshOnHistoryMiss:!1,defaultSwapStyle:"innerHTML",defaultSwapDelay:0,defaultSettleDelay:20,includeIndicatorStyles:!0,indicatorClass:"htmx-indicator",requestClass:"htmx-request",addedClass:"htmx-added",settlingClass:"htmx-settling",swappingClass:"htmx-swapping",allowEval:!0,allowScriptTags:!0,inlineScriptNonce:"",inlineStyleNonce:"",attributesToSettle:["class","style","width","height"],withCredentials:!1,timeout:0,wsReconnectDelay:"full-jitter",wsBinaryType:"blob",disableSelector:"[hx-disable], [data-hx-disable]",scrollBehavior:"instant",defaultFocusScroll:!1,getCacheBusterParam:!1,globalViewTransitions:!1,methodsThatUseUrlParams:["get","delete"],selfRequestsOnly:!0,ignoreTitle:!1,scrollIntoViewOnBoost:!0,triggerSpecsCache:null,disableInheritance:!1,responseHandling:[{code:"204",swap:!1},{code:"[23]..",swap:!0},{code:"[45]..",swap:!1,error:!0}],allowNestedOobSwaps:!0,historyRestoreAsHxRequest:!0,reportValidityOfForms:!1},parseInterval:null,location,_:null,version:"2.0.10"};htmx.onLoad=onLoadHelper,htmx.process=processNode,htmx.on=addEventListenerImpl,htmx.off=removeEventListenerImpl,htmx.trigger=triggerEvent,htmx.ajax=ajaxHelper,htmx.find=find,htmx.findAll=findAll,htmx.closest=closest,htmx.remove=removeElement,htmx.addClass=addClassToElement,htmx.removeClass=removeClassFromElement,htmx.toggleClass=toggleClassOnElement,htmx.takeClass=takeClassForElement,htmx.swap=swap,htmx.defineExtension=defineExtension,htmx.removeExtension=removeExtension,htmx.logAll=logAll,htmx.logNone=logNone,htmx.parseInterval=parseInterval,htmx._=internalEval;const internalAPI={addTriggerHandler,bodyContains,canAccessLocalStorage,findThisElement,filterValues,swap,hasAttribute,getAttributeValue,getClosestAttributeValue,getClosestMatch,getExpressionVars,getHeaders,getInputValues,getInternalData,getSwapSpecification,getTriggerSpecs,getTarget,makeFragment,mergeObjects,makeSettleInfo,oobSwap,querySelectorExt,settleImmediately,shouldCancel,triggerEvent,triggerErrorEvent,withExtensions},VERBS=["get","post","put","delete","patch"],VERB_SELECTOR=VERBS.map(function(n){return"[hx-"+n+"], [data-hx-"+n+"]"}).join(", ");function parseInterval(n){if(n==null)return;let e=NaN;return n.slice(-2)=="ms"?e=parseFloat(n.slice(0,-2)):n.slice(-1)=="s"?e=parseFloat(n.slice(0,-1))*1e3:n.slice(-1)=="m"?e=parseFloat(n.slice(0,-1))*1e3*60:e=parseFloat(n),isNaN(e)?void 0:e}function getRawAttribute(n,e){return n instanceof Element&&n.getAttribute(e)}function hasAttribute(n,e){return!!n.hasAttribute&&(n.hasAttribute(e)||n.hasAttribute("data-"+e))}function getAttributeValue(n,e){return getRawAttribute(n,e)||getRawAttribute(n,"data-"+e)}function parentElt(n){const e=n.parentElement;return!e&&n.parentNode instanceof ShadowRoot?n.parentNode:e}function getDocument(){return document}function getRootNode(n,e){return n.getRootNode?n.getRootNode({composed:e}):getDocument()}function getClosestMatch(n,e){for(;n&&!e(n);)n=parentElt(n);return n||null}function getAttributeValueWithDisinheritance(n,e,t){const r=getAttributeValue(e,t),a=getAttributeValue(e,"hx-disinherit");var o=getAttributeValue(e,"hx-inherit");if(n!==e){if(htmx.config.disableInheritance)return o&&(o==="*"||o.split(" ").indexOf(t)>=0)?r:null;if(a&&(a==="*"||a.split(" ").indexOf(t)>=0))return"unset"}return r}function getClosestAttributeValue(n,e){let t=null;if(getClosestMatch(n,function(r){return!!(t=getAttributeValueWithDisinheritance(n,asElement(r),e))}),t!=="unset")return t}function matches(n,e){return n instanceof Element&&n.matches(e)}function getStartTag(n){const t=/<([a-z][^\/\0>\x20\t\r\n\f]*)/i.exec(n);return t?t[1].toLowerCase():""}function parseHTML(n){return"parseHTMLUnsafe"in Document?Document.parseHTMLUnsafe(n):new DOMParser().parseFromString(n,"text/html")}function takeChildrenFor(n,e){for(;e.childNodes.length>0;)n.append(e.childNodes[0])}function duplicateScript(n){const e=getDocument().createElement("script");return forEach(n.attributes,function(t){e.setAttribute(t.name,t.value)}),e.textContent=n.textContent,e.async=!1,htmx.config.inlineScriptNonce&&(e.nonce=htmx.config.inlineScriptNonce),e}function isJavaScriptScriptNode(n){return n.matches("script")&&(n.type==="text/javascript"||n.type==="module"||n.type==="")}function normalizeScriptTags(n){Array.from(n.querySelectorAll("script")).forEach(e=>{if(isJavaScriptScriptNode(e)){const t=duplicateScript(e),r=e.parentNode;try{r.insertBefore(t,e)}catch(a){logError(a)}finally{e.remove()}}})}function makeFragment(n){const e=n.replace(/<head(\s[^>]*)?>[\s\S]*?<\/head>/i,""),t=getStartTag(e);let r;if(t==="html"){r=new DocumentFragment;const o=parseHTML(n);takeChildrenFor(r,o.body),r.title=o.title}else if(t==="body"){r=new DocumentFragment;const o=parseHTML(e);takeChildrenFor(r,o.body),r.title=o.title}else{const o=parseHTML('<body><template class="internal-htmx-wrapper">'+e+"</template></body>");r=o.querySelector("template").content,r.title=o.title;var a=r.querySelector("title");a&&a.parentNode===r&&(a.remove(),r.title=a.innerText)}return r&&(htmx.config.allowScriptTags?normalizeScriptTags(r):r.querySelectorAll("script").forEach(o=>o.remove())),r}function maybeCall(n){n&&n()}function isType(n,e){return Object.prototype.toString.call(n)==="[object "+e+"]"}function isFunction(n){return typeof n=="function"}function isRawObject(n){return isType(n,"Object")}function getInternalData(n){const e="htmx-internal-data";let t=n[e];return t||(t=n[e]={}),t}function toArray(n){const e=[];if(n)for(let t=0;t<n.length;t++)e.push(n[t]);return e}function forEach(n,e){if(n)for(let t=0;t<n.length;t++)e(n[t])}function isScrolledIntoView(n){const e=n.getBoundingClientRect(),t=e.top,r=e.bottom;return t<window.innerHeight&&r>=0}function bodyContains(n){return n.getRootNode({composed:!0})===document}function splitOnWhitespace(n){return n.trim().split(/\s+/)}function mergeObjects(n,e){for(const t in e)e.hasOwnProperty(t)&&(n[t]=e[t]);return n}function parseJSON(n){try{return JSON.parse(n)}catch(e){return logError(e),null}}function canAccessLocalStorage(){const n="htmx:sessionStorageTest";try{return sessionStorage.setItem(n,n),sessionStorage.removeItem(n),!0}catch{return!1}}function normalizePath(n){try{const e=new URL(n,window.location.href);n=e.pathname+e.search}catch{}return n!="/"&&(n=n.replace(/\/+$/,"")),n}function internalEval(str){return maybeEval(getDocument().body,function(){return eval(str)})}function onLoadHelper(n){return htmx.on("htmx:load",function(t){n(t.detail.elt)})}function logAll(){htmx.logger=function(n,e,t){console&&console.log(e,n,t)}}function logNone(){htmx.logger=null}function find(n,e){return typeof n!="string"?n.querySelector(e):find(getDocument(),n)}function findAll(n,e){return typeof n!="string"?n.querySelectorAll(e):findAll(getDocument(),n)}function getWindow(){return window}function removeElement(n,e){n=resolveTarget(n),e?getWindow().setTimeout(function(){removeElement(n),n=null},e):parentElt(n).removeChild(n)}function asElement(n){return n instanceof Element?n:null}function asHtmlElement(n){return n instanceof HTMLElement?n:null}function asString(n){return typeof n=="string"?n:null}function asParentNode(n){return n instanceof Element||n instanceof Document||n instanceof DocumentFragment?n:null}function addClassToElement(n,e,t){n=asElement(resolveTarget(n)),n&&(t?getWindow().setTimeout(function(){addClassToElement(n,e),n=null},t):n.classList&&n.classList.add(e))}function removeClassFromElement(n,e,t){let r=asElement(resolveTarget(n));r&&(t?getWindow().setTimeout(function(){removeClassFromElement(r,e),r=null},t):r.classList&&(r.classList.remove(e),r.classList.length===0&&r.removeAttribute("class")))}function toggleClassOnElement(n,e){n=resolveTarget(n),n.classList.toggle(e)}function takeClassForElement(n,e){n=resolveTarget(n),forEach(n.parentElement.children,function(t){removeClassFromElement(t,e)}),addClassToElement(asElement(n),e)}function closest(n,e){return n=asElement(resolveTarget(n)),n?n.closest(e):null}function startsWith(n,e){return n.substring(0,e.length)===e}function endsWith(n,e){return n.substring(n.length-e.length)===e}function normalizeSelector(n){const e=n.trim();return startsWith(e,"<")&&endsWith(e,"/>")?e.substring(1,e.length-2):e}function querySelectorAllExt(n,e,t){if(e.indexOf("global ")===0)return querySelectorAllExt(n,e.slice(7),!0);n=resolveTarget(n);const r=[];{let s=0,l=0;for(let c=0;c<e.length;c++){const f=e[c];if(f===","&&s===0){r.push(e.substring(l,c)),l=c+1;continue}f==="<"?s++:f==="/"&&c<e.length-1&&e[c+1]===">"&&s--}l<e.length&&r.push(e.substring(l))}const a=[],o=[];for(;r.length>0;){const s=normalizeSelector(r.shift());let l;s.indexOf("closest ")===0?l=closest(asElement(n),normalizeSelector(s.slice(8))):s.indexOf("find ")===0?l=find(asParentNode(n),normalizeSelector(s.slice(5))):s==="next"||s==="nextElementSibling"?l=asElement(n).nextElementSibling:s.indexOf("next ")===0?l=scanForwardQuery(n,normalizeSelector(s.slice(5)),!!t):s==="previous"||s==="previousElementSibling"?l=asElement(n).previousElementSibling:s.indexOf("previous ")===0?l=scanBackwardsQuery(n,normalizeSelector(s.slice(9)),!!t):s==="document"?l=document:s==="window"?l=window:s==="body"?l=document.body:s==="root"?l=getRootNode(n,!!t):s==="host"?l=n.getRootNode().host:o.push(s),l&&a.push(l)}if(o.length>0){const s=o.join(","),l=asParentNode(getRootNode(n,!!t));a.push(...toArray(l.querySelectorAll(s)))}return a}var scanForwardQuery=function(n,e,t){const r=asParentNode(getRootNode(n,t)).querySelectorAll(e);for(let a=0;a<r.length;a++){const o=r[a];if(o.compareDocumentPosition(n)===Node.DOCUMENT_POSITION_PRECEDING)return o}},scanBackwardsQuery=function(n,e,t){const r=asParentNode(getRootNode(n,t)).querySelectorAll(e);for(let a=r.length-1;a>=0;a--){const o=r[a];if(o.compareDocumentPosition(n)===Node.DOCUMENT_POSITION_FOLLOWING)return o}};function querySelectorExt(n,e){return typeof n!="string"?querySelectorAllExt(n,e)[0]:querySelectorAllExt(getDocument().body,n)[0]}function resolveTarget(n,e){return typeof n=="string"?find(asParentNode(e)||document,n):n}function processEventArgs(n,e,t,r){return isFunction(e)?{target:getDocument().body,event:asString(n),listener:e,options:t}:{target:resolveTarget(n),event:asString(e),listener:t,options:r}}function addEventListenerImpl(n,e,t,r){return ready(function(){const o=processEventArgs(n,e,t,r);o.target.addEventListener(o.event,o.listener,o.options)}),isFunction(e)?e:t}function removeEventListenerImpl(n,e,t){return ready(function(){const r=processEventArgs(n,e,t);r.target.removeEventListener(r.event,r.listener)}),isFunction(e)?e:t}const DUMMY_ELT=getDocument().createElement("output");function findAttributeTargets(n,e){const t=getClosestAttributeValue(n,e);if(t){if(t==="this")return[findThisElement(n,e)];{const r=querySelectorAllExt(n,t);if(/(^|,)(\s*)inherit(\s*)($|,)/.test(t)){const o=asElement(getClosestMatch(n,function(s){return s!==n&&hasAttribute(asElement(s),e)}));o&&r.push(...findAttributeTargets(o,e))}return r.length===0?(logError('The selector "'+t+'" on '+e+" returned no matches!"),[DUMMY_ELT]):r}}}function findThisElement(n,e){return asElement(getClosestMatch(n,function(t){return getAttributeValue(asElement(t),e)!=null}))}function getTarget(n){const e=getClosestAttributeValue(n,"hx-target");return e?e==="this"?findThisElement(n,"hx-target"):querySelectorExt(n,e):getInternalData(n).boosted?getDocument().body:n}function shouldSettleAttribute(n){return htmx.config.attributesToSettle.includes(n)}function cloneAttributes(n,e){forEach(Array.from(n.attributes),function(t){!e.hasAttribute(t.name)&&shouldSettleAttribute(t.name)&&n.removeAttribute(t.name)}),forEach(e.attributes,function(t){shouldSettleAttribute(t.name)&&n.setAttribute(t.name,t.value)})}function isInlineSwap(n,e){const t=getExtensions(e);for(let r=0;r<t.length;r++){const a=t[r];try{if(a.isInlineSwap(n))return!0}catch(o){logError(o)}}return n==="outerHTML"}function oobSwap(n,e,t,r){r=r||getDocument();let a="#"+CSS.escape(getRawAttribute(e,"id")),o="outerHTML";n==="true"||(n.indexOf(":")>0?(o=n.substring(0,n.indexOf(":")),a=n.substring(n.indexOf(":")+1)):o=n),e.removeAttribute("hx-swap-oob"),e.removeAttribute("data-hx-swap-oob");const s=querySelectorAllExt(r,a,!1);return s.length?(forEach(s,function(l){let c;const f=e.cloneNode(!0);c=getDocument().createDocumentFragment(),c.appendChild(f),isInlineSwap(o,l)||(c=asParentNode(f));const d={shouldSwap:!0,target:l,fragment:c};triggerEvent(l,"htmx:oobBeforeSwap",d)&&(l=d.target,d.shouldSwap&&(handlePreservedElements(c),swapWithStyle(o,l,l,c,t),restorePreservedElements()),forEach(t.elts,function(p){triggerEvent(p,"htmx:oobAfterSwap",d)}))}),e.parentNode.removeChild(e)):(e.parentNode.removeChild(e),triggerErrorEvent(getDocument().body,"htmx:oobErrorNoTarget",{content:e,target:a})),n}function restorePreservedElements(){const n=find("#--htmx-preserve-pantry--");if(n){for(const e of[...n.children]){const t=find("#"+e.id);t.parentNode.moveBefore(e,t),t.remove()}n.remove()}}function handlePreservedElements(n){forEach(findAll(n,"[hx-preserve], [data-hx-preserve]"),function(e){const t=getAttributeValue(e,"id"),r=getDocument().getElementById(t);if(r!=null)if(e.moveBefore){let a=find("#--htmx-preserve-pantry--");a==null&&(getDocument().body.insertAdjacentHTML("afterend","<div id='--htmx-preserve-pantry--'></div>"),a=find("#--htmx-preserve-pantry--")),a.moveBefore(r,null)}else e.parentNode.replaceChild(r,e)})}function handleAttributes(n,e,t){forEach(e.querySelectorAll("[id]"),function(r){const a=getRawAttribute(r,"id");if(a&&a.length>0){const o=asParentNode(n),s=o&&o.querySelector(CSS.escape(r.tagName)+"#"+CSS.escape(a));if(s&&s!==o){const l=r.cloneNode();cloneAttributes(r,s),t.tasks.push(function(){cloneAttributes(r,l)})}}})}function makeAjaxLoadTask(n){return function(){removeClassFromElement(n,htmx.config.addedClass),processNode(asElement(n)),processFocus(asParentNode(n)),triggerEvent(n,"htmx:load")}}function processFocus(n){const e="[autofocus]",t=asHtmlElement(matches(n,e)?n:n.querySelector(e));t?.focus()}function insertNodesBefore(n,e,t,r){for(handleAttributes(n,t,r);t.childNodes.length>0;){const a=t.firstChild;addClassToElement(asElement(a),htmx.config.addedClass),n.insertBefore(a,e),a.nodeType!==Node.TEXT_NODE&&a.nodeType!==Node.COMMENT_NODE&&r.tasks.push(makeAjaxLoadTask(a))}}function stringHash(n,e){let t=0;for(;t<n.length;)e=(e<<5)-e+n.charCodeAt(t++)|0;return e}function attributeHash(n){let e=0;for(let t=0;t<n.attributes.length;t++){const r=n.attributes[t];r.value&&(e=stringHash(r.name,e),e=stringHash(r.value,e))}return e}function deInitOnHandlers(n){const e=getInternalData(n);if(e.onHandlers){for(let t=0;t<e.onHandlers.length;t++){const r=e.onHandlers[t];removeEventListenerImpl(n,r.event,r.listener)}delete e.onHandlers}}function deInitNode(n){const e=getInternalData(n);e.timeout&&clearTimeout(e.timeout),e.listenerInfos&&forEach(e.listenerInfos,function(t){t.on&&removeEventListenerImpl(t.on,t.trigger,t.listener)}),deInitOnHandlers(n),forEach(Object.keys(e),function(t){t!=="firstInitCompleted"&&delete e[t]})}function cleanUpElement(n){triggerEvent(n,"htmx:beforeCleanupElement"),deInitNode(n),forEach(n.children,function(e){cleanUpElement(e)})}function swapOuterHTML(n,e,t){if(n.tagName==="BODY")return swapInnerHTML(n,e,t);let r;const a=n.previousSibling,o=parentElt(n);if(o){for(insertNodesBefore(o,n,e,t),a==null?r=o.firstChild:r=a.nextSibling,t.elts=t.elts.filter(function(s){return s!==n});r&&r!==n;)r instanceof Element&&t.elts.push(r),r=r.nextSibling;cleanUpElement(n),n.remove()}}function swapAfterBegin(n,e,t){return insertNodesBefore(n,n.firstChild,e,t)}function swapBeforeBegin(n,e,t){return insertNodesBefore(parentElt(n),n,e,t)}function swapBeforeEnd(n,e,t){return insertNodesBefore(n,null,e,t)}function swapAfterEnd(n,e,t){return insertNodesBefore(parentElt(n),n.nextSibling,e,t)}function swapDelete(n){cleanUpElement(n);const e=parentElt(n);if(e)return e.removeChild(n)}function swapInnerHTML(n,e,t){const r=n.firstChild;if(insertNodesBefore(n,r,e,t),r){for(;r.nextSibling;)cleanUpElement(r.nextSibling),n.removeChild(r.nextSibling);cleanUpElement(r),n.removeChild(r)}}function swapWithStyle(n,e,t,r,a){switch(n){case"none":return;case"outerHTML":swapOuterHTML(t,r,a);return;case"afterbegin":swapAfterBegin(t,r,a);return;case"beforebegin":swapBeforeBegin(t,r,a);return;case"beforeend":swapBeforeEnd(t,r,a);return;case"afterend":swapAfterEnd(t,r,a);return;case"delete":swapDelete(t);return;default:var o=getExtensions(e);for(let s=0;s<o.length;s++){const l=o[s];try{const c=l.handleSwap(n,t,r,a);if(c){if(Array.isArray(c))for(let f=0;f<c.length;f++){const d=c[f];d.nodeType!==Node.TEXT_NODE&&d.nodeType!==Node.COMMENT_NODE&&a.tasks.push(makeAjaxLoadTask(d))}return}}catch(c){logError(c)}}n==="innerHTML"?swapInnerHTML(t,r,a):swapWithStyle(htmx.config.defaultSwapStyle,e,t,r,a)}}function findAndSwapOobElements(n,e,t){var r=findAll(n,"[hx-swap-oob], [data-hx-swap-oob]");return forEach(r,function(a){if(htmx.config.allowNestedOobSwaps||a.parentElement===null){const o=getAttributeValue(a,"hx-swap-oob");o!=null&&oobSwap(o,a,e,t)}else a.removeAttribute("hx-swap-oob"),a.removeAttribute("data-hx-swap-oob")}),r.length>0}function swap(n,e,t,r){r||(r={});let a=null,o=null,s=function(){maybeCall(r.beforeSwapCallback),n=resolveTarget(n);const f=r.contextElement?getRootNode(r.contextElement,!1):getDocument(),d=document.activeElement;let p={};p={elt:d,start:d?d.selectionStart:null,end:d?d.selectionEnd:null};const _=makeSettleInfo(n);if(t.swapStyle==="textContent")n.textContent=e;else{let y=makeFragment(e);if(_.title=r.title||y.title,r.historyRequest&&(y=y.querySelector("[hx-history-elt],[data-hx-history-elt]")||y),r.selectOOB){const E=r.selectOOB.split(",");for(let C=0;C<E.length;C++){const D=E[C].split(":",2);let M=D[0].trim();M.indexOf("#")===0&&(M=M.substring(1));const F=D[1]||"true",P=y.querySelector("#"+M);P&&oobSwap(F,P,_,f)}}if(findAndSwapOobElements(y,_,f),forEach(findAll(y,"template"),function(E){E.content&&findAndSwapOobElements(E.content,_,f)&&E.remove()}),r.select){const E=getDocument().createDocumentFragment();forEach(y.querySelectorAll(r.select),function(C){E.appendChild(C)}),y=E}handlePreservedElements(y),swapWithStyle(t.swapStyle,r.contextElement,n,y,_),restorePreservedElements()}if(p.elt&&!bodyContains(p.elt)&&getRawAttribute(p.elt,"id")){const y=document.getElementById(getRawAttribute(p.elt,"id")),E={preventScroll:t.focusScroll!==void 0?!t.focusScroll:!htmx.config.defaultFocusScroll};if(y){if(p.start&&y.setSelectionRange)try{y.setSelectionRange(p.start,p.end)}catch{}y.focus(E)}}removeClassFromElement(n,htmx.config.swappingClass),forEach(_.elts,function(y){y.classList&&addClassToElement(y,htmx.config.settlingClass),triggerEvent(y,"htmx:afterSwap",r.eventInfo)}),maybeCall(r.afterSwapCallback),t.ignoreTitle||handleTitle(_.title);const b=function(){if(forEach(_.tasks,function(y){y.call()}),forEach(_.elts,function(y){y.classList&&removeClassFromElement(y,htmx.config.settlingClass),triggerEvent(y,"htmx:afterSettle",r.eventInfo)}),r.anchor){const y=asElement(resolveTarget("#"+r.anchor));y&&y.scrollIntoView({block:"start",behavior:"auto"})}updateScrollState(_.elts,t),maybeCall(r.afterSettleCallback),maybeCall(a)};t.settleDelay>0?getWindow().setTimeout(b,t.settleDelay):b()},l=htmx.config.globalViewTransitions;t.hasOwnProperty("transition")&&(l=t.transition);const c=r.contextElement||getDocument();if(l&&triggerEvent(c,"htmx:beforeTransition",r.eventInfo)&&typeof Promise<"u"&&document.startViewTransition){const f=new Promise(function(p,_){a=p,o=_}),d=s;s=function(){document.startViewTransition(function(){return d(),f})}}try{t?.swapDelay&&t.swapDelay>0?getWindow().setTimeout(s,t.swapDelay):s()}catch(f){throw triggerErrorEvent(c,"htmx:swapError",r.eventInfo),maybeCall(o),f}}function handleTriggerHeader(n,e,t){const r=n.getResponseHeader(e);if(r.indexOf("{")===0){const a=parseJSON(r);for(const o in a)if(a.hasOwnProperty(o)){let s=a[o];isRawObject(s)?t=s.target!==void 0?s.target:t:s={value:s},triggerEvent(t,o,s)}}else{const a=r.split(",");for(let o=0;o<a.length;o++)triggerEvent(t,a[o].trim(),[])}}const WHITESPACE_OR_COMMA=/[\s,]/,SYMBOL_START=/[_$a-zA-Z]/,SYMBOL_CONT=/[_$a-zA-Z0-9]/,STRINGISH_START=['"',"'","/"],NOT_WHITESPACE=/[^\s]/,COMBINED_SELECTOR_START=/[{(]/,COMBINED_SELECTOR_END=/[})]/;function tokenizeString(n){const e=[];let t=0;for(;t<n.length;){if(SYMBOL_START.exec(n.charAt(t))){for(var r=t;SYMBOL_CONT.exec(n.charAt(t+1));)t++;e.push(n.substring(r,t+1))}else if(STRINGISH_START.indexOf(n.charAt(t))!==-1){const a=n.charAt(t);var r=t;for(t++;t<n.length&&n.charAt(t)!==a;)n.charAt(t)==="\\"&&t++,t++;e.push(n.substring(r,t+1))}else{const a=n.charAt(t);e.push(a)}t++}return e}function isPossibleRelativeReference(n,e,t){return SYMBOL_START.exec(n.charAt(0))&&n!=="true"&&n!=="false"&&n!=="this"&&n!==t&&e!=="."}function maybeGenerateConditional(n,e,t){if(e[0]==="["){e.shift();let r=1,a=" return (function("+t+"){ return (",o=null;for(;e.length>0;){const s=e[0];if(s==="]"){if(r--,r===0){o===null&&(a=a+"true"),e.shift(),a+=")})";try{const l=maybeEval(n,function(){return Function(a)()},function(){return!0});return l.source=a,l}catch(l){return triggerErrorEvent(getDocument().body,"htmx:syntax:error",{error:l,source:a}),null}}}else s==="["&&r++;isPossibleRelativeReference(s,o,t)?a+="(("+t+"."+s+") ? ("+t+"."+s+") : (window."+s+"))":a=a+s,o=e.shift()}}}function consumeUntil(n,e){let t="";for(;n.length>0&&!e.test(n[0]);)t+=n.shift();return t}function consumeCSSSelector(n){let e;return n.length>0&&COMBINED_SELECTOR_START.test(n[0])?(n.shift(),e=consumeUntil(n,COMBINED_SELECTOR_END).trim(),n.shift()):e=consumeUntil(n,WHITESPACE_OR_COMMA),e}const INPUT_SELECTOR="input, textarea, select";function parseAndCacheTrigger(n,e,t){const r=[],a=tokenizeString(e);do{consumeUntil(a,NOT_WHITESPACE);const l=a.length,c=consumeUntil(a,/[,\[\s]/);if(c!=="")if(c==="every"){const f={trigger:"every"};consumeUntil(a,NOT_WHITESPACE),f.pollInterval=parseInterval(consumeUntil(a,/[,\[\s]/)),consumeUntil(a,NOT_WHITESPACE);var o=maybeGenerateConditional(n,a,"event");o&&(f.eventFilter=o),r.push(f)}else{const f={trigger:c};var o=maybeGenerateConditional(n,a,"event");for(o&&(f.eventFilter=o),consumeUntil(a,NOT_WHITESPACE);a.length>0&&a[0]!==",";){const p=a.shift();if(p==="changed")f.changed=!0;else if(p==="once")f.once=!0;else if(p==="consume")f.consume=!0;else if(p==="delay"&&a[0]===":")a.shift(),f.delay=parseInterval(consumeUntil(a,WHITESPACE_OR_COMMA));else if(p==="from"&&a[0]===":"){if(a.shift(),COMBINED_SELECTOR_START.test(a[0]))var s=consumeCSSSelector(a);else{var s=consumeUntil(a,WHITESPACE_OR_COMMA);if(s==="closest"||s==="find"||s==="next"||s==="previous"){a.shift();const b=consumeCSSSelector(a);b.length>0&&(s+=" "+b)}}f.from=s}else p==="target"&&a[0]===":"?(a.shift(),f.target=consumeCSSSelector(a)):p==="throttle"&&a[0]===":"?(a.shift(),f.throttle=parseInterval(consumeUntil(a,WHITESPACE_OR_COMMA))):p==="queue"&&a[0]===":"?(a.shift(),f.queue=consumeUntil(a,WHITESPACE_OR_COMMA)):p==="root"&&a[0]===":"?(a.shift(),f[p]=consumeCSSSelector(a)):p==="threshold"&&a[0]===":"?(a.shift(),f[p]=consumeUntil(a,WHITESPACE_OR_COMMA)):triggerErrorEvent(n,"htmx:syntax:error",{token:a.shift()});consumeUntil(a,NOT_WHITESPACE)}r.push(f)}a.length===l&&triggerErrorEvent(n,"htmx:syntax:error",{token:a.shift()}),consumeUntil(a,NOT_WHITESPACE)}while(a[0]===","&&a.shift());return t&&(t[e]=r),r}function getTriggerSpecs(n){const e=getAttributeValue(n,"hx-trigger");let t=[];if(e){const r=htmx.config.triggerSpecsCache;t=r&&r[e]||parseAndCacheTrigger(n,e,r)}return t.length>0?t:matches(n,"form")?[{trigger:"submit"}]:matches(n,'input[type="button"], input[type="submit"]')?[{trigger:"click"}]:matches(n,INPUT_SELECTOR)?[{trigger:"change"}]:[{trigger:"click"}]}function cancelPolling(n){getInternalData(n).cancelled=!0}function processPolling(n,e,t){const r=getInternalData(n);r.timeout=getWindow().setTimeout(function(){bodyContains(n)&&r.cancelled!==!0&&(maybeFilterEvent(t,n,makeEvent("hx:poll:trigger",{triggerSpec:t,target:n}))||e(n),processPolling(n,e,t))},t.pollInterval)}function isLocalLink(n){return location.hostname===n.hostname&&getRawAttribute(n,"href")&&getRawAttribute(n,"href").indexOf("#")!==0}function eltIsDisabled(n){return closest(n,htmx.config.disableSelector)}function boostElement(n,e,t){if(n instanceof HTMLAnchorElement&&isLocalLink(n)&&(n.target===""||n.target==="_self")||n.tagName==="FORM"&&String(getRawAttribute(n,"method")).toLowerCase()!=="dialog"){e.boosted=!0;let r,a;if(n.tagName==="A")r="get",a=getRawAttribute(n,"href");else{const o=getRawAttribute(n,"method");r=o?o.toLowerCase():"get",a=getRawAttribute(n,"action"),(a==null||a==="")&&(a=location.href),r==="get"&&a.includes("?")&&(a=a.replace(/\?[^#]+/,""))}t.forEach(function(o){addEventListener(n,function(s,l){const c=asElement(s);if(eltIsDisabled(c)){cleanUpElement(c);return}issueAjaxRequest(r,a,c,l)},e,o,!0)})}}function shouldCancel(n,e){if(n.type==="submit"&&e.tagName==="FORM")return!0;if(n.type==="click"){const t=e.closest('input[type="submit"], button');if(t&&t.form&&t.type==="submit")return!0;const r=e.closest("a"),a=/^#.+/;if(r&&r.href&&!a.test(r.getAttribute("href")))return!0}return!1}function ignoreBoostedAnchorCtrlClick(n,e){return getInternalData(n).boosted&&n instanceof HTMLAnchorElement&&e.type==="click"&&(e.ctrlKey||e.metaKey)}function maybeFilterEvent(n,e,t){const r=n.eventFilter;if(r)try{return r.call(e,t)!==!0}catch(a){const o=r.source;return triggerErrorEvent(getDocument().body,"htmx:eventFilter:error",{error:a,source:o}),!0}return!1}function addEventListener(n,e,t,r,a){const o=getInternalData(n);let s;r.from?s=querySelectorAllExt(n,r.from):s=[n],r.changed&&("lastValue"in o||(o.lastValue=new WeakMap),s.forEach(function(l){o.lastValue.has(r)||o.lastValue.set(r,new WeakMap),o.lastValue.get(r).set(l,l.value)})),forEach(s,function(l){const c=function(f){if(!bodyContains(n)){l.removeEventListener(r.trigger,c);return}if(ignoreBoostedAnchorCtrlClick(n,f)||((a||shouldCancel(f,l))&&f.preventDefault(),maybeFilterEvent(r,n,f)))return;const d=getInternalData(f);if(d.triggerSpec=r,d.handledFor==null&&(d.handledFor=[]),d.handledFor.indexOf(n)<0){if(d.handledFor.push(n),r.consume&&f.stopPropagation(),r.target&&f.target&&!matches(asElement(f.target),r.target))return;if(r.once){if(o.triggeredOnce)return;o.triggeredOnce=!0}if(r.changed){const p=f.target,_=p.value,b=o.lastValue.get(r);if(b.has(p)&&b.get(p)===_)return;b.set(p,_)}if(o.delayed&&clearTimeout(o.delayed),o.throttle)return;r.throttle>0?o.throttle||(triggerEvent(n,"htmx:trigger"),e(n,f),o.throttle=getWindow().setTimeout(function(){o.throttle=null},r.throttle)):r.delay>0?o.delayed=getWindow().setTimeout(function(){triggerEvent(n,"htmx:trigger"),e(n,f)},r.delay):(triggerEvent(n,"htmx:trigger"),e(n,f))}};t.listenerInfos==null&&(t.listenerInfos=[]),t.listenerInfos.push({trigger:r.trigger,listener:c,on:l}),l.addEventListener(r.trigger,c)})}let windowIsScrolling=!1,scrollHandler=null;function initScrollHandler(){scrollHandler||(scrollHandler=function(){windowIsScrolling=!0},window.addEventListener("scroll",scrollHandler),window.addEventListener("resize",scrollHandler),setInterval(function(){windowIsScrolling&&(windowIsScrolling=!1,forEach(getDocument().querySelectorAll("[hx-trigger*='revealed'],[data-hx-trigger*='revealed']"),function(n){maybeReveal(n)}))},200))}function maybeReveal(n){!hasAttribute(n,"data-hx-revealed")&&isScrolledIntoView(n)&&(n.setAttribute("data-hx-revealed","true"),getInternalData(n).initHash?triggerEvent(n,"revealed"):n.addEventListener("htmx:afterProcessNode",function(){triggerEvent(n,"revealed")},{once:!0}))}function loadImmediately(n,e,t,r){const a=function(){t.loaded||(t.loaded=!0,triggerEvent(n,"htmx:trigger"),e(n))};r>0?getWindow().setTimeout(a,r):a()}function processVerbs(n,e,t){let r=!1;return forEach(VERBS,function(a){if(hasAttribute(n,"hx-"+a)){const o=getAttributeValue(n,"hx-"+a);r=!0,e.path=o,e.verb=a,t.forEach(function(s){addTriggerHandler(n,s,e,function(l,c){const f=asElement(l);if(eltIsDisabled(f)){cleanUpElement(f);return}issueAjaxRequest(a,o,f,c)})})}}),r}function addTriggerHandler(n,e,t,r){if(e.trigger==="revealed")initScrollHandler(),addEventListener(n,r,t,e),maybeReveal(asElement(n));else if(e.trigger==="intersect"){const a={};e.root&&(a.root=querySelectorExt(n,e.root)),e.threshold&&(a.threshold=parseFloat(e.threshold)),new IntersectionObserver(function(s){for(let l=0;l<s.length;l++)if(s[l].isIntersecting){triggerEvent(n,"intersect");break}},a).observe(asElement(n)),addEventListener(asElement(n),r,t,e)}else!t.firstInitCompleted&&e.trigger==="load"?maybeFilterEvent(e,n,makeEvent("load",{elt:n}))||loadImmediately(asElement(n),r,t,e.delay):e.pollInterval>0?(t.polling=!0,processPolling(asElement(n),r,e)):addEventListener(n,r,t,e)}function shouldProcessHxOn(n){const e=asElement(n);if(!e)return!1;const t=e.attributes;for(let r=0;r<t.length;r++){const a=t[r].name;if(startsWith(a,"hx-on:")||startsWith(a,"data-hx-on:")||startsWith(a,"hx-on-")||startsWith(a,"data-hx-on-"))return!0}return!1}const HX_ON_QUERY=new XPathEvaluator().createExpression('.//*[@*[ starts-with(name(), "hx-on:") or starts-with(name(), "data-hx-on:") or starts-with(name(), "hx-on-") or starts-with(name(), "data-hx-on-") ]]');function processHXOnRoot(n,e){shouldProcessHxOn(n)&&e.push(asElement(n));const t=HX_ON_QUERY.evaluate(n);let r=null;for(;r=t.iterateNext();)e.push(asElement(r))}function findHxOnWildcardElements(n){const e=[];if(n instanceof DocumentFragment)for(const t of n.childNodes)processHXOnRoot(t,e);else processHXOnRoot(n,e);return e}function findElementsToProcess(n){if(n.querySelectorAll){const t=", [hx-boost] a, [data-hx-boost] a, a[hx-boost], a[data-hx-boost]",r=[];for(const o in extensions){const s=extensions[o];if(s.getSelectors){var e=s.getSelectors();e&&r.push(e)}}return n.querySelectorAll(VERB_SELECTOR+t+", form, [type='submit'], [hx-ext], [data-hx-ext], [hx-trigger], [data-hx-trigger]"+r.flat().map(o=>", "+o).join(""))}else return[]}function maybeSetLastButtonClicked(n){const e=getTargetButton(n.target),t=getRelatedFormData(n);t&&(t.lastButtonClicked=e)}function maybeUnsetLastButtonClicked(n){const e=getRelatedFormData(n);e&&(e.lastButtonClicked=null)}function getTargetButton(n){return closest(asElement(n),"button, input[type='submit']")}function getRelatedForm(n){return n.form||closest(n,"form")}function getRelatedFormData(n){const e=getTargetButton(n.target);if(!e)return;const t=getRelatedForm(e);if(t)return getInternalData(t)}function initButtonTracking(n){n.addEventListener("click",maybeSetLastButtonClicked),n.addEventListener("focusin",maybeSetLastButtonClicked),n.addEventListener("focusout",maybeUnsetLastButtonClicked)}function addHxOnEventHandler(n,e,t){const r=getInternalData(n);Array.isArray(r.onHandlers)||(r.onHandlers=[]);let a;const o=function(s){maybeEval(n,function(){eltIsDisabled(n)||(a||(a=new Function("event",t)),a.call(n,s))})};n.addEventListener(e,o),r.onHandlers.push({event:e,listener:o})}function processHxOnWildcard(n){deInitOnHandlers(n);for(let e=0;e<n.attributes.length;e++){const t=n.attributes[e].name,r=n.attributes[e].value;if(startsWith(t,"hx-on")||startsWith(t,"data-hx-on")){const a=t.indexOf("-on")+3,o=t.slice(a,a+1);if(o==="-"||o===":"){let s=t.slice(a+1);startsWith(s,":")?s="htmx"+s:startsWith(s,"-")?s="htmx:"+s.slice(1):startsWith(s,"htmx-")&&(s="htmx:"+s.slice(5)),addHxOnEventHandler(n,s,r)}}}}function initNode(n){triggerEvent(n,"htmx:beforeProcessNode");const e=getInternalData(n),t=getTriggerSpecs(n);processVerbs(n,e,t)||(getClosestAttributeValue(n,"hx-boost")==="true"?boostElement(n,e,t):hasAttribute(n,"hx-trigger")&&t.forEach(function(a){addTriggerHandler(n,a,e,function(){})})),(n.tagName==="FORM"||getRawAttribute(n,"type")==="submit"&&hasAttribute(n,"form"))&&initButtonTracking(n),e.firstInitCompleted=!0,triggerEvent(n,"htmx:afterProcessNode")}function maybeDeInitAndHash(n){if(!(n instanceof Element))return!1;const e=getInternalData(n),t=attributeHash(n);return e.initHash!==t?(deInitNode(n),e.initHash=t,!0):!1}function processNode(n){if(n=resolveTarget(n),eltIsDisabled(n)){cleanUpElement(n);return}const e=[];maybeDeInitAndHash(n)&&e.push(n),forEach(findElementsToProcess(n),function(t){if(eltIsDisabled(t)){cleanUpElement(t);return}maybeDeInitAndHash(t)&&e.push(t)}),forEach(findHxOnWildcardElements(n),processHxOnWildcard),forEach(e,initNode)}function kebabEventName(n){return n.replace(/([a-z0-9])([A-Z])/g,"$1-$2").toLowerCase()}function makeEvent(n,e){return new CustomEvent(n,{bubbles:!0,cancelable:!0,composed:!0,detail:e})}function triggerErrorEvent(n,e,t){triggerEvent(n,e,mergeObjects({error:e},t))}function ignoreEventForLogging(n){return n==="htmx:afterProcessNode"}function withExtensions(n,e,t){forEach(getExtensions(n,[],t),function(r){try{e(r)}catch(a){logError(a)}})}function logError(n){console.error(n)}function triggerEvent(n,e,t){n=resolveTarget(n),t==null&&(t={}),t.elt=n;const r=makeEvent(e,t);htmx.logger&&!ignoreEventForLogging(e)&&htmx.logger(n,e,t),t.error&&(logError(t.error+(t.target?", "+t.target:"")),triggerEvent(n,"htmx:error",{errorInfo:t}));let a=n.dispatchEvent(r);const o=kebabEventName(e);if(a&&o!==e){const s=makeEvent(o,r.detail);a=a&&n.dispatchEvent(s)}return withExtensions(asElement(n),function(s){a=a&&s.onEvent(e,r)!==!1&&!r.defaultPrevented}),a}let currentPathForHistory;function setCurrentPathForHistory(n){currentPathForHistory=n,canAccessLocalStorage()&&sessionStorage.setItem("htmx-current-path-for-history",n)}setCurrentPathForHistory(location.pathname+location.search);function getHistoryElement(){return getDocument().querySelector("[hx-history-elt],[data-hx-history-elt]")||getDocument().body}function saveToHistoryCache(n,e){if(!canAccessLocalStorage())return;const t=cleanInnerHtmlForHistory(e),r=getDocument().title,a=window.scrollY;if(htmx.config.historyCacheSize<=0){sessionStorage.removeItem("htmx-history-cache");return}n=normalizePath(n);const o=parseJSON(sessionStorage.getItem("htmx-history-cache"))||[];for(let l=0;l<o.length;l++)if(o[l].url===n){o.splice(l,1);break}const s={url:n,content:t,title:r,scroll:a};for(triggerEvent(getDocument().body,"htmx:historyItemCreated",{item:s,cache:o}),o.push(s);o.length>htmx.config.historyCacheSize;)o.shift();for(;o.length>0;)try{sessionStorage.setItem("htmx-history-cache",JSON.stringify(o));break}catch(l){triggerErrorEvent(getDocument().body,"htmx:historyCacheError",{cause:l,cache:o}),o.shift()}}function getCachedHistory(n){if(!canAccessLocalStorage())return null;n=normalizePath(n);const e=parseJSON(sessionStorage.getItem("htmx-history-cache"))||[];for(let t=0;t<e.length;t++)if(e[t].url===n)return e[t];return null}function cleanInnerHtmlForHistory(n){const e=htmx.config.requestClass,t=n.cloneNode(!0);return forEach(findAll(t,"."+e),function(r){removeClassFromElement(r,e)}),forEach(findAll(t,"[data-disabled-by-htmx]"),function(r){r.removeAttribute("disabled")}),t.innerHTML}function saveCurrentPageToHistory(){const n=getHistoryElement();let e=currentPathForHistory;canAccessLocalStorage()&&(e=sessionStorage.getItem("htmx-current-path-for-history")),e=e||location.pathname+location.search,getDocument().querySelector('[hx-history="false" i],[data-hx-history="false" i]')||(triggerEvent(getDocument().body,"htmx:beforeHistorySave",{path:e,historyElt:n}),saveToHistoryCache(e,n)),htmx.config.historyEnabled&&history.replaceState({htmx:!0},getDocument().title,location.href)}function pushUrlIntoHistory(n){htmx.config.getCacheBusterParam&&(n=n.replace(/org\.htmx\.cache-buster=[^&]*&?/,""),(endsWith(n,"&")||endsWith(n,"?"))&&(n=n.slice(0,-1))),htmx.config.historyEnabled&&history.pushState({htmx:!0},"",n),setCurrentPathForHistory(n)}function replaceUrlInHistory(n){htmx.config.historyEnabled&&history.replaceState({htmx:!0},"",n),setCurrentPathForHistory(n)}function settleImmediately(n){forEach(n,function(e){e.call(void 0)})}function loadHistoryFromServer(n){const e=new XMLHttpRequest,t={swapStyle:"innerHTML",swapDelay:0,settleDelay:0},r={path:n,xhr:e,historyElt:getHistoryElement(),swapSpec:t};e.open("GET",n,!0),htmx.config.historyRestoreAsHxRequest&&e.setRequestHeader("HX-Request","true"),e.setRequestHeader("HX-History-Restore-Request","true"),e.setRequestHeader("HX-Current-URL",location.href),e.onload=function(){this.status>=200&&this.status<400?(r.response=this.response,triggerEvent(getDocument().body,"htmx:historyCacheMissLoad",r),swap(r.historyElt,r.response,t,{contextElement:r.historyElt,historyRequest:!0}),setCurrentPathForHistory(r.path),triggerEvent(getDocument().body,"htmx:historyRestore",{path:n,cacheMiss:!0,serverResponse:r.response})):triggerErrorEvent(getDocument().body,"htmx:historyCacheMissLoadError",r)},triggerEvent(getDocument().body,"htmx:historyCacheMiss",r)&&e.send()}function restoreHistory(n){saveCurrentPageToHistory(),n=n||location.pathname+location.search;const e=getCachedHistory(n);if(e){const t={swapStyle:"innerHTML",swapDelay:0,settleDelay:0,scroll:e.scroll},r={path:n,item:e,historyElt:getHistoryElement(),swapSpec:t};triggerEvent(getDocument().body,"htmx:historyCacheHit",r)&&(swap(r.historyElt,e.content,t,{contextElement:r.historyElt,title:e.title}),setCurrentPathForHistory(r.path),triggerEvent(getDocument().body,"htmx:historyRestore",r))}else htmx.config.refreshOnHistoryMiss?htmx.location.reload(!0):loadHistoryFromServer(n)}function addRequestIndicatorClasses(n){let e=findAttributeTargets(n,"hx-indicator");return e==null&&(e=[n]),forEach(e,function(t){const r=getInternalData(t);r.requestCount=(r.requestCount||0)+1,addClassToElement(t,htmx.config.requestClass)}),e}function disableElements(n){let e=findAttributeTargets(n,"hx-disabled-elt");return e==null&&(e=[]),forEach(e,function(t){const r=getInternalData(t);r.requestCount=(r.requestCount||0)+1,t.hasAttribute("disabled")||(t.setAttribute("disabled",""),t.setAttribute("data-disabled-by-htmx",""))}),e}function removeRequestIndicators(n,e){forEach(n.concat(e),function(t){const r=getInternalData(t);r.requestCount=(r.requestCount||1)-1}),forEach(n,function(t){getInternalData(t).requestCount===0&&removeClassFromElement(t,htmx.config.requestClass)}),forEach(e,function(t){getInternalData(t).requestCount===0&&t.hasAttribute("data-disabled-by-htmx")&&(t.removeAttribute("disabled"),t.removeAttribute("data-disabled-by-htmx"))})}function haveSeenNode(n,e){for(let t=0;t<n.length;t++)if(n[t].isSameNode(e))return!0;return!1}function shouldInclude(n){const e=n;return e.name===""||e.name==null||e.disabled||closest(e,"fieldset[disabled]")||e.type==="button"||e.type==="submit"||e.tagName==="image"||e.tagName==="reset"||e.tagName==="file"?!1:e.type==="checkbox"||e.type==="radio"?e.checked:!0}function addValueToFormData(n,e,t){n!=null&&e!=null&&(Array.isArray(e)?e.forEach(function(r){t.append(n,r)}):t.append(n,e))}function removeValueFromFormData(n,e,t){if(n!=null&&e!=null){let r=t.getAll(n);Array.isArray(e)?r=r.filter(a=>e.indexOf(a)<0):r=r.filter(a=>a!==e),t.delete(n),forEach(r,a=>t.append(n,a))}}function getValueFromInput(n){return n instanceof HTMLSelectElement&&n.multiple?toArray(n.querySelectorAll("option:checked")).map(function(e){return e.value}):n instanceof HTMLInputElement&&n.files?toArray(n.files):n.value}function processInputValue(n,e,t,r,a){if(!(r==null||haveSeenNode(n,r))){if(n.push(r),shouldInclude(r)){const o=getRawAttribute(r,"name");addValueToFormData(o,getValueFromInput(r),e),a&&validateElement(r,t)}r instanceof HTMLFormElement&&(forEach(r.elements,function(o){n.indexOf(o)>=0?removeValueFromFormData(o.name,getValueFromInput(o),e):n.push(o),a&&validateElement(o,t)}),new FormData(r).forEach(function(o,s){o instanceof File&&o.name===""||addValueToFormData(s,o,e)}))}}function validateElement(n,e){const t=n;t.willValidate&&(triggerEvent(t,"htmx:validation:validate"),t.checkValidity()||(triggerEvent(t,"htmx:validation:failed",{message:t.validationMessage,validity:t.validity})&&!e.length&&htmx.config.reportValidityOfForms&&t.reportValidity(),e.push({elt:t,message:t.validationMessage,validity:t.validity})))}function overrideFormData(n,e){for(const t of e.keys())n.delete(t);return e.forEach(function(t,r){n.append(r,t)}),n}function getInputValues(n,e){const t=[],r=new FormData,a=new FormData,o=[],s=getInternalData(n);s.lastButtonClicked&&!bodyContains(s.lastButtonClicked)&&(s.lastButtonClicked=null);let l=n instanceof HTMLFormElement&&n.noValidate!==!0||getAttributeValue(n,"hx-validate")==="true";if(s.lastButtonClicked&&(l=l&&s.lastButtonClicked.formNoValidate!==!0),e!=="get"&&processInputValue(t,a,o,getRelatedForm(n),l),processInputValue(t,r,o,n,l),s.lastButtonClicked||n.tagName==="BUTTON"||n.tagName==="INPUT"&&getRawAttribute(n,"type")==="submit"){const f=s.lastButtonClicked||n,d=getRawAttribute(f,"name");addValueToFormData(d,f.value,a)}const c=findAttributeTargets(n,"hx-include");return forEach(c,function(f){processInputValue(t,r,o,asElement(f),l),matches(f,"form")||forEach(asParentNode(f).querySelectorAll(INPUT_SELECTOR),function(d){processInputValue(t,r,o,d,l)})}),overrideFormData(r,a),{errors:o,formData:r,values:formDataProxy(r)}}function appendParam(n,e,t){n!==""&&(n+="&"),String(t)==="[object Object]"&&(t=JSON.stringify(t));const r=encodeURIComponent(t);return n+=encodeURIComponent(e)+"="+r,n}function urlEncode(n){n=formDataFromObject(n);let e="";return n.forEach(function(t,r){e=appendParam(e,r,t)}),e}function getHeaders(n,e,t){const r={"HX-Request":"true","HX-Trigger":getRawAttribute(n,"id"),"HX-Trigger-Name":getRawAttribute(n,"name"),"HX-Target":getAttributeValue(e,"id"),"HX-Current-URL":location.href};return getValuesForElement(n,"hx-headers",!1,r),t!==void 0&&(r["HX-Prompt"]=t),getInternalData(n).boosted&&(r["HX-Boosted"]="true"),r}function filterValues(n,e){const t=getClosestAttributeValue(e,"hx-params");if(t){if(t==="none")return new FormData;if(t==="*")return n;if(t.indexOf("not ")===0)return forEach(t.slice(4).split(","),function(r){r=r.trim(),n.delete(r)}),n;{const r=new FormData;return forEach(t.split(","),function(a){a=a.trim(),n.has(a)&&n.getAll(a).forEach(function(o){r.append(a,o)})}),r}}else return n}function isAnchorLink(n){return!!getRawAttribute(n,"href")&&getRawAttribute(n,"href").indexOf("#")>=0}function getSwapSpecification(n,e){const t=e||getClosestAttributeValue(n,"hx-swap"),r={swapStyle:getInternalData(n).boosted?"innerHTML":htmx.config.defaultSwapStyle,swapDelay:htmx.config.defaultSwapDelay,settleDelay:htmx.config.defaultSettleDelay};if(htmx.config.scrollIntoViewOnBoost&&getInternalData(n).boosted&&!isAnchorLink(n)&&(r.show="top"),t){const s=splitOnWhitespace(t);if(s.length>0)for(let l=0;l<s.length;l++){const c=s[l];if(c.indexOf("swap:")===0)r.swapDelay=parseInterval(c.slice(5));else if(c.indexOf("settle:")===0)r.settleDelay=parseInterval(c.slice(7));else if(c.indexOf("transition:")===0)r.transition=c.slice(11)==="true";else if(c.indexOf("ignoreTitle:")===0)r.ignoreTitle=c.slice(12)==="true";else if(c.indexOf("scroll:")===0){var a=c.slice(7).split(":");const d=a.pop();var o=a.length>0?a.join(":"):null;r.scroll=d,r.scrollTarget=o}else if(c.indexOf("show:")===0){var a=c.slice(5).split(":");const p=a.pop();var o=a.length>0?a.join(":"):null;r.show=p,r.showTarget=o}else if(c.indexOf("focus-scroll:")===0){const f=c.slice(13);r.focusScroll=f=="true"}else l==0?r.swapStyle=c:logError("Unknown modifier in hx-swap: "+c)}}return r}function usesFormData(n){return getClosestAttributeValue(n,"hx-encoding")==="multipart/form-data"||matches(n,"form")&&getRawAttribute(n,"enctype")==="multipart/form-data"}function encodeParamsForBody(n,e,t){let r=null;return withExtensions(e,function(a){r==null&&(r=a.encodeParameters(n,t,e))}),r??(usesFormData(e)?overrideFormData(new FormData,formDataFromObject(t)):urlEncode(t))}function makeSettleInfo(n){return{tasks:[],elts:[n]}}function updateScrollState(n,e){const t=n[0],r=n[n.length-1];if(e.scroll){var a=null;e.scrollTarget&&(a=asElement(querySelectorExt(t,e.scrollTarget))),e.scroll==="top"&&(t||a)&&(a=a||t,a.scrollTop=0),e.scroll==="bottom"&&(r||a)&&(a=a||r,a.scrollTop=a.scrollHeight),typeof e.scroll=="number"&&getWindow().setTimeout(function(){window.scrollTo(0,e.scroll)},0)}if(e.show){var a=null;if(e.showTarget){let s=e.showTarget;e.showTarget==="window"&&(s="body"),a=asElement(querySelectorExt(t,s))}e.show==="top"&&(t||a)&&(a=a||t,a.scrollIntoView({block:"start",behavior:htmx.config.scrollBehavior})),e.show==="bottom"&&(r||a)&&(a=a||r,a.scrollIntoView({block:"end",behavior:htmx.config.scrollBehavior}))}}function getValuesForElement(n,e,t,r,a){if(r==null&&(r={}),n==null)return r;const o=getAttributeValue(n,e);if(o){let s=o.trim(),l=t;if(s==="unset")return null;s.indexOf("javascript:")===0?(s=s.slice(11),l=!0):s.indexOf("js:")===0&&(s=s.slice(3),l=!0),s.indexOf("{")!==0&&(s="{"+s+"}");let c;l?c=maybeEval(n,function(){return a?Function("event","return ("+s+")").call(n,a):Function("return ("+s+")").call(n)},{}):c=parseJSON(s);for(const f in c)c.hasOwnProperty(f)&&r[f]==null&&(r[f]=c[f])}return getValuesForElement(asElement(parentElt(n)),e,t,r,a)}function maybeEval(n,e,t){return htmx.config.allowEval?e():(triggerErrorEvent(n,"htmx:evalDisallowedError"),t)}function getHXVarsForElement(n,e,t){return getValuesForElement(n,"hx-vars",!0,t,e)}function getHXValsForElement(n,e,t){return getValuesForElement(n,"hx-vals",!1,t,e)}function getExpressionVars(n,e){return mergeObjects(getHXVarsForElement(n,e),getHXValsForElement(n,e))}function safelySetHeaderValue(n,e,t){if(t!==null)try{n.setRequestHeader(e,t)}catch{n.setRequestHeader(e,encodeURIComponent(t)),n.setRequestHeader(e+"-URI-AutoEncoded","true")}}function getPathFromResponse(n){if(n.responseURL)try{const e=new URL(n.responseURL);return e.pathname+e.search}catch{triggerErrorEvent(getDocument().body,"htmx:badResponseUrl",{url:n.responseURL})}}function hasHeader(n,e){return e.test(n.getAllResponseHeaders())}function ajaxHelper(n,e,t){if(n=n.toLowerCase(),t){if(t instanceof Element||typeof t=="string")return issueAjaxRequest(n,e,null,null,{targetOverride:resolveTarget(t)||DUMMY_ELT,returnPromise:!0});{let r=resolveTarget(t.target);return(t.target&&!r||t.source&&!r&&!resolveTarget(t.source))&&(r=DUMMY_ELT),issueAjaxRequest(n,e,resolveTarget(t.source),t.event,{handler:t.handler,headers:t.headers,values:t.values,targetOverride:r,swapOverride:t.swap,select:t.select,returnPromise:!0,push:t.push,replace:t.replace,selectOOB:t.selectOOB})}}else return issueAjaxRequest(n,e,null,null,{returnPromise:!0})}function hierarchyForElt(n){const e=[];for(;n;)e.push(n),n=n.parentElement;return e}function verifyPath(n,e,t){const r=new URL(e,location.protocol!=="about:"?location.href:window.origin),o=(location.protocol!=="about:"?location.origin:window.origin)===r.origin;return htmx.config.selfRequestsOnly&&!o?!1:triggerEvent(n,"htmx:validateUrl",mergeObjects({url:r,sameHost:o},t))}function formDataFromObject(n){if(n instanceof FormData)return n;const e=new FormData;for(const t in n)n.hasOwnProperty(t)&&(n[t]&&typeof n[t].forEach=="function"?n[t].forEach(function(r){e.append(t,r)}):typeof n[t]=="object"&&!(n[t]instanceof Blob)?e.append(t,JSON.stringify(n[t])):e.append(t,n[t]));return e}function formDataArrayProxy(n,e,t){return new Proxy(t,{get:function(r,a){return typeof a=="number"?r[a]:a==="length"?r.length:a==="push"?function(o){r.push(o),n.append(e,o)}:typeof r[a]=="function"?function(){r[a].apply(r,arguments),n.delete(e),r.forEach(function(o){n.append(e,o)})}:r[a]&&r[a].length===1?r[a][0]:r[a]},set:function(r,a,o){return r[a]=o,n.delete(e),r.forEach(function(s){n.append(e,s)}),!0}})}function formDataProxy(n){return new Proxy(n,{get:function(e,t){if(typeof t=="symbol"){const a=Reflect.get(e,t);return typeof a=="function"?function(){return a.apply(n,arguments)}:a}if(t==="toJSON")return()=>Object.fromEntries(n);if(t in e&&typeof e[t]=="function")return function(){return n[t].apply(n,arguments)};const r=n.getAll(t);if(r.length!==0)return r.length===1?r[0]:formDataArrayProxy(e,t,r)},set:function(e,t,r){return typeof t!="string"?!1:(e.delete(t),r&&typeof r.forEach=="function"?r.forEach(function(a){e.append(t,a)}):typeof r=="object"&&!(r instanceof Blob)?e.append(t,JSON.stringify(r)):e.append(t,r),!0)},deleteProperty:function(e,t){return typeof t=="string"&&e.delete(t),!0},ownKeys:function(e){return Reflect.ownKeys(Object.fromEntries(e))},getOwnPropertyDescriptor:function(e,t){return Reflect.getOwnPropertyDescriptor(Object.fromEntries(e),t)}})}function issueAjaxRequest(n,e,t,r,a,o){let s=null,l=null;if(a=a??{},a.returnPromise&&typeof Promise<"u")var c=new Promise(function(ge,Me){s=ge,l=Me});t==null&&(t=getDocument().body);const f=a.handler||handleAjaxResponse,d=a.select||null;if(!bodyContains(t))return maybeCall(s),c;const p=a.targetOverride||asElement(getTarget(t));if(p==null||p==DUMMY_ELT)return triggerErrorEvent(t,"htmx:targetError",{target:getClosestAttributeValue(t,"hx-target")}),maybeCall(l),c;let _=getInternalData(t);const b=_.lastButtonClicked;if(b){const ge=getRawAttribute(b,"formaction");ge!=null&&(e=ge);const Me=getRawAttribute(b,"formmethod");if(Me!=null)if(VERBS.includes(Me.toLowerCase()))n=Me;else return maybeCall(s),c}const y=getClosestAttributeValue(t,"hx-confirm");if(o===void 0&&triggerEvent(t,"htmx:confirm",{target:p,elt:t,path:e,verb:n,triggeringEvent:r,etc:a,issueRequest:function(Pe){return issueAjaxRequest(n,e,t,r,a,!!Pe)},question:y})===!1)return maybeCall(s),c;let E=t,C=getClosestAttributeValue(t,"hx-sync"),D=null,M=!1;if(C){const ge=C.split(":"),Me=ge[0].trim();if(Me==="this"?E=findThisElement(t,"hx-sync"):E=asElement(querySelectorExt(t,Me)),C=(ge[1]||"drop").trim(),_=getInternalData(E),C==="drop"&&_.xhr&&_.abortable!==!0)return maybeCall(s),c;if(C==="abort"){if(_.xhr)return maybeCall(s),c;M=!0}else C==="replace"?triggerEvent(E,"htmx:abort"):C.indexOf("queue")===0&&(D=(C.split(" ")[1]||"last").trim())}if(_.xhr)if(_.abortable)triggerEvent(E,"htmx:abort");else{if(D==null){if(r){const ge=getInternalData(r);ge&&ge.triggerSpec&&ge.triggerSpec.queue&&(D=ge.triggerSpec.queue)}D==null&&(D="last")}return _.queuedRequests==null&&(_.queuedRequests=[]),D==="first"&&_.queuedRequests.length===0?_.queuedRequests.push(function(){issueAjaxRequest(n,e,t,r,a)}):D==="all"?_.queuedRequests.push(function(){issueAjaxRequest(n,e,t,r,a)}):D==="last"&&(_.queuedRequests=[],_.queuedRequests.push(function(){issueAjaxRequest(n,e,t,r,a)})),maybeCall(s),c}const F=new XMLHttpRequest;_.xhr=F,_.abortable=M;const P=function(){_.xhr=null,_.abortable=!1,_.queuedRequests!=null&&_.queuedRequests.length>0&&_.queuedRequests.shift()()},H=getClosestAttributeValue(t,"hx-prompt");if(H){var B=prompt(H);if(B===null||!triggerEvent(t,"htmx:prompt",{prompt:B,target:p}))return maybeCall(s),P(),c}if(y&&!o&&!confirm(y))return maybeCall(s),P(),c;let g=getHeaders(t,p,B);n!=="get"&&!usesFormData(t)&&(g["Content-Type"]="application/x-www-form-urlencoded"),a.headers&&(g=mergeObjects(g,a.headers));const q=getInputValues(t,n);let G=q.errors;const Z=q.formData;a.values&&overrideFormData(Z,formDataFromObject(a.values));const te=formDataFromObject(getExpressionVars(t,r)),ne=overrideFormData(Z,te);let Q=filterValues(ne,t);htmx.config.getCacheBusterParam&&n==="get"&&Q.set("org.htmx.cache-buster",getRawAttribute(p,"id")||"true"),(e==null||e==="")&&(e=location.href);const Ee=getValuesForElement(t,"hx-request"),re=getInternalData(t).boosted;let de=htmx.config.methodsThatUseUrlParams.indexOf(n)>=0;const le={boosted:re,useUrlParams:de,formData:Q,parameters:formDataProxy(Q),unfilteredFormData:ne,unfilteredParameters:formDataProxy(ne),headers:g,elt:t,target:p,verb:n,errors:G,withCredentials:a.credentials||Ee.credentials||htmx.config.withCredentials,timeout:a.timeout||Ee.timeout||htmx.config.timeout,path:e,triggeringEvent:r};if(!triggerEvent(t,"htmx:configRequest",le))return maybeCall(s),P(),c;if(e=le.path,n=le.verb,g=le.headers,Q=formDataFromObject(le.parameters),G=le.errors,de=le.useUrlParams,G&&G.length>0)return triggerEvent(t,"htmx:validation:halted",le),maybeCall(s),P(),c;const $e=e.split("#"),xe=$e[0],Ve=$e[1];let Re=e;if(de&&(Re=xe,!Q.keys().next().done&&(Re.indexOf("?")<0?Re+="?":Re+="&",Re+=urlEncode(Q),Ve&&(Re+="#"+Ve))),!verifyPath(t,Re,le))return triggerErrorEvent(t,"htmx:invalidPath",le),maybeCall(l),P(),c;if(F.open(n.toUpperCase(),Re,!0),F.overrideMimeType("text/html"),F.withCredentials=le.withCredentials,F.timeout=le.timeout,!Ee.noHeaders){for(const ge in g)if(g.hasOwnProperty(ge)){const Me=g[ge];safelySetHeaderValue(F,ge,Me)}}const Te={xhr:F,target:p,requestConfig:le,etc:a,boosted:re,select:d,pathInfo:{requestPath:e,finalRequestPath:Re,responsePath:null,anchor:Ve}};if(F.onload=function(){try{const ge=hierarchyForElt(t);if(Te.pathInfo.responsePath=getPathFromResponse(F),f(t,Te),Te.keepIndicators!==!0&&removeRequestIndicators(je,Fe),triggerEvent(t,"htmx:afterRequest",Te),triggerEvent(t,"htmx:afterOnLoad",Te),!bodyContains(t)){let Me=null;for(;ge.length>0&&Me==null;){const Pe=ge.shift();bodyContains(Pe)&&(Me=Pe)}Me&&(triggerEvent(Me,"htmx:afterRequest",Te),triggerEvent(Me,"htmx:afterOnLoad",Te))}maybeCall(s)}catch(ge){throw triggerErrorEvent(t,"htmx:onLoadError",mergeObjects({error:ge},Te)),ge}finally{P()}},F.onerror=function(){removeRequestIndicators(je,Fe),triggerErrorEvent(t,"htmx:afterRequest",Te),triggerErrorEvent(t,"htmx:sendError",Te),maybeCall(l),P()},F.onabort=function(){removeRequestIndicators(je,Fe),triggerErrorEvent(t,"htmx:afterRequest",Te),triggerErrorEvent(t,"htmx:sendAbort",Te),maybeCall(l),P()},F.ontimeout=function(){removeRequestIndicators(je,Fe),triggerErrorEvent(t,"htmx:afterRequest",Te),triggerErrorEvent(t,"htmx:timeout",Te),maybeCall(l),P()},!triggerEvent(t,"htmx:beforeRequest",Te))return maybeCall(s),P(),c;var je=addRequestIndicatorClasses(t),Fe=disableElements(t);forEach(["loadstart","loadend","progress","abort"],function(ge){forEach([F,F.upload],function(Me){Me.addEventListener(ge,function(Pe){triggerEvent(t,"htmx:xhr:"+ge,{lengthComputable:Pe.lengthComputable,loaded:Pe.loaded,total:Pe.total})})})}),triggerEvent(t,"htmx:beforeSend",Te);const He=de?null:encodeParamsForBody(F,t,Q);return F.send(He),c}function determineHistoryUpdates(n,e){const t=e.xhr;let r=null,a=null;if(hasHeader(t,/HX-Push:/i)?(r=t.getResponseHeader("HX-Push"),a="push"):hasHeader(t,/HX-Push-Url:/i)?(r=t.getResponseHeader("HX-Push-Url"),a="push"):hasHeader(t,/HX-Replace-Url:/i)&&(r=t.getResponseHeader("HX-Replace-Url"),a="replace"),r)return r==="false"?{}:{type:a,path:r};const o=e.pathInfo.finalRequestPath,s=e.pathInfo.responsePath;let l=e.etc.push||getClosestAttributeValue(n,"hx-push-url"),c=e.etc.replace||getClosestAttributeValue(n,"hx-replace-url");l==="false"&&(l=null),c==="false"&&(c=null);const f=getInternalData(n).boosted;let d=null,p=null;return l?(d="push",p=l):c?(d="replace",p=c):f&&(d="push",p=s||o),p?(p==="true"&&(p=s||o),e.pathInfo.anchor&&p.indexOf("#")===-1&&(p=p+"#"+e.pathInfo.anchor),{type:d,path:p}):{}}function codeMatches(n,e){var t=new RegExp(n.code);return t.test(e.toString(10))}function resolveResponseHandling(n){for(var e=0;e<htmx.config.responseHandling.length;e++){var t=htmx.config.responseHandling[e];if(codeMatches(t,n.status))return t}return{swap:!1}}function handleTitle(n){if(n){const e=find("title");e?e.textContent=n:window.document.title=n}}function resolveRetarget(n,e){if(e==="this")return n;const t=asElement(querySelectorExt(n,e));if(t==null)throw triggerErrorEvent(n,"htmx:targetError",{target:e}),new Error(`Invalid re-target ${e}`);return t}function handleAjaxResponse(n,e){const t=e.xhr;let r=e.target;const a=e.etc,o=e.select;if(!triggerEvent(n,"htmx:beforeOnLoad",e))return;if(hasHeader(t,/HX-Trigger:/i)&&handleTriggerHeader(t,"HX-Trigger",n),hasHeader(t,/HX-Location:/i)){let M=t.getResponseHeader("HX-Location");var s={};M.indexOf("{")===0&&(s=parseJSON(M),M=s.path,delete s.path),s.push=s.push??"true",ajaxHelper("get",M,s);return}const l=hasHeader(t,/HX-Refresh:/i)&&t.getResponseHeader("HX-Refresh")==="true";if(hasHeader(t,/HX-Redirect:/i)){e.keepIndicators=!0,htmx.location.href=t.getResponseHeader("HX-Redirect"),l&&htmx.location.reload();return}if(l){e.keepIndicators=!0,htmx.location.reload();return}const c=determineHistoryUpdates(n,e),f=resolveResponseHandling(t),d=f.swap;let p=!!f.error,_=htmx.config.ignoreTitle||f.ignoreTitle,b=f.select;f.target&&(e.target=resolveRetarget(n,f.target));var y=a.swapOverride;y==null&&f.swapOverride&&(y=f.swapOverride),hasHeader(t,/HX-Retarget:/i)&&(e.target=resolveRetarget(n,t.getResponseHeader("HX-Retarget"))),hasHeader(t,/HX-Reswap:/i)&&(y=t.getResponseHeader("HX-Reswap"));var E=t.response,C=mergeObjects({shouldSwap:d,serverResponse:E,isError:p,ignoreTitle:_,selectOverride:b,swapOverride:y},e);if(!(f.event&&!triggerEvent(r,f.event,C))&&triggerEvent(r,"htmx:beforeSwap",C)){if(r=C.target,E=C.serverResponse,p=C.isError,_=C.ignoreTitle,b=C.selectOverride,y=C.swapOverride,e.target=r,e.failed=p,e.successful=!p,C.shouldSwap){t.status===286&&cancelPolling(n),withExtensions(n,function(P){E=P.transformResponse(E,t,n)}),c.type&&saveCurrentPageToHistory();var D=getSwapSpecification(n,y);D.hasOwnProperty("ignoreTitle")||(D.ignoreTitle=_),addClassToElement(r,htmx.config.swappingClass),o&&(b=o),hasHeader(t,/HX-Reselect:/i)&&(b=t.getResponseHeader("HX-Reselect"));const M=a.selectOOB||getClosestAttributeValue(n,"hx-select-oob"),F=getClosestAttributeValue(n,"hx-select");swap(r,E,D,{select:b==="unset"?null:b||F,selectOOB:M,eventInfo:e,anchor:e.pathInfo.anchor,contextElement:n,afterSwapCallback:function(){if(hasHeader(t,/HX-Trigger-After-Swap:/i)){let P=n;bodyContains(n)||(P=getDocument().body),handleTriggerHeader(t,"HX-Trigger-After-Swap",P)}},afterSettleCallback:function(){if(hasHeader(t,/HX-Trigger-After-Settle:/i)){let P=n;bodyContains(n)||(P=getDocument().body),handleTriggerHeader(t,"HX-Trigger-After-Settle",P)}},beforeSwapCallback:function(){c.type&&(triggerEvent(getDocument().body,"htmx:beforeHistoryUpdate",mergeObjects({history:c},e)),c.type==="push"?(pushUrlIntoHistory(c.path),triggerEvent(getDocument().body,"htmx:pushedIntoHistory",{path:c.path})):(replaceUrlInHistory(c.path),triggerEvent(getDocument().body,"htmx:replacedInHistory",{path:c.path})))}})}p&&triggerErrorEvent(n,"htmx:responseError",mergeObjects({error:"Response Status Error Code "+t.status+" from "+e.pathInfo.requestPath},e))}}const extensions={};function extensionBase(){return{init:function(n){return null},getSelectors:function(){return null},onEvent:function(n,e){return!0},transformResponse:function(n,e,t){return n},isInlineSwap:function(n){return!1},handleSwap:function(n,e,t,r){return!1},encodeParameters:function(n,e,t){return null}}}function defineExtension(n,e){e.init&&e.init(internalAPI),extensions[n]=mergeObjects(extensionBase(),e)}function removeExtension(n){delete extensions[n]}function getExtensions(n,e,t){if(e==null&&(e=[]),n==null)return e;t==null&&(t=[]);const r=getAttributeValue(n,"hx-ext");return r&&forEach(r.split(","),function(a){if(a=a.replace(/ /g,""),a.slice(0,7)=="ignore:"){t.push(a.slice(7));return}if(t.indexOf(a)<0){const o=extensions[a];o&&e.indexOf(o)<0&&e.push(o)}}),getExtensions(asElement(parentElt(n)),e,t)}var isReady=!1;getDocument().addEventListener("DOMContentLoaded",function(){isReady=!0});function ready(n){isReady||getDocument().readyState==="complete"?n():getDocument().addEventListener("DOMContentLoaded",n)}function insertIndicatorStyles(){if(htmx.config.includeIndicatorStyles!==!1){const n=htmx.config.inlineStyleNonce?` nonce="${htmx.config.inlineStyleNonce}"`:"",e=htmx.config.indicatorClass,t=htmx.config.requestClass;getDocument().head.insertAdjacentHTML("beforeend",`<style${n}>.${e}{opacity:0;visibility: hidden} .${t} .${e}, .${t}.${e}{opacity:1;visibility: visible;transition: opacity 200ms ease-in}</style>`)}}function getMetaConfig(){const n=getDocument().querySelector('meta[name="htmx-config"]');return n?parseJSON(n.content):null}function mergeMetaConfig(){const n=getMetaConfig();n&&(htmx.config=mergeObjects(htmx.config,n))}return ready(function(){mergeMetaConfig(),insertIndicatorStyles();let n=getDocument().body;processNode(n);const e=getDocument().querySelectorAll("[hx-trigger='restored'],[data-hx-trigger='restored']");n.addEventListener("htmx:abort",function(r){const a=r.detail.elt||r.target,o=getInternalData(a);o&&o.xhr&&o.xhr.abort()});const t=window.onpopstate?window.onpopstate.bind(window):null;window.onpopstate=function(r){r.state&&r.state.htmx?(restoreHistory(),forEach(e,function(a){triggerEvent(a,"htmx:restored",{document:getDocument(),triggerEvent})})):t&&t(r)},getWindow().setTimeout(function(){triggerEvent(n,"htmx:load",{}),n=null},0)}),htmx})();var HOOKS=["onChange","onClose","onDayCreate","onDestroy","onKeyDown","onMonthChange","onOpen","onParseConfig","onReady","onValueUpdate","onYearChange","onPreCalendarPosition"],defaults$1={_disable:[],allowInput:!1,allowInvalidPreload:!1,altFormat:"F j, Y",altInput:!1,altInputClass:"form-control input",animate:typeof window=="object"&&window.navigator.userAgent.indexOf("MSIE")===-1,ariaDateFormat:"F j, Y",autoFillDefaultTime:!0,clickOpens:!0,closeOnSelect:!0,conjunction:", ",dateFormat:"Y-m-d",defaultHour:12,defaultMinute:0,defaultSeconds:0,disable:[],disableMobile:!1,enableSeconds:!1,enableTime:!1,errorHandler:function(n){return typeof console<"u"&&console.warn(n)},getWeek:function(n){var e=new Date(n.getTime());e.setHours(0,0,0,0),e.setDate(e.getDate()+3-(e.getDay()+6)%7);var t=new Date(e.getFullYear(),0,4);return 1+Math.round(((e.getTime()-t.getTime())/864e5-3+(t.getDay()+6)%7)/7)},hourIncrement:1,ignoredFocusElements:[],inline:!1,locale:"default",minuteIncrement:5,mode:"single",monthSelectorType:"dropdown",nextArrow:"<svg version='1.1' xmlns='http://www.w3.org/2000/svg' xmlns:xlink='http://www.w3.org/1999/xlink' viewBox='0 0 17 17'><g></g><path d='M13.207 8.472l-7.854 7.854-0.707-0.707 7.146-7.146-7.146-7.148 0.707-0.707 7.854 7.854z' /></svg>",noCalendar:!1,now:new Date,onChange:[],onClose:[],onDayCreate:[],onDestroy:[],onKeyDown:[],onMonthChange:[],onOpen:[],onParseConfig:[],onReady:[],onValueUpdate:[],onYearChange:[],onPreCalendarPosition:[],plugins:[],position:"auto",positionElement:void 0,prevArrow:"<svg version='1.1' xmlns='http://www.w3.org/2000/svg' xmlns:xlink='http://www.w3.org/1999/xlink' viewBox='0 0 17 17'><g></g><path d='M5.207 8.471l7.146 7.147-0.707 0.707-7.853-7.854 7.854-7.853 0.707 0.707-7.147 7.146z' /></svg>",shorthandCurrentMonth:!1,showMonths:1,static:!1,time_24hr:!1,weekNumbers:!1,wrap:!1},english={weekdays:{shorthand:["Sun","Mon","Tue","Wed","Thu","Fri","Sat"],longhand:["Sunday","Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"]},months:{shorthand:["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"],longhand:["January","February","March","April","May","June","July","August","September","October","November","December"]},daysInMonth:[31,28,31,30,31,30,31,31,30,31,30,31],firstDayOfWeek:0,ordinal:function(n){var e=n%100;if(e>3&&e<21)return"th";switch(e%10){case 1:return"st";case 2:return"nd";case 3:return"rd";default:return"th"}},rangeSeparator:" to ",weekAbbreviation:"Wk",scrollTitle:"Scroll to increment",toggleTitle:"Click to toggle",amPM:["AM","PM"],yearAriaLabel:"Year",monthAriaLabel:"Month",hourAriaLabel:"Hour",minuteAriaLabel:"Minute",time_24hr:!1},pad=function(n,e){return e===void 0&&(e=2),("000"+n).slice(e*-1)},int=function(n){return n===!0?1:0};function debounce$1(n,e){var t;return function(){var r=this,a=arguments;clearTimeout(t),t=setTimeout(function(){return n.apply(r,a)},e)}}var arrayify=function(n){return n instanceof Array?n:[n]};function toggleClass(n,e,t){if(t===!0)return n.classList.add(e);n.classList.remove(e)}function createElement(n,e,t){var r=window.document.createElement(n);return e=e||"",t=t||"",r.className=e,t!==void 0&&(r.textContent=t),r}function clearNode(n){for(;n.firstChild;)n.removeChild(n.firstChild)}function findParent(n,e){if(e(n))return n;if(n.parentNode)return findParent(n.parentNode,e)}function createNumberInput(n,e){var t=createElement("div","numInputWrapper"),r=createElement("input","numInput "+n),a=createElement("span","arrowUp"),o=createElement("span","arrowDown");if(navigator.userAgent.indexOf("MSIE 9.0")===-1?r.type="number":(r.type="text",r.pattern="\\d*"),e!==void 0)for(var s in e)r.setAttribute(s,e[s]);return t.appendChild(r),t.appendChild(a),t.appendChild(o),t}function getEventTarget(n){try{if(typeof n.composedPath=="function"){var e=n.composedPath();return e[0]}return n.target}catch{return n.target}}var doNothing=function(){},monthToStr=function(n,e,t){return t.months[e?"shorthand":"longhand"][n]},revFormat={D:doNothing,F:function(n,e,t){n.setMonth(t.months.longhand.indexOf(e))},G:function(n,e){n.setHours((n.getHours()>=12?12:0)+parseFloat(e))},H:function(n,e){n.setHours(parseFloat(e))},J:function(n,e){n.setDate(parseFloat(e))},K:function(n,e,t){n.setHours(n.getHours()%12+12*int(new RegExp(t.amPM[1],"i").test(e)))},M:function(n,e,t){n.setMonth(t.months.shorthand.indexOf(e))},S:function(n,e){n.setSeconds(parseFloat(e))},U:function(n,e){return new Date(parseFloat(e)*1e3)},W:function(n,e,t){var r=parseInt(e),a=new Date(n.getFullYear(),0,2+(r-1)*7,0,0,0,0);return a.setDate(a.getDate()-a.getDay()+t.firstDayOfWeek),a},Y:function(n,e){n.setFullYear(parseFloat(e))},Z:function(n,e){return new Date(e)},d:function(n,e){n.setDate(parseFloat(e))},h:function(n,e){n.setHours((n.getHours()>=12?12:0)+parseFloat(e))},i:function(n,e){n.setMinutes(parseFloat(e))},j:function(n,e){n.setDate(parseFloat(e))},l:doNothing,m:function(n,e){n.setMonth(parseFloat(e)-1)},n:function(n,e){n.setMonth(parseFloat(e)-1)},s:function(n,e){n.setSeconds(parseFloat(e))},u:function(n,e){return new Date(parseFloat(e))},w:doNothing,y:function(n,e){n.setFullYear(2e3+parseFloat(e))}},tokenRegex={D:"",F:"",G:"(\\d\\d|\\d)",H:"(\\d\\d|\\d)",J:"(\\d\\d|\\d)\\w+",K:"",M:"",S:"(\\d\\d|\\d)",U:"(.+)",W:"(\\d\\d|\\d)",Y:"(\\d{4})",Z:"(.+)",d:"(\\d\\d|\\d)",h:"(\\d\\d|\\d)",i:"(\\d\\d|\\d)",j:"(\\d\\d|\\d)",l:"",m:"(\\d\\d|\\d)",n:"(\\d\\d|\\d)",s:"(\\d\\d|\\d)",u:"(.+)",w:"(\\d\\d|\\d)",y:"(\\d{2})"},formats={Z:function(n){return n.toISOString()},D:function(n,e,t){return e.weekdays.shorthand[formats.w(n,e,t)]},F:function(n,e,t){return monthToStr(formats.n(n,e,t)-1,!1,e)},G:function(n,e,t){return pad(formats.h(n,e,t))},H:function(n){return pad(n.getHours())},J:function(n,e){return e.ordinal!==void 0?n.getDate()+e.ordinal(n.getDate()):n.getDate()},K:function(n,e){return e.amPM[int(n.getHours()>11)]},M:function(n,e){return monthToStr(n.getMonth(),!0,e)},S:function(n){return pad(n.getSeconds())},U:function(n){return n.getTime()/1e3},W:function(n,e,t){return t.getWeek(n)},Y:function(n){return pad(n.getFullYear(),4)},d:function(n){return pad(n.getDate())},h:function(n){return n.getHours()%12?n.getHours()%12:12},i:function(n){return pad(n.getMinutes())},j:function(n){return n.getDate()},l:function(n,e){return e.weekdays.longhand[n.getDay()]},m:function(n){return pad(n.getMonth()+1)},n:function(n){return n.getMonth()+1},s:function(n){return n.getSeconds()},u:function(n){return n.getTime()},w:function(n){return n.getDay()},y:function(n){return String(n.getFullYear()).substring(2)}},createDateFormatter=function(n){var e=n.config,t=e===void 0?defaults$1:e,r=n.l10n,a=r===void 0?english:r,o=n.isMobile,s=o===void 0?!1:o;return function(l,c,f){var d=f||a;return t.formatDate!==void 0&&!s?t.formatDate(l,c,d):c.split("").map(function(p,_,b){return formats[p]&&b[_-1]!=="\\"?formats[p](l,d,t):p!=="\\"?p:""}).join("")}},createDateParser=function(n){var e=n.config,t=e===void 0?defaults$1:e,r=n.l10n,a=r===void 0?english:r;return function(o,s,l,c){if(!(o!==0&&!o)){var f=c||a,d,p=o;if(o instanceof Date)d=new Date(o.getTime());else if(typeof o!="string"&&o.toFixed!==void 0)d=new Date(o);else if(typeof o=="string"){var _=s||(t||defaults$1).dateFormat,b=String(o).trim();if(b==="today")d=new Date,l=!0;else if(t&&t.parseDate)d=t.parseDate(o,_);else if(/Z$/.test(b)||/GMT$/.test(b))d=new Date(o);else{for(var y=void 0,E=[],C=0,D=0,M="";C<_.length;C++){var F=_[C],P=F==="\\",H=_[C-1]==="\\"||P;if(tokenRegex[F]&&!H){M+=tokenRegex[F];var B=new RegExp(M).exec(o);B&&(y=!0)&&E[F!=="Y"?"push":"unshift"]({fn:revFormat[F],val:B[++D]})}else P||(M+=".")}d=!t||!t.noCalendar?new Date(new Date().getFullYear(),0,1,0,0,0,0):new Date(new Date().setHours(0,0,0,0)),E.forEach(function(g){var q=g.fn,G=g.val;return d=q(d,G,f)||d}),d=y?d:void 0}}if(!(d instanceof Date&&!isNaN(d.getTime()))){t.errorHandler(new Error("Invalid date provided: "+p));return}return l===!0&&d.setHours(0,0,0,0),d}}};function compareDates(n,e,t){return t===void 0&&(t=!0),t!==!1?new Date(n.getTime()).setHours(0,0,0,0)-new Date(e.getTime()).setHours(0,0,0,0):n.getTime()-e.getTime()}var isBetween=function(n,e,t){return n>Math.min(e,t)&&n<Math.max(e,t)},calculateSecondsSinceMidnight=function(n,e,t){return n*3600+e*60+t},parseSeconds=function(n){var e=Math.floor(n/3600),t=(n-e*3600)/60;return[e,t,n-e*3600-t*60]},duration={DAY:864e5};function getDefaultHours(n){var e=n.defaultHour,t=n.defaultMinute,r=n.defaultSeconds;if(n.minDate!==void 0){var a=n.minDate.getHours(),o=n.minDate.getMinutes(),s=n.minDate.getSeconds();e<a&&(e=a),e===a&&t<o&&(t=o),e===a&&t===o&&r<s&&(r=n.minDate.getSeconds())}if(n.maxDate!==void 0){var l=n.maxDate.getHours(),c=n.maxDate.getMinutes();e=Math.min(e,l),e===l&&(t=Math.min(c,t)),e===l&&t===c&&(r=n.maxDate.getSeconds())}return{hours:e,minutes:t,seconds:r}}typeof Object.assign!="function"&&(Object.assign=function(n){for(var e=[],t=1;t<arguments.length;t++)e[t-1]=arguments[t];if(!n)throw TypeError("Cannot convert undefined or null to object");for(var r=function(l){l&&Object.keys(l).forEach(function(c){return n[c]=l[c]})},a=0,o=e;a<o.length;a++){var s=o[a];r(s)}return n});var __assign=function(){return __assign=Object.assign||function(n){for(var e,t=1,r=arguments.length;t<r;t++){e=arguments[t];for(var a in e)Object.prototype.hasOwnProperty.call(e,a)&&(n[a]=e[a])}return n},__assign.apply(this,arguments)},__spreadArrays=function(){for(var n=0,e=0,t=arguments.length;e<t;e++)n+=arguments[e].length;for(var r=Array(n),a=0,e=0;e<t;e++)for(var o=arguments[e],s=0,l=o.length;s<l;s++,a++)r[a]=o[s];return r},DEBOUNCED_CHANGE_MS=300;function FlatpickrInstance(n,e){var t={config:__assign(__assign({},defaults$1),flatpickr.defaultConfig),l10n:english};t.parseDate=createDateParser({config:t.config,l10n:t.l10n}),t._handlers=[],t.pluginElements=[],t.loadedPlugins=[],t._bind=E,t._setHoursFromDate=_,t._positionCalendar=Ct,t.changeMonth=Re,t.changeYear=Me,t.clear=Te,t.close=je,t.onMouseOver=tt,t._createElement=createElement,t.createDay=B,t.destroy=Fe,t.isEnabled=Pe,t.jumpToDate=M,t.updateValue=Ye,t.open=jt,t.redraw=qe,t.set=We,t.setDate=Wt,t.toggle=bt;function r(){t.utils={getDaysInMonth:function(T,w){return T===void 0&&(T=t.currentMonth),w===void 0&&(w=t.currentYear),T===1&&(w%4===0&&w%100!==0||w%400===0)?29:t.l10n.daysInMonth[T]}}}function a(){t.element=t.input=n,t.isOpen=!1,St(),Je(),cn(),ln(),r(),t.isMobile||H(),D(),(t.selectedDates.length||t.config.noCalendar)&&(t.config.enableTime&&_(t.config.noCalendar?t.latestSelectedDateObj:void 0),Ye(!1)),l();var T=/^((?!chrome|android).)*safari/i.test(navigator.userAgent);!t.isMobile&&T&&Ct(),Le("onReady")}function o(){var T;return((T=t.calendarContainer)===null||T===void 0?void 0:T.getRootNode()).activeElement||document.activeElement}function s(T){return T.bind(t)}function l(){var T=t.config;T.weekNumbers===!1&&T.showMonths===1||T.noCalendar!==!0&&window.requestAnimationFrame(function(){if(t.calendarContainer!==void 0&&(t.calendarContainer.style.visibility="hidden",t.calendarContainer.style.display="block"),t.daysContainer!==void 0){var w=(t.days.offsetWidth+1)*T.showMonths;t.daysContainer.style.width=w+"px",t.calendarContainer.style.width=w+(t.weekWrapper!==void 0?t.weekWrapper.offsetWidth:0)+"px",t.calendarContainer.style.removeProperty("visibility"),t.calendarContainer.style.removeProperty("display")}})}function c(T){if(t.selectedDates.length===0){var w=t.config.minDate===void 0||compareDates(new Date,t.config.minDate)>=0?new Date:new Date(t.config.minDate.getTime()),I=getDefaultHours(t.config);w.setHours(I.hours,I.minutes,I.seconds,w.getMilliseconds()),t.selectedDates=[w],t.latestSelectedDateObj=w}T!==void 0&&T.type!=="blur"&&fn(T);var z=t._input.value;p(),Ye(),t._input.value!==z&&t._debouncedChange()}function f(T,w){return T%12+12*int(w===t.l10n.amPM[1])}function d(T){switch(T%24){case 0:case 12:return 12;default:return T%12}}function p(){if(!(t.hourElement===void 0||t.minuteElement===void 0)){var T=(parseInt(t.hourElement.value.slice(-2),10)||0)%24,w=(parseInt(t.minuteElement.value,10)||0)%60,I=t.secondElement!==void 0?(parseInt(t.secondElement.value,10)||0)%60:0;t.amPM!==void 0&&(T=f(T,t.amPM.textContent));var z=t.config.minTime!==void 0||t.config.minDate&&t.minDateHasTime&&t.latestSelectedDateObj&&compareDates(t.latestSelectedDateObj,t.config.minDate,!0)===0,J=t.config.maxTime!==void 0||t.config.maxDate&&t.maxDateHasTime&&t.latestSelectedDateObj&&compareDates(t.latestSelectedDateObj,t.config.maxDate,!0)===0;if(t.config.maxTime!==void 0&&t.config.minTime!==void 0&&t.config.minTime>t.config.maxTime){var ie=calculateSecondsSinceMidnight(t.config.minTime.getHours(),t.config.minTime.getMinutes(),t.config.minTime.getSeconds()),ye=calculateSecondsSinceMidnight(t.config.maxTime.getHours(),t.config.maxTime.getMinutes(),t.config.maxTime.getSeconds()),se=calculateSecondsSinceMidnight(T,w,I);if(se>ye&&se<ie){var ve=parseSeconds(ie);T=ve[0],w=ve[1],I=ve[2]}}else{if(J){var ce=t.config.maxTime!==void 0?t.config.maxTime:t.config.maxDate;T=Math.min(T,ce.getHours()),T===ce.getHours()&&(w=Math.min(w,ce.getMinutes())),w===ce.getMinutes()&&(I=Math.min(I,ce.getSeconds()))}if(z){var he=t.config.minTime!==void 0?t.config.minTime:t.config.minDate;T=Math.max(T,he.getHours()),T===he.getHours()&&w<he.getMinutes()&&(w=he.getMinutes()),w===he.getMinutes()&&(I=Math.max(I,he.getSeconds()))}}b(T,w,I)}}function _(T){var w=T||t.latestSelectedDateObj;w&&w instanceof Date&&b(w.getHours(),w.getMinutes(),w.getSeconds())}function b(T,w,I){t.latestSelectedDateObj!==void 0&&t.latestSelectedDateObj.setHours(T%24,w,I||0,0),!(!t.hourElement||!t.minuteElement||t.isMobile)&&(t.hourElement.value=pad(t.config.time_24hr?T:(12+T)%12+12*int(T%12===0)),t.minuteElement.value=pad(w),t.amPM!==void 0&&(t.amPM.textContent=t.l10n.amPM[int(T>=12)]),t.secondElement!==void 0&&(t.secondElement.value=pad(I)))}function y(T){var w=getEventTarget(T),I=parseInt(w.value)+(T.delta||0);(I/1e3>1||T.key==="Enter"&&!/[^\d]/.test(I.toString()))&&Me(I)}function E(T,w,I,z){if(w instanceof Array)return w.forEach(function(J){return E(T,J,I,z)});if(T instanceof Array)return T.forEach(function(J){return E(J,w,I,z)});T.addEventListener(w,I,z),t._handlers.push({remove:function(){return T.removeEventListener(w,I,z)}})}function C(){Le("onChange")}function D(){if(t.config.wrap&&["open","close","toggle","clear"].forEach(function(I){Array.prototype.forEach.call(t.element.querySelectorAll("[data-"+I+"]"),function(z){return E(z,"click",t[I])})}),t.isMobile){ct();return}var T=debounce$1(vt,50);if(t._debouncedChange=debounce$1(C,DEBOUNCED_CHANGE_MS),t.daysContainer&&!/iPhone|iPad|iPod/i.test(navigator.userAgent)&&E(t.daysContainer,"mouseover",function(I){t.config.mode==="range"&&tt(getEventTarget(I))}),E(t._input,"keydown",xt),t.calendarContainer!==void 0&&E(t.calendarContainer,"keydown",xt),!t.config.inline&&!t.config.static&&E(window,"resize",T),window.ontouchstart!==void 0?E(window.document,"touchstart",ge):E(window.document,"mousedown",ge),E(window.document,"focus",ge,{capture:!0}),t.config.clickOpens===!0&&(E(t._input,"focus",t.open),E(t._input,"click",t.open)),t.daysContainer!==void 0&&(E(t.monthNav,"click",It),E(t.monthNav,["keyup","increment"],y),E(t.daysContainer,"click",it)),t.timeContainer!==void 0&&t.minuteElement!==void 0&&t.hourElement!==void 0){var w=function(I){return getEventTarget(I).select()};E(t.timeContainer,["increment"],c),E(t.timeContainer,"blur",c,{capture:!0}),E(t.timeContainer,"click",F),E([t.hourElement,t.minuteElement],["focus","click"],w),t.secondElement!==void 0&&E(t.secondElement,"focus",function(){return t.secondElement&&t.secondElement.select()}),t.amPM!==void 0&&E(t.amPM,"click",function(I){c(I)})}t.config.allowInput&&E(t._input,"blur",Qe)}function M(T,w){var I=T!==void 0?t.parseDate(T):t.latestSelectedDateObj||(t.config.minDate&&t.config.minDate>t.now?t.config.minDate:t.config.maxDate&&t.config.maxDate<t.now?t.config.maxDate:t.now),z=t.currentYear,J=t.currentMonth;try{I!==void 0&&(t.currentYear=I.getFullYear(),t.currentMonth=I.getMonth())}catch(ie){ie.message="Invalid date supplied: "+I,t.config.errorHandler(ie)}w&&t.currentYear!==z&&(Le("onYearChange"),Q()),w&&(t.currentYear!==z||t.currentMonth!==J)&&Le("onMonthChange"),t.redraw()}function F(T){var w=getEventTarget(T);~w.className.indexOf("arrow")&&P(T,w.classList.contains("arrowUp")?1:-1)}function P(T,w,I){var z=T&&getEventTarget(T),J=I||z&&z.parentNode&&z.parentNode.firstChild,ie=Gt("increment");ie.delta=w,J&&J.dispatchEvent(ie)}function H(){var T=window.document.createDocumentFragment();if(t.calendarContainer=createElement("div","flatpickr-calendar"),t.calendarContainer.tabIndex=-1,!t.config.noCalendar){if(T.appendChild(de()),t.innerContainer=createElement("div","flatpickr-innerContainer"),t.config.weekNumbers){var w=Ve(),I=w.weekWrapper,z=w.weekNumbers;t.innerContainer.appendChild(I),t.weekNumbers=z,t.weekWrapper=I}t.rContainer=createElement("div","flatpickr-rContainer"),t.rContainer.appendChild($e()),t.daysContainer||(t.daysContainer=createElement("div","flatpickr-days"),t.daysContainer.tabIndex=-1),ne(),t.rContainer.appendChild(t.daysContainer),t.innerContainer.appendChild(t.rContainer),T.appendChild(t.innerContainer)}t.config.enableTime&&T.appendChild(le()),toggleClass(t.calendarContainer,"rangeMode",t.config.mode==="range"),toggleClass(t.calendarContainer,"animate",t.config.animate===!0),toggleClass(t.calendarContainer,"multiMonth",t.config.showMonths>1),t.calendarContainer.appendChild(T);var J=t.config.appendTo!==void 0&&t.config.appendTo.nodeType!==void 0;if((t.config.inline||t.config.static)&&(t.calendarContainer.classList.add(t.config.inline?"inline":"static"),t.config.inline&&(!J&&t.element.parentNode?t.element.parentNode.insertBefore(t.calendarContainer,t._input.nextSibling):t.config.appendTo!==void 0&&t.config.appendTo.appendChild(t.calendarContainer)),t.config.static)){var ie=createElement("div","flatpickr-wrapper");t.element.parentNode&&t.element.parentNode.insertBefore(ie,t.element),ie.appendChild(t.element),t.altInput&&ie.appendChild(t.altInput),ie.appendChild(t.calendarContainer)}!t.config.static&&!t.config.inline&&(t.config.appendTo!==void 0?t.config.appendTo:window.document.body).appendChild(t.calendarContainer)}function B(T,w,I,z){var J=Pe(w,!0),ie=createElement("span",T,w.getDate().toString());return ie.dateObj=w,ie.$i=z,ie.setAttribute("aria-label",t.formatDate(w,t.config.ariaDateFormat)),T.indexOf("hidden")===-1&&compareDates(w,t.now)===0&&(t.todayDateElem=ie,ie.classList.add("today"),ie.setAttribute("aria-current","date")),J?(ie.tabIndex=-1,Tt(w)&&(ie.classList.add("selected"),t.selectedDateElem=ie,t.config.mode==="range"&&(toggleClass(ie,"startRange",t.selectedDates[0]&&compareDates(w,t.selectedDates[0],!0)===0),toggleClass(ie,"endRange",t.selectedDates[1]&&compareDates(w,t.selectedDates[1],!0)===0),T==="nextMonthDay"&&ie.classList.add("inRange")))):ie.classList.add("flatpickr-disabled"),t.config.mode==="range"&&un(w)&&!Tt(w)&&ie.classList.add("inRange"),t.weekNumbers&&t.config.showMonths===1&&T!=="prevMonthDay"&&z%7===6&&t.weekNumbers.insertAdjacentHTML("beforeend","<span class='flatpickr-day'>"+t.config.getWeek(w)+"</span>"),Le("onDayCreate",ie),ie}function g(T){T.focus(),t.config.mode==="range"&&tt(T)}function q(T){for(var w=T>0?0:t.config.showMonths-1,I=T>0?t.config.showMonths:-1,z=w;z!=I;z+=T)for(var J=t.daysContainer.children[z],ie=T>0?0:J.children.length-1,ye=T>0?J.children.length:-1,se=ie;se!=ye;se+=T){var ve=J.children[se];if(ve.className.indexOf("hidden")===-1&&Pe(ve.dateObj))return ve}}function G(T,w){for(var I=T.className.indexOf("Month")===-1?T.dateObj.getMonth():t.currentMonth,z=w>0?t.config.showMonths:-1,J=w>0?1:-1,ie=I-t.currentMonth;ie!=z;ie+=J)for(var ye=t.daysContainer.children[ie],se=I-t.currentMonth===ie?T.$i+w:w<0?ye.children.length-1:0,ve=ye.children.length,ce=se;ce>=0&&ce<ve&&ce!=(w>0?ve:-1);ce+=J){var he=ye.children[ce];if(he.className.indexOf("hidden")===-1&&Pe(he.dateObj)&&Math.abs(T.$i-ce)>=Math.abs(w))return g(he)}t.changeMonth(J),Z(q(J),0)}function Z(T,w){var I=o(),z=st(I||document.body),J=T!==void 0?T:z?I:t.selectedDateElem!==void 0&&st(t.selectedDateElem)?t.selectedDateElem:t.todayDateElem!==void 0&&st(t.todayDateElem)?t.todayDateElem:q(w>0?1:-1);J===void 0?t._input.focus():z?G(J,w):g(J)}function te(T,w){for(var I=(new Date(T,w,1).getDay()-t.l10n.firstDayOfWeek+7)%7,z=t.utils.getDaysInMonth((w-1+12)%12,T),J=t.utils.getDaysInMonth(w,T),ie=window.document.createDocumentFragment(),ye=t.config.showMonths>1,se=ye?"prevMonthDay hidden":"prevMonthDay",ve=ye?"nextMonthDay hidden":"nextMonthDay",ce=z+1-I,he=0;ce<=z;ce++,he++)ie.appendChild(B("flatpickr-day "+se,new Date(T,w-1,ce),ce,he));for(ce=1;ce<=J;ce++,he++)ie.appendChild(B("flatpickr-day",new Date(T,w,ce),ce,he));for(var Ne=J+1;Ne<=42-I&&(t.config.showMonths===1||he%7!==0);Ne++,he++)ie.appendChild(B("flatpickr-day "+ve,new Date(T,w+1,Ne%J),Ne,he));var rt=createElement("div","dayContainer");return rt.appendChild(ie),rt}function ne(){if(t.daysContainer!==void 0){clearNode(t.daysContainer),t.weekNumbers&&clearNode(t.weekNumbers);for(var T=document.createDocumentFragment(),w=0;w<t.config.showMonths;w++){var I=new Date(t.currentYear,t.currentMonth,1);I.setMonth(t.currentMonth+w),T.appendChild(te(I.getFullYear(),I.getMonth()))}t.daysContainer.appendChild(T),t.days=t.daysContainer.firstChild,t.config.mode==="range"&&t.selectedDates.length===1&&tt()}}function Q(){if(!(t.config.showMonths>1||t.config.monthSelectorType!=="dropdown")){var T=function(z){return t.config.minDate!==void 0&&t.currentYear===t.config.minDate.getFullYear()&&z<t.config.minDate.getMonth()?!1:!(t.config.maxDate!==void 0&&t.currentYear===t.config.maxDate.getFullYear()&&z>t.config.maxDate.getMonth())};t.monthsDropdownContainer.tabIndex=-1,t.monthsDropdownContainer.innerHTML="";for(var w=0;w<12;w++)if(T(w)){var I=createElement("option","flatpickr-monthDropdown-month");I.value=new Date(t.currentYear,w).getMonth().toString(),I.textContent=monthToStr(w,t.config.shorthandCurrentMonth,t.l10n),I.tabIndex=-1,t.currentMonth===w&&(I.selected=!0),t.monthsDropdownContainer.appendChild(I)}}}function Ee(){var T=createElement("div","flatpickr-month"),w=window.document.createDocumentFragment(),I;t.config.showMonths>1||t.config.monthSelectorType==="static"?I=createElement("span","cur-month"):(t.monthsDropdownContainer=createElement("select","flatpickr-monthDropdown-months"),t.monthsDropdownContainer.setAttribute("aria-label",t.l10n.monthAriaLabel),E(t.monthsDropdownContainer,"change",function(ye){var se=getEventTarget(ye),ve=parseInt(se.value,10);t.changeMonth(ve-t.currentMonth),Le("onMonthChange")}),Q(),I=t.monthsDropdownContainer);var z=createNumberInput("cur-year",{tabindex:"-1"}),J=z.getElementsByTagName("input")[0];J.setAttribute("aria-label",t.l10n.yearAriaLabel),t.config.minDate&&J.setAttribute("min",t.config.minDate.getFullYear().toString()),t.config.maxDate&&(J.setAttribute("max",t.config.maxDate.getFullYear().toString()),J.disabled=!!t.config.minDate&&t.config.minDate.getFullYear()===t.config.maxDate.getFullYear());var ie=createElement("div","flatpickr-current-month");return ie.appendChild(I),ie.appendChild(z),w.appendChild(ie),T.appendChild(w),{container:T,yearElement:J,monthElement:I}}function re(){clearNode(t.monthNav),t.monthNav.appendChild(t.prevMonthNav),t.config.showMonths&&(t.yearElements=[],t.monthElements=[]);for(var T=t.config.showMonths;T--;){var w=Ee();t.yearElements.push(w.yearElement),t.monthElements.push(w.monthElement),t.monthNav.appendChild(w.container)}t.monthNav.appendChild(t.nextMonthNav)}function de(){return t.monthNav=createElement("div","flatpickr-months"),t.yearElements=[],t.monthElements=[],t.prevMonthNav=createElement("span","flatpickr-prev-month"),t.prevMonthNav.innerHTML=t.config.prevArrow,t.nextMonthNav=createElement("span","flatpickr-next-month"),t.nextMonthNav.innerHTML=t.config.nextArrow,re(),Object.defineProperty(t,"_hidePrevMonthArrow",{get:function(){return t.__hidePrevMonthArrow},set:function(T){t.__hidePrevMonthArrow!==T&&(toggleClass(t.prevMonthNav,"flatpickr-disabled",T),t.__hidePrevMonthArrow=T)}}),Object.defineProperty(t,"_hideNextMonthArrow",{get:function(){return t.__hideNextMonthArrow},set:function(T){t.__hideNextMonthArrow!==T&&(toggleClass(t.nextMonthNav,"flatpickr-disabled",T),t.__hideNextMonthArrow=T)}}),t.currentYearElement=t.yearElements[0],Pt(),t.monthNav}function le(){t.calendarContainer.classList.add("hasTime"),t.config.noCalendar&&t.calendarContainer.classList.add("noCalendar");var T=getDefaultHours(t.config);t.timeContainer=createElement("div","flatpickr-time"),t.timeContainer.tabIndex=-1;var w=createElement("span","flatpickr-time-separator",":"),I=createNumberInput("flatpickr-hour",{"aria-label":t.l10n.hourAriaLabel});t.hourElement=I.getElementsByTagName("input")[0];var z=createNumberInput("flatpickr-minute",{"aria-label":t.l10n.minuteAriaLabel});if(t.minuteElement=z.getElementsByTagName("input")[0],t.hourElement.tabIndex=t.minuteElement.tabIndex=-1,t.hourElement.value=pad(t.latestSelectedDateObj?t.latestSelectedDateObj.getHours():t.config.time_24hr?T.hours:d(T.hours)),t.minuteElement.value=pad(t.latestSelectedDateObj?t.latestSelectedDateObj.getMinutes():T.minutes),t.hourElement.setAttribute("step",t.config.hourIncrement.toString()),t.minuteElement.setAttribute("step",t.config.minuteIncrement.toString()),t.hourElement.setAttribute("min",t.config.time_24hr?"0":"1"),t.hourElement.setAttribute("max",t.config.time_24hr?"23":"12"),t.hourElement.setAttribute("maxlength","2"),t.minuteElement.setAttribute("min","0"),t.minuteElement.setAttribute("max","59"),t.minuteElement.setAttribute("maxlength","2"),t.timeContainer.appendChild(I),t.timeContainer.appendChild(w),t.timeContainer.appendChild(z),t.config.time_24hr&&t.timeContainer.classList.add("time24hr"),t.config.enableSeconds){t.timeContainer.classList.add("hasSeconds");var J=createNumberInput("flatpickr-second");t.secondElement=J.getElementsByTagName("input")[0],t.secondElement.value=pad(t.latestSelectedDateObj?t.latestSelectedDateObj.getSeconds():T.seconds),t.secondElement.setAttribute("step",t.minuteElement.getAttribute("step")),t.secondElement.setAttribute("min","0"),t.secondElement.setAttribute("max","59"),t.secondElement.setAttribute("maxlength","2"),t.timeContainer.appendChild(createElement("span","flatpickr-time-separator",":")),t.timeContainer.appendChild(J)}return t.config.time_24hr||(t.amPM=createElement("span","flatpickr-am-pm",t.l10n.amPM[int((t.latestSelectedDateObj?t.hourElement.value:t.config.defaultHour)>11)]),t.amPM.title=t.l10n.toggleTitle,t.amPM.tabIndex=-1,t.timeContainer.appendChild(t.amPM)),t.timeContainer}function $e(){t.weekdayContainer?clearNode(t.weekdayContainer):t.weekdayContainer=createElement("div","flatpickr-weekdays");for(var T=t.config.showMonths;T--;){var w=createElement("div","flatpickr-weekdaycontainer");t.weekdayContainer.appendChild(w)}return xe(),t.weekdayContainer}function xe(){if(t.weekdayContainer){var T=t.l10n.firstDayOfWeek,w=__spreadArrays(t.l10n.weekdays.shorthand);T>0&&T<w.length&&(w=__spreadArrays(w.splice(T,w.length),w.splice(0,T)));for(var I=t.config.showMonths;I--;)t.weekdayContainer.children[I].innerHTML=`
      <span class='flatpickr-weekday'>
        `+w.join("</span><span class='flatpickr-weekday'>")+`
      </span>
      `}}function Ve(){t.calendarContainer.classList.add("hasWeeks");var T=createElement("div","flatpickr-weekwrapper");T.appendChild(createElement("span","flatpickr-weekday",t.l10n.weekAbbreviation));var w=createElement("div","flatpickr-weeks");return T.appendChild(w),{weekWrapper:T,weekNumbers:w}}function Re(T,w){w===void 0&&(w=!0);var I=w?T:T-t.currentMonth;I<0&&t._hidePrevMonthArrow===!0||I>0&&t._hideNextMonthArrow===!0||(t.currentMonth+=I,(t.currentMonth<0||t.currentMonth>11)&&(t.currentYear+=t.currentMonth>11?1:-1,t.currentMonth=(t.currentMonth+12)%12,Le("onYearChange"),Q()),ne(),Le("onMonthChange"),Pt())}function Te(T,w){if(T===void 0&&(T=!0),w===void 0&&(w=!0),t.input.value="",t.altInput!==void 0&&(t.altInput.value=""),t.mobileInput!==void 0&&(t.mobileInput.value=""),t.selectedDates=[],t.latestSelectedDateObj=void 0,w===!0&&(t.currentYear=t._initialDate.getFullYear(),t.currentMonth=t._initialDate.getMonth()),t.config.enableTime===!0){var I=getDefaultHours(t.config),z=I.hours,J=I.minutes,ie=I.seconds;b(z,J,ie)}t.redraw(),T&&Le("onChange")}function je(){t.isOpen=!1,t.isMobile||(t.calendarContainer!==void 0&&t.calendarContainer.classList.remove("open"),t._input!==void 0&&t._input.classList.remove("active")),Le("onClose")}function Fe(){t.config!==void 0&&Le("onDestroy");for(var T=t._handlers.length;T--;)t._handlers[T].remove();if(t._handlers=[],t.mobileInput)t.mobileInput.parentNode&&t.mobileInput.parentNode.removeChild(t.mobileInput),t.mobileInput=void 0;else if(t.calendarContainer&&t.calendarContainer.parentNode)if(t.config.static&&t.calendarContainer.parentNode){var w=t.calendarContainer.parentNode;if(w.lastChild&&w.removeChild(w.lastChild),w.parentNode){for(;w.firstChild;)w.parentNode.insertBefore(w.firstChild,w);w.parentNode.removeChild(w)}}else t.calendarContainer.parentNode.removeChild(t.calendarContainer);t.altInput&&(t.input.type="text",t.altInput.parentNode&&t.altInput.parentNode.removeChild(t.altInput),delete t.altInput),t.input&&(t.input.type=t.input._type,t.input.classList.remove("flatpickr-input"),t.input.removeAttribute("readonly")),["_showTimeInput","latestSelectedDateObj","_hideNextMonthArrow","_hidePrevMonthArrow","__hideNextMonthArrow","__hidePrevMonthArrow","isMobile","isOpen","selectedDateElem","minDateHasTime","maxDateHasTime","days","daysContainer","_input","_positionElement","innerContainer","rContainer","monthNav","todayDateElem","calendarContainer","weekdayContainer","prevMonthNav","nextMonthNav","monthsDropdownContainer","currentMonthElement","currentYearElement","navigationCurrentMonth","selectedDateElem","config"].forEach(function(I){try{delete t[I]}catch{}})}function He(T){return t.calendarContainer.contains(T)}function ge(T){if(t.isOpen&&!t.config.inline){var w=getEventTarget(T),I=He(w),z=w===t.input||w===t.altInput||t.element.contains(w)||T.path&&T.path.indexOf&&(~T.path.indexOf(t.input)||~T.path.indexOf(t.altInput)),J=!z&&!I&&!He(T.relatedTarget),ie=!t.config.ignoredFocusElements.some(function(ye){return ye.contains(w)});J&&ie&&(t.config.allowInput&&t.setDate(t._input.value,!1,t.config.altInput?t.config.altFormat:t.config.dateFormat),t.timeContainer!==void 0&&t.minuteElement!==void 0&&t.hourElement!==void 0&&t.input.value!==""&&t.input.value!==void 0&&c(),t.close(),t.config&&t.config.mode==="range"&&t.selectedDates.length===1&&t.clear(!1))}}function Me(T){if(!(!T||t.config.minDate&&T<t.config.minDate.getFullYear()||t.config.maxDate&&T>t.config.maxDate.getFullYear())){var w=T,I=t.currentYear!==w;t.currentYear=w||t.currentYear,t.config.maxDate&&t.currentYear===t.config.maxDate.getFullYear()?t.currentMonth=Math.min(t.config.maxDate.getMonth(),t.currentMonth):t.config.minDate&&t.currentYear===t.config.minDate.getFullYear()&&(t.currentMonth=Math.max(t.config.minDate.getMonth(),t.currentMonth)),I&&(t.redraw(),Le("onYearChange"),Q())}}function Pe(T,w){var I;w===void 0&&(w=!0);var z=t.parseDate(T,void 0,w);if(t.config.minDate&&z&&compareDates(z,t.config.minDate,w!==void 0?w:!t.minDateHasTime)<0||t.config.maxDate&&z&&compareDates(z,t.config.maxDate,w!==void 0?w:!t.maxDateHasTime)>0)return!1;if(!t.config.enable&&t.config.disable.length===0)return!0;if(z===void 0)return!1;for(var J=!!t.config.enable,ie=(I=t.config.enable)!==null&&I!==void 0?I:t.config.disable,ye=0,se=void 0;ye<ie.length;ye++){if(se=ie[ye],typeof se=="function"&&se(z))return J;if(se instanceof Date&&z!==void 0&&se.getTime()===z.getTime())return J;if(typeof se=="string"){var ve=t.parseDate(se,void 0,!0);return ve&&ve.getTime()===z.getTime()?J:!J}else if(typeof se=="object"&&z!==void 0&&se.from&&se.to&&z.getTime()>=se.from.getTime()&&z.getTime()<=se.to.getTime())return J}return!J}function st(T){return t.daysContainer!==void 0?T.className.indexOf("hidden")===-1&&T.className.indexOf("flatpickr-disabled")===-1&&t.daysContainer.contains(T):!1}function Qe(T){var w=T.target===t._input,I=t._input.value.trimEnd()!==Xt();w&&I&&!(T.relatedTarget&&He(T.relatedTarget))&&t.setDate(t._input.value,!0,T.target===t.altInput?t.config.altFormat:t.config.dateFormat)}function xt(T){var w=getEventTarget(T),I=t.config.wrap?n.contains(w):w===t._input,z=t.config.allowInput,J=t.isOpen&&(!z||!I),ie=t.config.inline&&I&&!z;if(T.keyCode===13&&I){if(z)return t.setDate(t._input.value,!0,w===t.altInput?t.config.altFormat:t.config.dateFormat),t.close(),w.blur();t.open()}else if(He(w)||J||ie){var ye=!!t.timeContainer&&t.timeContainer.contains(w);switch(T.keyCode){case 13:ye?(T.preventDefault(),c(),nt()):it(T);break;case 27:T.preventDefault(),nt();break;case 8:case 46:I&&!t.config.allowInput&&(T.preventDefault(),t.clear());break;case 37:case 39:if(!ye&&!I){T.preventDefault();var se=o();if(t.daysContainer!==void 0&&(z===!1||se&&st(se))){var ve=T.keyCode===39?1:-1;T.ctrlKey?(T.stopPropagation(),Re(ve),Z(q(1),0)):Z(void 0,ve)}}else t.hourElement&&t.hourElement.focus();break;case 38:case 40:T.preventDefault();var ce=T.keyCode===40?1:-1;t.daysContainer&&w.$i!==void 0||w===t.input||w===t.altInput?T.ctrlKey?(T.stopPropagation(),Me(t.currentYear-ce),Z(q(1),0)):ye||Z(void 0,ce*7):w===t.currentYearElement?Me(t.currentYear-ce):t.config.enableTime&&(!ye&&t.hourElement&&t.hourElement.focus(),c(T),t._debouncedChange());break;case 9:if(ye){var he=[t.hourElement,t.minuteElement,t.secondElement,t.amPM].concat(t.pluginElements).filter(function(Ge){return Ge}),Ne=he.indexOf(w);if(Ne!==-1){var rt=he[Ne+(T.shiftKey?-1:1)];T.preventDefault(),(rt||t._input).focus()}}else!t.config.noCalendar&&t.daysContainer&&t.daysContainer.contains(w)&&T.shiftKey&&(T.preventDefault(),t._input.focus());break}}if(t.amPM!==void 0&&w===t.amPM)switch(T.key){case t.l10n.amPM[0].charAt(0):case t.l10n.amPM[0].charAt(0).toLowerCase():t.amPM.textContent=t.l10n.amPM[0],p(),Ye();break;case t.l10n.amPM[1].charAt(0):case t.l10n.amPM[1].charAt(0).toLowerCase():t.amPM.textContent=t.l10n.amPM[1],p(),Ye();break}(I||He(w))&&Le("onKeyDown",T)}function tt(T,w){if(w===void 0&&(w="flatpickr-day"),!(t.selectedDates.length!==1||T&&(!T.classList.contains(w)||T.classList.contains("flatpickr-disabled")))){for(var I=T?T.dateObj.getTime():t.days.firstElementChild.dateObj.getTime(),z=t.parseDate(t.selectedDates[0],void 0,!0).getTime(),J=Math.min(I,t.selectedDates[0].getTime()),ie=Math.max(I,t.selectedDates[0].getTime()),ye=!1,se=0,ve=0,ce=J;ce<ie;ce+=duration.DAY)Pe(new Date(ce),!0)||(ye=ye||ce>J&&ce<ie,ce<z&&(!se||ce>se)?se=ce:ce>z&&(!ve||ce<ve)&&(ve=ce));var he=Array.from(t.rContainer.querySelectorAll("*:nth-child(-n+"+t.config.showMonths+") > ."+w));he.forEach(function(Ne){var rt=Ne.dateObj,Ge=rt.getTime(),wt=se>0&&Ge<se||ve>0&&Ge>ve;if(wt){Ne.classList.add("notAllowed"),["inRange","startRange","endRange"].forEach(function(Ot){Ne.classList.remove(Ot)});return}else if(ye&&!wt)return;["startRange","inRange","endRange","notAllowed"].forEach(function(Ot){Ne.classList.remove(Ot)}),T!==void 0&&(T.classList.add(I<=t.selectedDates[0].getTime()?"startRange":"endRange"),z<I&&Ge===z?Ne.classList.add("startRange"):z>I&&Ge===z&&Ne.classList.add("endRange"),Ge>=se&&(ve===0||Ge<=ve)&&isBetween(Ge,z,I)&&Ne.classList.add("inRange"))})}}function vt(){t.isOpen&&!t.config.static&&!t.config.inline&&Ct()}function jt(T,w){if(w===void 0&&(w=t._positionElement),t.isMobile===!0){if(T){T.preventDefault();var I=getEventTarget(T);I&&I.blur()}t.mobileInput!==void 0&&(t.mobileInput.focus(),t.mobileInput.click()),Le("onOpen");return}else if(t._input.disabled||t.config.inline)return;var z=t.isOpen;t.isOpen=!0,z||(t.calendarContainer.classList.add("open"),t._input.classList.add("active"),Le("onOpen"),Ct(w)),t.config.enableTime===!0&&t.config.noCalendar===!0&&t.config.allowInput===!1&&(T===void 0||!t.timeContainer.contains(T.relatedTarget))&&setTimeout(function(){return t.hourElement.select()},50)}function Vt(T){return function(w){var I=t.config["_"+T+"Date"]=t.parseDate(w,t.config.dateFormat),z=t.config["_"+(T==="min"?"max":"min")+"Date"];I!==void 0&&(t[T==="min"?"minDateHasTime":"maxDateHasTime"]=I.getHours()>0||I.getMinutes()>0||I.getSeconds()>0),t.selectedDates&&(t.selectedDates=t.selectedDates.filter(function(J){return Pe(J)}),!t.selectedDates.length&&T==="min"&&_(I),Ye()),t.daysContainer&&(qe(),I!==void 0?t.currentYearElement[T]=I.getFullYear().toString():t.currentYearElement.removeAttribute(T),t.currentYearElement.disabled=!!z&&I!==void 0&&z.getFullYear()===I.getFullYear())}}function St(){var T=["wrap","weekNumbers","allowInput","allowInvalidPreload","clickOpens","time_24hr","enableTime","noCalendar","altInput","shorthandCurrentMonth","inline","static","enableSeconds","disableMobile"],w=__assign(__assign({},JSON.parse(JSON.stringify(n.dataset||{}))),e),I={};t.config.parseDate=w.parseDate,t.config.formatDate=w.formatDate,Object.defineProperty(t.config,"enable",{get:function(){return t.config._enable},set:function(he){t.config._enable=sn(he)}}),Object.defineProperty(t.config,"disable",{get:function(){return t.config._disable},set:function(he){t.config._disable=sn(he)}});var z=w.mode==="time";if(!w.dateFormat&&(w.enableTime||z)){var J=flatpickr.defaultConfig.dateFormat||defaults$1.dateFormat;I.dateFormat=w.noCalendar||z?"H:i"+(w.enableSeconds?":S":""):J+" H:i"+(w.enableSeconds?":S":"")}if(w.altInput&&(w.enableTime||z)&&!w.altFormat){var ie=flatpickr.defaultConfig.altFormat||defaults$1.altFormat;I.altFormat=w.noCalendar||z?"h:i"+(w.enableSeconds?":S K":" K"):ie+(" h:i"+(w.enableSeconds?":S":"")+" K")}Object.defineProperty(t.config,"minDate",{get:function(){return t.config._minDate},set:Vt("min")}),Object.defineProperty(t.config,"maxDate",{get:function(){return t.config._maxDate},set:Vt("max")});var ye=function(he){return function(Ne){t.config[he==="min"?"_minTime":"_maxTime"]=t.parseDate(Ne,"H:i:S")}};Object.defineProperty(t.config,"minTime",{get:function(){return t.config._minTime},set:ye("min")}),Object.defineProperty(t.config,"maxTime",{get:function(){return t.config._maxTime},set:ye("max")}),w.mode==="time"&&(t.config.noCalendar=!0,t.config.enableTime=!0),Object.assign(t.config,I,w);for(var se=0;se<T.length;se++)t.config[T[se]]=t.config[T[se]]===!0||t.config[T[se]]==="true";HOOKS.filter(function(he){return t.config[he]!==void 0}).forEach(function(he){t.config[he]=arrayify(t.config[he]||[]).map(s)}),t.isMobile=!t.config.disableMobile&&!t.config.inline&&t.config.mode==="single"&&!t.config.disable.length&&!t.config.enable&&!t.config.weekNumbers&&/Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);for(var se=0;se<t.config.plugins.length;se++){var ve=t.config.plugins[se](t)||{};for(var ce in ve)HOOKS.indexOf(ce)>-1?t.config[ce]=arrayify(ve[ce]).map(s).concat(t.config[ce]):typeof w[ce]>"u"&&(t.config[ce]=ve[ce])}w.altInputClass||(t.config.altInputClass=dt().className+" "+t.config.altInputClass),Le("onParseConfig")}function dt(){return t.config.wrap?n.querySelector("[data-input]"):n}function Je(){typeof t.config.locale!="object"&&typeof flatpickr.l10ns[t.config.locale]>"u"&&t.config.errorHandler(new Error("flatpickr: invalid locale "+t.config.locale)),t.l10n=__assign(__assign({},flatpickr.l10ns.default),typeof t.config.locale=="object"?t.config.locale:t.config.locale!=="default"?flatpickr.l10ns[t.config.locale]:void 0),tokenRegex.D="("+t.l10n.weekdays.shorthand.join("|")+")",tokenRegex.l="("+t.l10n.weekdays.longhand.join("|")+")",tokenRegex.M="("+t.l10n.months.shorthand.join("|")+")",tokenRegex.F="("+t.l10n.months.longhand.join("|")+")",tokenRegex.K="("+t.l10n.amPM[0]+"|"+t.l10n.amPM[1]+"|"+t.l10n.amPM[0].toLowerCase()+"|"+t.l10n.amPM[1].toLowerCase()+")";var T=__assign(__assign({},e),JSON.parse(JSON.stringify(n.dataset||{})));T.time_24hr===void 0&&flatpickr.defaultConfig.time_24hr===void 0&&(t.config.time_24hr=t.l10n.time_24hr),t.formatDate=createDateFormatter(t),t.parseDate=createDateParser({config:t.config,l10n:t.l10n})}function Ct(T){if(typeof t.config.position=="function")return void t.config.position(t,T);if(t.calendarContainer!==void 0){Le("onPreCalendarPosition");var w=T||t._positionElement,I=Array.prototype.reduce.call(t.calendarContainer.children,(function(hn,xn){return hn+xn.offsetHeight}),0),z=t.calendarContainer.offsetWidth,J=t.config.position.split(" "),ie=J[0],ye=J.length>1?J[1]:null,se=w.getBoundingClientRect(),ve=window.innerHeight-se.bottom,ce=ie==="above"||ie!=="below"&&ve<I&&se.top>I,he=window.pageYOffset+se.top+(ce?-I-2:w.offsetHeight+2);if(toggleClass(t.calendarContainer,"arrowTop",!ce),toggleClass(t.calendarContainer,"arrowBottom",ce),!t.config.inline){var Ne=window.pageXOffset+se.left,rt=!1,Ge=!1;ye==="center"?(Ne-=(z-se.width)/2,rt=!0):ye==="right"&&(Ne-=z-se.width,Ge=!0),toggleClass(t.calendarContainer,"arrowLeft",!rt&&!Ge),toggleClass(t.calendarContainer,"arrowCenter",rt),toggleClass(t.calendarContainer,"arrowRight",Ge);var wt=window.document.body.offsetWidth-(window.pageXOffset+se.right),Ot=Ne+z>window.document.body.offsetWidth,yn=wt+z>window.document.body.offsetWidth;if(toggleClass(t.calendarContainer,"rightMost",Ot),!t.config.static)if(t.calendarContainer.style.top=he+"px",!Ot)t.calendarContainer.style.left=Ne+"px",t.calendarContainer.style.right="auto";else if(!yn)t.calendarContainer.style.left="auto",t.calendarContainer.style.right=wt+"px";else{var Ut=lt();if(Ut===void 0)return;var En=window.document.body.offsetWidth,$t=Math.max(0,En/2-z/2),dn=".flatpickr-calendar.centerMost:before",Qt=".flatpickr-calendar.centerMost:after",Jt=Ut.cssRules.length,zt="{left:"+se.left+"px;right:auto;}";toggleClass(t.calendarContainer,"rightMost",!1),toggleClass(t.calendarContainer,"centerMost",!0),Ut.insertRule(dn+","+Qt+zt,Jt),t.calendarContainer.style.left=$t+"px",t.calendarContainer.style.right="auto"}}}}function lt(){for(var T=null,w=0;w<document.styleSheets.length;w++){var I=document.styleSheets[w];if(I.cssRules){try{I.cssRules}catch{continue}T=I;break}}return T??At()}function At(){var T=document.createElement("style");return document.head.appendChild(T),T.sheet}function qe(){t.config.noCalendar||t.isMobile||(Q(),Pt(),ne())}function nt(){t._input.focus(),window.navigator.userAgent.indexOf("MSIE")!==-1||navigator.msMaxTouchPoints!==void 0?setTimeout(t.close,0):t.close()}function it(T){T.preventDefault(),T.stopPropagation();var w=function(he){return he.classList&&he.classList.contains("flatpickr-day")&&!he.classList.contains("flatpickr-disabled")&&!he.classList.contains("notAllowed")},I=findParent(getEventTarget(T),w);if(I!==void 0){var z=I,J=t.latestSelectedDateObj=new Date(z.dateObj.getTime()),ie=(J.getMonth()<t.currentMonth||J.getMonth()>t.currentMonth+t.config.showMonths-1)&&t.config.mode!=="range";if(t.selectedDateElem=z,t.config.mode==="single")t.selectedDates=[J];else if(t.config.mode==="multiple"){var ye=Tt(J);ye?t.selectedDates.splice(parseInt(ye),1):t.selectedDates.push(J)}else t.config.mode==="range"&&(t.selectedDates.length===2&&t.clear(!1,!1),t.latestSelectedDateObj=J,t.selectedDates.push(J),compareDates(J,t.selectedDates[0],!0)!==0&&t.selectedDates.sort(function(he,Ne){return he.getTime()-Ne.getTime()}));if(p(),ie){var se=t.currentYear!==J.getFullYear();t.currentYear=J.getFullYear(),t.currentMonth=J.getMonth(),se&&(Le("onYearChange"),Q()),Le("onMonthChange")}if(Pt(),ne(),Ye(),!ie&&t.config.mode!=="range"&&t.config.showMonths===1?g(z):t.selectedDateElem!==void 0&&t.hourElement===void 0&&t.selectedDateElem&&t.selectedDateElem.focus(),t.hourElement!==void 0&&t.hourElement!==void 0&&t.hourElement.focus(),t.config.closeOnSelect){var ve=t.config.mode==="single"&&!t.config.enableTime,ce=t.config.mode==="range"&&t.selectedDates.length===2&&!t.config.enableTime;(ve||ce)&&nt()}C()}}var ue={locale:[Je,xe],showMonths:[re,l,$e],minDate:[M],maxDate:[M],positionElement:[Dt],clickOpens:[function(){t.config.clickOpens===!0?(E(t._input,"focus",t.open),E(t._input,"click",t.open)):(t._input.removeEventListener("focus",t.open),t._input.removeEventListener("click",t.open))}]};function We(T,w){if(T!==null&&typeof T=="object"){Object.assign(t.config,T);for(var I in T)ue[I]!==void 0&&ue[I].forEach(function(z){return z()})}else t.config[T]=w,ue[T]!==void 0?ue[T].forEach(function(z){return z()}):HOOKS.indexOf(T)>-1&&(t.config[T]=arrayify(w));t.redraw(),Ye(!0)}function kt(T,w){var I=[];if(T instanceof Array)I=T.map(function(z){return t.parseDate(z,w)});else if(T instanceof Date||typeof T=="number")I=[t.parseDate(T,w)];else if(typeof T=="string")switch(t.config.mode){case"single":case"time":I=[t.parseDate(T,w)];break;case"multiple":I=T.split(t.config.conjunction).map(function(z){return t.parseDate(z,w)});break;case"range":I=T.split(t.l10n.rangeSeparator).map(function(z){return t.parseDate(z,w)});break}else t.config.errorHandler(new Error("Invalid date supplied: "+JSON.stringify(T)));t.selectedDates=t.config.allowInvalidPreload?I:I.filter(function(z){return z instanceof Date&&Pe(z,!1)}),t.config.mode==="range"&&t.selectedDates.sort(function(z,J){return z.getTime()-J.getTime()})}function Wt(T,w,I){if(w===void 0&&(w=!1),I===void 0&&(I=t.config.dateFormat),T!==0&&!T||T instanceof Array&&T.length===0)return t.clear(w);kt(T,I),t.latestSelectedDateObj=t.selectedDates[t.selectedDates.length-1],t.redraw(),M(void 0,w),_(),t.selectedDates.length===0&&t.clear(!1),Ye(w),w&&Le("onChange")}function sn(T){return T.slice().map(function(w){return typeof w=="string"||typeof w=="number"||w instanceof Date?t.parseDate(w,void 0,!0):w&&typeof w=="object"&&w.from&&w.to?{from:t.parseDate(w.from,void 0),to:t.parseDate(w.to,void 0)}:w}).filter(function(w){return w})}function ln(){t.selectedDates=[],t.now=t.parseDate(t.config.now)||new Date;var T=t.config.defaultDate||((t.input.nodeName==="INPUT"||t.input.nodeName==="TEXTAREA")&&t.input.placeholder&&t.input.value===t.input.placeholder?null:t.input.value);T&&kt(T,t.config.dateFormat),t._initialDate=t.selectedDates.length>0?t.selectedDates[0]:t.config.minDate&&t.config.minDate.getTime()>t.now.getTime()?t.config.minDate:t.config.maxDate&&t.config.maxDate.getTime()<t.now.getTime()?t.config.maxDate:t.now,t.currentYear=t._initialDate.getFullYear(),t.currentMonth=t._initialDate.getMonth(),t.selectedDates.length>0&&(t.latestSelectedDateObj=t.selectedDates[0]),t.config.minTime!==void 0&&(t.config.minTime=t.parseDate(t.config.minTime,"H:i")),t.config.maxTime!==void 0&&(t.config.maxTime=t.parseDate(t.config.maxTime,"H:i")),t.minDateHasTime=!!t.config.minDate&&(t.config.minDate.getHours()>0||t.config.minDate.getMinutes()>0||t.config.minDate.getSeconds()>0),t.maxDateHasTime=!!t.config.maxDate&&(t.config.maxDate.getHours()>0||t.config.maxDate.getMinutes()>0||t.config.maxDate.getSeconds()>0)}function cn(){if(t.input=dt(),!t.input){t.config.errorHandler(new Error("Invalid input element specified"));return}t.input._type=t.input.type,t.input.type="text",t.input.classList.add("flatpickr-input"),t._input=t.input,t.config.altInput&&(t.altInput=createElement(t.input.nodeName,t.config.altInputClass),t._input=t.altInput,t.altInput.placeholder=t.input.placeholder,t.altInput.disabled=t.input.disabled,t.altInput.required=t.input.required,t.altInput.tabIndex=t.input.tabIndex,t.altInput.type="text",t.input.setAttribute("type","hidden"),!t.config.static&&t.input.parentNode&&t.input.parentNode.insertBefore(t.altInput,t.input.nextSibling)),t.config.allowInput||t._input.setAttribute("readonly","readonly"),Dt()}function Dt(){t._positionElement=t.config.positionElement||t._input}function ct(){var T=t.config.enableTime?t.config.noCalendar?"time":"datetime-local":"date";t.mobileInput=createElement("input",t.input.className+" flatpickr-mobile"),t.mobileInput.tabIndex=1,t.mobileInput.type=T,t.mobileInput.disabled=t.input.disabled,t.mobileInput.required=t.input.required,t.mobileInput.placeholder=t.input.placeholder,t.mobileFormatStr=T==="datetime-local"?"Y-m-d\\TH:i:S":T==="date"?"Y-m-d":"H:i:S",t.selectedDates.length>0&&(t.mobileInput.defaultValue=t.mobileInput.value=t.formatDate(t.selectedDates[0],t.mobileFormatStr)),t.config.minDate&&(t.mobileInput.min=t.formatDate(t.config.minDate,"Y-m-d")),t.config.maxDate&&(t.mobileInput.max=t.formatDate(t.config.maxDate,"Y-m-d")),t.input.getAttribute("step")&&(t.mobileInput.step=String(t.input.getAttribute("step"))),t.input.type="hidden",t.altInput!==void 0&&(t.altInput.type="hidden");try{t.input.parentNode&&t.input.parentNode.insertBefore(t.mobileInput,t.input.nextSibling)}catch{}E(t.mobileInput,"change",function(w){t.setDate(getEventTarget(w).value,!1,t.mobileFormatStr),Le("onChange"),Le("onClose")})}function bt(T){if(t.isOpen===!0)return t.close();t.open(T)}function Le(T,w){if(t.config!==void 0){var I=t.config[T];if(I!==void 0&&I.length>0)for(var z=0;I[z]&&z<I.length;z++)I[z](t.selectedDates,t.input.value,t,w);T==="onChange"&&(t.input.dispatchEvent(Gt("change")),t.input.dispatchEvent(Gt("input")))}}function Gt(T){var w=document.createEvent("Event");return w.initEvent(T,!0,!0),w}function Tt(T){for(var w=0;w<t.selectedDates.length;w++){var I=t.selectedDates[w];if(I instanceof Date&&compareDates(I,T)===0)return""+w}return!1}function un(T){return t.config.mode!=="range"||t.selectedDates.length<2?!1:compareDates(T,t.selectedDates[0])>=0&&compareDates(T,t.selectedDates[1])<=0}function Pt(){t.config.noCalendar||t.isMobile||!t.monthNav||(t.yearElements.forEach(function(T,w){var I=new Date(t.currentYear,t.currentMonth,1);I.setMonth(t.currentMonth+w),t.config.showMonths>1||t.config.monthSelectorType==="static"?t.monthElements[w].textContent=monthToStr(I.getMonth(),t.config.shorthandCurrentMonth,t.l10n)+" ":t.monthsDropdownContainer.value=I.getMonth().toString(),T.value=I.getFullYear().toString()}),t._hidePrevMonthArrow=t.config.minDate!==void 0&&(t.currentYear===t.config.minDate.getFullYear()?t.currentMonth<=t.config.minDate.getMonth():t.currentYear<t.config.minDate.getFullYear()),t._hideNextMonthArrow=t.config.maxDate!==void 0&&(t.currentYear===t.config.maxDate.getFullYear()?t.currentMonth+1>t.config.maxDate.getMonth():t.currentYear>t.config.maxDate.getFullYear()))}function Xt(T){var w=T||(t.config.altInput?t.config.altFormat:t.config.dateFormat);return t.selectedDates.map(function(I){return t.formatDate(I,w)}).filter(function(I,z,J){return t.config.mode!=="range"||t.config.enableTime||J.indexOf(I)===z}).join(t.config.mode!=="range"?t.config.conjunction:t.l10n.rangeSeparator)}function Ye(T){T===void 0&&(T=!0),t.mobileInput!==void 0&&t.mobileFormatStr&&(t.mobileInput.value=t.latestSelectedDateObj!==void 0?t.formatDate(t.latestSelectedDateObj,t.mobileFormatStr):""),t.input.value=Xt(t.config.dateFormat),t.altInput!==void 0&&(t.altInput.value=Xt(t.config.altFormat)),T!==!1&&Le("onValueUpdate")}function It(T){var w=getEventTarget(T),I=t.prevMonthNav.contains(w),z=t.nextMonthNav.contains(w);I||z?Re(I?-1:1):t.yearElements.indexOf(w)>=0?w.select():w.classList.contains("arrowUp")?t.changeYear(t.currentYear+1):w.classList.contains("arrowDown")&&t.changeYear(t.currentYear-1)}function fn(T){T.preventDefault();var w=T.type==="keydown",I=getEventTarget(T),z=I;t.amPM!==void 0&&I===t.amPM&&(t.amPM.textContent=t.l10n.amPM[int(t.amPM.textContent===t.l10n.amPM[0])]);var J=parseFloat(z.getAttribute("min")),ie=parseFloat(z.getAttribute("max")),ye=parseFloat(z.getAttribute("step")),se=parseInt(z.value,10),ve=T.delta||(w?T.which===38?1:-1:0),ce=se+ye*ve;if(typeof z.value<"u"&&z.value.length===2){var he=z===t.hourElement,Ne=z===t.minuteElement;ce<J?(ce=ie+ce+int(!he)+(int(he)&&int(!t.amPM)),Ne&&P(void 0,-1,t.hourElement)):ce>ie&&(ce=z===t.hourElement?ce-ie-int(!t.amPM):J,Ne&&P(void 0,1,t.hourElement)),t.amPM&&he&&(ye===1?ce+se===23:Math.abs(ce-se)>ye)&&(t.amPM.textContent=t.l10n.amPM[int(t.amPM.textContent===t.l10n.amPM[0])]),z.value=pad(ce)}}return a(),t}function _flatpickr(n,e){for(var t=Array.prototype.slice.call(n).filter(function(s){return s instanceof HTMLElement}),r=[],a=0;a<t.length;a++){var o=t[a];try{if(o.getAttribute("data-fp-omit")!==null)continue;o._flatpickr!==void 0&&(o._flatpickr.destroy(),o._flatpickr=void 0),o._flatpickr=FlatpickrInstance(o,e||{}),r.push(o._flatpickr)}catch(s){console.error(s)}}return r.length===1?r[0]:r}typeof HTMLElement<"u"&&typeof HTMLCollection<"u"&&typeof NodeList<"u"&&(HTMLCollection.prototype.flatpickr=NodeList.prototype.flatpickr=function(n){return _flatpickr(this,n)},HTMLElement.prototype.flatpickr=function(n){return _flatpickr([this],n)});var flatpickr=function(n,e){return typeof n=="string"?_flatpickr(window.document.querySelectorAll(n),e):n instanceof Node?_flatpickr([n],e):_flatpickr(n,e)};flatpickr.defaultConfig={};flatpickr.l10ns={en:__assign({},english),default:__assign({},english)};flatpickr.localize=function(n){flatpickr.l10ns.default=__assign(__assign({},flatpickr.l10ns.default),n)};flatpickr.setDefaults=function(n){flatpickr.defaultConfig=__assign(__assign({},flatpickr.defaultConfig),n)};flatpickr.parseDate=createDateParser({});flatpickr.formatDate=createDateFormatter({});flatpickr.compareDates=compareDates;typeof jQuery<"u"&&typeof jQuery.fn<"u"&&(jQuery.fn.flatpickr=function(n){return _flatpickr(this,n)});Date.prototype.fp_incr=function(n){return new Date(this.getFullYear(),this.getMonth(),this.getDate()+(typeof n=="string"?parseInt(n,10):n))};typeof window<"u"&&(window.flatpickr=flatpickr);function initDateSelector(){flatpickr(".datepicker",{allowInput:!0})}function getDefaultExportFromCjs(n){return n&&n.__esModule&&Object.prototype.hasOwnProperty.call(n,"default")?n.default:n}var jquery$1={exports:{}};var jquery=jquery$1.exports,hasRequiredJquery;function requireJquery(){return hasRequiredJquery||(hasRequiredJquery=1,(function(n){(function(e,t){n.exports=e.document?t(e,!0):function(r){if(!r.document)throw new Error("jQuery requires a window with a document");return t(r)}})(typeof window<"u"?window:jquery,function(e,t){var r=[],a=Object.getPrototypeOf,o=r.slice,s=r.flat?function(u){return r.flat.call(u)}:function(u){return r.concat.apply([],u)},l=r.push,c=r.indexOf,f={},d=f.toString,p=f.hasOwnProperty,_=p.toString,b=_.call(Object),y={},E=function(h){return typeof h=="function"&&typeof h.nodeType!="number"&&typeof h.item!="function"},C=function(h){return h!=null&&h===h.window},D=e.document,M={type:!0,src:!0,nonce:!0,noModule:!0};function F(u,h,m){m=m||D;var v,x,S=m.createElement("script");if(S.text=u,h)for(v in M)x=h[v]||h.getAttribute&&h.getAttribute(v),x&&S.setAttribute(v,x);m.head.appendChild(S).parentNode.removeChild(S)}function P(u){return u==null?u+"":typeof u=="object"||typeof u=="function"?f[d.call(u)]||"object":typeof u}var H="3.7.1",B=/HTML$/i,g=function(u,h){return new g.fn.init(u,h)};g.fn=g.prototype={jquery:H,constructor:g,length:0,toArray:function(){return o.call(this)},get:function(u){return u==null?o.call(this):u<0?this[u+this.length]:this[u]},pushStack:function(u){var h=g.merge(this.constructor(),u);return h.prevObject=this,h},each:function(u){return g.each(this,u)},map:function(u){return this.pushStack(g.map(this,function(h,m){return u.call(h,m,h)}))},slice:function(){return this.pushStack(o.apply(this,arguments))},first:function(){return this.eq(0)},last:function(){return this.eq(-1)},even:function(){return this.pushStack(g.grep(this,function(u,h){return(h+1)%2}))},odd:function(){return this.pushStack(g.grep(this,function(u,h){return h%2}))},eq:function(u){var h=this.length,m=+u+(u<0?h:0);return this.pushStack(m>=0&&m<h?[this[m]]:[])},end:function(){return this.prevObject||this.constructor()},push:l,sort:r.sort,splice:r.splice},g.extend=g.fn.extend=function(){var u,h,m,v,x,S,A=arguments[0]||{},N=1,L=arguments.length,R=!1;for(typeof A=="boolean"&&(R=A,A=arguments[N]||{},N++),typeof A!="object"&&!E(A)&&(A={}),N===L&&(A=this,N--);N<L;N++)if((u=arguments[N])!=null)for(h in u)v=u[h],!(h==="__proto__"||A===v)&&(R&&v&&(g.isPlainObject(v)||(x=Array.isArray(v)))?(m=A[h],x&&!Array.isArray(m)?S=[]:!x&&!g.isPlainObject(m)?S={}:S=m,x=!1,A[h]=g.extend(R,S,v)):v!==void 0&&(A[h]=v));return A},g.extend({expando:"jQuery"+(H+Math.random()).replace(/\D/g,""),isReady:!0,error:function(u){throw new Error(u)},noop:function(){},isPlainObject:function(u){var h,m;return!u||d.call(u)!=="[object Object]"?!1:(h=a(u),h?(m=p.call(h,"constructor")&&h.constructor,typeof m=="function"&&_.call(m)===b):!0)},isEmptyObject:function(u){var h;for(h in u)return!1;return!0},globalEval:function(u,h,m){F(u,{nonce:h&&h.nonce},m)},each:function(u,h){var m,v=0;if(q(u))for(m=u.length;v<m&&h.call(u[v],v,u[v])!==!1;v++);else for(v in u)if(h.call(u[v],v,u[v])===!1)break;return u},text:function(u){var h,m="",v=0,x=u.nodeType;if(!x)for(;h=u[v++];)m+=g.text(h);return x===1||x===11?u.textContent:x===9?u.documentElement.textContent:x===3||x===4?u.nodeValue:m},makeArray:function(u,h){var m=h||[];return u!=null&&(q(Object(u))?g.merge(m,typeof u=="string"?[u]:u):l.call(m,u)),m},inArray:function(u,h,m){return h==null?-1:c.call(h,u,m)},isXMLDoc:function(u){var h=u&&u.namespaceURI,m=u&&(u.ownerDocument||u).documentElement;return!B.test(h||m&&m.nodeName||"HTML")},merge:function(u,h){for(var m=+h.length,v=0,x=u.length;v<m;v++)u[x++]=h[v];return u.length=x,u},grep:function(u,h,m){for(var v,x=[],S=0,A=u.length,N=!m;S<A;S++)v=!h(u[S],S),v!==N&&x.push(u[S]);return x},map:function(u,h,m){var v,x,S=0,A=[];if(q(u))for(v=u.length;S<v;S++)x=h(u[S],S,m),x!=null&&A.push(x);else for(S in u)x=h(u[S],S,m),x!=null&&A.push(x);return s(A)},guid:1,support:y}),typeof Symbol=="function"&&(g.fn[Symbol.iterator]=r[Symbol.iterator]),g.each("Boolean Number String Function Array Date RegExp Object Error Symbol".split(" "),function(u,h){f["[object "+h+"]"]=h.toLowerCase()});function q(u){var h=!!u&&"length"in u&&u.length,m=P(u);return E(u)||C(u)?!1:m==="array"||h===0||typeof h=="number"&&h>0&&h-1 in u}function G(u,h){return u.nodeName&&u.nodeName.toLowerCase()===h.toLowerCase()}var Z=r.pop,te=r.sort,ne=r.splice,Q="[\\x20\\t\\r\\n\\f]",Ee=new RegExp("^"+Q+"+|((?:^|[^\\\\])(?:\\\\.)*)"+Q+"+$","g");g.contains=function(u,h){var m=h&&h.parentNode;return u===m||!!(m&&m.nodeType===1&&(u.contains?u.contains(m):u.compareDocumentPosition&&u.compareDocumentPosition(m)&16))};var re=/([\0-\x1f\x7f]|^-?\d)|^-$|[^\x80-\uFFFF\w-]/g;function de(u,h){return h?u==="\0"?"�":u.slice(0,-1)+"\\"+u.charCodeAt(u.length-1).toString(16)+" ":"\\"+u}g.escapeSelector=function(u){return(u+"").replace(re,de)};var le=D,$e=l;(function(){var u,h,m,v,x,S=$e,A,N,L,R,U,K=g.expando,V=0,X=0,_e=mn(),we=mn(),Se=mn(),ze=mn(),Ue=function(O,k){return O===k&&(x=!0),0},ht="checked|selected|async|autofocus|autoplay|controls|defer|disabled|hidden|ismap|loop|multiple|open|readonly|required|scoped",pt="(?:\\\\[\\da-fA-F]{1,6}"+Q+"?|\\\\[^\\r\\n\\f]|[\\w-]|[^\0-\\x7f])+",De="\\["+Q+"*("+pt+")(?:"+Q+"*([*^$|!~]?=)"+Q+`*(?:'((?:\\\\.|[^\\\\'])*)'|"((?:\\\\.|[^\\\\"])*)"|(`+pt+"))|)"+Q+"*\\]",Ht=":("+pt+`)(?:\\((('((?:\\\\.|[^\\\\'])*)'|"((?:\\\\.|[^\\\\"])*)")|((?:\\\\.|[^\\\\()[\\]]|`+De+")*)|.*)\\)|)",Oe=new RegExp(Q+"+","g"),Be=new RegExp("^"+Q+"*,"+Q+"*"),rn=new RegExp("^"+Q+"*([>+~]|"+Q+")"+Q+"*"),Nn=new RegExp(Q+"|>"),gt=new RegExp(Ht),an=new RegExp("^"+pt+"$"),mt={ID:new RegExp("^#("+pt+")"),CLASS:new RegExp("^\\.("+pt+")"),TAG:new RegExp("^("+pt+"|[*])"),ATTR:new RegExp("^"+De),PSEUDO:new RegExp("^"+Ht),CHILD:new RegExp("^:(only|first|last|nth|nth-last)-(child|of-type)(?:\\("+Q+"*(even|odd|(([+-]|)(\\d*)n|)"+Q+"*(?:([+-]|)"+Q+"*(\\d+)|))"+Q+"*\\)|)","i"),bool:new RegExp("^(?:"+ht+")$","i"),needsContext:new RegExp("^"+Q+"*[>+~]|:(even|odd|eq|gt|lt|nth|first|last)(?:\\("+Q+"*((?:-\\d)?\\d*)"+Q+"*\\)|)(?=[^-]|$)","i")},Mt=/^(?:input|select|textarea|button)$/i,Lt=/^h\d$/i,at=/^(?:#([\w-]+)|(\w+)|\.([\w-]+))$/,kn=/[+~]/,yt=new RegExp("\\\\[\\da-fA-F]{1,6}"+Q+"?|\\\\([^\\r\\n\\f])","g"),Et=function(O,k){var j="0x"+O.slice(1)-65536;return k||(j<0?String.fromCharCode(j+65536):String.fromCharCode(j>>10|55296,j&1023|56320))},Pi=function(){Nt()},Ii=vn(function(O){return O.disabled===!0&&G(O,"fieldset")},{dir:"parentNode",next:"legend"});function Ri(){try{return A.activeElement}catch{}}try{S.apply(r=o.call(le.childNodes),le.childNodes),r[le.childNodes.length].nodeType}catch{S={apply:function(k,j){$e.apply(k,o.call(j))},call:function(k){$e.apply(k,o.call(arguments,1))}}}function ke(O,k,j,W){var Y,ee,ae,fe,oe,Ce,me,be=k&&k.ownerDocument,Ae=k?k.nodeType:9;if(j=j||[],typeof O!="string"||!O||Ae!==1&&Ae!==9&&Ae!==11)return j;if(!W&&(Nt(k),k=k||A,L)){if(Ae!==11&&(oe=at.exec(O)))if(Y=oe[1]){if(Ae===9)if(ae=k.getElementById(Y)){if(ae.id===Y)return S.call(j,ae),j}else return j;else if(be&&(ae=be.getElementById(Y))&&ke.contains(k,ae)&&ae.id===Y)return S.call(j,ae),j}else{if(oe[2])return S.apply(j,k.getElementsByTagName(O)),j;if((Y=oe[3])&&k.getElementsByClassName)return S.apply(j,k.getElementsByClassName(Y)),j}if(!ze[O+" "]&&(!R||!R.test(O))){if(me=O,be=k,Ae===1&&(Nn.test(O)||rn.test(O))){for(be=kn.test(O)&&Pn(k.parentNode)||k,(be!=k||!y.scope)&&((fe=k.getAttribute("id"))?fe=g.escapeSelector(fe):k.setAttribute("id",fe=K)),Ce=on(O),ee=Ce.length;ee--;)Ce[ee]=(fe?"#"+fe:":scope")+" "+_n(Ce[ee]);me=Ce.join(",")}try{return S.apply(j,be.querySelectorAll(me)),j}catch{ze(O,!0)}finally{fe===K&&k.removeAttribute("id")}}}return si(O.replace(Ee,"$1"),k,j,W)}function mn(){var O=[];function k(j,W){return O.push(j+" ")>h.cacheLength&&delete k[O.shift()],k[j+" "]=W}return k}function ft(O){return O[K]=!0,O}function Yt(O){var k=A.createElement("fieldset");try{return!!O(k)}catch{return!1}finally{k.parentNode&&k.parentNode.removeChild(k),k=null}}function Fi(O){return function(k){return G(k,"input")&&k.type===O}}function Hi(O){return function(k){return(G(k,"input")||G(k,"button"))&&k.type===O}}function ai(O){return function(k){return"form"in k?k.parentNode&&k.disabled===!1?"label"in k?"label"in k.parentNode?k.parentNode.disabled===O:k.disabled===O:k.isDisabled===O||k.isDisabled!==!O&&Ii(k)===O:k.disabled===O:"label"in k?k.disabled===O:!1}}function Bt(O){return ft(function(k){return k=+k,ft(function(j,W){for(var Y,ee=O([],j.length,k),ae=ee.length;ae--;)j[Y=ee[ae]]&&(j[Y]=!(W[Y]=j[Y]))})})}function Pn(O){return O&&typeof O.getElementsByTagName<"u"&&O}function Nt(O){var k,j=O?O.ownerDocument||O:le;return j==A||j.nodeType!==9||!j.documentElement||(A=j,N=A.documentElement,L=!g.isXMLDoc(A),U=N.matches||N.webkitMatchesSelector||N.msMatchesSelector,N.msMatchesSelector&&le!=A&&(k=A.defaultView)&&k.top!==k&&k.addEventListener("unload",Pi),y.getById=Yt(function(W){return N.appendChild(W).id=g.expando,!A.getElementsByName||!A.getElementsByName(g.expando).length}),y.disconnectedMatch=Yt(function(W){return U.call(W,"*")}),y.scope=Yt(function(){return A.querySelectorAll(":scope")}),y.cssHas=Yt(function(){try{return A.querySelector(":has(*,:jqfake)"),!1}catch{return!0}}),y.getById?(h.filter.ID=function(W){var Y=W.replace(yt,Et);return function(ee){return ee.getAttribute("id")===Y}},h.find.ID=function(W,Y){if(typeof Y.getElementById<"u"&&L){var ee=Y.getElementById(W);return ee?[ee]:[]}}):(h.filter.ID=function(W){var Y=W.replace(yt,Et);return function(ee){var ae=typeof ee.getAttributeNode<"u"&&ee.getAttributeNode("id");return ae&&ae.value===Y}},h.find.ID=function(W,Y){if(typeof Y.getElementById<"u"&&L){var ee,ae,fe,oe=Y.getElementById(W);if(oe){if(ee=oe.getAttributeNode("id"),ee&&ee.value===W)return[oe];for(fe=Y.getElementsByName(W),ae=0;oe=fe[ae++];)if(ee=oe.getAttributeNode("id"),ee&&ee.value===W)return[oe]}return[]}}),h.find.TAG=function(W,Y){return typeof Y.getElementsByTagName<"u"?Y.getElementsByTagName(W):Y.querySelectorAll(W)},h.find.CLASS=function(W,Y){if(typeof Y.getElementsByClassName<"u"&&L)return Y.getElementsByClassName(W)},R=[],Yt(function(W){var Y;N.appendChild(W).innerHTML="<a id='"+K+"' href='' disabled='disabled'></a><select id='"+K+"-\r\\' disabled='disabled'><option selected=''></option></select>",W.querySelectorAll("[selected]").length||R.push("\\["+Q+"*(?:value|"+ht+")"),W.querySelectorAll("[id~="+K+"-]").length||R.push("~="),W.querySelectorAll("a#"+K+"+*").length||R.push(".#.+[+~]"),W.querySelectorAll(":checked").length||R.push(":checked"),Y=A.createElement("input"),Y.setAttribute("type","hidden"),W.appendChild(Y).setAttribute("name","D"),N.appendChild(W).disabled=!0,W.querySelectorAll(":disabled").length!==2&&R.push(":enabled",":disabled"),Y=A.createElement("input"),Y.setAttribute("name",""),W.appendChild(Y),W.querySelectorAll("[name='']").length||R.push("\\["+Q+"*name"+Q+"*="+Q+`*(?:''|"")`)}),y.cssHas||R.push(":has"),R=R.length&&new RegExp(R.join("|")),Ue=function(W,Y){if(W===Y)return x=!0,0;var ee=!W.compareDocumentPosition-!Y.compareDocumentPosition;return ee||(ee=(W.ownerDocument||W)==(Y.ownerDocument||Y)?W.compareDocumentPosition(Y):1,ee&1||!y.sortDetached&&Y.compareDocumentPosition(W)===ee?W===A||W.ownerDocument==le&&ke.contains(le,W)?-1:Y===A||Y.ownerDocument==le&&ke.contains(le,Y)?1:v?c.call(v,W)-c.call(v,Y):0:ee&4?-1:1)}),A}ke.matches=function(O,k){return ke(O,null,null,k)},ke.matchesSelector=function(O,k){if(Nt(O),L&&!ze[k+" "]&&(!R||!R.test(k)))try{var j=U.call(O,k);if(j||y.disconnectedMatch||O.document&&O.document.nodeType!==11)return j}catch{ze(k,!0)}return ke(k,A,null,[O]).length>0},ke.contains=function(O,k){return(O.ownerDocument||O)!=A&&Nt(O),g.contains(O,k)},ke.attr=function(O,k){(O.ownerDocument||O)!=A&&Nt(O);var j=h.attrHandle[k.toLowerCase()],W=j&&p.call(h.attrHandle,k.toLowerCase())?j(O,k,!L):void 0;return W!==void 0?W:O.getAttribute(k)},ke.error=function(O){throw new Error("Syntax error, unrecognized expression: "+O)},g.uniqueSort=function(O){var k,j=[],W=0,Y=0;if(x=!y.sortStable,v=!y.sortStable&&o.call(O,0),te.call(O,Ue),x){for(;k=O[Y++];)k===O[Y]&&(W=j.push(Y));for(;W--;)ne.call(O,j[W],1)}return v=null,O},g.fn.uniqueSort=function(){return this.pushStack(g.uniqueSort(o.apply(this)))},h=g.expr={cacheLength:50,createPseudo:ft,match:mt,attrHandle:{},find:{},relative:{">":{dir:"parentNode",first:!0}," ":{dir:"parentNode"},"+":{dir:"previousSibling",first:!0},"~":{dir:"previousSibling"}},preFilter:{ATTR:function(O){return O[1]=O[1].replace(yt,Et),O[3]=(O[3]||O[4]||O[5]||"").replace(yt,Et),O[2]==="~="&&(O[3]=" "+O[3]+" "),O.slice(0,4)},CHILD:function(O){return O[1]=O[1].toLowerCase(),O[1].slice(0,3)==="nth"?(O[3]||ke.error(O[0]),O[4]=+(O[4]?O[5]+(O[6]||1):2*(O[3]==="even"||O[3]==="odd")),O[5]=+(O[7]+O[8]||O[3]==="odd")):O[3]&&ke.error(O[0]),O},PSEUDO:function(O){var k,j=!O[6]&&O[2];return mt.CHILD.test(O[0])?null:(O[3]?O[2]=O[4]||O[5]||"":j&&gt.test(j)&&(k=on(j,!0))&&(k=j.indexOf(")",j.length-k)-j.length)&&(O[0]=O[0].slice(0,k),O[2]=j.slice(0,k)),O.slice(0,3))}},filter:{TAG:function(O){var k=O.replace(yt,Et).toLowerCase();return O==="*"?function(){return!0}:function(j){return G(j,k)}},CLASS:function(O){var k=_e[O+" "];return k||(k=new RegExp("(^|"+Q+")"+O+"("+Q+"|$)"))&&_e(O,function(j){return k.test(typeof j.className=="string"&&j.className||typeof j.getAttribute<"u"&&j.getAttribute("class")||"")})},ATTR:function(O,k,j){return function(W){var Y=ke.attr(W,O);return Y==null?k==="!=":k?(Y+="",k==="="?Y===j:k==="!="?Y!==j:k==="^="?j&&Y.indexOf(j)===0:k==="*="?j&&Y.indexOf(j)>-1:k==="$="?j&&Y.slice(-j.length)===j:k==="~="?(" "+Y.replace(Oe," ")+" ").indexOf(j)>-1:k==="|="?Y===j||Y.slice(0,j.length+1)===j+"-":!1):!0}},CHILD:function(O,k,j,W,Y){var ee=O.slice(0,3)!=="nth",ae=O.slice(-4)!=="last",fe=k==="of-type";return W===1&&Y===0?function(oe){return!!oe.parentNode}:function(oe,Ce,me){var be,Ae,pe,Ie,et,Ke=ee!==ae?"nextSibling":"previousSibling",ot=oe.parentNode,_t=fe&&oe.nodeName.toLowerCase(),Kt=!me&&!fe,Xe=!1;if(ot){if(ee){for(;Ke;){for(pe=oe;pe=pe[Ke];)if(fe?G(pe,_t):pe.nodeType===1)return!1;et=Ke=O==="only"&&!et&&"nextSibling"}return!0}if(et=[ae?ot.firstChild:ot.lastChild],ae&&Kt){for(Ae=ot[K]||(ot[K]={}),be=Ae[O]||[],Ie=be[0]===V&&be[1],Xe=Ie&&be[2],pe=Ie&&ot.childNodes[Ie];pe=++Ie&&pe&&pe[Ke]||(Xe=Ie=0)||et.pop();)if(pe.nodeType===1&&++Xe&&pe===oe){Ae[O]=[V,Ie,Xe];break}}else if(Kt&&(Ae=oe[K]||(oe[K]={}),be=Ae[O]||[],Ie=be[0]===V&&be[1],Xe=Ie),Xe===!1)for(;(pe=++Ie&&pe&&pe[Ke]||(Xe=Ie=0)||et.pop())&&!((fe?G(pe,_t):pe.nodeType===1)&&++Xe&&(Kt&&(Ae=pe[K]||(pe[K]={}),Ae[O]=[V,Xe]),pe===oe)););return Xe-=Y,Xe===W||Xe%W===0&&Xe/W>=0}}},PSEUDO:function(O,k){var j,W=h.pseudos[O]||h.setFilters[O.toLowerCase()]||ke.error("unsupported pseudo: "+O);return W[K]?W(k):W.length>1?(j=[O,O,"",k],h.setFilters.hasOwnProperty(O.toLowerCase())?ft(function(Y,ee){for(var ae,fe=W(Y,k),oe=fe.length;oe--;)ae=c.call(Y,fe[oe]),Y[ae]=!(ee[ae]=fe[oe])}):function(Y){return W(Y,0,j)}):W}},pseudos:{not:ft(function(O){var k=[],j=[],W=Hn(O.replace(Ee,"$1"));return W[K]?ft(function(Y,ee,ae,fe){for(var oe,Ce=W(Y,null,fe,[]),me=Y.length;me--;)(oe=Ce[me])&&(Y[me]=!(ee[me]=oe))}):function(Y,ee,ae){return k[0]=Y,W(k,null,ae,j),k[0]=null,!j.pop()}}),has:ft(function(O){return function(k){return ke(O,k).length>0}}),contains:ft(function(O){return O=O.replace(yt,Et),function(k){return(k.textContent||g.text(k)).indexOf(O)>-1}}),lang:ft(function(O){return an.test(O||"")||ke.error("unsupported lang: "+O),O=O.replace(yt,Et).toLowerCase(),function(k){var j;do if(j=L?k.lang:k.getAttribute("xml:lang")||k.getAttribute("lang"))return j=j.toLowerCase(),j===O||j.indexOf(O+"-")===0;while((k=k.parentNode)&&k.nodeType===1);return!1}}),target:function(O){var k=e.location&&e.location.hash;return k&&k.slice(1)===O.id},root:function(O){return O===N},focus:function(O){return O===Ri()&&A.hasFocus()&&!!(O.type||O.href||~O.tabIndex)},enabled:ai(!1),disabled:ai(!0),checked:function(O){return G(O,"input")&&!!O.checked||G(O,"option")&&!!O.selected},selected:function(O){return O.parentNode&&O.parentNode.selectedIndex,O.selected===!0},empty:function(O){for(O=O.firstChild;O;O=O.nextSibling)if(O.nodeType<6)return!1;return!0},parent:function(O){return!h.pseudos.empty(O)},header:function(O){return Lt.test(O.nodeName)},input:function(O){return Mt.test(O.nodeName)},button:function(O){return G(O,"input")&&O.type==="button"||G(O,"button")},text:function(O){var k;return G(O,"input")&&O.type==="text"&&((k=O.getAttribute("type"))==null||k.toLowerCase()==="text")},first:Bt(function(){return[0]}),last:Bt(function(O,k){return[k-1]}),eq:Bt(function(O,k,j){return[j<0?j+k:j]}),even:Bt(function(O,k){for(var j=0;j<k;j+=2)O.push(j);return O}),odd:Bt(function(O,k){for(var j=1;j<k;j+=2)O.push(j);return O}),lt:Bt(function(O,k,j){var W;for(j<0?W=j+k:j>k?W=k:W=j;--W>=0;)O.push(W);return O}),gt:Bt(function(O,k,j){for(var W=j<0?j+k:j;++W<k;)O.push(W);return O})}},h.pseudos.nth=h.pseudos.eq;for(u in{radio:!0,checkbox:!0,file:!0,password:!0,image:!0})h.pseudos[u]=Fi(u);for(u in{submit:!0,reset:!0})h.pseudos[u]=Hi(u);function oi(){}oi.prototype=h.filters=h.pseudos,h.setFilters=new oi;function on(O,k){var j,W,Y,ee,ae,fe,oe,Ce=we[O+" "];if(Ce)return k?0:Ce.slice(0);for(ae=O,fe=[],oe=h.preFilter;ae;){(!j||(W=Be.exec(ae)))&&(W&&(ae=ae.slice(W[0].length)||ae),fe.push(Y=[])),j=!1,(W=rn.exec(ae))&&(j=W.shift(),Y.push({value:j,type:W[0].replace(Ee," ")}),ae=ae.slice(j.length));for(ee in h.filter)(W=mt[ee].exec(ae))&&(!oe[ee]||(W=oe[ee](W)))&&(j=W.shift(),Y.push({value:j,type:ee,matches:W}),ae=ae.slice(j.length));if(!j)break}return k?ae.length:ae?ke.error(O):we(O,fe).slice(0)}function _n(O){for(var k=0,j=O.length,W="";k<j;k++)W+=O[k].value;return W}function vn(O,k,j){var W=k.dir,Y=k.next,ee=Y||W,ae=j&&ee==="parentNode",fe=X++;return k.first?function(oe,Ce,me){for(;oe=oe[W];)if(oe.nodeType===1||ae)return O(oe,Ce,me);return!1}:function(oe,Ce,me){var be,Ae,pe=[V,fe];if(me){for(;oe=oe[W];)if((oe.nodeType===1||ae)&&O(oe,Ce,me))return!0}else for(;oe=oe[W];)if(oe.nodeType===1||ae)if(Ae=oe[K]||(oe[K]={}),Y&&G(oe,Y))oe=oe[W]||oe;else{if((be=Ae[ee])&&be[0]===V&&be[1]===fe)return pe[2]=be[2];if(Ae[ee]=pe,pe[2]=O(oe,Ce,me))return!0}return!1}}function In(O){return O.length>1?function(k,j,W){for(var Y=O.length;Y--;)if(!O[Y](k,j,W))return!1;return!0}:O[0]}function Bi(O,k,j){for(var W=0,Y=k.length;W<Y;W++)ke(O,k[W],j);return j}function bn(O,k,j,W,Y){for(var ee,ae=[],fe=0,oe=O.length,Ce=k!=null;fe<oe;fe++)(ee=O[fe])&&(!j||j(ee,W,Y))&&(ae.push(ee),Ce&&k.push(fe));return ae}function Rn(O,k,j,W,Y,ee){return W&&!W[K]&&(W=Rn(W)),Y&&!Y[K]&&(Y=Rn(Y,ee)),ft(function(ae,fe,oe,Ce){var me,be,Ae,pe,Ie=[],et=[],Ke=fe.length,ot=ae||Bi(k||"*",oe.nodeType?[oe]:oe,[]),_t=O&&(ae||!k)?bn(ot,Ie,O,oe,Ce):ot;if(j?(pe=Y||(ae?O:Ke||W)?[]:fe,j(_t,pe,oe,Ce)):pe=_t,W)for(me=bn(pe,et),W(me,[],oe,Ce),be=me.length;be--;)(Ae=me[be])&&(pe[et[be]]=!(_t[et[be]]=Ae));if(ae){if(Y||O){if(Y){for(me=[],be=pe.length;be--;)(Ae=pe[be])&&me.push(_t[be]=Ae);Y(null,pe=[],me,Ce)}for(be=pe.length;be--;)(Ae=pe[be])&&(me=Y?c.call(ae,Ae):Ie[be])>-1&&(ae[me]=!(fe[me]=Ae))}}else pe=bn(pe===fe?pe.splice(Ke,pe.length):pe),Y?Y(null,fe,pe,Ce):S.apply(fe,pe)})}function Fn(O){for(var k,j,W,Y=O.length,ee=h.relative[O[0].type],ae=ee||h.relative[" "],fe=ee?1:0,oe=vn(function(be){return be===k},ae,!0),Ce=vn(function(be){return c.call(k,be)>-1},ae,!0),me=[function(be,Ae,pe){var Ie=!ee&&(pe||Ae!=m)||((k=Ae).nodeType?oe(be,Ae,pe):Ce(be,Ae,pe));return k=null,Ie}];fe<Y;fe++)if(j=h.relative[O[fe].type])me=[vn(In(me),j)];else{if(j=h.filter[O[fe].type].apply(null,O[fe].matches),j[K]){for(W=++fe;W<Y&&!h.relative[O[W].type];W++);return Rn(fe>1&&In(me),fe>1&&_n(O.slice(0,fe-1).concat({value:O[fe-2].type===" "?"*":""})).replace(Ee,"$1"),j,fe<W&&Fn(O.slice(fe,W)),W<Y&&Fn(O=O.slice(W)),W<Y&&_n(O))}me.push(j)}return In(me)}function ji(O,k){var j=k.length>0,W=O.length>0,Y=function(ee,ae,fe,oe,Ce){var me,be,Ae,pe=0,Ie="0",et=ee&&[],Ke=[],ot=m,_t=ee||W&&h.find.TAG("*",Ce),Kt=V+=ot==null?1:Math.random()||.1,Xe=_t.length;for(Ce&&(m=ae==A||ae||Ce);Ie!==Xe&&(me=_t[Ie])!=null;Ie++){if(W&&me){for(be=0,!ae&&me.ownerDocument!=A&&(Nt(me),fe=!L);Ae=O[be++];)if(Ae(me,ae||A,fe)){S.call(oe,me);break}Ce&&(V=Kt)}j&&((me=!Ae&&me)&&pe--,ee&&et.push(me))}if(pe+=Ie,j&&Ie!==pe){for(be=0;Ae=k[be++];)Ae(et,Ke,ae,fe);if(ee){if(pe>0)for(;Ie--;)et[Ie]||Ke[Ie]||(Ke[Ie]=Z.call(oe));Ke=bn(Ke)}S.apply(oe,Ke),Ce&&!ee&&Ke.length>0&&pe+k.length>1&&g.uniqueSort(oe)}return Ce&&(V=Kt,m=ot),et};return j?ft(Y):Y}function Hn(O,k){var j,W=[],Y=[],ee=Se[O+" "];if(!ee){for(k||(k=on(O)),j=k.length;j--;)ee=Fn(k[j]),ee[K]?W.push(ee):Y.push(ee);ee=Se(O,ji(Y,W)),ee.selector=O}return ee}function si(O,k,j,W){var Y,ee,ae,fe,oe,Ce=typeof O=="function"&&O,me=!W&&on(O=Ce.selector||O);if(j=j||[],me.length===1){if(ee=me[0]=me[0].slice(0),ee.length>2&&(ae=ee[0]).type==="ID"&&k.nodeType===9&&L&&h.relative[ee[1].type]){if(k=(h.find.ID(ae.matches[0].replace(yt,Et),k)||[])[0],k)Ce&&(k=k.parentNode);else return j;O=O.slice(ee.shift().value.length)}for(Y=mt.needsContext.test(O)?0:ee.length;Y--&&(ae=ee[Y],!h.relative[fe=ae.type]);)if((oe=h.find[fe])&&(W=oe(ae.matches[0].replace(yt,Et),kn.test(ee[0].type)&&Pn(k.parentNode)||k))){if(ee.splice(Y,1),O=W.length&&_n(ee),!O)return S.apply(j,W),j;break}}return(Ce||Hn(O,me))(W,k,!L,j,!k||kn.test(O)&&Pn(k.parentNode)||k),j}y.sortStable=K.split("").sort(Ue).join("")===K,Nt(),y.sortDetached=Yt(function(O){return O.compareDocumentPosition(A.createElement("fieldset"))&1}),g.find=ke,g.expr[":"]=g.expr.pseudos,g.unique=g.uniqueSort,ke.compile=Hn,ke.select=si,ke.setDocument=Nt,ke.tokenize=on,ke.escape=g.escapeSelector,ke.getText=g.text,ke.isXML=g.isXMLDoc,ke.selectors=g.expr,ke.support=g.support,ke.uniqueSort=g.uniqueSort})();var xe=function(u,h,m){for(var v=[],x=m!==void 0;(u=u[h])&&u.nodeType!==9;)if(u.nodeType===1){if(x&&g(u).is(m))break;v.push(u)}return v},Ve=function(u,h){for(var m=[];u;u=u.nextSibling)u.nodeType===1&&u!==h&&m.push(u);return m},Re=g.expr.match.needsContext,Te=/^<([a-z][^\/\0>:\x20\t\r\n\f]*)[\x20\t\r\n\f]*\/?>(?:<\/\1>|)$/i;function je(u,h,m){return E(h)?g.grep(u,function(v,x){return!!h.call(v,x,v)!==m}):h.nodeType?g.grep(u,function(v){return v===h!==m}):typeof h!="string"?g.grep(u,function(v){return c.call(h,v)>-1!==m}):g.filter(h,u,m)}g.filter=function(u,h,m){var v=h[0];return m&&(u=":not("+u+")"),h.length===1&&v.nodeType===1?g.find.matchesSelector(v,u)?[v]:[]:g.find.matches(u,g.grep(h,function(x){return x.nodeType===1}))},g.fn.extend({find:function(u){var h,m,v=this.length,x=this;if(typeof u!="string")return this.pushStack(g(u).filter(function(){for(h=0;h<v;h++)if(g.contains(x[h],this))return!0}));for(m=this.pushStack([]),h=0;h<v;h++)g.find(u,x[h],m);return v>1?g.uniqueSort(m):m},filter:function(u){return this.pushStack(je(this,u||[],!1))},not:function(u){return this.pushStack(je(this,u||[],!0))},is:function(u){return!!je(this,typeof u=="string"&&Re.test(u)?g(u):u||[],!1).length}});var Fe,He=/^(?:\s*(<[\w\W]+>)[^>]*|#([\w-]+))$/,ge=g.fn.init=function(u,h,m){var v,x;if(!u)return this;if(m=m||Fe,typeof u=="string")if(u[0]==="<"&&u[u.length-1]===">"&&u.length>=3?v=[null,u,null]:v=He.exec(u),v&&(v[1]||!h))if(v[1]){if(h=h instanceof g?h[0]:h,g.merge(this,g.parseHTML(v[1],h&&h.nodeType?h.ownerDocument||h:D,!0)),Te.test(v[1])&&g.isPlainObject(h))for(v in h)E(this[v])?this[v](h[v]):this.attr(v,h[v]);return this}else return x=D.getElementById(v[2]),x&&(this[0]=x,this.length=1),this;else return!h||h.jquery?(h||m).find(u):this.constructor(h).find(u);else{if(u.nodeType)return this[0]=u,this.length=1,this;if(E(u))return m.ready!==void 0?m.ready(u):u(g)}return g.makeArray(u,this)};ge.prototype=g.fn,Fe=g(D);var Me=/^(?:parents|prev(?:Until|All))/,Pe={children:!0,contents:!0,next:!0,prev:!0};g.fn.extend({has:function(u){var h=g(u,this),m=h.length;return this.filter(function(){for(var v=0;v<m;v++)if(g.contains(this,h[v]))return!0})},closest:function(u,h){var m,v=0,x=this.length,S=[],A=typeof u!="string"&&g(u);if(!Re.test(u)){for(;v<x;v++)for(m=this[v];m&&m!==h;m=m.parentNode)if(m.nodeType<11&&(A?A.index(m)>-1:m.nodeType===1&&g.find.matchesSelector(m,u))){S.push(m);break}}return this.pushStack(S.length>1?g.uniqueSort(S):S)},index:function(u){return u?typeof u=="string"?c.call(g(u),this[0]):c.call(this,u.jquery?u[0]:u):this[0]&&this[0].parentNode?this.first().prevAll().length:-1},add:function(u,h){return this.pushStack(g.uniqueSort(g.merge(this.get(),g(u,h))))},addBack:function(u){return this.add(u==null?this.prevObject:this.prevObject.filter(u))}});function st(u,h){for(;(u=u[h])&&u.nodeType!==1;);return u}g.each({parent:function(u){var h=u.parentNode;return h&&h.nodeType!==11?h:null},parents:function(u){return xe(u,"parentNode")},parentsUntil:function(u,h,m){return xe(u,"parentNode",m)},next:function(u){return st(u,"nextSibling")},prev:function(u){return st(u,"previousSibling")},nextAll:function(u){return xe(u,"nextSibling")},prevAll:function(u){return xe(u,"previousSibling")},nextUntil:function(u,h,m){return xe(u,"nextSibling",m)},prevUntil:function(u,h,m){return xe(u,"previousSibling",m)},siblings:function(u){return Ve((u.parentNode||{}).firstChild,u)},children:function(u){return Ve(u.firstChild)},contents:function(u){return u.contentDocument!=null&&a(u.contentDocument)?u.contentDocument:(G(u,"template")&&(u=u.content||u),g.merge([],u.childNodes))}},function(u,h){g.fn[u]=function(m,v){var x=g.map(this,h,m);return u.slice(-5)!=="Until"&&(v=m),v&&typeof v=="string"&&(x=g.filter(v,x)),this.length>1&&(Pe[u]||g.uniqueSort(x),Me.test(u)&&x.reverse()),this.pushStack(x)}});var Qe=/[^\x20\t\r\n\f]+/g;function xt(u){var h={};return g.each(u.match(Qe)||[],function(m,v){h[v]=!0}),h}g.Callbacks=function(u){u=typeof u=="string"?xt(u):g.extend({},u);var h,m,v,x,S=[],A=[],N=-1,L=function(){for(x=x||u.once,v=h=!0;A.length;N=-1)for(m=A.shift();++N<S.length;)S[N].apply(m[0],m[1])===!1&&u.stopOnFalse&&(N=S.length,m=!1);u.memory||(m=!1),h=!1,x&&(m?S=[]:S="")},R={add:function(){return S&&(m&&!h&&(N=S.length-1,A.push(m)),(function U(K){g.each(K,function(V,X){E(X)?(!u.unique||!R.has(X))&&S.push(X):X&&X.length&&P(X)!=="string"&&U(X)})})(arguments),m&&!h&&L()),this},remove:function(){return g.each(arguments,function(U,K){for(var V;(V=g.inArray(K,S,V))>-1;)S.splice(V,1),V<=N&&N--}),this},has:function(U){return U?g.inArray(U,S)>-1:S.length>0},empty:function(){return S&&(S=[]),this},disable:function(){return x=A=[],S=m="",this},disabled:function(){return!S},lock:function(){return x=A=[],!m&&!h&&(S=m=""),this},locked:function(){return!!x},fireWith:function(U,K){return x||(K=K||[],K=[U,K.slice?K.slice():K],A.push(K),h||L()),this},fire:function(){return R.fireWith(this,arguments),this},fired:function(){return!!v}};return R};function tt(u){return u}function vt(u){throw u}function jt(u,h,m,v){var x;try{u&&E(x=u.promise)?x.call(u).done(h).fail(m):u&&E(x=u.then)?x.call(u,h,m):h.apply(void 0,[u].slice(v))}catch(S){m.apply(void 0,[S])}}g.extend({Deferred:function(u){var h=[["notify","progress",g.Callbacks("memory"),g.Callbacks("memory"),2],["resolve","done",g.Callbacks("once memory"),g.Callbacks("once memory"),0,"resolved"],["reject","fail",g.Callbacks("once memory"),g.Callbacks("once memory"),1,"rejected"]],m="pending",v={state:function(){return m},always:function(){return x.done(arguments).fail(arguments),this},catch:function(S){return v.then(null,S)},pipe:function(){var S=arguments;return g.Deferred(function(A){g.each(h,function(N,L){var R=E(S[L[4]])&&S[L[4]];x[L[1]](function(){var U=R&&R.apply(this,arguments);U&&E(U.promise)?U.promise().progress(A.notify).done(A.resolve).fail(A.reject):A[L[0]+"With"](this,R?[U]:arguments)})}),S=null}).promise()},then:function(S,A,N){var L=0;function R(U,K,V,X){return function(){var _e=this,we=arguments,Se=function(){var Ue,ht;if(!(U<L)){if(Ue=V.apply(_e,we),Ue===K.promise())throw new TypeError("Thenable self-resolution");ht=Ue&&(typeof Ue=="object"||typeof Ue=="function")&&Ue.then,E(ht)?X?ht.call(Ue,R(L,K,tt,X),R(L,K,vt,X)):(L++,ht.call(Ue,R(L,K,tt,X),R(L,K,vt,X),R(L,K,tt,K.notifyWith))):(V!==tt&&(_e=void 0,we=[Ue]),(X||K.resolveWith)(_e,we))}},ze=X?Se:function(){try{Se()}catch(Ue){g.Deferred.exceptionHook&&g.Deferred.exceptionHook(Ue,ze.error),U+1>=L&&(V!==vt&&(_e=void 0,we=[Ue]),K.rejectWith(_e,we))}};U?ze():(g.Deferred.getErrorHook?ze.error=g.Deferred.getErrorHook():g.Deferred.getStackHook&&(ze.error=g.Deferred.getStackHook()),e.setTimeout(ze))}}return g.Deferred(function(U){h[0][3].add(R(0,U,E(N)?N:tt,U.notifyWith)),h[1][3].add(R(0,U,E(S)?S:tt)),h[2][3].add(R(0,U,E(A)?A:vt))}).promise()},promise:function(S){return S!=null?g.extend(S,v):v}},x={};return g.each(h,function(S,A){var N=A[2],L=A[5];v[A[1]]=N.add,L&&N.add(function(){m=L},h[3-S][2].disable,h[3-S][3].disable,h[0][2].lock,h[0][3].lock),N.add(A[3].fire),x[A[0]]=function(){return x[A[0]+"With"](this===x?void 0:this,arguments),this},x[A[0]+"With"]=N.fireWith}),v.promise(x),u&&u.call(x,x),x},when:function(u){var h=arguments.length,m=h,v=Array(m),x=o.call(arguments),S=g.Deferred(),A=function(N){return function(L){v[N]=this,x[N]=arguments.length>1?o.call(arguments):L,--h||S.resolveWith(v,x)}};if(h<=1&&(jt(u,S.done(A(m)).resolve,S.reject,!h),S.state()==="pending"||E(x[m]&&x[m].then)))return S.then();for(;m--;)jt(x[m],A(m),S.reject);return S.promise()}});var Vt=/^(Eval|Internal|Range|Reference|Syntax|Type|URI)Error$/;g.Deferred.exceptionHook=function(u,h){e.console&&e.console.warn&&u&&Vt.test(u.name)&&e.console.warn("jQuery.Deferred exception: "+u.message,u.stack,h)},g.readyException=function(u){e.setTimeout(function(){throw u})};var St=g.Deferred();g.fn.ready=function(u){return St.then(u).catch(function(h){g.readyException(h)}),this},g.extend({isReady:!1,readyWait:1,ready:function(u){(u===!0?--g.readyWait:g.isReady)||(g.isReady=!0,!(u!==!0&&--g.readyWait>0)&&St.resolveWith(D,[g]))}}),g.ready.then=St.then;function dt(){D.removeEventListener("DOMContentLoaded",dt),e.removeEventListener("load",dt),g.ready()}D.readyState==="complete"||D.readyState!=="loading"&&!D.documentElement.doScroll?e.setTimeout(g.ready):(D.addEventListener("DOMContentLoaded",dt),e.addEventListener("load",dt));var Je=function(u,h,m,v,x,S,A){var N=0,L=u.length,R=m==null;if(P(m)==="object"){x=!0;for(N in m)Je(u,h,N,m[N],!0,S,A)}else if(v!==void 0&&(x=!0,E(v)||(A=!0),R&&(A?(h.call(u,v),h=null):(R=h,h=function(U,K,V){return R.call(g(U),V)})),h))for(;N<L;N++)h(u[N],m,A?v:v.call(u[N],N,h(u[N],m)));return x?u:R?h.call(u):L?h(u[0],m):S},Ct=/^-ms-/,lt=/-([a-z])/g;function At(u,h){return h.toUpperCase()}function qe(u){return u.replace(Ct,"ms-").replace(lt,At)}var nt=function(u){return u.nodeType===1||u.nodeType===9||!+u.nodeType};function it(){this.expando=g.expando+it.uid++}it.uid=1,it.prototype={cache:function(u){var h=u[this.expando];return h||(h={},nt(u)&&(u.nodeType?u[this.expando]=h:Object.defineProperty(u,this.expando,{value:h,configurable:!0}))),h},set:function(u,h,m){var v,x=this.cache(u);if(typeof h=="string")x[qe(h)]=m;else for(v in h)x[qe(v)]=h[v];return x},get:function(u,h){return h===void 0?this.cache(u):u[this.expando]&&u[this.expando][qe(h)]},access:function(u,h,m){return h===void 0||h&&typeof h=="string"&&m===void 0?this.get(u,h):(this.set(u,h,m),m!==void 0?m:h)},remove:function(u,h){var m,v=u[this.expando];if(v!==void 0){if(h!==void 0)for(Array.isArray(h)?h=h.map(qe):(h=qe(h),h=h in v?[h]:h.match(Qe)||[]),m=h.length;m--;)delete v[h[m]];(h===void 0||g.isEmptyObject(v))&&(u.nodeType?u[this.expando]=void 0:delete u[this.expando])}},hasData:function(u){var h=u[this.expando];return h!==void 0&&!g.isEmptyObject(h)}};var ue=new it,We=new it,kt=/^(?:\{[\w\W]*\}|\[[\w\W]*\])$/,Wt=/[A-Z]/g;function sn(u){return u==="true"?!0:u==="false"?!1:u==="null"?null:u===+u+""?+u:kt.test(u)?JSON.parse(u):u}function ln(u,h,m){var v;if(m===void 0&&u.nodeType===1)if(v="data-"+h.replace(Wt,"-$&").toLowerCase(),m=u.getAttribute(v),typeof m=="string"){try{m=sn(m)}catch{}We.set(u,h,m)}else m=void 0;return m}g.extend({hasData:function(u){return We.hasData(u)||ue.hasData(u)},data:function(u,h,m){return We.access(u,h,m)},removeData:function(u,h){We.remove(u,h)},_data:function(u,h,m){return ue.access(u,h,m)},_removeData:function(u,h){ue.remove(u,h)}}),g.fn.extend({data:function(u,h){var m,v,x,S=this[0],A=S&&S.attributes;if(u===void 0){if(this.length&&(x=We.get(S),S.nodeType===1&&!ue.get(S,"hasDataAttrs"))){for(m=A.length;m--;)A[m]&&(v=A[m].name,v.indexOf("data-")===0&&(v=qe(v.slice(5)),ln(S,v,x[v])));ue.set(S,"hasDataAttrs",!0)}return x}return typeof u=="object"?this.each(function(){We.set(this,u)}):Je(this,function(N){var L;if(S&&N===void 0)return L=We.get(S,u),L!==void 0||(L=ln(S,u),L!==void 0)?L:void 0;this.each(function(){We.set(this,u,N)})},null,h,arguments.length>1,null,!0)},removeData:function(u){return this.each(function(){We.remove(this,u)})}}),g.extend({queue:function(u,h,m){var v;if(u)return h=(h||"fx")+"queue",v=ue.get(u,h),m&&(!v||Array.isArray(m)?v=ue.access(u,h,g.makeArray(m)):v.push(m)),v||[]},dequeue:function(u,h){h=h||"fx";var m=g.queue(u,h),v=m.length,x=m.shift(),S=g._queueHooks(u,h),A=function(){g.dequeue(u,h)};x==="inprogress"&&(x=m.shift(),v--),x&&(h==="fx"&&m.unshift("inprogress"),delete S.stop,x.call(u,A,S)),!v&&S&&S.empty.fire()},_queueHooks:function(u,h){var m=h+"queueHooks";return ue.get(u,m)||ue.access(u,m,{empty:g.Callbacks("once memory").add(function(){ue.remove(u,[h+"queue",m])})})}}),g.fn.extend({queue:function(u,h){var m=2;return typeof u!="string"&&(h=u,u="fx",m--),arguments.length<m?g.queue(this[0],u):h===void 0?this:this.each(function(){var v=g.queue(this,u,h);g._queueHooks(this,u),u==="fx"&&v[0]!=="inprogress"&&g.dequeue(this,u)})},dequeue:function(u){return this.each(function(){g.dequeue(this,u)})},clearQueue:function(u){return this.queue(u||"fx",[])},promise:function(u,h){var m,v=1,x=g.Deferred(),S=this,A=this.length,N=function(){--v||x.resolveWith(S,[S])};for(typeof u!="string"&&(h=u,u=void 0),u=u||"fx";A--;)m=ue.get(S[A],u+"queueHooks"),m&&m.empty&&(v++,m.empty.add(N));return N(),x.promise(h)}});var cn=/[+-]?(?:\d*\.|)\d+(?:[eE][+-]?\d+|)/.source,Dt=new RegExp("^(?:([+-])=|)("+cn+")([a-z%]*)$","i"),ct=["Top","Right","Bottom","Left"],bt=D.documentElement,Le=function(u){return g.contains(u.ownerDocument,u)},Gt={composed:!0};bt.getRootNode&&(Le=function(u){return g.contains(u.ownerDocument,u)||u.getRootNode(Gt)===u.ownerDocument});var Tt=function(u,h){return u=h||u,u.style.display==="none"||u.style.display===""&&Le(u)&&g.css(u,"display")==="none"};function un(u,h,m,v){var x,S,A=20,N=v?function(){return v.cur()}:function(){return g.css(u,h,"")},L=N(),R=m&&m[3]||(g.cssNumber[h]?"":"px"),U=u.nodeType&&(g.cssNumber[h]||R!=="px"&&+L)&&Dt.exec(g.css(u,h));if(U&&U[3]!==R){for(L=L/2,R=R||U[3],U=+L||1;A--;)g.style(u,h,U+R),(1-S)*(1-(S=N()/L||.5))<=0&&(A=0),U=U/S;U=U*2,g.style(u,h,U+R),m=m||[]}return m&&(U=+U||+L||0,x=m[1]?U+(m[1]+1)*m[2]:+m[2],v&&(v.unit=R,v.start=U,v.end=x)),x}var Pt={};function Xt(u){var h,m=u.ownerDocument,v=u.nodeName,x=Pt[v];return x||(h=m.body.appendChild(m.createElement(v)),x=g.css(h,"display"),h.parentNode.removeChild(h),x==="none"&&(x="block"),Pt[v]=x,x)}function Ye(u,h){for(var m,v,x=[],S=0,A=u.length;S<A;S++)v=u[S],v.style&&(m=v.style.display,h?(m==="none"&&(x[S]=ue.get(v,"display")||null,x[S]||(v.style.display="")),v.style.display===""&&Tt(v)&&(x[S]=Xt(v))):m!=="none"&&(x[S]="none",ue.set(v,"display",m)));for(S=0;S<A;S++)x[S]!=null&&(u[S].style.display=x[S]);return u}g.fn.extend({show:function(){return Ye(this,!0)},hide:function(){return Ye(this)},toggle:function(u){return typeof u=="boolean"?u?this.show():this.hide():this.each(function(){Tt(this)?g(this).show():g(this).hide()})}});var It=/^(?:checkbox|radio)$/i,fn=/<([a-z][^\/\0>\x20\t\r\n\f]*)/i,T=/^$|^module$|\/(?:java|ecma)script/i;(function(){var u=D.createDocumentFragment(),h=u.appendChild(D.createElement("div")),m=D.createElement("input");m.setAttribute("type","radio"),m.setAttribute("checked","checked"),m.setAttribute("name","t"),h.appendChild(m),y.checkClone=h.cloneNode(!0).cloneNode(!0).lastChild.checked,h.innerHTML="<textarea>x</textarea>",y.noCloneChecked=!!h.cloneNode(!0).lastChild.defaultValue,h.innerHTML="<option></option>",y.option=!!h.lastChild})();var w={thead:[1,"<table>","</table>"],col:[2,"<table><colgroup>","</colgroup></table>"],tr:[2,"<table><tbody>","</tbody></table>"],td:[3,"<table><tbody><tr>","</tr></tbody></table>"],_default:[0,"",""]};w.tbody=w.tfoot=w.colgroup=w.caption=w.thead,w.th=w.td,y.option||(w.optgroup=w.option=[1,"<select multiple='multiple'>","</select>"]);function I(u,h){var m;return typeof u.getElementsByTagName<"u"?m=u.getElementsByTagName(h||"*"):typeof u.querySelectorAll<"u"?m=u.querySelectorAll(h||"*"):m=[],h===void 0||h&&G(u,h)?g.merge([u],m):m}function z(u,h){for(var m=0,v=u.length;m<v;m++)ue.set(u[m],"globalEval",!h||ue.get(h[m],"globalEval"))}var J=/<|&#?\w+;/;function ie(u,h,m,v,x){for(var S,A,N,L,R,U,K=h.createDocumentFragment(),V=[],X=0,_e=u.length;X<_e;X++)if(S=u[X],S||S===0)if(P(S)==="object")g.merge(V,S.nodeType?[S]:S);else if(!J.test(S))V.push(h.createTextNode(S));else{for(A=A||K.appendChild(h.createElement("div")),N=(fn.exec(S)||["",""])[1].toLowerCase(),L=w[N]||w._default,A.innerHTML=L[1]+g.htmlPrefilter(S)+L[2],U=L[0];U--;)A=A.lastChild;g.merge(V,A.childNodes),A=K.firstChild,A.textContent=""}for(K.textContent="",X=0;S=V[X++];){if(v&&g.inArray(S,v)>-1){x&&x.push(S);continue}if(R=Le(S),A=I(K.appendChild(S),"script"),R&&z(A),m)for(U=0;S=A[U++];)T.test(S.type||"")&&m.push(S)}return K}var ye=/^([^.]*)(?:\.(.+)|)/;function se(){return!0}function ve(){return!1}function ce(u,h,m,v,x,S){var A,N;if(typeof h=="object"){typeof m!="string"&&(v=v||m,m=void 0);for(N in h)ce(u,N,m,v,h[N],S);return u}if(v==null&&x==null?(x=m,v=m=void 0):x==null&&(typeof m=="string"?(x=v,v=void 0):(x=v,v=m,m=void 0)),x===!1)x=ve;else if(!x)return u;return S===1&&(A=x,x=function(L){return g().off(L),A.apply(this,arguments)},x.guid=A.guid||(A.guid=g.guid++)),u.each(function(){g.event.add(this,h,x,v,m)})}g.event={global:{},add:function(u,h,m,v,x){var S,A,N,L,R,U,K,V,X,_e,we,Se=ue.get(u);if(nt(u))for(m.handler&&(S=m,m=S.handler,x=S.selector),x&&g.find.matchesSelector(bt,x),m.guid||(m.guid=g.guid++),(L=Se.events)||(L=Se.events=Object.create(null)),(A=Se.handle)||(A=Se.handle=function(ze){return typeof g<"u"&&g.event.triggered!==ze.type?g.event.dispatch.apply(u,arguments):void 0}),h=(h||"").match(Qe)||[""],R=h.length;R--;)N=ye.exec(h[R])||[],X=we=N[1],_e=(N[2]||"").split(".").sort(),X&&(K=g.event.special[X]||{},X=(x?K.delegateType:K.bindType)||X,K=g.event.special[X]||{},U=g.extend({type:X,origType:we,data:v,handler:m,guid:m.guid,selector:x,needsContext:x&&g.expr.match.needsContext.test(x),namespace:_e.join(".")},S),(V=L[X])||(V=L[X]=[],V.delegateCount=0,(!K.setup||K.setup.call(u,v,_e,A)===!1)&&u.addEventListener&&u.addEventListener(X,A)),K.add&&(K.add.call(u,U),U.handler.guid||(U.handler.guid=m.guid)),x?V.splice(V.delegateCount++,0,U):V.push(U),g.event.global[X]=!0)},remove:function(u,h,m,v,x){var S,A,N,L,R,U,K,V,X,_e,we,Se=ue.hasData(u)&&ue.get(u);if(!(!Se||!(L=Se.events))){for(h=(h||"").match(Qe)||[""],R=h.length;R--;){if(N=ye.exec(h[R])||[],X=we=N[1],_e=(N[2]||"").split(".").sort(),!X){for(X in L)g.event.remove(u,X+h[R],m,v,!0);continue}for(K=g.event.special[X]||{},X=(v?K.delegateType:K.bindType)||X,V=L[X]||[],N=N[2]&&new RegExp("(^|\\.)"+_e.join("\\.(?:.*\\.|)")+"(\\.|$)"),A=S=V.length;S--;)U=V[S],(x||we===U.origType)&&(!m||m.guid===U.guid)&&(!N||N.test(U.namespace))&&(!v||v===U.selector||v==="**"&&U.selector)&&(V.splice(S,1),U.selector&&V.delegateCount--,K.remove&&K.remove.call(u,U));A&&!V.length&&((!K.teardown||K.teardown.call(u,_e,Se.handle)===!1)&&g.removeEvent(u,X,Se.handle),delete L[X])}g.isEmptyObject(L)&&ue.remove(u,"handle events")}},dispatch:function(u){var h,m,v,x,S,A,N=new Array(arguments.length),L=g.event.fix(u),R=(ue.get(this,"events")||Object.create(null))[L.type]||[],U=g.event.special[L.type]||{};for(N[0]=L,h=1;h<arguments.length;h++)N[h]=arguments[h];if(L.delegateTarget=this,!(U.preDispatch&&U.preDispatch.call(this,L)===!1)){for(A=g.event.handlers.call(this,L,R),h=0;(x=A[h++])&&!L.isPropagationStopped();)for(L.currentTarget=x.elem,m=0;(S=x.handlers[m++])&&!L.isImmediatePropagationStopped();)(!L.rnamespace||S.namespace===!1||L.rnamespace.test(S.namespace))&&(L.handleObj=S,L.data=S.data,v=((g.event.special[S.origType]||{}).handle||S.handler).apply(x.elem,N),v!==void 0&&(L.result=v)===!1&&(L.preventDefault(),L.stopPropagation()));return U.postDispatch&&U.postDispatch.call(this,L),L.result}},handlers:function(u,h){var m,v,x,S,A,N=[],L=h.delegateCount,R=u.target;if(L&&R.nodeType&&!(u.type==="click"&&u.button>=1)){for(;R!==this;R=R.parentNode||this)if(R.nodeType===1&&!(u.type==="click"&&R.disabled===!0)){for(S=[],A={},m=0;m<L;m++)v=h[m],x=v.selector+" ",A[x]===void 0&&(A[x]=v.needsContext?g(x,this).index(R)>-1:g.find(x,this,null,[R]).length),A[x]&&S.push(v);S.length&&N.push({elem:R,handlers:S})}}return R=this,L<h.length&&N.push({elem:R,handlers:h.slice(L)}),N},addProp:function(u,h){Object.defineProperty(g.Event.prototype,u,{enumerable:!0,configurable:!0,get:E(h)?function(){if(this.originalEvent)return h(this.originalEvent)}:function(){if(this.originalEvent)return this.originalEvent[u]},set:function(m){Object.defineProperty(this,u,{enumerable:!0,configurable:!0,writable:!0,value:m})}})},fix:function(u){return u[g.expando]?u:new g.Event(u)},special:{load:{noBubble:!0},click:{setup:function(u){var h=this||u;return It.test(h.type)&&h.click&&G(h,"input")&&he(h,"click",!0),!1},trigger:function(u){var h=this||u;return It.test(h.type)&&h.click&&G(h,"input")&&he(h,"click"),!0},_default:function(u){var h=u.target;return It.test(h.type)&&h.click&&G(h,"input")&&ue.get(h,"click")||G(h,"a")}},beforeunload:{postDispatch:function(u){u.result!==void 0&&u.originalEvent&&(u.originalEvent.returnValue=u.result)}}}};function he(u,h,m){if(!m){ue.get(u,h)===void 0&&g.event.add(u,h,se);return}ue.set(u,h,!1),g.event.add(u,h,{namespace:!1,handler:function(v){var x,S=ue.get(this,h);if(v.isTrigger&1&&this[h]){if(S)(g.event.special[h]||{}).delegateType&&v.stopPropagation();else if(S=o.call(arguments),ue.set(this,h,S),this[h](),x=ue.get(this,h),ue.set(this,h,!1),S!==x)return v.stopImmediatePropagation(),v.preventDefault(),x}else S&&(ue.set(this,h,g.event.trigger(S[0],S.slice(1),this)),v.stopPropagation(),v.isImmediatePropagationStopped=se)}})}g.removeEvent=function(u,h,m){u.removeEventListener&&u.removeEventListener(h,m)},g.Event=function(u,h){if(!(this instanceof g.Event))return new g.Event(u,h);u&&u.type?(this.originalEvent=u,this.type=u.type,this.isDefaultPrevented=u.defaultPrevented||u.defaultPrevented===void 0&&u.returnValue===!1?se:ve,this.target=u.target&&u.target.nodeType===3?u.target.parentNode:u.target,this.currentTarget=u.currentTarget,this.relatedTarget=u.relatedTarget):this.type=u,h&&g.extend(this,h),this.timeStamp=u&&u.timeStamp||Date.now(),this[g.expando]=!0},g.Event.prototype={constructor:g.Event,isDefaultPrevented:ve,isPropagationStopped:ve,isImmediatePropagationStopped:ve,isSimulated:!1,preventDefault:function(){var u=this.originalEvent;this.isDefaultPrevented=se,u&&!this.isSimulated&&u.preventDefault()},stopPropagation:function(){var u=this.originalEvent;this.isPropagationStopped=se,u&&!this.isSimulated&&u.stopPropagation()},stopImmediatePropagation:function(){var u=this.originalEvent;this.isImmediatePropagationStopped=se,u&&!this.isSimulated&&u.stopImmediatePropagation(),this.stopPropagation()}},g.each({altKey:!0,bubbles:!0,cancelable:!0,changedTouches:!0,ctrlKey:!0,detail:!0,eventPhase:!0,metaKey:!0,pageX:!0,pageY:!0,shiftKey:!0,view:!0,char:!0,code:!0,charCode:!0,key:!0,keyCode:!0,button:!0,buttons:!0,clientX:!0,clientY:!0,offsetX:!0,offsetY:!0,pointerId:!0,pointerType:!0,screenX:!0,screenY:!0,targetTouches:!0,toElement:!0,touches:!0,which:!0},g.event.addProp),g.each({focus:"focusin",blur:"focusout"},function(u,h){function m(v){if(D.documentMode){var x=ue.get(this,"handle"),S=g.event.fix(v);S.type=v.type==="focusin"?"focus":"blur",S.isSimulated=!0,x(v),S.target===S.currentTarget&&x(S)}else g.event.simulate(h,v.target,g.event.fix(v))}g.event.special[u]={setup:function(){var v;if(he(this,u,!0),D.documentMode)v=ue.get(this,h),v||this.addEventListener(h,m),ue.set(this,h,(v||0)+1);else return!1},trigger:function(){return he(this,u),!0},teardown:function(){var v;if(D.documentMode)v=ue.get(this,h)-1,v?ue.set(this,h,v):(this.removeEventListener(h,m),ue.remove(this,h));else return!1},_default:function(v){return ue.get(v.target,u)},delegateType:h},g.event.special[h]={setup:function(){var v=this.ownerDocument||this.document||this,x=D.documentMode?this:v,S=ue.get(x,h);S||(D.documentMode?this.addEventListener(h,m):v.addEventListener(u,m,!0)),ue.set(x,h,(S||0)+1)},teardown:function(){var v=this.ownerDocument||this.document||this,x=D.documentMode?this:v,S=ue.get(x,h)-1;S?ue.set(x,h,S):(D.documentMode?this.removeEventListener(h,m):v.removeEventListener(u,m,!0),ue.remove(x,h))}}}),g.each({mouseenter:"mouseover",mouseleave:"mouseout",pointerenter:"pointerover",pointerleave:"pointerout"},function(u,h){g.event.special[u]={delegateType:h,bindType:h,handle:function(m){var v,x=this,S=m.relatedTarget,A=m.handleObj;return(!S||S!==x&&!g.contains(x,S))&&(m.type=A.origType,v=A.handler.apply(this,arguments),m.type=h),v}}}),g.fn.extend({on:function(u,h,m,v){return ce(this,u,h,m,v)},one:function(u,h,m,v){return ce(this,u,h,m,v,1)},off:function(u,h,m){var v,x;if(u&&u.preventDefault&&u.handleObj)return v=u.handleObj,g(u.delegateTarget).off(v.namespace?v.origType+"."+v.namespace:v.origType,v.selector,v.handler),this;if(typeof u=="object"){for(x in u)this.off(x,h,u[x]);return this}return(h===!1||typeof h=="function")&&(m=h,h=void 0),m===!1&&(m=ve),this.each(function(){g.event.remove(this,u,m,h)})}});var Ne=/<script|<style|<link/i,rt=/checked\s*(?:[^=]|=\s*.checked.)/i,Ge=/^\s*<!\[CDATA\[|\]\]>\s*$/g;function wt(u,h){return G(u,"table")&&G(h.nodeType!==11?h:h.firstChild,"tr")&&g(u).children("tbody")[0]||u}function Ot(u){return u.type=(u.getAttribute("type")!==null)+"/"+u.type,u}function yn(u){return(u.type||"").slice(0,5)==="true/"?u.type=u.type.slice(5):u.removeAttribute("type"),u}function Ut(u,h){var m,v,x,S,A,N,L;if(h.nodeType===1){if(ue.hasData(u)&&(S=ue.get(u),L=S.events,L)){ue.remove(h,"handle events");for(x in L)for(m=0,v=L[x].length;m<v;m++)g.event.add(h,x,L[x][m])}We.hasData(u)&&(A=We.access(u),N=g.extend({},A),We.set(h,N))}}function En(u,h){var m=h.nodeName.toLowerCase();m==="input"&&It.test(u.type)?h.checked=u.checked:(m==="input"||m==="textarea")&&(h.defaultValue=u.defaultValue)}function $t(u,h,m,v){h=s(h);var x,S,A,N,L,R,U=0,K=u.length,V=K-1,X=h[0],_e=E(X);if(_e||K>1&&typeof X=="string"&&!y.checkClone&&rt.test(X))return u.each(function(we){var Se=u.eq(we);_e&&(h[0]=X.call(this,we,Se.html())),$t(Se,h,m,v)});if(K&&(x=ie(h,u[0].ownerDocument,!1,u,v),S=x.firstChild,x.childNodes.length===1&&(x=S),S||v)){for(A=g.map(I(x,"script"),Ot),N=A.length;U<K;U++)L=x,U!==V&&(L=g.clone(L,!0,!0),N&&g.merge(A,I(L,"script"))),m.call(u[U],L,U);if(N)for(R=A[A.length-1].ownerDocument,g.map(A,yn),U=0;U<N;U++)L=A[U],T.test(L.type||"")&&!ue.access(L,"globalEval")&&g.contains(R,L)&&(L.src&&(L.type||"").toLowerCase()!=="module"?g._evalUrl&&!L.noModule&&g._evalUrl(L.src,{nonce:L.nonce||L.getAttribute("nonce")},R):F(L.textContent.replace(Ge,""),L,R))}return u}function dn(u,h,m){for(var v,x=h?g.filter(h,u):u,S=0;(v=x[S])!=null;S++)!m&&v.nodeType===1&&g.cleanData(I(v)),v.parentNode&&(m&&Le(v)&&z(I(v,"script")),v.parentNode.removeChild(v));return u}g.extend({htmlPrefilter:function(u){return u},clone:function(u,h,m){var v,x,S,A,N=u.cloneNode(!0),L=Le(u);if(!y.noCloneChecked&&(u.nodeType===1||u.nodeType===11)&&!g.isXMLDoc(u))for(A=I(N),S=I(u),v=0,x=S.length;v<x;v++)En(S[v],A[v]);if(h)if(m)for(S=S||I(u),A=A||I(N),v=0,x=S.length;v<x;v++)Ut(S[v],A[v]);else Ut(u,N);return A=I(N,"script"),A.length>0&&z(A,!L&&I(u,"script")),N},cleanData:function(u){for(var h,m,v,x=g.event.special,S=0;(m=u[S])!==void 0;S++)if(nt(m)){if(h=m[ue.expando]){if(h.events)for(v in h.events)x[v]?g.event.remove(m,v):g.removeEvent(m,v,h.handle);m[ue.expando]=void 0}m[We.expando]&&(m[We.expando]=void 0)}}}),g.fn.extend({detach:function(u){return dn(this,u,!0)},remove:function(u){return dn(this,u)},text:function(u){return Je(this,function(h){return h===void 0?g.text(this):this.empty().each(function(){(this.nodeType===1||this.nodeType===11||this.nodeType===9)&&(this.textContent=h)})},null,u,arguments.length)},append:function(){return $t(this,arguments,function(u){if(this.nodeType===1||this.nodeType===11||this.nodeType===9){var h=wt(this,u);h.appendChild(u)}})},prepend:function(){return $t(this,arguments,function(u){if(this.nodeType===1||this.nodeType===11||this.nodeType===9){var h=wt(this,u);h.insertBefore(u,h.firstChild)}})},before:function(){return $t(this,arguments,function(u){this.parentNode&&this.parentNode.insertBefore(u,this)})},after:function(){return $t(this,arguments,function(u){this.parentNode&&this.parentNode.insertBefore(u,this.nextSibling)})},empty:function(){for(var u,h=0;(u=this[h])!=null;h++)u.nodeType===1&&(g.cleanData(I(u,!1)),u.textContent="");return this},clone:function(u,h){return u=u??!1,h=h??u,this.map(function(){return g.clone(this,u,h)})},html:function(u){return Je(this,function(h){var m=this[0]||{},v=0,x=this.length;if(h===void 0&&m.nodeType===1)return m.innerHTML;if(typeof h=="string"&&!Ne.test(h)&&!w[(fn.exec(h)||["",""])[1].toLowerCase()]){h=g.htmlPrefilter(h);try{for(;v<x;v++)m=this[v]||{},m.nodeType===1&&(g.cleanData(I(m,!1)),m.innerHTML=h);m=0}catch{}}m&&this.empty().append(h)},null,u,arguments.length)},replaceWith:function(){var u=[];return $t(this,arguments,function(h){var m=this.parentNode;g.inArray(this,u)<0&&(g.cleanData(I(this)),m&&m.replaceChild(h,this))},u)}}),g.each({appendTo:"append",prependTo:"prepend",insertBefore:"before",insertAfter:"after",replaceAll:"replaceWith"},function(u,h){g.fn[u]=function(m){for(var v,x=[],S=g(m),A=S.length-1,N=0;N<=A;N++)v=N===A?this:this.clone(!0),g(S[N])[h](v),l.apply(x,v.get());return this.pushStack(x)}});var Qt=new RegExp("^("+cn+")(?!px)[a-z%]+$","i"),Jt=/^--/,zt=function(u){var h=u.ownerDocument.defaultView;return(!h||!h.opener)&&(h=e),h.getComputedStyle(u)},hn=function(u,h,m){var v,x,S={};for(x in h)S[x]=u.style[x],u.style[x]=h[x];v=m.call(u);for(x in h)u.style[x]=S[x];return v},xn=new RegExp(ct.join("|"),"i");(function(){function u(){if(R){L.style.cssText="position:absolute;left:-11111px;width:60px;margin-top:1px;padding:0;border:0",R.style.cssText="position:relative;display:block;box-sizing:border-box;overflow:scroll;margin:auto;border:1px;padding:1px;width:60%;top:1%",bt.appendChild(L).appendChild(R);var U=e.getComputedStyle(R);m=U.top!=="1%",N=h(U.marginLeft)===12,R.style.right="60%",S=h(U.right)===36,v=h(U.width)===36,R.style.position="absolute",x=h(R.offsetWidth/3)===12,bt.removeChild(L),R=null}}function h(U){return Math.round(parseFloat(U))}var m,v,x,S,A,N,L=D.createElement("div"),R=D.createElement("div");R.style&&(R.style.backgroundClip="content-box",R.cloneNode(!0).style.backgroundClip="",y.clearCloneStyle=R.style.backgroundClip==="content-box",g.extend(y,{boxSizingReliable:function(){return u(),v},pixelBoxStyles:function(){return u(),S},pixelPosition:function(){return u(),m},reliableMarginLeft:function(){return u(),N},scrollboxSize:function(){return u(),x},reliableTrDimensions:function(){var U,K,V,X;return A==null&&(U=D.createElement("table"),K=D.createElement("tr"),V=D.createElement("div"),U.style.cssText="position:absolute;left:-11111px;border-collapse:separate",K.style.cssText="box-sizing:content-box;border:1px solid",K.style.height="1px",V.style.height="9px",V.style.display="block",bt.appendChild(U).appendChild(K).appendChild(V),X=e.getComputedStyle(K),A=parseInt(X.height,10)+parseInt(X.borderTopWidth,10)+parseInt(X.borderBottomWidth,10)===K.offsetHeight,bt.removeChild(U)),A}}))})();function Zt(u,h,m){var v,x,S,A,N=Jt.test(h),L=u.style;return m=m||zt(u),m&&(A=m.getPropertyValue(h)||m[h],N&&A&&(A=A.replace(Ee,"$1")||void 0),A===""&&!Le(u)&&(A=g.style(u,h)),!y.pixelBoxStyles()&&Qt.test(A)&&xn.test(h)&&(v=L.width,x=L.minWidth,S=L.maxWidth,L.minWidth=L.maxWidth=L.width=A,A=m.width,L.width=v,L.minWidth=x,L.maxWidth=S)),A!==void 0?A+"":A}function Bn(u,h){return{get:function(){if(u()){delete this.get;return}return(this.get=h).apply(this,arguments)}}}var jn=["Webkit","Moz","ms"],Vn=D.createElement("div").style,Wn={};function ci(u){for(var h=u[0].toUpperCase()+u.slice(1),m=jn.length;m--;)if(u=jn[m]+h,u in Vn)return u}function Sn(u){var h=g.cssProps[u]||Wn[u];return h||(u in Vn?u:Wn[u]=ci(u)||u)}var ui=/^(none|table(?!-c[ea]).+)/,fi={position:"absolute",visibility:"hidden",display:"block"},Un={letterSpacing:"0",fontWeight:"400"};function zn(u,h,m){var v=Dt.exec(h);return v?Math.max(0,v[2]-(m||0))+(v[3]||"px"):h}function Cn(u,h,m,v,x,S){var A=h==="width"?1:0,N=0,L=0,R=0;if(m===(v?"border":"content"))return 0;for(;A<4;A+=2)m==="margin"&&(R+=g.css(u,m+ct[A],!0,x)),v?(m==="content"&&(L-=g.css(u,"padding"+ct[A],!0,x)),m!=="margin"&&(L-=g.css(u,"border"+ct[A]+"Width",!0,x))):(L+=g.css(u,"padding"+ct[A],!0,x),m!=="padding"?L+=g.css(u,"border"+ct[A]+"Width",!0,x):N+=g.css(u,"border"+ct[A]+"Width",!0,x));return!v&&S>=0&&(L+=Math.max(0,Math.ceil(u["offset"+h[0].toUpperCase()+h.slice(1)]-S-L-N-.5))||0),L+R}function qn(u,h,m){var v=zt(u),x=!y.boxSizingReliable()||m,S=x&&g.css(u,"boxSizing",!1,v)==="border-box",A=S,N=Zt(u,h,v),L="offset"+h[0].toUpperCase()+h.slice(1);if(Qt.test(N)){if(!m)return N;N="auto"}return(!y.boxSizingReliable()&&S||!y.reliableTrDimensions()&&G(u,"tr")||N==="auto"||!parseFloat(N)&&g.css(u,"display",!1,v)==="inline")&&u.getClientRects().length&&(S=g.css(u,"boxSizing",!1,v)==="border-box",A=L in u,A&&(N=u[L])),N=parseFloat(N)||0,N+Cn(u,h,m||(S?"border":"content"),A,v,N)+"px"}g.extend({cssHooks:{opacity:{get:function(u,h){if(h){var m=Zt(u,"opacity");return m===""?"1":m}}}},cssNumber:{animationIterationCount:!0,aspectRatio:!0,borderImageSlice:!0,columnCount:!0,flexGrow:!0,flexShrink:!0,fontWeight:!0,gridArea:!0,gridColumn:!0,gridColumnEnd:!0,gridColumnStart:!0,gridRow:!0,gridRowEnd:!0,gridRowStart:!0,lineHeight:!0,opacity:!0,order:!0,orphans:!0,scale:!0,widows:!0,zIndex:!0,zoom:!0,fillOpacity:!0,floodOpacity:!0,stopOpacity:!0,strokeMiterlimit:!0,strokeOpacity:!0},cssProps:{},style:function(u,h,m,v){if(!(!u||u.nodeType===3||u.nodeType===8||!u.style)){var x,S,A,N=qe(h),L=Jt.test(h),R=u.style;if(L||(h=Sn(N)),A=g.cssHooks[h]||g.cssHooks[N],m!==void 0){if(S=typeof m,S==="string"&&(x=Dt.exec(m))&&x[1]&&(m=un(u,h,x),S="number"),m==null||m!==m)return;S==="number"&&!L&&(m+=x&&x[3]||(g.cssNumber[N]?"":"px")),!y.clearCloneStyle&&m===""&&h.indexOf("background")===0&&(R[h]="inherit"),(!A||!("set"in A)||(m=A.set(u,m,v))!==void 0)&&(L?R.setProperty(h,m):R[h]=m)}else return A&&"get"in A&&(x=A.get(u,!1,v))!==void 0?x:R[h]}},css:function(u,h,m,v){var x,S,A,N=qe(h),L=Jt.test(h);return L||(h=Sn(N)),A=g.cssHooks[h]||g.cssHooks[N],A&&"get"in A&&(x=A.get(u,!0,m)),x===void 0&&(x=Zt(u,h,v)),x==="normal"&&h in Un&&(x=Un[h]),m===""||m?(S=parseFloat(x),m===!0||isFinite(S)?S||0:x):x}}),g.each(["height","width"],function(u,h){g.cssHooks[h]={get:function(m,v,x){if(v)return ui.test(g.css(m,"display"))&&(!m.getClientRects().length||!m.getBoundingClientRect().width)?hn(m,fi,function(){return qn(m,h,x)}):qn(m,h,x)},set:function(m,v,x){var S,A=zt(m),N=!y.scrollboxSize()&&A.position==="absolute",L=N||x,R=L&&g.css(m,"boxSizing",!1,A)==="border-box",U=x?Cn(m,h,x,R,A):0;return R&&N&&(U-=Math.ceil(m["offset"+h[0].toUpperCase()+h.slice(1)]-parseFloat(A[h])-Cn(m,h,"border",!1,A)-.5)),U&&(S=Dt.exec(v))&&(S[3]||"px")!=="px"&&(m.style[h]=v,v=g.css(m,h)),zn(m,v,U)}}}),g.cssHooks.marginLeft=Bn(y.reliableMarginLeft,function(u,h){if(h)return(parseFloat(Zt(u,"marginLeft"))||u.getBoundingClientRect().left-hn(u,{marginLeft:0},function(){return u.getBoundingClientRect().left}))+"px"}),g.each({margin:"",padding:"",border:"Width"},function(u,h){g.cssHooks[u+h]={expand:function(m){for(var v=0,x={},S=typeof m=="string"?m.split(" "):[m];v<4;v++)x[u+ct[v]+h]=S[v]||S[v-2]||S[0];return x}},u!=="margin"&&(g.cssHooks[u+h].set=zn)}),g.fn.extend({css:function(u,h){return Je(this,function(m,v,x){var S,A,N={},L=0;if(Array.isArray(v)){for(S=zt(m),A=v.length;L<A;L++)N[v[L]]=g.css(m,v[L],!1,S);return N}return x!==void 0?g.style(m,v,x):g.css(m,v)},u,h,arguments.length>1)}});function Ze(u,h,m,v,x){return new Ze.prototype.init(u,h,m,v,x)}g.Tween=Ze,Ze.prototype={constructor:Ze,init:function(u,h,m,v,x,S){this.elem=u,this.prop=m,this.easing=x||g.easing._default,this.options=h,this.start=this.now=this.cur(),this.end=v,this.unit=S||(g.cssNumber[m]?"":"px")},cur:function(){var u=Ze.propHooks[this.prop];return u&&u.get?u.get(this):Ze.propHooks._default.get(this)},run:function(u){var h,m=Ze.propHooks[this.prop];return this.options.duration?this.pos=h=g.easing[this.easing](u,this.options.duration*u,0,1,this.options.duration):this.pos=h=u,this.now=(this.end-this.start)*h+this.start,this.options.step&&this.options.step.call(this.elem,this.now,this),m&&m.set?m.set(this):Ze.propHooks._default.set(this),this}},Ze.prototype.init.prototype=Ze.prototype,Ze.propHooks={_default:{get:function(u){var h;return u.elem.nodeType!==1||u.elem[u.prop]!=null&&u.elem.style[u.prop]==null?u.elem[u.prop]:(h=g.css(u.elem,u.prop,""),!h||h==="auto"?0:h)},set:function(u){g.fx.step[u.prop]?g.fx.step[u.prop](u):u.elem.nodeType===1&&(g.cssHooks[u.prop]||u.elem.style[Sn(u.prop)]!=null)?g.style(u.elem,u.prop,u.now+u.unit):u.elem[u.prop]=u.now}}},Ze.propHooks.scrollTop=Ze.propHooks.scrollLeft={set:function(u){u.elem.nodeType&&u.elem.parentNode&&(u.elem[u.prop]=u.now)}},g.easing={linear:function(u){return u},swing:function(u){return .5-Math.cos(u*Math.PI)/2},_default:"swing"},g.fx=Ze.prototype.init,g.fx.step={};var qt,pn,di=/^(?:toggle|show|hide)$/,hi=/queueHooks$/;function An(){pn&&(D.hidden===!1&&e.requestAnimationFrame?e.requestAnimationFrame(An):e.setTimeout(An,g.fx.interval),g.fx.tick())}function Yn(){return e.setTimeout(function(){qt=void 0}),qt=Date.now()}function gn(u,h){var m,v=0,x={height:u};for(h=h?1:0;v<4;v+=2-h)m=ct[v],x["margin"+m]=x["padding"+m]=u;return h&&(x.opacity=x.width=u),x}function Kn(u,h,m){for(var v,x=(ut.tweeners[h]||[]).concat(ut.tweeners["*"]),S=0,A=x.length;S<A;S++)if(v=x[S].call(m,h,u))return v}function pi(u,h,m){var v,x,S,A,N,L,R,U,K="width"in h||"height"in h,V=this,X={},_e=u.style,we=u.nodeType&&Tt(u),Se=ue.get(u,"fxshow");m.queue||(A=g._queueHooks(u,"fx"),A.unqueued==null&&(A.unqueued=0,N=A.empty.fire,A.empty.fire=function(){A.unqueued||N()}),A.unqueued++,V.always(function(){V.always(function(){A.unqueued--,g.queue(u,"fx").length||A.empty.fire()})}));for(v in h)if(x=h[v],di.test(x)){if(delete h[v],S=S||x==="toggle",x===(we?"hide":"show"))if(x==="show"&&Se&&Se[v]!==void 0)we=!0;else continue;X[v]=Se&&Se[v]||g.style(u,v)}if(L=!g.isEmptyObject(h),!(!L&&g.isEmptyObject(X))){K&&u.nodeType===1&&(m.overflow=[_e.overflow,_e.overflowX,_e.overflowY],R=Se&&Se.display,R==null&&(R=ue.get(u,"display")),U=g.css(u,"display"),U==="none"&&(R?U=R:(Ye([u],!0),R=u.style.display||R,U=g.css(u,"display"),Ye([u]))),(U==="inline"||U==="inline-block"&&R!=null)&&g.css(u,"float")==="none"&&(L||(V.done(function(){_e.display=R}),R==null&&(U=_e.display,R=U==="none"?"":U)),_e.display="inline-block")),m.overflow&&(_e.overflow="hidden",V.always(function(){_e.overflow=m.overflow[0],_e.overflowX=m.overflow[1],_e.overflowY=m.overflow[2]})),L=!1;for(v in X)L||(Se?"hidden"in Se&&(we=Se.hidden):Se=ue.access(u,"fxshow",{display:R}),S&&(Se.hidden=!we),we&&Ye([u],!0),V.done(function(){we||Ye([u]),ue.remove(u,"fxshow");for(v in X)g.style(u,v,X[v])})),L=Kn(we?Se[v]:0,v,V),v in Se||(Se[v]=L.start,we&&(L.end=L.start,L.start=0))}}function gi(u,h){var m,v,x,S,A;for(m in u)if(v=qe(m),x=h[v],S=u[m],Array.isArray(S)&&(x=S[1],S=u[m]=S[0]),m!==v&&(u[v]=S,delete u[m]),A=g.cssHooks[v],A&&"expand"in A){S=A.expand(S),delete u[v];for(m in S)m in u||(u[m]=S[m],h[m]=x)}else h[v]=x}function ut(u,h,m){var v,x,S=0,A=ut.prefilters.length,N=g.Deferred().always(function(){delete L.elem}),L=function(){if(x)return!1;for(var K=qt||Yn(),V=Math.max(0,R.startTime+R.duration-K),X=V/R.duration||0,_e=1-X,we=0,Se=R.tweens.length;we<Se;we++)R.tweens[we].run(_e);return N.notifyWith(u,[R,_e,V]),_e<1&&Se?V:(Se||N.notifyWith(u,[R,1,0]),N.resolveWith(u,[R]),!1)},R=N.promise({elem:u,props:g.extend({},h),opts:g.extend(!0,{specialEasing:{},easing:g.easing._default},m),originalProperties:h,originalOptions:m,startTime:qt||Yn(),duration:m.duration,tweens:[],createTween:function(K,V){var X=g.Tween(u,R.opts,K,V,R.opts.specialEasing[K]||R.opts.easing);return R.tweens.push(X),X},stop:function(K){var V=0,X=K?R.tweens.length:0;if(x)return this;for(x=!0;V<X;V++)R.tweens[V].run(1);return K?(N.notifyWith(u,[R,1,0]),N.resolveWith(u,[R,K])):N.rejectWith(u,[R,K]),this}}),U=R.props;for(gi(U,R.opts.specialEasing);S<A;S++)if(v=ut.prefilters[S].call(R,u,U,R.opts),v)return E(v.stop)&&(g._queueHooks(R.elem,R.opts.queue).stop=v.stop.bind(v)),v;return g.map(U,Kn,R),E(R.opts.start)&&R.opts.start.call(u,R),R.progress(R.opts.progress).done(R.opts.done,R.opts.complete).fail(R.opts.fail).always(R.opts.always),g.fx.timer(g.extend(L,{elem:u,anim:R,queue:R.opts.queue})),R}g.Animation=g.extend(ut,{tweeners:{"*":[function(u,h){var m=this.createTween(u,h);return un(m.elem,u,Dt.exec(h),m),m}]},tweener:function(u,h){E(u)?(h=u,u=["*"]):u=u.match(Qe);for(var m,v=0,x=u.length;v<x;v++)m=u[v],ut.tweeners[m]=ut.tweeners[m]||[],ut.tweeners[m].unshift(h)},prefilters:[pi],prefilter:function(u,h){h?ut.prefilters.unshift(u):ut.prefilters.push(u)}}),g.speed=function(u,h,m){var v=u&&typeof u=="object"?g.extend({},u):{complete:m||!m&&h||E(u)&&u,duration:u,easing:m&&h||h&&!E(h)&&h};return g.fx.off?v.duration=0:typeof v.duration!="number"&&(v.duration in g.fx.speeds?v.duration=g.fx.speeds[v.duration]:v.duration=g.fx.speeds._default),(v.queue==null||v.queue===!0)&&(v.queue="fx"),v.old=v.complete,v.complete=function(){E(v.old)&&v.old.call(this),v.queue&&g.dequeue(this,v.queue)},v},g.fn.extend({fadeTo:function(u,h,m,v){return this.filter(Tt).css("opacity",0).show().end().animate({opacity:h},u,m,v)},animate:function(u,h,m,v){var x=g.isEmptyObject(u),S=g.speed(h,m,v),A=function(){var N=ut(this,g.extend({},u),S);(x||ue.get(this,"finish"))&&N.stop(!0)};return A.finish=A,x||S.queue===!1?this.each(A):this.queue(S.queue,A)},stop:function(u,h,m){var v=function(x){var S=x.stop;delete x.stop,S(m)};return typeof u!="string"&&(m=h,h=u,u=void 0),h&&this.queue(u||"fx",[]),this.each(function(){var x=!0,S=u!=null&&u+"queueHooks",A=g.timers,N=ue.get(this);if(S)N[S]&&N[S].stop&&v(N[S]);else for(S in N)N[S]&&N[S].stop&&hi.test(S)&&v(N[S]);for(S=A.length;S--;)A[S].elem===this&&(u==null||A[S].queue===u)&&(A[S].anim.stop(m),x=!1,A.splice(S,1));(x||!m)&&g.dequeue(this,u)})},finish:function(u){return u!==!1&&(u=u||"fx"),this.each(function(){var h,m=ue.get(this),v=m[u+"queue"],x=m[u+"queueHooks"],S=g.timers,A=v?v.length:0;for(m.finish=!0,g.queue(this,u,[]),x&&x.stop&&x.stop.call(this,!0),h=S.length;h--;)S[h].elem===this&&S[h].queue===u&&(S[h].anim.stop(!0),S.splice(h,1));for(h=0;h<A;h++)v[h]&&v[h].finish&&v[h].finish.call(this);delete m.finish})}}),g.each(["toggle","show","hide"],function(u,h){var m=g.fn[h];g.fn[h]=function(v,x,S){return v==null||typeof v=="boolean"?m.apply(this,arguments):this.animate(gn(h,!0),v,x,S)}}),g.each({slideDown:gn("show"),slideUp:gn("hide"),slideToggle:gn("toggle"),fadeIn:{opacity:"show"},fadeOut:{opacity:"hide"},fadeToggle:{opacity:"toggle"}},function(u,h){g.fn[u]=function(m,v,x){return this.animate(h,m,v,x)}}),g.timers=[],g.fx.tick=function(){var u,h=0,m=g.timers;for(qt=Date.now();h<m.length;h++)u=m[h],!u()&&m[h]===u&&m.splice(h--,1);m.length||g.fx.stop(),qt=void 0},g.fx.timer=function(u){g.timers.push(u),g.fx.start()},g.fx.interval=13,g.fx.start=function(){pn||(pn=!0,An())},g.fx.stop=function(){pn=null},g.fx.speeds={slow:600,fast:200,_default:400},g.fn.delay=function(u,h){return u=g.fx&&g.fx.speeds[u]||u,h=h||"fx",this.queue(h,function(m,v){var x=e.setTimeout(m,u);v.stop=function(){e.clearTimeout(x)}})},(function(){var u=D.createElement("input"),h=D.createElement("select"),m=h.appendChild(D.createElement("option"));u.type="checkbox",y.checkOn=u.value!=="",y.optSelected=m.selected,u=D.createElement("input"),u.value="t",u.type="radio",y.radioValue=u.value==="t"})();var Gn,en=g.expr.attrHandle;g.fn.extend({attr:function(u,h){return Je(this,g.attr,u,h,arguments.length>1)},removeAttr:function(u){return this.each(function(){g.removeAttr(this,u)})}}),g.extend({attr:function(u,h,m){var v,x,S=u.nodeType;if(!(S===3||S===8||S===2)){if(typeof u.getAttribute>"u")return g.prop(u,h,m);if((S!==1||!g.isXMLDoc(u))&&(x=g.attrHooks[h.toLowerCase()]||(g.expr.match.bool.test(h)?Gn:void 0)),m!==void 0){if(m===null){g.removeAttr(u,h);return}return x&&"set"in x&&(v=x.set(u,m,h))!==void 0?v:(u.setAttribute(h,m+""),m)}return x&&"get"in x&&(v=x.get(u,h))!==null?v:(v=g.find.attr(u,h),v??void 0)}},attrHooks:{type:{set:function(u,h){if(!y.radioValue&&h==="radio"&&G(u,"input")){var m=u.value;return u.setAttribute("type",h),m&&(u.value=m),h}}}},removeAttr:function(u,h){var m,v=0,x=h&&h.match(Qe);if(x&&u.nodeType===1)for(;m=x[v++];)u.removeAttribute(m)}}),Gn={set:function(u,h,m){return h===!1?g.removeAttr(u,m):u.setAttribute(m,m),m}},g.each(g.expr.match.bool.source.match(/\w+/g),function(u,h){var m=en[h]||g.find.attr;en[h]=function(v,x,S){var A,N,L=x.toLowerCase();return S||(N=en[L],en[L]=A,A=m(v,x,S)!=null?L:null,en[L]=N),A}});var mi=/^(?:input|select|textarea|button)$/i,_i=/^(?:a|area)$/i;g.fn.extend({prop:function(u,h){return Je(this,g.prop,u,h,arguments.length>1)},removeProp:function(u){return this.each(function(){delete this[g.propFix[u]||u]})}}),g.extend({prop:function(u,h,m){var v,x,S=u.nodeType;if(!(S===3||S===8||S===2))return(S!==1||!g.isXMLDoc(u))&&(h=g.propFix[h]||h,x=g.propHooks[h]),m!==void 0?x&&"set"in x&&(v=x.set(u,m,h))!==void 0?v:u[h]=m:x&&"get"in x&&(v=x.get(u,h))!==null?v:u[h]},propHooks:{tabIndex:{get:function(u){var h=g.find.attr(u,"tabindex");return h?parseInt(h,10):mi.test(u.nodeName)||_i.test(u.nodeName)&&u.href?0:-1}}},propFix:{for:"htmlFor",class:"className"}}),y.optSelected||(g.propHooks.selected={get:function(u){var h=u.parentNode;return h&&h.parentNode&&h.parentNode.selectedIndex,null},set:function(u){var h=u.parentNode;h&&(h.selectedIndex,h.parentNode&&h.parentNode.selectedIndex)}}),g.each(["tabIndex","readOnly","maxLength","cellSpacing","cellPadding","rowSpan","colSpan","useMap","frameBorder","contentEditable"],function(){g.propFix[this.toLowerCase()]=this});function Rt(u){var h=u.match(Qe)||[];return h.join(" ")}function Ft(u){return u.getAttribute&&u.getAttribute("class")||""}function Dn(u){return Array.isArray(u)?u:typeof u=="string"?u.match(Qe)||[]:[]}g.fn.extend({addClass:function(u){var h,m,v,x,S,A;return E(u)?this.each(function(N){g(this).addClass(u.call(this,N,Ft(this)))}):(h=Dn(u),h.length?this.each(function(){if(v=Ft(this),m=this.nodeType===1&&" "+Rt(v)+" ",m){for(S=0;S<h.length;S++)x=h[S],m.indexOf(" "+x+" ")<0&&(m+=x+" ");A=Rt(m),v!==A&&this.setAttribute("class",A)}}):this)},removeClass:function(u){var h,m,v,x,S,A;return E(u)?this.each(function(N){g(this).removeClass(u.call(this,N,Ft(this)))}):arguments.length?(h=Dn(u),h.length?this.each(function(){if(v=Ft(this),m=this.nodeType===1&&" "+Rt(v)+" ",m){for(S=0;S<h.length;S++)for(x=h[S];m.indexOf(" "+x+" ")>-1;)m=m.replace(" "+x+" "," ");A=Rt(m),v!==A&&this.setAttribute("class",A)}}):this):this.attr("class","")},toggleClass:function(u,h){var m,v,x,S,A=typeof u,N=A==="string"||Array.isArray(u);return E(u)?this.each(function(L){g(this).toggleClass(u.call(this,L,Ft(this),h),h)}):typeof h=="boolean"&&N?h?this.addClass(u):this.removeClass(u):(m=Dn(u),this.each(function(){if(N)for(S=g(this),x=0;x<m.length;x++)v=m[x],S.hasClass(v)?S.removeClass(v):S.addClass(v);else(u===void 0||A==="boolean")&&(v=Ft(this),v&&ue.set(this,"__className__",v),this.setAttribute&&this.setAttribute("class",v||u===!1?"":ue.get(this,"__className__")||""))}))},hasClass:function(u){var h,m,v=0;for(h=" "+u+" ";m=this[v++];)if(m.nodeType===1&&(" "+Rt(Ft(m))+" ").indexOf(h)>-1)return!0;return!1}});var vi=/\r/g;g.fn.extend({val:function(u){var h,m,v,x=this[0];return arguments.length?(v=E(u),this.each(function(S){var A;this.nodeType===1&&(v?A=u.call(this,S,g(this).val()):A=u,A==null?A="":typeof A=="number"?A+="":Array.isArray(A)&&(A=g.map(A,function(N){return N==null?"":N+""})),h=g.valHooks[this.type]||g.valHooks[this.nodeName.toLowerCase()],(!h||!("set"in h)||h.set(this,A,"value")===void 0)&&(this.value=A))})):x?(h=g.valHooks[x.type]||g.valHooks[x.nodeName.toLowerCase()],h&&"get"in h&&(m=h.get(x,"value"))!==void 0?m:(m=x.value,typeof m=="string"?m.replace(vi,""):m??"")):void 0}}),g.extend({valHooks:{option:{get:function(u){var h=g.find.attr(u,"value");return h??Rt(g.text(u))}},select:{get:function(u){var h,m,v,x=u.options,S=u.selectedIndex,A=u.type==="select-one",N=A?null:[],L=A?S+1:x.length;for(S<0?v=L:v=A?S:0;v<L;v++)if(m=x[v],(m.selected||v===S)&&!m.disabled&&(!m.parentNode.disabled||!G(m.parentNode,"optgroup"))){if(h=g(m).val(),A)return h;N.push(h)}return N},set:function(u,h){for(var m,v,x=u.options,S=g.makeArray(h),A=x.length;A--;)v=x[A],(v.selected=g.inArray(g.valHooks.option.get(v),S)>-1)&&(m=!0);return m||(u.selectedIndex=-1),S}}}}),g.each(["radio","checkbox"],function(){g.valHooks[this]={set:function(u,h){if(Array.isArray(h))return u.checked=g.inArray(g(u).val(),h)>-1}},y.checkOn||(g.valHooks[this].get=function(u){return u.getAttribute("value")===null?"on":u.value})});var tn=e.location,Xn={guid:Date.now()},Tn=/\?/;g.parseXML=function(u){var h,m;if(!u||typeof u!="string")return null;try{h=new e.DOMParser().parseFromString(u,"text/xml")}catch{}return m=h&&h.getElementsByTagName("parsererror")[0],(!h||m)&&g.error("Invalid XML: "+(m?g.map(m.childNodes,function(v){return v.textContent}).join(`
`):u)),h};var Qn=/^(?:focusinfocus|focusoutblur)$/,Jn=function(u){u.stopPropagation()};g.extend(g.event,{trigger:function(u,h,m,v){var x,S,A,N,L,R,U,K,V=[m||D],X=p.call(u,"type")?u.type:u,_e=p.call(u,"namespace")?u.namespace.split("."):[];if(S=K=A=m=m||D,!(m.nodeType===3||m.nodeType===8)&&!Qn.test(X+g.event.triggered)&&(X.indexOf(".")>-1&&(_e=X.split("."),X=_e.shift(),_e.sort()),L=X.indexOf(":")<0&&"on"+X,u=u[g.expando]?u:new g.Event(X,typeof u=="object"&&u),u.isTrigger=v?2:3,u.namespace=_e.join("."),u.rnamespace=u.namespace?new RegExp("(^|\\.)"+_e.join("\\.(?:.*\\.|)")+"(\\.|$)"):null,u.result=void 0,u.target||(u.target=m),h=h==null?[u]:g.makeArray(h,[u]),U=g.event.special[X]||{},!(!v&&U.trigger&&U.trigger.apply(m,h)===!1))){if(!v&&!U.noBubble&&!C(m)){for(N=U.delegateType||X,Qn.test(N+X)||(S=S.parentNode);S;S=S.parentNode)V.push(S),A=S;A===(m.ownerDocument||D)&&V.push(A.defaultView||A.parentWindow||e)}for(x=0;(S=V[x++])&&!u.isPropagationStopped();)K=S,u.type=x>1?N:U.bindType||X,R=(ue.get(S,"events")||Object.create(null))[u.type]&&ue.get(S,"handle"),R&&R.apply(S,h),R=L&&S[L],R&&R.apply&&nt(S)&&(u.result=R.apply(S,h),u.result===!1&&u.preventDefault());return u.type=X,!v&&!u.isDefaultPrevented()&&(!U._default||U._default.apply(V.pop(),h)===!1)&&nt(m)&&L&&E(m[X])&&!C(m)&&(A=m[L],A&&(m[L]=null),g.event.triggered=X,u.isPropagationStopped()&&K.addEventListener(X,Jn),m[X](),u.isPropagationStopped()&&K.removeEventListener(X,Jn),g.event.triggered=void 0,A&&(m[L]=A)),u.result}},simulate:function(u,h,m){var v=g.extend(new g.Event,m,{type:u,isSimulated:!0});g.event.trigger(v,null,h)}}),g.fn.extend({trigger:function(u,h){return this.each(function(){g.event.trigger(u,h,this)})},triggerHandler:function(u,h){var m=this[0];if(m)return g.event.trigger(u,h,m,!0)}});var bi=/\[\]$/,Zn=/\r?\n/g,yi=/^(?:submit|button|image|reset|file)$/i,Ei=/^(?:input|select|textarea|keygen)/i;function wn(u,h,m,v){var x;if(Array.isArray(h))g.each(h,function(S,A){m||bi.test(u)?v(u,A):wn(u+"["+(typeof A=="object"&&A!=null?S:"")+"]",A,m,v)});else if(!m&&P(h)==="object")for(x in h)wn(u+"["+x+"]",h[x],m,v);else v(u,h)}g.param=function(u,h){var m,v=[],x=function(S,A){var N=E(A)?A():A;v[v.length]=encodeURIComponent(S)+"="+encodeURIComponent(N??"")};if(u==null)return"";if(Array.isArray(u)||u.jquery&&!g.isPlainObject(u))g.each(u,function(){x(this.name,this.value)});else for(m in u)wn(m,u[m],h,x);return v.join("&")},g.fn.extend({serialize:function(){return g.param(this.serializeArray())},serializeArray:function(){return this.map(function(){var u=g.prop(this,"elements");return u?g.makeArray(u):this}).filter(function(){var u=this.type;return this.name&&!g(this).is(":disabled")&&Ei.test(this.nodeName)&&!yi.test(u)&&(this.checked||!It.test(u))}).map(function(u,h){var m=g(this).val();return m==null?null:Array.isArray(m)?g.map(m,function(v){return{name:h.name,value:v.replace(Zn,`\r
`)}}):{name:h.name,value:m.replace(Zn,`\r
`)}}).get()}});var xi=/%20/g,Si=/#.*$/,Ci=/([?&])_=[^&]*/,Ai=/^(.*?):[ \t]*([^\r\n]*)$/mg,Di=/^(?:about|app|app-storage|.+-extension|file|res|widget):$/,Ti=/^(?:GET|HEAD)$/,wi=/^\/\//,ei={},On={},ti="*/".concat("*"),$n=D.createElement("a");$n.href=tn.href;function ni(u){return function(h,m){typeof h!="string"&&(m=h,h="*");var v,x=0,S=h.toLowerCase().match(Qe)||[];if(E(m))for(;v=S[x++];)v[0]==="+"?(v=v.slice(1)||"*",(u[v]=u[v]||[]).unshift(m)):(u[v]=u[v]||[]).push(m)}}function ii(u,h,m,v){var x={},S=u===On;function A(N){var L;return x[N]=!0,g.each(u[N]||[],function(R,U){var K=U(h,m,v);if(typeof K=="string"&&!S&&!x[K])return h.dataTypes.unshift(K),A(K),!1;if(S)return!(L=K)}),L}return A(h.dataTypes[0])||!x["*"]&&A("*")}function Mn(u,h){var m,v,x=g.ajaxSettings.flatOptions||{};for(m in h)h[m]!==void 0&&((x[m]?u:v||(v={}))[m]=h[m]);return v&&g.extend(!0,u,v),u}function Oi(u,h,m){for(var v,x,S,A,N=u.contents,L=u.dataTypes;L[0]==="*";)L.shift(),v===void 0&&(v=u.mimeType||h.getResponseHeader("Content-Type"));if(v){for(x in N)if(N[x]&&N[x].test(v)){L.unshift(x);break}}if(L[0]in m)S=L[0];else{for(x in m){if(!L[0]||u.converters[x+" "+L[0]]){S=x;break}A||(A=x)}S=S||A}if(S)return S!==L[0]&&L.unshift(S),m[S]}function $i(u,h,m,v){var x,S,A,N,L,R={},U=u.dataTypes.slice();if(U[1])for(A in u.converters)R[A.toLowerCase()]=u.converters[A];for(S=U.shift();S;)if(u.responseFields[S]&&(m[u.responseFields[S]]=h),!L&&v&&u.dataFilter&&(h=u.dataFilter(h,u.dataType)),L=S,S=U.shift(),S){if(S==="*")S=L;else if(L!=="*"&&L!==S){if(A=R[L+" "+S]||R["* "+S],!A){for(x in R)if(N=x.split(" "),N[1]===S&&(A=R[L+" "+N[0]]||R["* "+N[0]],A)){A===!0?A=R[x]:R[x]!==!0&&(S=N[0],U.unshift(N[1]));break}}if(A!==!0)if(A&&u.throws)h=A(h);else try{h=A(h)}catch(K){return{state:"parsererror",error:A?K:"No conversion from "+L+" to "+S}}}}return{state:"success",data:h}}g.extend({active:0,lastModified:{},etag:{},ajaxSettings:{url:tn.href,type:"GET",isLocal:Di.test(tn.protocol),global:!0,processData:!0,async:!0,contentType:"application/x-www-form-urlencoded; charset=UTF-8",accepts:{"*":ti,text:"text/plain",html:"text/html",xml:"application/xml, text/xml",json:"application/json, text/javascript"},contents:{xml:/\bxml\b/,html:/\bhtml/,json:/\bjson\b/},responseFields:{xml:"responseXML",text:"responseText",json:"responseJSON"},converters:{"* text":String,"text html":!0,"text json":JSON.parse,"text xml":g.parseXML},flatOptions:{url:!0,context:!0}},ajaxSetup:function(u,h){return h?Mn(Mn(u,g.ajaxSettings),h):Mn(g.ajaxSettings,u)},ajaxPrefilter:ni(ei),ajaxTransport:ni(On),ajax:function(u,h){typeof u=="object"&&(h=u,u=void 0),h=h||{};var m,v,x,S,A,N,L,R,U,K,V=g.ajaxSetup({},h),X=V.context||V,_e=V.context&&(X.nodeType||X.jquery)?g(X):g.event,we=g.Deferred(),Se=g.Callbacks("once memory"),ze=V.statusCode||{},Ue={},ht={},pt="canceled",De={readyState:0,getResponseHeader:function(Oe){var Be;if(L){if(!S)for(S={};Be=Ai.exec(x);)S[Be[1].toLowerCase()+" "]=(S[Be[1].toLowerCase()+" "]||[]).concat(Be[2]);Be=S[Oe.toLowerCase()+" "]}return Be==null?null:Be.join(", ")},getAllResponseHeaders:function(){return L?x:null},setRequestHeader:function(Oe,Be){return L==null&&(Oe=ht[Oe.toLowerCase()]=ht[Oe.toLowerCase()]||Oe,Ue[Oe]=Be),this},overrideMimeType:function(Oe){return L==null&&(V.mimeType=Oe),this},statusCode:function(Oe){var Be;if(Oe)if(L)De.always(Oe[De.status]);else for(Be in Oe)ze[Be]=[ze[Be],Oe[Be]];return this},abort:function(Oe){var Be=Oe||pt;return m&&m.abort(Be),Ht(0,Be),this}};if(we.promise(De),V.url=((u||V.url||tn.href)+"").replace(wi,tn.protocol+"//"),V.type=h.method||h.type||V.method||V.type,V.dataTypes=(V.dataType||"*").toLowerCase().match(Qe)||[""],V.crossDomain==null){N=D.createElement("a");try{N.href=V.url,N.href=N.href,V.crossDomain=$n.protocol+"//"+$n.host!=N.protocol+"//"+N.host}catch{V.crossDomain=!0}}if(V.data&&V.processData&&typeof V.data!="string"&&(V.data=g.param(V.data,V.traditional)),ii(ei,V,h,De),L)return De;R=g.event&&V.global,R&&g.active++===0&&g.event.trigger("ajaxStart"),V.type=V.type.toUpperCase(),V.hasContent=!Ti.test(V.type),v=V.url.replace(Si,""),V.hasContent?V.data&&V.processData&&(V.contentType||"").indexOf("application/x-www-form-urlencoded")===0&&(V.data=V.data.replace(xi,"+")):(K=V.url.slice(v.length),V.data&&(V.processData||typeof V.data=="string")&&(v+=(Tn.test(v)?"&":"?")+V.data,delete V.data),V.cache===!1&&(v=v.replace(Ci,"$1"),K=(Tn.test(v)?"&":"?")+"_="+Xn.guid+++K),V.url=v+K),V.ifModified&&(g.lastModified[v]&&De.setRequestHeader("If-Modified-Since",g.lastModified[v]),g.etag[v]&&De.setRequestHeader("If-None-Match",g.etag[v])),(V.data&&V.hasContent&&V.contentType!==!1||h.contentType)&&De.setRequestHeader("Content-Type",V.contentType),De.setRequestHeader("Accept",V.dataTypes[0]&&V.accepts[V.dataTypes[0]]?V.accepts[V.dataTypes[0]]+(V.dataTypes[0]!=="*"?", "+ti+"; q=0.01":""):V.accepts["*"]);for(U in V.headers)De.setRequestHeader(U,V.headers[U]);if(V.beforeSend&&(V.beforeSend.call(X,De,V)===!1||L))return De.abort();if(pt="abort",Se.add(V.complete),De.done(V.success),De.fail(V.error),m=ii(On,V,h,De),!m)Ht(-1,"No Transport");else{if(De.readyState=1,R&&_e.trigger("ajaxSend",[De,V]),L)return De;V.async&&V.timeout>0&&(A=e.setTimeout(function(){De.abort("timeout")},V.timeout));try{L=!1,m.send(Ue,Ht)}catch(Oe){if(L)throw Oe;Ht(-1,Oe)}}function Ht(Oe,Be,rn,Nn){var gt,an,mt,Mt,Lt,at=Be;L||(L=!0,A&&e.clearTimeout(A),m=void 0,x=Nn||"",De.readyState=Oe>0?4:0,gt=Oe>=200&&Oe<300||Oe===304,rn&&(Mt=Oi(V,De,rn)),!gt&&g.inArray("script",V.dataTypes)>-1&&g.inArray("json",V.dataTypes)<0&&(V.converters["text script"]=function(){}),Mt=$i(V,Mt,De,gt),gt?(V.ifModified&&(Lt=De.getResponseHeader("Last-Modified"),Lt&&(g.lastModified[v]=Lt),Lt=De.getResponseHeader("etag"),Lt&&(g.etag[v]=Lt)),Oe===204||V.type==="HEAD"?at="nocontent":Oe===304?at="notmodified":(at=Mt.state,an=Mt.data,mt=Mt.error,gt=!mt)):(mt=at,(Oe||!at)&&(at="error",Oe<0&&(Oe=0))),De.status=Oe,De.statusText=(Be||at)+"",gt?we.resolveWith(X,[an,at,De]):we.rejectWith(X,[De,at,mt]),De.statusCode(ze),ze=void 0,R&&_e.trigger(gt?"ajaxSuccess":"ajaxError",[De,V,gt?an:mt]),Se.fireWith(X,[De,at]),R&&(_e.trigger("ajaxComplete",[De,V]),--g.active||g.event.trigger("ajaxStop")))}return De},getJSON:function(u,h,m){return g.get(u,h,m,"json")},getScript:function(u,h){return g.get(u,void 0,h,"script")}}),g.each(["get","post"],function(u,h){g[h]=function(m,v,x,S){return E(v)&&(S=S||x,x=v,v=void 0),g.ajax(g.extend({url:m,type:h,dataType:S,data:v,success:x},g.isPlainObject(m)&&m))}}),g.ajaxPrefilter(function(u){var h;for(h in u.headers)h.toLowerCase()==="content-type"&&(u.contentType=u.headers[h]||"")}),g._evalUrl=function(u,h,m){return g.ajax({url:u,type:"GET",dataType:"script",cache:!0,async:!1,global:!1,converters:{"text script":function(){}},dataFilter:function(v){g.globalEval(v,h,m)}})},g.fn.extend({wrapAll:function(u){var h;return this[0]&&(E(u)&&(u=u.call(this[0])),h=g(u,this[0].ownerDocument).eq(0).clone(!0),this[0].parentNode&&h.insertBefore(this[0]),h.map(function(){for(var m=this;m.firstElementChild;)m=m.firstElementChild;return m}).append(this)),this},wrapInner:function(u){return E(u)?this.each(function(h){g(this).wrapInner(u.call(this,h))}):this.each(function(){var h=g(this),m=h.contents();m.length?m.wrapAll(u):h.append(u)})},wrap:function(u){var h=E(u);return this.each(function(m){g(this).wrapAll(h?u.call(this,m):u)})},unwrap:function(u){return this.parent(u).not("body").each(function(){g(this).replaceWith(this.childNodes)}),this}}),g.expr.pseudos.hidden=function(u){return!g.expr.pseudos.visible(u)},g.expr.pseudos.visible=function(u){return!!(u.offsetWidth||u.offsetHeight||u.getClientRects().length)},g.ajaxSettings.xhr=function(){try{return new e.XMLHttpRequest}catch{}};var Mi={0:200,1223:204},nn=g.ajaxSettings.xhr();y.cors=!!nn&&"withCredentials"in nn,y.ajax=nn=!!nn,g.ajaxTransport(function(u){var h,m;if(y.cors||nn&&!u.crossDomain)return{send:function(v,x){var S,A=u.xhr();if(A.open(u.type,u.url,u.async,u.username,u.password),u.xhrFields)for(S in u.xhrFields)A[S]=u.xhrFields[S];u.mimeType&&A.overrideMimeType&&A.overrideMimeType(u.mimeType),!u.crossDomain&&!v["X-Requested-With"]&&(v["X-Requested-With"]="XMLHttpRequest");for(S in v)A.setRequestHeader(S,v[S]);h=function(N){return function(){h&&(h=m=A.onload=A.onerror=A.onabort=A.ontimeout=A.onreadystatechange=null,N==="abort"?A.abort():N==="error"?typeof A.status!="number"?x(0,"error"):x(A.status,A.statusText):x(Mi[A.status]||A.status,A.statusText,(A.responseType||"text")!=="text"||typeof A.responseText!="string"?{binary:A.response}:{text:A.responseText},A.getAllResponseHeaders()))}},A.onload=h(),m=A.onerror=A.ontimeout=h("error"),A.onabort!==void 0?A.onabort=m:A.onreadystatechange=function(){A.readyState===4&&e.setTimeout(function(){h&&m()})},h=h("abort");try{A.send(u.hasContent&&u.data||null)}catch(N){if(h)throw N}},abort:function(){h&&h()}}}),g.ajaxPrefilter(function(u){u.crossDomain&&(u.contents.script=!1)}),g.ajaxSetup({accepts:{script:"text/javascript, application/javascript, application/ecmascript, application/x-ecmascript"},contents:{script:/\b(?:java|ecma)script\b/},converters:{"text script":function(u){return g.globalEval(u),u}}}),g.ajaxPrefilter("script",function(u){u.cache===void 0&&(u.cache=!1),u.crossDomain&&(u.type="GET")}),g.ajaxTransport("script",function(u){if(u.crossDomain||u.scriptAttrs){var h,m;return{send:function(v,x){h=g("<script>").attr(u.scriptAttrs||{}).prop({charset:u.scriptCharset,src:u.url}).on("load error",m=function(S){h.remove(),m=null,S&&x(S.type==="error"?404:200,S.type)}),D.head.appendChild(h[0])},abort:function(){m&&m()}}}});var ri=[],Ln=/(=)\?(?=&|$)|\?\?/;g.ajaxSetup({jsonp:"callback",jsonpCallback:function(){var u=ri.pop()||g.expando+"_"+Xn.guid++;return this[u]=!0,u}}),g.ajaxPrefilter("json jsonp",function(u,h,m){var v,x,S,A=u.jsonp!==!1&&(Ln.test(u.url)?"url":typeof u.data=="string"&&(u.contentType||"").indexOf("application/x-www-form-urlencoded")===0&&Ln.test(u.data)&&"data");if(A||u.dataTypes[0]==="jsonp")return v=u.jsonpCallback=E(u.jsonpCallback)?u.jsonpCallback():u.jsonpCallback,A?u[A]=u[A].replace(Ln,"$1"+v):u.jsonp!==!1&&(u.url+=(Tn.test(u.url)?"&":"?")+u.jsonp+"="+v),u.converters["script json"]=function(){return S||g.error(v+" was not called"),S[0]},u.dataTypes[0]="json",x=e[v],e[v]=function(){S=arguments},m.always(function(){x===void 0?g(e).removeProp(v):e[v]=x,u[v]&&(u.jsonpCallback=h.jsonpCallback,ri.push(v)),S&&E(x)&&x(S[0]),S=x=void 0}),"script"}),y.createHTMLDocument=(function(){var u=D.implementation.createHTMLDocument("").body;return u.innerHTML="<form></form><form></form>",u.childNodes.length===2})(),g.parseHTML=function(u,h,m){if(typeof u!="string")return[];typeof h=="boolean"&&(m=h,h=!1);var v,x,S;return h||(y.createHTMLDocument?(h=D.implementation.createHTMLDocument(""),v=h.createElement("base"),v.href=D.location.href,h.head.appendChild(v)):h=D),x=Te.exec(u),S=!m&&[],x?[h.createElement(x[1])]:(x=ie([u],h,S),S&&S.length&&g(S).remove(),g.merge([],x.childNodes))},g.fn.load=function(u,h,m){var v,x,S,A=this,N=u.indexOf(" ");return N>-1&&(v=Rt(u.slice(N)),u=u.slice(0,N)),E(h)?(m=h,h=void 0):h&&typeof h=="object"&&(x="POST"),A.length>0&&g.ajax({url:u,type:x||"GET",dataType:"html",data:h}).done(function(L){S=arguments,A.html(v?g("<div>").append(g.parseHTML(L)).find(v):L)}).always(m&&function(L,R){A.each(function(){m.apply(this,S||[L.responseText,R,L])})}),this},g.expr.pseudos.animated=function(u){return g.grep(g.timers,function(h){return u===h.elem}).length},g.offset={setOffset:function(u,h,m){var v,x,S,A,N,L,R,U=g.css(u,"position"),K=g(u),V={};U==="static"&&(u.style.position="relative"),N=K.offset(),S=g.css(u,"top"),L=g.css(u,"left"),R=(U==="absolute"||U==="fixed")&&(S+L).indexOf("auto")>-1,R?(v=K.position(),A=v.top,x=v.left):(A=parseFloat(S)||0,x=parseFloat(L)||0),E(h)&&(h=h.call(u,m,g.extend({},N))),h.top!=null&&(V.top=h.top-N.top+A),h.left!=null&&(V.left=h.left-N.left+x),"using"in h?h.using.call(u,V):K.css(V)}},g.fn.extend({offset:function(u){if(arguments.length)return u===void 0?this:this.each(function(x){g.offset.setOffset(this,u,x)});var h,m,v=this[0];if(v)return v.getClientRects().length?(h=v.getBoundingClientRect(),m=v.ownerDocument.defaultView,{top:h.top+m.pageYOffset,left:h.left+m.pageXOffset}):{top:0,left:0}},position:function(){if(this[0]){var u,h,m,v=this[0],x={top:0,left:0};if(g.css(v,"position")==="fixed")h=v.getBoundingClientRect();else{for(h=this.offset(),m=v.ownerDocument,u=v.offsetParent||m.documentElement;u&&(u===m.body||u===m.documentElement)&&g.css(u,"position")==="static";)u=u.parentNode;u&&u!==v&&u.nodeType===1&&(x=g(u).offset(),x.top+=g.css(u,"borderTopWidth",!0),x.left+=g.css(u,"borderLeftWidth",!0))}return{top:h.top-x.top-g.css(v,"marginTop",!0),left:h.left-x.left-g.css(v,"marginLeft",!0)}}},offsetParent:function(){return this.map(function(){for(var u=this.offsetParent;u&&g.css(u,"position")==="static";)u=u.offsetParent;return u||bt})}}),g.each({scrollLeft:"pageXOffset",scrollTop:"pageYOffset"},function(u,h){var m=h==="pageYOffset";g.fn[u]=function(v){return Je(this,function(x,S,A){var N;if(C(x)?N=x:x.nodeType===9&&(N=x.defaultView),A===void 0)return N?N[h]:x[S];N?N.scrollTo(m?N.pageXOffset:A,m?A:N.pageYOffset):x[S]=A},u,v,arguments.length)}}),g.each(["top","left"],function(u,h){g.cssHooks[h]=Bn(y.pixelPosition,function(m,v){if(v)return v=Zt(m,h),Qt.test(v)?g(m).position()[h]+"px":v})}),g.each({Height:"height",Width:"width"},function(u,h){g.each({padding:"inner"+u,content:h,"":"outer"+u},function(m,v){g.fn[v]=function(x,S){var A=arguments.length&&(m||typeof x!="boolean"),N=m||(x===!0||S===!0?"margin":"border");return Je(this,function(L,R,U){var K;return C(L)?v.indexOf("outer")===0?L["inner"+u]:L.document.documentElement["client"+u]:L.nodeType===9?(K=L.documentElement,Math.max(L.body["scroll"+u],K["scroll"+u],L.body["offset"+u],K["offset"+u],K["client"+u])):U===void 0?g.css(L,R,N):g.style(L,R,U,N)},h,A?x:void 0,A)}})}),g.each(["ajaxStart","ajaxStop","ajaxComplete","ajaxError","ajaxSuccess","ajaxSend"],function(u,h){g.fn[h]=function(m){return this.on(h,m)}}),g.fn.extend({bind:function(u,h,m){return this.on(u,null,h,m)},unbind:function(u,h){return this.off(u,null,h)},delegate:function(u,h,m,v){return this.on(h,u,m,v)},undelegate:function(u,h,m){return arguments.length===1?this.off(u,"**"):this.off(h,u||"**",m)},hover:function(u,h){return this.on("mouseenter",u).on("mouseleave",h||u)}}),g.each("blur focus focusin focusout resize scroll click dblclick mousedown mouseup mousemove mouseover mouseout mouseenter mouseleave change select submit keydown keypress keyup contextmenu".split(" "),function(u,h){g.fn[h]=function(m,v){return arguments.length>0?this.on(h,null,m,v):this.trigger(h)}});var Li=/^[\s\uFEFF\xA0]+|([^\s\uFEFF\xA0])[\s\uFEFF\xA0]+$/g;g.proxy=function(u,h){var m,v,x;if(typeof h=="string"&&(m=u[h],h=u,u=m),!!E(u))return v=o.call(arguments,2),x=function(){return u.apply(h||this,v.concat(o.call(arguments)))},x.guid=u.guid=u.guid||g.guid++,x},g.holdReady=function(u){u?g.readyWait++:g.ready(!0)},g.isArray=Array.isArray,g.parseJSON=JSON.parse,g.nodeName=G,g.isFunction=E,g.isWindow=C,g.camelCase=qe,g.type=P,g.now=Date.now,g.isNumeric=function(u){var h=g.type(u);return(h==="number"||h==="string")&&!isNaN(u-parseFloat(u))},g.trim=function(u){return u==null?"":(u+"").replace(Li,"$1")};var Ni=e.jQuery,ki=e.$;return g.noConflict=function(u){return e.$===g&&(e.$=ki),u&&e.jQuery===g&&(e.jQuery=Ni),g},typeof t>"u"&&(e.jQuery=e.$=g),g})})(jquery$1)),jquery$1.exports}var jqueryExports=requireJquery();const jQuery$1=getDefaultExportFromCjs(jqueryExports),src=`/*!
 * Select2 4.1.0
 * https://select2.github.io
 *
 * Released under the MIT license
 * https://github.com/select2/select2/blob/master/LICENSE.md
 */
;(function (factory) {
  if (typeof define === 'function' && define.amd) {
    // AMD. Register as an anonymous module.
    define(['jquery'], factory);
  } else if (typeof module === 'object' && module.exports) {
    // Node/CommonJS
    module.exports = function (root, jQuery) {
      if (jQuery === undefined) {
        // require('jQuery') returns a factory that requires window to
        // build a jQuery instance, we normalize how we use modules
        // that require this pattern but the window provided is a noop
        // if it's defined (how jquery works)
        if (typeof window !== 'undefined') {
          jQuery = require('jquery');
        }
        else {
          jQuery = require('jquery')(root);
        }
      }
      factory(jQuery);
      return jQuery;
    };
  } else {
    // Browser globals
    factory(jQuery);
  }
} (function (jQuery) {
  // This is needed so we can catch the AMD loader configuration and use it
  // The inner file should be wrapped (by \`banner.start.js\`) in a function that
  // returns the AMD loader references.
  var S2 =(function () {
  // Restore the Select2 AMD loader so it can be used
  // Needed mostly in the language files, where the loader is not inserted
  if (jQuery && jQuery.fn && jQuery.fn.select2 && jQuery.fn.select2.amd) {
    var S2 = jQuery.fn.select2.amd;
  }
var S2;(function () { if (!S2 || !S2.requirejs) {
if (!S2) { S2 = {}; } else { require = S2; }
/**
 * @license almond 0.3.3 Copyright jQuery Foundation and other contributors.
 * Released under MIT license, http://github.com/requirejs/almond/LICENSE
 */
//Going sloppy to avoid 'use strict' string cost, but strict practices should
//be followed.
/*global setTimeout: false */

var requirejs, require, define;
(function (undef) {
    var main, req, makeMap, handlers,
        defined = {},
        waiting = {},
        config = {},
        defining = {},
        hasOwn = Object.prototype.hasOwnProperty,
        aps = [].slice,
        jsSuffixRegExp = /\\.js$/;

    function hasProp(obj, prop) {
        return hasOwn.call(obj, prop);
    }

    /**
     * Given a relative module name, like ./something, normalize it to
     * a real name that can be mapped to a path.
     * @param {String} name the relative name
     * @param {String} baseName a real name that the name arg is relative
     * to.
     * @returns {String} normalized name
     */
    function normalize(name, baseName) {
        var nameParts, nameSegment, mapValue, foundMap, lastIndex,
            foundI, foundStarMap, starI, i, j, part, normalizedBaseParts,
            baseParts = baseName && baseName.split("/"),
            map = config.map,
            starMap = (map && map['*']) || {};

        //Adjust any relative paths.
        if (name) {
            name = name.split('/');
            lastIndex = name.length - 1;

            // If wanting node ID compatibility, strip .js from end
            // of IDs. Have to do this here, and not in nameToUrl
            // because node allows either .js or non .js to map
            // to same file.
            if (config.nodeIdCompat && jsSuffixRegExp.test(name[lastIndex])) {
                name[lastIndex] = name[lastIndex].replace(jsSuffixRegExp, '');
            }

            // Starts with a '.' so need the baseName
            if (name[0].charAt(0) === '.' && baseParts) {
                //Convert baseName to array, and lop off the last part,
                //so that . matches that 'directory' and not name of the baseName's
                //module. For instance, baseName of 'one/two/three', maps to
                //'one/two/three.js', but we want the directory, 'one/two' for
                //this normalization.
                normalizedBaseParts = baseParts.slice(0, baseParts.length - 1);
                name = normalizedBaseParts.concat(name);
            }

            //start trimDots
            for (i = 0; i < name.length; i++) {
                part = name[i];
                if (part === '.') {
                    name.splice(i, 1);
                    i -= 1;
                } else if (part === '..') {
                    // If at the start, or previous value is still ..,
                    // keep them so that when converted to a path it may
                    // still work when converted to a path, even though
                    // as an ID it is less than ideal. In larger point
                    // releases, may be better to just kick out an error.
                    if (i === 0 || (i === 1 && name[2] === '..') || name[i - 1] === '..') {
                        continue;
                    } else if (i > 0) {
                        name.splice(i - 1, 2);
                        i -= 2;
                    }
                }
            }
            //end trimDots

            name = name.join('/');
        }

        //Apply map config if available.
        if ((baseParts || starMap) && map) {
            nameParts = name.split('/');

            for (i = nameParts.length; i > 0; i -= 1) {
                nameSegment = nameParts.slice(0, i).join("/");

                if (baseParts) {
                    //Find the longest baseName segment match in the config.
                    //So, do joins on the biggest to smallest lengths of baseParts.
                    for (j = baseParts.length; j > 0; j -= 1) {
                        mapValue = map[baseParts.slice(0, j).join('/')];

                        //baseName segment has  config, find if it has one for
                        //this name.
                        if (mapValue) {
                            mapValue = mapValue[nameSegment];
                            if (mapValue) {
                                //Match, update name to the new value.
                                foundMap = mapValue;
                                foundI = i;
                                break;
                            }
                        }
                    }
                }

                if (foundMap) {
                    break;
                }

                //Check for a star map match, but just hold on to it,
                //if there is a shorter segment match later in a matching
                //config, then favor over this star map.
                if (!foundStarMap && starMap && starMap[nameSegment]) {
                    foundStarMap = starMap[nameSegment];
                    starI = i;
                }
            }

            if (!foundMap && foundStarMap) {
                foundMap = foundStarMap;
                foundI = starI;
            }

            if (foundMap) {
                nameParts.splice(0, foundI, foundMap);
                name = nameParts.join('/');
            }
        }

        return name;
    }

    function makeRequire(relName, forceSync) {
        return function () {
            //A version of a require function that passes a moduleName
            //value for items that may need to
            //look up paths relative to the moduleName
            var args = aps.call(arguments, 0);

            //If first arg is not require('string'), and there is only
            //one arg, it is the array form without a callback. Insert
            //a null so that the following concat is correct.
            if (typeof args[0] !== 'string' && args.length === 1) {
                args.push(null);
            }
            return req.apply(undef, args.concat([relName, forceSync]));
        };
    }

    function makeNormalize(relName) {
        return function (name) {
            return normalize(name, relName);
        };
    }

    function makeLoad(depName) {
        return function (value) {
            defined[depName] = value;
        };
    }

    function callDep(name) {
        if (hasProp(waiting, name)) {
            var args = waiting[name];
            delete waiting[name];
            defining[name] = true;
            main.apply(undef, args);
        }

        if (!hasProp(defined, name) && !hasProp(defining, name)) {
            throw new Error('No ' + name);
        }
        return defined[name];
    }

    //Turns a plugin!resource to [plugin, resource]
    //with the plugin being undefined if the name
    //did not have a plugin prefix.
    function splitPrefix(name) {
        var prefix,
            index = name ? name.indexOf('!') : -1;
        if (index > -1) {
            prefix = name.substring(0, index);
            name = name.substring(index + 1, name.length);
        }
        return [prefix, name];
    }

    //Creates a parts array for a relName where first part is plugin ID,
    //second part is resource ID. Assumes relName has already been normalized.
    function makeRelParts(relName) {
        return relName ? splitPrefix(relName) : [];
    }

    /**
     * Makes a name map, normalizing the name, and using a plugin
     * for normalization if necessary. Grabs a ref to plugin
     * too, as an optimization.
     */
    makeMap = function (name, relParts) {
        var plugin,
            parts = splitPrefix(name),
            prefix = parts[0],
            relResourceName = relParts[1];

        name = parts[1];

        if (prefix) {
            prefix = normalize(prefix, relResourceName);
            plugin = callDep(prefix);
        }

        //Normalize according
        if (prefix) {
            if (plugin && plugin.normalize) {
                name = plugin.normalize(name, makeNormalize(relResourceName));
            } else {
                name = normalize(name, relResourceName);
            }
        } else {
            name = normalize(name, relResourceName);
            parts = splitPrefix(name);
            prefix = parts[0];
            name = parts[1];
            if (prefix) {
                plugin = callDep(prefix);
            }
        }

        //Using ridiculous property names for space reasons
        return {
            f: prefix ? prefix + '!' + name : name, //fullName
            n: name,
            pr: prefix,
            p: plugin
        };
    };

    function makeConfig(name) {
        return function () {
            return (config && config.config && config.config[name]) || {};
        };
    }

    handlers = {
        require: function (name) {
            return makeRequire(name);
        },
        exports: function (name) {
            var e = defined[name];
            if (typeof e !== 'undefined') {
                return e;
            } else {
                return (defined[name] = {});
            }
        },
        module: function (name) {
            return {
                id: name,
                uri: '',
                exports: defined[name],
                config: makeConfig(name)
            };
        }
    };

    main = function (name, deps, callback, relName) {
        var cjsModule, depName, ret, map, i, relParts,
            args = [],
            callbackType = typeof callback,
            usingExports;

        //Use name if no relName
        relName = relName || name;
        relParts = makeRelParts(relName);

        //Call the callback to define the module, if necessary.
        if (callbackType === 'undefined' || callbackType === 'function') {
            //Pull out the defined dependencies and pass the ordered
            //values to the callback.
            //Default to [require, exports, module] if no deps
            deps = !deps.length && callback.length ? ['require', 'exports', 'module'] : deps;
            for (i = 0; i < deps.length; i += 1) {
                map = makeMap(deps[i], relParts);
                depName = map.f;

                //Fast path CommonJS standard dependencies.
                if (depName === "require") {
                    args[i] = handlers.require(name);
                } else if (depName === "exports") {
                    //CommonJS module spec 1.1
                    args[i] = handlers.exports(name);
                    usingExports = true;
                } else if (depName === "module") {
                    //CommonJS module spec 1.1
                    cjsModule = args[i] = handlers.module(name);
                } else if (hasProp(defined, depName) ||
                           hasProp(waiting, depName) ||
                           hasProp(defining, depName)) {
                    args[i] = callDep(depName);
                } else if (map.p) {
                    map.p.load(map.n, makeRequire(relName, true), makeLoad(depName), {});
                    args[i] = defined[depName];
                } else {
                    throw new Error(name + ' missing ' + depName);
                }
            }

            ret = callback ? callback.apply(defined[name], args) : undefined;

            if (name) {
                //If setting exports via "module" is in play,
                //favor that over return value and exports. After that,
                //favor a non-undefined return value over exports use.
                if (cjsModule && cjsModule.exports !== undef &&
                        cjsModule.exports !== defined[name]) {
                    defined[name] = cjsModule.exports;
                } else if (ret !== undef || !usingExports) {
                    //Use the return value from the function.
                    defined[name] = ret;
                }
            }
        } else if (name) {
            //May just be an object definition for the module. Only
            //worry about defining if have a module name.
            defined[name] = callback;
        }
    };

    requirejs = require = req = function (deps, callback, relName, forceSync, alt) {
        if (typeof deps === "string") {
            if (handlers[deps]) {
                //callback in this case is really relName
                return handlers[deps](callback);
            }
            //Just return the module wanted. In this scenario, the
            //deps arg is the module name, and second arg (if passed)
            //is just the relName.
            //Normalize module name, if it contains . or ..
            return callDep(makeMap(deps, makeRelParts(callback)).f);
        } else if (!deps.splice) {
            //deps is a config object, not an array.
            config = deps;
            if (config.deps) {
                req(config.deps, config.callback);
            }
            if (!callback) {
                return;
            }

            if (callback.splice) {
                //callback is an array, which means it is a dependency list.
                //Adjust args if there are dependencies
                deps = callback;
                callback = relName;
                relName = null;
            } else {
                deps = undef;
            }
        }

        //Support require(['a'])
        callback = callback || function () {};

        //If relName is a function, it is an errback handler,
        //so remove it.
        if (typeof relName === 'function') {
            relName = forceSync;
            forceSync = alt;
        }

        //Simulate async callback;
        if (forceSync) {
            main(undef, deps, callback, relName);
        } else {
            //Using a non-zero value because of concern for what old browsers
            //do, and latest browsers "upgrade" to 4 if lower value is used:
            //http://www.whatwg.org/specs/web-apps/current-work/multipage/timers.html#dom-windowtimers-settimeout:
            //If want a value immediately, use require('id') instead -- something
            //that works in almond on the global level, but not guaranteed and
            //unlikely to work in other AMD implementations.
            setTimeout(function () {
                main(undef, deps, callback, relName);
            }, 4);
        }

        return req;
    };

    /**
     * Just drops the config on the floor, but returns req in case
     * the config return value is used.
     */
    req.config = function (cfg) {
        return req(cfg);
    };

    /**
     * Expose module registry for debugging and tooling
     */
    requirejs._defined = defined;

    define = function (name, deps, callback) {
        if (typeof name !== 'string') {
            throw new Error('See almond README: incorrect module build, no module name');
        }

        //This module may not have dependencies
        if (!deps.splice) {
            //deps is not an array, so probably means
            //an object literal or factory function for
            //the value. Adjust args.
            callback = deps;
            deps = [];
        }

        if (!hasProp(defined, name) && !hasProp(waiting, name)) {
            waiting[name] = [name, deps, callback];
        }
    };

    define.amd = {
        jQuery: true
    };
}());

S2.requirejs = requirejs;S2.require = require;S2.define = define;
}
}());
S2.define("almond", function(){});

/* global jQuery:false, $:false */
S2.define('jquery',[],function () {
  var _$ = jQuery || $;

  if (_$ == null && console && console.error) {
    console.error(
      'Select2: An instance of jQuery or a jQuery-compatible library was not ' +
      'found. Make sure that you are including jQuery before Select2 on your ' +
      'web page.'
    );
  }

  return _$;
});

S2.define('select2/utils',[
], function () {
  var Utils = {};

  Utils.Extend = function (ChildClass, SuperClass) {
    var __hasProp = {}.hasOwnProperty;

    function BaseConstructor () {
      this.constructor = ChildClass;
    }

    for (var key in SuperClass) {
      if (__hasProp.call(SuperClass, key)) {
        ChildClass[key] = SuperClass[key];
      }
    }

    BaseConstructor.prototype = SuperClass.prototype;
    ChildClass.prototype = new BaseConstructor();
    ChildClass.__super__ = SuperClass.prototype;

    return ChildClass;
  };

  function getMethods (theClass) {
    var proto = theClass.prototype;

    var methods = [];

    for (var methodName in proto) {
      var m = proto[methodName];

      if (typeof m !== 'function') {
        continue;
      }

      if (methodName === 'constructor') {
        continue;
      }

      methods.push(methodName);
    }

    return methods;
  }

  Utils.Decorate = function (SuperClass, DecoratorClass) {
    var decoratedMethods = getMethods(DecoratorClass);
    var superMethods = getMethods(SuperClass);

    function DecoratedClass () {
      var unshift = Array.prototype.unshift;

      var argCount = DecoratorClass.prototype.constructor.length;

      var calledConstructor = SuperClass.prototype.constructor;

      if (argCount > 0) {
        unshift.call(arguments, SuperClass.prototype.constructor);

        calledConstructor = DecoratorClass.prototype.constructor;
      }

      calledConstructor.apply(this, arguments);
    }

    DecoratorClass.displayName = SuperClass.displayName;

    function ctr () {
      this.constructor = DecoratedClass;
    }

    DecoratedClass.prototype = new ctr();

    for (var m = 0; m < superMethods.length; m++) {
      var superMethod = superMethods[m];

      DecoratedClass.prototype[superMethod] =
        SuperClass.prototype[superMethod];
    }

    var calledMethod = function (methodName) {
      // Stub out the original method if it's not decorating an actual method
      var originalMethod = function () {};

      if (methodName in DecoratedClass.prototype) {
        originalMethod = DecoratedClass.prototype[methodName];
      }

      var decoratedMethod = DecoratorClass.prototype[methodName];

      return function () {
        var unshift = Array.prototype.unshift;

        unshift.call(arguments, originalMethod);

        return decoratedMethod.apply(this, arguments);
      };
    };

    for (var d = 0; d < decoratedMethods.length; d++) {
      var decoratedMethod = decoratedMethods[d];

      DecoratedClass.prototype[decoratedMethod] = calledMethod(decoratedMethod);
    }

    return DecoratedClass;
  };

  var Observable = function () {
    this.listeners = {};
  };

  Observable.prototype.on = function (event, callback) {
    this.listeners = this.listeners || {};

    if (event in this.listeners) {
      this.listeners[event].push(callback);
    } else {
      this.listeners[event] = [callback];
    }
  };

  Observable.prototype.trigger = function (event) {
    var slice = Array.prototype.slice;
    var params = slice.call(arguments, 1);

    this.listeners = this.listeners || {};

    // Params should always come in as an array
    if (params == null) {
      params = [];
    }

    // If there are no arguments to the event, use a temporary object
    if (params.length === 0) {
      params.push({});
    }

    // Set the \`_type\` of the first object to the event
    params[0]._type = event;

    if (event in this.listeners) {
      this.invoke(this.listeners[event], slice.call(arguments, 1));
    }

    if ('*' in this.listeners) {
      this.invoke(this.listeners['*'], arguments);
    }
  };

  Observable.prototype.invoke = function (listeners, params) {
    for (var i = 0, len = listeners.length; i < len; i++) {
      listeners[i].apply(this, params);
    }
  };

  Utils.Observable = Observable;

  Utils.generateChars = function (length) {
    var chars = '';

    for (var i = 0; i < length; i++) {
      var randomChar = Math.floor(Math.random() * 36);
      chars += randomChar.toString(36);
    }

    return chars;
  };

  Utils.bind = function (func, context) {
    return function () {
      func.apply(context, arguments);
    };
  };

  Utils._convertData = function (data) {
    for (var originalKey in data) {
      var keys = originalKey.split('-');

      var dataLevel = data;

      if (keys.length === 1) {
        continue;
      }

      for (var k = 0; k < keys.length; k++) {
        var key = keys[k];

        // Lowercase the first letter
        // By default, dash-separated becomes camelCase
        key = key.substring(0, 1).toLowerCase() + key.substring(1);

        if (!(key in dataLevel)) {
          dataLevel[key] = {};
        }

        if (k == keys.length - 1) {
          dataLevel[key] = data[originalKey];
        }

        dataLevel = dataLevel[key];
      }

      delete data[originalKey];
    }

    return data;
  };

  Utils.hasScroll = function (index, el) {
    // Adapted from the function created by @ShadowScripter
    // and adapted by @BillBarry on the Stack Exchange Code Review website.
    // The original code can be found at
    // http://codereview.stackexchange.com/q/13338
    // and was designed to be used with the Sizzle selector engine.

    var overflowX = el.style.overflowX;
    var overflowY = el.style.overflowY;

    //Check both x and y declarations
    if (overflowX === overflowY &&
        (overflowY === 'hidden' || overflowY === 'visible')) {
      return false;
    }

    if (overflowX === 'scroll' || overflowY === 'scroll') {
      return true;
    }

    var computedEl = window.getComputedStyle(el);

    return (parseFloat(computedEl.height) < el.scrollHeight ||
      parseFloat(computedEl.width) < el.scrollWidth);
  };

  Utils.escapeMarkup = function (markup) {
    var replaceMap = {
      '\\\\': '&#92;',
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      '\\'': '&#39;',
      '/': '&#47;'
    };

    // Do not try to escape the markup if it's not a string
    if (typeof markup !== 'string') {
      return markup;
    }

    return String(markup).replace(/[&<>"'\\/\\\\]/g, function (match) {
      return replaceMap[match];
    });
  };

  // Cache objects in Utils.__cache instead of $.data (see #4346)
  Utils.__cache = {};

  var id = 0;
  Utils.GetUniqueElementId = function (element) {
    // Get a unique element Id. If element has no id,
    // creates a new unique number, stores it in the id
    // attribute and returns the new id with a prefix.
    // If an id already exists, it simply returns it with a prefix.

    var select2Id = element.getAttribute('data-select2-id');

    if (select2Id != null) {
      return select2Id;
    }

    // If element has id, use it.
    if (element.id) {
      select2Id = 'select2-data-' + element.id;
    } else {
      select2Id = 'select2-data-' + (++id).toString() +
        '-' + Utils.generateChars(4);
    }

    element.setAttribute('data-select2-id', select2Id);

    return select2Id;
  };

  Utils.StoreData = function (element, name, value) {
    // Stores an item in the cache for a specified element.
    // name is the cache key.
    var id = Utils.GetUniqueElementId(element);
    if (!Utils.__cache[id]) {
      Utils.__cache[id] = {};
    }

    Utils.__cache[id][name] = value;
  };

  Utils.GetData = function (element, name) {
    // Retrieves a value from the cache by its key (name)
    // name is optional. If no name specified, return
    // all cache items for the specified element.
    // and for a specified element.
    var id = Utils.GetUniqueElementId(element);
    if (name) {
      // Convert the attribute name format (e.g. 'foo-bar') to the dataset
      // property key format (e.g. 'fooBar') as required by the HTML spec.
      var datasetKey = name.replace(/-([a-z])/g, function (_, letter) {
        return letter.toUpperCase();
      });
      if (Utils.__cache[id]) {
        if (Utils.__cache[id][name] != null) {
          return Utils.__cache[id][name];
        }
        return element.dataset[datasetKey]; // Fallback to HTML5 data attribs.
      }
      return element.dataset[datasetKey]; // Fallback to HTML5 data attribs.
    } else {
      return Utils.__cache[id];
    }
  };

  Utils.RemoveData = function (element) {
    // Removes all cached items for a specified element.
    var id = Utils.GetUniqueElementId(element);
    if (Utils.__cache[id] != null) {
      delete Utils.__cache[id];
    }

    element.removeAttribute('data-select2-id');
  };

  Utils.copyNonInternalCssClasses = function (dest, src) {
    var classes;

    var destinationClasses = dest.getAttribute('class').trim().split(/\\s+/);

    destinationClasses = destinationClasses.filter(function (clazz) {
      // Save all Select2 classes
      return clazz.indexOf('select2-') === 0;
    });

    var sourceClasses = src.getAttribute('class').trim().split(/\\s+/);

    sourceClasses = sourceClasses.filter(function (clazz) {
      // Only copy non-Select2 classes
      return clazz.indexOf('select2-') !== 0;
    });

    var replacements = destinationClasses.concat(sourceClasses);

    dest.setAttribute('class', replacements.join(' '));
  };

  return Utils;
});

S2.define('select2/results',[
  'jquery',
  './utils'
], function ($, Utils) {
  function Results ($element, options, dataAdapter) {
    this.$element = $element;
    this.data = dataAdapter;
    this.options = options;

    Results.__super__.constructor.call(this);
  }

  Utils.Extend(Results, Utils.Observable);

  Results.prototype.render = function () {
    var $results = $(
      '<ul class="select2-results__options" role="listbox"></ul>'
    );

    if (this.options.get('multiple')) {
      $results[0].setAttribute('aria-multiselectable', 'true');
    }

    this.$results = $results;

    return $results;
  };

  Results.prototype.clear = function () {
    this.$results.empty();
  };

  Results.prototype.displayMessage = function (params) {
    var escapeMarkup = this.options.get('escapeMarkup');

    this.clear();
    this.hideLoading();

    var $message = $(
      '<li role="alert" aria-live="assertive"' +
      ' class="select2-results__option"></li>'
    );

    var message = this.options.get('translations').get(params.message);

    $message.append(
      escapeMarkup(
        message(params.args)
      )
    );

    $message[0].className += ' select2-results__message';

    this.$results.append($message);
  };

  Results.prototype.hideMessages = function () {
    this.$results.find('.select2-results__message').remove();
  };

  Results.prototype.append = function (data) {
    this.hideLoading();

    var $options = [];

    if (data.results == null || data.results.length === 0) {
      if (this.$results.children().length === 0) {
        this.trigger('results:message', {
          message: 'noResults'
        });
      }

      return;
    }

    data.results = this.sort(data.results);

    for (var d = 0; d < data.results.length; d++) {
      var item = data.results[d];

      var $option = this.option(item);

      $options.push($option);
    }

    this.$results.append($options);
  };

  Results.prototype.position = function ($results, $dropdown) {
    var $resultsContainer = $dropdown.find('.select2-results');
    $resultsContainer.append($results);
  };

  Results.prototype.sort = function (data) {
    var sorter = this.options.get('sorter');

    return sorter(data);
  };

  Results.prototype.highlightFirstItem = function () {
    var $options = this.$results
      .find('.select2-results__option--selectable');

    var $selected = $options.filter('.select2-results__option--selected');

    // Check if there are any selected options
    if ($selected.length > 0) {
      // If there are selected options, highlight the first
      $selected.first().trigger('mouseenter');
    } else {
      // If there are no selected options, highlight the first option
      // in the dropdown
      $options.first().trigger('mouseenter');
    }

    this.ensureHighlightVisible();
  };

  Results.prototype.setClasses = function () {
    var self = this;

    this.data.current(function (selected) {
      var selectedIds = selected.map(function (s) {
        return s.id.toString();
      });

      var $options = self.$results
        .find('.select2-results__option--selectable');

      $options.each(function () {
        var $option = $(this);

        var item = Utils.GetData(this, 'data');

        // id needs to be converted to a string when comparing
        var id = '' + item.id;

        if ((item.element != null && item.element.selected) ||
            (item.element == null && selectedIds.indexOf(id) > -1)) {
          this.classList.add('select2-results__option--selected');
          $option[0].setAttribute('aria-selected', 'true');
        } else {
          this.classList.remove('select2-results__option--selected');
          $option[0].setAttribute('aria-selected', 'false');
        }
      });

    });
  };

  Results.prototype.showLoading = function (params) {
    this.hideLoading();

    var loadingMore = this.options.get('translations').get('searching');

    var loading = {
      disabled: true,
      loading: true,
      text: loadingMore(params)
    };
    var $loading = this.option(loading);
    $loading.className += ' loading-results';

    this.$results.prepend($loading);
  };

  Results.prototype.hideLoading = function () {
    this.$results.find('.loading-results').remove();
  };

  Results.prototype.option = function (data) {
    var option = document.createElement('li');
    option.classList.add('select2-results__option');
    option.classList.add('select2-results__option--selectable');

    var attrs = {
      'role': 'option'
    };

    var matches = window.Element.prototype.matches ||
      window.Element.prototype.msMatchesSelector ||
      window.Element.prototype.webkitMatchesSelector;

    if ((data.element != null && matches.call(data.element, ':disabled')) ||
        (data.element == null && data.disabled)) {
      attrs['aria-disabled'] = 'true';

      option.classList.remove('select2-results__option--selectable');
      option.classList.add('select2-results__option--disabled');
    }

    if (data.id == null) {
      option.classList.remove('select2-results__option--selectable');
    }

    if (data._resultId != null) {
      option.id = data._resultId;
    }

    if (data.title) {
      option.title = data.title;
    }

    if (data.children) {
      attrs.role = 'group';
      attrs['aria-label'] = data.text;

      option.classList.remove('select2-results__option--selectable');
      option.classList.add('select2-results__option--group');
    }

    for (var attr in attrs) {
      var val = attrs[attr];

      option.setAttribute(attr, val);
    }

    if (data.children) {
      var $option = $(option);

      var label = document.createElement('strong');
      label.className = 'select2-results__group';

      this.template(data, label);

      var $children = [];

      for (var c = 0; c < data.children.length; c++) {
        var child = data.children[c];

        var $child = this.option(child);

        $children.push($child);
      }

      var $childrenContainer = $('<ul></ul>', {
        'class': 'select2-results__options select2-results__options--nested',
        'role': 'none'
      });

      $childrenContainer.append($children);

      $option.append(label);
      $option.append($childrenContainer);
    } else {
      this.template(data, option);
    }

    Utils.StoreData(option, 'data', data);

    return option;
  };

  Results.prototype.bind = function (container, $container) {
    var self = this;

    var id = container.id + '-results';

    this.$results[0].setAttribute('id', id);

    container.on('results:all', function (params) {
      self.clear();
      self.append(params.data);

      if (container.isOpen()) {
        self.setClasses();
        self.highlightFirstItem();
      }
    });

    container.on('results:append', function (params) {
      self.append(params.data);

      if (container.isOpen()) {
        self.setClasses();
      }
    });

    container.on('query', function (params) {
      self.hideMessages();
      self.showLoading(params);
    });

    container.on('select', function () {
      if (!container.isOpen()) {
        return;
      }

      self.setClasses();

      if (self.options.get('scrollAfterSelect')) {
        self.highlightFirstItem();
      }
    });

    container.on('unselect', function () {
      if (!container.isOpen()) {
        return;
      }

      self.setClasses();

      if (self.options.get('scrollAfterSelect')) {
        self.highlightFirstItem();
      }
    });

    container.on('open', function () {
      // When the dropdown is open, aria-expended="true"
      self.$results[0].setAttribute('aria-expanded', 'true');
      self.$results[0].setAttribute('aria-hidden', 'false');

      self.setClasses();
      self.ensureHighlightVisible();
    });

    container.on('close', function () {
      // When the dropdown is closed, aria-expended="false"
      self.$results[0].setAttribute('aria-expanded', 'false');
      self.$results[0].setAttribute('aria-hidden', 'true');
      self.$results[0].removeAttribute('aria-activedescendant');
    });

    container.on('results:toggle', function () {
      var $highlighted = self.getHighlightedResults();

      if ($highlighted.length === 0) {
        return;
      }

      $highlighted.trigger('mouseup');
    });

    container.on('results:select', function () {
      var $highlighted = self.getHighlightedResults();

      if ($highlighted.length === 0) {
        return;
      }

      var data = Utils.GetData($highlighted[0], 'data');

      if ($highlighted.hasClass('select2-results__option--selected')) {
        self.trigger('close', {});
      } else {
        self.trigger('select', {
          data: data
        });
      }
    });

    container.on('results:previous', function () {
      var $highlighted = self.getHighlightedResults();

      var $options = self.$results.find('.select2-results__option--selectable');

      var currentIndex = $options.index($highlighted);

      // If we are already at the top, don't move further
      // If no options, currentIndex will be -1
      if (currentIndex <= 0) {
        return;
      }

      var nextIndex = currentIndex - 1;

      // If none are highlighted, highlight the first
      if ($highlighted.length === 0) {
        nextIndex = 0;
      }

      var $next = $options.eq(nextIndex);

      $next.trigger('mouseenter');

      var currentOffset = self.$results.offset().top;
      var nextTop = $next.offset().top;
      var nextOffset = self.$results.scrollTop() + (nextTop - currentOffset);

      if (nextIndex === 0) {
        self.$results.scrollTop(0);
      } else if (nextTop - currentOffset < 0) {
        self.$results.scrollTop(nextOffset);
      }
    });

    container.on('results:next', function () {
      var $highlighted = self.getHighlightedResults();

      var $options = self.$results.find('.select2-results__option--selectable');

      var currentIndex = $options.index($highlighted);

      var nextIndex = currentIndex + 1;

      // If we are at the last option, stay there
      if (nextIndex >= $options.length) {
        return;
      }

      var $next = $options.eq(nextIndex);

      $next.trigger('mouseenter');

      var currentOffset = self.$results.offset().top +
        self.$results.outerHeight(false);
      var nextBottom = $next.offset().top + $next.outerHeight(false);
      var nextOffset = self.$results.scrollTop() + nextBottom - currentOffset;

      if (nextIndex === 0) {
        self.$results.scrollTop(0);
      } else if (nextBottom > currentOffset) {
        self.$results.scrollTop(nextOffset);
      }
    });

    container.on('results:focus', function (params) {
      params.element[0].classList.add('select2-results__option--highlighted');
      params.element[0].setAttribute('aria-selected', 'true');
    });

    container.on('results:message', function (params) {
      self.displayMessage(params);
    });

    if ($.fn.mousewheel) {
      this.$results.on('mousewheel', function (e) {
        var top = self.$results.scrollTop();

        var bottom = self.$results.get(0).scrollHeight - top + e.deltaY;

        var isAtTop = e.deltaY > 0 && top - e.deltaY <= 0;
        var isAtBottom = e.deltaY < 0 && bottom <= self.$results.height();

        if (isAtTop) {
          self.$results.scrollTop(0);

          e.preventDefault();
          e.stopPropagation();
        } else if (isAtBottom) {
          self.$results.scrollTop(
            self.$results.get(0).scrollHeight - self.$results.height()
          );

          e.preventDefault();
          e.stopPropagation();
        }
      });
    }

    this.$results.on('mouseup', '.select2-results__option--selectable',
      function (evt) {
      var $this = $(this);

      var data = Utils.GetData(this, 'data');

      if ($this.hasClass('select2-results__option--selected')) {
        if (self.options.get('multiple')) {
          self.trigger('unselect', {
            originalEvent: evt,
            data: data
          });
        } else {
          self.trigger('close', {
            originalEvent: evt,
            data: data
          });
        }

        return;
      }

      self.trigger('select', {
        originalEvent: evt,
        data: data
      });
    });

    this.$results.on('mouseenter', '.select2-results__option--selectable',
      function (evt) {
      var data = Utils.GetData(this, 'data');

      var $highlighted = self.getHighlightedResults();
      $highlighted.removeClass('select2-results__option--highlighted');
      $highlighted.each(function () {
        this.setAttribute('aria-selected', 'false');
      });

      self.trigger('results:focus', {
        data: data,
        element: $(this)
      });
    });
  };

  Results.prototype.getHighlightedResults = function () {
    var $highlighted = this.$results
    .find('.select2-results__option--highlighted');

    return $highlighted;
  };

  Results.prototype.destroy = function () {
    this.$results.remove();
  };

  Results.prototype.ensureHighlightVisible = function () {
    var $highlighted = this.getHighlightedResults();

    if ($highlighted.length === 0) {
      return;
    }

    var $options = this.$results.find('.select2-results__option--selectable');

    var currentIndex = $options.index($highlighted);

    var currentOffset = this.$results.offset().top;
    var nextTop = $highlighted.offset().top;
    var nextOffset = this.$results.scrollTop() + (nextTop - currentOffset);

    var offsetDelta = nextTop - currentOffset;
    nextOffset -= $highlighted.outerHeight(false) * 2;

    if (currentIndex <= 2) {
      this.$results.scrollTop(0);
    } else if (offsetDelta > this.$results.outerHeight() || offsetDelta < 0) {
      this.$results.scrollTop(nextOffset);
    }
  };

  Results.prototype.template = function (result, container) {
    var template = this.options.get('templateResult');
    var escapeMarkup = this.options.get('escapeMarkup');

    var content = template(result, container);

    if (content == null) {
      container.style.display = 'none';
    } else if (typeof content === 'string') {
      container.innerHTML = escapeMarkup(content);
    } else {
      $(container).append(content);
    }
  };

  return Results;
});

S2.define('select2/keys',[

], function () {
  var KEYS = {
    BACKSPACE: 8,
    TAB: 9,
    ENTER: 13,
    SHIFT: 16,
    CTRL: 17,
    ALT: 18,
    ESC: 27,
    SPACE: 32,
    PAGE_UP: 33,
    PAGE_DOWN: 34,
    END: 35,
    HOME: 36,
    LEFT: 37,
    UP: 38,
    RIGHT: 39,
    DOWN: 40,
    DELETE: 46
  };

  return KEYS;
});

S2.define('select2/selection/base',[
  'jquery',
  '../utils',
  '../keys'
], function ($, Utils, KEYS) {
  function BaseSelection ($element, options) {
    this.$element = $element;
    this.options = options;

    BaseSelection.__super__.constructor.call(this);
  }

  Utils.Extend(BaseSelection, Utils.Observable);

  BaseSelection.prototype.render = function () {
    var $selection = $(
      '<span class="select2-selection" role="combobox" ' +
      ' aria-haspopup="true" aria-expanded="false">' +
      '</span>'
    );

    this._tabindex = 0;

    if (Utils.GetData(this.$element[0], 'old-tabindex') != null) {
      this._tabindex = Utils.GetData(this.$element[0], 'old-tabindex');
    } else if (this.$element[0].getAttribute('tabindex') != null) {
      this._tabindex = this.$element[0].getAttribute('tabindex');
    }

    if(this.$element[0].getAttribute('title')) {
      $selection[0]
        .setAttribute('title', this.$element[0].getAttribute('title'));
    }
    $selection[0].setAttribute('tabindex', this._tabindex);
    $selection[0].setAttribute('aria-disabled', 'false');

    this.$selection = $selection;

    return $selection;
  };

  BaseSelection.prototype.bind = function (container, $container) {
    var self = this;

    var resultsId = container.id + '-results';

    this.container = container;

    this.$selection.on('focus', function (evt) {
      self.trigger('focus', evt);
    });

    this.$selection.on('blur', function (evt) {
      self._handleBlur(evt);
    });

    this.$selection.on('keydown', function (evt) {
      self.trigger('keypress', evt);

      if (evt.which === KEYS.SPACE) {
        evt.preventDefault();
      }
    });

    container.on('results:focus', function (params) {
      self.$selection[0]
        .setAttribute('aria-activedescendant', params.data._resultId);
    });

    container.on('selection:update', function (params) {
      self.update(params.data);
    });

    container.on('open', function () {
      // When the dropdown is open, aria-expanded="true"
      self.$selection[0].setAttribute('aria-expanded', 'true');
      self.$selection[0].setAttribute('aria-owns', resultsId);

      self._attachCloseHandler(container);
    });

    container.on('close', function () {
      // When the dropdown is closed, aria-expanded="false"
      self.$selection[0].setAttribute('aria-expanded', 'false');
      self.$selection[0].removeAttribute('aria-activedescendant');
      self.$selection[0].removeAttribute('aria-owns');

      self.$selection.trigger('focus');

      self._detachCloseHandler(container);
    });

    container.on('enable', function () {
      self.$selection[0].setAttribute('tabindex', self._tabindex);
      self.$selection[0].setAttribute('aria-disabled', 'false');
    });

    container.on('disable', function () {
      self.$selection[0].setAttribute('tabindex', '-1');
      self.$selection[0].setAttribute('aria-disabled', 'true');
    });
  };

  BaseSelection.prototype._handleBlur = function (evt) {
    var self = this;

    // This needs to be delayed as the active element is the body when the tab
    // key is pressed, possibly along with others.
    window.setTimeout(function () {
      // Don't trigger \`blur\` if the focus is still in the selection
      if (
        (document.activeElement == self.$selection[0]) ||
        ($.contains(self.$selection[0], document.activeElement))
      ) {
        return;
      }

      self.trigger('blur', evt);
    }, 1);
  };

  BaseSelection.prototype._attachCloseHandler = function (container) {

    $(document.body).on('mousedown.select2.' + container.id, function (e) {
      var $target = $(e.target);

      var $select = $target.closest('.select2');

      var $all = $('.select2.select2-container--open');

      $all.each(function () {
        if (this == $select[0]) {
          return;
        }

        var $element = Utils.GetData(this, 'element');

        $element.select2('close');
      });
    });
  };

  BaseSelection.prototype._detachCloseHandler = function (container) {
    $(document.body).off('mousedown.select2.' + container.id);
  };

  BaseSelection.prototype.position = function ($selection, $container) {
    var $selectionContainer = $container.find('.selection');
    $selectionContainer.append($selection);
  };

  BaseSelection.prototype.destroy = function () {
    this._detachCloseHandler(this.container);
  };

  BaseSelection.prototype.update = function (data) {
    throw new Error('The \`update\` method must be defined in child classes.');
  };

  /**
   * Helper method to abstract the "enabled" (not "disabled") state of this
   * object.
   *
   * @return {true} if the instance is not disabled.
   * @return {false} if the instance is disabled.
   */
  BaseSelection.prototype.isEnabled = function () {
    return !this.isDisabled();
  };

  /**
   * Helper method to abstract the "disabled" state of this object.
   *
   * @return {true} if the disabled option is true.
   * @return {false} if the disabled option is false.
   */
  BaseSelection.prototype.isDisabled = function () {
    return this.options.get('disabled');
  };

  return BaseSelection;
});

S2.define('select2/selection/single',[
  'jquery',
  './base',
  '../utils',
  '../keys'
], function ($, BaseSelection, Utils, KEYS) {
  function SingleSelection () {
    SingleSelection.__super__.constructor.apply(this, arguments);
  }

  Utils.Extend(SingleSelection, BaseSelection);

  SingleSelection.prototype.render = function () {
    var $selection = SingleSelection.__super__.render.call(this);

    $selection[0].classList.add('select2-selection--single');

    $selection.html(
      '<span class="select2-selection__rendered"></span>' +
      '<span class="select2-selection__arrow" role="presentation">' +
        '<b role="presentation"></b>' +
      '</span>'
    );

    return $selection;
  };

  SingleSelection.prototype.bind = function (container, $container) {
    var self = this;

    SingleSelection.__super__.bind.apply(this, arguments);

    var id = container.id + '-container';

    var rendered = this.$selection.find('.select2-selection__rendered')[0];
    if(rendered != null) {
      rendered.setAttribute('id', id);
      rendered.setAttribute('role', 'textbox');
      rendered.setAttribute('aria-readonly', 'true');
    }
    this.$selection[0].setAttribute('aria-labelledby', id);
    this.$selection[0].setAttribute('aria-controls', id);

    this.$selection.on('mousedown', function (evt) {
      // Only respond to left clicks
      if (evt.which !== 1) {
        return;
      }

      self.trigger('toggle', {
        originalEvent: evt
      });
    });

    this.$selection.on('focus', function (evt) {
      // User focuses on the container
    });

    this.$selection.on('blur', function (evt) {
      // User exits the container
    });

    container.on('focus', function (evt) {
      if (!container.isOpen()) {
        self.$selection.trigger('focus');
      }
    });
  };

  SingleSelection.prototype.clear = function () {
    var $rendered = this.$selection.find('.select2-selection__rendered');
    $rendered.empty();
    $rendered[0].removeAttribute('title'); // clear tooltip on empty
  };

  SingleSelection.prototype.display = function (data, container) {
    var template = this.options.get('templateSelection');
    var escapeMarkup = this.options.get('escapeMarkup');

    return escapeMarkup(template(data, container));
  };

  SingleSelection.prototype.selectionContainer = function () {
    return $('<span></span>');
  };

  SingleSelection.prototype.update = function (data) {
    if (data.length === 0) {
      this.clear();
      return;
    }

    var selection = data[0];

    var $rendered = this.$selection.find('.select2-selection__rendered');
    var formatted = this.display(selection, $rendered);

    $rendered.empty().append(formatted);

    var title = selection.title || selection.text;

    if (title) {
      $rendered[0].setAttribute('title', title);
    } else {
      $rendered[0].removeAttribute('title');
    }
  };

  return SingleSelection;
});

S2.define('select2/selection/multiple',[
  'jquery',
  './base',
  '../utils'
], function ($, BaseSelection, Utils) {
  function MultipleSelection ($element, options) {
    MultipleSelection.__super__.constructor.apply(this, arguments);
  }

  Utils.Extend(MultipleSelection, BaseSelection);

  MultipleSelection.prototype.render = function () {
    var $selection = MultipleSelection.__super__.render.call(this);

    $selection[0].classList.add('select2-selection--multiple');

    $selection.html(
      '<ul class="select2-selection__rendered"></ul>'
    );

    return $selection;
  };

  MultipleSelection.prototype.bind = function (container, $container) {
    var self = this;

    MultipleSelection.__super__.bind.apply(this, arguments);

    var id = container.id + '-container';

    var rendered = this.$selection.find('.select2-selection__rendered')[0];
    if(rendered != null) {
      rendered.setAttribute('id', id);
    }

    this.$selection.on('click', function (evt) {
      self.trigger('toggle', {
        originalEvent: evt
      });
    });

    this.$selection.on(
      'click',
      '.select2-selection__choice__remove',
      function (evt) {
        // Ignore the event if it is disabled
        if (self.isDisabled()) {
          return;
        }

        var $remove = $(this);
        var $selection = $remove.parent();

        var data = Utils.GetData($selection[0], 'data');

        self.trigger('unselect', {
          originalEvent: evt,
          data: data
        });
      }
    );

    this.$selection.on(
      'keydown',
      '.select2-selection__choice__remove',
      function (evt) {
        // Ignore the event if it is disabled
        if (self.isDisabled()) {
          return;
        }

        evt.stopPropagation();
      }
    );
  };

  MultipleSelection.prototype.clear = function () {
    var $rendered = this.$selection.find('.select2-selection__rendered');
    $rendered.empty();
    $rendered[0].removeAttribute('title');
  };

  MultipleSelection.prototype.display = function (data, container) {
    var template = this.options.get('templateSelection');
    var escapeMarkup = this.options.get('escapeMarkup');

    return escapeMarkup(template(data, container));
  };

  MultipleSelection.prototype.selectionContainer = function () {
    var $container = $(
      '<li class="select2-selection__choice">' +
        '<button type="button" class="select2-selection__choice__remove" ' +
        'tabindex="-1">' +
          '<span aria-hidden="true">&times;</span>' +
        '</button>' +
        '<span class="select2-selection__choice__display"></span>' +
      '</li>'
    );

    return $container;
  };

  MultipleSelection.prototype.update = function (data) {
    this.clear();

    if (data.length === 0) {
      return;
    }

    var $selections = [];

    var selectionIdPrefix = this.$selection
      .find('.select2-selection__rendered')[0]
      .getAttribute('id') + '-choice-';

    for (var d = 0; d < data.length; d++) {
      var selection = data[d];

      var $selection = this.selectionContainer();
      var formatted = this.display(selection, $selection);

      var selectionId = selectionIdPrefix + Utils.generateChars(4) + '-';

      if (selection.id) {
        selectionId += selection.id;
      } else {
        selectionId += Utils.generateChars(4);
      }

      $selection.find('.select2-selection__choice__display')
        .append(formatted)[0]
        .setAttribute('id', selectionId);

      var title = selection.title || selection.text;

      if (title) {
        $selection[0].setAttribute('title', title);
      }

      var removeItem = this.options.get('translations').get('removeItem');

      var remove = $selection.find('.select2-selection__choice__remove')[0];

      remove.setAttribute('title', removeItem());
      remove.setAttribute('aria-label', removeItem());
      remove.setAttribute('aria-describedby', selectionId);

      Utils.StoreData($selection[0], 'data', selection);

      $selections.push($selection);
    }

    var $rendered = this.$selection.find('.select2-selection__rendered');

    $rendered.append($selections);
  };

  return MultipleSelection;
});

S2.define('select2/selection/placeholder',[

], function () {
  function Placeholder (decorated, $element, options) {
    this.placeholder = this.normalizePlaceholder(options.get('placeholder'));

    decorated.call(this, $element, options);
  }

  Placeholder.prototype.normalizePlaceholder = function (_, placeholder) {
    if (typeof placeholder !== 'object') {
      placeholder = {
        id: '',
        text: placeholder
      };
    }

    return placeholder;
  };

  Placeholder.prototype.createPlaceholder = function (decorated, placeholder) {
    var $placeholder = this.selectionContainer();

    $placeholder.html(this.display(placeholder));
    $placeholder[0].classList.add('select2-selection__placeholder');
    $placeholder[0].classList.remove('select2-selection__choice');

    var placeholderTitle = placeholder.title ||
      placeholder.text ||
      $placeholder.text();

    this.$selection.find('.select2-selection__rendered')[0].setAttribute(
      'title',
      placeholderTitle
    );

    return $placeholder;
  };

  Placeholder.prototype.update = function (decorated, data) {
    var singlePlaceholder = (
      data.length == 1 && data[0].id != this.placeholder.id
    );
    var multipleSelections = data.length > 1;

    if (multipleSelections || singlePlaceholder) {
      return decorated.call(this, data);
    }

    this.clear();

    var $placeholder = this.createPlaceholder(this.placeholder);

    this.$selection.find('.select2-selection__rendered').append($placeholder);
  };

  return Placeholder;
});

S2.define('select2/selection/allowClear',[
  'jquery',
  '../keys',
  '../utils'
], function ($, KEYS, Utils) {
  function AllowClear () { }

  AllowClear.prototype.bind = function (decorated, container, $container) {
    var self = this;

    decorated.call(this, container, $container);

    if (this.placeholder == null) {
      if (this.options.get('debug') && window.console && console.error) {
        console.error(
          'Select2: The \`allowClear\` option should be used in combination ' +
          'with the \`placeholder\` option.'
        );
      }
    }

    this.$selection.on('mousedown', '.select2-selection__clear',
      function (evt) {
        self._handleClear(evt);
    });

    container.on('keypress', function (evt) {
      self._handleKeyboardClear(evt, container);
    });
  };

  AllowClear.prototype._handleClear = function (_, evt) {
    // Ignore the event if it is disabled
    if (this.isDisabled()) {
      return;
    }

    var $clear = this.$selection.find('.select2-selection__clear');

    // Ignore the event if nothing has been selected
    if ($clear.length === 0) {
      return;
    }

    evt.stopPropagation();

    var data = Utils.GetData($clear[0], 'data');

    var previousVal = this.$element.val();
    this.$element.val(this.placeholder.id);

    var unselectData = {
      data: data
    };
    this.trigger('clear', unselectData);
    if (unselectData.prevented) {
      this.$element.val(previousVal);
      return;
    }

    for (var d = 0; d < data.length; d++) {
      unselectData = {
        data: data[d]
      };

      // Trigger the \`unselect\` event, so people can prevent it from being
      // cleared.
      this.trigger('unselect', unselectData);

      // If the event was prevented, don't clear it out.
      if (unselectData.prevented) {
        this.$element.val(previousVal);
        return;
      }
    }

    this.$element.trigger('input').trigger('change');

    this.trigger('toggle', {});
  };

  AllowClear.prototype._handleKeyboardClear = function (_, evt, container) {
    if (container.isOpen()) {
      return;
    }

    if (evt.which == KEYS.DELETE || evt.which == KEYS.BACKSPACE) {
      this._handleClear(evt);
    }
  };

  AllowClear.prototype.update = function (decorated, data) {
    decorated.call(this, data);

    this.$selection.find('.select2-selection__clear').remove();
    this.$selection[0].classList.remove('select2-selection--clearable');

    if (this.$selection.find('.select2-selection__placeholder').length > 0 ||
        data.length === 0) {
      return;
    }

    var rendered = this.$selection.find('.select2-selection__rendered')[0];
    var selectionId = null;
    if(rendered != null) {
      selectionId = rendered.getAttribute('id');
    }

    var removeAll = this.options.get('translations').get('removeAllItems');

    var $remove = $(
      '<button type="button" class="select2-selection__clear" tabindex="-1">' +
        '<span aria-hidden="true">&times;</span>' +
      '</button>'
    );
    $remove[0].setAttribute('title', removeAll());
    $remove[0].setAttribute('aria-label', removeAll());
    $remove[0].setAttribute('aria-describedby', selectionId);
    Utils.StoreData($remove[0], 'data', data);

    this.$selection.prepend($remove);
    this.$selection[0].classList.add('select2-selection--clearable');
  };

  return AllowClear;
});

S2.define('select2/selection/search',[
  'jquery',
  '../utils',
  '../keys'
], function ($, Utils, KEYS) {
  function Search (decorated, $element, options) {
    decorated.call(this, $element, options);
  }

  Search.prototype.render = function (decorated) {
    var searchLabel = this.options.get('translations').get('search');
    var $search = $(
      '<span class="select2-search select2-search--inline">' +
        '<textarea class="select2-search__field"'+
        ' type="search" tabindex="-1"' +
        ' autocorrect="off" autocapitalize="none"' +
        ' spellcheck="false" role="searchbox" aria-autocomplete="list" >' +
        '</textarea>' +
      '</span>'
    );

    this.$searchContainer = $search;
    this.$search = $search.find('textarea');

    this.$search[0].autocomplete = this.options.get('autocomplete');
    this.$search[0].setAttribute('aria-label', searchLabel());

    var $rendered = decorated.call(this);

    this._transferTabIndex();
    $rendered.append(this.$searchContainer);

    return $rendered;
  };

  Search.prototype.bind = function (decorated, container, $container) {
    var self = this;

    var resultsId = container.id + '-results';
    var selectionId = container.id + '-container';

    decorated.call(this, container, $container);

    self.$search[0].setAttribute('aria-describedby', selectionId);

    container.on('open', function () {
      self.$search[0].setAttribute('aria-controls', resultsId);
      self.$search.trigger('focus');
    });

    container.on('close', function () {
      self.$search.val('');
      self.resizeSearch();
      self.$search[0].removeAttribute('aria-controls');
      self.$search[0].removeAttribute('aria-activedescendant');
      self.$search.trigger('focus');
    });

    container.on('enable', function () {
      self.$search[0].disabled = false;

      self._transferTabIndex();
    });

    container.on('disable', function () {
      self.$search[0].disabled = true;
    });

    container.on('focus', function (evt) {
      self.$search.trigger('focus');
    });

    container.on('results:focus', function (params) {
      if (params.data._resultId) {
        self.$search[0]
          .setAttribute('aria-activedescendant', params.data._resultId);
      } else {
        self.$search[0].removeAttribute('aria-activedescendant');
      }
    });

    this.$selection.on('focusin', '.select2-search--inline', function (evt) {
      self.trigger('focus', evt);
    });

    this.$selection.on('focusout', '.select2-search--inline', function (evt) {
      self._handleBlur(evt);
    });

    this.$selection.on('keydown', '.select2-search--inline', function (evt) {
      evt.stopPropagation();

      self.trigger('keypress', evt);

      self._keyUpPrevented = evt.isDefaultPrevented();

      var key = evt.which;

      if (key === KEYS.BACKSPACE && self.$search.val() === '') {
        var $previousChoice = self.$selection
          .find('.select2-selection__choice').last();

        if ($previousChoice.length > 0) {
          var item = Utils.GetData($previousChoice[0], 'data');

          self.searchRemoveChoice(item);

          evt.preventDefault();
        }
      }
    });

    this.$selection.on('click', '.select2-search--inline', function (evt) {
      if (self.$search.val()) {
        evt.stopPropagation();
      }
    });

    // Try to detect the IE version should the \`documentMode\` property that
    // is stored on the document. This is only implemented in IE and is
    // slightly cleaner than doing a user agent check.
    // This property is not available in Edge, but Edge also doesn't have
    // this bug.
    var msie = document.documentMode;
    var disableInputEvents = msie && msie <= 11;

    // Workaround for browsers which do not support the \`input\` event
    // This will prevent double-triggering of events for browsers which support
    // both the \`keyup\` and \`input\` events.
    this.$selection.on(
      'input.searchcheck',
      '.select2-search--inline',
      function (evt) {
        // IE will trigger the \`input\` event when a placeholder is used on a
        // search box. To get around this issue, we are forced to ignore all
        // \`input\` events in IE and keep using \`keyup\`.
        if (disableInputEvents) {
          self.$selection.off('input.search input.searchcheck');
          return;
        }

        // Unbind the duplicated \`keyup\` event
        self.$selection.off('keyup.search');
      }
    );

    this.$selection.on(
      'keyup.search input.search',
      '.select2-search--inline',
      function (evt) {
        // IE will trigger the \`input\` event when a placeholder is used on a
        // search box. To get around this issue, we are forced to ignore all
        // \`input\` events in IE and keep using \`keyup\`.
        if (disableInputEvents && evt.type === 'input') {
          self.$selection.off('input.search input.searchcheck');
          return;
        }

        var key = evt.which;

        // We can freely ignore events from modifier keys
        if (key == KEYS.SHIFT || key == KEYS.CTRL || key == KEYS.ALT) {
          return;
        }

        // Tabbing will be handled during the \`keydown\` phase
        if (key == KEYS.TAB) {
          return;
        }

        self.handleSearch(evt);
      }
    );
  };

  /**
   * This method will transfer the tabindex attribute from the rendered
   * selection to the search box. This allows for the search box to be used as
   * the primary focus instead of the selection container.
   *
   * @private
   */
  Search.prototype._transferTabIndex = function (decorated) {
    this.$search[0]
      .setAttribute('tabindex', this.$selection[0].getAttribute('tabindex'));
    this.$selection[0].setAttribute('tabindex', '-1');
  };

  Search.prototype.createPlaceholder = function (decorated, placeholder) {
    this.$search[0].setAttribute('placeholder', placeholder.text);
  };

  Search.prototype.update = function (decorated, data) {
    var searchHadFocus = this.$search[0] == document.activeElement;

    this.$search[0].setAttribute('placeholder', '');

    decorated.call(this, data);

    this.resizeSearch();
    if (searchHadFocus) {
      this.$search.trigger('focus');
    }
  };

  Search.prototype.handleSearch = function () {
    this.resizeSearch();

    if (!this._keyUpPrevented) {
      var input = this.$search.val();

      this.trigger('query', {
        term: input
      });
    }

    this._keyUpPrevented = false;
  };

  Search.prototype.searchRemoveChoice = function (decorated, item) {
    this.trigger('unselect', {
      data: item
    });

    this.$search.val(item.text);
    this.handleSearch();
  };

  Search.prototype.resizeSearch = function () {
    this.$search.css('width', '25px');

    var width = '100%';

    if (this.$search[0].getAttribute('placeholder') === '') {
      var minimumWidth = this.$search.val().length + 1;

      width = (minimumWidth * 0.75) + 'em';
    }

    this.$search.css('width', width);
  };

  return Search;
});

S2.define('select2/selection/selectionCss',[
  '../utils'
], function (Utils) {
  function SelectionCSS () { }

  SelectionCSS.prototype.render = function (decorated) {
    var $selection = decorated.call(this);

    var selectionCssClass = this.options.get('selectionCssClass') || '';

    if (selectionCssClass.indexOf(':all:') !== -1) {
      selectionCssClass = selectionCssClass.replace(':all:', '');

      Utils.copyNonInternalCssClasses($selection[0], this.$element[0]);
    }

    selectionCssClass.trim().split(' ').forEach(function(cssClass) {
      if(cssClass.length > 0) {
        $selection[0].classList.add(cssClass);
      }
    });

    return $selection;
  };

  return SelectionCSS;
});

S2.define('select2/selection/eventRelay',[
  'jquery'
], function ($) {
  function EventRelay () { }

  EventRelay.prototype.bind = function (decorated, container, $container) {
    var self = this;
    var relayEvents = [
      'open', 'opening',
      'close', 'closing',
      'select', 'selecting',
      'unselect', 'unselecting',
      'clear', 'clearing'
    ];

    var preventableEvents = [
      'opening', 'closing', 'selecting', 'unselecting', 'clearing'
    ];

    decorated.call(this, container, $container);

    container.on('*', function (name, params) {
      // Ignore events that should not be relayed
      if (relayEvents.indexOf(name) === -1) {
        return;
      }

      // The parameters should always be an object
      params = params || {};

      // Generate the jQuery event for the Select2 event
      var evt = $.Event('select2:' + name, {
        params: params
      });

      self.$element.trigger(evt);

      // Only handle preventable events if it was one
      if (preventableEvents.indexOf(name) === -1) {
        return;
      }

      params.prevented = evt.isDefaultPrevented();
    });
  };

  return EventRelay;
});

S2.define('select2/translation',[
  'require'
], function (require) {
  function Translation (dict) {
    this.dict = dict || {};
  }

  Translation.prototype.all = function () {
    return this.dict;
  };

  Translation.prototype.get = function (key) {
    return this.dict[key];
  };

  Translation.prototype.extend = function (translation) {
    this.dict = Object.assign({}, translation.all(), this.dict);
  };

  // Static functions

  Translation._cache = {};

  Translation.loadPath = function (path) {
    if (!(path in Translation._cache)) {
      var translations = require(path);

      Translation._cache[path] = translations;
    }

    return new Translation(Translation._cache[path]);
  };

  return Translation;
});

S2.define('select2/diacritics',[

], function () {
  var diacritics = {
    '\\u24B6': 'A',
    '\\uFF21': 'A',
    '\\u00C0': 'A',
    '\\u00C1': 'A',
    '\\u00C2': 'A',
    '\\u1EA6': 'A',
    '\\u1EA4': 'A',
    '\\u1EAA': 'A',
    '\\u1EA8': 'A',
    '\\u00C3': 'A',
    '\\u0100': 'A',
    '\\u0102': 'A',
    '\\u1EB0': 'A',
    '\\u1EAE': 'A',
    '\\u1EB4': 'A',
    '\\u1EB2': 'A',
    '\\u0226': 'A',
    '\\u01E0': 'A',
    '\\u00C4': 'A',
    '\\u01DE': 'A',
    '\\u1EA2': 'A',
    '\\u00C5': 'A',
    '\\u01FA': 'A',
    '\\u01CD': 'A',
    '\\u0200': 'A',
    '\\u0202': 'A',
    '\\u1EA0': 'A',
    '\\u1EAC': 'A',
    '\\u1EB6': 'A',
    '\\u1E00': 'A',
    '\\u0104': 'A',
    '\\u023A': 'A',
    '\\u2C6F': 'A',
    '\\uA732': 'AA',
    '\\u00C6': 'AE',
    '\\u01FC': 'AE',
    '\\u01E2': 'AE',
    '\\uA734': 'AO',
    '\\uA736': 'AU',
    '\\uA738': 'AV',
    '\\uA73A': 'AV',
    '\\uA73C': 'AY',
    '\\u24B7': 'B',
    '\\uFF22': 'B',
    '\\u1E02': 'B',
    '\\u1E04': 'B',
    '\\u1E06': 'B',
    '\\u0243': 'B',
    '\\u0182': 'B',
    '\\u0181': 'B',
    '\\u24B8': 'C',
    '\\uFF23': 'C',
    '\\u0106': 'C',
    '\\u0108': 'C',
    '\\u010A': 'C',
    '\\u010C': 'C',
    '\\u00C7': 'C',
    '\\u1E08': 'C',
    '\\u0187': 'C',
    '\\u023B': 'C',
    '\\uA73E': 'C',
    '\\u24B9': 'D',
    '\\uFF24': 'D',
    '\\u1E0A': 'D',
    '\\u010E': 'D',
    '\\u1E0C': 'D',
    '\\u1E10': 'D',
    '\\u1E12': 'D',
    '\\u1E0E': 'D',
    '\\u0110': 'D',
    '\\u018B': 'D',
    '\\u018A': 'D',
    '\\u0189': 'D',
    '\\uA779': 'D',
    '\\u01F1': 'DZ',
    '\\u01C4': 'DZ',
    '\\u01F2': 'Dz',
    '\\u01C5': 'Dz',
    '\\u24BA': 'E',
    '\\uFF25': 'E',
    '\\u00C8': 'E',
    '\\u00C9': 'E',
    '\\u00CA': 'E',
    '\\u1EC0': 'E',
    '\\u1EBE': 'E',
    '\\u1EC4': 'E',
    '\\u1EC2': 'E',
    '\\u1EBC': 'E',
    '\\u0112': 'E',
    '\\u1E14': 'E',
    '\\u1E16': 'E',
    '\\u0114': 'E',
    '\\u0116': 'E',
    '\\u00CB': 'E',
    '\\u1EBA': 'E',
    '\\u011A': 'E',
    '\\u0204': 'E',
    '\\u0206': 'E',
    '\\u1EB8': 'E',
    '\\u1EC6': 'E',
    '\\u0228': 'E',
    '\\u1E1C': 'E',
    '\\u0118': 'E',
    '\\u1E18': 'E',
    '\\u1E1A': 'E',
    '\\u0190': 'E',
    '\\u018E': 'E',
    '\\u24BB': 'F',
    '\\uFF26': 'F',
    '\\u1E1E': 'F',
    '\\u0191': 'F',
    '\\uA77B': 'F',
    '\\u24BC': 'G',
    '\\uFF27': 'G',
    '\\u01F4': 'G',
    '\\u011C': 'G',
    '\\u1E20': 'G',
    '\\u011E': 'G',
    '\\u0120': 'G',
    '\\u01E6': 'G',
    '\\u0122': 'G',
    '\\u01E4': 'G',
    '\\u0193': 'G',
    '\\uA7A0': 'G',
    '\\uA77D': 'G',
    '\\uA77E': 'G',
    '\\u24BD': 'H',
    '\\uFF28': 'H',
    '\\u0124': 'H',
    '\\u1E22': 'H',
    '\\u1E26': 'H',
    '\\u021E': 'H',
    '\\u1E24': 'H',
    '\\u1E28': 'H',
    '\\u1E2A': 'H',
    '\\u0126': 'H',
    '\\u2C67': 'H',
    '\\u2C75': 'H',
    '\\uA78D': 'H',
    '\\u24BE': 'I',
    '\\uFF29': 'I',
    '\\u00CC': 'I',
    '\\u00CD': 'I',
    '\\u00CE': 'I',
    '\\u0128': 'I',
    '\\u012A': 'I',
    '\\u012C': 'I',
    '\\u0130': 'I',
    '\\u00CF': 'I',
    '\\u1E2E': 'I',
    '\\u1EC8': 'I',
    '\\u01CF': 'I',
    '\\u0208': 'I',
    '\\u020A': 'I',
    '\\u1ECA': 'I',
    '\\u012E': 'I',
    '\\u1E2C': 'I',
    '\\u0197': 'I',
    '\\u24BF': 'J',
    '\\uFF2A': 'J',
    '\\u0134': 'J',
    '\\u0248': 'J',
    '\\u24C0': 'K',
    '\\uFF2B': 'K',
    '\\u1E30': 'K',
    '\\u01E8': 'K',
    '\\u1E32': 'K',
    '\\u0136': 'K',
    '\\u1E34': 'K',
    '\\u0198': 'K',
    '\\u2C69': 'K',
    '\\uA740': 'K',
    '\\uA742': 'K',
    '\\uA744': 'K',
    '\\uA7A2': 'K',
    '\\u24C1': 'L',
    '\\uFF2C': 'L',
    '\\u013F': 'L',
    '\\u0139': 'L',
    '\\u013D': 'L',
    '\\u1E36': 'L',
    '\\u1E38': 'L',
    '\\u013B': 'L',
    '\\u1E3C': 'L',
    '\\u1E3A': 'L',
    '\\u0141': 'L',
    '\\u023D': 'L',
    '\\u2C62': 'L',
    '\\u2C60': 'L',
    '\\uA748': 'L',
    '\\uA746': 'L',
    '\\uA780': 'L',
    '\\u01C7': 'LJ',
    '\\u01C8': 'Lj',
    '\\u24C2': 'M',
    '\\uFF2D': 'M',
    '\\u1E3E': 'M',
    '\\u1E40': 'M',
    '\\u1E42': 'M',
    '\\u2C6E': 'M',
    '\\u019C': 'M',
    '\\u24C3': 'N',
    '\\uFF2E': 'N',
    '\\u01F8': 'N',
    '\\u0143': 'N',
    '\\u00D1': 'N',
    '\\u1E44': 'N',
    '\\u0147': 'N',
    '\\u1E46': 'N',
    '\\u0145': 'N',
    '\\u1E4A': 'N',
    '\\u1E48': 'N',
    '\\u0220': 'N',
    '\\u019D': 'N',
    '\\uA790': 'N',
    '\\uA7A4': 'N',
    '\\u01CA': 'NJ',
    '\\u01CB': 'Nj',
    '\\u24C4': 'O',
    '\\uFF2F': 'O',
    '\\u00D2': 'O',
    '\\u00D3': 'O',
    '\\u00D4': 'O',
    '\\u1ED2': 'O',
    '\\u1ED0': 'O',
    '\\u1ED6': 'O',
    '\\u1ED4': 'O',
    '\\u00D5': 'O',
    '\\u1E4C': 'O',
    '\\u022C': 'O',
    '\\u1E4E': 'O',
    '\\u014C': 'O',
    '\\u1E50': 'O',
    '\\u1E52': 'O',
    '\\u014E': 'O',
    '\\u022E': 'O',
    '\\u0230': 'O',
    '\\u00D6': 'O',
    '\\u022A': 'O',
    '\\u1ECE': 'O',
    '\\u0150': 'O',
    '\\u01D1': 'O',
    '\\u020C': 'O',
    '\\u020E': 'O',
    '\\u01A0': 'O',
    '\\u1EDC': 'O',
    '\\u1EDA': 'O',
    '\\u1EE0': 'O',
    '\\u1EDE': 'O',
    '\\u1EE2': 'O',
    '\\u1ECC': 'O',
    '\\u1ED8': 'O',
    '\\u01EA': 'O',
    '\\u01EC': 'O',
    '\\u00D8': 'O',
    '\\u01FE': 'O',
    '\\u0186': 'O',
    '\\u019F': 'O',
    '\\uA74A': 'O',
    '\\uA74C': 'O',
    '\\u0152': 'OE',
    '\\u01A2': 'OI',
    '\\uA74E': 'OO',
    '\\u0222': 'OU',
    '\\u24C5': 'P',
    '\\uFF30': 'P',
    '\\u1E54': 'P',
    '\\u1E56': 'P',
    '\\u01A4': 'P',
    '\\u2C63': 'P',
    '\\uA750': 'P',
    '\\uA752': 'P',
    '\\uA754': 'P',
    '\\u24C6': 'Q',
    '\\uFF31': 'Q',
    '\\uA756': 'Q',
    '\\uA758': 'Q',
    '\\u024A': 'Q',
    '\\u24C7': 'R',
    '\\uFF32': 'R',
    '\\u0154': 'R',
    '\\u1E58': 'R',
    '\\u0158': 'R',
    '\\u0210': 'R',
    '\\u0212': 'R',
    '\\u1E5A': 'R',
    '\\u1E5C': 'R',
    '\\u0156': 'R',
    '\\u1E5E': 'R',
    '\\u024C': 'R',
    '\\u2C64': 'R',
    '\\uA75A': 'R',
    '\\uA7A6': 'R',
    '\\uA782': 'R',
    '\\u24C8': 'S',
    '\\uFF33': 'S',
    '\\u1E9E': 'S',
    '\\u015A': 'S',
    '\\u1E64': 'S',
    '\\u015C': 'S',
    '\\u1E60': 'S',
    '\\u0160': 'S',
    '\\u1E66': 'S',
    '\\u1E62': 'S',
    '\\u1E68': 'S',
    '\\u0218': 'S',
    '\\u015E': 'S',
    '\\u2C7E': 'S',
    '\\uA7A8': 'S',
    '\\uA784': 'S',
    '\\u24C9': 'T',
    '\\uFF34': 'T',
    '\\u1E6A': 'T',
    '\\u0164': 'T',
    '\\u1E6C': 'T',
    '\\u021A': 'T',
    '\\u0162': 'T',
    '\\u1E70': 'T',
    '\\u1E6E': 'T',
    '\\u0166': 'T',
    '\\u01AC': 'T',
    '\\u01AE': 'T',
    '\\u023E': 'T',
    '\\uA786': 'T',
    '\\uA728': 'TZ',
    '\\u24CA': 'U',
    '\\uFF35': 'U',
    '\\u00D9': 'U',
    '\\u00DA': 'U',
    '\\u00DB': 'U',
    '\\u0168': 'U',
    '\\u1E78': 'U',
    '\\u016A': 'U',
    '\\u1E7A': 'U',
    '\\u016C': 'U',
    '\\u00DC': 'U',
    '\\u01DB': 'U',
    '\\u01D7': 'U',
    '\\u01D5': 'U',
    '\\u01D9': 'U',
    '\\u1EE6': 'U',
    '\\u016E': 'U',
    '\\u0170': 'U',
    '\\u01D3': 'U',
    '\\u0214': 'U',
    '\\u0216': 'U',
    '\\u01AF': 'U',
    '\\u1EEA': 'U',
    '\\u1EE8': 'U',
    '\\u1EEE': 'U',
    '\\u1EEC': 'U',
    '\\u1EF0': 'U',
    '\\u1EE4': 'U',
    '\\u1E72': 'U',
    '\\u0172': 'U',
    '\\u1E76': 'U',
    '\\u1E74': 'U',
    '\\u0244': 'U',
    '\\u24CB': 'V',
    '\\uFF36': 'V',
    '\\u1E7C': 'V',
    '\\u1E7E': 'V',
    '\\u01B2': 'V',
    '\\uA75E': 'V',
    '\\u0245': 'V',
    '\\uA760': 'VY',
    '\\u24CC': 'W',
    '\\uFF37': 'W',
    '\\u1E80': 'W',
    '\\u1E82': 'W',
    '\\u0174': 'W',
    '\\u1E86': 'W',
    '\\u1E84': 'W',
    '\\u1E88': 'W',
    '\\u2C72': 'W',
    '\\u24CD': 'X',
    '\\uFF38': 'X',
    '\\u1E8A': 'X',
    '\\u1E8C': 'X',
    '\\u24CE': 'Y',
    '\\uFF39': 'Y',
    '\\u1EF2': 'Y',
    '\\u00DD': 'Y',
    '\\u0176': 'Y',
    '\\u1EF8': 'Y',
    '\\u0232': 'Y',
    '\\u1E8E': 'Y',
    '\\u0178': 'Y',
    '\\u1EF6': 'Y',
    '\\u1EF4': 'Y',
    '\\u01B3': 'Y',
    '\\u024E': 'Y',
    '\\u1EFE': 'Y',
    '\\u24CF': 'Z',
    '\\uFF3A': 'Z',
    '\\u0179': 'Z',
    '\\u1E90': 'Z',
    '\\u017B': 'Z',
    '\\u017D': 'Z',
    '\\u1E92': 'Z',
    '\\u1E94': 'Z',
    '\\u01B5': 'Z',
    '\\u0224': 'Z',
    '\\u2C7F': 'Z',
    '\\u2C6B': 'Z',
    '\\uA762': 'Z',
    '\\u24D0': 'a',
    '\\uFF41': 'a',
    '\\u1E9A': 'a',
    '\\u00E0': 'a',
    '\\u00E1': 'a',
    '\\u00E2': 'a',
    '\\u1EA7': 'a',
    '\\u1EA5': 'a',
    '\\u1EAB': 'a',
    '\\u1EA9': 'a',
    '\\u00E3': 'a',
    '\\u0101': 'a',
    '\\u0103': 'a',
    '\\u1EB1': 'a',
    '\\u1EAF': 'a',
    '\\u1EB5': 'a',
    '\\u1EB3': 'a',
    '\\u0227': 'a',
    '\\u01E1': 'a',
    '\\u00E4': 'a',
    '\\u01DF': 'a',
    '\\u1EA3': 'a',
    '\\u00E5': 'a',
    '\\u01FB': 'a',
    '\\u01CE': 'a',
    '\\u0201': 'a',
    '\\u0203': 'a',
    '\\u1EA1': 'a',
    '\\u1EAD': 'a',
    '\\u1EB7': 'a',
    '\\u1E01': 'a',
    '\\u0105': 'a',
    '\\u2C65': 'a',
    '\\u0250': 'a',
    '\\uA733': 'aa',
    '\\u00E6': 'ae',
    '\\u01FD': 'ae',
    '\\u01E3': 'ae',
    '\\uA735': 'ao',
    '\\uA737': 'au',
    '\\uA739': 'av',
    '\\uA73B': 'av',
    '\\uA73D': 'ay',
    '\\u24D1': 'b',
    '\\uFF42': 'b',
    '\\u1E03': 'b',
    '\\u1E05': 'b',
    '\\u1E07': 'b',
    '\\u0180': 'b',
    '\\u0183': 'b',
    '\\u0253': 'b',
    '\\u24D2': 'c',
    '\\uFF43': 'c',
    '\\u0107': 'c',
    '\\u0109': 'c',
    '\\u010B': 'c',
    '\\u010D': 'c',
    '\\u00E7': 'c',
    '\\u1E09': 'c',
    '\\u0188': 'c',
    '\\u023C': 'c',
    '\\uA73F': 'c',
    '\\u2184': 'c',
    '\\u24D3': 'd',
    '\\uFF44': 'd',
    '\\u1E0B': 'd',
    '\\u010F': 'd',
    '\\u1E0D': 'd',
    '\\u1E11': 'd',
    '\\u1E13': 'd',
    '\\u1E0F': 'd',
    '\\u0111': 'd',
    '\\u018C': 'd',
    '\\u0256': 'd',
    '\\u0257': 'd',
    '\\uA77A': 'd',
    '\\u01F3': 'dz',
    '\\u01C6': 'dz',
    '\\u24D4': 'e',
    '\\uFF45': 'e',
    '\\u00E8': 'e',
    '\\u00E9': 'e',
    '\\u00EA': 'e',
    '\\u1EC1': 'e',
    '\\u1EBF': 'e',
    '\\u1EC5': 'e',
    '\\u1EC3': 'e',
    '\\u1EBD': 'e',
    '\\u0113': 'e',
    '\\u1E15': 'e',
    '\\u1E17': 'e',
    '\\u0115': 'e',
    '\\u0117': 'e',
    '\\u00EB': 'e',
    '\\u1EBB': 'e',
    '\\u011B': 'e',
    '\\u0205': 'e',
    '\\u0207': 'e',
    '\\u1EB9': 'e',
    '\\u1EC7': 'e',
    '\\u0229': 'e',
    '\\u1E1D': 'e',
    '\\u0119': 'e',
    '\\u1E19': 'e',
    '\\u1E1B': 'e',
    '\\u0247': 'e',
    '\\u025B': 'e',
    '\\u01DD': 'e',
    '\\u24D5': 'f',
    '\\uFF46': 'f',
    '\\u1E1F': 'f',
    '\\u0192': 'f',
    '\\uA77C': 'f',
    '\\u24D6': 'g',
    '\\uFF47': 'g',
    '\\u01F5': 'g',
    '\\u011D': 'g',
    '\\u1E21': 'g',
    '\\u011F': 'g',
    '\\u0121': 'g',
    '\\u01E7': 'g',
    '\\u0123': 'g',
    '\\u01E5': 'g',
    '\\u0260': 'g',
    '\\uA7A1': 'g',
    '\\u1D79': 'g',
    '\\uA77F': 'g',
    '\\u24D7': 'h',
    '\\uFF48': 'h',
    '\\u0125': 'h',
    '\\u1E23': 'h',
    '\\u1E27': 'h',
    '\\u021F': 'h',
    '\\u1E25': 'h',
    '\\u1E29': 'h',
    '\\u1E2B': 'h',
    '\\u1E96': 'h',
    '\\u0127': 'h',
    '\\u2C68': 'h',
    '\\u2C76': 'h',
    '\\u0265': 'h',
    '\\u0195': 'hv',
    '\\u24D8': 'i',
    '\\uFF49': 'i',
    '\\u00EC': 'i',
    '\\u00ED': 'i',
    '\\u00EE': 'i',
    '\\u0129': 'i',
    '\\u012B': 'i',
    '\\u012D': 'i',
    '\\u00EF': 'i',
    '\\u1E2F': 'i',
    '\\u1EC9': 'i',
    '\\u01D0': 'i',
    '\\u0209': 'i',
    '\\u020B': 'i',
    '\\u1ECB': 'i',
    '\\u012F': 'i',
    '\\u1E2D': 'i',
    '\\u0268': 'i',
    '\\u0131': 'i',
    '\\u24D9': 'j',
    '\\uFF4A': 'j',
    '\\u0135': 'j',
    '\\u01F0': 'j',
    '\\u0249': 'j',
    '\\u24DA': 'k',
    '\\uFF4B': 'k',
    '\\u1E31': 'k',
    '\\u01E9': 'k',
    '\\u1E33': 'k',
    '\\u0137': 'k',
    '\\u1E35': 'k',
    '\\u0199': 'k',
    '\\u2C6A': 'k',
    '\\uA741': 'k',
    '\\uA743': 'k',
    '\\uA745': 'k',
    '\\uA7A3': 'k',
    '\\u24DB': 'l',
    '\\uFF4C': 'l',
    '\\u0140': 'l',
    '\\u013A': 'l',
    '\\u013E': 'l',
    '\\u1E37': 'l',
    '\\u1E39': 'l',
    '\\u013C': 'l',
    '\\u1E3D': 'l',
    '\\u1E3B': 'l',
    '\\u017F': 'l',
    '\\u0142': 'l',
    '\\u019A': 'l',
    '\\u026B': 'l',
    '\\u2C61': 'l',
    '\\uA749': 'l',
    '\\uA781': 'l',
    '\\uA747': 'l',
    '\\u01C9': 'lj',
    '\\u24DC': 'm',
    '\\uFF4D': 'm',
    '\\u1E3F': 'm',
    '\\u1E41': 'm',
    '\\u1E43': 'm',
    '\\u0271': 'm',
    '\\u026F': 'm',
    '\\u24DD': 'n',
    '\\uFF4E': 'n',
    '\\u01F9': 'n',
    '\\u0144': 'n',
    '\\u00F1': 'n',
    '\\u1E45': 'n',
    '\\u0148': 'n',
    '\\u1E47': 'n',
    '\\u0146': 'n',
    '\\u1E4B': 'n',
    '\\u1E49': 'n',
    '\\u019E': 'n',
    '\\u0272': 'n',
    '\\u0149': 'n',
    '\\uA791': 'n',
    '\\uA7A5': 'n',
    '\\u01CC': 'nj',
    '\\u24DE': 'o',
    '\\uFF4F': 'o',
    '\\u00F2': 'o',
    '\\u00F3': 'o',
    '\\u00F4': 'o',
    '\\u1ED3': 'o',
    '\\u1ED1': 'o',
    '\\u1ED7': 'o',
    '\\u1ED5': 'o',
    '\\u00F5': 'o',
    '\\u1E4D': 'o',
    '\\u022D': 'o',
    '\\u1E4F': 'o',
    '\\u014D': 'o',
    '\\u1E51': 'o',
    '\\u1E53': 'o',
    '\\u014F': 'o',
    '\\u022F': 'o',
    '\\u0231': 'o',
    '\\u00F6': 'o',
    '\\u022B': 'o',
    '\\u1ECF': 'o',
    '\\u0151': 'o',
    '\\u01D2': 'o',
    '\\u020D': 'o',
    '\\u020F': 'o',
    '\\u01A1': 'o',
    '\\u1EDD': 'o',
    '\\u1EDB': 'o',
    '\\u1EE1': 'o',
    '\\u1EDF': 'o',
    '\\u1EE3': 'o',
    '\\u1ECD': 'o',
    '\\u1ED9': 'o',
    '\\u01EB': 'o',
    '\\u01ED': 'o',
    '\\u00F8': 'o',
    '\\u01FF': 'o',
    '\\u0254': 'o',
    '\\uA74B': 'o',
    '\\uA74D': 'o',
    '\\u0275': 'o',
    '\\u0153': 'oe',
    '\\u01A3': 'oi',
    '\\u0223': 'ou',
    '\\uA74F': 'oo',
    '\\u24DF': 'p',
    '\\uFF50': 'p',
    '\\u1E55': 'p',
    '\\u1E57': 'p',
    '\\u01A5': 'p',
    '\\u1D7D': 'p',
    '\\uA751': 'p',
    '\\uA753': 'p',
    '\\uA755': 'p',
    '\\u24E0': 'q',
    '\\uFF51': 'q',
    '\\u024B': 'q',
    '\\uA757': 'q',
    '\\uA759': 'q',
    '\\u24E1': 'r',
    '\\uFF52': 'r',
    '\\u0155': 'r',
    '\\u1E59': 'r',
    '\\u0159': 'r',
    '\\u0211': 'r',
    '\\u0213': 'r',
    '\\u1E5B': 'r',
    '\\u1E5D': 'r',
    '\\u0157': 'r',
    '\\u1E5F': 'r',
    '\\u024D': 'r',
    '\\u027D': 'r',
    '\\uA75B': 'r',
    '\\uA7A7': 'r',
    '\\uA783': 'r',
    '\\u24E2': 's',
    '\\uFF53': 's',
    '\\u00DF': 's',
    '\\u015B': 's',
    '\\u1E65': 's',
    '\\u015D': 's',
    '\\u1E61': 's',
    '\\u0161': 's',
    '\\u1E67': 's',
    '\\u1E63': 's',
    '\\u1E69': 's',
    '\\u0219': 's',
    '\\u015F': 's',
    '\\u023F': 's',
    '\\uA7A9': 's',
    '\\uA785': 's',
    '\\u1E9B': 's',
    '\\u24E3': 't',
    '\\uFF54': 't',
    '\\u1E6B': 't',
    '\\u1E97': 't',
    '\\u0165': 't',
    '\\u1E6D': 't',
    '\\u021B': 't',
    '\\u0163': 't',
    '\\u1E71': 't',
    '\\u1E6F': 't',
    '\\u0167': 't',
    '\\u01AD': 't',
    '\\u0288': 't',
    '\\u2C66': 't',
    '\\uA787': 't',
    '\\uA729': 'tz',
    '\\u24E4': 'u',
    '\\uFF55': 'u',
    '\\u00F9': 'u',
    '\\u00FA': 'u',
    '\\u00FB': 'u',
    '\\u0169': 'u',
    '\\u1E79': 'u',
    '\\u016B': 'u',
    '\\u1E7B': 'u',
    '\\u016D': 'u',
    '\\u00FC': 'u',
    '\\u01DC': 'u',
    '\\u01D8': 'u',
    '\\u01D6': 'u',
    '\\u01DA': 'u',
    '\\u1EE7': 'u',
    '\\u016F': 'u',
    '\\u0171': 'u',
    '\\u01D4': 'u',
    '\\u0215': 'u',
    '\\u0217': 'u',
    '\\u01B0': 'u',
    '\\u1EEB': 'u',
    '\\u1EE9': 'u',
    '\\u1EEF': 'u',
    '\\u1EED': 'u',
    '\\u1EF1': 'u',
    '\\u1EE5': 'u',
    '\\u1E73': 'u',
    '\\u0173': 'u',
    '\\u1E77': 'u',
    '\\u1E75': 'u',
    '\\u0289': 'u',
    '\\u24E5': 'v',
    '\\uFF56': 'v',
    '\\u1E7D': 'v',
    '\\u1E7F': 'v',
    '\\u028B': 'v',
    '\\uA75F': 'v',
    '\\u028C': 'v',
    '\\uA761': 'vy',
    '\\u24E6': 'w',
    '\\uFF57': 'w',
    '\\u1E81': 'w',
    '\\u1E83': 'w',
    '\\u0175': 'w',
    '\\u1E87': 'w',
    '\\u1E85': 'w',
    '\\u1E98': 'w',
    '\\u1E89': 'w',
    '\\u2C73': 'w',
    '\\u24E7': 'x',
    '\\uFF58': 'x',
    '\\u1E8B': 'x',
    '\\u1E8D': 'x',
    '\\u24E8': 'y',
    '\\uFF59': 'y',
    '\\u1EF3': 'y',
    '\\u00FD': 'y',
    '\\u0177': 'y',
    '\\u1EF9': 'y',
    '\\u0233': 'y',
    '\\u1E8F': 'y',
    '\\u00FF': 'y',
    '\\u1EF7': 'y',
    '\\u1E99': 'y',
    '\\u1EF5': 'y',
    '\\u01B4': 'y',
    '\\u024F': 'y',
    '\\u1EFF': 'y',
    '\\u24E9': 'z',
    '\\uFF5A': 'z',
    '\\u017A': 'z',
    '\\u1E91': 'z',
    '\\u017C': 'z',
    '\\u017E': 'z',
    '\\u1E93': 'z',
    '\\u1E95': 'z',
    '\\u01B6': 'z',
    '\\u0225': 'z',
    '\\u0240': 'z',
    '\\u2C6C': 'z',
    '\\uA763': 'z',
    '\\u0386': '\\u0391',
    '\\u0388': '\\u0395',
    '\\u0389': '\\u0397',
    '\\u038A': '\\u0399',
    '\\u03AA': '\\u0399',
    '\\u038C': '\\u039F',
    '\\u038E': '\\u03A5',
    '\\u03AB': '\\u03A5',
    '\\u038F': '\\u03A9',
    '\\u03AC': '\\u03B1',
    '\\u03AD': '\\u03B5',
    '\\u03AE': '\\u03B7',
    '\\u03AF': '\\u03B9',
    '\\u03CA': '\\u03B9',
    '\\u0390': '\\u03B9',
    '\\u03CC': '\\u03BF',
    '\\u03CD': '\\u03C5',
    '\\u03CB': '\\u03C5',
    '\\u03B0': '\\u03C5',
    '\\u03CE': '\\u03C9',
    '\\u03C2': '\\u03C3',
    '\\u2019': '\\''
  };

  return diacritics;
});

S2.define('select2/data/base',[
  '../utils'
], function (Utils) {
  function BaseAdapter ($element, options) {
    BaseAdapter.__super__.constructor.call(this);
  }

  Utils.Extend(BaseAdapter, Utils.Observable);

  BaseAdapter.prototype.current = function (callback) {
    throw new Error('The \`current\` method must be defined in child classes.');
  };

  BaseAdapter.prototype.query = function (params, callback) {
    throw new Error('The \`query\` method must be defined in child classes.');
  };

  BaseAdapter.prototype.bind = function (container, $container) {
    // Can be implemented in subclasses
  };

  BaseAdapter.prototype.destroy = function () {
    // Can be implemented in subclasses
  };

  BaseAdapter.prototype.generateResultId = function (container, data) {
    var id = container.id + '-result-';

    id += Utils.generateChars(4);

    if (data.id != null) {
      id += '-' + data.id.toString();
    } else {
      id += '-' + Utils.generateChars(4);
    }
    return id;
  };

  return BaseAdapter;
});

S2.define('select2/data/select',[
  './base',
  '../utils',
  'jquery'
], function (BaseAdapter, Utils, $) {
  function SelectAdapter ($element, options) {
    this.$element = $element;
    this.options = options;

    SelectAdapter.__super__.constructor.call(this);
  }

  Utils.Extend(SelectAdapter, BaseAdapter);

  SelectAdapter.prototype.current = function (callback) {
    var self = this;

    var data = Array.prototype.map.call(
      this.$element[0].querySelectorAll(':checked'),
      function (selectedElement) {
        return self.item($(selectedElement));
      }
    );

    callback(data);
  };

  SelectAdapter.prototype.select = function (data) {
    var self = this;

    data.selected = true;

    // If data.element is a DOM node, use it instead
    if (
      data.element != null && data.element.tagName.toLowerCase() === 'option'
    ) {
      data.element.selected = true;

      this.$element.trigger('input').trigger('change');

      return;
    }

    if (this.$element[0].multiple) {
      this.current(function (currentData) {
        var val = [];

        data = [data];
        data.push.apply(data, currentData);

        for (var d = 0; d < data.length; d++) {
          var id = data[d].id;

          if (val.indexOf(id) === -1) {
            val.push(id);
          }
        }

        self.$element.val(val);
        self.$element.trigger('input').trigger('change');
      });
    } else {
      var val = data.id;

      this.$element.val(val);
      this.$element.trigger('input').trigger('change');
    }
  };

  SelectAdapter.prototype.unselect = function (data) {
    var self = this;

    if (!this.$element[0].multiple) {
      return;
    }

    data.selected = false;

    if (
      data.element != null &&
      data.element.tagName.toLowerCase() === 'option'
    ) {
      data.element.selected = false;

      this.$element.trigger('input').trigger('change');

      return;
    }

    this.current(function (currentData) {
      var val = [];

      for (var d = 0; d < currentData.length; d++) {
        var id = currentData[d].id;

        if (id !== data.id && val.indexOf(id) === -1) {
          val.push(id);
        }
      }

      self.$element.val(val);

      self.$element.trigger('input').trigger('change');
    });
  };

  SelectAdapter.prototype.bind = function (container, $container) {
    var self = this;

    this.container = container;

    container.on('select', function (params) {
      self.select(params.data);
    });

    container.on('unselect', function (params) {
      self.unselect(params.data);
    });
  };

  SelectAdapter.prototype.destroy = function () {
    // Remove anything added to child elements
    this.$element.find('*').each(function () {
      // Remove any custom data set by Select2
      Utils.RemoveData(this);
    });
  };

  SelectAdapter.prototype.query = function (params, callback) {
    var data = [];
    var self = this;

    var $options = this.$element.children();

    $options.each(function () {
      if (
        this.tagName.toLowerCase() !== 'option' &&
        this.tagName.toLowerCase() !== 'optgroup'
      ) {
        return;
      }

      var $option = $(this);

      var option = self.item($option);

      var matches = self.matches(params, option);

      if (matches !== null) {
        data.push(matches);
      }
    });

    callback({
      results: data
    });
  };

  SelectAdapter.prototype.addOptions = function ($options) {
    this.$element.append($options);
  };

  SelectAdapter.prototype.option = function (data) {
    var option;

    if (data.children) {
      option = document.createElement('optgroup');
      option.label = data.text;
    } else {
      option = document.createElement('option');

      if (option.textContent !== undefined) {
        option.textContent = data.text;
      } else {
        option.innerText = data.text;
      }
    }

    if (data.id !== undefined) {
      option.value = data.id;
    }

    if (data.disabled) {
      option.disabled = true;
    }

    if (data.selected) {
      option.selected = true;
    }

    if (data.title) {
      option.title = data.title;
    }

    var normalizedData = this._normalizeItem(data);
    normalizedData.element = option;

    // Override the option's data with the combined data
    Utils.StoreData(option, 'data', normalizedData);

    return $(option);
  };

  SelectAdapter.prototype.item = function ($option) {
    var data = {};

    data = Utils.GetData($option[0], 'data');

    if (data != null) {
      return data;
    }

    var option = $option[0];

    if (option.tagName.toLowerCase() === 'option') {
      data = {
        id: $option.val(),
        text: $option.text(),
        disabled: $option[0].disabled,
        selected: $option[0].selected,
        title: $option[0].title
      };
    } else if (option.tagName.toLowerCase() === 'optgroup') {
      data = {
        text: $option[0].label,
        children: [],
        title: $option[0].title
      };

      var $children = $option.children('option');
      var children = [];

      for (var c = 0; c < $children.length; c++) {
        var $child = $($children[c]);

        var child = this.item($child);

        children.push(child);
      }

      data.children = children;
    }

    data = this._normalizeItem(data);
    data.element = $option[0];

    Utils.StoreData($option[0], 'data', data);

    return data;
  };

  SelectAdapter.prototype._normalizeItem = function (item) {
    if (item !== Object(item)) {
      item = {
        id: item,
        text: item
      };
    }

    item = $.extend({}, {
      text: ''
    }, item);

    var defaults = {
      selected: false,
      disabled: false
    };

    if (item.id != null) {
      item.id = item.id.toString();
    }

    if (item.text != null) {
      item.text = item.text.toString();
    }

    if (item._resultId == null && item.id && this.container != null) {
      item._resultId = this.generateResultId(this.container, item);
    }

    if (item.children) {
        item.children = item.children.map(
            SelectAdapter.prototype._normalizeItem
        );
    }

    return $.extend({}, defaults, item);
  };

  SelectAdapter.prototype.matches = function (params, data) {
    var matcher = this.options.get('matcher');

    return matcher(params, data);
  };

  return SelectAdapter;
});

S2.define('select2/data/array',[
  './select',
  '../utils',
  'jquery'
], function (SelectAdapter, Utils, $) {
  function ArrayAdapter ($element, options) {
    this._dataToConvert = options.get('data') || [];

    ArrayAdapter.__super__.constructor.call(this, $element, options);
  }

  Utils.Extend(ArrayAdapter, SelectAdapter);

  ArrayAdapter.prototype.bind = function (container, $container) {
    ArrayAdapter.__super__.bind.call(this, container, $container);

    this.addOptions(this.convertToOptions(this._dataToConvert));
  };

  ArrayAdapter.prototype.select = function (data) {
    var $option = this.$element.find('option').filter(function (i, elm) {
      return elm.value == data.id.toString();
    });

    if ($option.length === 0) {
      $option = this.option(data);

      this.addOptions($option);
    }

    ArrayAdapter.__super__.select.call(this, data);
  };

  ArrayAdapter.prototype.convertToOptions = function (data) {
    var self = this;

    var $existing = this.$element.find('option');
    var existingIds = $existing.map(function () {
      return self.item($(this)).id;
    }).get();

    var $options = [];

    // Filter out all items except for the one passed in the argument
    function onlyItem (item) {
      return function () {
        return $(this).val() == item.id;
      };
    }

    for (var d = 0; d < data.length; d++) {
      var item = this._normalizeItem(data[d]);

      // Skip items which were pre-loaded, only merge the data
      if (existingIds.indexOf(item.id) >= 0) {
        var $existingOption = $existing.filter(onlyItem(item));

        var existingData = this.item($existingOption);
        var newData = $.extend(true, {}, item, existingData);

        var $newOption = this.option(newData);

        $existingOption.replaceWith($newOption);

        continue;
      }

      var $option = this.option(item);

      if (item.children) {
        var $children = this.convertToOptions(item.children);

        $option.append($children);
      }

      $options.push($option);
    }

    return $options;
  };

  return ArrayAdapter;
});

S2.define('select2/data/ajax',[
  './array',
  '../utils',
  'jquery'
], function (ArrayAdapter, Utils, $) {
  function AjaxAdapter ($element, options) {
    this.ajaxOptions = this._applyDefaults(options.get('ajax'));

    if (this.ajaxOptions.processResults != null) {
      this.processResults = this.ajaxOptions.processResults;
    }

    AjaxAdapter.__super__.constructor.call(this, $element, options);
  }

  Utils.Extend(AjaxAdapter, ArrayAdapter);

  AjaxAdapter.prototype._applyDefaults = function (options) {
    var defaults = {
      data: function (params) {
        return $.extend({}, params, {
          q: params.term
        });
      },
      transport: function (params, success, failure) {
        var $request = $.ajax(params);

        $request.then(success);
        $request.fail(failure);

        return $request;
      }
    };

    return $.extend({}, defaults, options, true);
  };

  AjaxAdapter.prototype.processResults = function (results) {
    return results;
  };

  AjaxAdapter.prototype.query = function (params, callback) {
    var matches = [];
    var self = this;

    if (this._request != null) {
      // JSONP requests cannot always be aborted
      if (typeof this._request.abort === 'function') {
        this._request.abort();
      }

      this._request = null;
    }

    var options = $.extend({
      type: 'GET'
    }, this.ajaxOptions);

    if (typeof options.url === 'function') {
      options.url = options.url.call(this.$element, params);
    }

    if (typeof options.data === 'function') {
      options.data = options.data.call(this.$element, params);
    }

    function request () {
      var $request = options.transport(options, function (data) {
        var results = self.processResults(data, params);

        if (results && results.results && Array.isArray(results.results)) {
          results.results = results.results.map(
            AjaxAdapter.prototype._normalizeItem
          );
        } else {
          if (self.options.get('debug') && window.console && console.error) {
            // Check to make sure that the response included a \`results\` key.
            console.error(
              'Select2: The AJAX results did not return an array in the ' +
              '\`results\` key of the response.'
            );
          }
        }

        callback(results);
      }, function () {
        // Attempt to detect if a request was aborted
        // Only works if the transport exposes a status property
        if ($request && 'status' in $request &&
            ($request.status === 0 || $request.status === '0')) {
          return;
        }

        self.trigger('results:message', {
          message: 'errorLoading'
        });
      });

      self._request = $request;
    }

    if (this.ajaxOptions.delay && params.term != null) {
      if (this._queryTimeout) {
        window.clearTimeout(this._queryTimeout);
      }

      this._queryTimeout = window.setTimeout(request, this.ajaxOptions.delay);
    } else {
      request();
    }
  };

  return AjaxAdapter;
});

S2.define('select2/data/tags',[
  'jquery'
], function ($) {
  function Tags (decorated, $element, options) {
    var tags = options.get('tags');

    var createTag = options.get('createTag');

    if (createTag !== undefined) {
      this.createTag = createTag;
    }

    var insertTag = options.get('insertTag');

    if (insertTag !== undefined) {
        this.insertTag = insertTag;
    }

    decorated.call(this, $element, options);

    if (Array.isArray(tags)) {
      for (var t = 0; t < tags.length; t++) {
        var tag = tags[t];
        var item = this._normalizeItem(tag);

        var $option = this.option(item);

        this.$element.append($option);
      }
    }
  }

  Tags.prototype.query = function (decorated, params, callback) {
    var self = this;

    this._removeOldTags();

    if (params.term == null || params.page != null) {
      decorated.call(this, params, callback);
      return;
    }

    function wrapper (obj, child) {
      var data = obj.results;

      for (var i = 0; i < data.length; i++) {
        var option = data[i];

        var checkChildren = (
          option.children != null &&
          !wrapper({
            results: option.children
          }, true)
        );

        var optionText = (option.text || '').toUpperCase();
        var paramsTerm = (params.term || '').toUpperCase();

        var checkText = optionText === paramsTerm;

        if (checkText || checkChildren) {
          if (child) {
            return false;
          }

          obj.data = data;
          callback(obj);

          return;
        }
      }

      if (child) {
        return true;
      }

      var tag = self.createTag(params);

      if (tag != null) {
        var $option = self.option(tag);
        $option[0].setAttribute('data-select2-tag', 'true');

        self.addOptions([$option]);

        self.insertTag(data, tag);
      }

      obj.results = data;

      callback(obj);
    }

    decorated.call(this, params, wrapper);
  };

  Tags.prototype.createTag = function (decorated, params) {
    if (params.term == null) {
      return null;
    }

    var term = params.term.trim();

    if (term === '') {
      return null;
    }

    return {
      id: term,
      text: term
    };
  };

  Tags.prototype.insertTag = function (_, data, tag) {
    data.unshift(tag);
  };

  Tags.prototype._removeOldTags = function (_) {
    var $options = this.$element.find('option[data-select2-tag]');

    $options.each(function () {
      if (this.selected) {
        return;
      }

      $(this).remove();
    });
  };

  return Tags;
});

S2.define('select2/data/tokenizer',[
  'jquery'
], function ($) {
  function Tokenizer (decorated, $element, options) {
    var tokenizer = options.get('tokenizer');

    if (tokenizer !== undefined) {
      this.tokenizer = tokenizer;
    }

    decorated.call(this, $element, options);
  }

  Tokenizer.prototype.bind = function (decorated, container, $container) {
    decorated.call(this, container, $container);

    this.$search =  container.dropdown.$search || container.selection.$search ||
      $container.find('.select2-search__field');
  };

  Tokenizer.prototype.query = function (decorated, params, callback) {
    var self = this;

    function createAndSelect (data) {
      // Normalize the data object so we can use it for checks
      var item = self._normalizeItem(data);

      // Check if the data object already exists as a tag
      // Select it if it doesn't
      var $existingOptions = self.$element.find('option').filter(function () {
        return $(this).val() === item.id;
      });

      // If an existing option wasn't found for it, create the option
      if (!$existingOptions.length) {
        var $option = self.option(item);
        $option[0].setAttribute('data-select2-tag', true);

        self._removeOldTags();
        self.addOptions([$option]);
      }

      // Select the item, now that we know there is an option for it
      select(item);
    }

    function select (data) {
      self.trigger('select', {
        data: data
      });
    }

    params.term = params.term || '';

    var tokenData = this.tokenizer(params, this.options, createAndSelect);

    if (tokenData.term !== params.term) {
      // Replace the search term if we have the search box
      if (this.$search.length) {
        this.$search.val(tokenData.term);
        this.$search.trigger('focus');
      }

      params.term = tokenData.term;
    }

    decorated.call(this, params, callback);
  };

  Tokenizer.prototype.tokenizer = function (_, params, options, callback) {
    var separators = options.get('tokenSeparators') || [];
    var term = params.term;
    var i = 0;

    var createTag = this.createTag || function (params) {
      return {
        id: params.term,
        text: params.term
      };
    };

    while (i < term.length) {
      var termChar = term[i];

      if (separators.indexOf(termChar) === -1) {
        i++;

        continue;
      }

      var part = term.substr(0, i);
      var partParams = $.extend({}, params, {
        term: part
      });

      var data = createTag(partParams);

      if (data == null) {
        i++;
        continue;
      }

      callback(data);

      // Reset the term to not include the tokenized portion
      term = term.substr(i + 1) || '';
      i = 0;
    }

    return {
      term: term
    };
  };

  return Tokenizer;
});

S2.define('select2/data/minimumInputLength',[

], function () {
  function MinimumInputLength (decorated, $e, options) {
    this.minimumInputLength = options.get('minimumInputLength');

    decorated.call(this, $e, options);
  }

  MinimumInputLength.prototype.query = function (decorated, params, callback) {
    params.term = params.term || '';

    if (params.term.length < this.minimumInputLength) {
      this.trigger('results:message', {
        message: 'inputTooShort',
        args: {
          minimum: this.minimumInputLength,
          input: params.term,
          params: params
        }
      });

      return;
    }

    decorated.call(this, params, callback);
  };

  return MinimumInputLength;
});

S2.define('select2/data/maximumInputLength',[

], function () {
  function MaximumInputLength (decorated, $e, options) {
    this.maximumInputLength = options.get('maximumInputLength');

    decorated.call(this, $e, options);
  }

  MaximumInputLength.prototype.query = function (decorated, params, callback) {
    params.term = params.term || '';

    if (this.maximumInputLength > 0 &&
        params.term.length > this.maximumInputLength) {
      this.trigger('results:message', {
        message: 'inputTooLong',
        args: {
          maximum: this.maximumInputLength,
          input: params.term,
          params: params
        }
      });

      return;
    }

    decorated.call(this, params, callback);
  };

  return MaximumInputLength;
});

S2.define('select2/data/maximumSelectionLength',[

], function (){
  function MaximumSelectionLength (decorated, $e, options) {
    this.maximumSelectionLength = options.get('maximumSelectionLength');

    decorated.call(this, $e, options);
  }

  MaximumSelectionLength.prototype.bind =
    function (decorated, container, $container) {
      var self = this;

      decorated.call(this, container, $container);

      container.on('select', function () {
        self._checkIfMaximumSelected();
      });
  };

  MaximumSelectionLength.prototype.query =
    function (decorated, params, callback) {
      var self = this;

      this._checkIfMaximumSelected(function () {
        decorated.call(self, params, callback);
      });
  };

  MaximumSelectionLength.prototype._checkIfMaximumSelected =
    function (_, successCallback) {
      var self = this;

      this.current(function (currentData) {
        var count = currentData != null ? currentData.length : 0;
        if (self.maximumSelectionLength > 0 &&
          count >= self.maximumSelectionLength) {
          self.trigger('results:message', {
            message: 'maximumSelected',
            args: {
              maximum: self.maximumSelectionLength
            }
          });
          return;
        }

        if (successCallback) {
          successCallback();
        }
      });
  };

  return MaximumSelectionLength;
});

S2.define('select2/dropdown',[
  'jquery',
  './utils'
], function ($, Utils) {
  function Dropdown ($element, options) {
    this.$element = $element;
    this.options = options;

    Dropdown.__super__.constructor.call(this);
  }

  Utils.Extend(Dropdown, Utils.Observable);

  Dropdown.prototype.render = function () {
    var $dropdown = $(
      '<span class="select2-dropdown">' +
        '<span class="select2-results"></span>' +
      '</span>'
    );

    $dropdown[0].setAttribute('dir', this.options.get('dir'));

    this.$dropdown = $dropdown;

    return $dropdown;
  };

  Dropdown.prototype.bind = function () {
    // Should be implemented in subclasses
  };

  Dropdown.prototype.position = function ($dropdown, $container) {
    // Should be implemented in subclasses
  };

  Dropdown.prototype.destroy = function () {
    // Remove the dropdown from the DOM
    this.$dropdown.remove();
  };

  return Dropdown;
});

S2.define('select2/dropdown/search',[
  'jquery'
], function ($) {
  function Search () { }

  Search.prototype.render = function (decorated) {
    var $rendered = decorated.call(this);
    var searchLabel = this.options.get('translations').get('search');

    var $search = $(
      '<span class="select2-search select2-search--dropdown">' +
        '<input class="select2-search__field" type="search" tabindex="-1"' +
        ' autocorrect="off" autocapitalize="none"' +
        ' spellcheck="false" role="searchbox" aria-autocomplete="list" />' +
      '</span>'
    );

    this.$searchContainer = $search;
    this.$search = $search.find('input');

    this.$search[0].autocomplete = this.options.get('autocomplete');
    this.$search[0].setAttribute('aria-label', searchLabel());

    $rendered.prepend($search);

    return $rendered;
  };

  Search.prototype.bind = function (decorated, container, $container) {
    var self = this;

    var resultsId = container.id + '-results';

    decorated.call(this, container, $container);

    this.$search.on('keydown', function (evt) {
      self.trigger('keypress', evt);

      self._keyUpPrevented = evt.isDefaultPrevented();
    });

    // Workaround for browsers which do not support the \`input\` event
    // This will prevent double-triggering of events for browsers which support
    // both the \`keyup\` and \`input\` events.
    this.$search.on('input', function (evt) {
      // Unbind the duplicated \`keyup\` event
      $(this).off('keyup');
    });

    this.$search.on('keyup input', function (evt) {
      self.handleSearch(evt);
    });

    container.on('open', function () {
      self.$search[0].setAttribute('tabindex', 0);
      self.$search[0].setAttribute('aria-controls', resultsId);

      self.$search.trigger('focus');

      window.setTimeout(function () {
        self.$search.trigger('focus');
      }, 0);
    });

    container.on('close', function () {
      self.$search[0].setAttribute('tabindex', -1);
      self.$search[0].removeAttribute('aria-controls');
      self.$search[0].removeAttribute('aria-activedescendant');

      self.$search.val('');
      self.$search.trigger('blur');
    });

    container.on('focus', function () {
      if (!container.isOpen()) {
        self.$search.trigger('focus');
      }
    });

    container.on('results:all', function (params) {
      if (params.query.term == null || params.query.term === '') {
        var showSearch = self.showSearch(params);

        if (showSearch) {
          self.$searchContainer[0].classList.remove('select2-search--hide');
        } else {
          self.$searchContainer[0].classList.add('select2-search--hide');
        }
      }
    });

    container.on('results:focus', function (params) {
      if (params.data._resultId) {
        self.$search[0]
          .setAttribute('aria-activedescendant', params.data._resultId);
      } else {
        self.$search[0].removeAttribute('aria-activedescendant');
      }
    });
  };

  Search.prototype.handleSearch = function (evt) {
    if (!this._keyUpPrevented) {
      var input = this.$search.val();

      this.trigger('query', {
        term: input
      });
    }

    this._keyUpPrevented = false;
  };

  Search.prototype.showSearch = function (_, params) {
    return true;
  };

  return Search;
});

S2.define('select2/dropdown/hidePlaceholder',[

], function () {
  function HidePlaceholder (decorated, $element, options, dataAdapter) {
    this.placeholder = this.normalizePlaceholder(options.get('placeholder'));

    decorated.call(this, $element, options, dataAdapter);
  }

  HidePlaceholder.prototype.append = function (decorated, data) {
    data.results = this.removePlaceholder(data.results);

    decorated.call(this, data);
  };

  HidePlaceholder.prototype.normalizePlaceholder = function (_, placeholder) {
    if (typeof placeholder !== 'object') {
      placeholder = {
        id: '',
        text: placeholder
      };
    }

    return placeholder;
  };

  HidePlaceholder.prototype.removePlaceholder = function (_, data) {
    var modifiedData = data.slice(0);

    for (var d = data.length - 1; d >= 0; d--) {
      var item = data[d];

      if (this.placeholder.id === item.id) {
        modifiedData.splice(d, 1);
      }
    }

    return modifiedData;
  };

  return HidePlaceholder;
});

S2.define('select2/dropdown/infiniteScroll',[
  'jquery'
], function ($) {
  function InfiniteScroll (decorated, $element, options, dataAdapter) {
    this.lastParams = {};

    decorated.call(this, $element, options, dataAdapter);

    this.$loadingMore = this.createLoadingMore();
    this.loading = false;
  }

  InfiniteScroll.prototype.append = function (decorated, data) {
    this.$loadingMore.remove();
    this.loading = false;

    decorated.call(this, data);

    if (this.showLoadingMore(data)) {
      this.$results.append(this.$loadingMore);
      this.loadMoreIfNeeded();
    }
  };

  InfiniteScroll.prototype.bind = function (decorated, container, $container) {
    var self = this;

    decorated.call(this, container, $container);

    container.on('query', function (params) {
      self.lastParams = params;
      self.loading = true;
    });

    container.on('query:append', function (params) {
      self.lastParams = params;
      self.loading = true;
    });

    this.$results.on('scroll', this.loadMoreIfNeeded.bind(this));
  };

  InfiniteScroll.prototype.loadMoreIfNeeded = function () {
    var isLoadMoreVisible = $.contains(
      document.documentElement,
      this.$loadingMore[0]
    );

    if (this.loading || !isLoadMoreVisible) {
      return;
    }

    var currentOffset = this.$results.offset().top +
      this.$results.outerHeight(false);
    var loadingMoreOffset = this.$loadingMore.offset().top +
      this.$loadingMore.outerHeight(false);

    if (currentOffset + 50 >= loadingMoreOffset) {
      this.loadMore();
    }
  };

  InfiniteScroll.prototype.loadMore = function () {
    this.loading = true;

    var params = $.extend({}, {page: 1}, this.lastParams);

    params.page++;

    this.trigger('query:append', params);
  };

  InfiniteScroll.prototype.showLoadingMore = function (_, data) {
    return data.pagination && data.pagination.more;
  };

  InfiniteScroll.prototype.createLoadingMore = function () {
    var $option = $(
      '<li ' +
      'class="select2-results__option select2-results__option--load-more"' +
      'role="option" aria-disabled="true"></li>'
    );

    var message = this.options.get('translations').get('loadingMore');

    $option.html(message(this.lastParams));

    return $option;
  };

  return InfiniteScroll;
});

S2.define('select2/dropdown/attachBody',[
  'jquery',
  '../utils'
], function ($, Utils) {
  function AttachBody (decorated, $element, options) {
    this.$dropdownParent = $(options.get('dropdownParent') || document.body);

    decorated.call(this, $element, options);
  }

  AttachBody.prototype.bind = function (decorated, container, $container) {
    var self = this;

    decorated.call(this, container, $container);

    container.on('open', function () {
      self._showDropdown();
      self._attachPositioningHandler(container);

      // Must bind after the results handlers to ensure correct sizing
      self._bindContainerResultHandlers(container);
    });

    container.on('close', function () {
      self._hideDropdown();
      self._detachPositioningHandler(container);
    });

    this.$dropdownContainer.on('mousedown', function (evt) {
      evt.stopPropagation();
    });
  };

  AttachBody.prototype.destroy = function (decorated) {
    decorated.call(this);

    this.$dropdownContainer.remove();
  };

  AttachBody.prototype.position = function (decorated, $dropdown, $container) {
    // Clone all of the container classes
    $dropdown[0].setAttribute('class', $container[0].getAttribute('class'));

    $dropdown[0].classList.remove('select2');
    $dropdown[0].classList.add('select2-container--open');

    $dropdown.css({
      position: 'absolute',
      top: -999999
    });

    this.$container = $container;
  };

  AttachBody.prototype.render = function (decorated) {
    var $container = $('<span></span>');

    var $dropdown = decorated.call(this);
    $container.append($dropdown);

    this.$dropdownContainer = $container;

    return $container;
  };

  AttachBody.prototype._hideDropdown = function (decorated) {
    this.$dropdownContainer.detach();
  };

  AttachBody.prototype._bindContainerResultHandlers =
      function (decorated, container) {

    // These should only be bound once
    if (this._containerResultsHandlersBound) {
      return;
    }

    var self = this;

    container.on('results:all', function () {
      self._positionDropdown();
      self._resizeDropdown();
    });

    container.on('results:append', function () {
      self._positionDropdown();
      self._resizeDropdown();
    });

    container.on('results:message', function () {
      self._positionDropdown();
      self._resizeDropdown();
    });

    container.on('select', function () {
      self._positionDropdown();
      self._resizeDropdown();
    });

    container.on('unselect', function () {
      self._positionDropdown();
      self._resizeDropdown();
    });

    this._containerResultsHandlersBound = true;
  };

  AttachBody.prototype._attachPositioningHandler =
      function (decorated, container) {
    var self = this;

    var scrollEvent = 'scroll.select2.' + container.id;
    var resizeEvent = 'resize.select2.' + container.id;
    var orientationEvent = 'orientationchange.select2.' + container.id;

    var $watchers = this.$container.parents().filter(Utils.hasScroll);
    $watchers.each(function () {
      Utils.StoreData(this, 'select2-scroll-position', {
        x: $(this).scrollLeft(),
        y: $(this).scrollTop()
      });
    });

    $watchers.on(scrollEvent, function (ev) {
      var position = Utils.GetData(this, 'select2-scroll-position');
      $(this).scrollTop(position.y);
    });

    $(window).on(scrollEvent + ' ' + resizeEvent + ' ' + orientationEvent,
      function (e) {
      self._positionDropdown();
      self._resizeDropdown();
    });
  };

  AttachBody.prototype._detachPositioningHandler =
      function (decorated, container) {
    var scrollEvent = 'scroll.select2.' + container.id;
    var resizeEvent = 'resize.select2.' + container.id;
    var orientationEvent = 'orientationchange.select2.' + container.id;

    var $watchers = this.$container.parents().filter(Utils.hasScroll);
    $watchers.off(scrollEvent);

    $(window).off(scrollEvent + ' ' + resizeEvent + ' ' + orientationEvent);
  };

  AttachBody.prototype._positionDropdown = function () {
    var $window = $(window);

    var isCurrentlyAbove = this.$dropdown[0].classList
      .contains('select2-dropdown--above');
    var isCurrentlyBelow = this.$dropdown[0].classList
      .contains('select2-dropdown--below');

    var newDirection = null;

    var offset = this.$container.offset();

    offset.bottom = offset.top + this.$container.outerHeight(false);

    var container = {
      height: this.$container.outerHeight(false)
    };

    container.top = offset.top;
    container.bottom = offset.top + container.height;

    var dropdown = {
      height: this.$dropdown.outerHeight(false)
    };

    var viewport = {
      top: $window.scrollTop(),
      bottom: $window.scrollTop() + $window.height()
    };

    var enoughRoomAbove = viewport.top < (offset.top - dropdown.height);
    var enoughRoomBelow = viewport.bottom > (offset.bottom + dropdown.height);

    var css = {
      left: offset.left,
      top: container.bottom
    };

    // Determine what the parent element is to use for calculating the offset
    var $offsetParent = this.$dropdownParent;

    // For statically positioned elements, we need to get the element
    // that is determining the offset
    if ($offsetParent.css('position') === 'static') {
      $offsetParent = $offsetParent.offsetParent();
    }

    var parentOffset = {
      top: 0,
      left: 0
    };

    if (
      $.contains(document.body, $offsetParent[0]) ||
      $offsetParent[0].isConnected
      ) {
      parentOffset = $offsetParent.offset();
    }

    css.top -= parentOffset.top;
    css.left -= parentOffset.left;

    if (!isCurrentlyAbove && !isCurrentlyBelow) {
      newDirection = 'below';
    }

    if (!enoughRoomBelow && enoughRoomAbove && !isCurrentlyAbove) {
      newDirection = 'above';
    } else if (!enoughRoomAbove && enoughRoomBelow && isCurrentlyAbove) {
      newDirection = 'below';
    }

    if (newDirection == 'above' ||
      (isCurrentlyAbove && newDirection !== 'below')) {
      css.top = container.top - parentOffset.top - dropdown.height;
    }

    if (newDirection != null) {
      this.$dropdown[0].classList.remove('select2-dropdown--below');
      this.$dropdown[0].classList.remove('select2-dropdown--above');
      this.$dropdown[0].classList.add('select2-dropdown--' + newDirection);

      this.$container[0].classList.remove('select2-container--below');
      this.$container[0].classList.remove('select2-container--above');
      this.$container[0].classList.add('select2-container--' + newDirection);
    }

    this.$dropdownContainer.css(css);
  };

  AttachBody.prototype._resizeDropdown = function () {
    var css = {
      width: this.$container.outerWidth(false) + 'px'
    };

    if (this.options.get('dropdownAutoWidth')) {
      css.minWidth = css.width;
      css.position = 'relative';
      css.width = 'auto';
    }

    this.$dropdown.css(css);
  };

  AttachBody.prototype._showDropdown = function (decorated) {
    this.$dropdownContainer.appendTo(this.$dropdownParent);

    this._positionDropdown();
    this._resizeDropdown();
  };

  return AttachBody;
});

S2.define('select2/dropdown/minimumResultsForSearch',[

], function () {
  function countResults (data) {
    var count = 0;

    for (var d = 0; d < data.length; d++) {
      var item = data[d];

      if (item.children) {
        count += countResults(item.children);
      } else {
        count++;
      }
    }

    return count;
  }

  function MinimumResultsForSearch (decorated, $element, options, dataAdapter) {
    this.minimumResultsForSearch = options.get('minimumResultsForSearch');

    if (this.minimumResultsForSearch < 0) {
      this.minimumResultsForSearch = Infinity;
    }

    decorated.call(this, $element, options, dataAdapter);
  }

  MinimumResultsForSearch.prototype.showSearch = function (decorated, params) {
    if (countResults(params.data.results) < this.minimumResultsForSearch) {
      return false;
    }

    return decorated.call(this, params);
  };

  return MinimumResultsForSearch;
});

S2.define('select2/dropdown/selectOnClose',[
  '../utils'
], function (Utils) {
  function SelectOnClose () { }

  SelectOnClose.prototype.bind = function (decorated, container, $container) {
    var self = this;

    decorated.call(this, container, $container);

    container.on('close', function (params) {
      self._handleSelectOnClose(params);
    });
  };

  SelectOnClose.prototype._handleSelectOnClose = function (_, params) {
    if (params && params.originalSelect2Event != null) {
      var event = params.originalSelect2Event;

      // Don't select an item if the close event was triggered from a select or
      // unselect event
      if (event._type === 'select' || event._type === 'unselect') {
        return;
      }
    }

    var $highlightedResults = this.getHighlightedResults();

    // Only select highlighted results
    if ($highlightedResults.length < 1) {
      return;
    }

    var data = Utils.GetData($highlightedResults[0], 'data');

    // Don't re-select already selected resulte
    if (
      (data.element != null && data.element.selected) ||
      (data.element == null && data.selected)
    ) {
      return;
    }

    this.trigger('select', {
        data: data
    });
  };

  return SelectOnClose;
});

S2.define('select2/dropdown/closeOnSelect',[

], function () {
  function CloseOnSelect () { }

  CloseOnSelect.prototype.bind = function (decorated, container, $container) {
    var self = this;

    decorated.call(this, container, $container);

    container.on('select', function (evt) {
      self._selectTriggered(evt);
    });

    container.on('unselect', function (evt) {
      self._selectTriggered(evt);
    });
  };

  CloseOnSelect.prototype._selectTriggered = function (_, evt) {
    var originalEvent = evt.originalEvent;

    // Don't close if the control key is being held
    if (originalEvent && (originalEvent.ctrlKey || originalEvent.metaKey)) {
      return;
    }

    this.trigger('close', {
      originalEvent: originalEvent,
      originalSelect2Event: evt
    });
  };

  return CloseOnSelect;
});

S2.define('select2/dropdown/dropdownCss',[
  '../utils'
], function (Utils) {
  function DropdownCSS () { }

  DropdownCSS.prototype.render = function (decorated) {
    var $dropdown = decorated.call(this);

    var dropdownCssClass = this.options.get('dropdownCssClass') || '';

    if (dropdownCssClass.indexOf(':all:') !== -1) {
      dropdownCssClass = dropdownCssClass.replace(':all:', '');

      Utils.copyNonInternalCssClasses($dropdown[0], this.$element[0]);
    }

    dropdownCssClass.trim().split(' ').forEach(function(cssClass) {
      if(cssClass.length > 0) {
        $dropdown[0].classList.add(cssClass);
      }
    });

    return $dropdown;
  };

  return DropdownCSS;
});

S2.define('select2/dropdown/tagsSearchHighlight',[
  '../utils'
], function (Utils) {
  function TagsSearchHighlight () { }

  TagsSearchHighlight.prototype.highlightFirstItem = function (decorated) {
    var $options = this.$results
    .find(
      '.select2-results__option--selectable' +
      ':not(.select2-results__option--selected)'
    );

    if ($options.length > 0) {
      var $firstOption = $options.first();
      var data = Utils.GetData($firstOption[0], 'data');
      var firstElement = data.element;

      if (firstElement && firstElement.getAttribute) {
        if (firstElement.getAttribute('data-select2-tag') === 'true') {
          $firstOption.trigger('mouseenter');

          return;
        }
      }
    }

    decorated.call(this);
  };

  return TagsSearchHighlight;
});

S2.define('select2/i18n/en',[],function () {
  // English
  return {
    errorLoading: function () {
      return 'The results could not be loaded.';
    },
    inputTooLong: function (args) {
      var overChars = args.input.length - args.maximum;

      var message = 'Please delete ' + overChars + ' character';

      if (overChars != 1) {
        message += 's';
      }

      return message;
    },
    inputTooShort: function (args) {
      var remainingChars = args.minimum - args.input.length;

      var message = 'Please enter ' + remainingChars + ' or more characters';

      return message;
    },
    loadingMore: function () {
      return 'Loading more results…';
    },
    maximumSelected: function (args) {
      var message = 'You can only select ' + args.maximum + ' item';

      if (args.maximum != 1) {
        message += 's';
      }

      return message;
    },
    noResults: function () {
      return 'No results found';
    },
    searching: function () {
      return 'Searching…';
    },
    removeAllItems: function () {
      return 'Remove all items';
    },
    removeItem: function () {
      return 'Remove item';
    },
    search: function() {
      return 'Search';
    }
  };
});

S2.define('select2/defaults',[
  'jquery',

  './results',

  './selection/single',
  './selection/multiple',
  './selection/placeholder',
  './selection/allowClear',
  './selection/search',
  './selection/selectionCss',
  './selection/eventRelay',

  './utils',
  './translation',
  './diacritics',

  './data/select',
  './data/array',
  './data/ajax',
  './data/tags',
  './data/tokenizer',
  './data/minimumInputLength',
  './data/maximumInputLength',
  './data/maximumSelectionLength',

  './dropdown',
  './dropdown/search',
  './dropdown/hidePlaceholder',
  './dropdown/infiniteScroll',
  './dropdown/attachBody',
  './dropdown/minimumResultsForSearch',
  './dropdown/selectOnClose',
  './dropdown/closeOnSelect',
  './dropdown/dropdownCss',
  './dropdown/tagsSearchHighlight',

  './i18n/en'
], function ($,

             ResultsList,

             SingleSelection, MultipleSelection, Placeholder, AllowClear,
             SelectionSearch, SelectionCSS, EventRelay,

             Utils, Translation, DIACRITICS,

             SelectData, ArrayData, AjaxData, Tags, Tokenizer,
             MinimumInputLength, MaximumInputLength, MaximumSelectionLength,

             Dropdown, DropdownSearch, HidePlaceholder, InfiniteScroll,
             AttachBody, MinimumResultsForSearch, SelectOnClose, CloseOnSelect,
             DropdownCSS, TagsSearchHighlight,

             EnglishTranslation) {
  function Defaults () {
    this.reset();
  }

  Defaults.prototype.apply = function (options) {
    options = $.extend(true, {}, this.defaults, options);

    if (options.dataAdapter == null) {
      if (options.ajax != null) {
        options.dataAdapter = AjaxData;
      } else if (options.data != null) {
        options.dataAdapter = ArrayData;
      } else {
        options.dataAdapter = SelectData;
      }

      if (options.minimumInputLength > 0) {
        options.dataAdapter = Utils.Decorate(
          options.dataAdapter,
          MinimumInputLength
        );
      }

      if (options.maximumInputLength > 0) {
        options.dataAdapter = Utils.Decorate(
          options.dataAdapter,
          MaximumInputLength
        );
      }

      if (options.maximumSelectionLength > 0) {
        options.dataAdapter = Utils.Decorate(
          options.dataAdapter,
          MaximumSelectionLength
        );
      }

      if (options.tags) {
        options.dataAdapter = Utils.Decorate(options.dataAdapter, Tags);
      }

      if (options.tokenSeparators != null || options.tokenizer != null) {
        options.dataAdapter = Utils.Decorate(
          options.dataAdapter,
          Tokenizer
        );
      }
    }

    if (options.resultsAdapter == null) {
      options.resultsAdapter = ResultsList;

      if (options.ajax != null) {
        options.resultsAdapter = Utils.Decorate(
          options.resultsAdapter,
          InfiniteScroll
        );
      }

      if (options.placeholder != null) {
        options.resultsAdapter = Utils.Decorate(
          options.resultsAdapter,
          HidePlaceholder
        );
      }

      if (options.selectOnClose) {
        options.resultsAdapter = Utils.Decorate(
          options.resultsAdapter,
          SelectOnClose
        );
      }

      if (options.tags) {
        options.resultsAdapter = Utils.Decorate(
          options.resultsAdapter,
          TagsSearchHighlight
        );
      }
    }

    if (options.dropdownAdapter == null) {
      if (options.multiple) {
        options.dropdownAdapter = Dropdown;
      } else {
        var SearchableDropdown = Utils.Decorate(Dropdown, DropdownSearch);

        options.dropdownAdapter = SearchableDropdown;
      }

      if (options.minimumResultsForSearch !== 0) {
        options.dropdownAdapter = Utils.Decorate(
          options.dropdownAdapter,
          MinimumResultsForSearch
        );
      }

      if (options.closeOnSelect) {
        options.dropdownAdapter = Utils.Decorate(
          options.dropdownAdapter,
          CloseOnSelect
        );
      }

      if (options.dropdownCssClass != null) {
        options.dropdownAdapter = Utils.Decorate(
          options.dropdownAdapter,
          DropdownCSS
        );
      }

      options.dropdownAdapter = Utils.Decorate(
        options.dropdownAdapter,
        AttachBody
      );
    }

    if (options.selectionAdapter == null) {
      if (options.multiple) {
        options.selectionAdapter = MultipleSelection;
      } else {
        options.selectionAdapter = SingleSelection;
      }

      // Add the placeholder mixin if a placeholder was specified
      if (options.placeholder != null) {
        options.selectionAdapter = Utils.Decorate(
          options.selectionAdapter,
          Placeholder
        );
      }

      if (options.allowClear) {
        options.selectionAdapter = Utils.Decorate(
          options.selectionAdapter,
          AllowClear
        );
      }

      if (options.multiple) {
        options.selectionAdapter = Utils.Decorate(
          options.selectionAdapter,
          SelectionSearch
        );
      }

      if (options.selectionCssClass != null) {
        options.selectionAdapter = Utils.Decorate(
          options.selectionAdapter,
          SelectionCSS
        );
      }

      options.selectionAdapter = Utils.Decorate(
        options.selectionAdapter,
        EventRelay
      );
    }

    // If the defaults were not previously applied from an element, it is
    // possible for the language option to have not been resolved
    options.language = this._resolveLanguage(options.language);

    // Always fall back to English since it will always be complete
    options.language.push('en');

    var uniqueLanguages = [];

    for (var l = 0; l < options.language.length; l++) {
      var language = options.language[l];

      if (uniqueLanguages.indexOf(language) === -1) {
        uniqueLanguages.push(language);
      }
    }

    options.language = uniqueLanguages;

    options.translations = this._processTranslations(
      options.language,
      options.debug
    );

    return options;
  };

  Defaults.prototype.reset = function () {
    function stripDiacritics (text) {
      // Used 'uni range + named function' from http://jsperf.com/diacritics/18
      function match(a) {
        return DIACRITICS[a] || a;
      }

      return text.replace(/[^\\u0000-\\u007E]/g, match);
    }

    function matcher (params, data) {
      // Always return the object if there is nothing to compare
      if (params.term == null || params.term.trim() === '') {
        return data;
      }

      // Do a recursive check for options with children
      if (data.children && data.children.length > 0) {
        // Clone the data object if there are children
        // This is required as we modify the object to remove any non-matches
        var match = $.extend(true, {}, data);

        // Check each child of the option
        for (var c = data.children.length - 1; c >= 0; c--) {
          var child = data.children[c];

          var matches = matcher(params, child);

          // If there wasn't a match, remove the object in the array
          if (matches == null) {
            match.children.splice(c, 1);
          }
        }

        // If any children matched, return the new object
        if (match.children.length > 0) {
          return match;
        }

        // If there were no matching children, check just the plain object
        return matcher(params, match);
      }

      var original = stripDiacritics(data.text).toUpperCase();
      var term = stripDiacritics(params.term).toUpperCase();

      // Check if the text contains the term
      if (original.indexOf(term) > -1) {
        return data;
      }

      // If it doesn't contain the term, don't return anything
      return null;
    }

    this.defaults = {
      amdLanguageBase: './i18n/',
      autocomplete: 'off',
      closeOnSelect: true,
      debug: false,
      dropdownAutoWidth: false,
      escapeMarkup: Utils.escapeMarkup,
      language: {},
      matcher: matcher,
      minimumInputLength: 0,
      maximumInputLength: 0,
      maximumSelectionLength: 0,
      minimumResultsForSearch: 0,
      selectOnClose: false,
      scrollAfterSelect: false,
      sorter: function (data) {
        return data;
      },
      templateResult: function (result) {
        return result.text;
      },
      templateSelection: function (selection) {
        return selection.text;
      },
      theme: 'default',
      width: 'resolve'
    };
  };

  Defaults.prototype.applyFromElement = function (options, $element) {
    var optionLanguage = options.language;
    var defaultLanguage = this.defaults.language;
    var elementLanguage = $element[0].lang;
    var elementClosest = $element.closest('[lang]');
    var parentLanguage = elementClosest[0] ? elementClosest[0].lang : null;

    var languages = Array.prototype.concat.call(
      this._resolveLanguage(elementLanguage),
      this._resolveLanguage(optionLanguage),
      this._resolveLanguage(defaultLanguage),
      this._resolveLanguage(parentLanguage)
    );

    options.language = languages;

    return options;
  };

  Defaults.prototype._resolveLanguage = function (language) {
    if (!language) {
      return [];
    }

    if ($.isEmptyObject(language)) {
      return [];
    }

    if ($.isPlainObject(language)) {
      return [language];
    }

    var languages;

    if (!Array.isArray(language)) {
      languages = [language];
    } else {
      languages = language;
    }

    var resolvedLanguages = [];

    for (var l = 0; l < languages.length; l++) {
      resolvedLanguages.push(languages[l]);

      if (typeof languages[l] === 'string' && languages[l].indexOf('-') > 0) {
        // Extract the region information if it is included
        var languageParts = languages[l].split('-');
        var baseLanguage = languageParts[0];

        resolvedLanguages.push(baseLanguage);
      }
    }

    return resolvedLanguages;
  };

  Defaults.prototype._processTranslations = function (languages, debug) {
    var translations = new Translation();

    for (var l = 0; l < languages.length; l++) {
      var languageData = new Translation();

      var language = languages[l];

      if (typeof language === 'string') {
        try {
          // Try to load it with the original name
          languageData = Translation.loadPath(language);
        } catch (e) {
          try {
            // If we couldn't load it, check if it wasn't the full path
            language = this.defaults.amdLanguageBase + language;
            languageData = Translation.loadPath(language);
          } catch (ex) {
            // The translation could not be loaded at all. Sometimes this is
            // because of a configuration problem, other times this can be
            // because of how Select2 helps load all possible translation files
            if (debug && window.console && console.warn) {
              console.warn(
                'Select2: The language file for "' + language + '" could ' +
                'not be automatically loaded. A fallback will be used instead.'
              );
            }
          }
        }
      } else if ($.isPlainObject(language)) {
        languageData = new Translation(language);
      } else {
        languageData = language;
      }

      translations.extend(languageData);
    }

    return translations;
  };

  Defaults.prototype.set = function (key, value) {
    function upperCaseLetter(_, letter) {
      return letter.toUpperCase();
    }
    var camelKey = key.replace(/-([a-z])/g, upperCaseLetter);

    var data = {};
    data[camelKey] = value;

    var convertedData = Utils._convertData(data);

    $.extend(true, this.defaults, convertedData);
  };

  var defaults = new Defaults();

  return defaults;
});

S2.define('select2/options',[
  'jquery',
  './defaults',
  './utils'
], function ($, Defaults, Utils) {
  function Options (options, $element) {
    this.options = options;

    if ($element != null) {
      this.fromElement($element);
    }

    if ($element != null) {
      this.options = Defaults.applyFromElement(this.options, $element);
    }

    this.options = Defaults.apply(this.options);
  }

  Options.prototype.fromElement = function ($e) {
    var excludedData = ['select2'];

    if (this.options.multiple == null) {
      this.options.multiple = $e[0].multiple;
    }

    if (this.options.disabled == null) {
      this.options.disabled = $e[0].disabled;
    }

    if (this.options.autocomplete == null && $e[0].autocomplete) {
      this.options.autocomplete = $e[0].autocomplete;
    }

    if (this.options.dir === null) {
      var dirValue = $e[0].getAttribute('dir');

      if (dirValue) {
        this.options.dir = dirValue;
      } else {
        var closestDirValue = $e.closest('[dir]').getAttribute('dir');

        if (closestDirValue) {
          this.options.dir = closestDirValue;
        } else {
          this.options.dir = 'ltr';
        }
      }
    }

    $e[0].disabled = this.options.disabled;
    $e[0].multiple = this.options.multiple;

    if (Utils.GetData($e[0], 'select2Tags')) {
      if (this.options.debug && window.console && console.warn) {
        console.warn(
          'Select2: The \`data-select2-tags\` attribute has been changed to ' +
          'use the \`data-data\` and \`data-tags="true"\` attributes and will be ' +
          'removed in future versions of Select2.'
        );
      }

      Utils.StoreData($e[0], 'data', Utils.GetData($e[0], 'select2Tags'));
      Utils.StoreData($e[0], 'tags', true);
    }

    if (Utils.GetData($e[0], 'ajaxUrl')) {
      if (this.options.debug && window.console && console.warn) {
        console.warn(
          'Select2: The \`data-ajax-url\` attribute has been changed to ' +
          '\`data-ajax--url\` and support for the old attribute will be removed' +
          ' in future versions of Select2.'
        );
      }

      $e[0].setAttribute('ajax--url', Utils.GetData($e[0], 'ajaxUrl'));
      Utils.StoreData($e[0], 'ajax-Url', Utils.GetData($e[0], 'ajaxUrl'));
    }

    var dataset = {};

    function upperCaseLetter(_, letter) {
      return letter.toUpperCase();
    }

    // Pre-load all of the attributes which are prefixed with \`data-\`
    for (var attr = 0; attr < $e[0].attributes.length; attr++) {
      var attributeName = $e[0].attributes[attr].name;
      var prefix = 'data-';

      if (attributeName.substr(0, prefix.length) == prefix) {
        // Get the contents of the attribute after \`data-\`
        var dataName = attributeName.substring(prefix.length);

        // Get the data contents from the consistent source
        // This is more than likely the jQuery data helper
        var dataValue = Utils.GetData($e[0], dataName);

        // camelCase the attribute name to match the spec
        var camelDataName = dataName.replace(/-([a-z])/g, upperCaseLetter);

        // Store the data attribute contents into the dataset since
        dataset[camelDataName] = dataValue;
      }
    }

    // Prefer the element's \`dataset\` attribute if it exists
    // jQuery 1.x does not correctly handle data attributes with multiple dashes
    if ($.fn.jquery && $.fn.jquery.substr(0, 2) == '1.' && $e[0].dataset) {
      dataset = $.extend(true, {}, $e[0].dataset, dataset);
    }

    // Prefer our internal data cache if it exists
    var data = $.extend(true, {}, Utils.GetData($e[0]), dataset);

    data = Utils._convertData(data);

    for (var key in data) {
      if (excludedData.indexOf(key) > -1) {
        continue;
      }

      if ($.isPlainObject(this.options[key])) {
        $.extend(this.options[key], data[key]);
      } else {
        this.options[key] = data[key];
      }
    }

    return this;
  };

  Options.prototype.get = function (key) {
    return this.options[key];
  };

  Options.prototype.set = function (key, val) {
    this.options[key] = val;
  };

  return Options;
});

S2.define('select2/core',[
  'jquery',
  './options',
  './utils',
  './keys'
], function ($, Options, Utils, KEYS) {
  var Select2 = function ($element, options) {
    if (Utils.GetData($element[0], 'select2') != null) {
      Utils.GetData($element[0], 'select2').destroy();
    }

    this.$element = $element;

    this.id = this._generateId($element);

    options = options || {};

    this.options = new Options(options, $element);

    Select2.__super__.constructor.call(this);

    // Set up the tabindex

    var tabindex = $element[0].getAttribute('tabindex') || 0;
    Utils.StoreData($element[0], 'old-tabindex', tabindex);
    $element[0].setAttribute('tabindex', '-1');

    // Set up containers and adapters

    var DataAdapter = this.options.get('dataAdapter');
    this.dataAdapter = new DataAdapter($element, this.options);

    var $container = this.render();

    this._placeContainer($container);

    var SelectionAdapter = this.options.get('selectionAdapter');
    this.selection = new SelectionAdapter($element, this.options);
    this.$selection = this.selection.render();

    this.selection.position(this.$selection, $container);

    var DropdownAdapter = this.options.get('dropdownAdapter');
    this.dropdown = new DropdownAdapter($element, this.options);
    this.$dropdown = this.dropdown.render();

    this.dropdown.position(this.$dropdown, $container);

    var ResultsAdapter = this.options.get('resultsAdapter');
    this.results = new ResultsAdapter($element, this.options, this.dataAdapter);
    this.$results = this.results.render();

    this.results.position(this.$results, this.$dropdown);

    // Bind events

    var self = this;

    // Bind the container to all of the adapters
    this._bindAdapters();

    // Register any DOM event handlers
    this._registerDomEvents();

    // Register any internal event handlers
    this._registerDataEvents();
    this._registerSelectionEvents();
    this._registerDropdownEvents();
    this._registerResultsEvents();
    this._registerEvents();

    // Set the initial state
    this.dataAdapter.current(function (initialData) {
      self.trigger('selection:update', {
        data: initialData
      });
    });

    // Hide the original select
    $element[0].classList.add('select2-hidden-accessible');
    $element[0].setAttribute('aria-hidden', 'true');

    // Synchronize any monitored attributes
    this._syncAttributes();

    Utils.StoreData($element[0], 'select2', this);

    // Ensure backwards compatibility with $element.data('select2').
    $element.data('select2', this);
  };

  Utils.Extend(Select2, Utils.Observable);

  Select2.prototype._generateId = function ($element) {
    var id = '';
    var element = $element[0];

    if (element != null && element.getAttribute('id') != null) {
      id = element.getAttribute('id');
    } else if (element != null && element.getAttribute('name') != null) {
      id = element.getAttribute('name') + '-' + Utils.generateChars(2);
    } else {
      id = Utils.generateChars(4);
    }

    id = id.replace(/(:|\\.|\\[|\\]|,)/g, '');
    id = 'select2-' + id;

    return id;
  };

  Select2.prototype._placeContainer = function ($container) {
    $container.insertAfter(this.$element);

    var width = this._resolveWidth(this.$element, this.options.get('width'));

    if (width != null) {
      $container.css('width', width);
    }
  };

  Select2.prototype._resolveWidth = function ($element, method) {
    var WIDTH = /^width:(([-+]?([0-9]*\\.)?[0-9]+)(px|em|ex|%|in|cm|mm|pt|pc))/i;

    if (method == 'resolve') {
      var styleWidth = this._resolveWidth($element, 'style');

      if (styleWidth != null) {
        return styleWidth;
      }

      return this._resolveWidth($element, 'element');
    }

    if (method == 'element') {
      var elementWidth = $element.outerWidth(false);

      if (elementWidth <= 0) {
        return 'auto';
      }

      return elementWidth + 'px';
    }

    if (method == 'style') {
      var style = $element[0].getAttribute('style');

      if (typeof(style) !== 'string') {
        return null;
      }

      var attrs = style.split(';');

      for (var i = 0, l = attrs.length; i < l; i = i + 1) {
        var attr = attrs[i].replace(/\\s/g, '');
        var matches = attr.match(WIDTH);

        if (matches !== null && matches.length >= 1) {
          return matches[1];
        }
      }

      return null;
    }

    if (method == 'computedstyle') {
      var computedStyle = window.getComputedStyle($element[0]);

      return computedStyle.width;
    }

    return method;
  };

  Select2.prototype._bindAdapters = function () {
    this.dataAdapter.bind(this, this.$container);
    this.selection.bind(this, this.$container);

    this.dropdown.bind(this, this.$container);
    this.results.bind(this, this.$container);
  };

  Select2.prototype._registerDomEvents = function () {
    var self = this;

    this.$element.on('change.select2', function () {
      self.dataAdapter.current(function (data) {
        self.trigger('selection:update', {
          data: data
        });
      });
    });

    this.$element.on('focus.select2', function (evt) {
      self.trigger('focus', evt);
    });

    this._syncA = Utils.bind(this._syncAttributes, this);
    this._syncS = Utils.bind(this._syncSubtree, this);

    this._observer = new window.MutationObserver(function (mutations) {
      self._syncA();
      self._syncS(mutations);
    });
    this._observer.observe(this.$element[0], {
      attributes: true,
      childList: true,
      subtree: false
    });
  };

  Select2.prototype._registerDataEvents = function () {
    var self = this;

    this.dataAdapter.on('*', function (name, params) {
      self.trigger(name, params);
    });
  };

  Select2.prototype._registerSelectionEvents = function () {
    var self = this;
    var nonRelayEvents = ['toggle', 'focus'];

    this.selection.on('toggle', function () {
      self.toggleDropdown();
    });

    this.selection.on('focus', function (params) {
      self.focus(params);
    });

    this.selection.on('*', function (name, params) {
      if (nonRelayEvents.indexOf(name) !== -1) {
        return;
      }

      self.trigger(name, params);
    });
  };

  Select2.prototype._registerDropdownEvents = function () {
    var self = this;

    this.dropdown.on('*', function (name, params) {
      self.trigger(name, params);
    });
  };

  Select2.prototype._registerResultsEvents = function () {
    var self = this;

    this.results.on('*', function (name, params) {
      self.trigger(name, params);
    });
  };

  Select2.prototype._registerEvents = function () {
    var self = this;

    this.on('open', function () {
      self.$container[0].classList.add('select2-container--open');
    });

    this.on('close', function () {
      self.$container[0].classList.remove('select2-container--open');
    });

    this.on('enable', function () {
      self.$container[0].classList.remove('select2-container--disabled');
    });

    this.on('disable', function () {
      self.$container[0].classList.add('select2-container--disabled');
    });

    this.on('blur', function () {
      self.$container[0].classList.remove('select2-container--focus');
    });

    this.on('query', function (params) {
      if (!self.isOpen()) {
        self.trigger('open', {});
      }

      this.dataAdapter.query(params, function (data) {
        self.trigger('results:all', {
          data: data,
          query: params
        });
      });
    });

    this.on('query:append', function (params) {
      this.dataAdapter.query(params, function (data) {
        self.trigger('results:append', {
          data: data,
          query: params
        });
      });
    });

    this.on('keypress', function (evt) {
      var key = evt.which;

      if (self.isOpen()) {
        if (key === KEYS.ESC || (key === KEYS.UP && evt.altKey)) {
          self.close(evt);

          evt.preventDefault();
        } else if (key === KEYS.ENTER || key === KEYS.TAB) {
          self.trigger('results:select', {});

          evt.preventDefault();
        } else if ((key === KEYS.SPACE && evt.ctrlKey)) {
          self.trigger('results:toggle', {});

          evt.preventDefault();
        } else if (key === KEYS.UP) {
          self.trigger('results:previous', {});

          evt.preventDefault();
        } else if (key === KEYS.DOWN) {
          self.trigger('results:next', {});

          evt.preventDefault();
        }
      } else {
        if (key === KEYS.ENTER || key === KEYS.SPACE ||
            (key === KEYS.DOWN && evt.altKey)) {
          self.open();

          evt.preventDefault();
        }
      }
    });
  };

  Select2.prototype._syncAttributes = function () {
    this.options.set('disabled', this.$element[0].disabled);

    if (this.isDisabled()) {
      if (this.isOpen()) {
        this.close();
      }

      this.trigger('disable', {});
    } else {
      this.trigger('enable', {});
    }
  };

  Select2.prototype._isChangeMutation = function (mutations) {
    var self = this;

    if (mutations.addedNodes && mutations.addedNodes.length > 0) {
      for (var n = 0; n < mutations.addedNodes.length; n++) {
        var node = mutations.addedNodes[n];

        if (node.selected) {
          return true;
        }
      }
    } else if (mutations.removedNodes && mutations.removedNodes.length > 0) {
      return true;
    } else if (Array.isArray(mutations)) {
      return mutations.some(function (mutation) {
        return self._isChangeMutation(mutation);
      });
    }

    return false;
  };

  Select2.prototype._syncSubtree = function (mutations) {
    var changed = this._isChangeMutation(mutations);
    var self = this;

    // Only re-pull the data if we think there is a change
    if (changed) {
      this.dataAdapter.current(function (currentData) {
        self.trigger('selection:update', {
          data: currentData
        });
      });
    }
  };

  /**
   * Override the trigger method to automatically trigger pre-events when
   * there are events that can be prevented.
   */
  Select2.prototype.trigger = function (name, args) {
    var actualTrigger = Select2.__super__.trigger;
    var preTriggerMap = {
      'open': 'opening',
      'close': 'closing',
      'select': 'selecting',
      'unselect': 'unselecting',
      'clear': 'clearing'
    };

    if (args === undefined) {
      args = {};
    }

    if (name in preTriggerMap) {
      var preTriggerName = preTriggerMap[name];
      var preTriggerArgs = {
        prevented: false,
        name: name,
        args: args
      };

      actualTrigger.call(this, preTriggerName, preTriggerArgs);

      if (preTriggerArgs.prevented) {
        args.prevented = true;

        return;
      }
    }

    actualTrigger.call(this, name, args);
  };

  Select2.prototype.toggleDropdown = function () {
    if (this.isDisabled()) {
      return;
    }

    if (this.isOpen()) {
      this.close();
    } else {
      this.open();
    }
  };

  Select2.prototype.open = function () {
    if (this.isOpen()) {
      return;
    }

    if (this.isDisabled()) {
      return;
    }

    this.trigger('query', {});
  };

  Select2.prototype.close = function (evt) {
    if (!this.isOpen()) {
      return;
    }

    this.trigger('close', { originalEvent : evt });
  };

  /**
   * Helper method to abstract the "enabled" (not "disabled") state of this
   * object.
   *
   * @return {true} if the instance is not disabled.
   * @return {false} if the instance is disabled.
   */
  Select2.prototype.isEnabled = function () {
    return !this.isDisabled();
  };

  /**
   * Helper method to abstract the "disabled" state of this object.
   *
   * @return {true} if the disabled option is true.
   * @return {false} if the disabled option is false.
   */
  Select2.prototype.isDisabled = function () {
    return this.options.get('disabled');
  };

  Select2.prototype.isOpen = function () {
    return this.$container[0].classList.contains('select2-container--open');
  };

  Select2.prototype.hasFocus = function () {
    return this.$container[0].classList.contains('select2-container--focus');
  };

  Select2.prototype.focus = function (data) {
    // No need to re-trigger focus events if we are already focused
    if (this.hasFocus()) {
      return;
    }

    this.$container[0].classList.add('select2-container--focus');
    this.trigger('focus', {});
  };

  Select2.prototype.enable = function (args) {
    if (this.options.get('debug') && window.console && console.warn) {
      console.warn(
        'Select2: The \`select2("enable")\` method has been deprecated and will' +
        ' be removed in later Select2 versions. Use $element[0].disabled' +
        ' instead.'
      );
    }

    if (args == null || args.length === 0) {
      args = [true];
    }

    var disabled = !args[0];

    this.$element[0].disabled = disabled;
  };

  Select2.prototype.data = function () {
    if (this.options.get('debug') &&
        arguments.length > 0 && window.console && console.warn) {
      console.warn(
        'Select2: Data can no longer be set using \`select2("data")\`. You ' +
        'should consider setting the value instead using \`$element.val()\`.'
      );
    }

    var data = [];

    this.dataAdapter.current(function (currentData) {
      data = currentData;
    });

    return data;
  };

  Select2.prototype.val = function (args) {
    if (this.options.get('debug') && window.console && console.warn) {
      console.warn(
        'Select2: The \`select2("val")\` method has been deprecated and will be' +
        ' removed in later Select2 versions. Use $element.val() instead.'
      );
    }

    if (args == null || args.length === 0) {
      return this.$element.val();
    }

    var newVal = args[0];

    if (Array.isArray(newVal)) {
      newVal = newVal.map(function (obj) {
        return obj.toString();
      });
    }

    this.$element.val(newVal).trigger('input').trigger('change');
  };

  Select2.prototype.destroy = function () {
    Utils.RemoveData(this.$container[0]);
    this.$container.remove();

    this._observer.disconnect();
    this._observer = null;

    this._syncA = null;
    this._syncS = null;

    this.$element.off('.select2');
    this.$element[0].setAttribute('tabindex',
    Utils.GetData(this.$element[0], 'old-tabindex'));

    this.$element[0].classList.remove('select2-hidden-accessible');
    this.$element[0].setAttribute('aria-hidden', 'false');
    Utils.RemoveData(this.$element[0]);
    this.$element.removeData('select2');

    this.dataAdapter.destroy();
    this.selection.destroy();
    this.dropdown.destroy();
    this.results.destroy();

    this.dataAdapter = null;
    this.selection = null;
    this.dropdown = null;
    this.results = null;
  };

  Select2.prototype.render = function () {
    var $container = $(
      '<span class="select2 select2-container">' +
        '<span class="selection"></span>' +
        '<span class="dropdown-wrapper" aria-hidden="true"></span>' +
      '</span>'
    );

    $container[0].setAttribute('dir', this.options.get('dir'));

    this.$container = $container;

    this.$container[0].classList
      .add('select2-container--' + this.options.get('theme'));

    Utils.StoreData($container[0], 'element', this.$element);

    return $container;
  };

  return Select2;
});

S2.define('jquery-mousewheel',[
  'jquery'
], function ($) {
  // Used to shim jQuery.mousewheel for non-full builds.
  return $;
});

S2.define('jquery.select2',[
  'jquery',
  'jquery-mousewheel',

  './select2/core',
  './select2/defaults',
  './select2/utils'
], function ($, _, Select2, Defaults, Utils) {
  if ($.fn.select2 == null) {
    // All methods that should return the element
    var thisMethods = ['open', 'close', 'destroy'];

    $.fn.select2 = function (options) {
      options = options || {};

      if (typeof options === 'object') {
        this.each(function () {
          var instanceOptions = $.extend(true, {}, options);

          var instance = new Select2($(this), instanceOptions);
        });

        return this;
      } else if (typeof options === 'string') {
        var ret;
        var args = Array.prototype.slice.call(arguments, 1);

        this.each(function () {
          var instance = Utils.GetData(this, 'select2');

          if (instance == null && window.console && console.error) {
            console.error(
              'The select2(\\'' + options + '\\') method was called on an ' +
              'element that is not using Select2.'
            );
          }

          ret = instance[options].apply(instance, args);
        });

        // Check if we should be returning \`this\`
        if (thisMethods.indexOf(options) > -1) {
          return this;
        }

        return ret;
      } else {
        throw new Error('Invalid arguments for Select2: ' + options);
      }
    };
  }

  if ($.fn.select2.defaults == null) {
    $.fn.select2.defaults = Defaults;
  }

  return Select2;
});

  // Return the AMD loader configuration so it can be used outside of this file
  return {
    define: S2.define,
    require: S2.require
  };
}());

  // Autoload the jQuery bindings
  // We know that all of the modules exist above this, so we're safe
  var select2 = S2.require('jquery.select2');

  // Hold the AMD module references on the jQuery function that was just loaded
  // This allows Select2 to use the internal loader outside of this file, such
  // as in the language files.
  jQuery.fn.select2.amd = S2;

  // Return the Select2 instance for anyone who is importing it.
  return select2;
}));
`;new Function("module","require","window","jQuery",src)({},()=>jQuery$1,window,jQuery$1);function initSelect2(){jQuery$1(".fos-select2").select2({placeholder:"Select a fos"})}function initForm(){jQuery$1(document).on("click","#form_reset_button",function(){resetForm(jQuery$1("#filter_form"))});const n=[["selectAll","attributeform-"],["selectAllAllocations","allocationform-"],["selectAll","userform-"],["selectAll","users"],["selectAll","noteform-"],["selectAll","grantform-"],["selectAll","pubform-"],["selectAll","grantdownloadform-"]];for(const e of n)jQuery$1("#"+e[0]).click(function(){jQuery$1("input[name^='"+e[1]+"']").prop("checked",jQuery$1(this).prop("checked"))}),jQuery$1("input[name^='"+e[1]+"']").click(function(){jQuery$1(this).attr("id")!=e[0]&&jQuery$1("#"+e[0]).prop("checked",!1)})}function resetForm(n){n.find("input:text, input:password, input:file, select, textarea").val(""),n.find("input:radio, input:checkbox").removeAttr("checked").removeAttr("selected")}var $$1=jQuery$1,DataTable=function(n,e){if(DataTable.factory(n,e))return DataTable;if(this instanceof DataTable)return $$1(n).DataTable(e);e=n;var t=this,r=e===void 0,a=this.length;return r&&(e={}),this.api=function(){return new _Api(this)},this.each(function(){var o={},s=a>1?_fnExtend(o,e,!0):e,l=0,c,f=this.getAttribute("id"),d=DataTable.defaults,p=$$1(this);if(this.nodeName.toLowerCase()!="table"){_fnLog(null,0,"Non-table node initialisation ("+this.nodeName+")",2);return}s.on&&s.on.options&&_fnListener(p,"options",s.on.options),p.trigger("options.dt",s),_fnCompatOpts(d),_fnCompatCols(d.column),_fnCamelToHungarian(d,d,!0),_fnCamelToHungarian(d.column,d.column,!0),_fnCamelToHungarian(d,$$1.extend(s,_fnEscapeObject(p.data())),!0);var _=DataTable.settings;for(l=0,c=_.length;l<c;l++){var b=_[l];if(b.nTable==this||b.nTHead&&b.nTHead.parentNode==this||b.nTFoot&&b.nTFoot.parentNode==this){var y=s.bRetrieve!==void 0?s.bRetrieve:d.bRetrieve,E=s.bDestroy!==void 0?s.bDestroy:d.bDestroy;if(r||y)return b.oInstance;if(E){new DataTable.Api(b).destroy();break}else{_fnLog(b,0,"Cannot reinitialise DataTable",3);return}}if(b.sTableId==this.id){_.splice(l,1);break}}(f===null||f==="")&&(f="DataTables_Table_"+DataTable.ext._unique++,this.id=f),p.children("colgroup").remove();var C=$$1.extend(!0,{},DataTable.models.oSettings,{sDestroyWidth:p[0].style.width,sInstance:f,sTableId:f,colgroup:$$1("<colgroup>"),fastData:function(re,de,le){return _fnGetCellData(C,re,de,le)}});C.nTable=this,C.oInit=s,_.push(C),C.api=new _Api(C),C.oInstance=t.length===1?t:p.dataTable(),_fnCompatOpts(s),s.aLengthMenu&&!s.iDisplayLength&&(s.iDisplayLength=Array.isArray(s.aLengthMenu[0])?s.aLengthMenu[0][0]:$$1.isPlainObject(s.aLengthMenu[0])?s.aLengthMenu[0].value:s.aLengthMenu[0]),s=_fnExtend($$1.extend(!0,{},d),s),_fnMap(C.oFeatures,s,["bPaginate","bLengthChange","bFilter","bSort","bSortMulti","bInfo","bProcessing","bAutoWidth","bSortClasses","bServerSide","bDeferRender"]),_fnMap(C,s,["ajax","fnFormatNumber","sServerMethod","aaSorting","aaSortingFixed","aLengthMenu","sPaginationType","iStateDuration","bSortCellsTop","iTabIndex","sDom","fnStateLoadCallback","fnStateSaveCallback","renderer","searchDelay","rowId","caption","layout","orderDescReverse","orderIndicators","orderHandler","titleRow","typeDetect","columnTitleTag",["iCookieDuration","iStateDuration"],["oSearch","oPreviousSearch"],["aoSearchCols","aoPreSearchCols"],["iDisplayLength","_iDisplayLength"]]),_fnMap(C.oScroll,s,[["sScrollX","sX"],["sScrollXInner","sXInner"],["sScrollY","sY"],["bScrollCollapse","bCollapse"]]),_fnMap(C.oLanguage,s,"fnInfoCallback"),_fnCallbackReg(C,"aoDrawCallback",s.fnDrawCallback),_fnCallbackReg(C,"aoStateSaveParams",s.fnStateSaveParams),_fnCallbackReg(C,"aoStateLoadParams",s.fnStateLoadParams),_fnCallbackReg(C,"aoStateLoaded",s.fnStateLoaded),_fnCallbackReg(C,"aoRowCallback",s.fnRowCallback),_fnCallbackReg(C,"aoRowCreatedCallback",s.fnCreatedRow),_fnCallbackReg(C,"aoHeaderCallback",s.fnHeaderCallback),_fnCallbackReg(C,"aoFooterCallback",s.fnFooterCallback),_fnCallbackReg(C,"aoInitComplete",s.fnInitComplete),_fnCallbackReg(C,"aoPreDrawCallback",s.fnPreDrawCallback),C.rowIdFn=_fnGetObjectDataFn(s.rowId),s.on&&Object.keys(s.on).forEach(function(re){_fnListener(p,re,s.on[re])}),_fnBrowserDetect(C);var D=C.oClasses;$$1.extend(D,DataTable.ext.classes,s.oClasses),p.addClass(D.table),C.oFeatures.bPaginate||(s.iDisplayStart=0),C.iInitDisplayStart===void 0&&(C.iInitDisplayStart=s.iDisplayStart,C._iDisplayStart=s.iDisplayStart);var M=s.iDeferLoading;if(M!==null){C.deferLoading=!0;var F=Array.isArray(M);C._iRecordsDisplay=F?M[0]:M,C._iRecordsTotal=F?M[1]:M}var P=[],H=this.getElementsByTagName("thead"),B=_fnDetectHeader(C,H[0]);if(s.aoColumns)P=s.aoColumns;else if(B.length)for(l=0,c=B[0].length;l<c;l++)P.push(null);for(l=0,c=P.length;l<c;l++)_fnAddColumn(C);_fnApplyColumnDefs(C,s.aoColumnDefs,P,B,function(re,de){_fnColumnOptions(C,re,de)});var g=p.children("tbody").find("tr:first-child").eq(0);if(g.length){var q=function(re,de){return re.getAttribute("data-"+de)!==null?de:null};$$1(g[0]).children("th, td").each(function(re,de){var le=C.aoColumns[re];if(le||_fnLog(C,0,"Incorrect column count",18),le.mData===re){var $e=q(de,"sort")||q(de,"order"),xe=q(de,"filter")||q(de,"search");($e!==null||xe!==null)&&(le.mData={_:re+".display",sort:$e!==null?re+".@data-"+$e:void 0,type:$e!==null?re+".@data-"+$e:void 0,filter:xe!==null?re+".@data-"+xe:void 0},le._isArrayHost=!0,_fnColumnOptions(C,re))}})}_fnCallbackReg(C,"aoDrawCallback",_fnSaveState);var G=C.oFeatures;if(s.bStateSave&&(G.bStateSave=!0),s.aaSorting===void 0){var Z=C.aaSorting;for(l=0,c=Z.length;l<c;l++)Z[l][1]=C.aoColumns[l].asSorting[0]}_fnSortingClasses(C),_fnCallbackReg(C,"aoDrawCallback",function(){(C.bSorted||_fnDataSource(C)==="ssp"||G.bDeferRender)&&_fnSortingClasses(C)});var te=p.children("caption");C.caption&&(te.length===0&&(te=$$1("<caption/>").prependTo(p)),te.html(C.caption)),te.length&&(te[0]._captionSide=te.css("caption-side"),C.captionNode=te[0]),te.length?C.colgroup.insertAfter(te):C.colgroup.prependTo(C.nTable),H.length===0&&(H=$$1("<thead/>").appendTo(p)),C.nTHead=H[0];var ne=p.children("tbody");ne.length===0&&(ne=$$1("<tbody/>").insertAfter(H)),C.nTBody=ne[0];var Q=p.children("tfoot");Q.length===0&&(Q=$$1("<tfoot/>").appendTo(p)),C.nTFoot=Q[0],C.aiDisplay=C.aiDisplayMaster.slice(),C.bInitialised=!0;var Ee=C.oLanguage;$$1.extend(!0,Ee,s.oLanguage),Ee.sUrl?$$1.ajax({dataType:"json",url:Ee.sUrl,success:function(re){_fnCamelToHungarian(d.oLanguage,re),$$1.extend(!0,Ee,re,C.oInit.oLanguage),_fnCallbackFire(C,null,"i18n",[C],!0),_fnInitialise(C)},error:function(){_fnLog(C,0,"i18n file loading error",21),_fnInitialise(C)}}):(_fnCallbackFire(C,null,"i18n",[C],!0),_fnInitialise(C))}),t=null,this};DataTable.ext=_ext={builder:"-source-",buttons:{},ccContent:{},classes:{},errMode:"alert",escape:{attributes:!1},feature:[],features:{},search:[],selector:{cell:[],column:[],row:[]},legacy:{ajax:null},pager:{},renderer:{pageButton:{},header:{}},order:{},type:{className:{},detect:[],render:{},search:{},order:{}},_unique:0,fnVersionCheck:DataTable.fnVersionCheck,iApiIndex:0,sVersion:DataTable.version};$$1.extend(_ext,{afnFiltering:_ext.search,aTypes:_ext.type.detect,ofnSearch:_ext.type.search,oSort:_ext.type.order,afnSortData:_ext.order,aoFeatures:_ext.feature,oStdClasses:_ext.classes,oPagination:_ext.pager});$$1.extend(DataTable.ext.classes,{container:"dt-container",empty:{row:"dt-empty"},info:{container:"dt-info"},layout:{row:"dt-layout-row",cell:"dt-layout-cell",tableRow:"dt-layout-table",tableCell:"",start:"dt-layout-start",end:"dt-layout-end",full:"dt-layout-full"},length:{container:"dt-length",select:"dt-input"},order:{canAsc:"dt-orderable-asc",canDesc:"dt-orderable-desc",isAsc:"dt-ordering-asc",isDesc:"dt-ordering-desc",none:"dt-orderable-none",position:"sorting_"},processing:{container:"dt-processing"},scrolling:{body:"dt-scroll-body",container:"dt-scroll",footer:{self:"dt-scroll-foot",inner:"dt-scroll-footInner"},header:{self:"dt-scroll-head",inner:"dt-scroll-headInner"}},search:{container:"dt-search",input:"dt-input"},table:"dataTable",tbody:{cell:"",row:""},thead:{cell:"",row:""},tfoot:{cell:"",row:""},paging:{active:"current",button:"dt-paging-button",container:"dt-paging",disabled:"disabled",nav:""}});var _ext,_Api,_api_register,_api_registerPlural,_re_dic={},_re_new_lines=/[\r\n\u2028]/g,_re_html=/<([^>]*>)/g,_max_str_len=Math.pow(2,28),_re_date=/^\d{2,4}[./-]\d{1,2}[./-]\d{1,2}([T ]{1}\d{1,2}[:.]\d{2}([.:]\d{2})?)?$/,_re_escape_regex=new RegExp("(\\"+["/",".","*","+","?","|","(",")","[","]","{","}","\\","$","^","-"].join("|\\")+")","g"),_re_formatted_numeric=/['\u00A0,$£€¥%\u2009\u202F\u20BD\u20a9\u20BArfkɃΞ]/gi,_empty=function(n){return!n||n===!0||n==="-"},_intVal=function(n){var e=parseInt(n,10);return!isNaN(e)&&isFinite(n)?e:null},_numToDecimal=function(n,e){return _re_dic[e]||(_re_dic[e]=new RegExp(_fnEscapeRegex(e),"g")),typeof n=="string"&&e!=="."?n.replace(/\./g,"").replace(_re_dic[e],"."):n},_isNumber=function(n,e,t,r){var a=typeof n,o=a==="string";return a==="number"||a==="bigint"||r&&_empty(n)?!0:(e&&o&&(n=_numToDecimal(n,e)),t&&o&&(n=n.replace(_re_formatted_numeric,"")),!isNaN(parseFloat(n))&&isFinite(n))},_isHtml=function(n){return _empty(n)||typeof n=="string"},_htmlNumeric=function(n,e,t,r){if(r&&_empty(n))return!0;if(typeof n=="string"&&n.match(/<(input|select)/i))return null;var a=_isHtml(n);return a&&_isNumber(_stripHtml(n),e,t,r)?!0:null},_pluck=function(n,e,t){var r=[],a=0,o=n.length;if(t!==void 0)for(;a<o;a++)n[a]&&n[a][e]&&r.push(n[a][e][t]);else for(;a<o;a++)n[a]&&r.push(n[a][e]);return r},_pluck_order=function(n,e,t,r){var a=[],o=0,s=e.length;if(r!==void 0)for(;o<s;o++)n[e[o]]&&n[e[o]][t]&&a.push(n[e[o]][t][r]);else for(;o<s;o++)n[e[o]]&&a.push(n[e[o]][t]);return a},_range=function(n,e){var t=[],r;e===void 0?(e=0,r=n):(r=e,e=n);for(var a=e;a<r;a++)t.push(a);return t},_removeEmpty=function(n){for(var e=[],t=0,r=n.length;t<r;t++)n[t]&&e.push(n[t]);return e},_stripHtml=function(n,e){if(!n||typeof n!="string")return n;if(n.length>_max_str_len)throw new Error("Exceeded max str len");var t;n=n.replace(_re_html,e||"");do t=n,n=n.replace(/<script/i,"");while(n!==t);return t},_escapeHtml=function(n){return Array.isArray(n)&&(n=n.join(",")),typeof n=="string"?n.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;"):n},_normalize=function(n,e){if(typeof n!="string")return n;var t=n.normalize?n.normalize("NFD"):n;return t.length!==n.length?(e===!0?n+" ":"")+t.replace(/[\u0300-\u036f]/g,""):t},_areAllUnique=function(n){if(n.length<2)return!0;for(var e=n.slice().sort(),t=e[0],r=1,a=e.length;r<a;r++){if(e[r]===t)return!1;t=e[r]}return!0},_unique=function(n){if(Array.from&&Set)return Array.from(new Set(n));if(_areAllUnique(n))return n.slice();var e=[],t,r,a=n.length,o,s=0;e:for(r=0;r<a;r++){for(t=n[r],o=0;o<s;o++)if(e[o]===t)continue e;e.push(t),s++}return e},_flatten=function(n,e){if(Array.isArray(e))for(var t=0;t<e.length;t++)_flatten(n,e[t]);else n.push(e);return n};function _addClass(n,e){e&&e.split(" ").forEach(function(t){t&&n.classList.add(t)})}DataTable.util={diacritics:function(n,e){var t=typeof n;if(t!=="function")return _normalize(n,e);_normalize=n},debounce:function(n,e){var t;return function(){var r=this,a=arguments;clearTimeout(t),t=setTimeout(function(){n.apply(r,a)},e||250)}},throttle:function(n,e){var t=e!==void 0?e:200,r,a;return function(){var o=this,s=+new Date,l=arguments;r&&s<r+t?(clearTimeout(a),a=setTimeout(function(){r=void 0,n.apply(o,l)},t)):(r=s,n.apply(o,l))}},escapeRegex:function(n){return n.replace(_re_escape_regex,"\\$1")},set:function(n){if($$1.isPlainObject(n))return DataTable.util.set(n._);if(n===null)return function(){};if(typeof n=="function")return function(t,r,a){n(t,"set",r,a)};if(typeof n=="string"&&(n.indexOf(".")!==-1||n.indexOf("[")!==-1||n.indexOf("(")!==-1)){var e=function(t,r,a){for(var o=_fnSplitObjNotation(a),s,l=o[o.length-1],c,f,d,p,_=0,b=o.length-1;_<b;_++){if(o[_]==="__proto__"||o[_]==="constructor")throw new Error("Cannot set prototype values");if(c=o[_].match(__reArray),f=o[_].match(__reFn),c){if(o[_]=o[_].replace(__reArray,""),t[o[_]]=[],s=o.slice(),s.splice(0,_+1),p=s.join("."),Array.isArray(r))for(var y=0,E=r.length;y<E;y++)d={},e(d,r[y],p),t[o[_]].push(d);else t[o[_]]=r;return}else f&&(o[_]=o[_].replace(__reFn,""),t=t[o[_]](r));(t[o[_]]===null||t[o[_]]===void 0)&&(t[o[_]]={}),t=t[o[_]]}l.match(__reFn)?t=t[l.replace(__reFn,"")](r):t[l.replace(__reArray,"")]=r};return function(t,r){return e(t,r,n)}}else return function(t,r){t[n]=r}},get:function(n){if($$1.isPlainObject(n)){var e={};return $$1.each(n,function(r,a){a&&(e[r]=DataTable.util.get(a))}),function(r,a,o,s){var l=e[a]||e._;return l!==void 0?l(r,a,o,s):r}}else{if(n===null)return function(r){return r};if(typeof n=="function")return function(r,a,o,s){return n(r,a,o,s)};if(typeof n=="string"&&(n.indexOf(".")!==-1||n.indexOf("[")!==-1||n.indexOf("(")!==-1)){var t=function(r,a,o){var s,l,c,f;if(o!=="")for(var d=_fnSplitObjNotation(o),p=0,_=d.length;p<_;p++){if(s=d[p].match(__reArray),l=d[p].match(__reFn),s){if(d[p]=d[p].replace(__reArray,""),d[p]!==""&&(r=r[d[p]]),c=[],d.splice(0,p+1),f=d.join("."),Array.isArray(r))for(var b=0,y=r.length;b<y;b++)c.push(t(r[b],a,f));var E=s[0].substring(1,s[0].length-1);r=E===""?c:c.join(E);break}else if(l){d[p]=d[p].replace(__reFn,""),r=r[d[p]]();continue}if(r===null||r[d[p]]===null)return null;if(r===void 0||r[d[p]]===void 0)return;r=r[d[p]]}return r};return function(r,a){return t(r,a,n)}}else return function(r){return r[n]}}},stripHtml:function(n,e){var t=typeof n;if(t==="function"){_stripHtml=n;return}else if(t==="string")return _stripHtml(n,e);return n},escapeHtml:function(n){var e=typeof n;if(e==="function"){_escapeHtml=n;return}else if(e==="string"||Array.isArray(n))return _escapeHtml(n);return n},unique:_unique};function _fnHungarianMap(n){var e="a aa ai ao as b fn i m o s ",t,r,a={};$$1.each(n,function(o){t=o.match(/^([^A-Z]+?)([A-Z])/),t&&e.indexOf(t[1]+" ")!==-1&&(r=o.replace(t[0],t[2].toLowerCase()),a[r]=o,t[1]==="o"&&_fnHungarianMap(n[o]))}),n._hungarianMap=a}function _fnCamelToHungarian(n,e,t){n._hungarianMap||_fnHungarianMap(n);var r;$$1.each(e,function(a){r=n._hungarianMap[a],r!==void 0&&(t||e[r]===void 0)&&(r.charAt(0)==="o"?(e[r]||(e[r]={}),$$1.extend(!0,e[r],e[a]),_fnCamelToHungarian(n[r],e[r],t)):e[r]=e[a])})}var _fnCompatMap=function(n,e,t){n[e]!==void 0&&(n[t]=n[e])};function _fnCompatOpts(n){_fnCompatMap(n,"ordering","bSort"),_fnCompatMap(n,"orderMulti","bSortMulti"),_fnCompatMap(n,"orderClasses","bSortClasses"),_fnCompatMap(n,"orderCellsTop","bSortCellsTop"),_fnCompatMap(n,"order","aaSorting"),_fnCompatMap(n,"orderFixed","aaSortingFixed"),_fnCompatMap(n,"paging","bPaginate"),_fnCompatMap(n,"pagingType","sPaginationType"),_fnCompatMap(n,"pageLength","iDisplayLength"),_fnCompatMap(n,"searching","bFilter"),typeof n.sScrollX=="boolean"&&(n.sScrollX=n.sScrollX?"100%":""),typeof n.scrollX=="boolean"&&(n.scrollX=n.scrollX?"100%":""),typeof n.bSort=="object"?(n.orderIndicators=n.bSort.indicators!==void 0?n.bSort.indicators:!0,n.orderHandler=n.bSort.handler!==void 0?n.bSort.handler:!0,n.bSort=!0):n.bSort===!1?(n.orderIndicators=!1,n.orderHandler=!1):n.bSort===!0&&(n.orderIndicators=!0,n.orderHandler=!0),typeof n.bSortCellsTop=="boolean"&&(n.titleRow=n.bSortCellsTop);var e=n.aoSearchCols;if(e)for(var t=0,r=e.length;t<r;t++)e[t]&&_fnCamelToHungarian(DataTable.models.oSearch,e[t]);n.serverSide&&!n.searchDelay&&(n.searchDelay=400)}function _fnCompatCols(n){_fnCompatMap(n,"orderable","bSortable"),_fnCompatMap(n,"orderData","aDataSort"),_fnCompatMap(n,"orderSequence","asSorting"),_fnCompatMap(n,"orderDataType","sortDataType");var e=n.aDataSort;typeof e=="number"&&!Array.isArray(e)&&(n.aDataSort=[e])}function _fnBrowserDetect(n){if(!DataTable.__browser){var e={};DataTable.__browser=e;var t=$$1("<div/>").css({position:"fixed",top:0,left:-1*window.pageXOffset,height:1,width:1,overflow:"hidden"}).append($$1("<div/>").css({position:"absolute",top:1,left:1,width:100,overflow:"scroll"}).append($$1("<div/>").css({width:"100%",height:10}))).appendTo("body"),r=t.children(),a=r.children();e.barWidth=r[0].offsetWidth-r[0].clientWidth,e.bScrollbarLeft=Math.round(a.offset().left)!==1,t.remove()}$$1.extend(n.oBrowser,DataTable.__browser),n.oScroll.iBarWidth=DataTable.__browser.barWidth}function _fnAddColumn(n){var e=DataTable.defaults.column,t=n.aoColumns.length,r=$$1.extend({},DataTable.models.oColumn,e,{aDataSort:e.aDataSort?e.aDataSort:[t],mData:e.mData?e.mData:t,idx:t,searchFixed:{},colEl:$$1("<col>").attr("data-dt-column",t)});n.aoColumns.push(r);var a=n.aoPreSearchCols;a[t]=$$1.extend({},DataTable.models.oSearch,a[t])}function _fnColumnOptions(n,e,t){var r=n.aoColumns[e];if(t!=null){_fnCompatCols(t),_fnCamelToHungarian(DataTable.defaults.column,t,!0),t.mDataProp!==void 0&&!t.mData&&(t.mData=t.mDataProp),t.sType&&(r._sManualType=t.sType),t.className&&!t.sClass&&(t.sClass=t.className);var a=r.sClass;$$1.extend(r,t),_fnMap(r,t,"sWidth","sWidthOrig"),a!==r.sClass&&(r.sClass=a+" "+r.sClass),t.iDataSort!==void 0&&(r.aDataSort=[t.iDataSort]),_fnMap(r,t,"aDataSort")}var o=r.mData,s=_fnGetObjectDataFn(o);if(r.mRender&&Array.isArray(r.mRender)){var l=r.mRender.slice(),c=l.shift();r.mRender=DataTable.render[c].apply(window,l)}r._render=r.mRender?_fnGetObjectDataFn(r.mRender):null;var f=function(d){return typeof d=="string"&&d.indexOf("@")!==-1};r._bAttrSrc=$$1.isPlainObject(o)&&(f(o.sort)||f(o.type)||f(o.filter)),r._setter=null,r.fnGetData=function(d,p,_){var b=s(d,p,void 0,_);return r._render&&p?r._render(b,p,d,_):b},r.fnSetData=function(d,p,_){return _fnSetObjectDataFn(o)(d,p,_)},typeof o!="number"&&!r._isArrayHost&&(n._rowReadObject=!0),n.oFeatures.bSort||(r.bSortable=!1)}function _fnAdjustColumnSizing(n){_fnCalculateColumnWidths(n),_fnColumnSizes(n);var e=n.oScroll;(e.sY!==""||e.sX!=="")&&_fnScrollDraw(n),_fnCallbackFire(n,null,"column-sizing",[n])}function _fnColumnSizes(n){for(var e=n.aoColumns,t=0;t<e.length;t++){var r=_fnColumnsSumWidth(n,[t],!1);e[t].colEl.css("width",r),n.oScroll.sX&&e[t].colEl.css("min-width",r)}}function _fnVisibleToColumnIndex(n,e){var t=_fnGetColumns(n,"bVisible");return typeof t[e]=="number"?t[e]:null}function _fnColumnIndexToVisible(n,e){var t=_fnGetColumns(n,"bVisible"),r=t.indexOf(e);return r!==-1?r:null}function _fnVisibleColumns(n){var e=n.aoHeader,t=n.aoColumns,r=0;if(e.length)for(var a=0,o=e[0].length;a<o;a++)t[a].bVisible&&$$1(e[0][a].cell).css("display")!=="none"&&r++;return r}function _fnGetColumns(n,e){var t=[];return n.aoColumns.map(function(r,a){r[e]&&t.push(a)}),t}function _typeResult(n,e){return e===!0?n._name:e}function _fnColumnTypes(n){var e=n.aoColumns,t=n.aoData,r=DataTable.ext.type.detect,a,o,s,l,c,f,d,p,_;for(a=0,o=e.length;a<o;a++){if(d=e[a],_=[],!d.sType&&d._sManualType)d.sType=d._sManualType;else if(!d.sType){if(!n.typeDetect)return;for(s=0,l=r.length;s<l;s++){var b=r[s],y=b.oneOf,E=b.allOf||b,C=b.init,D=!1;if(p=null,C&&(p=_typeResult(b,C(n,d,a)),p)){d.sType=p;break}for(c=0,f=t.length;c<f&&!(t[c]&&(_[c]===void 0&&(_[c]=_fnGetCellData(n,c,a,"type")),y&&!D&&(D=_typeResult(b,y(_[c],n))),p=_typeResult(b,E(_[c],n)),!p&&s!==r.length-3||p==="html"&&!_empty(_[c])));c++);if(y&&D&&p||!y&&p){d.sType=p;break}}d.sType||(d.sType="string")}var M=_ext.type.className[d.sType];M&&(_columnAutoClass(n.aoHeader,a,M),_columnAutoClass(n.aoFooter,a,M));var F=_ext.type.render[d.sType];F&&!d._render&&(d._render=DataTable.util.get(F),_columnAutoRender(n,a))}}function _columnAutoRender(n,e){for(var t=n.aoData,r=0;r<t.length;r++)if(t[r].nTr){var a=_fnGetCellData(n,r,e,"display");t[r].displayData[e]=a,_fnWriteCell(t[r].anCells[e],a)}}function _columnAutoClass(n,e,t){n.forEach(function(r){r[e]&&r[e].unique&&_addClass(r[e].cell,t)})}function _fnApplyColumnDefs(n,e,t,r,a){var o,s,l,c,f,d,p,_=n.aoColumns;if(t)for(o=0,s=t.length;o<s;o++)t[o]&&t[o].name&&(_[o].sName=t[o].name);if(e)for(o=e.length-1;o>=0;o--){p=e[o];var b=p.target!==void 0?p.target:p.targets!==void 0?p.targets:p.aTargets;for(Array.isArray(b)||(b=[b]),l=0,c=b.length;l<c;l++){var y=b[l];if(typeof y=="number"&&y>=0){for(;_.length<=y;)_fnAddColumn(n);a(y,p)}else if(typeof y=="number"&&y<0)a(_.length+y,p);else if(typeof y=="string")for(f=0,d=_.length;f<d;f++)y==="_all"?a(f,p):y.indexOf(":name")!==-1?_[f].sName===y.replace(":name","")&&a(f,p):r.forEach(function(E){if(E[f]){var C=$$1(E[f].cell);y.match(/^[a-z][\w-]*$/i)&&(y="."+y),C.is(y)&&a(f,p)}})}}if(t)for(o=0,s=t.length;o<s;o++)a(o,t[o])}function _fnColumnsSumWidth(n,e,t,r){Array.isArray(e)||(e=_fnColumnsFromHeader(e));for(var a=0,o,s=n.aoColumns,l=0,c=e.length;l<c;l++){var f=s[e[l]],d=t?f.sWidthOrig:f.sWidth;if(f.bVisible!==!1){if(d==null)return null;if(typeof d=="number")o="px",a+=d;else{var p=d.match(/([\d\.]+)([^\d]*)/);p&&(a+=p[1]*1,o=p.length===3?p[2]:"px")}}}return a+o}function _fnColumnsFromHeader(n){var e=$$1(n).closest("[data-dt-column]").attr("data-dt-column");return e?e.split(",").map(function(t){return t*1}):[]}function _fnAddData(n,e,t,r){var a=n.aoData.length,o=$$1.extend(!0,{},DataTable.models.oRow,{src:t?"dom":"data",idx:a});o._aData=e,n.aoData.push(o);for(var s=n.aoColumns,l=0,c=s.length;l<c;l++)s[l].sType=null;n.aiDisplayMaster.push(a);var f=n.rowIdFn(e);return f!==void 0&&(n.aIds[f]=o),(t||!n.oFeatures.bDeferRender)&&_fnCreateTr(n,a,t,r),a}function _fnAddTr(n,e){var t;return e instanceof $$1||(e=$$1(e)),e.map(function(r,a){return t=_fnGetRowElements(n,a),_fnAddData(n,t.data,a,t.cells)})}function _fnGetCellData(n,e,t,r){r==="search"?r="filter":r==="order"&&(r="sort");var a=n.aoData[e];if(a){var o=n.iDraw,s=n.aoColumns[t],l=a._aData,c=s.sDefaultContent,f=s.fnGetData(l,r,{settings:n,row:e,col:t});if(r!=="display"&&f&&typeof f=="object"&&f.nodeName&&(f=f.innerHTML),f===void 0)return n.iDrawError!=o&&c===null&&(_fnLog(n,0,"Requested unknown parameter "+(typeof s.mData=="function"?"{function}":"'"+s.mData+"'")+" for row "+e+", column "+t,4),n.iDrawError=o),c;if((f===l||f===null)&&c!==null&&r!==void 0)f=c;else if(typeof f=="function")return f.call(l);if(f===null&&r==="display")return"";if(r==="filter"){var d=DataTable.ext.type.search;d[s.sType]&&(f=d[s.sType](f))}return f}}function _fnSetCellData(n,e,t,r){var a=n.aoColumns[t],o=n.aoData[e]._aData;a.fnSetData(o,r,{settings:n,row:e,col:t})}function _fnWriteCell(n,e){e&&typeof e=="object"&&e.nodeName?$$1(n).empty().append(e):n.innerHTML=e}var __reArray=/\[.*?\]$/,__reFn=/\(\)$/;function _fnSplitObjNotation(n){var e=n.match(/(\\.|[^.])+/g)||[""];return e.map(function(t){return t.replace(/\\\./g,".")})}var _fnGetObjectDataFn=DataTable.util.get,_fnSetObjectDataFn=DataTable.util.set;function _fnGetDataMaster(n){return _pluck(n.aoData,"_aData")}function _fnClearTable(n){n.aoData.length=0,n.aiDisplayMaster.length=0,n.aiDisplay.length=0,n.aIds={}}function _fnInvalidate(n,e,t,r){var a=n.aoData[e],o,s;if(a._aSortData=null,a._aFilterData=null,a.displayData=null,t==="dom"||(!t||t==="auto")&&a.src==="dom")a._aData=_fnGetRowElements(n,a,r,r===void 0?void 0:a._aData).data;else{var l=a.anCells,c=_fnGetRowDisplay(n,e);if(l)if(r!==void 0)_fnWriteCell(l[r],c[r]);else for(o=0,s=l.length;o<s;o++)_fnWriteCell(l[o],c[o])}var f=n.aoColumns;if(r!==void 0)f[r].sType=null,f[r].wideStrings=null;else{for(o=0,s=f.length;o<s;o++)f[o].sType=null,f[o].wideStrings=null;_fnRowAttributes(n,a)}}function _fnGetRowElements(n,e,t,r){var a=[],o=e.firstChild,s,l,c=0,f,d=n.aoColumns,p=n._rowReadObject;r=r!==void 0?r:p?{}:[];var _=function(M,F){if(typeof M=="string"){var P=M.indexOf("@");if(P!==-1){var H=M.substring(P+1),B=_fnSetObjectDataFn(M);B(r,F.getAttribute(H))}}},b=function(M){if(t===void 0||t===c)if(l=d[c],f=M.innerHTML.trim(),l&&l._bAttrSrc){var F=_fnSetObjectDataFn(l.mData._);F(r,f),_(l.mData.sort,M),_(l.mData.type,M),_(l.mData.filter,M)}else p?(l._setter||(l._setter=_fnSetObjectDataFn(l.mData)),l._setter(r,f)):r[c]=f;c++};if(o)for(;o;)s=o.nodeName.toUpperCase(),(s=="TD"||s=="TH")&&(b(o),a.push(o)),o=o.nextSibling;else{a=e.anCells;for(var y=0,E=a.length;y<E;y++)b(a[y])}var C=e.firstChild?e:e.nTr;if(C){var D=C.getAttribute("id");D&&_fnSetObjectDataFn(n.rowId)(r,D)}return{data:r,cells:a}}function _fnGetRowDisplay(n,e){var t=n.aoData[e],r=n.aoColumns;if(!t.displayData){t.displayData=[];for(var a=0,o=r.length;a<o;a++)t.displayData.push(_fnGetCellData(n,e,a,"display"))}return t.displayData}function _fnCreateTr(n,e,t,r){var a=n.aoData[e],o=a._aData,s=[],l,c,f,d,p,_,b=n.oClasses.tbody.row;if(a.nTr===null){for(l=t||document.createElement("tr"),a.nTr=l,a.anCells=s,_addClass(l,b),l._DT_RowIndex=e,_fnRowAttributes(n,a),d=0,p=n.aoColumns.length;d<p;d++){f=n.aoColumns[d],_=!(t&&r[d]),c=_?document.createElement(f.sCellType):r[d],c||_fnLog(n,0,"Incorrect column count",18),c._DT_CellIndex={row:e,column:d},s.push(c);var y=_fnGetRowDisplay(n,e);(_||(f.mRender||f.mData!==d)&&(!$$1.isPlainObject(f.mData)||f.mData._!==d+".display"))&&_fnWriteCell(c,y[d]),_addClass(c,f.sClass),f.bVisible&&_?l.appendChild(c):!f.bVisible&&!_&&c.parentNode.removeChild(c),f.fnCreatedCell&&f.fnCreatedCell.call(n.oInstance,c,_fnGetCellData(n,e,d),o,e,d)}_fnCallbackFire(n,"aoRowCreatedCallback","row-created",[l,o,e,s])}else _addClass(a.nTr,b)}function _fnRowAttributes(n,e){var t=e.nTr,r=e._aData;if(t){var a=n.rowIdFn(r);if(a&&(t.id=a),r.DT_RowClass){var o=r.DT_RowClass.split(" ");e.__rowc=e.__rowc?_unique(e.__rowc.concat(o)):o,$$1(t).removeClass(e.__rowc.join(" ")).addClass(r.DT_RowClass)}r.DT_RowAttr&&$$1(t).attr(r.DT_RowAttr),r.DT_RowData&&$$1(t).data(r.DT_RowData)}}function _fnBuildHead(n,e){var t=n.oClasses,r=n.aoColumns,a,o,s,l=e==="header"?n.nTHead:n.nTFoot,c=e==="header"?"sTitle":e;if(l){if((e==="header"||_pluck(n.aoColumns,c).join(""))&&(s=$$1("tr",l),s.length||(s=$$1("<tr/>").appendTo(l)),s.length===1)){var f=0;for($$1("td, th",s).each(function(){f+=this.colSpan}),a=f,o=r.length;a<o;a++)$$1("<th/>").html(r[a][c]||"").appendTo(s)}var d=_fnDetectHeader(n,l,!0);e==="header"?(n.aoHeader=d,$$1("tr",l).addClass(t.thead.row)):(n.aoFooter=d,$$1("tr",l).addClass(t.tfoot.row)),$$1(l).children("tr").children("th, td").each(function(){_fnRenderer(n,e)(n,$$1(this),t)})}}function _fnHeaderLayout(n,e,t){var r,a,o,s=[],l=[],c=n.aoColumns,f=c.length,d,p;if(e){for(t||(t=_range(f).filter(function(y){return c[y].bVisible})),r=0;r<e.length;r++)s[r]=e[r].slice().filter(function(y,E){return t.includes(E)}),l.push([]);for(r=0;r<s.length;r++)for(a=0;a<s[r].length;a++)if(d=1,p=1,l[r][a]===void 0){for(o=s[r][a].cell;s[r+d]!==void 0&&s[r][a].cell==s[r+d][a].cell;)l[r+d][a]=null,d++;for(;s[r][a+p]!==void 0&&s[r][a].cell==s[r][a+p].cell;){for(var _=0;_<d;_++)l[r+_][a+p]=null;p++}var b=$$1(".dt-column-title",o);l[r][a]={cell:o,colspan:p,rowspan:d,title:b.length?b.html():$$1(o).html()}}return l}}function _fnDrawHead(n,e){for(var t=_fnHeaderLayout(n,e),r,a,o=0;o<e.length;o++){if(r=e[o].row,r)for(;a=r.firstChild;)r.removeChild(a);for(var s=0;s<t[o].length;s++){var l=t[o][s];l&&$$1(l.cell).appendTo(r).attr("rowspan",l.rowspan).attr("colspan",l.colspan)}}}function _fnDraw(n,e){_fnStart(n);var t=_fnCallbackFire(n,"aoPreDrawCallback","preDraw",[n]);if(t.indexOf(!1)!==-1){_fnProcessingDisplay(n,!1);return}var r=[],a=0,o=_fnDataSource(n)=="ssp",s=n.aiDisplay,l=n._iDisplayStart,c=n.fnDisplayEnd(),f=n.aoColumns,d=$$1(n.nTBody);if(n.bDrawing=!0,n.deferLoading)n.deferLoading=!1,n.iDraw++,_fnProcessingDisplay(n,!1);else if(!o)n.iDraw++;else if(!n.bDestroying&&!e){n.iDraw===0&&d.empty().append(_emptyRow(n)),_fnAjaxUpdate(n);return}if(s.length!==0)for(var p=o?0:l,_=o?n.aoData.length:c,b=p;b<_;b++){var y=s[b],E=n.aoData[y];if(E!==null){E.nTr===null&&_fnCreateTr(n,y);for(var C=E.nTr,D=0;D<f.length;D++){var M=f[D],F=E.anCells[D];_addClass(F,_ext.type.className[M.sType]),_addClass(F,n.oClasses.tbody.cell)}_fnCallbackFire(n,"aoRowCallback",null,[C,E._aData,a,b,y]),r.push(C),a++}}else r[0]=_emptyRow(n);_fnCallbackFire(n,"aoHeaderCallback","header",[$$1(n.nTHead).children("tr")[0],_fnGetDataMaster(n),l,c,s]),_fnCallbackFire(n,"aoFooterCallback","footer",[$$1(n.nTFoot).children("tr")[0],_fnGetDataMaster(n),l,c,s]),d[0].replaceChildren?d[0].replaceChildren.apply(d[0],r):(d.children().detach(),d.append($$1(r))),$$1(n.nTableWrapper).toggleClass("dt-empty-footer",$$1("tr",n.nTFoot).length===0),_fnCallbackFire(n,"aoDrawCallback","draw",[n],!0),n.bSorted=!1,n.bFiltered=!1,n.bDrawing=!1}function _fnReDraw(n,e,t){var r=n.oFeatures,a=r.bSort,o=r.bFilter;(t===void 0||t===!0)&&(_fnColumnTypes(n),a&&_fnSort(n),o?_fnFilterComplete(n,n.oPreviousSearch):n.aiDisplay=n.aiDisplayMaster.slice()),e!==!0?n._iDisplayStart=0:_fnLengthOverflow(n),n._drawHold=e,_fnDraw(n),n.api.one("draw",function(){n._drawHold=!1})}function _emptyRow(n){var e=n.oLanguage,t=e.sZeroRecords,r=_fnDataSource(n);return(r==="ssp"||r==="ajax")&&!n.json?t=e.sLoadingRecords:e.sEmptyTable&&n.fnRecordsTotal()===0&&(t=e.sEmptyTable),$$1("<tr/>").append($$1("<td />",{colSpan:_fnVisibleColumns(n),class:n.oClasses.empty.row}).html(t))[0]}function _layoutItems(n,e,t){if(Array.isArray(t)){for(var r=0;r<t.length;r++)_layoutItems(n,e,t[r]);return}var a=n[e];$$1.isPlainObject(t)?t.features?(t.rowId&&(n.id=t.rowId),t.rowClass&&(n.className=t.rowClass),a.id=t.id,a.className=t.className,_layoutItems(n,e,t.features)):Object.keys(t).map(function(o){a.contents.push({feature:o,opts:t[o]})}):a.contents.push(t)}function _layoutGetRow(n,e,t){for(var r,a=0;a<n.length;a++)if(r=n[a],r.rowNum===e&&(t==="full"&&r.full||(t==="start"||t==="end")&&(r.start||r.end)))return r[t]||(r[t]={contents:[]}),r;return r={rowNum:e},r[t]={contents:[]},n.push(r),r}function _layoutArray(n,e,t){var r=[];$$1.each(e,function(o,s){if(s!==null){var l=o.match(/^([a-z]+)([0-9]*)([A-Za-z]*)$/),c=l[2]?l[2]*1:0,f=l[3]?l[3].toLowerCase():"full";if(l[1]===t){var d=_layoutGetRow(r,c,f);_layoutItems(d,f,s)}}}),r.sort(function(o,s){var l=o.rowNum,c=s.rowNum;if(l===c){var f=o.full&&!s.full?-1:1;return t==="bottom"?f*-1:f}return c-l}),t==="bottom"&&r.reverse();for(var a=0;a<r.length;a++)delete r[a].rowNum,_layoutResolve(n,r[a]);return r}function _layoutResolve(n,e){var t=function(a,o){return _ext.features[a]||_fnLog(n,0,"Unknown feature: "+a),_ext.features[a].apply(this,[n,o])},r=function(a){if(e[a])for(var o=e[a].contents,s=0,l=o.length;s<l;s++)if(o[s]){if(typeof o[s]=="string")o[s]=t(o[s],null);else if($$1.isPlainObject(o[s]))o[s]=t(o[s].feature,o[s].opts);else if(typeof o[s].node=="function")o[s]=o[s].node(n);else if(typeof o[s]=="function"){var c=o[s](n);o[s]=typeof c.node=="function"?c.node():c}}else continue};r("start"),r("end"),r("full")}function _fnAddOptionsHtml(n){var e=n.oClasses,t=$$1(n.nTable),r=$$1("<div/>").attr({id:n.sTableId+"_wrapper",class:e.container}).insertBefore(t);if(n.nTableWrapper=r[0],n.sDom)_fnLayoutDom(n,n.sDom,r);else{var a=_layoutArray(n,n.layout,"top"),o=_layoutArray(n,n.layout,"bottom"),s=_fnRenderer(n,"layout");a.forEach(function(l){s(n,r,l)}),s(n,r,{full:{table:!0,contents:[_fnFeatureHtmlTable(n)]}}),o.forEach(function(l){s(n,r,l)})}_processingHtml(n)}function _fnLayoutDom(n,e,t){for(var r=e.match(/(".*?")|('.*?')|./g),a,o,s,l,c,f=0;f<r.length;f++){if(a=null,o=r[f],o=="<"){if(s=$$1("<div/>"),l=r[f+1],l[0]=="'"||l[0]=='"'){c=l.replace(/['"]/g,"");var d="",p;if(c.indexOf(".")!=-1){var _=c.split(".");d=_[0],p=_[1]}else c[0]=="#"?d=c:p=c;s.attr("id",d.substring(1)).addClass(p),f++}t.append(s),t=s}else o==">"?t=t.parent():o=="t"?a=_fnFeatureHtmlTable(n):DataTable.ext.feature.forEach(function(b){o==b.cFeature&&(a=b.fnInit(n))});a&&t.append(a)}}function _fnDetectHeader(n,e,t){var r=n.aoColumns,a=$$1(e).children("tr"),o,s,l,c,f,d,p,_,b,y,E=n.titleRow,C=e&&e.nodeName.toLowerCase()==="thead",D=[],M,F=function(Z,te,ne){for(var Q=Z[te];Q[ne];)ne++;return ne};for(l=0,d=a.length;l<d;l++)D.push([]);for(l=0,d=a.length;l<d;l++)for(o=a[l],_=0,s=o.firstChild;s;){if(s.nodeName.toUpperCase()=="TD"||s.nodeName.toUpperCase()=="TH"){var P=[],H=$$1(s);if(b=s.getAttribute("colspan")*1,y=s.getAttribute("rowspan")*1,b=!b||b===0||b===1?1:b,y=!y||y===0||y===1?1:y,p=F(D,l,_),M=b===1,t){if(M){_fnColumnOptions(n,p,_fnEscapeObject(H.data()));var B=r[p],g=s.getAttribute("width")||null,q=s.style.width.match(/width:\s*(\d+[pxem%]+)/);q&&(g=q[1]),B.sWidthOrig=B.sWidth||g,C?(B.sTitle!==null&&!B.autoTitle&&(E===!0&&l===0||E===!1&&l===a.length-1||E===l||E===null)&&(s.innerHTML=B.sTitle),!B.sTitle&&M&&(B.sTitle=_stripHtml(s.innerHTML),B.autoTitle=!0)):B.footer&&(s.innerHTML=B.footer),B.ariaTitle||(B.ariaTitle=H.attr("aria-label")||B.sTitle),B.className&&H.addClass(B.className)}$$1(".dt-column-title",s).length===0&&$$1(document.createElement(n.columnTitleTag)).addClass("dt-column-title").append(s.childNodes).appendTo(s),n.orderIndicators&&C&&H.filter(":not([data-dt-order=disable])").length!==0&&H.parent(":not([data-dt-order=disable])").length!==0&&$$1(".dt-column-order",s).length===0&&$$1(document.createElement(n.columnTitleTag)).addClass("dt-column-order").appendTo(s);var G=C?"header":"footer";$$1("div.dt-column-"+G,s).length===0&&$$1("<div>").addClass("dt-column-"+G).append(s.childNodes).appendTo(s)}for(f=0;f<b;f++){for(c=0;c<y;c++)D[l+c][p+f]={cell:s,unique:M},D[l+c].row=o;P.push(p+f)}s.setAttribute("data-dt-column",_unique(P).join(","))}s=s.nextSibling}return D}function _fnStart(n){var e=_fnDataSource(n)=="ssp",t=n.iInitDisplayStart;t!==void 0&&t!==-1&&(n._iDisplayStart=e?t:t>=n.fnRecordsDisplay()?0:t,n.iInitDisplayStart=-1)}function _fnBuildAjax(n,e,t){var r,a=n.ajax,o=n.oInstance,s=function(d){var p=n.jqXHR?n.jqXHR.status:null;(d===null||typeof p=="number"&&p==204)&&(d={},_fnAjaxDataSrc(n,d,[]));var _=d.error||d.sError;if(_&&_fnLog(n,0,_),d.d&&typeof d.d=="string")try{d=JSON.parse(d.d)}catch{}n.json=d,_fnCallbackFire(n,null,"xhr",[n,d,n.jqXHR],!0),t(d)};if($$1.isPlainObject(a)&&a.data){r=a.data;var l=typeof r=="function"?r(e,n):r;e=typeof r=="function"&&l?l:$$1.extend(!0,e,l),delete a.data}var c={url:typeof a=="string"?a:"",data:e,success:s,dataType:"json",cache:!1,type:n.sServerMethod,error:function(d,p){var _=_fnCallbackFire(n,null,"xhr",[n,null,n.jqXHR],!0);_.indexOf(!0)===-1&&(p=="parsererror"?_fnLog(n,0,"Invalid JSON response",1):d.readyState===4&&_fnLog(n,0,"Ajax error",7)),_fnProcessingDisplay(n,!1)}};if($$1.isPlainObject(a)&&$$1.extend(c,a),n.oAjaxData=e,_fnCallbackFire(n,null,"preXhr",[n,e,c],!0),c.submitAs==="json"&&typeof e=="object"&&(c.data=JSON.stringify(e),c.contentType||(c.contentType="application/json; charset=utf-8")),typeof a=="function")n.jqXHR=a.call(o,e,s,n);else if(a.url===""){var f={};_fnAjaxDataSrc(n,f,[]),s(f)}else n.jqXHR=$$1.ajax(c);r&&(a.data=r)}function _fnAjaxUpdate(n){n.iDraw++,_fnProcessingDisplay(n,!0),_fnBuildAjax(n,_fnAjaxParameters(n),function(e){_fnAjaxUpdateDraw(n,e)})}function _fnAjaxParameters(n){var e=n.aoColumns,t=n.oFeatures,r=n.oPreviousSearch,a=n.aoPreSearchCols,o=function(s,l){return typeof e[s][l]=="function"?"function":e[s][l]};return{draw:n.iDraw,columns:e.map(function(s,l){return{data:o(l,"mData"),name:s.sName,searchable:s.bSearchable,orderable:s.bSortable,search:{value:a[l].search,regex:a[l].regex,fixed:Object.keys(s.searchFixed).map(function(c){return{name:c,term:typeof s.searchFixed[c]!="function"?s.searchFixed[c].toString():"function"}})}}}),order:_fnSortFlatten(n).map(function(s){return{column:s.col,dir:s.dir,name:o(s.col,"sName")}}),start:n._iDisplayStart,length:t.bPaginate?n._iDisplayLength:-1,search:{value:r.search,regex:r.regex,fixed:Object.keys(n.searchFixed).map(function(s){return{name:s,term:typeof n.searchFixed[s]!="function"?n.searchFixed[s].toString():"function"}})}}}function _fnAjaxUpdateDraw(n,e){var t=_fnAjaxDataSrc(n,e),r=_fnAjaxDataSrcParam(n,"draw",e),a=_fnAjaxDataSrcParam(n,"recordsTotal",e),o=_fnAjaxDataSrcParam(n,"recordsFiltered",e);if(r!==void 0){if(r*1<n.iDraw)return;n.iDraw=r*1}t||(t=[]),_fnClearTable(n),n._iRecordsTotal=parseInt(a,10),n._iRecordsDisplay=parseInt(o,10);for(var s=0,l=t.length;s<l;s++)_fnAddData(n,t[s]);n.aiDisplay=n.aiDisplayMaster.slice(),_fnColumnTypes(n),_fnDraw(n,!0),_fnInitComplete(n),_fnProcessingDisplay(n,!1)}function _fnAjaxDataSrc(n,e,t){var r="data";if($$1.isPlainObject(n.ajax)&&n.ajax.dataSrc!==void 0){var a=n.ajax.dataSrc;typeof a=="string"||typeof a=="function"?r=a:a.data!==void 0&&(r=a.data)}if(!t)return r==="data"?e.aaData||e[r]:r!==""?_fnGetObjectDataFn(r)(e):e;_fnSetObjectDataFn(r)(e,t)}function _fnAjaxDataSrcParam(n,e,t){var r=$$1.isPlainObject(n.ajax)?n.ajax.dataSrc:null;if(r&&r[e])return _fnGetObjectDataFn(r[e])(t);var a="";return e==="draw"?a="sEcho":e==="recordsTotal"?a="iTotalRecords":e==="recordsFiltered"&&(a="iTotalDisplayRecords"),t[a]!==void 0?t[a]:t[e]}function _fnFilterComplete(n,e){var t=n.aoPreSearchCols;if(_fnDataSource(n)!="ssp"){_fnFilterData(n),n.aiDisplay=n.aiDisplayMaster.slice(),_fnFilter(n.aiDisplay,n,e.search,e),$$1.each(n.searchFixed,function(o,s){_fnFilter(n.aiDisplay,n,s,{})});for(var r=0;r<t.length;r++){var a=t[r];_fnFilter(n.aiDisplay,n,a.search,a,r),$$1.each(n.aoColumns[r].searchFixed,function(o,s){_fnFilter(n.aiDisplay,n,s,{},r)})}_fnFilterCustom(n)}n.bFiltered=!0,_fnCallbackFire(n,null,"search",[n])}function _fnFilterCustom(n){for(var e=DataTable.ext.search,t=n.aiDisplay,r,a,o=0,s=e.length;o<s;o++){for(var l=[],c=0,f=t.length;c<f;c++)a=t[c],r=n.aoData[a],e[o](n,r._aFilterData,a,r._aData,c)&&l.push(a);t.length=0,_fnArrayApply(t,l)}}function _fnFilter(n,e,t,r,a){if(t!==""){var o=0,s=[],l=typeof t=="function"?t:null,c=t instanceof RegExp?t:l?null:_fnFilterCreateSearch(t,r);for(o=0;o<n.length;o++){var f=e.aoData[n[o]],d=a===void 0?f._sFilterRow:f._aFilterData[a];(l&&l(d,f._aData,n[o],a)||c&&c.test(d))&&s.push(n[o])}for(n.length=s.length,o=0;o<s.length;o++)n[o]=s[o]}}function _fnFilterCreateSearch(n,e){var t=[],r=$$1.extend({},{boundary:!1,caseInsensitive:!0,exact:!1,regex:!1,smart:!0},e);if(typeof n!="string"&&(n=n.toString()),n=_normalize(n),r.exact)return new RegExp("^"+_fnEscapeRegex(n)+"$",r.caseInsensitive?"i":"");if(n=r.regex?n:_fnEscapeRegex(n),r.smart){var a=n.match(/!?["\u201C][^"\u201D]+["\u201D]|[^ ]+/g)||[""],o=a.map(function(c){var f=!1,d;return c.charAt(0)==="!"&&(f=!0,c=c.substring(1)),c.charAt(0)==='"'?(d=c.match(/^"(.*)"$/),c=d?d[1]:c):c.charAt(0)==="“"&&(d=c.match(/^\u201C(.*)\u201D$/),c=d?d[1]:c),f&&(c.length>1&&t.push("(?!"+c+")"),c=""),c.replace(/"/g,"")}),s=t.length?t.join(""):"",l=r.boundary?"\\b":"";n="^(?=.*?"+l+o.join(")(?=.*?"+l)+")("+s+".)*$"}return new RegExp(n,r.caseInsensitive?"i":"")}var _fnEscapeRegex=DataTable.util.escapeRegex,__filter_div=$$1("<div>")[0],__filter_div_textContent=__filter_div.textContent!==void 0;function _fnFilterData(n){for(var e=n.aoColumns,t=n.aoData,r,a,o,s,l,c,f=!1,d=0;d<t.length;d++)if(t[d]&&(c=t[d],!c._aFilterData)){for(s=[],a=0,o=e.length;a<o;a++)r=e[a],r.bSearchable?(l=_fnGetCellData(n,d,a,"filter"),l===null&&(l=""),typeof l!="string"&&l.toString&&(l=l.toString())):l="",l.indexOf&&l.indexOf("&")!==-1&&(__filter_div.innerHTML=l,l=__filter_div_textContent?__filter_div.textContent:__filter_div.innerText),l.replace&&(l=l.replace(/[\r\n\u2028]/g,"")),s.push(l);c._aFilterData=s,c._sFilterRow=s.join("  "),f=!0}return f}function _fnInitialise(n){var e,t=n.oInit,r=n.deferLoading,a=_fnDataSource(n);if(!n.bInitialised){setTimeout(function(){_fnInitialise(n)},200);return}_fnBuildHead(n,"header"),_fnBuildHead(n,"footer"),_fnLoadState(n,t,function(){_fnDrawHead(n,n.aoHeader),_fnDrawHead(n,n.aoFooter);var o=n.iInitDisplayStart;if(t.aaData)for(e=0;e<t.aaData.length;e++)_fnAddData(n,t.aaData[e]);else(r||a=="dom")&&_fnAddTr(n,$$1(n.nTBody).children("tr"));n.aiDisplay=n.aiDisplayMaster.slice(),_fnAddOptionsHtml(n),_fnSortInit(n),_colGroup(n),_fnProcessingDisplay(n,!0),_fnCallbackFire(n,null,"preInit",[n],!0),_fnReDraw(n),(a!="ssp"||r)&&(a=="ajax"?_fnBuildAjax(n,{},function(s){var l=_fnAjaxDataSrc(n,s);for(e=0;e<l.length;e++)_fnAddData(n,l[e]);n.iInitDisplayStart=o,_fnReDraw(n),_fnProcessingDisplay(n,!1),_fnInitComplete(n)}):(_fnInitComplete(n),_fnProcessingDisplay(n,!1)))})}function _fnInitComplete(n){if(n._bInitComplete)return;var e=[n,n.json];let t=$$1(n.tfoot);t.children().length===0&&t.remove(),n._bInitComplete=!0,_fnAdjustColumnSizing(n),_fnCallbackFire(n,null,"plugin-init",e,!0),_fnCallbackFire(n,"aoInitComplete","init",e,!0)}function _fnLengthChange(n,e){var t=parseInt(e,10);n._iDisplayLength=t,_fnLengthOverflow(n),_fnCallbackFire(n,null,"length",[n,t])}function _fnPageChange(n,e,t){var r=n._iDisplayStart,a=n._iDisplayLength,o=n.fnRecordsDisplay();if(o===0||a===-1)r=0;else if(typeof e=="number")r=e*a,r>o&&(r=0);else if(e=="first")r=0;else if(e=="previous")r=a>=0?r-a:0,r<0&&(r=0);else if(e=="next")r+a<o&&(r+=a);else if(e=="last")r=Math.floor((o-1)/a)*a;else{if(e==="ellipsis")return;_fnLog(n,0,"Unknown paging action: "+e,5)}var s=n._iDisplayStart!==r;return n._iDisplayStart=r,_fnCallbackFire(n,null,s?"page":"page-nc",[n]),s&&t&&_fnDraw(n),s}function _processingHtml(n){var e=n.nTable,t=n.oScroll.sX!==""||n.oScroll.sY!=="";if(n.oFeatures.bProcessing){var r=$$1("<div/>",{id:n.sTableId+"_processing",class:n.oClasses.processing.container,role:"status"}).html(n.oLanguage.sProcessing).append("<div><div></div><div></div><div></div><div></div></div>");t?r.prependTo($$1("div.dt-scroll",n.nTableWrapper)):r.insertBefore(e),$$1(e).on("processing.dt.DT",function(a,o,s){r.css("display",s?"block":"none")})}}function _fnProcessingDisplay(n,e){n.bDrawing&&e===!1||_fnCallbackFire(n,null,"processing",[n,e])}function _fnProcessingRun(n,e,t){e?(_fnProcessingDisplay(n,!0),setTimeout(function(){t(),_fnProcessingDisplay(n,!1)},0)):t()}function _fnFeatureHtmlTable(n){var e=$$1(n.nTable),t=n.oScroll;if(t.sX===""&&t.sY==="")return n.nTable;var r=t.sX,a=t.sY,o=n.oClasses.scrolling,s=n.captionNode,l=s?s._captionSide:null,c=$$1(e[0].cloneNode(!1)),f=$$1(e[0].cloneNode(!1)),d=e.children("tfoot"),p="<div/>",_=function(M){return M?_fnStringToCss(M):null};d.length||(d=null);var b=$$1(p,{class:o.container}).append($$1(p,{class:o.header.self}).css({overflow:"hidden",position:"relative",border:0,width:r?_(r):"100%"}).append($$1(p,{class:o.header.inner}).css({"box-sizing":"content-box",width:t.sXInner||"100%"}).append(c.removeAttr("id").css("margin-left",0).append(l==="top"?s:null).append(e.children("thead"))))).append($$1(p,{class:o.body}).css({position:"relative",overflow:"auto",width:_(r)}).append(e));d&&b.append($$1(p,{class:o.footer.self}).css({overflow:"hidden",border:0,width:r?_(r):"100%"}).append($$1(p,{class:o.footer.inner}).append(f.removeAttr("id").css("margin-left",0).append(l==="bottom"?s:null).append(e.children("tfoot")))));var y=b.children(),E=y[0],C=y[1],D=d?y[2]:null;return $$1(C).on("scroll.DT",function(){var M=this.scrollLeft;E.scrollLeft=M,d&&(D.scrollLeft=M)}),$$1("th, td",E).on("focus",function(){var M=E.scrollLeft;C.scrollLeft=M,d&&(C.scrollLeft=M)}),$$1(C).css("max-height",a),t.bCollapse||$$1(C).css("height",a),n.nScrollHead=E,n.nScrollBody=C,n.nScrollFoot=D,n.aoDrawCallback.push(_fnScrollDraw),b[0]}function _fnScrollDraw(n){var e=n.oScroll,t=e.iBarWidth,r=$$1(n.nScrollHead),a=r.children("div"),o=a.children("table"),s=n.nScrollBody,l=$$1(s),c=$$1(n.nScrollFoot),f=c.children("div"),d=f.children("table"),p=$$1(n.nTHead),_=$$1(n.nTable),b=n.nTFoot&&$$1("th, td",n.nTFoot).length?$$1(n.nTFoot):null,y=n.oBrowser,E,C,D=s.scrollHeight>s.clientHeight;if(n.scrollBarVis!==D&&n.scrollBarVis!==void 0){n.scrollBarVis=D,_fnAdjustColumnSizing(n);return}else n.scrollBarVis=D;if(_.children("thead, tfoot").remove(),E=p.clone().prependTo(_),E.find("th, td").removeAttr("tabindex"),E.find("[id]").removeAttr("id"),b&&(C=b.clone().prependTo(_),C.find("[id]").removeAttr("id")),n.aiDisplay.length){var M=null,F=_fnDataSource(n)!=="ssp"?n._iDisplayStart:0;for(g=F;g<F+n.aiDisplay.length;g++){var P=n.aiDisplay[g],H=n.aoData[P].nTr;if(H){M=H;break}}if(M)for(var B=$$1(M).children("th, td").map(function(Q){return{idx:_fnVisibleToColumnIndex(n,Q),width:$$1(this).outerWidth()}}),g=0;g<B.length;g++){var q=n.aoColumns[B[g].idx].colEl[0],G=q.style.width.replace("px","");G!==B[g].width&&(q.style.width=B[g].width+"px",e.sX&&(q.style.minWidth=B[g].width+"px"))}}o.find("colgroup").remove(),o.append(n.colgroup.clone()),b&&(d.find("colgroup").remove(),d.append(n.colgroup.clone())),$$1("th, td",E).each(function(){$$1(this.childNodes).wrapAll('<div class="dt-scroll-sizing" />')}),b&&$$1("th, td",C).each(function(){$$1(this.childNodes).wrapAll('<div class="dt-scroll-sizing" />')});var Z=Math.floor(_.height())>s.clientHeight||l.css("overflow-y")=="scroll",te="padding"+(y.bScrollbarLeft?"Left":"Right"),ne=_.outerWidth();o.css("width",_fnStringToCss(ne)),a.css("width",_fnStringToCss(ne)).css(te,Z?t+"px":"0px"),b&&(d.css("width",_fnStringToCss(ne)),f.css("width",_fnStringToCss(ne)).css(te,Z?t+"px":"0px")),_.children("colgroup").prependTo(_),_.find("thead, tfoot").find("[tabindex]").removeAttr("tabindex"),_.find("thead, tfoot").find("role").removeAttr("role"),l.trigger("scroll"),(n.bSorted||n.bFiltered)&&!n._drawHold&&(s.scrollTop=0)}function _fnCalculateColumnWidths(n){if(n.oFeatures.bAutoWidth){var e=n.nTable,t=n.aoColumns,r=n.oScroll,a=r.sY,o=r.sX,s=r.sXInner,l=_fnGetColumns(n,"bVisible"),c=e.getAttribute("width"),f=e.parentNode,d,p,_,b,y=e.style.width,E=_fnWrapperWidth(n);if(E===n.containerWidth)return!1;n.containerWidth=E,!y&&!c&&(e.style.width="100%",y="100%"),y&&y.indexOf("%")!==-1&&(c=y),_fnCallbackFire(n,null,"column-calc",{visible:l},!1);var C=$$1(e.cloneNode()).css("visibility","hidden").css("margin",0).removeAttr("id");C.append("<tbody/>"),C.append($$1(n.nTHead).clone()).append($$1(n.nTFoot).clone()),C.find("tfoot th, tfoot td").css("width",""),C.find("thead th, thead td").each(function(){var re=_fnColumnsSumWidth(n,this,!0);re?(this.style.width=re,o&&(this.style.minWidth=re,$$1(this).append($$1("<div/>").css({width:re,margin:0,padding:0,border:0,height:1})))):this.style.width=""});var D=[];for(d=0;d<l.length;d++)D.push(_fnGetWideStrings(n,l[d]));if(D.length)for(d=0;d<D[0].length;d++){var M=$$1("<tr/>").appendTo(C.find("tbody"));for(p=0;p<l.length;p++){b=l[p],_=t[b];var F=D[p][d]||"",P=_ext.type.className[_.sType],H=_.sContentPadding||(o?"-":""),B=F+H,g=F.indexOf("<")===-1&&F.indexOf("&")===-1?document.createTextNode(B):B;$$1("<td/>").addClass(P).addClass(_.sClass).append(g).appendTo(M)}}$$1("[name]",C).removeAttr("name");var q=$$1("<div/>").css(o||a?{position:"absolute",top:0,left:0,height:1,right:0,overflow:"hidden"}:{}).append(C).appendTo(f);o&&s?C.width(s):o?(C.css("width","auto"),C.removeAttr("width"),C.outerWidth()<f.clientWidth&&c&&C.outerWidth(f.clientWidth)):a?C.outerWidth(f.clientWidth):c&&C.outerWidth(c);var G=0,Z=C.find("tbody tr").eq(0).children();for(d=0;d<l.length;d++){var te=Z[d].getBoundingClientRect().width;G+=te,t[l[d]].sWidth=_fnStringToCss(te)}if(e.style.width=_fnStringToCss(G),q.remove(),c&&(e.style.width=_fnStringToCss(c)),(c||o)&&!n._reszEvt){var ne=DataTable.util.throttle(function(){var re=_fnWrapperWidth(n);!n.bDestroying&&re!==0&&_fnAdjustColumnSizing(n)});if(window.ResizeObserver){var Q=$$1(n.nTableWrapper).is(":visible"),Ee=$$1("<div>").css({width:"100%",height:0}).addClass("dt-autosize").appendTo(n.nTableWrapper);n.resizeObserver=new ResizeObserver(function(re){Q?Q=!1:ne()}),n.resizeObserver.observe(Ee[0])}else $$1(window).on("resize.DT-"+n.sInstance,ne);n._reszEvt=!0}}}function _fnWrapperWidth(n){return $$1(n.nTableWrapper).is(":visible")?$$1(n.nTableWrapper).width():0}function _fnGetWideStrings(n,e){var t=n.aoColumns[e];if(!t.wideStrings){for(var r=[],a=[],o=0,s=n.aiDisplayMaster.length;o<s;o++){var l=n.aiDisplayMaster[o],c=_fnGetRowDisplay(n,l)[e],f=c&&typeof c=="object"&&c.nodeType?c.innerHTML:c+"";f=f.replace(/id=".*?"/g,"").replace(/name=".*?"/g,""),f=f.replace(/<script[\s\S]*?<\/script>/gi," ").replace(/<dialog[\s\S]*?<\/dialog>/gi," ").replace(/<template[\s\S]*?<\/template>/gi," ");var d=_stripHtml(f," ").replace(/&nbsp;/g," ");a.push({str:f,len:d.length}),r.push(d)}a.sort(function(_,b){return b.len-_.len}).splice(3),t.wideStrings=a.map(function(_){return _.str});let p=r.join(" ").split(" ");p.sort(function(_,b){return b.length-_.length}),p.length&&t.wideStrings.push(p[0]),p.length>1&&t.wideStrings.push(p[1]),p.length>2&&t.wideStrings.push(p[3])}return t.wideStrings}function _fnStringToCss(n){return n===null?"0px":typeof n=="number"?n<0?"0px":n+"px":n.match(/\d$/)?n+"px":n}function _colGroup(n){var e=n.aoColumns;for(n.colgroup.empty(),i=0;i<e.length;i++)e[i].bVisible&&n.colgroup.append(e[i].colEl)}function _fnSortInit(n){var e=n.nTHead,t=e.querySelectorAll("tr"),r=n.titleRow,a=':not([data-dt-order="disable"]):not([data-dt-order="icon-only"])';r===!0?e=t[0]:r===!1?e=t[t.length-1]:r!==null&&(e=t[r]),n.orderHandler&&_fnSortAttachListener(n,e,e===n.nTHead?"tr"+a+" th"+a+", tr"+a+" td"+a:"th"+a+", td"+a);var o=[];_fnSortResolve(n,o,n.aaSorting),n.aaSorting=o}function _fnSortAttachListener(n,e,t,r,a){_fnBindAction(e,t,function(o){var s=!1,l=r===void 0?_fnColumnsFromHeader(o.target):typeof r=="function"?r():Array.isArray(r)?r:[r];if(l.length){for(var c=0,f=l.length;c<f;c++){var d=_fnSortAdd(n,l[c],c,o.shiftKey);if(d!==!1&&(s=!0),n.aaSorting.length===1&&n.aaSorting[0][1]==="")break}s&&_fnProcessingRun(n,!0,function(){_fnSort(n),_fnSortDisplay(n,n.aiDisplay),_fnReDraw(n,!1,!1),a&&a()})}})}function _fnSortDisplay(n,e){if(!(e.length<2)){var t=n.aiDisplayMaster,r={},a={},o;for(o=0;o<t.length;o++)r[t[o]]=o;for(o=0;o<e.length;o++)a[e[o]]=r[e[o]];e.sort(function(s,l){return a[s]-a[l]})}}function _fnSortResolve(n,e,t){var r=function(o){if($$1.isPlainObject(o)){if(o.idx!==void 0)e.push([o.idx,o.dir]);else if(o.name){var s=_pluck(n.aoColumns,"sName"),l=s.indexOf(o.name);l!==-1&&e.push([l,o.dir])}}else e.push(o)};if($$1.isPlainObject(t))r(t);else if(t.length&&typeof t[0]=="number")r(t);else if(t.length)for(var a=0;a<t.length;a++)r(t[a])}function _fnSortFlatten(n){var e,t,r,a=[],o=DataTable.ext.type.order,s=n.aoColumns,l,c,f,d,p=n.aaSortingFixed,_=$$1.isPlainObject(p),b=[];if(!n.oFeatures.bSort)return a;for(Array.isArray(p)&&_fnSortResolve(n,b,p),_&&p.pre&&_fnSortResolve(n,b,p.pre),_fnSortResolve(n,b,n.aaSorting),_&&p.post&&_fnSortResolve(n,b,p.post),e=0;e<b.length;e++)if(d=b[e][0],s[d])for(l=s[d].aDataSort,t=0,r=l.length;t<r;t++)c=l[t],f=s[c].sType||"string",b[e]._idx===void 0&&(b[e]._idx=s[c].asSorting.indexOf(b[e][1])),b[e][1]&&a.push({src:d,col:c,dir:b[e][1],index:b[e]._idx,type:f,formatter:o[f+"-pre"],sorter:o[f+"-"+b[e][1]]});return a}function _fnSort(n,e,t){var r,a,o=[],s=DataTable.ext.type.order,l=n.aoData,c,f=n.aiDisplayMaster,d;if(_fnColumnTypes(n),e!==void 0){var p=n.aoColumns[e];d=[{src:e,col:e,dir:t,index:0,type:p.sType,formatter:s[p.sType+"-pre"],sorter:s[p.sType+"-"+t]}],f=f.slice()}else d=_fnSortFlatten(n);for(r=0,a=d.length;r<a;r++)c=d[r],_fnSortData(n,c.col);if(_fnDataSource(n)!="ssp"&&d.length!==0){for(r=0,a=f.length;r<a;r++)o[r]=r;d.length&&d[0].dir==="desc"&&n.orderDescReverse&&o.reverse(),f.sort(function(_,b){var y,E,C,D,M,F=d.length,P=l[_]._aSortData,H=l[b]._aSortData;for(C=0;C<F;C++)if(M=d[C],y=P[M.col],E=H[M.col],M.sorter){if(D=M.sorter(y,E),D!==0)return D}else if(D=y<E?-1:y>E?1:0,D!==0)return M.dir==="asc"?D:-D;return y=o[_],E=o[b],y<E?-1:y>E?1:0})}else d.length===0&&f.sort(function(_,b){return _<b?-1:_>b?1:0});return e===void 0&&(n.bSorted=!0,n.sortDetails=d,_fnCallbackFire(n,null,"order",[n,d])),f}function _fnSortAdd(n,e,t,r){var a=n.aoColumns[e],o=n.aaSorting,s=a.asSorting,l,c=function(d,p){var _=d._idx;return _===void 0&&(_=s.indexOf(d[1])),_+1<s.length?_+1:p?null:0};if(!a.bSortable)return!1;if(typeof o[0]=="number"&&(o=n.aaSorting=[o]),(r||t)&&n.oFeatures.bSortMulti){var f=_pluck(o,"0").indexOf(e);f!==-1?(l=c(o[f],!0),l===null&&o.length===1&&(l=0),l===null||s[l]===""?o.splice(f,1):(o[f][1]=s[l],o[f]._idx=l)):r?(o.push([e,s[0],0]),o[o.length-1]._idx=0):(o.push([e,o[0][1],0]),o[o.length-1]._idx=0)}else o.length&&o[0][0]==e?(l=c(o[0]),o.length=1,o[0][1]=s[l],o[0]._idx=l):(o.length=0,o.push([e,s[0]]),o[0]._idx=0)}function _fnSortingClasses(n){var e=n.aLastSort,t=n.oClasses.order.position,r=_fnSortFlatten(n),a=n.oFeatures,o,s,l;if(a.bSort&&a.bSortClasses){for(o=0,s=e.length;o<s;o++)l=e[o].src,$$1(_pluck(n.aoData,"anCells",l)).removeClass(t+(o<2?o+1:3));for(o=0,s=r.length;o<s;o++)l=r[o].src,$$1(_pluck(n.aoData,"anCells",l)).addClass(t+(o<2?o+1:3))}n.aLastSort=r}function _fnSortData(n,e){var t=n.aoColumns[e],r=DataTable.ext.order[t.sSortDataType],a;r&&(a=r.call(n.oInstance,n,e,_fnColumnIndexToVisible(n,e)));for(var o,s,l=DataTable.ext.type.order[t.sType+"-pre"],c=n.aoData,f=0;f<c.length;f++)c[f]&&(o=c[f],o._aSortData||(o._aSortData=[]),(!o._aSortData[e]||r)&&(s=r?a[f]:_fnGetCellData(n,f,e,"sort"),o._aSortData[e]=l?l(s,n):s))}function _fnSaveState(n){if(!n._bLoadingState){var e=[];_fnSortResolve(n,e,n.aaSorting);var t=n.aoColumns,r={time:+new Date,start:n._iDisplayStart,length:n._iDisplayLength,order:e.map(function(a){return t[a[0]]&&t[a[0]].sName?[t[a[0]].sName,a[1]]:a.slice()}),search:$$1.extend({},n.oPreviousSearch),columns:n.aoColumns.map(function(a,o){return{name:a.sName,visible:a.bVisible,search:$$1.extend({},n.aoPreSearchCols[o])}})};n.oSavedState=r,_fnCallbackFire(n,"aoStateSaveParams","stateSaveParams",[n,r]),n.oFeatures.bStateSave&&!n.bDestroying&&n.fnStateSaveCallback.call(n.oInstance,n,r)}}function _fnLoadState(n,e,t){if(!n.oFeatures.bStateSave){t();return}var r=function(o){_fnImplementState(n,o,t)},a=n.fnStateLoadCallback.call(n.oInstance,n,r);return a!==void 0&&_fnImplementState(n,a,t),!0}function _fnImplementState(n,e,t){var r,a,o=n.aoColumns,s=_pluck(n.aoColumns,"sName");n._bLoadingState=!0;var l=n._bInitComplete?new DataTable.Api(n):null;if(!e||!e.time){n._bLoadingState=!1,t();return}var c=n.iStateDuration;if(c>0&&e.time<+new Date-c*1e3){n._bLoadingState=!1,t();return}var f=_fnCallbackFire(n,"aoStateLoadParams","stateLoadParams",[n,e]);if(f.indexOf(!1)!==-1){n._bLoadingState=!1,t();return}if(n.oLoadedState=$$1.extend(!0,{},e),_fnCallbackFire(n,null,"stateLoadInit",[n,e],!0),e.length!==void 0&&(l?l.page.len(e.length):n._iDisplayLength=e.length),e.start!==void 0&&(l===null?(n._iDisplayStart=e.start,n.iInitDisplayStart=e.start):_fnPageChange(n,e.start/n._iDisplayLength)),e.order!==void 0&&(n.aaSorting=[],$$1.each(e.order,function(y,E){var C=[E[0],E[1]];if(typeof E[0]=="string"){var D=s.indexOf(E[0]);if(D<0)return;C[0]=D}else if(C[0]>=o.length)return;n.aaSorting.push(C)})),e.search!==void 0&&$$1.extend(n.oPreviousSearch,e.search),e.columns){var d=e.columns,p=_pluck(e.columns,"name");if(p.join("").length&&p.join("")!==s.join(""))for(d=[],r=0;r<s.length;r++)if(s[r]!=""){var _=p.indexOf(s[r]);_>=0?d.push(e.columns[_]):d.push({})}else d.push({});if(d.length===o.length){for(r=0,a=d.length;r<a;r++){var b=d[r];b.visible!==void 0&&(l?l.column(r).visible(b.visible,!1):o[r].bVisible=b.visible),b.search!==void 0&&$$1.extend(n.aoPreSearchCols[r],b.search)}l&&l.one("draw",function(){l.columns.adjust()})}}n._bLoadingState=!1,_fnCallbackFire(n,"aoStateLoaded","stateLoaded",[n,e]),t()}function _fnLog(n,e,t,r){t="DataTables warning: "+(n?"table id="+n.sTableId+" - ":"")+t,r&&(t+=". For more information about this error, please see https://datatables.net/tn/"+r);{var a=DataTable.ext,o=a.sErrMode||a.errMode;if(n&&_fnCallbackFire(n,null,"dt-error",[n,r,t],!0),o=="alert")alert(t);else{if(o=="throw")throw new Error(t);typeof o=="function"&&o(n,r,t)}}}function _fnMap(n,e,t,r){if(Array.isArray(t)){$$1.each(t,function(a,o){Array.isArray(o)?_fnMap(n,e,o[0],o[1]):_fnMap(n,e,o)});return}r===void 0&&(r=t),e[t]!==void 0&&(n[r]=e[t])}function _fnExtend(n,e,t){var r;for(var a in e)Object.prototype.hasOwnProperty.call(e,a)&&(r=e[a],$$1.isPlainObject(r)?($$1.isPlainObject(n[a])||(n[a]={}),$$1.extend(!0,n[a],r)):t&&a!=="data"&&a!=="aaData"&&Array.isArray(r)?n[a]=r.slice():n[a]=r);return n}function _fnBindAction(n,e,t){$$1(n).on("click.DT",e,function(r){t(r)}).on("keypress.DT",e,function(r){r.which===13&&(r.preventDefault(),t(r))}).on("selectstart.DT",e,function(){return!1})}function _fnCallbackReg(n,e,t){t&&n[e].push(t)}function _fnCallbackFire(n,e,t,r,a){var o=[];if(e&&(o=n[e].slice().reverse().map(function(c){return c.apply(n.oInstance,r)})),t!==null){var s=$$1.Event(t+".dt"),l=$$1(n.nTable);s.dt=n.api,l[a?"trigger":"triggerHandler"](s,r),a&&l.parents("body").length===0&&$$1("body").trigger(s,r),o.push(s.result)}return o}function _fnLengthOverflow(n){var e=n._iDisplayStart,t=n.fnDisplayEnd(),r=n._iDisplayLength;e>=t&&(e=t-r),e-=e%r,(r===-1||e<0)&&(e=0),n._iDisplayStart=e}function _fnRenderer(n,e){var t=n.renderer,r=DataTable.ext.renderer[e];return $$1.isPlainObject(t)&&t[e]?r[t[e]]||r._:typeof t=="string"&&r[t]||r._}function _fnDataSource(n){return n.oFeatures.bServerSide?"ssp":n.ajax?"ajax":"dom"}function _fnMacros(n,e,t){var r=n.fnFormatNumber,a=n._iDisplayStart+1,o=n._iDisplayLength,s=n.fnRecordsDisplay(),l=n.fnRecordsTotal(),c=o===-1;return e.replace(/_START_/g,r.call(n,a)).replace(/_END_/g,r.call(n,n.fnDisplayEnd())).replace(/_MAX_/g,r.call(n,l)).replace(/_TOTAL_/g,r.call(n,s)).replace(/_PAGE_/g,r.call(n,c?1:Math.ceil(a/o))).replace(/_PAGES_/g,r.call(n,c?1:Math.ceil(s/o))).replace(/_ENTRIES_/g,n.api.i18n("entries","",t)).replace(/_ENTRIES-MAX_/g,n.api.i18n("entries","",l)).replace(/_ENTRIES-TOTAL_/g,n.api.i18n("entries","",s))}function _fnArrayApply(n,e){if(e)if(e.length<1e4)n.push.apply(n,e);else for(i=0;i<e.length;i++)n.push(e[i])}function _fnListener(n,e,t){for(Array.isArray(t)||(t=[t]),i=0;i<t.length;i++)n.on(e+".dt",t[i])}function _fnEscapeObject(n){return DataTable.ext.escape.attributes&&$$1.each(n,function(e,t){n[e]=_escapeHtml(t)}),n}var __apiStruct=[],__arrayProto=Array.prototype,_toSettings=function(n){var e,t,r=DataTable.settings,a=_pluck(r,"nTable");if(n){if(n.nTable&&n.oFeatures)return[n];if(n.nodeName&&n.nodeName.toLowerCase()==="table")return e=a.indexOf(n),e!==-1?[r[e]]:null;if(n&&typeof n.settings=="function")return n.settings().toArray();typeof n=="string"?t=$$1(n).get():n instanceof $$1&&(t=n.get())}else return[];if(t)return r.filter(function(o,s){return t.includes(a[s])})};_Api=function(n,e){if(!(this instanceof _Api))return new _Api(n,e);var t,r=[],a=function(o){var s=_toSettings(o);s&&r.push.apply(r,s)};if(Array.isArray(n))for(t=0;t<n.length;t++)a(n[t]);else a(n);this.context=r.length>1?_unique(r):r,_fnArrayApply(this,e),this.selector={rows:null,cols:null,opts:null},_Api.extend(this,this,__apiStruct)};DataTable.Api=_Api;$$1.extend(_Api.prototype,{any:function(){return this.count()!==0},context:[],count:function(){return this.flatten().length},each:function(n){for(var e=0,t=this.length;e<t;e++)n.call(this,this[e],e,this);return this},eq:function(n){var e=this.context;return e.length>n?new _Api(e[n],this[n]):null},filter:function(n){var e=__arrayProto.filter.call(this,n,this);return new _Api(this.context,e)},flatten:function(){var n=[];return new _Api(this.context,n.concat.apply(n,this.toArray()))},get:function(n){return this[n]},join:__arrayProto.join,includes:function(n){return this.indexOf(n)!==-1},indexOf:__arrayProto.indexOf,iterator:function(n,e,t,r){var a=[],o,s,l,c,f,d=this.context,p,_,b,y=this.selector;for(typeof n=="string"&&(r=t,t=e,e=n,n=!1),s=0,l=d.length;s<l;s++){var E=new _Api(d[s]);if(e==="table")o=t.call(E,d[s],s),o!==void 0&&a.push(o);else if(e==="columns"||e==="rows")o=t.call(E,d[s],this[s],s),o!==void 0&&a.push(o);else if(e==="every"||e==="column"||e==="column-rows"||e==="row"||e==="cell")for(_=this[s],e==="column-rows"&&(p=_selector_row_indexes(d[s],y.opts)),c=0,f=_.length;c<f;c++)b=_[c],e==="cell"?o=t.call(E,d[s],b.row,b.column,s,c):o=t.call(E,d[s],b,s,c,p),o!==void 0&&a.push(o)}if(a.length||r){var C=new _Api(d,n?a.concat.apply([],a):a),D=C.selector;return D.rows=y.rows,D.cols=y.cols,D.opts=y.opts,C}return this},lastIndexOf:__arrayProto.lastIndexOf,length:0,map:function(n){var e=__arrayProto.map.call(this,n,this);return new _Api(this.context,e)},pluck:function(n){var e=DataTable.util.get(n);return this.map(function(t){return e(t)})},pop:__arrayProto.pop,push:__arrayProto.push,reduce:__arrayProto.reduce,reduceRight:__arrayProto.reduceRight,reverse:__arrayProto.reverse,selector:null,shift:__arrayProto.shift,slice:function(){return new _Api(this.context,this)},sort:__arrayProto.sort,splice:__arrayProto.splice,toArray:function(){return __arrayProto.slice.call(this)},to$:function(){return $$1(this)},toJQuery:function(){return $$1(this)},unique:function(){return new _Api(this.context,_unique(this.toArray()))},unshift:__arrayProto.unshift});function _api_scope(n,e,t){return function(){var r=e.apply(n||this,arguments);return _Api.extend(r,r,t.methodExt),r}}function _api_find(n,e){for(var t=0,r=n.length;t<r;t++)if(n[t].name===e)return n[t];return null}window.__apiStruct=__apiStruct;_Api.extend=function(n,e,t){if(!(!t.length||!e||!(e instanceof _Api)&&!e.__dt_wrapper)){var r,a,o;for(r=0,a=t.length;r<a;r++)o=t[r],o.name!=="__proto__"&&(e[o.name]=o.type==="function"?_api_scope(n,o.val,o):o.type==="object"?{}:o.val,e[o.name].__dt_wrapper=!0,_Api.extend(n,e[o.name],o.propExt))}};_Api.register=_api_register=function(n,e){if(Array.isArray(n)){for(var t=0,r=n.length;t<r;t++)_Api.register(n[t],e);return}var a,o,s=n.split("."),l=__apiStruct,c,f;for(a=0,o=s.length;a<o;a++){f=s[a].indexOf("()")!==-1,c=f?s[a].replace("()",""):s[a];var d=_api_find(l,c);d||(d={name:c,val:{},methodExt:[],propExt:[],type:"object"},l.push(d)),a===o-1?(d.val=e,d.type=typeof e=="function"?"function":$$1.isPlainObject(e)?"object":"other"):l=f?d.methodExt:d.propExt}};_Api.registerPlural=_api_registerPlural=function(n,e,t){_Api.register(n,t),_Api.register(e,function(){var r=t.apply(this,arguments);return r===this?this:r instanceof _Api?r.length?Array.isArray(r[0])?new _Api(r.context,r[0]):r[0]:void 0:r})};var __table_selector=function(n,e){if(Array.isArray(n)){var t=[];return n.forEach(function(a){var o=__table_selector(a,e);_fnArrayApply(t,o)}),t.filter(function(a){return a})}if(typeof n=="number")return[e[n]];var r=e.map(function(a){return a.nTable});return $$1(r).filter(n).map(function(){var a=r.indexOf(this);return e[a]}).toArray()};_api_register("tables()",function(n){return n!=null?new _Api(__table_selector(n,this.context)):this});_api_register("table()",function(n){var e=this.tables(n),t=e.context;return t.length?new _Api(t[0]):e});[["nodes","node","nTable"],["body","body","nTBody"],["header","header","nTHead"],["footer","footer","nTFoot"]].forEach(function(n){_api_registerPlural("tables()."+n[0]+"()","table()."+n[1]+"()",function(){return this.iterator("table",function(e){return e[n[2]]},1)})});[["header","aoHeader"],["footer","aoFooter"]].forEach(function(n){_api_register("table()."+n[0]+".structure()",function(e){var t=this.columns(e).indexes().flatten().toArray(),r=this.context[0],a=_fnHeaderLayout(r,r[n[1]],t),o=t.slice().sort(function(s,l){return s-l});return a.map(function(s){return t.map(function(l){return s[o.indexOf(l)]})})})});_api_registerPlural("tables().containers()","table().container()",function(){return this.iterator("table",function(n){return n.nTableWrapper},1)});_api_register("tables().every()",function(n){var e=this;return this.iterator("table",function(t,r){n.call(e.table(r),r)})});_api_register("caption()",function(n,e){var t=this.context;if(n===void 0){var r=t[0].captionNode;return r&&t.length?r.innerHTML:null}return this.iterator("table",function(a){var o=$$1(a.nTable),s=$$1(a.captionNode),l=$$1(a.nTableWrapper);if(s.length||(s=$$1("<caption/>").html(n),a.captionNode=s[0],e||(o.prepend(s),e=s.css("caption-side"))),s.html(n),e&&(s.css("caption-side",e),s[0]._captionSide=e),l.find("div.dataTables_scroll").length){var c=e==="top"?"Head":"Foot";l.find("div.dataTables_scroll"+c+" table").prepend(s)}else o.prepend(s)},1)});_api_register("caption.node()",function(){var n=this.context;return n.length?n[0].captionNode:null});_api_register("draw()",function(n){return this.iterator("table",function(e){n==="page"?_fnDraw(e):(typeof n=="string"&&(n=n!=="full-hold"),_fnReDraw(e,n===!1))})});_api_register("page()",function(n){return n===void 0?this.page.info().page:this.iterator("table",function(e){_fnPageChange(e,n)})});_api_register("page.info()",function(){if(this.context.length!==0){var n=this.context[0],e=n._iDisplayStart,t=n.oFeatures.bPaginate?n._iDisplayLength:-1,r=n.fnRecordsDisplay(),a=t===-1;return{page:a?0:Math.floor(e/t),pages:a?1:Math.ceil(r/t),start:e,end:n.fnDisplayEnd(),length:t,recordsTotal:n.fnRecordsTotal(),recordsDisplay:r,serverSide:_fnDataSource(n)==="ssp"}}});_api_register("page.len()",function(n){return n===void 0?this.context.length!==0?this.context[0]._iDisplayLength:void 0:this.iterator("table",function(e){_fnLengthChange(e,n)})});var __reload=function(n,e,t){if(t){var r=new _Api(n);r.one("draw",function(){t(r.ajax.json())})}if(_fnDataSource(n)=="ssp")_fnReDraw(n,e);else{_fnProcessingDisplay(n,!0);var a=n.jqXHR;a&&a.readyState!==4&&a.abort(),_fnBuildAjax(n,{},function(o){_fnClearTable(n);for(var s=_fnAjaxDataSrc(n,o),l=0,c=s.length;l<c;l++)_fnAddData(n,s[l]);_fnReDraw(n,e),_fnInitComplete(n),_fnProcessingDisplay(n,!1)})}};_api_register("ajax.json()",function(){var n=this.context;if(n.length>0)return n[0].json});_api_register("ajax.params()",function(){var n=this.context;if(n.length>0)return n[0].oAjaxData});_api_register("ajax.reload()",function(n,e){return this.iterator("table",function(t){__reload(t,e===!1,n)})});_api_register("ajax.url()",function(n){var e=this.context;return n===void 0?e.length===0?void 0:(e=e[0],$$1.isPlainObject(e.ajax)?e.ajax.url:e.ajax):this.iterator("table",function(t){$$1.isPlainObject(t.ajax)?t.ajax.url=n:t.ajax=n})});_api_register("ajax.url().load()",function(n,e){return this.iterator("table",function(t){__reload(t,e===!1,n)})});var _selector_run=function(n,e,t,r,a){var o=[],s,l,c,f=typeof e;for((!e||f==="string"||f==="function"||e.length===void 0)&&(e=[e]),l=0,c=e.length;l<c;l++)s=t(typeof e[l]=="string"?e[l].trim():e[l]),s=s.filter(function(p){return p!=null}),s&&s.length&&(o=o.concat(s));var d=_ext.selector[n];if(d.length)for(l=0,c=d.length;l<c;l++)o=d[l](r,a,o);return _unique(o)},_selector_opts=function(n){return n||(n={}),n.filter&&n.search===void 0&&(n.search=n.filter),$$1.extend({columnOrder:"implied",search:"none",order:"current",page:"all"},n)},_selector_first=function(n){var e=new _Api(n.context[0]);return n.length&&e.push(n[0]),e.selector=n.selector,e.length&&e[0].length>1&&e[0].splice(1),e},_selector_row_indexes=function(n,e){var t,r,a,o=[],s=n.aiDisplay,l=n.aiDisplayMaster,c=e.search,f=e.order,d=e.page;if(_fnDataSource(n)=="ssp")return c==="removed"?[]:_range(0,l.length);if(d=="current")for(t=n._iDisplayStart,r=n.fnDisplayEnd();t<r;t++)o.push(s[t]);else if(f=="current"||f=="applied"){if(c=="none")o=l.slice();else if(c=="applied")o=s.slice();else if(c=="removed"){var p={};for(t=0,r=s.length;t<r;t++)p[s[t]]=null;l.forEach(function(b){Object.prototype.hasOwnProperty.call(p,b)||o.push(b)})}}else if(f=="index"||f=="original")for(t=0,r=n.aoData.length;t<r;t++)n.aoData[t]&&(c=="none"?o.push(t):(a=s.indexOf(t),(a===-1&&c=="removed"||a>=0&&c=="applied")&&o.push(t)));else if(typeof f=="number"){var _=_fnSort(n,f,"asc");if(c==="none")o=_;else for(t=0;t<_.length;t++)a=s.indexOf(_[t]),(a===-1&&c=="removed"||a>=0&&c=="applied")&&o.push(_[t])}return o},__row_selector=function(n,e,t){var r,a=function(s){var l=_intVal(s),c=n.aoData;if(l!==null&&!t)return[l];if(r||(r=_selector_row_indexes(n,t)),l!==null&&r.indexOf(l)!==-1)return[l];if(s==null||s==="")return r;if(typeof s=="function")return r.map(function(y){var E=c[y];return s(y,E._aData,E.nTr)?y:null});if(s.nodeName){var f=s._DT_RowIndex,d=s._DT_CellIndex;if(f!==void 0)return c[f]&&c[f].nTr===s?[f]:[];if(d)return c[d.row]&&c[d.row].nTr===s.parentNode?[d.row]:[];var p=$$1(s).closest("*[data-dt-row]");return p.length?[p.data("dt-row")]:[]}if(typeof s=="string"&&s.charAt(0)==="#"){var _=n.aIds[s.replace(/^#/,"")];if(_!==void 0)return[_.idx]}var b=_removeEmpty(_pluck_order(n.aoData,r,"nTr"));return $$1(b).filter(s).map(function(){return this._DT_RowIndex}).toArray()},o=_selector_run("row",e,a,n,t);return(t.order==="current"||t.order==="applied")&&_fnSortDisplay(n,o),o};_api_register("rows()",function(n,e){n===void 0?n="":$$1.isPlainObject(n)&&(e=n,n=""),e=_selector_opts(e);var t=this.iterator("table",function(r){return __row_selector(r,n,e)},1);return t.selector.rows=n,t.selector.opts=e,t});_api_register("rows().nodes()",function(){return this.iterator("row",function(n,e){return n.aoData[e].nTr||void 0},1)});_api_register("rows().data()",function(){return this.iterator(!0,"rows",function(n,e){return _pluck_order(n.aoData,e,"_aData")},1)});_api_registerPlural("rows().cache()","row().cache()",function(n){return this.iterator("row",function(e,t){var r=e.aoData[t];return n==="search"?r._aFilterData:r._aSortData},1)});_api_registerPlural("rows().invalidate()","row().invalidate()",function(n){return this.iterator("row",function(e,t){_fnInvalidate(e,t,n)})});_api_registerPlural("rows().indexes()","row().index()",function(){return this.iterator("row",function(n,e){return e},1)});_api_registerPlural("rows().ids()","row().id()",function(n){for(var e=[],t=this.context,r=0,a=t.length;r<a;r++)for(var o=0,s=this[r].length;o<s;o++){var l=t[r].rowIdFn(t[r].aoData[this[r][o]]._aData);e.push((n===!0?"#":"")+l)}return new _Api(t,e)});_api_registerPlural("rows().remove()","row().remove()",function(){return this.iterator("row",function(n,e){var t=n.aoData,r=t[e],a=n.aiDisplayMaster.indexOf(e);a!==-1&&n.aiDisplayMaster.splice(a,1),n._iRecordsDisplay>0&&n._iRecordsDisplay--,_fnLengthOverflow(n);var o=n.rowIdFn(r._aData);o!==void 0&&delete n.aIds[o],t[e]=null}),this});_api_register("rows.add()",function(n){var e=this.iterator("table",function(r){var a,o,s,l=[];for(o=0,s=n.length;o<s;o++)a=n[o],a.nodeName&&a.nodeName.toUpperCase()==="TR"?l.push(_fnAddTr(r,a)[0]):l.push(_fnAddData(r,a));return l},1),t=this.rows(-1);return t.pop(),_fnArrayApply(t,e),t});_api_register("row()",function(n,e){return _selector_first(this.rows(n,e))});_api_register("row().data()",function(n){var e=this.context;if(n===void 0)return e.length&&this.length&&this[0].length?e[0].aoData[this[0]]._aData:void 0;var t=e[0].aoData[this[0]];return t._aData=n,Array.isArray(n)&&t.nTr&&t.nTr.id&&_fnSetObjectDataFn(e[0].rowId)(n,t.nTr.id),_fnInvalidate(e[0],this[0],"data"),this});_api_register("row().node()",function(){var n=this.context;if(n.length&&this.length&&this[0].length){var e=n[0].aoData[this[0]];if(e&&e.nTr)return e.nTr}return null});_api_register("row.add()",function(n){n instanceof $$1&&n.length&&(n=n[0]);var e=this.iterator("table",function(t){return n.nodeName&&n.nodeName.toUpperCase()==="TR"?_fnAddTr(t,n)[0]:_fnAddData(t,n)});return this.row(e[0])});$$1(document).on("plugin-init.dt",function(n,e){var t=new _Api(e);t.on("stateSaveParams.DT",function(r,a,o){for(var s=a.rowIdFn,l=a.aiDisplayMaster,c=[],f=0;f<l.length;f++){var d=l[f],p=a.aoData[d];p._detailsShow&&c.push("#"+s(p._aData))}o.childRows=c}),t.on("stateLoaded.DT",function(r,a,o){__details_state_load(t,o)}),__details_state_load(t,t.state.loaded())});var __details_state_load=function(n,e){e&&e.childRows&&n.rows(e.childRows.map(function(t){return t.replace(/([^:\\]*(?:\\.[^:\\]*)*):/g,"$1\\:")})).every(function(){_fnCallbackFire(n.settings()[0],null,"requestChild",[this])})},__details_add=function(n,e,t,r){var a=[],o=function(s,l){if(Array.isArray(s)||s instanceof $$1){for(var c=0,f=s.length;c<f;c++)o(s[c],l);return}if(s.nodeName&&s.nodeName.toLowerCase()==="tr")s.setAttribute("data-dt-row",e.idx),a.push(s);else{var d=$$1("<tr><td></td></tr>").attr("data-dt-row",e.idx).addClass(l);$$1("td",d).addClass(l).html(s)[0].colSpan=_fnVisibleColumns(n),a.push(d[0])}};o(t,r),e._details&&e._details.detach(),e._details=$$1(a),e._detailsShow&&e._details.insertAfter(e.nTr)},__details_state=DataTable.util.throttle(function(n){_fnSaveState(n[0])},500),__details_remove=function(n,e){var t=n.context;if(t.length){var r=t[0].aoData[e!==void 0?e:n[0]];r&&r._details&&(r._details.detach(),r._detailsShow=void 0,r._details=void 0,$$1(r.nTr).removeClass("dt-hasChild"),__details_state(t))}},__details_display=function(n,e){var t=n.context;if(t.length&&n.length){var r=t[0].aoData[n[0]];r._details&&(r._detailsShow=e,e?(r._details.insertAfter(r.nTr),$$1(r.nTr).addClass("dt-hasChild")):(r._details.detach(),$$1(r.nTr).removeClass("dt-hasChild")),_fnCallbackFire(t[0],null,"childRow",[e,n.row(n[0])]),__details_events(t[0]),__details_state(t))}},__details_events=function(n){var e=new _Api(n),t=".dt.DT_details",r="draw"+t,a="column-sizing"+t,o="destroy"+t,s=n.aoData;e.off(r+" "+a+" "+o),_pluck(s,"_details").length>0&&(e.on(r,function(l,c){n===c&&e.rows({page:"current"}).eq(0).each(function(f){var d=s[f];d._detailsShow&&d._details.insertAfter(d.nTr)})}),e.on(a,function(l,c){if(n===c)for(var f,d=_fnVisibleColumns(c),p=0,_=s.length;p<_;p++)f=s[p],f&&f._details&&f._details.each(function(){var b=$$1(this).children("td");b.length==1&&b.attr("colspan",d)})}),e.on(o,function(l,c){if(n===c)for(var f=0,d=s.length;f<d;f++)s[f]&&s[f]._details&&__details_remove(e,f)}))},_emp="",_child_obj=_emp+"row().child",_child_mth=_child_obj+"()";_api_register(_child_mth,function(n,e){var t=this.context;return n===void 0?t.length&&this.length&&t[0].aoData[this[0]]?t[0].aoData[this[0]]._details:void 0:(n===!0?this.child.show():n===!1?__details_remove(this):t.length&&this.length&&__details_add(t[0],t[0].aoData[this[0]],n,e),this)});_api_register([_child_obj+".show()",_child_mth+".show()"],function(){return __details_display(this,!0),this});_api_register([_child_obj+".hide()",_child_mth+".hide()"],function(){return __details_display(this,!1),this});_api_register([_child_obj+".remove()",_child_mth+".remove()"],function(){return __details_remove(this),this});_api_register(_child_obj+".isShown()",function(){var n=this.context;return n.length&&this.length&&n[0].aoData[this[0]]&&n[0].aoData[this[0]]._detailsShow||!1});var __re_column_selector=/^([^:]+)?:(name|title|visIdx|visible)$/,__columnData=function(n,e,t,r,a,o){for(var s=[],l=0,c=a.length;l<c;l++)s.push(_fnGetCellData(n,a[l],e,o));return s},__column_header=function(n,e,t){var r=n.aoHeader,a=n.titleRow,o=null;if(t!==void 0)o=t;else if(a===!0)o=0;else if(a===!1)o=r.length-1;else if(a!==null)o=a;else{for(var s=0;s<r.length;s++)r[s][e].unique&&$$1(".dt-column-title",r[s][e].cell).text()&&(o=s);o===null&&(o=0)}return r[o][e].cell},__column_header_cells=function(n){for(var e=[],t=0;t<n.length;t++)for(var r=0;r<n[t].length;r++){var a=n[t][r].cell;e.includes(a)||e.push(a)}return e},__column_selector=function(n,e,t){var r=n.aoColumns,a,o,s=__column_header_cells(n.aoHeader),l=function(f){var d=_intVal(f);if(f==="")return _range(r.length);if(d!==null)return[d>=0?d:r.length+d];if(typeof f=="function"){var p=_selector_row_indexes(n,t);return r.map(function(D,M){return f(M,__columnData(n,M,0,0,p),__column_header(n,M))?M:null})}var _=typeof f=="string"?f.match(__re_column_selector):"";if(_)switch(_[2]){case"visIdx":case"visible":if(_[1]&&_[1].match(/^\d+$/)){var b=parseInt(_[1],10);if(b<0){var y=r.map(function(D,M){return D.bVisible?M:null});return[y[y.length+b]]}return[_fnVisibleToColumnIndex(n,b)]}return r.map(function(D,M){return!D.bVisible||D.responsiveVisible===!1?null:_[1]?$$1(s[M]).filter(_[1]).length>0?M:null:M});case"name":return a||(a=_pluck(r,"sName")),a.map(function(D,M){return D===_[1]?M:null});case"title":return o||(o=_pluck(r,"sTitle")),o.map(function(D,M){return D===_[1]?M:null});default:return[]}if(f.nodeName&&f._DT_CellIndex)return[f._DT_CellIndex.column];var E=$$1(s).filter(f).map(function(){return _fnColumnsFromHeader(this)}).toArray().sort(function(D,M){return D-M});if(E.length||!f.nodeName)return E;var C=$$1(f).closest("*[data-dt-column]");return C.length?[C.data("dt-column")]:[]},c=_selector_run("column",e,l,n,t);return t.columnOrder&&t.columnOrder==="index"?c.sort(function(f,d){return f-d}):c},__setColumnVis=function(n,e,t){var r=n.aoColumns,a=r[e],o=n.aoData,s,l,c,f;if(t===void 0)return a.bVisible;if(a.bVisible===t)return!1;if(t){var d=_pluck(r,"bVisible").indexOf(!0,e+1);for(l=0,c=o.length;l<c;l++)o[l]&&(f=o[l].nTr,s=o[l].anCells,f&&f.insertBefore(s[e],s[d]||null))}else $$1(_pluck(n.aoData,"anCells",e)).detach();return a.bVisible=t,_colGroup(n),!0};_api_register("columns()",function(n,e){n===void 0?n="":$$1.isPlainObject(n)&&(e=n,n=""),e=_selector_opts(e);var t=this.iterator("table",function(r){return __column_selector(r,n,e)},1);return t.selector.cols=n,t.selector.opts=e,t});_api_registerPlural("columns().header()","column().header()",function(n){return this.iterator("column",function(e,t){return __column_header(e,t,n)},1)});_api_registerPlural("columns().footer()","column().footer()",function(n){return this.iterator("column",function(e,t){var r=e.aoFooter;return r.length?e.aoFooter[n!==void 0?n:0][t].cell:null},1)});_api_registerPlural("columns().data()","column().data()",function(){return this.iterator("column-rows",__columnData,1)});_api_registerPlural("columns().render()","column().render()",function(n){return this.iterator("column-rows",function(e,t,r,a,o){return __columnData(e,t,r,a,o,n)},1)});_api_registerPlural("columns().dataSrc()","column().dataSrc()",function(){return this.iterator("column",function(n,e){return n.aoColumns[e].mData},1)});_api_registerPlural("columns().cache()","column().cache()",function(n){return this.iterator("column-rows",function(e,t,r,a,o){return _pluck_order(e.aoData,o,n==="search"?"_aFilterData":"_aSortData",t)},1)});_api_registerPlural("columns().init()","column().init()",function(){return this.iterator("column",function(n,e){return n.aoColumns[e]},1)});_api_registerPlural("columns().names()","column().name()",function(){return this.iterator("column",function(n,e){return n.aoColumns[e].sName},1)});_api_registerPlural("columns().nodes()","column().nodes()",function(){return this.iterator("column-rows",function(n,e,t,r,a){return _pluck_order(n.aoData,a,"anCells",e)},1)});_api_registerPlural("columns().titles()","column().title()",function(n,e){return this.iterator("column",function(t,r){typeof n=="number"&&(e=n,n=void 0);var a=$$1(".dt-column-title",this.column(r).header(e));return n!==void 0?(a.html(n),this):a.html()},1)});_api_registerPlural("columns().types()","column().type()",function(){return this.iterator("column",function(n,e){var t=n.aoColumns[e],r=t.sType;return r||(_fnColumnTypes(n),r=t.sType),r},1)});_api_registerPlural("columns().visible()","column().visible()",function(n,e){var t=this,r=[],a=this.iterator("column",function(o,s){if(n===void 0)return o.aoColumns[s].bVisible;__setColumnVis(o,s,n)&&r.push(s)});return n!==void 0&&this.iterator("table",function(o){_fnDrawHead(o,o.aoHeader),_fnDrawHead(o,o.aoFooter),o.aiDisplay.length||$$1(o.nTBody).find("td[colspan]").attr("colspan",_fnVisibleColumns(o)),_fnSaveState(o),t.iterator("column",function(s,l){r.includes(l)&&_fnCallbackFire(s,null,"column-visibility",[s,l,n,e])}),r.length&&(e===void 0||e)&&t.columns.adjust()}),a});_api_registerPlural("columns().widths()","column().width()",function(){var n=this.columns(":visible").count(),e=$$1("<tr>").html("<td>"+Array(n).join("</td><td>")+"</td>");$$1(this.table().body()).append(e);var t=e.children().map(function(){return $$1(this).outerWidth()});return e.remove(),this.iterator("column",function(r,a){var o=_fnColumnIndexToVisible(r,a);return o!==null?t[o]:0},1)});_api_registerPlural("columns().indexes()","column().index()",function(n){return this.iterator("column",function(e,t){return n==="visible"?_fnColumnIndexToVisible(e,t):t},1)});_api_register("columns.adjust()",function(){return this.iterator("table",function(n){n.containerWidth=-1,_fnAdjustColumnSizing(n)},1)});_api_register("column.index()",function(n,e){if(this.context.length!==0){var t=this.context[0];if(n==="fromVisible"||n==="toData")return _fnVisibleToColumnIndex(t,e);if(n==="fromData"||n==="toVisible")return _fnColumnIndexToVisible(t,e)}});_api_register("column()",function(n,e){return _selector_first(this.columns(n,e))});var __cell_selector=function(n,e,t){var r=n.aoData,a=_selector_row_indexes(n,t),o=_removeEmpty(_pluck_order(r,a,"anCells")),s=$$1(_flatten([],o)),l,c=n.aoColumns.length,f,d,p,_,b,y,E=function(C){var D=typeof C=="function";if(C==null||D){for(f=[],d=0,p=a.length;d<p;d++)for(l=a[d],_=0;_<c;_++)b={row:l,column:_},D?(y=r[l],C(b,_fnGetCellData(n,l,_),y.anCells?y.anCells[_]:null)&&f.push(b)):f.push(b);return f}if($$1.isPlainObject(C))return C.column!==void 0&&C.row!==void 0&&a.indexOf(C.row)!==-1?[C]:[];var M=s.filter(C).map(function(F,P){return{row:P._DT_CellIndex.row,column:P._DT_CellIndex.column}}).toArray();return M.length||!C.nodeName?M:(y=$$1(C).closest("*[data-dt-row]"),y.length?[{row:y.data("dt-row"),column:y.data("dt-column")}]:[])};return _selector_run("cell",e,E,n,t)};_api_register("cells()",function(n,e,t){if($$1.isPlainObject(n)&&(n.row===void 0?(t=n,n=null):(t=e,e=null)),$$1.isPlainObject(e)&&(t=e,e=null),e==null)return this.iterator("table",function(_){return __cell_selector(_,n,_selector_opts(t))});var r=t?{page:t.page,order:t.order,search:t.search}:{},a=this.columns(e,r),o=this.rows(n,r),s,l,c,f,d=this.iterator("table",function(_,b){var y=[];for(s=0,l=o[b].length;s<l;s++)for(c=0,f=a[b].length;c<f;c++)y.push({row:o[b][s],column:a[b][c]});return y},1),p=t&&t.selected?this.cells(d,t):d;return $$1.extend(p.selector,{cols:e,rows:n,opts:t}),p});_api_registerPlural("cells().nodes()","cell().node()",function(){return this.iterator("cell",function(n,e,t){var r=n.aoData[e];return r&&r.anCells?r.anCells[t]:void 0},1)});_api_register("cells().data()",function(){return this.iterator("cell",function(n,e,t){return _fnGetCellData(n,e,t)},1)});_api_registerPlural("cells().cache()","cell().cache()",function(n){return n=n==="search"?"_aFilterData":"_aSortData",this.iterator("cell",function(e,t,r){return e.aoData[t][n][r]},1)});_api_registerPlural("cells().render()","cell().render()",function(n){return this.iterator("cell",function(e,t,r){return _fnGetCellData(e,t,r,n)},1)});_api_registerPlural("cells().indexes()","cell().index()",function(){return this.iterator("cell",function(n,e,t){return{row:e,column:t,columnVisible:_fnColumnIndexToVisible(n,t)}},1)});_api_registerPlural("cells().invalidate()","cell().invalidate()",function(n){return this.iterator("cell",function(e,t,r){_fnInvalidate(e,t,n,r)})});_api_register("cell()",function(n,e,t){return _selector_first(this.cells(n,e,t))});_api_register("cell().data()",function(n){var e=this.context,t=this[0];return n===void 0?e.length&&t.length?_fnGetCellData(e[0],t[0].row,t[0].column):void 0:(_fnSetCellData(e[0],t[0].row,t[0].column,n),_fnInvalidate(e[0],t[0].row,"data",t[0].column),this)});_api_register("order()",function(n,e){var t=this.context,r=Array.prototype.slice.call(arguments);return n===void 0?t.length!==0?t[0].aaSorting:void 0:(typeof n=="number"?n=[[n,e]]:r.length>1&&(n=r),this.iterator("table",function(a){var o=[];_fnSortResolve(a,o,n),a.aaSorting=o}))});_api_register("order.listener()",function(n,e,t){return this.iterator("table",function(r){_fnSortAttachListener(r,n,{},e,t)})});_api_register("order.fixed()",function(n){if(!n){var e=this.context,t=e.length?e[0].aaSortingFixed:void 0;return Array.isArray(t)?{pre:t}:t}return this.iterator("table",function(r){r.aaSortingFixed=$$1.extend(!0,{},n)})});_api_register(["columns().order()","column().order()"],function(n){var e=this;return n?this.iterator("table",function(t,r){t.aaSorting=e[r].map(function(a){return[a,n]})}):this.iterator("column",function(t,r){for(var a=_fnSortFlatten(t),o=0,s=a.length;o<s;o++)if(a[o].col===r)return a[o].dir;return null},1)});_api_registerPlural("columns().orderable()","column().orderable()",function(n){return this.iterator("column",function(e,t){var r=e.aoColumns[t];return n?r.asSorting:r.bSortable},1)});_api_register("processing()",function(n){return this.iterator("table",function(e){_fnProcessingDisplay(e,n)})});_api_register("search()",function(n,e,t,r){var a=this.context;return n===void 0?a.length!==0?a[0].oPreviousSearch.search:void 0:this.iterator("table",function(o){o.oFeatures.bFilter&&(typeof e=="object"?_fnFilterComplete(o,$$1.extend(o.oPreviousSearch,e,{search:n})):_fnFilterComplete(o,$$1.extend(o.oPreviousSearch,{search:n,regex:e===null?!1:e,smart:t===null?!0:t,caseInsensitive:r===null?!0:r})))})});_api_register("search.fixed()",function(n,e){var t=this.iterator(!0,"table",function(r){var a=r.searchFixed;if(n){if(e===void 0)return a[n];e===null?delete a[n]:a[n]=e}else return Object.keys(a);return this});return n!==void 0&&e===void 0?t[0]:t});_api_registerPlural("columns().search()","column().search()",function(n,e,t,r){return this.iterator("column",function(a,o){var s=a.aoPreSearchCols;if(n===void 0)return s[o].search;a.oFeatures.bFilter&&(typeof e=="object"?$$1.extend(s[o],e,{search:n}):$$1.extend(s[o],{search:n,regex:e===null?!1:e,smart:t===null?!0:t,caseInsensitive:r===null?!0:r}),_fnFilterComplete(a,a.oPreviousSearch))})});_api_register(["columns().search.fixed()","column().search.fixed()"],function(n,e){var t=this.iterator(!0,"column",function(r,a){var o=r.aoColumns[a].searchFixed;if(n){if(e===void 0)return o[n]||null;e===null?delete o[n]:o[n]=e}else return Object.keys(o);return this});return n!==void 0&&e===void 0?t[0]:t});_api_register("state()",function(n,e){if(!n)return this.context.length?this.context[0].oSavedState:null;var t=$$1.extend(!0,{},n);return this.iterator("table",function(r){e!==!1&&(t.time=+new Date+100),_fnImplementState(r,t,function(){})})});_api_register("state.clear()",function(){return this.iterator("table",function(n){n.fnStateSaveCallback.call(n.oInstance,n,{})})});_api_register("state.loaded()",function(){return this.context.length?this.context[0].oLoadedState:null});_api_register("state.save()",function(){return this.iterator("table",function(n){_fnSaveState(n)})});var __bootstrap,__foundation;DataTable.use=function(n,e){var t=typeof n=="string"?e:n,r=typeof e=="string"?e:n;if(t===void 0&&typeof r=="string")switch(r){case"lib":case"jq":return $$1;case"win":return window;case"datetime":return DataTable.DateTime;case"luxon":return __luxon;case"moment":return __moment;case"bootstrap":return __bootstrap||window.bootstrap;case"foundation":return __foundation||window.Foundation;default:return null}r==="lib"||r==="jq"||t&&t.fn&&t.fn.jquery?$$1=t:r==="win"||t&&t.document?(window=t,document=t.document):r==="datetime"||t&&t.type==="DateTime"?DataTable.DateTime=t:r==="luxon"||t&&t.FixedOffsetZone?__luxon=t:r==="moment"||t&&t.isMoment?__moment=t:r==="bootstrap"||t&&t.Modal&&t.Modal.NAME==="modal"?__bootstrap=t:(r==="foundation"||t&&t.Reveal)&&(__foundation=t)};DataTable.factory=function(n,e){var t=!1;return n&&n.document&&(window=n,document=n.document),e&&e.fn&&e.fn.jquery&&($$1=e,t=!0),t};DataTable.versionCheck=function(n,e){for(var t=e?e.split("."):DataTable.version.split("."),r=n.split("."),a,o,s=0,l=r.length;s<l;s++)if(a=parseInt(t[s],10)||0,o=parseInt(r[s],10)||0,a!==o)return a>o;return!0};DataTable.isDataTable=function(n){var e=$$1(n).get(0),t=!1;return n instanceof DataTable.Api?!0:($$1.each(DataTable.settings,function(r,a){var o=a.nScrollHead?$$1("table",a.nScrollHead)[0]:null,s=a.nScrollFoot?$$1("table",a.nScrollFoot)[0]:null;(a.nTable===e||o===e||s===e)&&(t=!0)}),t)};DataTable.tables=function(n){var e=!1;$$1.isPlainObject(n)&&(e=n.api,n=n.visible);var t=DataTable.settings.filter(function(r){return!!(!n||n&&$$1(r.nTable).is(":visible"))}).map(function(r){return r.nTable});return e?new _Api(t):t};DataTable.camelToHungarian=_fnCamelToHungarian;_api_register("$()",function(n,e){var t=this.rows(e).nodes(),r=$$1(t);return $$1([].concat(r.filter(n).toArray(),r.find(n).toArray()))});$$1.each(["on","one","off"],function(n,e){_api_register(e+"()",function(){var t=Array.prototype.slice.call(arguments);t[0]=t[0].split(/\s/).map(function(a){return a.match(/\.dt\b/)?a:a+".dt"}).join(" ");var r=$$1(this.tables().nodes());return r[e].apply(r,t),this})});_api_register("clear()",function(){return this.iterator("table",function(n){_fnClearTable(n)})});_api_register("error()",function(n){return this.iterator("table",function(e){_fnLog(e,0,n)})});_api_register("settings()",function(){return new _Api(this.context,this.context)});_api_register("init()",function(){var n=this.context;return n.length?n[0].oInit:null});_api_register("data()",function(){return this.iterator("table",function(n){return _pluck(n.aoData,"_aData")}).flatten()});_api_register("trigger()",function(n,e,t){return this.iterator("table",function(r){return _fnCallbackFire(r,null,n,e,t)}).flatten()});_api_register("ready()",function(n){var e=this.context;return n?this.tables().every(function(){var t=this;this.context[0]._bInitComplete?n.call(t):this.on("init.dt.DT",function(){n.call(t)})}):e.length?e[0]._bInitComplete||!1:null});_api_register("destroy()",function(n){return n=n||!1,this.iterator("table",function(e){var t=e.oClasses,r=e.nTable,a=e.nTBody,o=e.nTHead,s=e.nTFoot,l=$$1(r),c=$$1(a),f=$$1(e.nTableWrapper),d=e.aoData.map(function(C){return C?C.nTr:null}),p=t.order;e.bDestroying=!0,_fnCallbackFire(e,"aoDestroyCallback","destroy",[e],!0),n||new _Api(e).columns().visible(!0),e.resizeObserver&&e.resizeObserver.disconnect(),f.off(".DT").find(":not(tbody *)").off(".DT"),$$1(window).off(".DT-"+e.sInstance),r!=o.parentNode&&(l.children("thead").detach(),l.append(o)),s&&r!=s.parentNode&&(l.children("tfoot").detach(),l.append(s)),cleanHeader(o,"header"),cleanHeader(s,"footer"),e.colgroup.remove(),e.aaSorting=[],e.aaSortingFixed=[],_fnSortingClasses(e),$$1(l).find("th, td").removeClass($$1.map(DataTable.ext.type.className,function(C){return C}).join(" ")),$$1("th, td",o).removeClass(p.none+" "+p.canAsc+" "+p.canDesc+" "+p.isAsc+" "+p.isDesc).css("width","").removeAttr("aria-sort"),c.children().detach(),c.append(d);var _=e.nTableWrapper.parentNode,b=e.nTableWrapper.nextSibling,y=n?"remove":"detach";l[y](),f[y](),!n&&_&&(_.insertBefore(r,b),l.css("width",e.sDestroyWidth).removeClass(t.table));var E=DataTable.settings.indexOf(e);E!==-1&&DataTable.settings.splice(E,1)})});$$1.each(["column","row","cell"],function(n,e){_api_register(e+"s().every()",function(t){var r=this.selector.opts,a=this,o,s=0;return this.iterator("every",function(l,c,f){o=a[e](c,r),e==="cell"?t.call(o,o[0][0].row,o[0][0].column,f,s):t.call(o,c,f,s),s++})})});_api_register("i18n()",function(n,e,t){var r=this.context[0],a=_fnGetObjectDataFn(n)(r.oLanguage);return a===void 0&&(a=e),$$1.isPlainObject(a)&&(a=t!==void 0&&a[t]!==void 0?a[t]:t===!1?a:a._),typeof a=="string"?a.replace("%d",t):a});function cleanHeader(n,e){$$1(n).find(".dt-column-order").remove(),$$1(n).find(".dt-column-title").each(function(){var t=$$1(this).html();$$1(this).parent().parent().append(t),$$1(this).remove()}),$$1(n).find("div.dt-column-"+e).remove(),$$1("th, td",n).removeAttr("data-dt-column")}DataTable.version="2.3.8";DataTable.settings=[];DataTable.models={};DataTable.models.oSearch={caseInsensitive:!0,search:"",regex:!1,smart:!0,return:!1};DataTable.models.oRow={nTr:null,anCells:null,_aData:[],_aSortData:null,_aFilterData:null,_sFilterRow:null,src:null,idx:-1,displayData:null};DataTable.models.oColumn={idx:null,aDataSort:null,asSorting:null,bSearchable:null,bSortable:null,bVisible:null,_sManualType:null,_bAttrSrc:!1,fnCreatedCell:null,fnGetData:null,fnSetData:null,mData:null,mRender:null,sClass:null,sContentPadding:null,sDefaultContent:null,sName:null,sSortDataType:"std",sSortingClass:null,sTitle:null,sType:null,sWidth:null,sWidthOrig:null,wideStrings:null,searchFixed:null};DataTable.defaults={aaData:null,aaSorting:[[0,"asc"]],aaSortingFixed:[],ajax:null,aLengthMenu:[10,25,50,100],aoColumns:null,aoColumnDefs:null,aoSearchCols:[],bAutoWidth:!0,bDeferRender:!0,bDestroy:!1,bFilter:!0,bInfo:!0,bLengthChange:!0,bPaginate:!0,bProcessing:!1,bRetrieve:!1,bScrollCollapse:!1,bServerSide:!1,bSort:!0,bSortMulti:!0,bSortCellsTop:null,titleRow:null,bSortClasses:!0,bStateSave:!1,fnCreatedRow:null,fnDrawCallback:null,fnFooterCallback:null,fnFormatNumber:function(n){return n.toString().replace(/\B(?=(\d{3})+(?!\d))/g,this.oLanguage.sThousands)},fnHeaderCallback:null,fnInfoCallback:null,fnInitComplete:null,fnPreDrawCallback:null,fnRowCallback:null,fnStateLoadCallback:function(n){try{return JSON.parse((n.iStateDuration===-1?sessionStorage:localStorage).getItem("DataTables_"+n.sInstance+"_"+location.pathname))}catch{return{}}},fnStateLoadParams:null,fnStateLoaded:null,fnStateSaveCallback:function(n,e){try{(n.iStateDuration===-1?sessionStorage:localStorage).setItem("DataTables_"+n.sInstance+"_"+location.pathname,JSON.stringify(e))}catch{}},fnStateSaveParams:null,iStateDuration:7200,iDisplayLength:10,iDisplayStart:0,iTabIndex:0,oClasses:{},oLanguage:{oAria:{orderable:": Activate to sort",orderableReverse:": Activate to invert sorting",orderableRemove:": Activate to remove sorting",paginate:{first:"First",last:"Last",next:"Next",previous:"Previous",number:""}},oPaginate:{sFirst:"«",sLast:"»",sNext:"›",sPrevious:"‹"},entries:{_:"entries",1:"entry"},lengthLabels:{"-1":"All"},sEmptyTable:"No data available in table",sInfo:"Showing _START_ to _END_ of _TOTAL_ _ENTRIES-TOTAL_",sInfoEmpty:"Showing 0 to 0 of 0 _ENTRIES-TOTAL_",sInfoFiltered:"(filtered from _MAX_ total _ENTRIES-MAX_)",sInfoPostFix:"",sDecimal:"",sThousands:",",sLengthMenu:"_MENU_ _ENTRIES_ per page",sLoadingRecords:"Loading...",sProcessing:"",sSearch:"Search:",sSearchPlaceholder:"",sUrl:"",sZeroRecords:"No matching records found"},orderDescReverse:!0,oSearch:$$1.extend({},DataTable.models.oSearch),layout:{topStart:"pageLength",topEnd:"search",bottomStart:"info",bottomEnd:"paging"},sDom:null,searchDelay:null,sPaginationType:"",sScrollX:"",sScrollXInner:"",sScrollY:"",sServerMethod:"GET",renderer:null,rowId:"DT_RowId",caption:null,iDeferLoading:null,on:null,columnTitleTag:"span"};_fnHungarianMap(DataTable.defaults);DataTable.defaults.column={aDataSort:null,iDataSort:-1,ariaTitle:"",asSorting:["asc","desc",""],bSearchable:!0,bSortable:!0,bVisible:!0,fnCreatedCell:null,mData:null,mRender:null,sCellType:"td",sClass:"",sContentPadding:"",sDefaultContent:null,sName:"",sSortDataType:"std",sTitle:null,sType:null,sWidth:null};_fnHungarianMap(DataTable.defaults.column);DataTable.models.oSettings={oFeatures:{bAutoWidth:null,bDeferRender:null,bFilter:null,bInfo:!0,bLengthChange:!0,bPaginate:null,bProcessing:null,bServerSide:null,bSort:null,bSortMulti:null,bSortClasses:null,bStateSave:null},oScroll:{bCollapse:null,iBarWidth:0,sX:null,sXInner:null,sY:null},oLanguage:{fnInfoCallback:null},oBrowser:{bScrollbarLeft:!1,barWidth:0},ajax:null,aanFeatures:[],aoData:[],aiDisplay:[],aiDisplayMaster:[],aIds:{},aoColumns:[],aoHeader:[],aoFooter:[],oPreviousSearch:{},searchFixed:{},aoPreSearchCols:[],aaSorting:null,aaSortingFixed:[],sDestroyWidth:0,aoRowCallback:[],aoHeaderCallback:[],aoFooterCallback:[],aoDrawCallback:[],aoRowCreatedCallback:[],aoPreDrawCallback:[],aoInitComplete:[],aoStateSaveParams:[],aoStateLoadParams:[],aoStateLoaded:[],sTableId:"",nTable:null,nTHead:null,nTFoot:null,nTBody:null,nTableWrapper:null,bInitialised:!1,aoOpenRows:[],sDom:null,searchDelay:null,sPaginationType:"two_button",pagingControls:0,iStateDuration:0,aoStateSave:[],aoStateLoad:[],oSavedState:null,oLoadedState:null,bAjaxDataGet:!0,jqXHR:null,json:void 0,oAjaxData:void 0,sServerMethod:null,fnFormatNumber:null,aLengthMenu:null,iDraw:0,bDrawing:!1,iDrawError:-1,_iDisplayLength:10,_iDisplayStart:0,_iRecordsTotal:0,_iRecordsDisplay:0,oClasses:{},bFiltered:!1,bSorted:!1,bSortCellsTop:null,oInit:null,aoDestroyCallback:[],fnRecordsTotal:function(){return _fnDataSource(this)=="ssp"?this._iRecordsTotal*1:this.aiDisplayMaster.length},fnRecordsDisplay:function(){return _fnDataSource(this)=="ssp"?this._iRecordsDisplay*1:this.aiDisplay.length},fnDisplayEnd:function(){var n=this._iDisplayLength,e=this._iDisplayStart,t=e+n,r=this.aiDisplay.length,a=this.oFeatures,o=a.bPaginate;return a.bServerSide?o===!1||n===-1?e+r:Math.min(e+n,this._iRecordsDisplay):!o||t>r||n===-1?r:t},oInstance:null,sInstance:null,iTabIndex:0,nScrollHead:null,nScrollFoot:null,aLastSort:[],oPlugins:{},rowIdFn:null,rowId:null,caption:"",captionNode:null,colgroup:null,deferLoading:null,typeDetect:!0,resizeObserver:null,containerWidth:-1,orderDescReverse:null,orderIndicators:!0,orderHandler:!0,titleRow:null,columnTitleTag:"span"};var extPagination=DataTable.ext.pager;$$1.extend(extPagination,{simple:function(){return["previous","next"]},full:function(){return["first","previous","next","last"]},numbers:function(){return["numbers"]},simple_numbers:function(){return["previous","numbers","next"]},full_numbers:function(){return["first","previous","numbers","next","last"]},first_last:function(){return["first","last"]},first_last_numbers:function(){return["first","numbers","last"]},_numbers:_pagingNumbers,numbers_length:7});$$1.extend(!0,DataTable.ext.renderer,{pagingButton:{_:function(n,e,t,r,a){var o=n.oClasses.paging,s=[o.button],l;return r&&s.push(o.active),a&&s.push(o.disabled),e==="ellipsis"?l=$$1('<span class="ellipsis"></span>').html(t)[0]:l=$$1("<button>",{class:s.join(" "),role:"link",type:"button"}).html(t),{display:l,clicker:l}}},pagingContainer:{_:function(n,e){return e}}});var _filterString=function(n,e){return function(t){return _empty(t)||typeof t!="string"||(t=t.replace(_re_new_lines," "),n&&(t=_stripHtml(t)),t=_normalize(t,!1)),t}};function __mld(n,e,t,r,a){return __moment?n[e](a):__luxon?n[t](a):r?n[r](a):n}var __mlWarning=!1,__luxon,__moment,__reIsoTimezone=/[T\s]\d{2}.*?(Z|[+-]\d{2}(?::?\d{2})?)$/;function resolveWindowLibs(){window.luxon&&!__luxon&&(__luxon=window.luxon),window.moment&&!__moment&&(__moment=window.moment)}function __mldObj(n,e,t){var r;if(resolveWindowLibs(),__moment){if(r=__moment(n,e,t,!0),!r.isValid())return null}else if(__luxon){if(r=e&&typeof n=="string"?__luxon.DateTime.fromFormat(n,e):__luxon.DateTime.fromISO(n),!r.isValid)return null;r=r.setLocale(t)}else e?(__mlWarning||alert("DataTables warning: Formatted date without Moment.js or Luxon - https://datatables.net/tn/17"),__mlWarning=!0):r=new Date(n);return r}function __mlHelper(n){return function(e,t,r,a){arguments.length===0?(r="en",t=null,e=null):arguments.length===1?(r="en",t=e,e=null):arguments.length===2&&(r=t,t=e,e=null);var o="datetime"+(t?"-"+t:"");return DataTable.ext.type.order[o+"-pre"]||DataTable.type(o,{detect:function(s){return s===o?o:!1},order:{pre:function(s){return s.valueOf()}},className:"dt-right"}),function(s,l){if(s==null)if(a==="--now"){var c=new Date;s=new Date(Date.UTC(c.getFullYear(),c.getMonth(),c.getDate(),c.getHours(),c.getMinutes(),c.getSeconds()))}else s="";if(l==="type")return o;if(s==="")return l!=="sort"?"":__mldObj("0000-01-01 00:00:00",null,r);if(t!==null&&e===t&&l!=="sort"&&l!=="type"&&!(s instanceof Date))return s;let f={},d=typeof s=="string"?s.match(__reIsoTimezone):null;d&&(f.timeZone=d[1]==="Z"?"UTC":d[1]);var p=__mldObj(s,e,r);if(p===null)return s;if(l==="sort")return p;var _=t===null?__mld(p,"toDate","toJSDate","")[n](navigator.language,f):__mld(p,"format","toFormat","toISOString",t);return l==="display"?_escapeHtml(_):_}}}var __thousands=",",__decimal=".";if(window.Intl!==void 0)try{for(var num=new Intl.NumberFormat().formatToParts(100000.1),i=0;i<num.length;i++)num[i].type==="group"?__thousands=num[i].value:num[i].type==="decimal"&&(__decimal=num[i].value)}catch{}DataTable.datetime=function(n,e){var t="datetime-"+n;e||(e="en"),DataTable.ext.type.order[t]||DataTable.type(t,{detect:function(r){var a=__mldObj(r,n,e);return r===""||a?t:!1},order:{pre:function(r){return __mldObj(r,n,e)||0}},className:"dt-right"})};DataTable.render={date:__mlHelper("toLocaleDateString"),datetime:__mlHelper("toLocaleString"),time:__mlHelper("toLocaleTimeString"),number:function(n,e,t,r,a){return n==null&&(n=__thousands),e==null&&(e=__decimal),{display:function(o){if(typeof o!="number"&&typeof o!="string"||o===""||o===null)return o;var s=o<0?"-":"",l=parseFloat(o),c=Math.abs(l);if(c>=1e11||c<1e-4&&c!==0){var f=l.toExponential(t).split(/e\+?/);return f[0]+" x 10<sup>"+f[1]+"</sup>"}if(isNaN(l))return _escapeHtml(o);l=l.toFixed(t),o=Math.abs(l);var d=parseInt(o,10),p=t?e+(o-d).toFixed(t).substring(2):"";return d===0&&parseFloat(p)===0&&(s=""),s+(r||"")+d.toString().replace(/\B(?=(\d{3})+(?!\d))/g,n)+p+(a||"")}}},text:function(){return{display:_escapeHtml,filter:_escapeHtml}}};var _extTypes=DataTable.ext.type;DataTable.type=function(n,e,t){if(!e)return{className:_extTypes.className[n],detect:_extTypes.detect.find(function(s){return s._name===n}),order:{pre:_extTypes.order[n+"-pre"],asc:_extTypes.order[n+"-asc"],desc:_extTypes.order[n+"-desc"]},render:_extTypes.render[n],search:_extTypes.search[n]};var r=function(s,l){_extTypes[s][n]=l},a=function(s){Object.defineProperty(s,"_name",{value:n});var l=_extTypes.detect.findIndex(function(c){return c._name===n});l===-1?_extTypes.detect.unshift(s):_extTypes.detect.splice(l,1,s)},o=function(s){_extTypes.order[n+"-pre"]=s.pre,_extTypes.order[n+"-asc"]=s.asc,_extTypes.order[n+"-desc"]=s.desc};t===void 0&&(t=e,e=null),e==="className"?r("className",t):e==="detect"?a(t):e==="order"?o(t):e==="render"?r("render",t):e==="search"?r("search",t):e||(t.className&&r("className",t.className),t.detect!==void 0&&a(t.detect),t.order&&o(t.order),t.render!==void 0&&r("render",t.render),t.search!==void 0&&r("search",t.search))};DataTable.types=function(){return _extTypes.detect.map(function(n){return n._name})};var __diacriticSort=function(n,e){return n=n!=null?n.toString().toLowerCase():"",e=e!=null?e.toString().toLowerCase():"",n.localeCompare(e,navigator.languages[0]||navigator.language,{numeric:!0,ignorePunctuation:!0})},__diacriticHtmlSort=function(n,e){return n=_stripHtml(n),e=_stripHtml(e),__diacriticSort(n,e)};DataTable.type("string",{detect:function(){return"string"},order:{pre:function(n){return _empty(n)&&typeof n!="boolean"?"":typeof n=="string"?n.toLowerCase():n.toString?n.toString():""}},search:_filterString(!1)});DataTable.type("string-utf8",{detect:{allOf:function(n){return!0},oneOf:function(n){return!_empty(n)&&navigator.languages&&typeof n=="string"&&n.match(/[^\x00-\x7F]/)}},order:{asc:__diacriticSort,desc:function(n,e){return __diacriticSort(n,e)*-1}},search:_filterString(!1)});DataTable.type("html",{detect:{allOf:function(n){return _empty(n)||typeof n=="string"&&n.indexOf("<")!==-1},oneOf:function(n){return!_empty(n)&&typeof n=="string"&&n.indexOf("<")!==-1}},order:{pre:function(n){return _empty(n)?"":n.replace?_stripHtml(n).trim().toLowerCase():n+""}},search:_filterString(!0)});DataTable.type("html-utf8",{detect:{allOf:function(n){return _empty(n)||typeof n=="string"&&n.indexOf("<")!==-1},oneOf:function(n){return navigator.languages&&!_empty(n)&&typeof n=="string"&&n.indexOf("<")!==-1&&typeof n=="string"&&n.match(/[^\x00-\x7F]/)}},order:{asc:__diacriticHtmlSort,desc:function(n,e){return __diacriticHtmlSort(n,e)*-1}},search:_filterString(!0)});DataTable.type("date",{className:"dt-type-date",detect:{allOf:function(n){if(n&&!(n instanceof Date)&&!_re_date.test(n))return null;var e=Date.parse(n);return e!==null&&!isNaN(e)||_empty(n)},oneOf:function(n){return n instanceof Date||typeof n=="string"&&_re_date.test(n)}},order:{pre:function(n){var e=Date.parse(n);return isNaN(e)?-1/0:e}}});DataTable.type("html-num-fmt",{className:"dt-type-numeric",detect:{allOf:function(n,e){var t=e.oLanguage.sDecimal;return _htmlNumeric(n,t,!0,!1)},oneOf:function(n,e){var t=e.oLanguage.sDecimal;return _htmlNumeric(n,t,!0,!1)}},order:{pre:function(n,e){var t=e.oLanguage.sDecimal;return __numericReplace(n,t,_re_html,_re_formatted_numeric)}},search:_filterString(!0)});DataTable.type("html-num",{className:"dt-type-numeric",detect:{allOf:function(n,e){var t=e.oLanguage.sDecimal;return _htmlNumeric(n,t,!1,!0)},oneOf:function(n,e){var t=e.oLanguage.sDecimal;return _htmlNumeric(n,t,!1,!1)}},order:{pre:function(n,e){var t=e.oLanguage.sDecimal;return __numericReplace(n,t,_re_html)}},search:_filterString(!0)});DataTable.type("num-fmt",{className:"dt-type-numeric",detect:{allOf:function(n,e){var t=e.oLanguage.sDecimal;return _isNumber(n,t,!0,!0)},oneOf:function(n,e){var t=e.oLanguage.sDecimal;return _isNumber(n,t,!0,!1)}},order:{pre:function(n,e){var t=e.oLanguage.sDecimal;return __numericReplace(n,t,_re_formatted_numeric)}}});DataTable.type("num",{className:"dt-type-numeric",detect:{allOf:function(n,e){var t=e.oLanguage.sDecimal;return _isNumber(n,t,!1,!0)},oneOf:function(n,e){var t=e.oLanguage.sDecimal;return _isNumber(n,t,!1,!1)}},order:{pre:function(n,e){var t=e.oLanguage.sDecimal;return __numericReplace(n,t)}}});var __numericReplace=function(n,e,t,r){if(n!==0&&(!n||n==="-"))return-1/0;var a=typeof n;return a==="number"||a==="bigint"?n:(e&&(n=_numToDecimal(n,e)),n.replace&&(t&&(n=n.replace(t,"")),r&&(n=n.replace(r,""))),n*1)};$$1.extend(!0,DataTable.ext.renderer,{footer:{_:function(n,e,t){e.addClass(t.tfoot.cell)}},header:{_:function(n,e,t){e.addClass(t.thead.cell),n.oFeatures.bSort||e.addClass(t.order.none);var r=n.titleRow,a=e.closest("thead").find("tr"),o=e.parent().index();e.attr("data-dt-order")==="disable"||e.parent().attr("data-dt-order")==="disable"||r===!0&&o!==0||r===!1&&o!==a.length-1||typeof r=="number"&&o!==r||$$1(n.nTable).on("order.dt.DT column-visibility.dt.DT",function(s,l,c){if(n===l){var f=l.sortDetails;if(f){var d=_pluck(f,"col");if(!(s.type==="column-visibility"&&!d.includes(c))){var p,_=t.order,b=l.api.columns(e),y=n.aoColumns[b.flatten()[0]],E=b.orderable().includes(!0),C="",D=b.indexes(),M=b.orderable(!0).flatten(),F=n.iTabIndex,P=l.orderHandler&&E;e.removeClass(_.isAsc+" "+_.isDesc).toggleClass(_.none,!E).toggleClass(_.canAsc,P&&M.includes("asc")).toggleClass(_.canDesc,P&&M.includes("desc"));var H=!0;for(p=0;p<D.length;p++)d.includes(D[p])||(H=!1);if(H){var B=b.order();e.addClass(B.includes("asc")?_.isAsc:""+B.includes("desc")?_.isDesc:"")}var g=-1;for(p=0;p<d.length;p++)if(n.aoColumns[d[p]].bVisible){g=d[p];break}if(D[0]==g){var q=f[0],G=y.asSorting;e.attr("aria-sort",q.dir==="asc"?"ascending":"descending"),C=G[q.index+1]?"Reverse":"Remove"}else e.removeAttr("aria-sort");if(E){var Z=e.find(".dt-column-order");Z.attr("role","button").attr("aria-label",E?y.ariaTitle+l.api.i18n("oAria.orderable"+C):y.ariaTitle),F!==-1&&Z.attr("tabindex",F)}}}}})}},layout:{_:function(n,e,t){var r=n.oClasses.layout,a=$$1("<div/>").attr("id",t.id||null).addClass(t.className||r.row).appendTo(e);DataTable.ext.renderer.layout._forLayoutRow(t,function(o,s){if(!(o==="id"||o==="className")){var l="";s.table&&(a.addClass(r.tableRow),l+=r.tableCell+" "),o==="start"?l+=r.start:o==="end"?l+=r.end:l+=r.full,$$1("<div/>").attr({id:s.id||null,class:s.className?s.className:r.cell+" "+l}).append(s.contents).appendTo(a)}})},_forLayoutRow:function(n,e){var t=function(r){switch(r){case"":return 0;case"start":return 1;case"end":return 2;default:return 3}};Object.keys(n).sort(function(r,a){return t(r)-t(a)}).forEach(function(r){e(r,n[r])})}}});DataTable.feature={};DataTable.feature.register=function(n,e,t){DataTable.ext.features[n]=e,t&&_ext.feature.push({cFeature:t,fnInit:e})};function _divProp(n,e,t){t&&(n[e]=t)}DataTable.feature.register("div",function(n,e){var t=$$1("<div>")[0];return e&&(_divProp(t,"className",e.className),_divProp(t,"id",e.id),_divProp(t,"innerHTML",e.html),_divProp(t,"textContent",e.text)),t});DataTable.feature.register("info",function(n,e){if(!n.oFeatures.bInfo)return null;var t=n.oLanguage,r=n.sTableId,a=$$1("<div/>",{class:n.oClasses.info.container});return e=$$1.extend({callback:t.fnInfoCallback,empty:t.sInfoEmpty,postfix:t.sInfoPostFix,search:t.sInfoFiltered,text:t.sInfo},e),n.aoDrawCallback.push(function(o){_fnUpdateInfo(o,e,a)}),n._infoEl||(a.attr({"aria-live":"polite",id:r+"_info",role:"status"}),$$1(n.nTable).attr("aria-describedby",r+"_info"),n._infoEl=a),a},"i");function _fnUpdateInfo(n,e,t){var r=n._iDisplayStart+1,a=n.fnDisplayEnd(),o=n.fnRecordsTotal(),s=n.fnRecordsDisplay(),l=s?e.text:e.empty;s!==o&&(l+=" "+e.search),l+=e.postfix,l=_fnMacros(n,l),e.callback&&(l=e.callback.call(n.oInstance,n,r,a,o,s,l)),t.html(l),_fnCallbackFire(n,null,"info",[n,t[0],l])}var __searchCounter=0;DataTable.feature.register("search",function(n,e){if(!n.oFeatures.bFilter)return null;var t=n.oClasses.search,r=n.sTableId,a=n.oLanguage,o=n.oPreviousSearch,s='<input type="search" class="'+t.input+'"/>';e=$$1.extend({placeholder:a.sSearchPlaceholder,processing:!1,text:a.sSearch},e),e.text.indexOf("_INPUT_")===-1&&(e.text+="_INPUT_"),e.text=_fnMacros(n,e.text);var l=e.text.match(/_INPUT_$/),c=e.text.match(/^_INPUT_/),f=e.text.replace(/_INPUT_/,""),d="<label>"+e.text+"</label>";c?d="_INPUT_<label>"+f+"</label>":l&&(d="<label>"+f+"</label>_INPUT_");var p=$$1("<div>").addClass(t.container).append(d.replace(/_INPUT_/,s));p.find("label").attr("for","dt-search-"+__searchCounter),p.find("input").attr("id","dt-search-"+__searchCounter),__searchCounter++;var _=function(E){var C=this.value;o.return&&E.key!=="Enter"||C!=o.search&&_fnProcessingRun(n,e.processing,function(){o.search=C,_fnFilterComplete(n,o),n._iDisplayStart=0,_fnDraw(n)})},b=n.searchDelay!==null?n.searchDelay:0,y=$$1("input",p).val(o.search).attr("placeholder",e.placeholder).on("keyup.DT search.DT input.DT paste.DT cut.DT",b?DataTable.util.debounce(_,b):_).on("mouseup.DT",function(E){setTimeout(function(){_.call(y[0],E)},10)}).on("keypress.DT",function(E){if(E.keyCode==13)return!1}).attr("aria-controls",r);return $$1(n.nTable).on("search.dt.DT",function(E,C){n===C&&y[0]!==document.activeElement&&y.val(typeof o.search!="function"?o.search:"")}),p},"f");DataTable.feature.register("paging",function(n,e){if(!n.oFeatures.bPaginate)return null;e=$$1.extend({buttons:DataTable.ext.pager.numbers_length,type:n.sPaginationType,boundaryNumbers:!0,firstLast:!0,previousNext:!0,numbers:!0},e);var t=$$1("<div/>").addClass(n.oClasses.paging.container+(e.type?" paging_"+e.type:"")).append($$1("<nav>").attr("aria-label","pagination").addClass(n.oClasses.paging.nav)),r=function(){_pagingDraw(n,t.children(),e)};return n.aoDrawCallback.push(r),$$1(n.nTable).on("column-sizing.dt.DT",r),t},"p");function _pagingDynamic(n){var e=[];return n.numbers&&e.push("numbers"),n.previousNext&&(e.unshift("previous"),e.push("next")),n.firstLast&&(e.unshift("first"),e.push("last")),e}function _pagingDraw(n,e,t){if(n._bInitComplete){var r=t.type?DataTable.ext.pager[t.type]:_pagingDynamic,a=n.oLanguage.oAria.paginate||{},o=n._iDisplayStart,s=n._iDisplayLength,l=n.fnRecordsDisplay(),c=s===-1,f=c?0:Math.ceil(o/s),d=c?1:Math.ceil(l/s),p=[],_=[],b=r(t).map(function(B){return B==="numbers"?_pagingNumbers(f,d,t.buttons,t.boundaryNumbers):B});p=p.concat.apply(p,b);for(var y=0;y<p.length;y++){var E=p[y],C=_pagingButtonInfo(n,E,f,d),D=_fnRenderer(n,"pagingButton")(n,E,C.display,C.active,C.disabled),M=typeof E=="string"?a[E]:a.number?a.number+(E+1):null;$$1(D.clicker).attr({"aria-controls":n.sTableId,"aria-disabled":C.disabled?"true":null,"aria-current":C.active?"page":null,"aria-label":M,"data-dt-idx":E,tabIndex:C.disabled?-1:n.iTabIndex&&D.clicker[0].nodeName.toLowerCase()!=="span"?n.iTabIndex:null}),typeof E!="number"&&$$1(D.clicker).addClass(E),_fnBindAction(D.clicker,{action:E},function(B){B.preventDefault(),_fnPageChange(n,B.data.action,!0)}),_.push(D.display)}var F=_fnRenderer(n,"pagingContainer")(n,_),P=e.find(document.activeElement).data("dt-idx");if(e.empty().append(F),P!==void 0&&e.find("[data-dt-idx="+P+"]").trigger("focus"),_.length){var H=$$1(_[0]).outerHeight();t.buttons>1&&H>0&&$$1(e).height()>=H*2-10&&_pagingDraw(n,e,$$1.extend({},t,{buttons:t.buttons-2}))}}}function _pagingButtonInfo(n,e,t,r){var a=n.oLanguage.oPaginate,o={display:"",active:!1,disabled:!1};switch(e){case"ellipsis":o.display="&#x2026;";break;case"first":o.display=a.sFirst,t===0&&(o.disabled=!0);break;case"previous":o.display=a.sPrevious,t===0&&(o.disabled=!0);break;case"next":o.display=a.sNext,(r===0||t===r-1)&&(o.disabled=!0);break;case"last":o.display=a.sLast,(r===0||t===r-1)&&(o.disabled=!0);break;default:typeof e=="number"&&(o.display=n.fnFormatNumber(e+1),t===e&&(o.active=!0));break}return o}function _pagingNumbers(n,e,t,r){var a=[],o=Math.floor(t/2),s=r?2:1,l=r?1:0;return e<=t?a=_range(0,e):t===1?a=[n]:t===3?n<=1?a=[0,1,"ellipsis"]:n>=e-2?(a=_range(e-2,e),a.unshift("ellipsis")):a=["ellipsis",n,"ellipsis"]:n<=o?(a=_range(0,t-s),a.push("ellipsis"),r&&a.push(e-1)):n>=e-1-o?(a=_range(e-(t-s),e),a.unshift("ellipsis"),r&&a.unshift(0)):(a=_range(n-o+s,n+o-l),a.push("ellipsis"),a.unshift("ellipsis"),r&&(a.push(e-1),a.unshift(0))),a}var __lengthCounter=0;DataTable.feature.register("pageLength",function(n,e){var t=n.oFeatures;if(!t.bPaginate||!t.bLengthChange)return null;e=$$1.extend({menu:n.aLengthMenu,text:n.oLanguage.sLengthMenu},e);var r=n.oClasses.length,a=n.sTableId,o=e.menu,s=[],l=[],c;if(Array.isArray(o[0]))s=o[0],l=o[1];else for(c=0;c<o.length;c++)$$1.isPlainObject(o[c])?(s.push(o[c].value),l.push(o[c].label)):(s.push(o[c]),l.push(o[c]));var f=e.text.match(/_MENU_$/),d=e.text.match(/^_MENU_/),p=e.text.replace(/_MENU_/,""),_="<label>"+e.text+"</label>";d?_="_MENU_<label>"+p+"</label>":f&&(_="<label>"+p+"</label>_MENU_");var b="tmp-"+ +new Date,y=$$1("<div/>").addClass(r.container).append(_.replace("_MENU_",'<span id="'+b+'"></span>')),E=[];Array.prototype.slice.call(y.find("label")[0].childNodes).forEach(function(F){F.nodeType===Node.TEXT_NODE&&E.push({el:F,text:F.textContent})});var C=function(F){E.forEach(function(P){P.el.textContent=_fnMacros(n,P.text,F)})},D=$$1("<select/>",{"aria-controls":a,class:r.select});for(c=0;c<s.length;c++){var M=n.api.i18n("lengthLabels."+s[c],null);M===null&&(M=typeof l[c]=="number"?n.fnFormatNumber(l[c]):l[c]),D[0][c]=new Option(M,s[c])}return y.find("label").attr("for","dt-length-"+__lengthCounter),D.attr("id","dt-length-"+__lengthCounter),__lengthCounter++,y.find("#"+b).replaceWith(D),$$1("select",y).val(n._iDisplayLength).on("change.DT",function(){_fnLengthChange(n,$$1(this).val()),_fnDraw(n)}),$$1(n.nTable).on("length.dt.DT",function(F,P,H){n===P&&($$1("select",y).val(H),C(H))}),C(n._iDisplayLength),y},"l");$$1.fn.dataTable=DataTable;DataTable.$=$$1;$$1.fn.dataTableSettings=DataTable.settings;$$1.fn.dataTableExt=DataTable.ext;$$1.fn.DataTable=function(n){return $$1(this).dataTable(n).api()};$$1.each(DataTable,function(n,e){$$1.fn.DataTable[n]=e});let $=jQuery$1;$.extend(!0,DataTable.defaults,{renderer:"bootstrap"});$.extend(!0,DataTable.ext.classes,{container:"dt-container dt-bootstrap5",search:{input:"form-control form-control-sm"},length:{select:"form-select form-select-sm"},processing:{container:"dt-processing card"},layout:{row:"row mt-2 justify-content-between",cell:"d-md-flex justify-content-between align-items-center",tableCell:"col-12",start:"dt-layout-start col-md-auto me-auto",end:"dt-layout-end col-md-auto ms-auto",full:"dt-layout-full col-md"}});DataTable.ext.renderer.pagingButton.bootstrap=function(n,e,t,r,a){var o=["dt-paging-button","page-item"];r&&o.push("active"),a&&o.push("disabled");var s=$("<li>").addClass(o.join(" ")),l=$("<button>",{class:"page-link",role:"link",type:"button"}).html(t).appendTo(s);return{display:s,clicker:l}};DataTable.ext.renderer.pagingContainer.bootstrap=function(n,e){return $("<ul/>").addClass("pagination").append(e)};function initDataTable(){const n=document.querySelectorAll("div.table-responsive > table.datatable");for(const t of n)t!==null&&new DataTable(t,{pageLength:10,orderClasses:!1,order:[[1,"desc"]]});const e=document.querySelectorAll("div.table-responsive > table.datatable-long");for(const t of e)t!==null&&new DataTable(t,{pageLength:50,orderClasses:!1,order:[[1,"desc"]]})}function round(n){return n+.5|0}const lim=(n,e,t)=>Math.max(Math.min(n,t),e);function p2b(n){return lim(round(n*2.55),0,255)}function n2b(n){return lim(round(n*255),0,255)}function b2n(n){return lim(round(n/2.55)/100,0,1)}function n2p(n){return lim(round(n*100),0,100)}const map$1={0:0,1:1,2:2,3:3,4:4,5:5,6:6,7:7,8:8,9:9,A:10,B:11,C:12,D:13,E:14,F:15,a:10,b:11,c:12,d:13,e:14,f:15},hex=[..."0123456789ABCDEF"],h1=n=>hex[n&15],h2=n=>hex[(n&240)>>4]+hex[n&15],eq=n=>(n&240)>>4===(n&15),isShort=n=>eq(n.r)&&eq(n.g)&&eq(n.b)&&eq(n.a);function hexParse(n){var e=n.length,t;return n[0]==="#"&&(e===4||e===5?t={r:255&map$1[n[1]]*17,g:255&map$1[n[2]]*17,b:255&map$1[n[3]]*17,a:e===5?map$1[n[4]]*17:255}:(e===7||e===9)&&(t={r:map$1[n[1]]<<4|map$1[n[2]],g:map$1[n[3]]<<4|map$1[n[4]],b:map$1[n[5]]<<4|map$1[n[6]],a:e===9?map$1[n[7]]<<4|map$1[n[8]]:255})),t}const alpha=(n,e)=>n<255?e(n):"";function hexString(n){var e=isShort(n)?h1:h2;return n?"#"+e(n.r)+e(n.g)+e(n.b)+alpha(n.a,e):void 0}const HUE_RE=/^(hsla?|hwb|hsv)\(\s*([-+.e\d]+)(?:deg)?[\s,]+([-+.e\d]+)%[\s,]+([-+.e\d]+)%(?:[\s,]+([-+.e\d]+)(%)?)?\s*\)$/;function hsl2rgbn(n,e,t){const r=e*Math.min(t,1-t),a=(o,s=(o+n/30)%12)=>t-r*Math.max(Math.min(s-3,9-s,1),-1);return[a(0),a(8),a(4)]}function hsv2rgbn(n,e,t){const r=(a,o=(a+n/60)%6)=>t-t*e*Math.max(Math.min(o,4-o,1),0);return[r(5),r(3),r(1)]}function hwb2rgbn(n,e,t){const r=hsl2rgbn(n,1,.5);let a;for(e+t>1&&(a=1/(e+t),e*=a,t*=a),a=0;a<3;a++)r[a]*=1-e-t,r[a]+=e;return r}function hueValue(n,e,t,r,a){return n===a?(e-t)/r+(e<t?6:0):e===a?(t-n)/r+2:(n-e)/r+4}function rgb2hsl(n){const t=n.r/255,r=n.g/255,a=n.b/255,o=Math.max(t,r,a),s=Math.min(t,r,a),l=(o+s)/2;let c,f,d;return o!==s&&(d=o-s,f=l>.5?d/(2-o-s):d/(o+s),c=hueValue(t,r,a,d,o),c=c*60+.5),[c|0,f||0,l]}function calln(n,e,t,r){return(Array.isArray(e)?n(e[0],e[1],e[2]):n(e,t,r)).map(n2b)}function hsl2rgb(n,e,t){return calln(hsl2rgbn,n,e,t)}function hwb2rgb(n,e,t){return calln(hwb2rgbn,n,e,t)}function hsv2rgb(n,e,t){return calln(hsv2rgbn,n,e,t)}function hue(n){return(n%360+360)%360}function hueParse(n){const e=HUE_RE.exec(n);let t=255,r;if(!e)return;e[5]!==r&&(t=e[6]?p2b(+e[5]):n2b(+e[5]));const a=hue(+e[2]),o=+e[3]/100,s=+e[4]/100;return e[1]==="hwb"?r=hwb2rgb(a,o,s):e[1]==="hsv"?r=hsv2rgb(a,o,s):r=hsl2rgb(a,o,s),{r:r[0],g:r[1],b:r[2],a:t}}function rotate(n,e){var t=rgb2hsl(n);t[0]=hue(t[0]+e),t=hsl2rgb(t),n.r=t[0],n.g=t[1],n.b=t[2]}function hslString(n){if(!n)return;const e=rgb2hsl(n),t=e[0],r=n2p(e[1]),a=n2p(e[2]);return n.a<255?`hsla(${t}, ${r}%, ${a}%, ${b2n(n.a)})`:`hsl(${t}, ${r}%, ${a}%)`}const map$2={x:"dark",Z:"light",Y:"re",X:"blu",W:"gr",V:"medium",U:"slate",A:"ee",T:"ol",S:"or",B:"ra",C:"lateg",D:"ights",R:"in",Q:"turquois",E:"hi",P:"ro",O:"al",N:"le",M:"de",L:"yello",F:"en",K:"ch",G:"arks",H:"ea",I:"ightg",J:"wh"},names$1={OiceXe:"f0f8ff",antiquewEte:"faebd7",aqua:"ffff",aquamarRe:"7fffd4",azuY:"f0ffff",beige:"f5f5dc",bisque:"ffe4c4",black:"0",blanKedOmond:"ffebcd",Xe:"ff",XeviTet:"8a2be2",bPwn:"a52a2a",burlywood:"deb887",caMtXe:"5f9ea0",KartYuse:"7fff00",KocTate:"d2691e",cSO:"ff7f50",cSnflowerXe:"6495ed",cSnsilk:"fff8dc",crimson:"dc143c",cyan:"ffff",xXe:"8b",xcyan:"8b8b",xgTMnPd:"b8860b",xWay:"a9a9a9",xgYF:"6400",xgYy:"a9a9a9",xkhaki:"bdb76b",xmagFta:"8b008b",xTivegYF:"556b2f",xSange:"ff8c00",xScEd:"9932cc",xYd:"8b0000",xsOmon:"e9967a",xsHgYF:"8fbc8f",xUXe:"483d8b",xUWay:"2f4f4f",xUgYy:"2f4f4f",xQe:"ced1",xviTet:"9400d3",dAppRk:"ff1493",dApskyXe:"bfff",dimWay:"696969",dimgYy:"696969",dodgerXe:"1e90ff",fiYbrick:"b22222",flSOwEte:"fffaf0",foYstWAn:"228b22",fuKsia:"ff00ff",gaRsbSo:"dcdcdc",ghostwEte:"f8f8ff",gTd:"ffd700",gTMnPd:"daa520",Way:"808080",gYF:"8000",gYFLw:"adff2f",gYy:"808080",honeyMw:"f0fff0",hotpRk:"ff69b4",RdianYd:"cd5c5c",Rdigo:"4b0082",ivSy:"fffff0",khaki:"f0e68c",lavFMr:"e6e6fa",lavFMrXsh:"fff0f5",lawngYF:"7cfc00",NmoncEffon:"fffacd",ZXe:"add8e6",ZcSO:"f08080",Zcyan:"e0ffff",ZgTMnPdLw:"fafad2",ZWay:"d3d3d3",ZgYF:"90ee90",ZgYy:"d3d3d3",ZpRk:"ffb6c1",ZsOmon:"ffa07a",ZsHgYF:"20b2aa",ZskyXe:"87cefa",ZUWay:"778899",ZUgYy:"778899",ZstAlXe:"b0c4de",ZLw:"ffffe0",lime:"ff00",limegYF:"32cd32",lRF:"faf0e6",magFta:"ff00ff",maPon:"800000",VaquamarRe:"66cdaa",VXe:"cd",VScEd:"ba55d3",VpurpN:"9370db",VsHgYF:"3cb371",VUXe:"7b68ee",VsprRggYF:"fa9a",VQe:"48d1cc",VviTetYd:"c71585",midnightXe:"191970",mRtcYam:"f5fffa",mistyPse:"ffe4e1",moccasR:"ffe4b5",navajowEte:"ffdead",navy:"80",Tdlace:"fdf5e6",Tive:"808000",TivedBb:"6b8e23",Sange:"ffa500",SangeYd:"ff4500",ScEd:"da70d6",pOegTMnPd:"eee8aa",pOegYF:"98fb98",pOeQe:"afeeee",pOeviTetYd:"db7093",papayawEp:"ffefd5",pHKpuff:"ffdab9",peru:"cd853f",pRk:"ffc0cb",plum:"dda0dd",powMrXe:"b0e0e6",purpN:"800080",YbeccapurpN:"663399",Yd:"ff0000",Psybrown:"bc8f8f",PyOXe:"4169e1",saddNbPwn:"8b4513",sOmon:"fa8072",sandybPwn:"f4a460",sHgYF:"2e8b57",sHshell:"fff5ee",siFna:"a0522d",silver:"c0c0c0",skyXe:"87ceeb",UXe:"6a5acd",UWay:"708090",UgYy:"708090",snow:"fffafa",sprRggYF:"ff7f",stAlXe:"4682b4",tan:"d2b48c",teO:"8080",tEstN:"d8bfd8",tomato:"ff6347",Qe:"40e0d0",viTet:"ee82ee",JHt:"f5deb3",wEte:"ffffff",wEtesmoke:"f5f5f5",Lw:"ffff00",LwgYF:"9acd32"};function unpack(){const n={},e=Object.keys(names$1),t=Object.keys(map$2);let r,a,o,s,l;for(r=0;r<e.length;r++){for(s=l=e[r],a=0;a<t.length;a++)o=t[a],l=l.replace(o,map$2[o]);o=parseInt(names$1[s],16),n[l]=[o>>16&255,o>>8&255,o&255]}return n}let names;function nameParse(n){names||(names=unpack(),names.transparent=[0,0,0,0]);const e=names[n.toLowerCase()];return e&&{r:e[0],g:e[1],b:e[2],a:e.length===4?e[3]:255}}const RGB_RE=/^rgba?\(\s*([-+.\d]+)(%)?[\s,]+([-+.e\d]+)(%)?[\s,]+([-+.e\d]+)(%)?(?:[\s,/]+([-+.e\d]+)(%)?)?\s*\)$/;function rgbParse(n){const e=RGB_RE.exec(n);let t=255,r,a,o;if(e){if(e[7]!==r){const s=+e[7];t=e[8]?p2b(s):lim(s*255,0,255)}return r=+e[1],a=+e[3],o=+e[5],r=255&(e[2]?p2b(r):lim(r,0,255)),a=255&(e[4]?p2b(a):lim(a,0,255)),o=255&(e[6]?p2b(o):lim(o,0,255)),{r,g:a,b:o,a:t}}}function rgbString(n){return n&&(n.a<255?`rgba(${n.r}, ${n.g}, ${n.b}, ${b2n(n.a)})`:`rgb(${n.r}, ${n.g}, ${n.b})`)}const to=n=>n<=.0031308?n*12.92:Math.pow(n,1/2.4)*1.055-.055,from=n=>n<=.04045?n/12.92:Math.pow((n+.055)/1.055,2.4);function interpolate$1(n,e,t){const r=from(b2n(n.r)),a=from(b2n(n.g)),o=from(b2n(n.b));return{r:n2b(to(r+t*(from(b2n(e.r))-r))),g:n2b(to(a+t*(from(b2n(e.g))-a))),b:n2b(to(o+t*(from(b2n(e.b))-o))),a:n.a+t*(e.a-n.a)}}function modHSL(n,e,t){if(n){let r=rgb2hsl(n);r[e]=Math.max(0,Math.min(r[e]+r[e]*t,e===0?360:1)),r=hsl2rgb(r),n.r=r[0],n.g=r[1],n.b=r[2]}}function clone$1(n,e){return n&&Object.assign(e||{},n)}function fromObject(n){var e={r:0,g:0,b:0,a:255};return Array.isArray(n)?n.length>=3&&(e={r:n[0],g:n[1],b:n[2],a:255},n.length>3&&(e.a=n2b(n[3]))):(e=clone$1(n,{r:0,g:0,b:0,a:1}),e.a=n2b(e.a)),e}function functionParse(n){return n.charAt(0)==="r"?rgbParse(n):hueParse(n)}class Color{constructor(e){if(e instanceof Color)return e;const t=typeof e;let r;t==="object"?r=fromObject(e):t==="string"&&(r=hexParse(e)||nameParse(e)||functionParse(e)),this._rgb=r,this._valid=!!r}get valid(){return this._valid}get rgb(){var e=clone$1(this._rgb);return e&&(e.a=b2n(e.a)),e}set rgb(e){this._rgb=fromObject(e)}rgbString(){return this._valid?rgbString(this._rgb):void 0}hexString(){return this._valid?hexString(this._rgb):void 0}hslString(){return this._valid?hslString(this._rgb):void 0}mix(e,t){if(e){const r=this.rgb,a=e.rgb;let o;const s=t===o?.5:t,l=2*s-1,c=r.a-a.a,f=((l*c===-1?l:(l+c)/(1+l*c))+1)/2;o=1-f,r.r=255&f*r.r+o*a.r+.5,r.g=255&f*r.g+o*a.g+.5,r.b=255&f*r.b+o*a.b+.5,r.a=s*r.a+(1-s)*a.a,this.rgb=r}return this}interpolate(e,t){return e&&(this._rgb=interpolate$1(this._rgb,e._rgb,t)),this}clone(){return new Color(this.rgb)}alpha(e){return this._rgb.a=n2b(e),this}clearer(e){const t=this._rgb;return t.a*=1-e,this}greyscale(){const e=this._rgb,t=round(e.r*.3+e.g*.59+e.b*.11);return e.r=e.g=e.b=t,this}opaquer(e){const t=this._rgb;return t.a*=1+e,this}negate(){const e=this._rgb;return e.r=255-e.r,e.g=255-e.g,e.b=255-e.b,this}lighten(e){return modHSL(this._rgb,2,e),this}darken(e){return modHSL(this._rgb,2,-e),this}saturate(e){return modHSL(this._rgb,1,e),this}desaturate(e){return modHSL(this._rgb,1,-e),this}rotate(e){return rotate(this._rgb,e),this}}function noop(){}const uid=(()=>{let n=0;return()=>n++})();function isNullOrUndef(n){return n==null}function isArray(n){if(Array.isArray&&Array.isArray(n))return!0;const e=Object.prototype.toString.call(n);return e.slice(0,7)==="[object"&&e.slice(-6)==="Array]"}function isObject(n){return n!==null&&Object.prototype.toString.call(n)==="[object Object]"}function isNumberFinite(n){return(typeof n=="number"||n instanceof Number)&&isFinite(+n)}function finiteOrDefault(n,e){return isNumberFinite(n)?n:e}function valueOrDefault(n,e){return typeof n>"u"?e:n}const toPercentage=(n,e)=>typeof n=="string"&&n.endsWith("%")?parseFloat(n)/100:+n/e,toDimension=(n,e)=>typeof n=="string"&&n.endsWith("%")?parseFloat(n)/100*e:+n;function callback(n,e,t){if(n&&typeof n.call=="function")return n.apply(t,e)}function each(n,e,t,r){let a,o,s;if(isArray(n))for(o=n.length,a=0;a<o;a++)e.call(t,n[a],a);else if(isObject(n))for(s=Object.keys(n),o=s.length,a=0;a<o;a++)e.call(t,n[s[a]],s[a])}function _elementsEqual(n,e){let t,r,a,o;if(!n||!e||n.length!==e.length)return!1;for(t=0,r=n.length;t<r;++t)if(a=n[t],o=e[t],a.datasetIndex!==o.datasetIndex||a.index!==o.index)return!1;return!0}function clone(n){if(isArray(n))return n.map(clone);if(isObject(n)){const e=Object.create(null),t=Object.keys(n),r=t.length;let a=0;for(;a<r;++a)e[t[a]]=clone(n[t[a]]);return e}return n}function isValidKey(n){return["__proto__","prototype","constructor"].indexOf(n)===-1}function _merger(n,e,t,r){if(!isValidKey(n))return;const a=e[n],o=t[n];isObject(a)&&isObject(o)?merge(a,o,r):e[n]=clone(o)}function merge(n,e,t){const r=isArray(e)?e:[e],a=r.length;if(!isObject(n))return n;t=t||{};const o=t.merger||_merger;let s;for(let l=0;l<a;++l){if(s=r[l],!isObject(s))continue;const c=Object.keys(s);for(let f=0,d=c.length;f<d;++f)o(c[f],n,s,t)}return n}function mergeIf(n,e){return merge(n,e,{merger:_mergerIf})}function _mergerIf(n,e,t){if(!isValidKey(n))return;const r=e[n],a=t[n];isObject(r)&&isObject(a)?mergeIf(r,a):Object.prototype.hasOwnProperty.call(e,n)||(e[n]=clone(a))}const keyResolvers={"":n=>n,x:n=>n.x,y:n=>n.y};function _splitKey(n){const e=n.split("."),t=[];let r="";for(const a of e)r+=a,r.endsWith("\\")?r=r.slice(0,-1)+".":(t.push(r),r="");return t}function _getKeyResolver(n){const e=_splitKey(n);return t=>{for(const r of e){if(r==="")break;t=t&&t[r]}return t}}function resolveObjectKey(n,e){return(keyResolvers[e]||(keyResolvers[e]=_getKeyResolver(e)))(n)}function _capitalize(n){return n.charAt(0).toUpperCase()+n.slice(1)}const defined=n=>typeof n<"u",isFunction=n=>typeof n=="function",setsEqual=(n,e)=>{if(n.size!==e.size)return!1;for(const t of n)if(!e.has(t))return!1;return!0};function _isClickEvent(n){return n.type==="mouseup"||n.type==="click"||n.type==="contextmenu"}const PI=Math.PI,TAU=2*PI,PITAU=TAU+PI,INFINITY=Number.POSITIVE_INFINITY,RAD_PER_DEG=PI/180,HALF_PI=PI/2,QUARTER_PI=PI/4,TWO_THIRDS_PI=PI*2/3,log10=Math.log10,sign=Math.sign;function almostEquals(n,e,t){return Math.abs(n-e)<t}function niceNum(n){const e=Math.round(n);n=almostEquals(n,e,n/1e3)?e:n;const t=Math.pow(10,Math.floor(log10(n))),r=n/t;return(r<=1?1:r<=2?2:r<=5?5:10)*t}function _factorize(n){const e=[],t=Math.sqrt(n);let r;for(r=1;r<t;r++)n%r===0&&(e.push(r),e.push(n/r));return t===(t|0)&&e.push(t),e.sort((a,o)=>a-o).pop(),e}function isNonPrimitive(n){return typeof n=="symbol"||typeof n=="object"&&n!==null&&!(Symbol.toPrimitive in n||"toString"in n||"valueOf"in n)}function isNumber(n){return!isNonPrimitive(n)&&!isNaN(parseFloat(n))&&isFinite(n)}function almostWhole(n,e){const t=Math.round(n);return t-e<=n&&t+e>=n}function _setMinAndMaxByKey(n,e,t){let r,a,o;for(r=0,a=n.length;r<a;r++)o=n[r][t],isNaN(o)||(e.min=Math.min(e.min,o),e.max=Math.max(e.max,o))}function toRadians(n){return n*(PI/180)}function toDegrees(n){return n*(180/PI)}function _decimalPlaces(n){if(!isNumberFinite(n))return;let e=1,t=0;for(;Math.round(n*e)/e!==n;)e*=10,t++;return t}function getAngleFromPoint(n,e){const t=e.x-n.x,r=e.y-n.y,a=Math.sqrt(t*t+r*r);let o=Math.atan2(r,t);return o<-.5*PI&&(o+=TAU),{angle:o,distance:a}}function distanceBetweenPoints(n,e){return Math.sqrt(Math.pow(e.x-n.x,2)+Math.pow(e.y-n.y,2))}function _angleDiff(n,e){return(n-e+PITAU)%TAU-PI}function _normalizeAngle(n){return(n%TAU+TAU)%TAU}function _angleBetween(n,e,t,r){const a=_normalizeAngle(n),o=_normalizeAngle(e),s=_normalizeAngle(t),l=_normalizeAngle(o-a),c=_normalizeAngle(s-a),f=_normalizeAngle(a-o),d=_normalizeAngle(a-s);return a===o||a===s||r&&o===s||l>c&&f<d}function _limitValue(n,e,t){return Math.max(e,Math.min(t,n))}function _int16Range(n){return _limitValue(n,-32768,32767)}function _isBetween(n,e,t,r=1e-6){return n>=Math.min(e,t)-r&&n<=Math.max(e,t)+r}function _lookup(n,e,t){t=t||(s=>n[s]<e);let r=n.length-1,a=0,o;for(;r-a>1;)o=a+r>>1,t(o)?a=o:r=o;return{lo:a,hi:r}}const _lookupByKey=(n,e,t,r)=>_lookup(n,t,r?a=>{const o=n[a][e];return o<t||o===t&&n[a+1][e]===t}:a=>n[a][e]<t),_rlookupByKey=(n,e,t)=>_lookup(n,t,r=>n[r][e]>=t);function _filterBetween(n,e,t){let r=0,a=n.length;for(;r<a&&n[r]<e;)r++;for(;a>r&&n[a-1]>t;)a--;return r>0||a<n.length?n.slice(r,a):n}const arrayEvents=["push","pop","shift","splice","unshift"];function listenArrayEvents(n,e){if(n._chartjs){n._chartjs.listeners.push(e);return}Object.defineProperty(n,"_chartjs",{configurable:!0,enumerable:!1,value:{listeners:[e]}}),arrayEvents.forEach(t=>{const r="_onData"+_capitalize(t),a=n[t];Object.defineProperty(n,t,{configurable:!0,enumerable:!1,value(...o){const s=a.apply(this,o);return n._chartjs.listeners.forEach(l=>{typeof l[r]=="function"&&l[r](...o)}),s}})})}function unlistenArrayEvents(n,e){const t=n._chartjs;if(!t)return;const r=t.listeners,a=r.indexOf(e);a!==-1&&r.splice(a,1),!(r.length>0)&&(arrayEvents.forEach(o=>{delete n[o]}),delete n._chartjs)}function _arrayUnique(n){const e=new Set(n);return e.size===n.length?n:Array.from(e)}const requestAnimFrame=(function(){return typeof window>"u"?function(n){return n()}:window.requestAnimationFrame})();function throttled(n,e){let t=[],r=!1;return function(...a){t=a,r||(r=!0,requestAnimFrame.call(window,()=>{r=!1,n.apply(e,t)}))}}function debounce(n,e){let t;return function(...r){return e?(clearTimeout(t),t=setTimeout(n,e,r)):n.apply(this,r),e}}const _toLeftRightCenter=n=>n==="start"?"left":n==="end"?"right":"center",_alignStartEnd=(n,e,t)=>n==="start"?e:n==="end"?t:(e+t)/2,_textX=(n,e,t,r)=>n===(r?"left":"right")?t:n==="center"?(e+t)/2:e;function _getStartAndCountOfVisiblePoints(n,e,t){const r=e.length;let a=0,o=r;if(n._sorted){const{iScale:s,vScale:l,_parsed:c}=n,f=n.dataset&&n.dataset.options?n.dataset.options.spanGaps:null,d=s.axis,{min:p,max:_,minDefined:b,maxDefined:y}=s.getUserBounds();if(b){if(a=Math.min(_lookupByKey(c,d,p).lo,t?r:_lookupByKey(e,d,s.getPixelForValue(p)).lo),f){const E=c.slice(0,a+1).reverse().findIndex(C=>!isNullOrUndef(C[l.axis]));a-=Math.max(0,E)}a=_limitValue(a,0,r-1)}if(y){let E=Math.max(_lookupByKey(c,s.axis,_,!0).hi+1,t?0:_lookupByKey(e,d,s.getPixelForValue(_),!0).hi+1);if(f){const C=c.slice(E-1).findIndex(D=>!isNullOrUndef(D[l.axis]));E+=Math.max(0,C)}o=_limitValue(E,a,r)-a}else o=r-a}return{start:a,count:o}}function _scaleRangesChanged(n){const{xScale:e,yScale:t,_scaleRanges:r}=n,a={xmin:e.min,xmax:e.max,ymin:t.min,ymax:t.max};if(!r)return n._scaleRanges=a,!0;const o=r.xmin!==e.min||r.xmax!==e.max||r.ymin!==t.min||r.ymax!==t.max;return Object.assign(r,a),o}const atEdge=n=>n===0||n===1,elasticIn=(n,e,t)=>-(Math.pow(2,10*(n-=1))*Math.sin((n-e)*TAU/t)),elasticOut=(n,e,t)=>Math.pow(2,-10*n)*Math.sin((n-e)*TAU/t)+1,effects={linear:n=>n,easeInQuad:n=>n*n,easeOutQuad:n=>-n*(n-2),easeInOutQuad:n=>(n/=.5)<1?.5*n*n:-.5*(--n*(n-2)-1),easeInCubic:n=>n*n*n,easeOutCubic:n=>(n-=1)*n*n+1,easeInOutCubic:n=>(n/=.5)<1?.5*n*n*n:.5*((n-=2)*n*n+2),easeInQuart:n=>n*n*n*n,easeOutQuart:n=>-((n-=1)*n*n*n-1),easeInOutQuart:n=>(n/=.5)<1?.5*n*n*n*n:-.5*((n-=2)*n*n*n-2),easeInQuint:n=>n*n*n*n*n,easeOutQuint:n=>(n-=1)*n*n*n*n+1,easeInOutQuint:n=>(n/=.5)<1?.5*n*n*n*n*n:.5*((n-=2)*n*n*n*n+2),easeInSine:n=>-Math.cos(n*HALF_PI)+1,easeOutSine:n=>Math.sin(n*HALF_PI),easeInOutSine:n=>-.5*(Math.cos(PI*n)-1),easeInExpo:n=>n===0?0:Math.pow(2,10*(n-1)),easeOutExpo:n=>n===1?1:-Math.pow(2,-10*n)+1,easeInOutExpo:n=>atEdge(n)?n:n<.5?.5*Math.pow(2,10*(n*2-1)):.5*(-Math.pow(2,-10*(n*2-1))+2),easeInCirc:n=>n>=1?n:-(Math.sqrt(1-n*n)-1),easeOutCirc:n=>Math.sqrt(1-(n-=1)*n),easeInOutCirc:n=>(n/=.5)<1?-.5*(Math.sqrt(1-n*n)-1):.5*(Math.sqrt(1-(n-=2)*n)+1),easeInElastic:n=>atEdge(n)?n:elasticIn(n,.075,.3),easeOutElastic:n=>atEdge(n)?n:elasticOut(n,.075,.3),easeInOutElastic(n){return atEdge(n)?n:n<.5?.5*elasticIn(n*2,.1125,.45):.5+.5*elasticOut(n*2-1,.1125,.45)},easeInBack(n){return n*n*((1.70158+1)*n-1.70158)},easeOutBack(n){return(n-=1)*n*((1.70158+1)*n+1.70158)+1},easeInOutBack(n){let e=1.70158;return(n/=.5)<1?.5*(n*n*(((e*=1.525)+1)*n-e)):.5*((n-=2)*n*(((e*=1.525)+1)*n+e)+2)},easeInBounce:n=>1-effects.easeOutBounce(1-n),easeOutBounce(n){return n<1/2.75?7.5625*n*n:n<2/2.75?7.5625*(n-=1.5/2.75)*n+.75:n<2.5/2.75?7.5625*(n-=2.25/2.75)*n+.9375:7.5625*(n-=2.625/2.75)*n+.984375},easeInOutBounce:n=>n<.5?effects.easeInBounce(n*2)*.5:effects.easeOutBounce(n*2-1)*.5+.5};function isPatternOrGradient(n){if(n&&typeof n=="object"){const e=n.toString();return e==="[object CanvasPattern]"||e==="[object CanvasGradient]"}return!1}function color(n){return isPatternOrGradient(n)?n:new Color(n)}function getHoverColor(n){return isPatternOrGradient(n)?n:new Color(n).saturate(.5).darken(.1).hexString()}const numbers=["x","y","borderWidth","radius","tension"],colors=["color","borderColor","backgroundColor"];function applyAnimationsDefaults(n){n.set("animation",{delay:void 0,duration:1e3,easing:"easeOutQuart",fn:void 0,from:void 0,loop:void 0,to:void 0,type:void 0}),n.describe("animation",{_fallback:!1,_indexable:!1,_scriptable:e=>e!=="onProgress"&&e!=="onComplete"&&e!=="fn"}),n.set("animations",{colors:{type:"color",properties:colors},numbers:{type:"number",properties:numbers}}),n.describe("animations",{_fallback:"animation"}),n.set("transitions",{active:{animation:{duration:400}},resize:{animation:{duration:0}},show:{animations:{colors:{from:"transparent"},visible:{type:"boolean",duration:0}}},hide:{animations:{colors:{to:"transparent"},visible:{type:"boolean",easing:"linear",fn:e=>e|0}}}})}function applyLayoutsDefaults(n){n.set("layout",{autoPadding:!0,padding:{top:0,right:0,bottom:0,left:0}})}const intlCache=new Map;function getNumberFormat(n,e){e=e||{};const t=n+JSON.stringify(e);let r=intlCache.get(t);return r||(r=new Intl.NumberFormat(n,e),intlCache.set(t,r)),r}function formatNumber(n,e,t){return getNumberFormat(e,t).format(n)}const formatters={values(n){return isArray(n)?n:""+n},numeric(n,e,t){if(n===0)return"0";const r=this.chart.options.locale;let a,o=n;if(t.length>1){const f=Math.max(Math.abs(t[0].value),Math.abs(t[t.length-1].value));(f<1e-4||f>1e15)&&(a="scientific"),o=calculateDelta(n,t)}const s=log10(Math.abs(o)),l=isNaN(s)?1:Math.max(Math.min(-1*Math.floor(s),20),0),c={notation:a,minimumFractionDigits:l,maximumFractionDigits:l};return Object.assign(c,this.options.ticks.format),formatNumber(n,r,c)},logarithmic(n,e,t){if(n===0)return"0";const r=t[e].significand||n/Math.pow(10,Math.floor(log10(n)));return[1,2,3,5,10,15].includes(r)||e>.8*t.length?formatters.numeric.call(this,n,e,t):""}};function calculateDelta(n,e){let t=e.length>3?e[2].value-e[1].value:e[1].value-e[0].value;return Math.abs(t)>=1&&n!==Math.floor(n)&&(t=n-Math.floor(n)),t}var Ticks={formatters};function applyScaleDefaults(n){n.set("scale",{display:!0,offset:!1,reverse:!1,beginAtZero:!1,bounds:"ticks",clip:!0,grace:0,grid:{display:!0,lineWidth:1,drawOnChartArea:!0,drawTicks:!0,tickLength:8,tickWidth:(e,t)=>t.lineWidth,tickColor:(e,t)=>t.color,offset:!1},border:{display:!0,dash:[],dashOffset:0,width:1},title:{display:!1,text:"",padding:{top:4,bottom:4}},ticks:{minRotation:0,maxRotation:50,mirror:!1,textStrokeWidth:0,textStrokeColor:"",padding:3,display:!0,autoSkip:!0,autoSkipPadding:3,labelOffset:0,callback:Ticks.formatters.values,minor:{},major:{},align:"center",crossAlign:"near",showLabelBackdrop:!1,backdropColor:"rgba(255, 255, 255, 0.75)",backdropPadding:2}}),n.route("scale.ticks","color","","color"),n.route("scale.grid","color","","borderColor"),n.route("scale.border","color","","borderColor"),n.route("scale.title","color","","color"),n.describe("scale",{_fallback:!1,_scriptable:e=>!e.startsWith("before")&&!e.startsWith("after")&&e!=="callback"&&e!=="parser",_indexable:e=>e!=="borderDash"&&e!=="tickBorderDash"&&e!=="dash"}),n.describe("scales",{_fallback:"scale"}),n.describe("scale.ticks",{_scriptable:e=>e!=="backdropPadding"&&e!=="callback",_indexable:e=>e!=="backdropPadding"})}const overrides=Object.create(null),descriptors=Object.create(null);function getScope$1(n,e){if(!e)return n;const t=e.split(".");for(let r=0,a=t.length;r<a;++r){const o=t[r];n=n[o]||(n[o]=Object.create(null))}return n}function set(n,e,t){return typeof e=="string"?merge(getScope$1(n,e),t):merge(getScope$1(n,""),e)}class Defaults{constructor(e,t){this.animation=void 0,this.backgroundColor="rgba(0,0,0,0.1)",this.borderColor="rgba(0,0,0,0.1)",this.color="#666",this.datasets={},this.devicePixelRatio=r=>r.chart.platform.getDevicePixelRatio(),this.elements={},this.events=["mousemove","mouseout","click","touchstart","touchmove"],this.font={family:"'Helvetica Neue', 'Helvetica', 'Arial', sans-serif",size:12,style:"normal",lineHeight:1.2,weight:null},this.hover={},this.hoverBackgroundColor=(r,a)=>getHoverColor(a.backgroundColor),this.hoverBorderColor=(r,a)=>getHoverColor(a.borderColor),this.hoverColor=(r,a)=>getHoverColor(a.color),this.indexAxis="x",this.interaction={mode:"nearest",intersect:!0,includeInvisible:!1},this.maintainAspectRatio=!0,this.onHover=null,this.onClick=null,this.parsing=!0,this.plugins={},this.responsive=!0,this.scale=void 0,this.scales={},this.showLine=!0,this.drawActiveElementsOnTop=!0,this.describe(e),this.apply(t)}set(e,t){return set(this,e,t)}get(e){return getScope$1(this,e)}describe(e,t){return set(descriptors,e,t)}override(e,t){return set(overrides,e,t)}route(e,t,r,a){const o=getScope$1(this,e),s=getScope$1(this,r),l="_"+t;Object.defineProperties(o,{[l]:{value:o[t],writable:!0},[t]:{enumerable:!0,get(){const c=this[l],f=s[a];return isObject(c)?Object.assign({},f,c):valueOrDefault(c,f)},set(c){this[l]=c}}})}apply(e){e.forEach(t=>t(this))}}var defaults=new Defaults({_scriptable:n=>!n.startsWith("on"),_indexable:n=>n!=="events",hover:{_fallback:"interaction"},interaction:{_scriptable:!1,_indexable:!1}},[applyAnimationsDefaults,applyLayoutsDefaults,applyScaleDefaults]);function toFontString(n){return!n||isNullOrUndef(n.size)||isNullOrUndef(n.family)?null:(n.style?n.style+" ":"")+(n.weight?n.weight+" ":"")+n.size+"px "+n.family}function _measureText(n,e,t,r,a){let o=e[a];return o||(o=e[a]=n.measureText(a).width,t.push(a)),o>r&&(r=o),r}function _longestText(n,e,t,r){r=r||{};let a=r.data=r.data||{},o=r.garbageCollect=r.garbageCollect||[];r.font!==e&&(a=r.data={},o=r.garbageCollect=[],r.font=e),n.save(),n.font=e;let s=0;const l=t.length;let c,f,d,p,_;for(c=0;c<l;c++)if(p=t[c],p!=null&&!isArray(p))s=_measureText(n,a,o,s,p);else if(isArray(p))for(f=0,d=p.length;f<d;f++)_=p[f],_!=null&&!isArray(_)&&(s=_measureText(n,a,o,s,_));n.restore();const b=o.length/2;if(b>t.length){for(c=0;c<b;c++)delete a[o[c]];o.splice(0,b)}return s}function _alignPixel(n,e,t){const r=n.currentDevicePixelRatio,a=t!==0?Math.max(t/2,.5):0;return Math.round((e-a)*r)/r+a}function clearCanvas(n,e){!e&&!n||(e=e||n.getContext("2d"),e.save(),e.resetTransform(),e.clearRect(0,0,n.width,n.height),e.restore())}function drawPoint(n,e,t,r){drawPointLegend(n,e,t,r,null)}function drawPointLegend(n,e,t,r,a){let o,s,l,c,f,d,p,_;const b=e.pointStyle,y=e.rotation,E=e.radius;let C=(y||0)*RAD_PER_DEG;if(b&&typeof b=="object"&&(o=b.toString(),o==="[object HTMLImageElement]"||o==="[object HTMLCanvasElement]")){n.save(),n.translate(t,r),n.rotate(C),n.drawImage(b,-b.width/2,-b.height/2,b.width,b.height),n.restore();return}if(!(isNaN(E)||E<=0)){switch(n.beginPath(),b){default:a?n.ellipse(t,r,a/2,E,0,0,TAU):n.arc(t,r,E,0,TAU),n.closePath();break;case"triangle":d=a?a/2:E,n.moveTo(t+Math.sin(C)*d,r-Math.cos(C)*E),C+=TWO_THIRDS_PI,n.lineTo(t+Math.sin(C)*d,r-Math.cos(C)*E),C+=TWO_THIRDS_PI,n.lineTo(t+Math.sin(C)*d,r-Math.cos(C)*E),n.closePath();break;case"rectRounded":f=E*.516,c=E-f,s=Math.cos(C+QUARTER_PI)*c,p=Math.cos(C+QUARTER_PI)*(a?a/2-f:c),l=Math.sin(C+QUARTER_PI)*c,_=Math.sin(C+QUARTER_PI)*(a?a/2-f:c),n.arc(t-p,r-l,f,C-PI,C-HALF_PI),n.arc(t+_,r-s,f,C-HALF_PI,C),n.arc(t+p,r+l,f,C,C+HALF_PI),n.arc(t-_,r+s,f,C+HALF_PI,C+PI),n.closePath();break;case"rect":if(!y){c=Math.SQRT1_2*E,d=a?a/2:c,n.rect(t-d,r-c,2*d,2*c);break}C+=QUARTER_PI;case"rectRot":p=Math.cos(C)*(a?a/2:E),s=Math.cos(C)*E,l=Math.sin(C)*E,_=Math.sin(C)*(a?a/2:E),n.moveTo(t-p,r-l),n.lineTo(t+_,r-s),n.lineTo(t+p,r+l),n.lineTo(t-_,r+s),n.closePath();break;case"crossRot":C+=QUARTER_PI;case"cross":p=Math.cos(C)*(a?a/2:E),s=Math.cos(C)*E,l=Math.sin(C)*E,_=Math.sin(C)*(a?a/2:E),n.moveTo(t-p,r-l),n.lineTo(t+p,r+l),n.moveTo(t+_,r-s),n.lineTo(t-_,r+s);break;case"star":p=Math.cos(C)*(a?a/2:E),s=Math.cos(C)*E,l=Math.sin(C)*E,_=Math.sin(C)*(a?a/2:E),n.moveTo(t-p,r-l),n.lineTo(t+p,r+l),n.moveTo(t+_,r-s),n.lineTo(t-_,r+s),C+=QUARTER_PI,p=Math.cos(C)*(a?a/2:E),s=Math.cos(C)*E,l=Math.sin(C)*E,_=Math.sin(C)*(a?a/2:E),n.moveTo(t-p,r-l),n.lineTo(t+p,r+l),n.moveTo(t+_,r-s),n.lineTo(t-_,r+s);break;case"line":s=a?a/2:Math.cos(C)*E,l=Math.sin(C)*E,n.moveTo(t-s,r-l),n.lineTo(t+s,r+l);break;case"dash":n.moveTo(t,r),n.lineTo(t+Math.cos(C)*(a?a/2:E),r+Math.sin(C)*E);break;case!1:n.closePath();break}n.fill(),e.borderWidth>0&&n.stroke()}}function _isPointInArea(n,e,t){return t=t||.5,!e||n&&n.x>e.left-t&&n.x<e.right+t&&n.y>e.top-t&&n.y<e.bottom+t}function clipArea(n,e){n.save(),n.beginPath(),n.rect(e.left,e.top,e.right-e.left,e.bottom-e.top),n.clip()}function unclipArea(n){n.restore()}function _steppedLineTo(n,e,t,r,a){if(!e)return n.lineTo(t.x,t.y);if(a==="middle"){const o=(e.x+t.x)/2;n.lineTo(o,e.y),n.lineTo(o,t.y)}else a==="after"!=!!r?n.lineTo(e.x,t.y):n.lineTo(t.x,e.y);n.lineTo(t.x,t.y)}function _bezierCurveTo(n,e,t,r){if(!e)return n.lineTo(t.x,t.y);n.bezierCurveTo(r?e.cp1x:e.cp2x,r?e.cp1y:e.cp2y,r?t.cp2x:t.cp1x,r?t.cp2y:t.cp1y,t.x,t.y)}function setRenderOpts(n,e){e.translation&&n.translate(e.translation[0],e.translation[1]),isNullOrUndef(e.rotation)||n.rotate(e.rotation),e.color&&(n.fillStyle=e.color),e.textAlign&&(n.textAlign=e.textAlign),e.textBaseline&&(n.textBaseline=e.textBaseline)}function decorateText(n,e,t,r,a){if(a.strikethrough||a.underline){const o=n.measureText(r),s=e-o.actualBoundingBoxLeft,l=e+o.actualBoundingBoxRight,c=t-o.actualBoundingBoxAscent,f=t+o.actualBoundingBoxDescent,d=a.strikethrough?(c+f)/2:f;n.strokeStyle=n.fillStyle,n.beginPath(),n.lineWidth=a.decorationWidth||2,n.moveTo(s,d),n.lineTo(l,d),n.stroke()}}function drawBackdrop(n,e){const t=n.fillStyle;n.fillStyle=e.color,n.fillRect(e.left,e.top,e.width,e.height),n.fillStyle=t}function renderText(n,e,t,r,a,o={}){const s=isArray(e)?e:[e],l=o.strokeWidth>0&&o.strokeColor!=="";let c,f;for(n.save(),n.font=a.string,setRenderOpts(n,o),c=0;c<s.length;++c)f=s[c],o.backdrop&&drawBackdrop(n,o.backdrop),l&&(o.strokeColor&&(n.strokeStyle=o.strokeColor),isNullOrUndef(o.strokeWidth)||(n.lineWidth=o.strokeWidth),n.strokeText(f,t,r,o.maxWidth)),n.fillText(f,t,r,o.maxWidth),decorateText(n,t,r,f,o),r+=Number(a.lineHeight);n.restore()}function addRoundedRectPath(n,e){const{x:t,y:r,w:a,h:o,radius:s}=e;n.arc(t+s.topLeft,r+s.topLeft,s.topLeft,1.5*PI,PI,!0),n.lineTo(t,r+o-s.bottomLeft),n.arc(t+s.bottomLeft,r+o-s.bottomLeft,s.bottomLeft,PI,HALF_PI,!0),n.lineTo(t+a-s.bottomRight,r+o),n.arc(t+a-s.bottomRight,r+o-s.bottomRight,s.bottomRight,HALF_PI,0,!0),n.lineTo(t+a,r+s.topRight),n.arc(t+a-s.topRight,r+s.topRight,s.topRight,0,-HALF_PI,!0),n.lineTo(t+s.topLeft,r)}const LINE_HEIGHT=/^(normal|(\d+(?:\.\d+)?)(px|em|%)?)$/,FONT_STYLE=/^(normal|italic|initial|inherit|unset|(oblique( -?[0-9]?[0-9]deg)?))$/;function toLineHeight(n,e){const t=(""+n).match(LINE_HEIGHT);if(!t||t[1]==="normal")return e*1.2;switch(n=+t[2],t[3]){case"px":return n;case"%":n/=100;break}return e*n}const numberOrZero=n=>+n||0;function _readValueToProps(n,e){const t={},r=isObject(e),a=r?Object.keys(e):e,o=isObject(n)?r?s=>valueOrDefault(n[s],n[e[s]]):s=>n[s]:()=>n;for(const s of a)t[s]=numberOrZero(o(s));return t}function toTRBL(n){return _readValueToProps(n,{top:"y",right:"x",bottom:"y",left:"x"})}function toTRBLCorners(n){return _readValueToProps(n,["topLeft","topRight","bottomLeft","bottomRight"])}function toPadding(n){const e=toTRBL(n);return e.width=e.left+e.right,e.height=e.top+e.bottom,e}function toFont(n,e){n=n||{},e=e||defaults.font;let t=valueOrDefault(n.size,e.size);typeof t=="string"&&(t=parseInt(t,10));let r=valueOrDefault(n.style,e.style);r&&!(""+r).match(FONT_STYLE)&&(console.warn('Invalid font style specified: "'+r+'"'),r=void 0);const a={family:valueOrDefault(n.family,e.family),lineHeight:toLineHeight(valueOrDefault(n.lineHeight,e.lineHeight),t),size:t,style:r,weight:valueOrDefault(n.weight,e.weight),string:""};return a.string=toFontString(a),a}function resolve(n,e,t,r){let a,o,s;for(a=0,o=n.length;a<o;++a)if(s=n[a],s!==void 0&&s!==void 0)return s}function _addGrace(n,e,t){const{min:r,max:a}=n,o=toDimension(e,(a-r)/2),s=(l,c)=>t&&l===0?0:l+c;return{min:s(r,-Math.abs(o)),max:s(a,o)}}function createContext(n,e){return Object.assign(Object.create(n),e)}function _createResolver(n,e=[""],t,r,a=()=>n[0]){const o=t||n;typeof r>"u"&&(r=_resolve("_fallback",n));const s={[Symbol.toStringTag]:"Object",_cacheable:!0,_scopes:n,_rootScopes:o,_fallback:r,_getTarget:a,override:l=>_createResolver([l,...n],e,o,r)};return new Proxy(s,{deleteProperty(l,c){return delete l[c],delete l._keys,delete n[0][c],!0},get(l,c){return _cached(l,c,()=>_resolveWithPrefixes(c,e,n,l))},getOwnPropertyDescriptor(l,c){return Reflect.getOwnPropertyDescriptor(l._scopes[0],c)},getPrototypeOf(){return Reflect.getPrototypeOf(n[0])},has(l,c){return getKeysFromAllScopes(l).includes(c)},ownKeys(l){return getKeysFromAllScopes(l)},set(l,c,f){const d=l._storage||(l._storage=a());return l[c]=d[c]=f,delete l._keys,!0}})}function _attachContext(n,e,t,r){const a={_cacheable:!1,_proxy:n,_context:e,_subProxy:t,_stack:new Set,_descriptors:_descriptors(n,r),setContext:o=>_attachContext(n,o,t,r),override:o=>_attachContext(n.override(o),e,t,r)};return new Proxy(a,{deleteProperty(o,s){return delete o[s],delete n[s],!0},get(o,s,l){return _cached(o,s,()=>_resolveWithContext(o,s,l))},getOwnPropertyDescriptor(o,s){return o._descriptors.allKeys?Reflect.has(n,s)?{enumerable:!0,configurable:!0}:void 0:Reflect.getOwnPropertyDescriptor(n,s)},getPrototypeOf(){return Reflect.getPrototypeOf(n)},has(o,s){return Reflect.has(n,s)},ownKeys(){return Reflect.ownKeys(n)},set(o,s,l){return n[s]=l,delete o[s],!0}})}function _descriptors(n,e={scriptable:!0,indexable:!0}){const{_scriptable:t=e.scriptable,_indexable:r=e.indexable,_allKeys:a=e.allKeys}=n;return{allKeys:a,scriptable:t,indexable:r,isScriptable:isFunction(t)?t:()=>t,isIndexable:isFunction(r)?r:()=>r}}const readKey=(n,e)=>n?n+_capitalize(e):e,needsSubResolver=(n,e)=>isObject(e)&&n!=="adapters"&&(Object.getPrototypeOf(e)===null||e.constructor===Object);function _cached(n,e,t){if(Object.prototype.hasOwnProperty.call(n,e)||e==="constructor")return n[e];const r=t();return n[e]=r,r}function _resolveWithContext(n,e,t){const{_proxy:r,_context:a,_subProxy:o,_descriptors:s}=n;let l=r[e];return isFunction(l)&&s.isScriptable(e)&&(l=_resolveScriptable(e,l,n,t)),isArray(l)&&l.length&&(l=_resolveArray(e,l,n,s.isIndexable)),needsSubResolver(e,l)&&(l=_attachContext(l,a,o&&o[e],s)),l}function _resolveScriptable(n,e,t,r){const{_proxy:a,_context:o,_subProxy:s,_stack:l}=t;if(l.has(n))throw new Error("Recursion detected: "+Array.from(l).join("->")+"->"+n);l.add(n);let c=e(o,s||r);return l.delete(n),needsSubResolver(n,c)&&(c=createSubResolver(a._scopes,a,n,c)),c}function _resolveArray(n,e,t,r){const{_proxy:a,_context:o,_subProxy:s,_descriptors:l}=t;if(typeof o.index<"u"&&r(n))return e[o.index%e.length];if(isObject(e[0])){const c=e,f=a._scopes.filter(d=>d!==c);e=[];for(const d of c){const p=createSubResolver(f,a,n,d);e.push(_attachContext(p,o,s&&s[n],l))}}return e}function resolveFallback(n,e,t){return isFunction(n)?n(e,t):n}const getScope=(n,e)=>n===!0?e:typeof n=="string"?resolveObjectKey(e,n):void 0;function addScopes(n,e,t,r,a){for(const o of e){const s=getScope(t,o);if(s){n.add(s);const l=resolveFallback(s._fallback,t,a);if(typeof l<"u"&&l!==t&&l!==r)return l}else if(s===!1&&typeof r<"u"&&t!==r)return null}return!1}function createSubResolver(n,e,t,r){const a=e._rootScopes,o=resolveFallback(e._fallback,t,r),s=[...n,...a],l=new Set;l.add(r);let c=addScopesFromKey(l,s,t,o||t,r);return c===null||typeof o<"u"&&o!==t&&(c=addScopesFromKey(l,s,o,c,r),c===null)?!1:_createResolver(Array.from(l),[""],a,o,()=>subGetTarget(e,t,r))}function addScopesFromKey(n,e,t,r,a){for(;t;)t=addScopes(n,e,t,r,a);return t}function subGetTarget(n,e,t){const r=n._getTarget();e in r||(r[e]={});const a=r[e];return isArray(a)&&isObject(t)?t:a||{}}function _resolveWithPrefixes(n,e,t,r){let a;for(const o of e)if(a=_resolve(readKey(o,n),t),typeof a<"u")return needsSubResolver(n,a)?createSubResolver(t,r,n,a):a}function _resolve(n,e){for(const t of e){if(!t)continue;const r=t[n];if(typeof r<"u")return r}}function getKeysFromAllScopes(n){let e=n._keys;return e||(e=n._keys=resolveKeysFromAllScopes(n._scopes)),e}function resolveKeysFromAllScopes(n){const e=new Set;for(const t of n)for(const r of Object.keys(t).filter(a=>!a.startsWith("_")))e.add(r);return Array.from(e)}function _parseObjectDataRadialScale(n,e,t,r){const{iScale:a}=n,{key:o="r"}=this._parsing,s=new Array(r);let l,c,f,d;for(l=0,c=r;l<c;++l)f=l+t,d=e[f],s[l]={r:a.parse(resolveObjectKey(d,o),f)};return s}const EPSILON=Number.EPSILON||1e-14,getPoint=(n,e)=>e<n.length&&!n[e].skip&&n[e],getValueAxis=n=>n==="x"?"y":"x";function splineCurve(n,e,t,r){const a=n.skip?e:n,o=e,s=t.skip?e:t,l=distanceBetweenPoints(o,a),c=distanceBetweenPoints(s,o);let f=l/(l+c),d=c/(l+c);f=isNaN(f)?0:f,d=isNaN(d)?0:d;const p=r*f,_=r*d;return{previous:{x:o.x-p*(s.x-a.x),y:o.y-p*(s.y-a.y)},next:{x:o.x+_*(s.x-a.x),y:o.y+_*(s.y-a.y)}}}function monotoneAdjust(n,e,t){const r=n.length;let a,o,s,l,c,f=getPoint(n,0);for(let d=0;d<r-1;++d)if(c=f,f=getPoint(n,d+1),!(!c||!f)){if(almostEquals(e[d],0,EPSILON)){t[d]=t[d+1]=0;continue}a=t[d]/e[d],o=t[d+1]/e[d],l=Math.pow(a,2)+Math.pow(o,2),!(l<=9)&&(s=3/Math.sqrt(l),t[d]=a*s*e[d],t[d+1]=o*s*e[d])}}function monotoneCompute(n,e,t="x"){const r=getValueAxis(t),a=n.length;let o,s,l,c=getPoint(n,0);for(let f=0;f<a;++f){if(s=l,l=c,c=getPoint(n,f+1),!l)continue;const d=l[t],p=l[r];s&&(o=(d-s[t])/3,l[`cp1${t}`]=d-o,l[`cp1${r}`]=p-o*e[f]),c&&(o=(c[t]-d)/3,l[`cp2${t}`]=d+o,l[`cp2${r}`]=p+o*e[f])}}function splineCurveMonotone(n,e="x"){const t=getValueAxis(e),r=n.length,a=Array(r).fill(0),o=Array(r);let s,l,c,f=getPoint(n,0);for(s=0;s<r;++s)if(l=c,c=f,f=getPoint(n,s+1),!!c){if(f){const d=f[e]-c[e];a[s]=d!==0?(f[t]-c[t])/d:0}o[s]=l?f?sign(a[s-1])!==sign(a[s])?0:(a[s-1]+a[s])/2:a[s-1]:a[s]}monotoneAdjust(n,a,o),monotoneCompute(n,o,e)}function capControlPoint(n,e,t){return Math.max(Math.min(n,t),e)}function capBezierPoints(n,e){let t,r,a,o,s,l=_isPointInArea(n[0],e);for(t=0,r=n.length;t<r;++t)s=o,o=l,l=t<r-1&&_isPointInArea(n[t+1],e),o&&(a=n[t],s&&(a.cp1x=capControlPoint(a.cp1x,e.left,e.right),a.cp1y=capControlPoint(a.cp1y,e.top,e.bottom)),l&&(a.cp2x=capControlPoint(a.cp2x,e.left,e.right),a.cp2y=capControlPoint(a.cp2y,e.top,e.bottom)))}function _updateBezierControlPoints(n,e,t,r,a){let o,s,l,c;if(e.spanGaps&&(n=n.filter(f=>!f.skip)),e.cubicInterpolationMode==="monotone")splineCurveMonotone(n,a);else{let f=r?n[n.length-1]:n[0];for(o=0,s=n.length;o<s;++o)l=n[o],c=splineCurve(f,l,n[Math.min(o+1,s-(r?0:1))%s],e.tension),l.cp1x=c.previous.x,l.cp1y=c.previous.y,l.cp2x=c.next.x,l.cp2y=c.next.y,f=l}e.capBezierPoints&&capBezierPoints(n,t)}function _isDomSupported(){return typeof window<"u"&&typeof document<"u"}function _getParentNode(n){let e=n.parentNode;return e&&e.toString()==="[object ShadowRoot]"&&(e=e.host),e}function parseMaxStyle(n,e,t){let r;return typeof n=="string"?(r=parseInt(n,10),n.indexOf("%")!==-1&&(r=r/100*e.parentNode[t])):r=n,r}const getComputedStyle$1=n=>n.ownerDocument.defaultView.getComputedStyle(n,null);function getStyle(n,e){return getComputedStyle$1(n).getPropertyValue(e)}const positions=["top","right","bottom","left"];function getPositionedStyle(n,e,t){const r={};t=t?"-"+t:"";for(let a=0;a<4;a++){const o=positions[a];r[o]=parseFloat(n[e+"-"+o+t])||0}return r.width=r.left+r.right,r.height=r.top+r.bottom,r}const useOffsetPos=(n,e,t)=>(n>0||e>0)&&(!t||!t.shadowRoot);function getCanvasPosition(n,e){const t=n.touches,r=t&&t.length?t[0]:n,{offsetX:a,offsetY:o}=r;let s=!1,l,c;if(useOffsetPos(a,o,n.target))l=a,c=o;else{const f=e.getBoundingClientRect();l=r.clientX-f.left,c=r.clientY-f.top,s=!0}return{x:l,y:c,box:s}}function getRelativePosition(n,e){if("native"in n)return n;const{canvas:t,currentDevicePixelRatio:r}=e,a=getComputedStyle$1(t),o=a.boxSizing==="border-box",s=getPositionedStyle(a,"padding"),l=getPositionedStyle(a,"border","width"),{x:c,y:f,box:d}=getCanvasPosition(n,t),p=s.left+(d&&l.left),_=s.top+(d&&l.top);let{width:b,height:y}=e;return o&&(b-=s.width+l.width,y-=s.height+l.height),{x:Math.round((c-p)/b*t.width/r),y:Math.round((f-_)/y*t.height/r)}}function getContainerSize(n,e,t){let r,a;if(e===void 0||t===void 0){const o=n&&_getParentNode(n);if(!o)e=n.clientWidth,t=n.clientHeight;else{const s=o.getBoundingClientRect(),l=getComputedStyle$1(o),c=getPositionedStyle(l,"border","width"),f=getPositionedStyle(l,"padding");e=s.width-f.width-c.width,t=s.height-f.height-c.height,r=parseMaxStyle(l.maxWidth,o,"clientWidth"),a=parseMaxStyle(l.maxHeight,o,"clientHeight")}}return{width:e,height:t,maxWidth:r||INFINITY,maxHeight:a||INFINITY}}const round1=n=>Math.round(n*10)/10;function getMaximumSize(n,e,t,r){const a=getComputedStyle$1(n),o=getPositionedStyle(a,"margin"),s=parseMaxStyle(a.maxWidth,n,"clientWidth")||INFINITY,l=parseMaxStyle(a.maxHeight,n,"clientHeight")||INFINITY,c=getContainerSize(n,e,t);let{width:f,height:d}=c;if(a.boxSizing==="content-box"){const _=getPositionedStyle(a,"border","width"),b=getPositionedStyle(a,"padding");f-=b.width+_.width,d-=b.height+_.height}return f=Math.max(0,f-o.width),d=Math.max(0,r?f/r:d-o.height),f=round1(Math.min(f,s,c.maxWidth)),d=round1(Math.min(d,l,c.maxHeight)),f&&!d&&(d=round1(f/2)),(e!==void 0||t!==void 0)&&r&&c.height&&d>c.height&&(d=c.height,f=round1(Math.floor(d*r))),{width:f,height:d}}function retinaScale(n,e,t){const r=e||1,a=round1(n.height*r),o=round1(n.width*r);n.height=round1(n.height),n.width=round1(n.width);const s=n.canvas;return s.style&&(t||!s.style.height&&!s.style.width)&&(s.style.height=`${n.height}px`,s.style.width=`${n.width}px`),n.currentDevicePixelRatio!==r||s.height!==a||s.width!==o?(n.currentDevicePixelRatio=r,s.height=a,s.width=o,n.ctx.setTransform(r,0,0,r,0,0),!0):!1}const supportsEventListenerOptions=(function(){let n=!1;try{const e={get passive(){return n=!0,!1}};_isDomSupported()&&(window.addEventListener("test",null,e),window.removeEventListener("test",null,e))}catch{}return n})();function readUsedSize(n,e){const t=getStyle(n,e),r=t&&t.match(/^(\d+)(\.\d+)?px$/);return r?+r[1]:void 0}function _pointInLine(n,e,t,r){return{x:n.x+t*(e.x-n.x),y:n.y+t*(e.y-n.y)}}function _steppedInterpolation(n,e,t,r){return{x:n.x+t*(e.x-n.x),y:r==="middle"?t<.5?n.y:e.y:r==="after"?t<1?n.y:e.y:t>0?e.y:n.y}}function _bezierInterpolation(n,e,t,r){const a={x:n.cp2x,y:n.cp2y},o={x:e.cp1x,y:e.cp1y},s=_pointInLine(n,a,t),l=_pointInLine(a,o,t),c=_pointInLine(o,e,t),f=_pointInLine(s,l,t),d=_pointInLine(l,c,t);return _pointInLine(f,d,t)}const getRightToLeftAdapter=function(n,e){return{x(t){return n+n+e-t},setWidth(t){e=t},textAlign(t){return t==="center"?t:t==="right"?"left":"right"},xPlus(t,r){return t-r},leftForLtr(t,r){return t-r}}},getLeftToRightAdapter=function(){return{x(n){return n},setWidth(n){},textAlign(n){return n},xPlus(n,e){return n+e},leftForLtr(n,e){return n}}};function getRtlAdapter(n,e,t){return n?getRightToLeftAdapter(e,t):getLeftToRightAdapter()}function overrideTextDirection(n,e){let t,r;(e==="ltr"||e==="rtl")&&(t=n.canvas.style,r=[t.getPropertyValue("direction"),t.getPropertyPriority("direction")],t.setProperty("direction",e,"important"),n.prevTextDirection=r)}function restoreTextDirection(n,e){e!==void 0&&(delete n.prevTextDirection,n.canvas.style.setProperty("direction",e[0],e[1]))}function propertyFn(n){return n==="angle"?{between:_angleBetween,compare:_angleDiff,normalize:_normalizeAngle}:{between:_isBetween,compare:(e,t)=>e-t,normalize:e=>e}}function normalizeSegment({start:n,end:e,count:t,loop:r,style:a}){return{start:n%t,end:e%t,loop:r&&(e-n+1)%t===0,style:a}}function getSegment(n,e,t){const{property:r,start:a,end:o}=t,{between:s,normalize:l}=propertyFn(r),c=e.length;let{start:f,end:d,loop:p}=n,_,b;if(p){for(f+=c,d+=c,_=0,b=c;_<b&&s(l(e[f%c][r]),a,o);++_)f--,d--;f%=c,d%=c}return d<f&&(d+=c),{start:f,end:d,loop:p,style:n.style}}function _boundSegment(n,e,t){if(!t)return[n];const{property:r,start:a,end:o}=t,s=e.length,{compare:l,between:c,normalize:f}=propertyFn(r),{start:d,end:p,loop:_,style:b}=getSegment(n,e,t),y=[];let E=!1,C=null,D,M,F;const P=()=>c(a,F,D)&&l(a,F)!==0,H=()=>l(o,D)===0||c(o,F,D),B=()=>E||P(),g=()=>!E||H();for(let q=d,G=d;q<=p;++q)M=e[q%s],!M.skip&&(D=f(M[r]),D!==F&&(E=c(D,a,o),C===null&&B()&&(C=l(D,a)===0?q:G),C!==null&&g()&&(y.push(normalizeSegment({start:C,end:q,loop:_,count:s,style:b})),C=null),G=q,F=D));return C!==null&&y.push(normalizeSegment({start:C,end:p,loop:_,count:s,style:b})),y}function _boundSegments(n,e){const t=[],r=n.segments;for(let a=0;a<r.length;a++){const o=_boundSegment(r[a],n.points,e);o.length&&t.push(...o)}return t}function findStartAndEnd(n,e,t,r){let a=0,o=e-1;if(t&&!r)for(;a<e&&!n[a].skip;)a++;for(;a<e&&n[a].skip;)a++;for(a%=e,t&&(o+=a);o>a&&n[o%e].skip;)o--;return o%=e,{start:a,end:o}}function solidSegments(n,e,t,r){const a=n.length,o=[];let s=e,l=n[e],c;for(c=e+1;c<=t;++c){const f=n[c%a];f.skip||f.stop?l.skip||(r=!1,o.push({start:e%a,end:(c-1)%a,loop:r}),e=s=f.stop?c:null):(s=c,l.skip&&(e=c)),l=f}return s!==null&&o.push({start:e%a,end:s%a,loop:r}),o}function _computeSegments(n,e){const t=n.points,r=n.options.spanGaps,a=t.length;if(!a)return[];const o=!!n._loop,{start:s,end:l}=findStartAndEnd(t,a,o,r);if(r===!0)return splitByStyles(n,[{start:s,end:l,loop:o}],t,e);const c=l<s?l+a:l,f=!!n._fullLoop&&s===0&&l===a-1;return splitByStyles(n,solidSegments(t,s,c,f),t,e)}function splitByStyles(n,e,t,r){return!r||!r.setContext||!t?e:doSplitByStyles(n,e,t,r)}function doSplitByStyles(n,e,t,r){const a=n._chart.getContext(),o=readStyle(n.options),{_datasetIndex:s,options:{spanGaps:l}}=n,c=t.length,f=[];let d=o,p=e[0].start,_=p;function b(y,E,C,D){const M=l?-1:1;if(y!==E){for(y+=c;t[y%c].skip;)y-=M;for(;t[E%c].skip;)E+=M;y%c!==E%c&&(f.push({start:y%c,end:E%c,loop:C,style:D}),d=D,p=E%c)}}for(const y of e){p=l?p:y.start;let E=t[p%c],C;for(_=p+1;_<=y.end;_++){const D=t[_%c];C=readStyle(r.setContext(createContext(a,{type:"segment",p0:E,p1:D,p0DataIndex:(_-1)%c,p1DataIndex:_%c,datasetIndex:s}))),styleChanged(C,d)&&b(p,_-1,y.loop,d),E=D,d=C}p<_-1&&b(p,_-1,y.loop,d)}return f}function readStyle(n){return{backgroundColor:n.backgroundColor,borderCapStyle:n.borderCapStyle,borderDash:n.borderDash,borderDashOffset:n.borderDashOffset,borderJoinStyle:n.borderJoinStyle,borderWidth:n.borderWidth,borderColor:n.borderColor}}function styleChanged(n,e){if(!e)return!1;const t=[],r=function(a,o){return isPatternOrGradient(o)?(t.includes(o)||t.push(o),t.indexOf(o)):o};return JSON.stringify(n,r)!==JSON.stringify(e,r)}function getSizeForArea(n,e,t){return n.options.clip?n[t]:e[t]}function getDatasetArea(n,e){const{xScale:t,yScale:r}=n;return t&&r?{left:getSizeForArea(t,e,"left"),right:getSizeForArea(t,e,"right"),top:getSizeForArea(r,e,"top"),bottom:getSizeForArea(r,e,"bottom")}:e}function getDatasetClipArea(n,e){const t=e._clip;if(t.disabled)return!1;const r=getDatasetArea(e,n.chartArea);return{left:t.left===!1?0:r.left-(t.left===!0?0:t.left),right:t.right===!1?n.width:r.right+(t.right===!0?0:t.right),top:t.top===!1?0:r.top-(t.top===!0?0:t.top),bottom:t.bottom===!1?n.height:r.bottom+(t.bottom===!0?0:t.bottom)}}class Animator{constructor(){this._request=null,this._charts=new Map,this._running=!1,this._lastDate=void 0}_notify(e,t,r,a){const o=t.listeners[a],s=t.duration;o.forEach(l=>l({chart:e,initial:t.initial,numSteps:s,currentStep:Math.min(r-t.start,s)}))}_refresh(){this._request||(this._running=!0,this._request=requestAnimFrame.call(window,()=>{this._update(),this._request=null,this._running&&this._refresh()}))}_update(e=Date.now()){let t=0;this._charts.forEach((r,a)=>{if(!r.running||!r.items.length)return;const o=r.items;let s=o.length-1,l=!1,c;for(;s>=0;--s)c=o[s],c._active?(c._total>r.duration&&(r.duration=c._total),c.tick(e),l=!0):(o[s]=o[o.length-1],o.pop());l&&(a.draw(),this._notify(a,r,e,"progress")),o.length||(r.running=!1,this._notify(a,r,e,"complete"),r.initial=!1),t+=o.length}),this._lastDate=e,t===0&&(this._running=!1)}_getAnims(e){const t=this._charts;let r=t.get(e);return r||(r={running:!1,initial:!0,items:[],listeners:{complete:[],progress:[]}},t.set(e,r)),r}listen(e,t,r){this._getAnims(e).listeners[t].push(r)}add(e,t){!t||!t.length||this._getAnims(e).items.push(...t)}has(e){return this._getAnims(e).items.length>0}start(e){const t=this._charts.get(e);t&&(t.running=!0,t.start=Date.now(),t.duration=t.items.reduce((r,a)=>Math.max(r,a._duration),0),this._refresh())}running(e){if(!this._running)return!1;const t=this._charts.get(e);return!(!t||!t.running||!t.items.length)}stop(e){const t=this._charts.get(e);if(!t||!t.items.length)return;const r=t.items;let a=r.length-1;for(;a>=0;--a)r[a].cancel();t.items=[],this._notify(e,t,Date.now(),"complete")}remove(e){return this._charts.delete(e)}}var animator=new Animator;const transparent="transparent",interpolators={boolean(n,e,t){return t>.5?e:n},color(n,e,t){const r=color(n||transparent),a=r.valid&&color(e||transparent);return a&&a.valid?a.mix(r,t).hexString():e},number(n,e,t){return n+(e-n)*t}};class Animation{constructor(e,t,r,a){const o=t[r];a=resolve([e.to,a,o,e.from]);const s=resolve([e.from,o,a]);this._active=!0,this._fn=e.fn||interpolators[e.type||typeof s],this._easing=effects[e.easing]||effects.linear,this._start=Math.floor(Date.now()+(e.delay||0)),this._duration=this._total=Math.floor(e.duration),this._loop=!!e.loop,this._target=t,this._prop=r,this._from=s,this._to=a,this._promises=void 0}active(){return this._active}update(e,t,r){if(this._active){this._notify(!1);const a=this._target[this._prop],o=r-this._start,s=this._duration-o;this._start=r,this._duration=Math.floor(Math.max(s,e.duration)),this._total+=o,this._loop=!!e.loop,this._to=resolve([e.to,t,a,e.from]),this._from=resolve([e.from,a,t])}}cancel(){this._active&&(this.tick(Date.now()),this._active=!1,this._notify(!1))}tick(e){const t=e-this._start,r=this._duration,a=this._prop,o=this._from,s=this._loop,l=this._to;let c;if(this._active=o!==l&&(s||t<r),!this._active){this._target[a]=l,this._notify(!0);return}if(t<0){this._target[a]=o;return}c=t/r%2,c=s&&c>1?2-c:c,c=this._easing(Math.min(1,Math.max(0,c))),this._target[a]=this._fn(o,l,c)}wait(){const e=this._promises||(this._promises=[]);return new Promise((t,r)=>{e.push({res:t,rej:r})})}_notify(e){const t=e?"res":"rej",r=this._promises||[];for(let a=0;a<r.length;a++)r[a][t]()}}class Animations{constructor(e,t){this._chart=e,this._properties=new Map,this.configure(t)}configure(e){if(!isObject(e))return;const t=Object.keys(defaults.animation),r=this._properties;Object.getOwnPropertyNames(e).forEach(a=>{const o=e[a];if(!isObject(o))return;const s={};for(const l of t)s[l]=o[l];(isArray(o.properties)&&o.properties||[a]).forEach(l=>{(l===a||!r.has(l))&&r.set(l,s)})})}_animateOptions(e,t){const r=t.options,a=resolveTargetOptions(e,r);if(!a)return[];const o=this._createAnimations(a,r);return r.$shared&&awaitAll(e.options.$animations,r).then(()=>{e.options=r},()=>{}),o}_createAnimations(e,t){const r=this._properties,a=[],o=e.$animations||(e.$animations={}),s=Object.keys(t),l=Date.now();let c;for(c=s.length-1;c>=0;--c){const f=s[c];if(f.charAt(0)==="$")continue;if(f==="options"){a.push(...this._animateOptions(e,t));continue}const d=t[f];let p=o[f];const _=r.get(f);if(p)if(_&&p.active()){p.update(_,d,l);continue}else p.cancel();if(!_||!_.duration){e[f]=d;continue}o[f]=p=new Animation(_,e,f,d),a.push(p)}return a}update(e,t){if(this._properties.size===0){Object.assign(e,t);return}const r=this._createAnimations(e,t);if(r.length)return animator.add(this._chart,r),!0}}function awaitAll(n,e){const t=[],r=Object.keys(e);for(let a=0;a<r.length;a++){const o=n[r[a]];o&&o.active()&&t.push(o.wait())}return Promise.all(t)}function resolveTargetOptions(n,e){if(!e)return;let t=n.options;if(!t){n.options=e;return}return t.$shared&&(n.options=t=Object.assign({},t,{$shared:!1,$animations:{}})),t}function scaleClip(n,e){const t=n&&n.options||{},r=t.reverse,a=t.min===void 0?e:0,o=t.max===void 0?e:0;return{start:r?o:a,end:r?a:o}}function defaultClip(n,e,t){if(t===!1)return!1;const r=scaleClip(n,t),a=scaleClip(e,t);return{top:a.end,right:r.end,bottom:a.start,left:r.start}}function toClip(n){let e,t,r,a;return isObject(n)?(e=n.top,t=n.right,r=n.bottom,a=n.left):e=t=r=a=n,{top:e,right:t,bottom:r,left:a,disabled:n===!1}}function getSortedDatasetIndices(n,e){const t=[],r=n._getSortedDatasetMetas(e);let a,o;for(a=0,o=r.length;a<o;++a)t.push(r[a].index);return t}function applyStack(n,e,t,r={}){const a=n.keys,o=r.mode==="single";let s,l,c,f;if(e===null)return;let d=!1;for(s=0,l=a.length;s<l;++s){if(c=+a[s],c===t){if(d=!0,r.all)continue;break}f=n.values[c],isNumberFinite(f)&&(o||e===0||sign(e)===sign(f))&&(e+=f)}return!d&&!r.all?0:e}function convertObjectDataToArray(n,e){const{iScale:t,vScale:r}=e,a=t.axis==="x"?"x":"y",o=r.axis==="x"?"x":"y",s=Object.keys(n),l=new Array(s.length);let c,f,d;for(c=0,f=s.length;c<f;++c)d=s[c],l[c]={[a]:d,[o]:n[d]};return l}function isStacked(n,e){const t=n&&n.options.stacked;return t||t===void 0&&e.stack!==void 0}function getStackKey(n,e,t){return`${n.id}.${e.id}.${t.stack||t.type}`}function getUserBounds(n){const{min:e,max:t,minDefined:r,maxDefined:a}=n.getUserBounds();return{min:r?e:Number.NEGATIVE_INFINITY,max:a?t:Number.POSITIVE_INFINITY}}function getOrCreateStack(n,e,t){const r=n[e]||(n[e]={});return r[t]||(r[t]={})}function getLastIndexInStack(n,e,t,r){for(const a of e.getMatchingVisibleMetas(r).reverse()){const o=n[a.index];if(t&&o>0||!t&&o<0)return a.index}return null}function updateStacks(n,e){const{chart:t,_cachedMeta:r}=n,a=t._stacks||(t._stacks={}),{iScale:o,vScale:s,index:l}=r,c=o.axis,f=s.axis,d=getStackKey(o,s,r),p=e.length;let _;for(let b=0;b<p;++b){const y=e[b],{[c]:E,[f]:C}=y,D=y._stacks||(y._stacks={});_=D[f]=getOrCreateStack(a,d,E),_[l]=C,_._top=getLastIndexInStack(_,s,!0,r.type),_._bottom=getLastIndexInStack(_,s,!1,r.type);const M=_._visualValues||(_._visualValues={});M[l]=C}}function getFirstScaleId(n,e){const t=n.scales;return Object.keys(t).filter(r=>t[r].axis===e).shift()}function createDatasetContext(n,e){return createContext(n,{active:!1,dataset:void 0,datasetIndex:e,index:e,mode:"default",type:"dataset"})}function createDataContext(n,e,t){return createContext(n,{active:!1,dataIndex:e,parsed:void 0,raw:void 0,element:t,index:e,mode:"default",type:"data"})}function clearStacks(n,e){const t=n.controller.index,r=n.vScale&&n.vScale.axis;if(r){e=e||n._parsed;for(const a of e){const o=a._stacks;if(!o||o[r]===void 0||o[r][t]===void 0)return;delete o[r][t],o[r]._visualValues!==void 0&&o[r]._visualValues[t]!==void 0&&delete o[r]._visualValues[t]}}}const isDirectUpdateMode=n=>n==="reset"||n==="none",cloneIfNotShared=(n,e)=>e?n:Object.assign({},n),createStack=(n,e,t)=>n&&!e.hidden&&e._stacked&&{keys:getSortedDatasetIndices(t,!0),values:null};class DatasetController{static defaults={};static datasetElementType=null;static dataElementType=null;constructor(e,t){this.chart=e,this._ctx=e.ctx,this.index=t,this._cachedDataOpts={},this._cachedMeta=this.getMeta(),this._type=this._cachedMeta.type,this.options=void 0,this._parsing=!1,this._data=void 0,this._objectData=void 0,this._sharedOptions=void 0,this._drawStart=void 0,this._drawCount=void 0,this.enableOptionSharing=!1,this.supportsDecimation=!1,this.$context=void 0,this._syncList=[],this.datasetElementType=new.target.datasetElementType,this.dataElementType=new.target.dataElementType,this.initialize()}initialize(){const e=this._cachedMeta;this.configure(),this.linkScales(),e._stacked=isStacked(e.vScale,e),this.addElements(),this.options.fill&&!this.chart.isPluginEnabled("filler")&&console.warn("Tried to use the 'fill' option without the 'Filler' plugin enabled. Please import and register the 'Filler' plugin and make sure it is not disabled in the options")}updateIndex(e){this.index!==e&&clearStacks(this._cachedMeta),this.index=e}linkScales(){const e=this.chart,t=this._cachedMeta,r=this.getDataset(),a=(p,_,b,y)=>p==="x"?_:p==="r"?y:b,o=t.xAxisID=valueOrDefault(r.xAxisID,getFirstScaleId(e,"x")),s=t.yAxisID=valueOrDefault(r.yAxisID,getFirstScaleId(e,"y")),l=t.rAxisID=valueOrDefault(r.rAxisID,getFirstScaleId(e,"r")),c=t.indexAxis,f=t.iAxisID=a(c,o,s,l),d=t.vAxisID=a(c,s,o,l);t.xScale=this.getScaleForId(o),t.yScale=this.getScaleForId(s),t.rScale=this.getScaleForId(l),t.iScale=this.getScaleForId(f),t.vScale=this.getScaleForId(d)}getDataset(){return this.chart.data.datasets[this.index]}getMeta(){return this.chart.getDatasetMeta(this.index)}getScaleForId(e){return this.chart.scales[e]}_getOtherScale(e){const t=this._cachedMeta;return e===t.iScale?t.vScale:t.iScale}reset(){this._update("reset")}_destroy(){const e=this._cachedMeta;this._data&&unlistenArrayEvents(this._data,this),e._stacked&&clearStacks(e)}_dataCheck(){const e=this.getDataset(),t=e.data||(e.data=[]),r=this._data;if(isObject(t)){const a=this._cachedMeta;this._data=convertObjectDataToArray(t,a)}else if(r!==t){if(r){unlistenArrayEvents(r,this);const a=this._cachedMeta;clearStacks(a),a._parsed=[]}t&&Object.isExtensible(t)&&listenArrayEvents(t,this),this._syncList=[],this._data=t}}addElements(){const e=this._cachedMeta;this._dataCheck(),this.datasetElementType&&(e.dataset=new this.datasetElementType)}buildOrUpdateElements(e){const t=this._cachedMeta,r=this.getDataset();let a=!1;this._dataCheck();const o=t._stacked;t._stacked=isStacked(t.vScale,t),t.stack!==r.stack&&(a=!0,clearStacks(t),t.stack=r.stack),this._resyncElements(e),(a||o!==t._stacked)&&(updateStacks(this,t._parsed),t._stacked=isStacked(t.vScale,t))}configure(){const e=this.chart.config,t=e.datasetScopeKeys(this._type),r=e.getOptionScopes(this.getDataset(),t,!0);this.options=e.createResolver(r,this.getContext()),this._parsing=this.options.parsing,this._cachedDataOpts={}}parse(e,t){const{_cachedMeta:r,_data:a}=this,{iScale:o,_stacked:s}=r,l=o.axis;let c=e===0&&t===a.length?!0:r._sorted,f=e>0&&r._parsed[e-1],d,p,_;if(this._parsing===!1)r._parsed=a,r._sorted=!0,_=a;else{isArray(a[e])?_=this.parseArrayData(r,a,e,t):isObject(a[e])?_=this.parseObjectData(r,a,e,t):_=this.parsePrimitiveData(r,a,e,t);const b=()=>p[l]===null||f&&p[l]<f[l];for(d=0;d<t;++d)r._parsed[d+e]=p=_[d],c&&(b()&&(c=!1),f=p);r._sorted=c}s&&updateStacks(this,_)}parsePrimitiveData(e,t,r,a){const{iScale:o,vScale:s}=e,l=o.axis,c=s.axis,f=o.getLabels(),d=o===s,p=new Array(a);let _,b,y;for(_=0,b=a;_<b;++_)y=_+r,p[_]={[l]:d||o.parse(f[y],y),[c]:s.parse(t[y],y)};return p}parseArrayData(e,t,r,a){const{xScale:o,yScale:s}=e,l=new Array(a);let c,f,d,p;for(c=0,f=a;c<f;++c)d=c+r,p=t[d],l[c]={x:o.parse(p[0],d),y:s.parse(p[1],d)};return l}parseObjectData(e,t,r,a){const{xScale:o,yScale:s}=e,{xAxisKey:l="x",yAxisKey:c="y"}=this._parsing,f=new Array(a);let d,p,_,b;for(d=0,p=a;d<p;++d)_=d+r,b=t[_],f[d]={x:o.parse(resolveObjectKey(b,l),_),y:s.parse(resolveObjectKey(b,c),_)};return f}getParsed(e){return this._cachedMeta._parsed[e]}getDataElement(e){return this._cachedMeta.data[e]}applyStack(e,t,r){const a=this.chart,o=this._cachedMeta,s=t[e.axis],l={keys:getSortedDatasetIndices(a,!0),values:t._stacks[e.axis]._visualValues};return applyStack(l,s,o.index,{mode:r})}updateRangeFromParsed(e,t,r,a){const o=r[t.axis];let s=o===null?NaN:o;const l=a&&r._stacks[t.axis];a&&l&&(a.values=l,s=applyStack(a,o,this._cachedMeta.index)),e.min=Math.min(e.min,s),e.max=Math.max(e.max,s)}getMinMax(e,t){const r=this._cachedMeta,a=r._parsed,o=r._sorted&&e===r.iScale,s=a.length,l=this._getOtherScale(e),c=createStack(t,r,this.chart),f={min:Number.POSITIVE_INFINITY,max:Number.NEGATIVE_INFINITY},{min:d,max:p}=getUserBounds(l);let _,b;function y(){b=a[_];const E=b[l.axis];return!isNumberFinite(b[e.axis])||d>E||p<E}for(_=0;_<s&&!(!y()&&(this.updateRangeFromParsed(f,e,b,c),o));++_);if(o){for(_=s-1;_>=0;--_)if(!y()){this.updateRangeFromParsed(f,e,b,c);break}}return f}getAllParsedValues(e){const t=this._cachedMeta._parsed,r=[];let a,o,s;for(a=0,o=t.length;a<o;++a)s=t[a][e.axis],isNumberFinite(s)&&r.push(s);return r}getMaxOverflow(){return!1}getLabelAndValue(e){const t=this._cachedMeta,r=t.iScale,a=t.vScale,o=this.getParsed(e);return{label:r?""+r.getLabelForValue(o[r.axis]):"",value:a?""+a.getLabelForValue(o[a.axis]):""}}_update(e){const t=this._cachedMeta;this.update(e||"default"),t._clip=toClip(valueOrDefault(this.options.clip,defaultClip(t.xScale,t.yScale,this.getMaxOverflow())))}update(e){}draw(){const e=this._ctx,t=this.chart,r=this._cachedMeta,a=r.data||[],o=t.chartArea,s=[],l=this._drawStart||0,c=this._drawCount||a.length-l,f=this.options.drawActiveElementsOnTop;let d;for(r.dataset&&r.dataset.draw(e,o,l,c),d=l;d<l+c;++d){const p=a[d];p.hidden||(p.active&&f?s.push(p):p.draw(e,o))}for(d=0;d<s.length;++d)s[d].draw(e,o)}getStyle(e,t){const r=t?"active":"default";return e===void 0&&this._cachedMeta.dataset?this.resolveDatasetElementOptions(r):this.resolveDataElementOptions(e||0,r)}getContext(e,t,r){const a=this.getDataset();let o;if(e>=0&&e<this._cachedMeta.data.length){const s=this._cachedMeta.data[e];o=s.$context||(s.$context=createDataContext(this.getContext(),e,s)),o.parsed=this.getParsed(e),o.raw=a.data[e],o.index=o.dataIndex=e}else o=this.$context||(this.$context=createDatasetContext(this.chart.getContext(),this.index)),o.dataset=a,o.index=o.datasetIndex=this.index;return o.active=!!t,o.mode=r,o}resolveDatasetElementOptions(e){return this._resolveElementOptions(this.datasetElementType.id,e)}resolveDataElementOptions(e,t){return this._resolveElementOptions(this.dataElementType.id,t,e)}_resolveElementOptions(e,t="default",r){const a=t==="active",o=this._cachedDataOpts,s=e+"-"+t,l=o[s],c=this.enableOptionSharing&&defined(r);if(l)return cloneIfNotShared(l,c);const f=this.chart.config,d=f.datasetElementScopeKeys(this._type,e),p=a?[`${e}Hover`,"hover",e,""]:[e,""],_=f.getOptionScopes(this.getDataset(),d),b=Object.keys(defaults.elements[e]),y=()=>this.getContext(r,a,t),E=f.resolveNamedOptions(_,b,y,p);return E.$shared&&(E.$shared=c,o[s]=Object.freeze(cloneIfNotShared(E,c))),E}_resolveAnimations(e,t,r){const a=this.chart,o=this._cachedDataOpts,s=`animation-${t}`,l=o[s];if(l)return l;let c;if(a.options.animation!==!1){const d=this.chart.config,p=d.datasetAnimationScopeKeys(this._type,t),_=d.getOptionScopes(this.getDataset(),p);c=d.createResolver(_,this.getContext(e,r,t))}const f=new Animations(a,c&&c.animations);return c&&c._cacheable&&(o[s]=Object.freeze(f)),f}getSharedOptions(e){if(e.$shared)return this._sharedOptions||(this._sharedOptions=Object.assign({},e))}includeOptions(e,t){return!t||isDirectUpdateMode(e)||this.chart._animationsDisabled}_getSharedOptions(e,t){const r=this.resolveDataElementOptions(e,t),a=this._sharedOptions,o=this.getSharedOptions(r),s=this.includeOptions(t,o)||o!==a;return this.updateSharedOptions(o,t,r),{sharedOptions:o,includeOptions:s}}updateElement(e,t,r,a){isDirectUpdateMode(a)?Object.assign(e,r):this._resolveAnimations(t,a).update(e,r)}updateSharedOptions(e,t,r){e&&!isDirectUpdateMode(t)&&this._resolveAnimations(void 0,t).update(e,r)}_setStyle(e,t,r,a){e.active=a;const o=this.getStyle(t,a);this._resolveAnimations(t,r,a).update(e,{options:!a&&this.getSharedOptions(o)||o})}removeHoverStyle(e,t,r){this._setStyle(e,r,"active",!1)}setHoverStyle(e,t,r){this._setStyle(e,r,"active",!0)}_removeDatasetHoverStyle(){const e=this._cachedMeta.dataset;e&&this._setStyle(e,void 0,"active",!1)}_setDatasetHoverStyle(){const e=this._cachedMeta.dataset;e&&this._setStyle(e,void 0,"active",!0)}_resyncElements(e){const t=this._data,r=this._cachedMeta.data;for(const[l,c,f]of this._syncList)this[l](c,f);this._syncList=[];const a=r.length,o=t.length,s=Math.min(o,a);s&&this.parse(0,s),o>a?this._insertElements(a,o-a,e):o<a&&this._removeElements(o,a-o)}_insertElements(e,t,r=!0){const a=this._cachedMeta,o=a.data,s=e+t;let l;const c=f=>{for(f.length+=t,l=f.length-1;l>=s;l--)f[l]=f[l-t]};for(c(o),l=e;l<s;++l)o[l]=new this.dataElementType;this._parsing&&c(a._parsed),this.parse(e,t),r&&this.updateElements(o,e,t,"reset")}updateElements(e,t,r,a){}_removeElements(e,t){const r=this._cachedMeta;if(this._parsing){const a=r._parsed.splice(e,t);r._stacked&&clearStacks(r,a)}r.data.splice(e,t)}_sync(e){if(this._parsing)this._syncList.push(e);else{const[t,r,a]=e;this[t](r,a)}this.chart._dataChanges.push([this.index,...e])}_onDataPush(){const e=arguments.length;this._sync(["_insertElements",this.getDataset().data.length-e,e])}_onDataPop(){this._sync(["_removeElements",this._cachedMeta.data.length-1,1])}_onDataShift(){this._sync(["_removeElements",0,1])}_onDataSplice(e,t){t&&this._sync(["_removeElements",e,t]);const r=arguments.length-2;r&&this._sync(["_insertElements",e,r])}_onDataUnshift(){this._sync(["_insertElements",0,arguments.length])}}function getAllScaleValues(n,e){if(!n._cache.$bar){const t=n.getMatchingVisibleMetas(e);let r=[];for(let a=0,o=t.length;a<o;a++)r=r.concat(t[a].controller.getAllParsedValues(n));n._cache.$bar=_arrayUnique(r.sort((a,o)=>a-o))}return n._cache.$bar}function computeMinSampleSize(n){const e=n.iScale,t=getAllScaleValues(e,n.type);let r=e._length,a,o,s,l;const c=()=>{s===32767||s===-32768||(defined(l)&&(r=Math.min(r,Math.abs(s-l)||r)),l=s)};for(a=0,o=t.length;a<o;++a)s=e.getPixelForValue(t[a]),c();for(l=void 0,a=0,o=e.ticks.length;a<o;++a)s=e.getPixelForTick(a),c();return r}function computeFitCategoryTraits(n,e,t,r){const a=t.barThickness;let o,s;return isNullOrUndef(a)?(o=e.min*t.categoryPercentage,s=t.barPercentage):(o=a*r,s=1),{chunk:o/r,ratio:s,start:e.pixels[n]-o/2}}function computeFlexCategoryTraits(n,e,t,r){const a=e.pixels,o=a[n];let s=n>0?a[n-1]:null,l=n<a.length-1?a[n+1]:null;const c=t.categoryPercentage;s===null&&(s=o-(l===null?e.end-e.start:l-o)),l===null&&(l=o+o-s);const f=o-(o-Math.min(s,l))/2*c;return{chunk:Math.abs(l-s)/2*c/r,ratio:t.barPercentage,start:f}}function parseFloatBar(n,e,t,r){const a=t.parse(n[0],r),o=t.parse(n[1],r),s=Math.min(a,o),l=Math.max(a,o);let c=s,f=l;Math.abs(s)>Math.abs(l)&&(c=l,f=s),e[t.axis]=f,e._custom={barStart:c,barEnd:f,start:a,end:o,min:s,max:l}}function parseValue(n,e,t,r){return isArray(n)?parseFloatBar(n,e,t,r):e[t.axis]=t.parse(n,r),e}function parseArrayOrPrimitive(n,e,t,r){const a=n.iScale,o=n.vScale,s=a.getLabels(),l=a===o,c=[];let f,d,p,_;for(f=t,d=t+r;f<d;++f)_=e[f],p={},p[a.axis]=l||a.parse(s[f],f),c.push(parseValue(_,p,o,f));return c}function isFloatBar(n){return n&&n.barStart!==void 0&&n.barEnd!==void 0}function barSign(n,e,t){return n!==0?sign(n):(e.isHorizontal()?1:-1)*(e.min>=t?1:-1)}function borderProps(n){let e,t,r,a,o;return n.horizontal?(e=n.base>n.x,t="left",r="right"):(e=n.base<n.y,t="bottom",r="top"),e?(a="end",o="start"):(a="start",o="end"),{start:t,end:r,reverse:e,top:a,bottom:o}}function setBorderSkipped(n,e,t,r){let a=e.borderSkipped;const o={};if(!a){n.borderSkipped=o;return}if(a===!0){n.borderSkipped={top:!0,right:!0,bottom:!0,left:!0};return}const{start:s,end:l,reverse:c,top:f,bottom:d}=borderProps(n);a==="middle"&&t&&(n.enableBorderRadius=!0,(t._top||0)===r?a=f:(t._bottom||0)===r?a=d:(o[parseEdge(d,s,l,c)]=!0,a=f)),o[parseEdge(a,s,l,c)]=!0,n.borderSkipped=o}function parseEdge(n,e,t,r){return r?(n=swap(n,e,t),n=startEnd(n,t,e)):n=startEnd(n,e,t),n}function swap(n,e,t){return n===e?t:n===t?e:n}function startEnd(n,e,t){return n==="start"?e:n==="end"?t:n}function setInflateAmount(n,{inflateAmount:e},t){n.inflateAmount=e==="auto"?t===1?.33:0:e}class BarController extends DatasetController{static id="bar";static defaults={datasetElementType:!1,dataElementType:"bar",categoryPercentage:.8,barPercentage:.9,grouped:!0,animations:{numbers:{type:"number",properties:["x","y","base","width","height"]}}};static overrides={scales:{_index_:{type:"category",offset:!0,grid:{offset:!0}},_value_:{type:"linear",beginAtZero:!0}}};parsePrimitiveData(e,t,r,a){return parseArrayOrPrimitive(e,t,r,a)}parseArrayData(e,t,r,a){return parseArrayOrPrimitive(e,t,r,a)}parseObjectData(e,t,r,a){const{iScale:o,vScale:s}=e,{xAxisKey:l="x",yAxisKey:c="y"}=this._parsing,f=o.axis==="x"?l:c,d=s.axis==="x"?l:c,p=[];let _,b,y,E;for(_=r,b=r+a;_<b;++_)E=t[_],y={},y[o.axis]=o.parse(resolveObjectKey(E,f),_),p.push(parseValue(resolveObjectKey(E,d),y,s,_));return p}updateRangeFromParsed(e,t,r,a){super.updateRangeFromParsed(e,t,r,a);const o=r._custom;o&&t===this._cachedMeta.vScale&&(e.min=Math.min(e.min,o.min),e.max=Math.max(e.max,o.max))}getMaxOverflow(){return 0}getLabelAndValue(e){const t=this._cachedMeta,{iScale:r,vScale:a}=t,o=this.getParsed(e),s=o._custom,l=isFloatBar(s)?"["+s.start+", "+s.end+"]":""+a.getLabelForValue(o[a.axis]);return{label:""+r.getLabelForValue(o[r.axis]),value:l}}initialize(){this.enableOptionSharing=!0,super.initialize();const e=this._cachedMeta;e.stack=this.getDataset().stack}update(e){const t=this._cachedMeta;this.updateElements(t.data,0,t.data.length,e)}updateElements(e,t,r,a){const o=a==="reset",{index:s,_cachedMeta:{vScale:l}}=this,c=l.getBasePixel(),f=l.isHorizontal(),d=this._getRuler(),{sharedOptions:p,includeOptions:_}=this._getSharedOptions(t,a);for(let b=t;b<t+r;b++){const y=this.getParsed(b),E=o||isNullOrUndef(y[l.axis])?{base:c,head:c}:this._calculateBarValuePixels(b),C=this._calculateBarIndexPixels(b,d),D=(y._stacks||{})[l.axis],M={horizontal:f,base:E.base,enableBorderRadius:!D||isFloatBar(y._custom)||s===D._top||s===D._bottom,x:f?E.head:C.center,y:f?C.center:E.head,height:f?C.size:Math.abs(E.size),width:f?Math.abs(E.size):C.size};_&&(M.options=p||this.resolveDataElementOptions(b,e[b].active?"active":a));const F=M.options||e[b].options;setBorderSkipped(M,F,D,s),setInflateAmount(M,F,d.ratio),this.updateElement(e[b],b,M,a)}}_getStacks(e,t){const{iScale:r}=this._cachedMeta,a=r.getMatchingVisibleMetas(this._type).filter(d=>d.controller.options.grouped),o=r.options.stacked,s=[],l=this._cachedMeta.controller.getParsed(t),c=l&&l[r.axis],f=d=>{const p=d._parsed.find(b=>b[r.axis]===c),_=p&&p[d.vScale.axis];if(isNullOrUndef(_)||isNaN(_))return!0};for(const d of a)if(!(t!==void 0&&f(d))&&((o===!1||s.indexOf(d.stack)===-1||o===void 0&&d.stack===void 0)&&s.push(d.stack),d.index===e))break;return s.length||s.push(void 0),s}_getStackCount(e){return this._getStacks(void 0,e).length}_getAxisCount(){return this._getAxis().length}getFirstScaleIdForIndexAxis(){const e=this.chart.scales,t=this.chart.options.indexAxis;return Object.keys(e).filter(r=>e[r].axis===t).shift()}_getAxis(){const e={},t=this.getFirstScaleIdForIndexAxis();for(const r of this.chart.data.datasets)e[valueOrDefault(this.chart.options.indexAxis==="x"?r.xAxisID:r.yAxisID,t)]=!0;return Object.keys(e)}_getStackIndex(e,t,r){const a=this._getStacks(e,r),o=t!==void 0?a.indexOf(t):-1;return o===-1?a.length-1:o}_getRuler(){const e=this.options,t=this._cachedMeta,r=t.iScale,a=[];let o,s;for(o=0,s=t.data.length;o<s;++o)a.push(r.getPixelForValue(this.getParsed(o)[r.axis],o));const l=e.barThickness;return{min:l||computeMinSampleSize(t),pixels:a,start:r._startPixel,end:r._endPixel,stackCount:this._getStackCount(),scale:r,grouped:e.grouped,ratio:l?1:e.categoryPercentage*e.barPercentage}}_calculateBarValuePixels(e){const{_cachedMeta:{vScale:t,_stacked:r,index:a},options:{base:o,minBarLength:s}}=this,l=o||0,c=this.getParsed(e),f=c._custom,d=isFloatBar(f);let p=c[t.axis],_=0,b=r?this.applyStack(t,c,r):p,y,E;b!==p&&(_=b-p,b=p),d&&(p=f.barStart,b=f.barEnd-f.barStart,p!==0&&sign(p)!==sign(f.barEnd)&&(_=0),_+=p);const C=!isNullOrUndef(o)&&!d?o:_;let D=t.getPixelForValue(C);if(this.chart.getDataVisibility(e)?y=t.getPixelForValue(_+b):y=D,E=y-D,Math.abs(E)<s){E=barSign(E,t,l)*s,p===l&&(D-=E/2);const M=t.getPixelForDecimal(0),F=t.getPixelForDecimal(1),P=Math.min(M,F),H=Math.max(M,F);D=Math.max(Math.min(D,H),P),y=D+E,r&&!d&&(c._stacks[t.axis]._visualValues[a]=t.getValueForPixel(y)-t.getValueForPixel(D))}if(D===t.getPixelForValue(l)){const M=sign(E)*t.getLineWidthForValue(l)/2;D+=M,E-=M}return{size:E,base:D,head:y,center:y+E/2}}_calculateBarIndexPixels(e,t){const r=t.scale,a=this.options,o=a.skipNull,s=valueOrDefault(a.maxBarThickness,1/0);let l,c;const f=this._getAxisCount();if(t.grouped){const d=o?this._getStackCount(e):t.stackCount,p=a.barThickness==="flex"?computeFlexCategoryTraits(e,t,a,d*f):computeFitCategoryTraits(e,t,a,d*f),_=this.chart.options.indexAxis==="x"?this.getDataset().xAxisID:this.getDataset().yAxisID,b=this._getAxis().indexOf(valueOrDefault(_,this.getFirstScaleIdForIndexAxis())),y=this._getStackIndex(this.index,this._cachedMeta.stack,o?e:void 0)+b;l=p.start+p.chunk*y+p.chunk/2,c=Math.min(s,p.chunk*p.ratio)}else l=r.getPixelForValue(this.getParsed(e)[r.axis],e),c=Math.min(s,t.min*t.ratio);return{base:l-c/2,head:l+c/2,center:l,size:c}}draw(){const e=this._cachedMeta,t=e.vScale,r=e.data,a=r.length;let o=0;for(;o<a;++o)this.getParsed(o)[t.axis]!==null&&!r[o].hidden&&r[o].draw(this._ctx)}}class BubbleController extends DatasetController{static id="bubble";static defaults={datasetElementType:!1,dataElementType:"point",animations:{numbers:{type:"number",properties:["x","y","borderWidth","radius"]}}};static overrides={scales:{x:{type:"linear"},y:{type:"linear"}}};initialize(){this.enableOptionSharing=!0,super.initialize()}parsePrimitiveData(e,t,r,a){const o=super.parsePrimitiveData(e,t,r,a);for(let s=0;s<o.length;s++)o[s]._custom=this.resolveDataElementOptions(s+r).radius;return o}parseArrayData(e,t,r,a){const o=super.parseArrayData(e,t,r,a);for(let s=0;s<o.length;s++){const l=t[r+s];o[s]._custom=valueOrDefault(l[2],this.resolveDataElementOptions(s+r).radius)}return o}parseObjectData(e,t,r,a){const o=super.parseObjectData(e,t,r,a);for(let s=0;s<o.length;s++){const l=t[r+s];o[s]._custom=valueOrDefault(l&&l.r&&+l.r,this.resolveDataElementOptions(s+r).radius)}return o}getMaxOverflow(){const e=this._cachedMeta.data;let t=0;for(let r=e.length-1;r>=0;--r)t=Math.max(t,e[r].size(this.resolveDataElementOptions(r))/2);return t>0&&t}getLabelAndValue(e){const t=this._cachedMeta,r=this.chart.data.labels||[],{xScale:a,yScale:o}=t,s=this.getParsed(e),l=a.getLabelForValue(s.x),c=o.getLabelForValue(s.y),f=s._custom;return{label:r[e]||"",value:"("+l+", "+c+(f?", "+f:"")+")"}}update(e){const t=this._cachedMeta.data;this.updateElements(t,0,t.length,e)}updateElements(e,t,r,a){const o=a==="reset",{iScale:s,vScale:l}=this._cachedMeta,{sharedOptions:c,includeOptions:f}=this._getSharedOptions(t,a),d=s.axis,p=l.axis;for(let _=t;_<t+r;_++){const b=e[_],y=!o&&this.getParsed(_),E={},C=E[d]=o?s.getPixelForDecimal(.5):s.getPixelForValue(y[d]),D=E[p]=o?l.getBasePixel():l.getPixelForValue(y[p]);E.skip=isNaN(C)||isNaN(D),f&&(E.options=c||this.resolveDataElementOptions(_,b.active?"active":a),o&&(E.options.radius=0)),this.updateElement(b,_,E,a)}}resolveDataElementOptions(e,t){const r=this.getParsed(e);let a=super.resolveDataElementOptions(e,t);a.$shared&&(a=Object.assign({},a,{$shared:!1}));const o=a.radius;return t!=="active"&&(a.radius=0),a.radius+=valueOrDefault(r&&r._custom,o),a}}function getRatioAndOffset(n,e,t){let r=1,a=1,o=0,s=0;if(e<TAU){const l=n,c=l+e,f=Math.cos(l),d=Math.sin(l),p=Math.cos(c),_=Math.sin(c),b=(F,P,H)=>_angleBetween(F,l,c,!0)?1:Math.max(P,P*t,H,H*t),y=(F,P,H)=>_angleBetween(F,l,c,!0)?-1:Math.min(P,P*t,H,H*t),E=b(0,f,p),C=b(HALF_PI,d,_),D=y(PI,f,p),M=y(PI+HALF_PI,d,_);r=(E-D)/2,a=(C-M)/2,o=-(E+D)/2,s=-(C+M)/2}return{ratioX:r,ratioY:a,offsetX:o,offsetY:s}}class DoughnutController extends DatasetController{static id="doughnut";static defaults={datasetElementType:!1,dataElementType:"arc",animation:{animateRotate:!0,animateScale:!1},animations:{numbers:{type:"number",properties:["circumference","endAngle","innerRadius","outerRadius","startAngle","x","y","offset","borderWidth","spacing"]}},cutout:"50%",rotation:0,circumference:360,radius:"100%",spacing:0,indexAxis:"r"};static descriptors={_scriptable:e=>e!=="spacing",_indexable:e=>e!=="spacing"&&!e.startsWith("borderDash")&&!e.startsWith("hoverBorderDash")};static overrides={aspectRatio:1,plugins:{legend:{labels:{generateLabels(e){const t=e.data,{labels:{pointStyle:r,textAlign:a,color:o,useBorderRadius:s,borderRadius:l}}=e.legend.options;return t.labels.length&&t.datasets.length?t.labels.map((c,f)=>{const p=e.getDatasetMeta(0).controller.getStyle(f);return{text:c,fillStyle:p.backgroundColor,fontColor:o,hidden:!e.getDataVisibility(f),lineDash:p.borderDash,lineDashOffset:p.borderDashOffset,lineJoin:p.borderJoinStyle,lineWidth:p.borderWidth,strokeStyle:p.borderColor,textAlign:a,pointStyle:r,borderRadius:s&&(l||p.borderRadius),index:f}}):[]}},onClick(e,t,r){r.chart.toggleDataVisibility(t.index),r.chart.update()}}}};constructor(e,t){super(e,t),this.enableOptionSharing=!0,this.innerRadius=void 0,this.outerRadius=void 0,this.offsetX=void 0,this.offsetY=void 0}linkScales(){}parse(e,t){const r=this.getDataset().data,a=this._cachedMeta;if(this._parsing===!1)a._parsed=r;else{let o=c=>+r[c];if(isObject(r[e])){const{key:c="value"}=this._parsing;o=f=>+resolveObjectKey(r[f],c)}let s,l;for(s=e,l=e+t;s<l;++s)a._parsed[s]=o(s)}}_getRotation(){return toRadians(this.options.rotation-90)}_getCircumference(){return toRadians(this.options.circumference)}_getRotationExtents(){let e=TAU,t=-TAU;for(let r=0;r<this.chart.data.datasets.length;++r)if(this.chart.isDatasetVisible(r)&&this.chart.getDatasetMeta(r).type===this._type){const a=this.chart.getDatasetMeta(r).controller,o=a._getRotation(),s=a._getCircumference();e=Math.min(e,o),t=Math.max(t,o+s)}return{rotation:e,circumference:t-e}}update(e){const t=this.chart,{chartArea:r}=t,a=this._cachedMeta,o=a.data,s=this.getMaxBorderWidth()+this.getMaxOffset(o)+this.options.spacing,l=Math.max((Math.min(r.width,r.height)-s)/2,0),c=Math.min(toPercentage(this.options.cutout,l),1),f=this._getRingWeight(this.index),{circumference:d,rotation:p}=this._getRotationExtents(),{ratioX:_,ratioY:b,offsetX:y,offsetY:E}=getRatioAndOffset(p,d,c),C=(r.width-s)/_,D=(r.height-s)/b,M=Math.max(Math.min(C,D)/2,0),F=toDimension(this.options.radius,M),P=Math.max(F*c,0),H=(F-P)/this._getVisibleDatasetWeightTotal();this.offsetX=y*F,this.offsetY=E*F,a.total=this.calculateTotal(),this.outerRadius=F-H*this._getRingWeightOffset(this.index),this.innerRadius=Math.max(this.outerRadius-H*f,0),this.updateElements(o,0,o.length,e)}_circumference(e,t){const r=this.options,a=this._cachedMeta,o=this._getCircumference();return t&&r.animation.animateRotate||!this.chart.getDataVisibility(e)||a._parsed[e]===null||a.data[e].hidden?0:this.calculateCircumference(a._parsed[e]*o/TAU)}updateElements(e,t,r,a){const o=a==="reset",s=this.chart,l=s.chartArea,f=s.options.animation,d=(l.left+l.right)/2,p=(l.top+l.bottom)/2,_=o&&f.animateScale,b=_?0:this.innerRadius,y=_?0:this.outerRadius,{sharedOptions:E,includeOptions:C}=this._getSharedOptions(t,a);let D=this._getRotation(),M;for(M=0;M<t;++M)D+=this._circumference(M,o);for(M=t;M<t+r;++M){const F=this._circumference(M,o),P=e[M],H={x:d+this.offsetX,y:p+this.offsetY,startAngle:D,endAngle:D+F,circumference:F,outerRadius:y,innerRadius:b};C&&(H.options=E||this.resolveDataElementOptions(M,P.active?"active":a)),D+=F,this.updateElement(P,M,H,a)}}calculateTotal(){const e=this._cachedMeta,t=e.data;let r=0,a;for(a=0;a<t.length;a++){const o=e._parsed[a];o!==null&&!isNaN(o)&&this.chart.getDataVisibility(a)&&!t[a].hidden&&(r+=Math.abs(o))}return r}calculateCircumference(e){const t=this._cachedMeta.total;return t>0&&!isNaN(e)?TAU*(Math.abs(e)/t):0}getLabelAndValue(e){const t=this._cachedMeta,r=this.chart,a=r.data.labels||[],o=formatNumber(t._parsed[e],r.options.locale);return{label:a[e]||"",value:o}}getMaxBorderWidth(e){let t=0;const r=this.chart;let a,o,s,l,c;if(!e){for(a=0,o=r.data.datasets.length;a<o;++a)if(r.isDatasetVisible(a)){s=r.getDatasetMeta(a),e=s.data,l=s.controller;break}}if(!e)return 0;for(a=0,o=e.length;a<o;++a)c=l.resolveDataElementOptions(a),c.borderAlign!=="inner"&&(t=Math.max(t,c.borderWidth||0,c.hoverBorderWidth||0));return t}getMaxOffset(e){let t=0;for(let r=0,a=e.length;r<a;++r){const o=this.resolveDataElementOptions(r);t=Math.max(t,o.offset||0,o.hoverOffset||0)}return t}_getRingWeightOffset(e){let t=0;for(let r=0;r<e;++r)this.chart.isDatasetVisible(r)&&(t+=this._getRingWeight(r));return t}_getRingWeight(e){return Math.max(valueOrDefault(this.chart.data.datasets[e].weight,1),0)}_getVisibleDatasetWeightTotal(){return this._getRingWeightOffset(this.chart.data.datasets.length)||1}}class LineController extends DatasetController{static id="line";static defaults={datasetElementType:"line",dataElementType:"point",showLine:!0,spanGaps:!1};static overrides={scales:{_index_:{type:"category"},_value_:{type:"linear"}}};initialize(){this.enableOptionSharing=!0,this.supportsDecimation=!0,super.initialize()}update(e){const t=this._cachedMeta,{dataset:r,data:a=[],_dataset:o}=t,s=this.chart._animationsDisabled;let{start:l,count:c}=_getStartAndCountOfVisiblePoints(t,a,s);this._drawStart=l,this._drawCount=c,_scaleRangesChanged(t)&&(l=0,c=a.length),r._chart=this.chart,r._datasetIndex=this.index,r._decimated=!!o._decimated,r.points=a;const f=this.resolveDatasetElementOptions(e);this.options.showLine||(f.borderWidth=0),f.segment=this.options.segment,this.updateElement(r,void 0,{animated:!s,options:f},e),this.updateElements(a,l,c,e)}updateElements(e,t,r,a){const o=a==="reset",{iScale:s,vScale:l,_stacked:c,_dataset:f}=this._cachedMeta,{sharedOptions:d,includeOptions:p}=this._getSharedOptions(t,a),_=s.axis,b=l.axis,{spanGaps:y,segment:E}=this.options,C=isNumber(y)?y:Number.POSITIVE_INFINITY,D=this.chart._animationsDisabled||o||a==="none",M=t+r,F=e.length;let P=t>0&&this.getParsed(t-1);for(let H=0;H<F;++H){const B=e[H],g=D?B:{};if(H<t||H>=M){g.skip=!0;continue}const q=this.getParsed(H),G=isNullOrUndef(q[b]),Z=g[_]=s.getPixelForValue(q[_],H),te=g[b]=o||G?l.getBasePixel():l.getPixelForValue(c?this.applyStack(l,q,c):q[b],H);g.skip=isNaN(Z)||isNaN(te)||G,g.stop=H>0&&Math.abs(q[_]-P[_])>C,E&&(g.parsed=q,g.raw=f.data[H]),p&&(g.options=d||this.resolveDataElementOptions(H,B.active?"active":a)),D||this.updateElement(B,H,g,a),P=q}}getMaxOverflow(){const e=this._cachedMeta,t=e.dataset,r=t.options&&t.options.borderWidth||0,a=e.data||[];if(!a.length)return r;const o=a[0].size(this.resolveDataElementOptions(0)),s=a[a.length-1].size(this.resolveDataElementOptions(a.length-1));return Math.max(r,o,s)/2}draw(){const e=this._cachedMeta;e.dataset.updateControlPoints(this.chart.chartArea,e.iScale.axis),super.draw()}}class PolarAreaController extends DatasetController{static id="polarArea";static defaults={dataElementType:"arc",animation:{animateRotate:!0,animateScale:!0},animations:{numbers:{type:"number",properties:["x","y","startAngle","endAngle","innerRadius","outerRadius"]}},indexAxis:"r",startAngle:0};static overrides={aspectRatio:1,plugins:{legend:{labels:{generateLabels(e){const t=e.data;if(t.labels.length&&t.datasets.length){const{labels:{pointStyle:r,color:a}}=e.legend.options;return t.labels.map((o,s)=>{const c=e.getDatasetMeta(0).controller.getStyle(s);return{text:o,fillStyle:c.backgroundColor,strokeStyle:c.borderColor,fontColor:a,lineWidth:c.borderWidth,pointStyle:r,hidden:!e.getDataVisibility(s),index:s}})}return[]}},onClick(e,t,r){r.chart.toggleDataVisibility(t.index),r.chart.update()}}},scales:{r:{type:"radialLinear",angleLines:{display:!1},beginAtZero:!0,grid:{circular:!0},pointLabels:{display:!1},startAngle:0}}};constructor(e,t){super(e,t),this.innerRadius=void 0,this.outerRadius=void 0}getLabelAndValue(e){const t=this._cachedMeta,r=this.chart,a=r.data.labels||[],o=formatNumber(t._parsed[e].r,r.options.locale);return{label:a[e]||"",value:o}}parseObjectData(e,t,r,a){return _parseObjectDataRadialScale.bind(this)(e,t,r,a)}update(e){const t=this._cachedMeta.data;this._updateRadius(),this.updateElements(t,0,t.length,e)}getMinMax(){const e=this._cachedMeta,t={min:Number.POSITIVE_INFINITY,max:Number.NEGATIVE_INFINITY};return e.data.forEach((r,a)=>{const o=this.getParsed(a).r;!isNaN(o)&&this.chart.getDataVisibility(a)&&(o<t.min&&(t.min=o),o>t.max&&(t.max=o))}),t}_updateRadius(){const e=this.chart,t=e.chartArea,r=e.options,a=Math.min(t.right-t.left,t.bottom-t.top),o=Math.max(a/2,0),s=Math.max(r.cutoutPercentage?o/100*r.cutoutPercentage:1,0),l=(o-s)/e.getVisibleDatasetCount();this.outerRadius=o-l*this.index,this.innerRadius=this.outerRadius-l}updateElements(e,t,r,a){const o=a==="reset",s=this.chart,c=s.options.animation,f=this._cachedMeta.rScale,d=f.xCenter,p=f.yCenter,_=f.getIndexAngle(0)-.5*PI;let b=_,y;const E=360/this.countVisibleElements();for(y=0;y<t;++y)b+=this._computeAngle(y,a,E);for(y=t;y<t+r;y++){const C=e[y];let D=b,M=b+this._computeAngle(y,a,E),F=s.getDataVisibility(y)?f.getDistanceFromCenterForValue(this.getParsed(y).r):0;b=M,o&&(c.animateScale&&(F=0),c.animateRotate&&(D=M=_));const P={x:d,y:p,innerRadius:0,outerRadius:F,startAngle:D,endAngle:M,options:this.resolveDataElementOptions(y,C.active?"active":a)};this.updateElement(C,y,P,a)}}countVisibleElements(){const e=this._cachedMeta;let t=0;return e.data.forEach((r,a)=>{!isNaN(this.getParsed(a).r)&&this.chart.getDataVisibility(a)&&t++}),t}_computeAngle(e,t,r){return this.chart.getDataVisibility(e)?toRadians(this.resolveDataElementOptions(e,t).angle||r):0}}class PieController extends DoughnutController{static id="pie";static defaults={cutout:0,rotation:0,circumference:360,radius:"100%"}}class RadarController extends DatasetController{static id="radar";static defaults={datasetElementType:"line",dataElementType:"point",indexAxis:"r",showLine:!0,elements:{line:{fill:"start"}}};static overrides={aspectRatio:1,scales:{r:{type:"radialLinear"}}};getLabelAndValue(e){const t=this._cachedMeta.vScale,r=this.getParsed(e);return{label:t.getLabels()[e],value:""+t.getLabelForValue(r[t.axis])}}parseObjectData(e,t,r,a){return _parseObjectDataRadialScale.bind(this)(e,t,r,a)}update(e){const t=this._cachedMeta,r=t.dataset,a=t.data||[],o=t.iScale.getLabels();if(r.points=a,e!=="resize"){const s=this.resolveDatasetElementOptions(e);this.options.showLine||(s.borderWidth=0);const l={_loop:!0,_fullLoop:o.length===a.length,options:s};this.updateElement(r,void 0,l,e)}this.updateElements(a,0,a.length,e)}updateElements(e,t,r,a){const o=this._cachedMeta.rScale,s=a==="reset";for(let l=t;l<t+r;l++){const c=e[l],f=this.resolveDataElementOptions(l,c.active?"active":a),d=o.getPointPositionForValue(l,this.getParsed(l).r),p=s?o.xCenter:d.x,_=s?o.yCenter:d.y,b={x:p,y:_,angle:d.angle,skip:isNaN(p)||isNaN(_),options:f};this.updateElement(c,l,b,a)}}}class ScatterController extends DatasetController{static id="scatter";static defaults={datasetElementType:!1,dataElementType:"point",showLine:!1,fill:!1};static overrides={interaction:{mode:"point"},scales:{x:{type:"linear"},y:{type:"linear"}}};getLabelAndValue(e){const t=this._cachedMeta,r=this.chart.data.labels||[],{xScale:a,yScale:o}=t,s=this.getParsed(e),l=a.getLabelForValue(s.x),c=o.getLabelForValue(s.y);return{label:r[e]||"",value:"("+l+", "+c+")"}}update(e){const t=this._cachedMeta,{data:r=[]}=t,a=this.chart._animationsDisabled;let{start:o,count:s}=_getStartAndCountOfVisiblePoints(t,r,a);if(this._drawStart=o,this._drawCount=s,_scaleRangesChanged(t)&&(o=0,s=r.length),this.options.showLine){this.datasetElementType||this.addElements();const{dataset:l,_dataset:c}=t;l._chart=this.chart,l._datasetIndex=this.index,l._decimated=!!c._decimated,l.points=r;const f=this.resolveDatasetElementOptions(e);f.segment=this.options.segment,this.updateElement(l,void 0,{animated:!a,options:f},e)}else this.datasetElementType&&(delete t.dataset,this.datasetElementType=!1);this.updateElements(r,o,s,e)}addElements(){const{showLine:e}=this.options;!this.datasetElementType&&e&&(this.datasetElementType=this.chart.registry.getElement("line")),super.addElements()}updateElements(e,t,r,a){const o=a==="reset",{iScale:s,vScale:l,_stacked:c,_dataset:f}=this._cachedMeta,d=this.resolveDataElementOptions(t,a),p=this.getSharedOptions(d),_=this.includeOptions(a,p),b=s.axis,y=l.axis,{spanGaps:E,segment:C}=this.options,D=isNumber(E)?E:Number.POSITIVE_INFINITY,M=this.chart._animationsDisabled||o||a==="none";let F=t>0&&this.getParsed(t-1);for(let P=t;P<t+r;++P){const H=e[P],B=this.getParsed(P),g=M?H:{},q=isNullOrUndef(B[y]),G=g[b]=s.getPixelForValue(B[b],P),Z=g[y]=o||q?l.getBasePixel():l.getPixelForValue(c?this.applyStack(l,B,c):B[y],P);g.skip=isNaN(G)||isNaN(Z)||q,g.stop=P>0&&Math.abs(B[b]-F[b])>D,C&&(g.parsed=B,g.raw=f.data[P]),_&&(g.options=p||this.resolveDataElementOptions(P,H.active?"active":a)),M||this.updateElement(H,P,g,a),F=B}this.updateSharedOptions(p,a,d)}getMaxOverflow(){const e=this._cachedMeta,t=e.data||[];if(!this.options.showLine){let l=0;for(let c=t.length-1;c>=0;--c)l=Math.max(l,t[c].size(this.resolveDataElementOptions(c))/2);return l>0&&l}const r=e.dataset,a=r.options&&r.options.borderWidth||0;if(!t.length)return a;const o=t[0].size(this.resolveDataElementOptions(0)),s=t[t.length-1].size(this.resolveDataElementOptions(t.length-1));return Math.max(a,o,s)/2}}var controllers=Object.freeze({__proto__:null,BarController,BubbleController,DoughnutController,LineController,PieController,PolarAreaController,RadarController,ScatterController});function abstract(){throw new Error("This method is not implemented: Check that a complete date adapter is provided.")}class DateAdapterBase{static override(e){Object.assign(DateAdapterBase.prototype,e)}options;constructor(e){this.options=e||{}}init(){}formats(){return abstract()}parse(){return abstract()}format(){return abstract()}add(){return abstract()}diff(){return abstract()}startOf(){return abstract()}endOf(){return abstract()}}var adapters={_date:DateAdapterBase};function binarySearch(n,e,t,r){const{controller:a,data:o,_sorted:s}=n,l=a._cachedMeta.iScale,c=n.dataset&&n.dataset.options?n.dataset.options.spanGaps:null;if(l&&e===l.axis&&e!=="r"&&s&&o.length){const f=l._reversePixels?_rlookupByKey:_lookupByKey;if(r){if(a._sharedOptions){const d=o[0],p=typeof d.getRange=="function"&&d.getRange(e);if(p){const _=f(o,e,t-p),b=f(o,e,t+p);return{lo:_.lo,hi:b.hi}}}}else{const d=f(o,e,t);if(c){const{vScale:p}=a._cachedMeta,{_parsed:_}=n,b=_.slice(0,d.lo+1).reverse().findIndex(E=>!isNullOrUndef(E[p.axis]));d.lo-=Math.max(0,b);const y=_.slice(d.hi).findIndex(E=>!isNullOrUndef(E[p.axis]));d.hi+=Math.max(0,y)}return d}}return{lo:0,hi:o.length-1}}function evaluateInteractionItems(n,e,t,r,a){const o=n.getSortedVisibleDatasetMetas(),s=t[e];for(let l=0,c=o.length;l<c;++l){const{index:f,data:d}=o[l],{lo:p,hi:_}=binarySearch(o[l],e,s,a);for(let b=p;b<=_;++b){const y=d[b];y.skip||r(y,f,b)}}}function getDistanceMetricForAxis(n){const e=n.indexOf("x")!==-1,t=n.indexOf("y")!==-1;return function(r,a){const o=e?Math.abs(r.x-a.x):0,s=t?Math.abs(r.y-a.y):0;return Math.sqrt(Math.pow(o,2)+Math.pow(s,2))}}function getIntersectItems(n,e,t,r,a){const o=[];return!a&&!n.isPointInArea(e)||evaluateInteractionItems(n,t,e,function(l,c,f){!a&&!_isPointInArea(l,n.chartArea,0)||l.inRange(e.x,e.y,r)&&o.push({element:l,datasetIndex:c,index:f})},!0),o}function getNearestRadialItems(n,e,t,r){let a=[];function o(s,l,c){const{startAngle:f,endAngle:d}=s.getProps(["startAngle","endAngle"],r),{angle:p}=getAngleFromPoint(s,{x:e.x,y:e.y});_angleBetween(p,f,d)&&a.push({element:s,datasetIndex:l,index:c})}return evaluateInteractionItems(n,t,e,o),a}function getNearestCartesianItems(n,e,t,r,a,o){let s=[];const l=getDistanceMetricForAxis(t);let c=Number.POSITIVE_INFINITY;function f(d,p,_){const b=d.inRange(e.x,e.y,a);if(r&&!b)return;const y=d.getCenterPoint(a);if(!(!!o||n.isPointInArea(y))&&!b)return;const C=l(e,y);C<c?(s=[{element:d,datasetIndex:p,index:_}],c=C):C===c&&s.push({element:d,datasetIndex:p,index:_})}return evaluateInteractionItems(n,t,e,f),s}function getNearestItems(n,e,t,r,a,o){return!o&&!n.isPointInArea(e)?[]:t==="r"&&!r?getNearestRadialItems(n,e,t,a):getNearestCartesianItems(n,e,t,r,a,o)}function getAxisItems(n,e,t,r,a){const o=[],s=t==="x"?"inXRange":"inYRange";let l=!1;return evaluateInteractionItems(n,t,e,(c,f,d)=>{c[s]&&c[s](e[t],a)&&(o.push({element:c,datasetIndex:f,index:d}),l=l||c.inRange(e.x,e.y,a))}),r&&!l?[]:o}var Interaction={modes:{index(n,e,t,r){const a=getRelativePosition(e,n),o=t.axis||"x",s=t.includeInvisible||!1,l=t.intersect?getIntersectItems(n,a,o,r,s):getNearestItems(n,a,o,!1,r,s),c=[];return l.length?(n.getSortedVisibleDatasetMetas().forEach(f=>{const d=l[0].index,p=f.data[d];p&&!p.skip&&c.push({element:p,datasetIndex:f.index,index:d})}),c):[]},dataset(n,e,t,r){const a=getRelativePosition(e,n),o=t.axis||"xy",s=t.includeInvisible||!1;let l=t.intersect?getIntersectItems(n,a,o,r,s):getNearestItems(n,a,o,!1,r,s);if(l.length>0){const c=l[0].datasetIndex,f=n.getDatasetMeta(c).data;l=[];for(let d=0;d<f.length;++d)l.push({element:f[d],datasetIndex:c,index:d})}return l},point(n,e,t,r){const a=getRelativePosition(e,n),o=t.axis||"xy",s=t.includeInvisible||!1;return getIntersectItems(n,a,o,r,s)},nearest(n,e,t,r){const a=getRelativePosition(e,n),o=t.axis||"xy",s=t.includeInvisible||!1;return getNearestItems(n,a,o,t.intersect,r,s)},x(n,e,t,r){const a=getRelativePosition(e,n);return getAxisItems(n,a,"x",t.intersect,r)},y(n,e,t,r){const a=getRelativePosition(e,n);return getAxisItems(n,a,"y",t.intersect,r)}}};const STATIC_POSITIONS=["left","top","right","bottom"];function filterByPosition(n,e){return n.filter(t=>t.pos===e)}function filterDynamicPositionByAxis(n,e){return n.filter(t=>STATIC_POSITIONS.indexOf(t.pos)===-1&&t.box.axis===e)}function sortByWeight(n,e){return n.sort((t,r)=>{const a=e?r:t,o=e?t:r;return a.weight===o.weight?a.index-o.index:a.weight-o.weight})}function wrapBoxes(n){const e=[];let t,r,a,o,s,l;for(t=0,r=(n||[]).length;t<r;++t)a=n[t],{position:o,options:{stack:s,stackWeight:l=1}}=a,e.push({index:t,box:a,pos:o,horizontal:a.isHorizontal(),weight:a.weight,stack:s&&o+s,stackWeight:l});return e}function buildStacks(n){const e={};for(const t of n){const{stack:r,pos:a,stackWeight:o}=t;if(!r||!STATIC_POSITIONS.includes(a))continue;const s=e[r]||(e[r]={count:0,placed:0,weight:0,size:0});s.count++,s.weight+=o}return e}function setLayoutDims(n,e){const t=buildStacks(n),{vBoxMaxWidth:r,hBoxMaxHeight:a}=e;let o,s,l;for(o=0,s=n.length;o<s;++o){l=n[o];const{fullSize:c}=l.box,f=t[l.stack],d=f&&l.stackWeight/f.weight;l.horizontal?(l.width=d?d*r:c&&e.availableWidth,l.height=a):(l.width=r,l.height=d?d*a:c&&e.availableHeight)}return t}function buildLayoutBoxes(n){const e=wrapBoxes(n),t=sortByWeight(e.filter(f=>f.box.fullSize),!0),r=sortByWeight(filterByPosition(e,"left"),!0),a=sortByWeight(filterByPosition(e,"right")),o=sortByWeight(filterByPosition(e,"top"),!0),s=sortByWeight(filterByPosition(e,"bottom")),l=filterDynamicPositionByAxis(e,"x"),c=filterDynamicPositionByAxis(e,"y");return{fullSize:t,leftAndTop:r.concat(o),rightAndBottom:a.concat(c).concat(s).concat(l),chartArea:filterByPosition(e,"chartArea"),vertical:r.concat(a).concat(c),horizontal:o.concat(s).concat(l)}}function getCombinedMax(n,e,t,r){return Math.max(n[t],e[t])+Math.max(n[r],e[r])}function updateMaxPadding(n,e){n.top=Math.max(n.top,e.top),n.left=Math.max(n.left,e.left),n.bottom=Math.max(n.bottom,e.bottom),n.right=Math.max(n.right,e.right)}function updateDims(n,e,t,r){const{pos:a,box:o}=t,s=n.maxPadding;if(!isObject(a)){t.size&&(n[a]-=t.size);const p=r[t.stack]||{size:0,count:1};p.size=Math.max(p.size,t.horizontal?o.height:o.width),t.size=p.size/p.count,n[a]+=t.size}o.getPadding&&updateMaxPadding(s,o.getPadding());const l=Math.max(0,e.outerWidth-getCombinedMax(s,n,"left","right")),c=Math.max(0,e.outerHeight-getCombinedMax(s,n,"top","bottom")),f=l!==n.w,d=c!==n.h;return n.w=l,n.h=c,t.horizontal?{same:f,other:d}:{same:d,other:f}}function handleMaxPadding(n){const e=n.maxPadding;function t(r){const a=Math.max(e[r]-n[r],0);return n[r]+=a,a}n.y+=t("top"),n.x+=t("left"),t("right"),t("bottom")}function getMargins(n,e){const t=e.maxPadding;function r(a){const o={left:0,top:0,right:0,bottom:0};return a.forEach(s=>{o[s]=Math.max(e[s],t[s])}),o}return r(n?["left","right"]:["top","bottom"])}function fitBoxes(n,e,t,r){const a=[];let o,s,l,c,f,d;for(o=0,s=n.length,f=0;o<s;++o){l=n[o],c=l.box,c.update(l.width||e.w,l.height||e.h,getMargins(l.horizontal,e));const{same:p,other:_}=updateDims(e,t,l,r);f|=p&&a.length,d=d||_,c.fullSize||a.push(l)}return f&&fitBoxes(a,e,t,r)||d}function setBoxDims(n,e,t,r,a){n.top=t,n.left=e,n.right=e+r,n.bottom=t+a,n.width=r,n.height=a}function placeBoxes(n,e,t,r){const a=t.padding;let{x:o,y:s}=e;for(const l of n){const c=l.box,f=r[l.stack]||{placed:0,weight:1},d=l.stackWeight/f.weight||1;if(l.horizontal){const p=e.w*d,_=f.size||c.height;defined(f.start)&&(s=f.start),c.fullSize?setBoxDims(c,a.left,s,t.outerWidth-a.right-a.left,_):setBoxDims(c,e.left+f.placed,s,p,_),f.start=s,f.placed+=p,s=c.bottom}else{const p=e.h*d,_=f.size||c.width;defined(f.start)&&(o=f.start),c.fullSize?setBoxDims(c,o,a.top,_,t.outerHeight-a.bottom-a.top):setBoxDims(c,o,e.top+f.placed,_,p),f.start=o,f.placed+=p,o=c.right}}e.x=o,e.y=s}var layouts={addBox(n,e){n.boxes||(n.boxes=[]),e.fullSize=e.fullSize||!1,e.position=e.position||"top",e.weight=e.weight||0,e._layers=e._layers||function(){return[{z:0,draw(t){e.draw(t)}}]},n.boxes.push(e)},removeBox(n,e){const t=n.boxes?n.boxes.indexOf(e):-1;t!==-1&&n.boxes.splice(t,1)},configure(n,e,t){e.fullSize=t.fullSize,e.position=t.position,e.weight=t.weight},update(n,e,t,r){if(!n)return;const a=toPadding(n.options.layout.padding),o=Math.max(e-a.width,0),s=Math.max(t-a.height,0),l=buildLayoutBoxes(n.boxes),c=l.vertical,f=l.horizontal;each(n.boxes,E=>{typeof E.beforeLayout=="function"&&E.beforeLayout()});const d=c.reduce((E,C)=>C.box.options&&C.box.options.display===!1?E:E+1,0)||1,p=Object.freeze({outerWidth:e,outerHeight:t,padding:a,availableWidth:o,availableHeight:s,vBoxMaxWidth:o/2/d,hBoxMaxHeight:s/2}),_=Object.assign({},a);updateMaxPadding(_,toPadding(r));const b=Object.assign({maxPadding:_,w:o,h:s,x:a.left,y:a.top},a),y=setLayoutDims(c.concat(f),p);fitBoxes(l.fullSize,b,p,y),fitBoxes(c,b,p,y),fitBoxes(f,b,p,y)&&fitBoxes(c,b,p,y),handleMaxPadding(b),placeBoxes(l.leftAndTop,b,p,y),b.x+=b.w,b.y+=b.h,placeBoxes(l.rightAndBottom,b,p,y),n.chartArea={left:b.left,top:b.top,right:b.left+b.w,bottom:b.top+b.h,height:b.h,width:b.w},each(l.chartArea,E=>{const C=E.box;Object.assign(C,n.chartArea),C.update(b.w,b.h,{left:0,top:0,right:0,bottom:0})})}};class BasePlatform{acquireContext(e,t){}releaseContext(e){return!1}addEventListener(e,t,r){}removeEventListener(e,t,r){}getDevicePixelRatio(){return 1}getMaximumSize(e,t,r,a){return t=Math.max(0,t||e.width),r=r||e.height,{width:t,height:Math.max(0,a?Math.floor(t/a):r)}}isAttached(e){return!0}updateConfig(e){}}class BasicPlatform extends BasePlatform{acquireContext(e){return e&&e.getContext&&e.getContext("2d")||null}updateConfig(e){e.options.animation=!1}}const EXPANDO_KEY="$chartjs",EVENT_TYPES={touchstart:"mousedown",touchmove:"mousemove",touchend:"mouseup",pointerenter:"mouseenter",pointerdown:"mousedown",pointermove:"mousemove",pointerup:"mouseup",pointerleave:"mouseout",pointerout:"mouseout"},isNullOrEmpty=n=>n===null||n==="";function initCanvas(n,e){const t=n.style,r=n.getAttribute("height"),a=n.getAttribute("width");if(n[EXPANDO_KEY]={initial:{height:r,width:a,style:{display:t.display,height:t.height,width:t.width}}},t.display=t.display||"block",t.boxSizing=t.boxSizing||"border-box",isNullOrEmpty(a)){const o=readUsedSize(n,"width");o!==void 0&&(n.width=o)}if(isNullOrEmpty(r))if(n.style.height==="")n.height=n.width/(e||2);else{const o=readUsedSize(n,"height");o!==void 0&&(n.height=o)}return n}const eventListenerOptions=supportsEventListenerOptions?{passive:!0}:!1;function addListener(n,e,t){n&&n.addEventListener(e,t,eventListenerOptions)}function removeListener(n,e,t){n&&n.canvas&&n.canvas.removeEventListener(e,t,eventListenerOptions)}function fromNativeEvent(n,e){const t=EVENT_TYPES[n.type]||n.type,{x:r,y:a}=getRelativePosition(n,e);return{type:t,chart:e,native:n,x:r!==void 0?r:null,y:a!==void 0?a:null}}function nodeListContains(n,e){for(const t of n)if(t===e||t.contains(e))return!0}function createAttachObserver(n,e,t){const r=n.canvas,a=new MutationObserver(o=>{let s=!1;for(const l of o)s=s||nodeListContains(l.addedNodes,r),s=s&&!nodeListContains(l.removedNodes,r);s&&t()});return a.observe(document,{childList:!0,subtree:!0}),a}function createDetachObserver(n,e,t){const r=n.canvas,a=new MutationObserver(o=>{let s=!1;for(const l of o)s=s||nodeListContains(l.removedNodes,r),s=s&&!nodeListContains(l.addedNodes,r);s&&t()});return a.observe(document,{childList:!0,subtree:!0}),a}const drpListeningCharts=new Map;let oldDevicePixelRatio=0;function onWindowResize(){const n=window.devicePixelRatio;n!==oldDevicePixelRatio&&(oldDevicePixelRatio=n,drpListeningCharts.forEach((e,t)=>{t.currentDevicePixelRatio!==n&&e()}))}function listenDevicePixelRatioChanges(n,e){drpListeningCharts.size||window.addEventListener("resize",onWindowResize),drpListeningCharts.set(n,e)}function unlistenDevicePixelRatioChanges(n){drpListeningCharts.delete(n),drpListeningCharts.size||window.removeEventListener("resize",onWindowResize)}function createResizeObserver(n,e,t){const r=n.canvas,a=r&&_getParentNode(r);if(!a)return;const o=throttled((l,c)=>{const f=a.clientWidth;t(l,c),f<a.clientWidth&&t()},window),s=new ResizeObserver(l=>{const c=l[0],f=c.contentRect.width,d=c.contentRect.height;f===0&&d===0||o(f,d)});return s.observe(a),listenDevicePixelRatioChanges(n,o),s}function releaseObserver(n,e,t){t&&t.disconnect(),e==="resize"&&unlistenDevicePixelRatioChanges(n)}function createProxyAndListen(n,e,t){const r=n.canvas,a=throttled(o=>{n.ctx!==null&&t(fromNativeEvent(o,n))},n);return addListener(r,e,a),a}class DomPlatform extends BasePlatform{acquireContext(e,t){const r=e&&e.getContext&&e.getContext("2d");return r&&r.canvas===e?(initCanvas(e,t),r):null}releaseContext(e){const t=e.canvas;if(!t[EXPANDO_KEY])return!1;const r=t[EXPANDO_KEY].initial;["height","width"].forEach(o=>{const s=r[o];isNullOrUndef(s)?t.removeAttribute(o):t.setAttribute(o,s)});const a=r.style||{};return Object.keys(a).forEach(o=>{t.style[o]=a[o]}),t.width=t.width,delete t[EXPANDO_KEY],!0}addEventListener(e,t,r){this.removeEventListener(e,t);const a=e.$proxies||(e.$proxies={}),s={attach:createAttachObserver,detach:createDetachObserver,resize:createResizeObserver}[t]||createProxyAndListen;a[t]=s(e,t,r)}removeEventListener(e,t){const r=e.$proxies||(e.$proxies={}),a=r[t];if(!a)return;({attach:releaseObserver,detach:releaseObserver,resize:releaseObserver}[t]||removeListener)(e,t,a),r[t]=void 0}getDevicePixelRatio(){return window.devicePixelRatio}getMaximumSize(e,t,r,a){return getMaximumSize(e,t,r,a)}isAttached(e){const t=e&&_getParentNode(e);return!!(t&&t.isConnected)}}function _detectPlatform(n){return!_isDomSupported()||typeof OffscreenCanvas<"u"&&n instanceof OffscreenCanvas?BasicPlatform:DomPlatform}let Element$1=class{static defaults={};static defaultRoutes=void 0;x;y;active=!1;options;$animations;tooltipPosition(e){const{x:t,y:r}=this.getProps(["x","y"],e);return{x:t,y:r}}hasValue(){return isNumber(this.x)&&isNumber(this.y)}getProps(e,t){const r=this.$animations;if(!t||!r)return this;const a={};return e.forEach(o=>{a[o]=r[o]&&r[o].active()?r[o]._to:this[o]}),a}};function autoSkip(n,e){const t=n.options.ticks,r=determineMaxTicks(n),a=Math.min(t.maxTicksLimit||r,r),o=t.major.enabled?getMajorIndices(e):[],s=o.length,l=o[0],c=o[s-1],f=[];if(s>a)return skipMajors(e,f,o,s/a),f;const d=calculateSpacing(o,e,a);if(s>0){let p,_;const b=s>1?Math.round((c-l)/(s-1)):null;for(skip(e,f,d,isNullOrUndef(b)?0:l-b,l),p=0,_=s-1;p<_;p++)skip(e,f,d,o[p],o[p+1]);return skip(e,f,d,c,isNullOrUndef(b)?e.length:c+b),f}return skip(e,f,d),f}function determineMaxTicks(n){const e=n.options.offset,t=n._tickSize(),r=n._length/t+(e?0:1),a=n._maxLength/t;return Math.floor(Math.min(r,a))}function calculateSpacing(n,e,t){const r=getEvenSpacing(n),a=e.length/t;if(!r)return Math.max(a,1);const o=_factorize(r);for(let s=0,l=o.length-1;s<l;s++){const c=o[s];if(c>a)return c}return Math.max(a,1)}function getMajorIndices(n){const e=[];let t,r;for(t=0,r=n.length;t<r;t++)n[t].major&&e.push(t);return e}function skipMajors(n,e,t,r){let a=0,o=t[0],s;for(r=Math.ceil(r),s=0;s<n.length;s++)s===o&&(e.push(n[s]),a++,o=t[a*r])}function skip(n,e,t,r,a){const o=valueOrDefault(r,0),s=Math.min(valueOrDefault(a,n.length),n.length);let l=0,c,f,d;for(t=Math.ceil(t),a&&(c=a-r,t=c/Math.floor(c/t)),d=o;d<0;)l++,d=Math.round(o+l*t);for(f=Math.max(o,0);f<s;f++)f===d&&(e.push(n[f]),l++,d=Math.round(o+l*t))}function getEvenSpacing(n){const e=n.length;let t,r;if(e<2)return!1;for(r=n[0],t=1;t<e;++t)if(n[t]-n[t-1]!==r)return!1;return r}const reverseAlign=n=>n==="left"?"right":n==="right"?"left":n,offsetFromEdge=(n,e,t)=>e==="top"||e==="left"?n[e]+t:n[e]-t,getTicksLimit=(n,e)=>Math.min(e||n,n);function sample(n,e){const t=[],r=n.length/e,a=n.length;let o=0;for(;o<a;o+=r)t.push(n[Math.floor(o)]);return t}function getPixelForGridLine(n,e,t){const r=n.ticks.length,a=Math.min(e,r-1),o=n._startPixel,s=n._endPixel,l=1e-6;let c=n.getPixelForTick(a),f;if(!(t&&(r===1?f=Math.max(c-o,s-c):e===0?f=(n.getPixelForTick(1)-c)/2:f=(c-n.getPixelForTick(a-1))/2,c+=a<e?f:-f,c<o-l||c>s+l)))return c}function garbageCollect(n,e){each(n,t=>{const r=t.gc,a=r.length/2;let o;if(a>e){for(o=0;o<a;++o)delete t.data[r[o]];r.splice(0,a)}})}function getTickMarkLength(n){return n.drawTicks?n.tickLength:0}function getTitleHeight(n,e){if(!n.display)return 0;const t=toFont(n.font,e),r=toPadding(n.padding);return(isArray(n.text)?n.text.length:1)*t.lineHeight+r.height}function createScaleContext(n,e){return createContext(n,{scale:e,type:"scale"})}function createTickContext(n,e,t){return createContext(n,{tick:t,index:e,type:"tick"})}function titleAlign(n,e,t){let r=_toLeftRightCenter(n);return(t&&e!=="right"||!t&&e==="right")&&(r=reverseAlign(r)),r}function titleArgs(n,e,t,r){const{top:a,left:o,bottom:s,right:l,chart:c}=n,{chartArea:f,scales:d}=c;let p=0,_,b,y;const E=s-a,C=l-o;if(n.isHorizontal()){if(b=_alignStartEnd(r,o,l),isObject(t)){const D=Object.keys(t)[0],M=t[D];y=d[D].getPixelForValue(M)+E-e}else t==="center"?y=(f.bottom+f.top)/2+E-e:y=offsetFromEdge(n,t,e);_=l-o}else{if(isObject(t)){const D=Object.keys(t)[0],M=t[D];b=d[D].getPixelForValue(M)-C+e}else t==="center"?b=(f.left+f.right)/2-C+e:b=offsetFromEdge(n,t,e);y=_alignStartEnd(r,s,a),p=t==="left"?-HALF_PI:HALF_PI}return{titleX:b,titleY:y,maxWidth:_,rotation:p}}class Scale extends Element$1{constructor(e){super(),this.id=e.id,this.type=e.type,this.options=void 0,this.ctx=e.ctx,this.chart=e.chart,this.top=void 0,this.bottom=void 0,this.left=void 0,this.right=void 0,this.width=void 0,this.height=void 0,this._margins={left:0,right:0,top:0,bottom:0},this.maxWidth=void 0,this.maxHeight=void 0,this.paddingTop=void 0,this.paddingBottom=void 0,this.paddingLeft=void 0,this.paddingRight=void 0,this.axis=void 0,this.labelRotation=void 0,this.min=void 0,this.max=void 0,this._range=void 0,this.ticks=[],this._gridLineItems=null,this._labelItems=null,this._labelSizes=null,this._length=0,this._maxLength=0,this._longestTextCache={},this._startPixel=void 0,this._endPixel=void 0,this._reversePixels=!1,this._userMax=void 0,this._userMin=void 0,this._suggestedMax=void 0,this._suggestedMin=void 0,this._ticksLength=0,this._borderValue=0,this._cache={},this._dataLimitsCached=!1,this.$context=void 0}init(e){this.options=e.setContext(this.getContext()),this.axis=e.axis,this._userMin=this.parse(e.min),this._userMax=this.parse(e.max),this._suggestedMin=this.parse(e.suggestedMin),this._suggestedMax=this.parse(e.suggestedMax)}parse(e,t){return e}getUserBounds(){let{_userMin:e,_userMax:t,_suggestedMin:r,_suggestedMax:a}=this;return e=finiteOrDefault(e,Number.POSITIVE_INFINITY),t=finiteOrDefault(t,Number.NEGATIVE_INFINITY),r=finiteOrDefault(r,Number.POSITIVE_INFINITY),a=finiteOrDefault(a,Number.NEGATIVE_INFINITY),{min:finiteOrDefault(e,r),max:finiteOrDefault(t,a),minDefined:isNumberFinite(e),maxDefined:isNumberFinite(t)}}getMinMax(e){let{min:t,max:r,minDefined:a,maxDefined:o}=this.getUserBounds(),s;if(a&&o)return{min:t,max:r};const l=this.getMatchingVisibleMetas();for(let c=0,f=l.length;c<f;++c)s=l[c].controller.getMinMax(this,e),a||(t=Math.min(t,s.min)),o||(r=Math.max(r,s.max));return t=o&&t>r?r:t,r=a&&t>r?t:r,{min:finiteOrDefault(t,finiteOrDefault(r,t)),max:finiteOrDefault(r,finiteOrDefault(t,r))}}getPadding(){return{left:this.paddingLeft||0,top:this.paddingTop||0,right:this.paddingRight||0,bottom:this.paddingBottom||0}}getTicks(){return this.ticks}getLabels(){const e=this.chart.data;return this.options.labels||(this.isHorizontal()?e.xLabels:e.yLabels)||e.labels||[]}getLabelItems(e=this.chart.chartArea){return this._labelItems||(this._labelItems=this._computeLabelItems(e))}beforeLayout(){this._cache={},this._dataLimitsCached=!1}beforeUpdate(){callback(this.options.beforeUpdate,[this])}update(e,t,r){const{beginAtZero:a,grace:o,ticks:s}=this.options,l=s.sampleSize;this.beforeUpdate(),this.maxWidth=e,this.maxHeight=t,this._margins=r=Object.assign({left:0,right:0,top:0,bottom:0},r),this.ticks=null,this._labelSizes=null,this._gridLineItems=null,this._labelItems=null,this.beforeSetDimensions(),this.setDimensions(),this.afterSetDimensions(),this._maxLength=this.isHorizontal()?this.width+r.left+r.right:this.height+r.top+r.bottom,this._dataLimitsCached||(this.beforeDataLimits(),this.determineDataLimits(),this.afterDataLimits(),this._range=_addGrace(this,o,a),this._dataLimitsCached=!0),this.beforeBuildTicks(),this.ticks=this.buildTicks()||[],this.afterBuildTicks();const c=l<this.ticks.length;this._convertTicksToLabels(c?sample(this.ticks,l):this.ticks),this.configure(),this.beforeCalculateLabelRotation(),this.calculateLabelRotation(),this.afterCalculateLabelRotation(),s.display&&(s.autoSkip||s.source==="auto")&&(this.ticks=autoSkip(this,this.ticks),this._labelSizes=null,this.afterAutoSkip()),c&&this._convertTicksToLabels(this.ticks),this.beforeFit(),this.fit(),this.afterFit(),this.afterUpdate()}configure(){let e=this.options.reverse,t,r;this.isHorizontal()?(t=this.left,r=this.right):(t=this.top,r=this.bottom,e=!e),this._startPixel=t,this._endPixel=r,this._reversePixels=e,this._length=r-t,this._alignToPixels=this.options.alignToPixels}afterUpdate(){callback(this.options.afterUpdate,[this])}beforeSetDimensions(){callback(this.options.beforeSetDimensions,[this])}setDimensions(){this.isHorizontal()?(this.width=this.maxWidth,this.left=0,this.right=this.width):(this.height=this.maxHeight,this.top=0,this.bottom=this.height),this.paddingLeft=0,this.paddingTop=0,this.paddingRight=0,this.paddingBottom=0}afterSetDimensions(){callback(this.options.afterSetDimensions,[this])}_callHooks(e){this.chart.notifyPlugins(e,this.getContext()),callback(this.options[e],[this])}beforeDataLimits(){this._callHooks("beforeDataLimits")}determineDataLimits(){}afterDataLimits(){this._callHooks("afterDataLimits")}beforeBuildTicks(){this._callHooks("beforeBuildTicks")}buildTicks(){return[]}afterBuildTicks(){this._callHooks("afterBuildTicks")}beforeTickToLabelConversion(){callback(this.options.beforeTickToLabelConversion,[this])}generateTickLabels(e){const t=this.options.ticks;let r,a,o;for(r=0,a=e.length;r<a;r++)o=e[r],o.label=callback(t.callback,[o.value,r,e],this)}afterTickToLabelConversion(){callback(this.options.afterTickToLabelConversion,[this])}beforeCalculateLabelRotation(){callback(this.options.beforeCalculateLabelRotation,[this])}calculateLabelRotation(){const e=this.options,t=e.ticks,r=getTicksLimit(this.ticks.length,e.ticks.maxTicksLimit),a=t.minRotation||0,o=t.maxRotation;let s=a,l,c,f;if(!this._isVisible()||!t.display||a>=o||r<=1||!this.isHorizontal()){this.labelRotation=a;return}const d=this._getLabelSizes(),p=d.widest.width,_=d.highest.height,b=_limitValue(this.chart.width-p,0,this.maxWidth);l=e.offset?this.maxWidth/r:b/(r-1),p+6>l&&(l=b/(r-(e.offset?.5:1)),c=this.maxHeight-getTickMarkLength(e.grid)-t.padding-getTitleHeight(e.title,this.chart.options.font),f=Math.sqrt(p*p+_*_),s=toDegrees(Math.min(Math.asin(_limitValue((d.highest.height+6)/l,-1,1)),Math.asin(_limitValue(c/f,-1,1))-Math.asin(_limitValue(_/f,-1,1)))),s=Math.max(a,Math.min(o,s))),this.labelRotation=s}afterCalculateLabelRotation(){callback(this.options.afterCalculateLabelRotation,[this])}afterAutoSkip(){}beforeFit(){callback(this.options.beforeFit,[this])}fit(){const e={width:0,height:0},{chart:t,options:{ticks:r,title:a,grid:o}}=this,s=this._isVisible(),l=this.isHorizontal();if(s){const c=getTitleHeight(a,t.options.font);if(l?(e.width=this.maxWidth,e.height=getTickMarkLength(o)+c):(e.height=this.maxHeight,e.width=getTickMarkLength(o)+c),r.display&&this.ticks.length){const{first:f,last:d,widest:p,highest:_}=this._getLabelSizes(),b=r.padding*2,y=toRadians(this.labelRotation),E=Math.cos(y),C=Math.sin(y);if(l){const D=r.mirror?0:C*p.width+E*_.height;e.height=Math.min(this.maxHeight,e.height+D+b)}else{const D=r.mirror?0:E*p.width+C*_.height;e.width=Math.min(this.maxWidth,e.width+D+b)}this._calculatePadding(f,d,C,E)}}this._handleMargins(),l?(this.width=this._length=t.width-this._margins.left-this._margins.right,this.height=e.height):(this.width=e.width,this.height=this._length=t.height-this._margins.top-this._margins.bottom)}_calculatePadding(e,t,r,a){const{ticks:{align:o,padding:s},position:l}=this.options,c=this.labelRotation!==0,f=l!=="top"&&this.axis==="x";if(this.isHorizontal()){const d=this.getPixelForTick(0)-this.left,p=this.right-this.getPixelForTick(this.ticks.length-1);let _=0,b=0;c?f?(_=a*e.width,b=r*t.height):(_=r*e.height,b=a*t.width):o==="start"?b=t.width:o==="end"?_=e.width:o!=="inner"&&(_=e.width/2,b=t.width/2),this.paddingLeft=Math.max((_-d+s)*this.width/(this.width-d),0),this.paddingRight=Math.max((b-p+s)*this.width/(this.width-p),0)}else{let d=t.height/2,p=e.height/2;o==="start"?(d=0,p=e.height):o==="end"&&(d=t.height,p=0),this.paddingTop=d+s,this.paddingBottom=p+s}}_handleMargins(){this._margins&&(this._margins.left=Math.max(this.paddingLeft,this._margins.left),this._margins.top=Math.max(this.paddingTop,this._margins.top),this._margins.right=Math.max(this.paddingRight,this._margins.right),this._margins.bottom=Math.max(this.paddingBottom,this._margins.bottom))}afterFit(){callback(this.options.afterFit,[this])}isHorizontal(){const{axis:e,position:t}=this.options;return t==="top"||t==="bottom"||e==="x"}isFullSize(){return this.options.fullSize}_convertTicksToLabels(e){this.beforeTickToLabelConversion(),this.generateTickLabels(e);let t,r;for(t=0,r=e.length;t<r;t++)isNullOrUndef(e[t].label)&&(e.splice(t,1),r--,t--);this.afterTickToLabelConversion()}_getLabelSizes(){let e=this._labelSizes;if(!e){const t=this.options.ticks.sampleSize;let r=this.ticks;t<r.length&&(r=sample(r,t)),this._labelSizes=e=this._computeLabelSizes(r,r.length,this.options.ticks.maxTicksLimit)}return e}_computeLabelSizes(e,t,r){const{ctx:a,_longestTextCache:o}=this,s=[],l=[],c=Math.floor(t/getTicksLimit(t,r));let f=0,d=0,p,_,b,y,E,C,D,M,F,P,H;for(p=0;p<t;p+=c){if(y=e[p].label,E=this._resolveTickFontOptions(p),a.font=C=E.string,D=o[C]=o[C]||{data:{},gc:[]},M=E.lineHeight,F=P=0,!isNullOrUndef(y)&&!isArray(y))F=_measureText(a,D.data,D.gc,F,y),P=M;else if(isArray(y))for(_=0,b=y.length;_<b;++_)H=y[_],!isNullOrUndef(H)&&!isArray(H)&&(F=_measureText(a,D.data,D.gc,F,H),P+=M);s.push(F),l.push(P),f=Math.max(F,f),d=Math.max(P,d)}garbageCollect(o,t);const B=s.indexOf(f),g=l.indexOf(d),q=G=>({width:s[G]||0,height:l[G]||0});return{first:q(0),last:q(t-1),widest:q(B),highest:q(g),widths:s,heights:l}}getLabelForValue(e){return e}getPixelForValue(e,t){return NaN}getValueForPixel(e){}getPixelForTick(e){const t=this.ticks;return e<0||e>t.length-1?null:this.getPixelForValue(t[e].value)}getPixelForDecimal(e){this._reversePixels&&(e=1-e);const t=this._startPixel+e*this._length;return _int16Range(this._alignToPixels?_alignPixel(this.chart,t,0):t)}getDecimalForPixel(e){const t=(e-this._startPixel)/this._length;return this._reversePixels?1-t:t}getBasePixel(){return this.getPixelForValue(this.getBaseValue())}getBaseValue(){const{min:e,max:t}=this;return e<0&&t<0?t:e>0&&t>0?e:0}getContext(e){const t=this.ticks||[];if(e>=0&&e<t.length){const r=t[e];return r.$context||(r.$context=createTickContext(this.getContext(),e,r))}return this.$context||(this.$context=createScaleContext(this.chart.getContext(),this))}_tickSize(){const e=this.options.ticks,t=toRadians(this.labelRotation),r=Math.abs(Math.cos(t)),a=Math.abs(Math.sin(t)),o=this._getLabelSizes(),s=e.autoSkipPadding||0,l=o?o.widest.width+s:0,c=o?o.highest.height+s:0;return this.isHorizontal()?c*r>l*a?l/r:c/a:c*a<l*r?c/r:l/a}_isVisible(){const e=this.options.display;return e!=="auto"?!!e:this.getMatchingVisibleMetas().length>0}_computeGridLineItems(e){const t=this.axis,r=this.chart,a=this.options,{grid:o,position:s,border:l}=a,c=o.offset,f=this.isHorizontal(),p=this.ticks.length+(c?1:0),_=getTickMarkLength(o),b=[],y=l.setContext(this.getContext()),E=y.display?y.width:0,C=E/2,D=function(de){return _alignPixel(r,de,E)};let M,F,P,H,B,g,q,G,Z,te,ne,Q;if(s==="top")M=D(this.bottom),g=this.bottom-_,G=M-C,te=D(e.top)+C,Q=e.bottom;else if(s==="bottom")M=D(this.top),te=e.top,Q=D(e.bottom)-C,g=M+C,G=this.top+_;else if(s==="left")M=D(this.right),B=this.right-_,q=M-C,Z=D(e.left)+C,ne=e.right;else if(s==="right")M=D(this.left),Z=e.left,ne=D(e.right)-C,B=M+C,q=this.left+_;else if(t==="x"){if(s==="center")M=D((e.top+e.bottom)/2+.5);else if(isObject(s)){const de=Object.keys(s)[0],le=s[de];M=D(this.chart.scales[de].getPixelForValue(le))}te=e.top,Q=e.bottom,g=M+C,G=g+_}else if(t==="y"){if(s==="center")M=D((e.left+e.right)/2);else if(isObject(s)){const de=Object.keys(s)[0],le=s[de];M=D(this.chart.scales[de].getPixelForValue(le))}B=M-C,q=B-_,Z=e.left,ne=e.right}const Ee=valueOrDefault(a.ticks.maxTicksLimit,p),re=Math.max(1,Math.ceil(p/Ee));for(F=0;F<p;F+=re){const de=this.getContext(F),le=o.setContext(de),$e=l.setContext(de),xe=le.lineWidth,Ve=le.color,Re=$e.dash||[],Te=$e.dashOffset,je=le.tickWidth,Fe=le.tickColor,He=le.tickBorderDash||[],ge=le.tickBorderDashOffset;P=getPixelForGridLine(this,F,c),P!==void 0&&(H=_alignPixel(r,P,xe),f?B=q=Z=ne=H:g=G=te=Q=H,b.push({tx1:B,ty1:g,tx2:q,ty2:G,x1:Z,y1:te,x2:ne,y2:Q,width:xe,color:Ve,borderDash:Re,borderDashOffset:Te,tickWidth:je,tickColor:Fe,tickBorderDash:He,tickBorderDashOffset:ge}))}return this._ticksLength=p,this._borderValue=M,b}_computeLabelItems(e){const t=this.axis,r=this.options,{position:a,ticks:o}=r,s=this.isHorizontal(),l=this.ticks,{align:c,crossAlign:f,padding:d,mirror:p}=o,_=getTickMarkLength(r.grid),b=_+d,y=p?-d:b,E=-toRadians(this.labelRotation),C=[];let D,M,F,P,H,B,g,q,G,Z,te,ne,Q="middle";if(a==="top")B=this.bottom-y,g=this._getXAxisLabelAlignment();else if(a==="bottom")B=this.top+y,g=this._getXAxisLabelAlignment();else if(a==="left"){const re=this._getYAxisLabelAlignment(_);g=re.textAlign,H=re.x}else if(a==="right"){const re=this._getYAxisLabelAlignment(_);g=re.textAlign,H=re.x}else if(t==="x"){if(a==="center")B=(e.top+e.bottom)/2+b;else if(isObject(a)){const re=Object.keys(a)[0],de=a[re];B=this.chart.scales[re].getPixelForValue(de)+b}g=this._getXAxisLabelAlignment()}else if(t==="y"){if(a==="center")H=(e.left+e.right)/2-b;else if(isObject(a)){const re=Object.keys(a)[0],de=a[re];H=this.chart.scales[re].getPixelForValue(de)}g=this._getYAxisLabelAlignment(_).textAlign}t==="y"&&(c==="start"?Q="top":c==="end"&&(Q="bottom"));const Ee=this._getLabelSizes();for(D=0,M=l.length;D<M;++D){F=l[D],P=F.label;const re=o.setContext(this.getContext(D));q=this.getPixelForTick(D)+o.labelOffset,G=this._resolveTickFontOptions(D),Z=G.lineHeight,te=isArray(P)?P.length:1;const de=te/2,le=re.color,$e=re.textStrokeColor,xe=re.textStrokeWidth;let Ve=g;s?(H=q,g==="inner"&&(D===M-1?Ve=this.options.reverse?"left":"right":D===0?Ve=this.options.reverse?"right":"left":Ve="center"),a==="top"?f==="near"||E!==0?ne=-te*Z+Z/2:f==="center"?ne=-Ee.highest.height/2-de*Z+Z:ne=-Ee.highest.height+Z/2:f==="near"||E!==0?ne=Z/2:f==="center"?ne=Ee.highest.height/2-de*Z:ne=Ee.highest.height-te*Z,p&&(ne*=-1),E!==0&&!re.showLabelBackdrop&&(H+=Z/2*Math.sin(E))):(B=q,ne=(1-te)*Z/2);let Re;if(re.showLabelBackdrop){const Te=toPadding(re.backdropPadding),je=Ee.heights[D],Fe=Ee.widths[D];let He=ne-Te.top,ge=0-Te.left;switch(Q){case"middle":He-=je/2;break;case"bottom":He-=je;break}switch(g){case"center":ge-=Fe/2;break;case"right":ge-=Fe;break;case"inner":D===M-1?ge-=Fe:D>0&&(ge-=Fe/2);break}Re={left:ge,top:He,width:Fe+Te.width,height:je+Te.height,color:re.backdropColor}}C.push({label:P,font:G,textOffset:ne,options:{rotation:E,color:le,strokeColor:$e,strokeWidth:xe,textAlign:Ve,textBaseline:Q,translation:[H,B],backdrop:Re}})}return C}_getXAxisLabelAlignment(){const{position:e,ticks:t}=this.options;if(-toRadians(this.labelRotation))return e==="top"?"left":"right";let a="center";return t.align==="start"?a="left":t.align==="end"?a="right":t.align==="inner"&&(a="inner"),a}_getYAxisLabelAlignment(e){const{position:t,ticks:{crossAlign:r,mirror:a,padding:o}}=this.options,s=this._getLabelSizes(),l=e+o,c=s.widest.width;let f,d;return t==="left"?a?(d=this.right+o,r==="near"?f="left":r==="center"?(f="center",d+=c/2):(f="right",d+=c)):(d=this.right-l,r==="near"?f="right":r==="center"?(f="center",d-=c/2):(f="left",d=this.left)):t==="right"?a?(d=this.left+o,r==="near"?f="right":r==="center"?(f="center",d-=c/2):(f="left",d-=c)):(d=this.left+l,r==="near"?f="left":r==="center"?(f="center",d+=c/2):(f="right",d=this.right)):f="right",{textAlign:f,x:d}}_computeLabelArea(){if(this.options.ticks.mirror)return;const e=this.chart,t=this.options.position;if(t==="left"||t==="right")return{top:0,left:this.left,bottom:e.height,right:this.right};if(t==="top"||t==="bottom")return{top:this.top,left:0,bottom:this.bottom,right:e.width}}drawBackground(){const{ctx:e,options:{backgroundColor:t},left:r,top:a,width:o,height:s}=this;t&&(e.save(),e.fillStyle=t,e.fillRect(r,a,o,s),e.restore())}getLineWidthForValue(e){const t=this.options.grid;if(!this._isVisible()||!t.display)return 0;const a=this.ticks.findIndex(o=>o.value===e);return a>=0?t.setContext(this.getContext(a)).lineWidth:0}drawGrid(e){const t=this.options.grid,r=this.ctx,a=this._gridLineItems||(this._gridLineItems=this._computeGridLineItems(e));let o,s;const l=(c,f,d)=>{!d.width||!d.color||(r.save(),r.lineWidth=d.width,r.strokeStyle=d.color,r.setLineDash(d.borderDash||[]),r.lineDashOffset=d.borderDashOffset,r.beginPath(),r.moveTo(c.x,c.y),r.lineTo(f.x,f.y),r.stroke(),r.restore())};if(t.display)for(o=0,s=a.length;o<s;++o){const c=a[o];t.drawOnChartArea&&l({x:c.x1,y:c.y1},{x:c.x2,y:c.y2},c),t.drawTicks&&l({x:c.tx1,y:c.ty1},{x:c.tx2,y:c.ty2},{color:c.tickColor,width:c.tickWidth,borderDash:c.tickBorderDash,borderDashOffset:c.tickBorderDashOffset})}}drawBorder(){const{chart:e,ctx:t,options:{border:r,grid:a}}=this,o=r.setContext(this.getContext()),s=r.display?o.width:0;if(!s)return;const l=a.setContext(this.getContext(0)).lineWidth,c=this._borderValue;let f,d,p,_;this.isHorizontal()?(f=_alignPixel(e,this.left,s)-s/2,d=_alignPixel(e,this.right,l)+l/2,p=_=c):(p=_alignPixel(e,this.top,s)-s/2,_=_alignPixel(e,this.bottom,l)+l/2,f=d=c),t.save(),t.lineWidth=o.width,t.strokeStyle=o.color,t.beginPath(),t.moveTo(f,p),t.lineTo(d,_),t.stroke(),t.restore()}drawLabels(e){if(!this.options.ticks.display)return;const r=this.ctx,a=this._computeLabelArea();a&&clipArea(r,a);const o=this.getLabelItems(e);for(const s of o){const l=s.options,c=s.font,f=s.label,d=s.textOffset;renderText(r,f,0,d,c,l)}a&&unclipArea(r)}drawTitle(){const{ctx:e,options:{position:t,title:r,reverse:a}}=this;if(!r.display)return;const o=toFont(r.font),s=toPadding(r.padding),l=r.align;let c=o.lineHeight/2;t==="bottom"||t==="center"||isObject(t)?(c+=s.bottom,isArray(r.text)&&(c+=o.lineHeight*(r.text.length-1))):c+=s.top;const{titleX:f,titleY:d,maxWidth:p,rotation:_}=titleArgs(this,c,t,l);renderText(e,r.text,0,0,o,{color:r.color,maxWidth:p,rotation:_,textAlign:titleAlign(l,t,a),textBaseline:"middle",translation:[f,d]})}draw(e){this._isVisible()&&(this.drawBackground(),this.drawGrid(e),this.drawBorder(),this.drawTitle(),this.drawLabels(e))}_layers(){const e=this.options,t=e.ticks&&e.ticks.z||0,r=valueOrDefault(e.grid&&e.grid.z,-1),a=valueOrDefault(e.border&&e.border.z,0);return!this._isVisible()||this.draw!==Scale.prototype.draw?[{z:t,draw:o=>{this.draw(o)}}]:[{z:r,draw:o=>{this.drawBackground(),this.drawGrid(o),this.drawTitle()}},{z:a,draw:()=>{this.drawBorder()}},{z:t,draw:o=>{this.drawLabels(o)}}]}getMatchingVisibleMetas(e){const t=this.chart.getSortedVisibleDatasetMetas(),r=this.axis+"AxisID",a=[];let o,s;for(o=0,s=t.length;o<s;++o){const l=t[o];l[r]===this.id&&(!e||l.type===e)&&a.push(l)}return a}_resolveTickFontOptions(e){const t=this.options.ticks.setContext(this.getContext(e));return toFont(t.font)}_maxDigits(){const e=this._resolveTickFontOptions(0).lineHeight;return(this.isHorizontal()?this.width:this.height)/e}}class TypedRegistry{constructor(e,t,r){this.type=e,this.scope=t,this.override=r,this.items=Object.create(null)}isForType(e){return Object.prototype.isPrototypeOf.call(this.type.prototype,e.prototype)}register(e){const t=Object.getPrototypeOf(e);let r;isIChartComponent(t)&&(r=this.register(t));const a=this.items,o=e.id,s=this.scope+"."+o;if(!o)throw new Error("class does not have id: "+e);return o in a||(a[o]=e,registerDefaults(e,s,r),this.override&&defaults.override(e.id,e.overrides)),s}get(e){return this.items[e]}unregister(e){const t=this.items,r=e.id,a=this.scope;r in t&&delete t[r],a&&r in defaults[a]&&(delete defaults[a][r],this.override&&delete overrides[r])}}function registerDefaults(n,e,t){const r=merge(Object.create(null),[t?defaults.get(t):{},defaults.get(e),n.defaults]);defaults.set(e,r),n.defaultRoutes&&routeDefaults(e,n.defaultRoutes),n.descriptors&&defaults.describe(e,n.descriptors)}function routeDefaults(n,e){Object.keys(e).forEach(t=>{const r=t.split("."),a=r.pop(),o=[n].concat(r).join("."),s=e[t].split("."),l=s.pop(),c=s.join(".");defaults.route(o,a,c,l)})}function isIChartComponent(n){return"id"in n&&"defaults"in n}class Registry{constructor(){this.controllers=new TypedRegistry(DatasetController,"datasets",!0),this.elements=new TypedRegistry(Element$1,"elements"),this.plugins=new TypedRegistry(Object,"plugins"),this.scales=new TypedRegistry(Scale,"scales"),this._typedRegistries=[this.controllers,this.scales,this.elements]}add(...e){this._each("register",e)}remove(...e){this._each("unregister",e)}addControllers(...e){this._each("register",e,this.controllers)}addElements(...e){this._each("register",e,this.elements)}addPlugins(...e){this._each("register",e,this.plugins)}addScales(...e){this._each("register",e,this.scales)}getController(e){return this._get(e,this.controllers,"controller")}getElement(e){return this._get(e,this.elements,"element")}getPlugin(e){return this._get(e,this.plugins,"plugin")}getScale(e){return this._get(e,this.scales,"scale")}removeControllers(...e){this._each("unregister",e,this.controllers)}removeElements(...e){this._each("unregister",e,this.elements)}removePlugins(...e){this._each("unregister",e,this.plugins)}removeScales(...e){this._each("unregister",e,this.scales)}_each(e,t,r){[...t].forEach(a=>{const o=r||this._getRegistryForType(a);r||o.isForType(a)||o===this.plugins&&a.id?this._exec(e,o,a):each(a,s=>{const l=r||this._getRegistryForType(s);this._exec(e,l,s)})})}_exec(e,t,r){const a=_capitalize(e);callback(r["before"+a],[],r),t[e](r),callback(r["after"+a],[],r)}_getRegistryForType(e){for(let t=0;t<this._typedRegistries.length;t++){const r=this._typedRegistries[t];if(r.isForType(e))return r}return this.plugins}_get(e,t,r){const a=t.get(e);if(a===void 0)throw new Error('"'+e+'" is not a registered '+r+".");return a}}var registry=new Registry;class PluginService{constructor(){this._init=void 0}notify(e,t,r,a){if(t==="beforeInit"&&(this._init=this._createDescriptors(e,!0),this._notify(this._init,e,"install")),this._init===void 0)return;const o=a?this._descriptors(e).filter(a):this._descriptors(e),s=this._notify(o,e,t,r);return t==="afterDestroy"&&(this._notify(o,e,"stop"),this._notify(this._init,e,"uninstall"),this._init=void 0),s}_notify(e,t,r,a){a=a||{};for(const o of e){const s=o.plugin,l=s[r],c=[t,a,o.options];if(callback(l,c,s)===!1&&a.cancelable)return!1}return!0}invalidate(){isNullOrUndef(this._cache)||(this._oldCache=this._cache,this._cache=void 0)}_descriptors(e){if(this._cache)return this._cache;const t=this._cache=this._createDescriptors(e);return this._notifyStateChanges(e),t}_createDescriptors(e,t){const r=e&&e.config,a=valueOrDefault(r.options&&r.options.plugins,{}),o=allPlugins(r);return a===!1&&!t?[]:createDescriptors(e,o,a,t)}_notifyStateChanges(e){const t=this._oldCache||[],r=this._cache,a=(o,s)=>o.filter(l=>!s.some(c=>l.plugin.id===c.plugin.id));this._notify(a(t,r),e,"stop"),this._notify(a(r,t),e,"start")}}function allPlugins(n){const e={},t=[],r=Object.keys(registry.plugins.items);for(let o=0;o<r.length;o++)t.push(registry.getPlugin(r[o]));const a=n.plugins||[];for(let o=0;o<a.length;o++){const s=a[o];t.indexOf(s)===-1&&(t.push(s),e[s.id]=!0)}return{plugins:t,localIds:e}}function getOpts(n,e){return!e&&n===!1?null:n===!0?{}:n}function createDescriptors(n,{plugins:e,localIds:t},r,a){const o=[],s=n.getContext();for(const l of e){const c=l.id,f=getOpts(r[c],a);f!==null&&o.push({plugin:l,options:pluginOpts(n.config,{plugin:l,local:t[c]},f,s)})}return o}function pluginOpts(n,{plugin:e,local:t},r,a){const o=n.pluginScopeKeys(e),s=n.getOptionScopes(r,o);return t&&e.defaults&&s.push(e.defaults),n.createResolver(s,a,[""],{scriptable:!1,indexable:!1,allKeys:!0})}function getIndexAxis(n,e){const t=defaults.datasets[n]||{};return((e.datasets||{})[n]||{}).indexAxis||e.indexAxis||t.indexAxis||"x"}function getAxisFromDefaultScaleID(n,e){let t=n;return n==="_index_"?t=e:n==="_value_"&&(t=e==="x"?"y":"x"),t}function getDefaultScaleIDFromAxis(n,e){return n===e?"_index_":"_value_"}function idMatchesAxis(n){if(n==="x"||n==="y"||n==="r")return n}function axisFromPosition(n){if(n==="top"||n==="bottom")return"x";if(n==="left"||n==="right")return"y"}function determineAxis(n,...e){if(idMatchesAxis(n))return n;for(const t of e){const r=t.axis||axisFromPosition(t.position)||n.length>1&&idMatchesAxis(n[0].toLowerCase());if(r)return r}throw new Error(`Cannot determine type of '${n}' axis. Please provide 'axis' or 'position' option.`)}function getAxisFromDataset(n,e,t){if(t[e+"AxisID"]===n)return{axis:e}}function retrieveAxisFromDatasets(n,e){if(e.data&&e.data.datasets){const t=e.data.datasets.filter(r=>r.xAxisID===n||r.yAxisID===n);if(t.length)return getAxisFromDataset(n,"x",t[0])||getAxisFromDataset(n,"y",t[0])}return{}}function mergeScaleConfig(n,e){const t=overrides[n.type]||{scales:{}},r=e.scales||{},a=getIndexAxis(n.type,e),o=Object.create(null);return Object.keys(r).forEach(s=>{const l=r[s];if(!isObject(l))return console.error(`Invalid scale configuration for scale: ${s}`);if(l._proxy)return console.warn(`Ignoring resolver passed as options for scale: ${s}`);const c=determineAxis(s,l,retrieveAxisFromDatasets(s,n),defaults.scales[l.type]),f=getDefaultScaleIDFromAxis(c,a),d=t.scales||{};o[s]=mergeIf(Object.create(null),[{axis:c},l,d[c],d[f]])}),n.data.datasets.forEach(s=>{const l=s.type||n.type,c=s.indexAxis||getIndexAxis(l,e),d=(overrides[l]||{}).scales||{};Object.keys(d).forEach(p=>{const _=getAxisFromDefaultScaleID(p,c),b=s[_+"AxisID"]||_;o[b]=o[b]||Object.create(null),mergeIf(o[b],[{axis:_},r[b],d[p]])})}),Object.keys(o).forEach(s=>{const l=o[s];mergeIf(l,[defaults.scales[l.type],defaults.scale])}),o}function initOptions(n){const e=n.options||(n.options={});e.plugins=valueOrDefault(e.plugins,{}),e.scales=mergeScaleConfig(n,e)}function initData(n){return n=n||{},n.datasets=n.datasets||[],n.labels=n.labels||[],n}function initConfig(n){return n=n||{},n.data=initData(n.data),initOptions(n),n}const keyCache=new Map,keysCached=new Set;function cachedKeys(n,e){let t=keyCache.get(n);return t||(t=e(),keyCache.set(n,t),keysCached.add(t)),t}const addIfFound=(n,e,t)=>{const r=resolveObjectKey(e,t);r!==void 0&&n.add(r)};class Config{constructor(e){this._config=initConfig(e),this._scopeCache=new Map,this._resolverCache=new Map}get platform(){return this._config.platform}get type(){return this._config.type}set type(e){this._config.type=e}get data(){return this._config.data}set data(e){this._config.data=initData(e)}get options(){return this._config.options}set options(e){this._config.options=e}get plugins(){return this._config.plugins}update(){const e=this._config;this.clearCache(),initOptions(e)}clearCache(){this._scopeCache.clear(),this._resolverCache.clear()}datasetScopeKeys(e){return cachedKeys(e,()=>[[`datasets.${e}`,""]])}datasetAnimationScopeKeys(e,t){return cachedKeys(`${e}.transition.${t}`,()=>[[`datasets.${e}.transitions.${t}`,`transitions.${t}`],[`datasets.${e}`,""]])}datasetElementScopeKeys(e,t){return cachedKeys(`${e}-${t}`,()=>[[`datasets.${e}.elements.${t}`,`datasets.${e}`,`elements.${t}`,""]])}pluginScopeKeys(e){const t=e.id,r=this.type;return cachedKeys(`${r}-plugin-${t}`,()=>[[`plugins.${t}`,...e.additionalOptionScopes||[]]])}_cachedScopes(e,t){const r=this._scopeCache;let a=r.get(e);return(!a||t)&&(a=new Map,r.set(e,a)),a}getOptionScopes(e,t,r){const{options:a,type:o}=this,s=this._cachedScopes(e,r),l=s.get(t);if(l)return l;const c=new Set;t.forEach(d=>{e&&(c.add(e),d.forEach(p=>addIfFound(c,e,p))),d.forEach(p=>addIfFound(c,a,p)),d.forEach(p=>addIfFound(c,overrides[o]||{},p)),d.forEach(p=>addIfFound(c,defaults,p)),d.forEach(p=>addIfFound(c,descriptors,p))});const f=Array.from(c);return f.length===0&&f.push(Object.create(null)),keysCached.has(t)&&s.set(t,f),f}chartOptionScopes(){const{options:e,type:t}=this;return[e,overrides[t]||{},defaults.datasets[t]||{},{type:t},defaults,descriptors]}resolveNamedOptions(e,t,r,a=[""]){const o={$shared:!0},{resolver:s,subPrefixes:l}=getResolver(this._resolverCache,e,a);let c=s;if(needContext(s,t)){o.$shared=!1,r=isFunction(r)?r():r;const f=this.createResolver(e,r,l);c=_attachContext(s,r,f)}for(const f of t)o[f]=c[f];return o}createResolver(e,t,r=[""],a){const{resolver:o}=getResolver(this._resolverCache,e,r);return isObject(t)?_attachContext(o,t,void 0,a):o}}function getResolver(n,e,t){let r=n.get(e);r||(r=new Map,n.set(e,r));const a=t.join();let o=r.get(a);return o||(o={resolver:_createResolver(e,t),subPrefixes:t.filter(l=>!l.toLowerCase().includes("hover"))},r.set(a,o)),o}const hasFunction=n=>isObject(n)&&Object.getOwnPropertyNames(n).some(e=>isFunction(n[e]));function needContext(n,e){const{isScriptable:t,isIndexable:r}=_descriptors(n);for(const a of e){const o=t(a),s=r(a),l=(s||o)&&n[a];if(o&&(isFunction(l)||hasFunction(l))||s&&isArray(l))return!0}return!1}var version="4.5.1";const KNOWN_POSITIONS=["top","bottom","left","right","chartArea"];function positionIsHorizontal(n,e){return n==="top"||n==="bottom"||KNOWN_POSITIONS.indexOf(n)===-1&&e==="x"}function compare2Level(n,e){return function(t,r){return t[n]===r[n]?t[e]-r[e]:t[n]-r[n]}}function onAnimationsComplete(n){const e=n.chart,t=e.options.animation;e.notifyPlugins("afterRender"),callback(t&&t.onComplete,[n],e)}function onAnimationProgress(n){const e=n.chart,t=e.options.animation;callback(t&&t.onProgress,[n],e)}function getCanvas(n){return _isDomSupported()&&typeof n=="string"?n=document.getElementById(n):n&&n.length&&(n=n[0]),n&&n.canvas&&(n=n.canvas),n}const instances={},getChart=n=>{const e=getCanvas(n);return Object.values(instances).filter(t=>t.canvas===e).pop()};function moveNumericKeys(n,e,t){const r=Object.keys(n);for(const a of r){const o=+a;if(o>=e){const s=n[a];delete n[a],(t>0||o>e)&&(n[o+t]=s)}}}function determineLastEvent(n,e,t,r){return!t||n.type==="mouseout"?null:r?e:n}class Chart{static defaults=defaults;static instances=instances;static overrides=overrides;static registry=registry;static version=version;static getChart=getChart;static register(...e){registry.add(...e),invalidatePlugins()}static unregister(...e){registry.remove(...e),invalidatePlugins()}constructor(e,t){const r=this.config=new Config(t),a=getCanvas(e),o=getChart(a);if(o)throw new Error("Canvas is already in use. Chart with ID '"+o.id+"' must be destroyed before the canvas with ID '"+o.canvas.id+"' can be reused.");const s=r.createResolver(r.chartOptionScopes(),this.getContext());this.platform=new(r.platform||_detectPlatform(a)),this.platform.updateConfig(r);const l=this.platform.acquireContext(a,s.aspectRatio),c=l&&l.canvas,f=c&&c.height,d=c&&c.width;if(this.id=uid(),this.ctx=l,this.canvas=c,this.width=d,this.height=f,this._options=s,this._aspectRatio=this.aspectRatio,this._layers=[],this._metasets=[],this._stacks=void 0,this.boxes=[],this.currentDevicePixelRatio=void 0,this.chartArea=void 0,this._active=[],this._lastEvent=void 0,this._listeners={},this._responsiveListeners=void 0,this._sortedMetasets=[],this.scales={},this._plugins=new PluginService,this.$proxies={},this._hiddenIndices={},this.attached=!1,this._animationsDisabled=void 0,this.$context=void 0,this._doResize=debounce(p=>this.update(p),s.resizeDelay||0),this._dataChanges=[],instances[this.id]=this,!l||!c){console.error("Failed to create chart: can't acquire context from the given item");return}animator.listen(this,"complete",onAnimationsComplete),animator.listen(this,"progress",onAnimationProgress),this._initialize(),this.attached&&this.update()}get aspectRatio(){const{options:{aspectRatio:e,maintainAspectRatio:t},width:r,height:a,_aspectRatio:o}=this;return isNullOrUndef(e)?t&&o?o:a?r/a:null:e}get data(){return this.config.data}set data(e){this.config.data=e}get options(){return this._options}set options(e){this.config.options=e}get registry(){return registry}_initialize(){return this.notifyPlugins("beforeInit"),this.options.responsive?this.resize():retinaScale(this,this.options.devicePixelRatio),this.bindEvents(),this.notifyPlugins("afterInit"),this}clear(){return clearCanvas(this.canvas,this.ctx),this}stop(){return animator.stop(this),this}resize(e,t){animator.running(this)?this._resizeBeforeDraw={width:e,height:t}:this._resize(e,t)}_resize(e,t){const r=this.options,a=this.canvas,o=r.maintainAspectRatio&&this.aspectRatio,s=this.platform.getMaximumSize(a,e,t,o),l=r.devicePixelRatio||this.platform.getDevicePixelRatio(),c=this.width?"resize":"attach";this.width=s.width,this.height=s.height,this._aspectRatio=this.aspectRatio,retinaScale(this,l,!0)&&(this.notifyPlugins("resize",{size:s}),callback(r.onResize,[this,s],this),this.attached&&this._doResize(c)&&this.render())}ensureScalesHaveIDs(){const t=this.options.scales||{};each(t,(r,a)=>{r.id=a})}buildOrUpdateScales(){const e=this.options,t=e.scales,r=this.scales,a=Object.keys(r).reduce((s,l)=>(s[l]=!1,s),{});let o=[];t&&(o=o.concat(Object.keys(t).map(s=>{const l=t[s],c=determineAxis(s,l),f=c==="r",d=c==="x";return{options:l,dposition:f?"chartArea":d?"bottom":"left",dtype:f?"radialLinear":d?"category":"linear"}}))),each(o,s=>{const l=s.options,c=l.id,f=determineAxis(c,l),d=valueOrDefault(l.type,s.dtype);(l.position===void 0||positionIsHorizontal(l.position,f)!==positionIsHorizontal(s.dposition))&&(l.position=s.dposition),a[c]=!0;let p=null;if(c in r&&r[c].type===d)p=r[c];else{const _=registry.getScale(d);p=new _({id:c,type:d,ctx:this.ctx,chart:this}),r[p.id]=p}p.init(l,e)}),each(a,(s,l)=>{s||delete r[l]}),each(r,s=>{layouts.configure(this,s,s.options),layouts.addBox(this,s)})}_updateMetasets(){const e=this._metasets,t=this.data.datasets.length,r=e.length;if(e.sort((a,o)=>a.index-o.index),r>t){for(let a=t;a<r;++a)this._destroyDatasetMeta(a);e.splice(t,r-t)}this._sortedMetasets=e.slice(0).sort(compare2Level("order","index"))}_removeUnreferencedMetasets(){const{_metasets:e,data:{datasets:t}}=this;e.length>t.length&&delete this._stacks,e.forEach((r,a)=>{t.filter(o=>o===r._dataset).length===0&&this._destroyDatasetMeta(a)})}buildOrUpdateControllers(){const e=[],t=this.data.datasets;let r,a;for(this._removeUnreferencedMetasets(),r=0,a=t.length;r<a;r++){const o=t[r];let s=this.getDatasetMeta(r);const l=o.type||this.config.type;if(s.type&&s.type!==l&&(this._destroyDatasetMeta(r),s=this.getDatasetMeta(r)),s.type=l,s.indexAxis=o.indexAxis||getIndexAxis(l,this.options),s.order=o.order||0,s.index=r,s.label=""+o.label,s.visible=this.isDatasetVisible(r),s.controller)s.controller.updateIndex(r),s.controller.linkScales();else{const c=registry.getController(l),{datasetElementType:f,dataElementType:d}=defaults.datasets[l];Object.assign(c,{dataElementType:registry.getElement(d),datasetElementType:f&&registry.getElement(f)}),s.controller=new c(this,r),e.push(s.controller)}}return this._updateMetasets(),e}_resetElements(){each(this.data.datasets,(e,t)=>{this.getDatasetMeta(t).controller.reset()},this)}reset(){this._resetElements(),this.notifyPlugins("reset")}update(e){const t=this.config;t.update();const r=this._options=t.createResolver(t.chartOptionScopes(),this.getContext()),a=this._animationsDisabled=!r.animation;if(this._updateScales(),this._checkEventBindings(),this._updateHiddenIndices(),this._plugins.invalidate(),this.notifyPlugins("beforeUpdate",{mode:e,cancelable:!0})===!1)return;const o=this.buildOrUpdateControllers();this.notifyPlugins("beforeElementsUpdate");let s=0;for(let f=0,d=this.data.datasets.length;f<d;f++){const{controller:p}=this.getDatasetMeta(f),_=!a&&o.indexOf(p)===-1;p.buildOrUpdateElements(_),s=Math.max(+p.getMaxOverflow(),s)}s=this._minPadding=r.layout.autoPadding?s:0,this._updateLayout(s),a||each(o,f=>{f.reset()}),this._updateDatasets(e),this.notifyPlugins("afterUpdate",{mode:e}),this._layers.sort(compare2Level("z","_idx"));const{_active:l,_lastEvent:c}=this;c?this._eventHandler(c,!0):l.length&&this._updateHoverStyles(l,l,!0),this.render()}_updateScales(){each(this.scales,e=>{layouts.removeBox(this,e)}),this.ensureScalesHaveIDs(),this.buildOrUpdateScales()}_checkEventBindings(){const e=this.options,t=new Set(Object.keys(this._listeners)),r=new Set(e.events);(!setsEqual(t,r)||!!this._responsiveListeners!==e.responsive)&&(this.unbindEvents(),this.bindEvents())}_updateHiddenIndices(){const{_hiddenIndices:e}=this,t=this._getUniformDataChanges()||[];for(const{method:r,start:a,count:o}of t){const s=r==="_removeElements"?-o:o;moveNumericKeys(e,a,s)}}_getUniformDataChanges(){const e=this._dataChanges;if(!e||!e.length)return;this._dataChanges=[];const t=this.data.datasets.length,r=o=>new Set(e.filter(s=>s[0]===o).map((s,l)=>l+","+s.splice(1).join(","))),a=r(0);for(let o=1;o<t;o++)if(!setsEqual(a,r(o)))return;return Array.from(a).map(o=>o.split(",")).map(o=>({method:o[1],start:+o[2],count:+o[3]}))}_updateLayout(e){if(this.notifyPlugins("beforeLayout",{cancelable:!0})===!1)return;layouts.update(this,this.width,this.height,e);const t=this.chartArea,r=t.width<=0||t.height<=0;this._layers=[],each(this.boxes,a=>{r&&a.position==="chartArea"||(a.configure&&a.configure(),this._layers.push(...a._layers()))},this),this._layers.forEach((a,o)=>{a._idx=o}),this.notifyPlugins("afterLayout")}_updateDatasets(e){if(this.notifyPlugins("beforeDatasetsUpdate",{mode:e,cancelable:!0})!==!1){for(let t=0,r=this.data.datasets.length;t<r;++t)this.getDatasetMeta(t).controller.configure();for(let t=0,r=this.data.datasets.length;t<r;++t)this._updateDataset(t,isFunction(e)?e({datasetIndex:t}):e);this.notifyPlugins("afterDatasetsUpdate",{mode:e})}}_updateDataset(e,t){const r=this.getDatasetMeta(e),a={meta:r,index:e,mode:t,cancelable:!0};this.notifyPlugins("beforeDatasetUpdate",a)!==!1&&(r.controller._update(t),a.cancelable=!1,this.notifyPlugins("afterDatasetUpdate",a))}render(){this.notifyPlugins("beforeRender",{cancelable:!0})!==!1&&(animator.has(this)?this.attached&&!animator.running(this)&&animator.start(this):(this.draw(),onAnimationsComplete({chart:this})))}draw(){let e;if(this._resizeBeforeDraw){const{width:r,height:a}=this._resizeBeforeDraw;this._resizeBeforeDraw=null,this._resize(r,a)}if(this.clear(),this.width<=0||this.height<=0||this.notifyPlugins("beforeDraw",{cancelable:!0})===!1)return;const t=this._layers;for(e=0;e<t.length&&t[e].z<=0;++e)t[e].draw(this.chartArea);for(this._drawDatasets();e<t.length;++e)t[e].draw(this.chartArea);this.notifyPlugins("afterDraw")}_getSortedDatasetMetas(e){const t=this._sortedMetasets,r=[];let a,o;for(a=0,o=t.length;a<o;++a){const s=t[a];(!e||s.visible)&&r.push(s)}return r}getSortedVisibleDatasetMetas(){return this._getSortedDatasetMetas(!0)}_drawDatasets(){if(this.notifyPlugins("beforeDatasetsDraw",{cancelable:!0})===!1)return;const e=this.getSortedVisibleDatasetMetas();for(let t=e.length-1;t>=0;--t)this._drawDataset(e[t]);this.notifyPlugins("afterDatasetsDraw")}_drawDataset(e){const t=this.ctx,r={meta:e,index:e.index,cancelable:!0},a=getDatasetClipArea(this,e);this.notifyPlugins("beforeDatasetDraw",r)!==!1&&(a&&clipArea(t,a),e.controller.draw(),a&&unclipArea(t),r.cancelable=!1,this.notifyPlugins("afterDatasetDraw",r))}isPointInArea(e){return _isPointInArea(e,this.chartArea,this._minPadding)}getElementsAtEventForMode(e,t,r,a){const o=Interaction.modes[t];return typeof o=="function"?o(this,e,r,a):[]}getDatasetMeta(e){const t=this.data.datasets[e],r=this._metasets;let a=r.filter(o=>o&&o._dataset===t).pop();return a||(a={type:null,data:[],dataset:null,controller:null,hidden:null,xAxisID:null,yAxisID:null,order:t&&t.order||0,index:e,_dataset:t,_parsed:[],_sorted:!1},r.push(a)),a}getContext(){return this.$context||(this.$context=createContext(null,{chart:this,type:"chart"}))}getVisibleDatasetCount(){return this.getSortedVisibleDatasetMetas().length}isDatasetVisible(e){const t=this.data.datasets[e];if(!t)return!1;const r=this.getDatasetMeta(e);return typeof r.hidden=="boolean"?!r.hidden:!t.hidden}setDatasetVisibility(e,t){const r=this.getDatasetMeta(e);r.hidden=!t}toggleDataVisibility(e){this._hiddenIndices[e]=!this._hiddenIndices[e]}getDataVisibility(e){return!this._hiddenIndices[e]}_updateVisibility(e,t,r){const a=r?"show":"hide",o=this.getDatasetMeta(e),s=o.controller._resolveAnimations(void 0,a);defined(t)?(o.data[t].hidden=!r,this.update()):(this.setDatasetVisibility(e,r),s.update(o,{visible:r}),this.update(l=>l.datasetIndex===e?a:void 0))}hide(e,t){this._updateVisibility(e,t,!1)}show(e,t){this._updateVisibility(e,t,!0)}_destroyDatasetMeta(e){const t=this._metasets[e];t&&t.controller&&t.controller._destroy(),delete this._metasets[e]}_stop(){let e,t;for(this.stop(),animator.remove(this),e=0,t=this.data.datasets.length;e<t;++e)this._destroyDatasetMeta(e)}destroy(){this.notifyPlugins("beforeDestroy");const{canvas:e,ctx:t}=this;this._stop(),this.config.clearCache(),e&&(this.unbindEvents(),clearCanvas(e,t),this.platform.releaseContext(t),this.canvas=null,this.ctx=null),delete instances[this.id],this.notifyPlugins("afterDestroy")}toBase64Image(...e){return this.canvas.toDataURL(...e)}bindEvents(){this.bindUserEvents(),this.options.responsive?this.bindResponsiveEvents():this.attached=!0}bindUserEvents(){const e=this._listeners,t=this.platform,r=(o,s)=>{t.addEventListener(this,o,s),e[o]=s},a=(o,s,l)=>{o.offsetX=s,o.offsetY=l,this._eventHandler(o)};each(this.options.events,o=>r(o,a))}bindResponsiveEvents(){this._responsiveListeners||(this._responsiveListeners={});const e=this._responsiveListeners,t=this.platform,r=(c,f)=>{t.addEventListener(this,c,f),e[c]=f},a=(c,f)=>{e[c]&&(t.removeEventListener(this,c,f),delete e[c])},o=(c,f)=>{this.canvas&&this.resize(c,f)};let s;const l=()=>{a("attach",l),this.attached=!0,this.resize(),r("resize",o),r("detach",s)};s=()=>{this.attached=!1,a("resize",o),this._stop(),this._resize(0,0),r("attach",l)},t.isAttached(this.canvas)?l():s()}unbindEvents(){each(this._listeners,(e,t)=>{this.platform.removeEventListener(this,t,e)}),this._listeners={},each(this._responsiveListeners,(e,t)=>{this.platform.removeEventListener(this,t,e)}),this._responsiveListeners=void 0}updateHoverStyle(e,t,r){const a=r?"set":"remove";let o,s,l,c;for(t==="dataset"&&(o=this.getDatasetMeta(e[0].datasetIndex),o.controller["_"+a+"DatasetHoverStyle"]()),l=0,c=e.length;l<c;++l){s=e[l];const f=s&&this.getDatasetMeta(s.datasetIndex).controller;f&&f[a+"HoverStyle"](s.element,s.datasetIndex,s.index)}}getActiveElements(){return this._active||[]}setActiveElements(e){const t=this._active||[],r=e.map(({datasetIndex:o,index:s})=>{const l=this.getDatasetMeta(o);if(!l)throw new Error("No dataset found at index "+o);return{datasetIndex:o,element:l.data[s],index:s}});!_elementsEqual(r,t)&&(this._active=r,this._lastEvent=null,this._updateHoverStyles(r,t))}notifyPlugins(e,t,r){return this._plugins.notify(this,e,t,r)}isPluginEnabled(e){return this._plugins._cache.filter(t=>t.plugin.id===e).length===1}_updateHoverStyles(e,t,r){const a=this.options.hover,o=(c,f)=>c.filter(d=>!f.some(p=>d.datasetIndex===p.datasetIndex&&d.index===p.index)),s=o(t,e),l=r?e:o(e,t);s.length&&this.updateHoverStyle(s,a.mode,!1),l.length&&a.mode&&this.updateHoverStyle(l,a.mode,!0)}_eventHandler(e,t){const r={event:e,replay:t,cancelable:!0,inChartArea:this.isPointInArea(e)},a=s=>(s.options.events||this.options.events).includes(e.native.type);if(this.notifyPlugins("beforeEvent",r,a)===!1)return;const o=this._handleEvent(e,t,r.inChartArea);return r.cancelable=!1,this.notifyPlugins("afterEvent",r,a),(o||r.changed)&&this.render(),this}_handleEvent(e,t,r){const{_active:a=[],options:o}=this,s=t,l=this._getActiveElements(e,a,r,s),c=_isClickEvent(e),f=determineLastEvent(e,this._lastEvent,r,c);r&&(this._lastEvent=null,callback(o.onHover,[e,l,this],this),c&&callback(o.onClick,[e,l,this],this));const d=!_elementsEqual(l,a);return(d||t)&&(this._active=l,this._updateHoverStyles(l,a,t)),this._lastEvent=f,d}_getActiveElements(e,t,r,a){if(e.type==="mouseout")return[];if(!r)return t;const o=this.options.hover;return this.getElementsAtEventForMode(e,o.mode,o,a)}}function invalidatePlugins(){return each(Chart.instances,n=>n._plugins.invalidate())}function clipSelf(n,e,t){const{startAngle:r,x:a,y:o,outerRadius:s,innerRadius:l,options:c}=e,{borderWidth:f,borderJoinStyle:d}=c,p=Math.min(f/s,_normalizeAngle(r-t));if(n.beginPath(),n.arc(a,o,s-f/2,r+p/2,t-p/2),l>0){const _=Math.min(f/l,_normalizeAngle(r-t));n.arc(a,o,l+f/2,t-_/2,r+_/2,!0)}else{const _=Math.min(f/2,s*_normalizeAngle(r-t));if(d==="round")n.arc(a,o,_,t-PI/2,r+PI/2,!0);else if(d==="bevel"){const b=2*_*_,y=-b*Math.cos(t+PI/2)+a,E=-b*Math.sin(t+PI/2)+o,C=b*Math.cos(r+PI/2)+a,D=b*Math.sin(r+PI/2)+o;n.lineTo(y,E),n.lineTo(C,D)}}n.closePath(),n.moveTo(0,0),n.rect(0,0,n.canvas.width,n.canvas.height),n.clip("evenodd")}function clipArc(n,e,t){const{startAngle:r,pixelMargin:a,x:o,y:s,outerRadius:l,innerRadius:c}=e;let f=a/l;n.beginPath(),n.arc(o,s,l,r-f,t+f),c>a?(f=a/c,n.arc(o,s,c,t+f,r-f,!0)):n.arc(o,s,a,t+HALF_PI,r-HALF_PI),n.closePath(),n.clip()}function toRadiusCorners(n){return _readValueToProps(n,["outerStart","outerEnd","innerStart","innerEnd"])}function parseBorderRadius$1(n,e,t,r){const a=toRadiusCorners(n.options.borderRadius),o=(t-e)/2,s=Math.min(o,r*e/2),l=c=>{const f=(t-Math.min(o,c))*r/2;return _limitValue(c,0,Math.min(o,f))};return{outerStart:l(a.outerStart),outerEnd:l(a.outerEnd),innerStart:_limitValue(a.innerStart,0,s),innerEnd:_limitValue(a.innerEnd,0,s)}}function rThetaToXY(n,e,t,r){return{x:t+n*Math.cos(e),y:r+n*Math.sin(e)}}function pathArc(n,e,t,r,a,o){const{x:s,y:l,startAngle:c,pixelMargin:f,innerRadius:d}=e,p=Math.max(e.outerRadius+r+t-f,0),_=d>0?d+r+t+f:0;let b=0;const y=a-c;if(r){const re=d>0?d-r:0,de=p>0?p-r:0,le=(re+de)/2,$e=le!==0?y*le/(le+r):y;b=(y-$e)/2}const E=Math.max(.001,y*p-t/PI)/p,C=(y-E)/2,D=c+C+b,M=a-C-b,{outerStart:F,outerEnd:P,innerStart:H,innerEnd:B}=parseBorderRadius$1(e,_,p,M-D),g=p-F,q=p-P,G=D+F/g,Z=M-P/q,te=_+H,ne=_+B,Q=D+H/te,Ee=M-B/ne;if(n.beginPath(),o){const re=(G+Z)/2;if(n.arc(s,l,p,G,re),n.arc(s,l,p,re,Z),P>0){const xe=rThetaToXY(q,Z,s,l);n.arc(xe.x,xe.y,P,Z,M+HALF_PI)}const de=rThetaToXY(ne,M,s,l);if(n.lineTo(de.x,de.y),B>0){const xe=rThetaToXY(ne,Ee,s,l);n.arc(xe.x,xe.y,B,M+HALF_PI,Ee+Math.PI)}const le=(M-B/_+(D+H/_))/2;if(n.arc(s,l,_,M-B/_,le,!0),n.arc(s,l,_,le,D+H/_,!0),H>0){const xe=rThetaToXY(te,Q,s,l);n.arc(xe.x,xe.y,H,Q+Math.PI,D-HALF_PI)}const $e=rThetaToXY(g,D,s,l);if(n.lineTo($e.x,$e.y),F>0){const xe=rThetaToXY(g,G,s,l);n.arc(xe.x,xe.y,F,D-HALF_PI,G)}}else{n.moveTo(s,l);const re=Math.cos(G)*p+s,de=Math.sin(G)*p+l;n.lineTo(re,de);const le=Math.cos(Z)*p+s,$e=Math.sin(Z)*p+l;n.lineTo(le,$e)}n.closePath()}function drawArc(n,e,t,r,a){const{fullCircles:o,startAngle:s,circumference:l}=e;let c=e.endAngle;if(o){pathArc(n,e,t,r,c,a);for(let f=0;f<o;++f)n.fill();isNaN(l)||(c=s+(l%TAU||TAU))}return pathArc(n,e,t,r,c,a),n.fill(),c}function drawBorder(n,e,t,r,a){const{fullCircles:o,startAngle:s,circumference:l,options:c}=e,{borderWidth:f,borderJoinStyle:d,borderDash:p,borderDashOffset:_,borderRadius:b}=c,y=c.borderAlign==="inner";if(!f)return;n.setLineDash(p||[]),n.lineDashOffset=_,y?(n.lineWidth=f*2,n.lineJoin=d||"round"):(n.lineWidth=f,n.lineJoin=d||"bevel");let E=e.endAngle;if(o){pathArc(n,e,t,r,E,a);for(let C=0;C<o;++C)n.stroke();isNaN(l)||(E=s+(l%TAU||TAU))}y&&clipArc(n,e,E),c.selfJoin&&E-s>=PI&&b===0&&d!=="miter"&&clipSelf(n,e,E),o||(pathArc(n,e,t,r,E,a),n.stroke())}class ArcElement extends Element$1{static id="arc";static defaults={borderAlign:"center",borderColor:"#fff",borderDash:[],borderDashOffset:0,borderJoinStyle:void 0,borderRadius:0,borderWidth:2,offset:0,spacing:0,angle:void 0,circular:!0,selfJoin:!1};static defaultRoutes={backgroundColor:"backgroundColor"};static descriptors={_scriptable:!0,_indexable:e=>e!=="borderDash"};circumference;endAngle;fullCircles;innerRadius;outerRadius;pixelMargin;startAngle;constructor(e){super(),this.options=void 0,this.circumference=void 0,this.startAngle=void 0,this.endAngle=void 0,this.innerRadius=void 0,this.outerRadius=void 0,this.pixelMargin=0,this.fullCircles=0,e&&Object.assign(this,e)}inRange(e,t,r){const a=this.getProps(["x","y"],r),{angle:o,distance:s}=getAngleFromPoint(a,{x:e,y:t}),{startAngle:l,endAngle:c,innerRadius:f,outerRadius:d,circumference:p}=this.getProps(["startAngle","endAngle","innerRadius","outerRadius","circumference"],r),_=(this.options.spacing+this.options.borderWidth)/2,b=valueOrDefault(p,c-l),y=_angleBetween(o,l,c)&&l!==c,E=b>=TAU||y,C=_isBetween(s,f+_,d+_);return E&&C}getCenterPoint(e){const{x:t,y:r,startAngle:a,endAngle:o,innerRadius:s,outerRadius:l}=this.getProps(["x","y","startAngle","endAngle","innerRadius","outerRadius"],e),{offset:c,spacing:f}=this.options,d=(a+o)/2,p=(s+l+f+c)/2;return{x:t+Math.cos(d)*p,y:r+Math.sin(d)*p}}tooltipPosition(e){return this.getCenterPoint(e)}draw(e){const{options:t,circumference:r}=this,a=(t.offset||0)/4,o=(t.spacing||0)/2,s=t.circular;if(this.pixelMargin=t.borderAlign==="inner"?.33:0,this.fullCircles=r>TAU?Math.floor(r/TAU):0,r===0||this.innerRadius<0||this.outerRadius<0)return;e.save();const l=(this.startAngle+this.endAngle)/2;e.translate(Math.cos(l)*a,Math.sin(l)*a);const c=1-Math.sin(Math.min(PI,r||0)),f=a*c;e.fillStyle=t.backgroundColor,e.strokeStyle=t.borderColor,drawArc(e,this,f,o,s),drawBorder(e,this,f,o,s),e.restore()}}function setStyle(n,e,t=e){n.lineCap=valueOrDefault(t.borderCapStyle,e.borderCapStyle),n.setLineDash(valueOrDefault(t.borderDash,e.borderDash)),n.lineDashOffset=valueOrDefault(t.borderDashOffset,e.borderDashOffset),n.lineJoin=valueOrDefault(t.borderJoinStyle,e.borderJoinStyle),n.lineWidth=valueOrDefault(t.borderWidth,e.borderWidth),n.strokeStyle=valueOrDefault(t.borderColor,e.borderColor)}function lineTo(n,e,t){n.lineTo(t.x,t.y)}function getLineMethod(n){return n.stepped?_steppedLineTo:n.tension||n.cubicInterpolationMode==="monotone"?_bezierCurveTo:lineTo}function pathVars(n,e,t={}){const r=n.length,{start:a=0,end:o=r-1}=t,{start:s,end:l}=e,c=Math.max(a,s),f=Math.min(o,l),d=a<s&&o<s||a>l&&o>l;return{count:r,start:c,loop:e.loop,ilen:f<c&&!d?r+f-c:f-c}}function pathSegment(n,e,t,r){const{points:a,options:o}=e,{count:s,start:l,loop:c,ilen:f}=pathVars(a,t,r),d=getLineMethod(o);let{move:p=!0,reverse:_}=r||{},b,y,E;for(b=0;b<=f;++b)y=a[(l+(_?f-b:b))%s],!y.skip&&(p?(n.moveTo(y.x,y.y),p=!1):d(n,E,y,_,o.stepped),E=y);return c&&(y=a[(l+(_?f:0))%s],d(n,E,y,_,o.stepped)),!!c}function fastPathSegment(n,e,t,r){const a=e.points,{count:o,start:s,ilen:l}=pathVars(a,t,r),{move:c=!0,reverse:f}=r||{};let d=0,p=0,_,b,y,E,C,D;const M=P=>(s+(f?l-P:P))%o,F=()=>{E!==C&&(n.lineTo(d,C),n.lineTo(d,E),n.lineTo(d,D))};for(c&&(b=a[M(0)],n.moveTo(b.x,b.y)),_=0;_<=l;++_){if(b=a[M(_)],b.skip)continue;const P=b.x,H=b.y,B=P|0;B===y?(H<E?E=H:H>C&&(C=H),d=(p*d+P)/++p):(F(),n.lineTo(P,H),y=B,p=0,E=C=H),D=H}F()}function _getSegmentMethod(n){const e=n.options,t=e.borderDash&&e.borderDash.length;return!n._decimated&&!n._loop&&!e.tension&&e.cubicInterpolationMode!=="monotone"&&!e.stepped&&!t?fastPathSegment:pathSegment}function _getInterpolationMethod(n){return n.stepped?_steppedInterpolation:n.tension||n.cubicInterpolationMode==="monotone"?_bezierInterpolation:_pointInLine}function strokePathWithCache(n,e,t,r){let a=e._path;a||(a=e._path=new Path2D,e.path(a,t,r)&&a.closePath()),setStyle(n,e.options),n.stroke(a)}function strokePathDirect(n,e,t,r){const{segments:a,options:o}=e,s=_getSegmentMethod(e);for(const l of a)setStyle(n,o,l.style),n.beginPath(),s(n,e,l,{start:t,end:t+r-1})&&n.closePath(),n.stroke()}const usePath2D=typeof Path2D=="function";function draw(n,e,t,r){usePath2D&&!e.options.segment?strokePathWithCache(n,e,t,r):strokePathDirect(n,e,t,r)}class LineElement extends Element$1{static id="line";static defaults={borderCapStyle:"butt",borderDash:[],borderDashOffset:0,borderJoinStyle:"miter",borderWidth:3,capBezierPoints:!0,cubicInterpolationMode:"default",fill:!1,spanGaps:!1,stepped:!1,tension:0};static defaultRoutes={backgroundColor:"backgroundColor",borderColor:"borderColor"};static descriptors={_scriptable:!0,_indexable:e=>e!=="borderDash"&&e!=="fill"};constructor(e){super(),this.animated=!0,this.options=void 0,this._chart=void 0,this._loop=void 0,this._fullLoop=void 0,this._path=void 0,this._points=void 0,this._segments=void 0,this._decimated=!1,this._pointsUpdated=!1,this._datasetIndex=void 0,e&&Object.assign(this,e)}updateControlPoints(e,t){const r=this.options;if((r.tension||r.cubicInterpolationMode==="monotone")&&!r.stepped&&!this._pointsUpdated){const a=r.spanGaps?this._loop:this._fullLoop;_updateBezierControlPoints(this._points,r,e,a,t),this._pointsUpdated=!0}}set points(e){this._points=e,delete this._segments,delete this._path,this._pointsUpdated=!1}get points(){return this._points}get segments(){return this._segments||(this._segments=_computeSegments(this,this.options.segment))}first(){const e=this.segments,t=this.points;return e.length&&t[e[0].start]}last(){const e=this.segments,t=this.points,r=e.length;return r&&t[e[r-1].end]}interpolate(e,t){const r=this.options,a=e[t],o=this.points,s=_boundSegments(this,{property:t,start:a,end:a});if(!s.length)return;const l=[],c=_getInterpolationMethod(r);let f,d;for(f=0,d=s.length;f<d;++f){const{start:p,end:_}=s[f],b=o[p],y=o[_];if(b===y){l.push(b);continue}const E=Math.abs((a-b[t])/(y[t]-b[t])),C=c(b,y,E,r.stepped);C[t]=e[t],l.push(C)}return l.length===1?l[0]:l}pathSegment(e,t,r){return _getSegmentMethod(this)(e,this,t,r)}path(e,t,r){const a=this.segments,o=_getSegmentMethod(this);let s=this._loop;t=t||0,r=r||this.points.length-t;for(const l of a)s&=o(e,this,l,{start:t,end:t+r-1});return!!s}draw(e,t,r,a){const o=this.options||{};(this.points||[]).length&&o.borderWidth&&(e.save(),draw(e,this,r,a),e.restore()),this.animated&&(this._pointsUpdated=!1,this._path=void 0)}}function inRange$1(n,e,t,r){const a=n.options,{[t]:o}=n.getProps([t],r);return Math.abs(e-o)<a.radius+a.hitRadius}class PointElement extends Element$1{static id="point";parsed;skip;stop;static defaults={borderWidth:1,hitRadius:1,hoverBorderWidth:1,hoverRadius:4,pointStyle:"circle",radius:3,rotation:0};static defaultRoutes={backgroundColor:"backgroundColor",borderColor:"borderColor"};constructor(e){super(),this.options=void 0,this.parsed=void 0,this.skip=void 0,this.stop=void 0,e&&Object.assign(this,e)}inRange(e,t,r){const a=this.options,{x:o,y:s}=this.getProps(["x","y"],r);return Math.pow(e-o,2)+Math.pow(t-s,2)<Math.pow(a.hitRadius+a.radius,2)}inXRange(e,t){return inRange$1(this,e,"x",t)}inYRange(e,t){return inRange$1(this,e,"y",t)}getCenterPoint(e){const{x:t,y:r}=this.getProps(["x","y"],e);return{x:t,y:r}}size(e){e=e||this.options||{};let t=e.radius||0;t=Math.max(t,t&&e.hoverRadius||0);const r=t&&e.borderWidth||0;return(t+r)*2}draw(e,t){const r=this.options;this.skip||r.radius<.1||!_isPointInArea(this,t,this.size(r)/2)||(e.strokeStyle=r.borderColor,e.lineWidth=r.borderWidth,e.fillStyle=r.backgroundColor,drawPoint(e,r,this.x,this.y))}getRange(){const e=this.options||{};return e.radius+e.hitRadius}}function getBarBounds(n,e){const{x:t,y:r,base:a,width:o,height:s}=n.getProps(["x","y","base","width","height"],e);let l,c,f,d,p;return n.horizontal?(p=s/2,l=Math.min(t,a),c=Math.max(t,a),f=r-p,d=r+p):(p=o/2,l=t-p,c=t+p,f=Math.min(r,a),d=Math.max(r,a)),{left:l,top:f,right:c,bottom:d}}function skipOrLimit(n,e,t,r){return n?0:_limitValue(e,t,r)}function parseBorderWidth(n,e,t){const r=n.options.borderWidth,a=n.borderSkipped,o=toTRBL(r);return{t:skipOrLimit(a.top,o.top,0,t),r:skipOrLimit(a.right,o.right,0,e),b:skipOrLimit(a.bottom,o.bottom,0,t),l:skipOrLimit(a.left,o.left,0,e)}}function parseBorderRadius(n,e,t){const{enableBorderRadius:r}=n.getProps(["enableBorderRadius"]),a=n.options.borderRadius,o=toTRBLCorners(a),s=Math.min(e,t),l=n.borderSkipped,c=r||isObject(a);return{topLeft:skipOrLimit(!c||l.top||l.left,o.topLeft,0,s),topRight:skipOrLimit(!c||l.top||l.right,o.topRight,0,s),bottomLeft:skipOrLimit(!c||l.bottom||l.left,o.bottomLeft,0,s),bottomRight:skipOrLimit(!c||l.bottom||l.right,o.bottomRight,0,s)}}function boundingRects(n){const e=getBarBounds(n),t=e.right-e.left,r=e.bottom-e.top,a=parseBorderWidth(n,t/2,r/2),o=parseBorderRadius(n,t/2,r/2);return{outer:{x:e.left,y:e.top,w:t,h:r,radius:o},inner:{x:e.left+a.l,y:e.top+a.t,w:t-a.l-a.r,h:r-a.t-a.b,radius:{topLeft:Math.max(0,o.topLeft-Math.max(a.t,a.l)),topRight:Math.max(0,o.topRight-Math.max(a.t,a.r)),bottomLeft:Math.max(0,o.bottomLeft-Math.max(a.b,a.l)),bottomRight:Math.max(0,o.bottomRight-Math.max(a.b,a.r))}}}}function inRange(n,e,t,r){const a=e===null,o=t===null,l=n&&!(a&&o)&&getBarBounds(n,r);return l&&(a||_isBetween(e,l.left,l.right))&&(o||_isBetween(t,l.top,l.bottom))}function hasRadius(n){return n.topLeft||n.topRight||n.bottomLeft||n.bottomRight}function addNormalRectPath(n,e){n.rect(e.x,e.y,e.w,e.h)}function inflateRect(n,e,t={}){const r=n.x!==t.x?-e:0,a=n.y!==t.y?-e:0,o=(n.x+n.w!==t.x+t.w?e:0)-r,s=(n.y+n.h!==t.y+t.h?e:0)-a;return{x:n.x+r,y:n.y+a,w:n.w+o,h:n.h+s,radius:n.radius}}class BarElement extends Element$1{static id="bar";static defaults={borderSkipped:"start",borderWidth:0,borderRadius:0,inflateAmount:"auto",pointStyle:void 0};static defaultRoutes={backgroundColor:"backgroundColor",borderColor:"borderColor"};constructor(e){super(),this.options=void 0,this.horizontal=void 0,this.base=void 0,this.width=void 0,this.height=void 0,this.inflateAmount=void 0,e&&Object.assign(this,e)}draw(e){const{inflateAmount:t,options:{borderColor:r,backgroundColor:a}}=this,{inner:o,outer:s}=boundingRects(this),l=hasRadius(s.radius)?addRoundedRectPath:addNormalRectPath;e.save(),(s.w!==o.w||s.h!==o.h)&&(e.beginPath(),l(e,inflateRect(s,t,o)),e.clip(),l(e,inflateRect(o,-t,s)),e.fillStyle=r,e.fill("evenodd")),e.beginPath(),l(e,inflateRect(o,t)),e.fillStyle=a,e.fill(),e.restore()}inRange(e,t,r){return inRange(this,e,t,r)}inXRange(e,t){return inRange(this,e,null,t)}inYRange(e,t){return inRange(this,null,e,t)}getCenterPoint(e){const{x:t,y:r,base:a,horizontal:o}=this.getProps(["x","y","base","horizontal"],e);return{x:o?(t+a)/2:t,y:o?r:(r+a)/2}}getRange(e){return e==="x"?this.width/2:this.height/2}}var elements=Object.freeze({__proto__:null,ArcElement,BarElement,LineElement,PointElement});const BORDER_COLORS=["rgb(54, 162, 235)","rgb(255, 99, 132)","rgb(255, 159, 64)","rgb(255, 205, 86)","rgb(75, 192, 192)","rgb(153, 102, 255)","rgb(201, 203, 207)"],BACKGROUND_COLORS=BORDER_COLORS.map(n=>n.replace("rgb(","rgba(").replace(")",", 0.5)"));function getBorderColor(n){return BORDER_COLORS[n%BORDER_COLORS.length]}function getBackgroundColor(n){return BACKGROUND_COLORS[n%BACKGROUND_COLORS.length]}function colorizeDefaultDataset(n,e){return n.borderColor=getBorderColor(e),n.backgroundColor=getBackgroundColor(e),++e}function colorizeDoughnutDataset(n,e){return n.backgroundColor=n.data.map(()=>getBorderColor(e++)),e}function colorizePolarAreaDataset(n,e){return n.backgroundColor=n.data.map(()=>getBackgroundColor(e++)),e}function getColorizer(n){let e=0;return(t,r)=>{const a=n.getDatasetMeta(r).controller;a instanceof DoughnutController?e=colorizeDoughnutDataset(t,e):a instanceof PolarAreaController?e=colorizePolarAreaDataset(t,e):a&&(e=colorizeDefaultDataset(t,e))}}function containsColorsDefinitions(n){let e;for(e in n)if(n[e].borderColor||n[e].backgroundColor)return!0;return!1}function containsColorsDefinition(n){return n&&(n.borderColor||n.backgroundColor)}function containsDefaultColorsDefenitions(){return defaults.borderColor!=="rgba(0,0,0,0.1)"||defaults.backgroundColor!=="rgba(0,0,0,0.1)"}var plugin_colors={id:"colors",defaults:{enabled:!0,forceOverride:!1},beforeLayout(n,e,t){if(!t.enabled)return;const{data:{datasets:r},options:a}=n.config,{elements:o}=a,s=containsColorsDefinitions(r)||containsColorsDefinition(a)||o&&containsColorsDefinitions(o)||containsDefaultColorsDefenitions();if(!t.forceOverride&&s)return;const l=getColorizer(n);r.forEach(l)}};function lttbDecimation(n,e,t,r,a){const o=a.samples||r;if(o>=t)return n.slice(e,e+t);const s=[],l=(t-2)/(o-2);let c=0;const f=e+t-1;let d=e,p,_,b,y,E;for(s[c++]=n[d],p=0;p<o-2;p++){let C=0,D=0,M;const F=Math.floor((p+1)*l)+1+e,P=Math.min(Math.floor((p+2)*l)+1,t)+e,H=P-F;for(M=F;M<P;M++)C+=n[M].x,D+=n[M].y;C/=H,D/=H;const B=Math.floor(p*l)+1+e,g=Math.min(Math.floor((p+1)*l)+1,t)+e,{x:q,y:G}=n[d];for(b=y=-1,M=B;M<g;M++)y=.5*Math.abs((q-C)*(n[M].y-G)-(q-n[M].x)*(D-G)),y>b&&(b=y,_=n[M],E=M);s[c++]=_,d=E}return s[c++]=n[f],s}function minMaxDecimation(n,e,t,r){let a=0,o=0,s,l,c,f,d,p,_,b,y,E;const C=[],D=e+t-1,M=n[e].x,P=n[D].x-M;for(s=e;s<e+t;++s){l=n[s],c=(l.x-M)/P*r,f=l.y;const H=c|0;if(H===d)f<y?(y=f,p=s):f>E&&(E=f,_=s),a=(o*a+l.x)/++o;else{const B=s-1;if(!isNullOrUndef(p)&&!isNullOrUndef(_)){const g=Math.min(p,_),q=Math.max(p,_);g!==b&&g!==B&&C.push({...n[g],x:a}),q!==b&&q!==B&&C.push({...n[q],x:a})}s>0&&B!==b&&C.push(n[B]),C.push(l),d=H,o=0,y=E=f,p=_=b=s}}return C}function cleanDecimatedDataset(n){if(n._decimated){const e=n._data;delete n._decimated,delete n._data,Object.defineProperty(n,"data",{configurable:!0,enumerable:!0,writable:!0,value:e})}}function cleanDecimatedData(n){n.data.datasets.forEach(e=>{cleanDecimatedDataset(e)})}function getStartAndCountOfVisiblePointsSimplified(n,e){const t=e.length;let r=0,a;const{iScale:o}=n,{min:s,max:l,minDefined:c,maxDefined:f}=o.getUserBounds();return c&&(r=_limitValue(_lookupByKey(e,o.axis,s).lo,0,t-1)),f?a=_limitValue(_lookupByKey(e,o.axis,l).hi+1,r,t)-r:a=t-r,{start:r,count:a}}var plugin_decimation={id:"decimation",defaults:{algorithm:"min-max",enabled:!1},beforeElementsUpdate:(n,e,t)=>{if(!t.enabled){cleanDecimatedData(n);return}const r=n.width;n.data.datasets.forEach((a,o)=>{const{_data:s,indexAxis:l}=a,c=n.getDatasetMeta(o),f=s||a.data;if(resolve([l,n.options.indexAxis])==="y"||!c.controller.supportsDecimation)return;const d=n.scales[c.xAxisID];if(d.type!=="linear"&&d.type!=="time"||n.options.parsing)return;let{start:p,count:_}=getStartAndCountOfVisiblePointsSimplified(c,f);const b=t.threshold||4*r;if(_<=b){cleanDecimatedDataset(a);return}isNullOrUndef(s)&&(a._data=f,delete a.data,Object.defineProperty(a,"data",{configurable:!0,enumerable:!0,get:function(){return this._decimated},set:function(E){this._data=E}}));let y;switch(t.algorithm){case"lttb":y=lttbDecimation(f,p,_,r,t);break;case"min-max":y=minMaxDecimation(f,p,_,r);break;default:throw new Error(`Unsupported decimation algorithm '${t.algorithm}'`)}a._decimated=y})},destroy(n){cleanDecimatedData(n)}};function _segments(n,e,t){const r=n.segments,a=n.points,o=e.points,s=[];for(const l of r){let{start:c,end:f}=l;f=_findSegmentEnd(c,f,a);const d=_getBounds(t,a[c],a[f],l.loop);if(!e.segments){s.push({source:l,target:d,start:a[c],end:a[f]});continue}const p=_boundSegments(e,d);for(const _ of p){const b=_getBounds(t,o[_.start],o[_.end],_.loop),y=_boundSegment(l,a,b);for(const E of y)s.push({source:E,target:_,start:{[t]:_getEdge(d,b,"start",Math.max)},end:{[t]:_getEdge(d,b,"end",Math.min)}})}}return s}function _getBounds(n,e,t,r){if(r)return;let a=e[n],o=t[n];return n==="angle"&&(a=_normalizeAngle(a),o=_normalizeAngle(o)),{property:n,start:a,end:o}}function _pointsFromSegments(n,e){const{x:t=null,y:r=null}=n||{},a=e.points,o=[];return e.segments.forEach(({start:s,end:l})=>{l=_findSegmentEnd(s,l,a);const c=a[s],f=a[l];r!==null?(o.push({x:c.x,y:r}),o.push({x:f.x,y:r})):t!==null&&(o.push({x:t,y:c.y}),o.push({x:t,y:f.y}))}),o}function _findSegmentEnd(n,e,t){for(;e>n;e--){const r=t[e];if(!isNaN(r.x)&&!isNaN(r.y))break}return e}function _getEdge(n,e,t,r){return n&&e?r(n[t],e[t]):n?n[t]:e?e[t]:0}function _createBoundaryLine(n,e){let t=[],r=!1;return isArray(n)?(r=!0,t=n):t=_pointsFromSegments(n,e),t.length?new LineElement({points:t,options:{tension:0},_loop:r,_fullLoop:r}):null}function _shouldApplyFill(n){return n&&n.fill!==!1}function _resolveTarget(n,e,t){let a=n[e].fill;const o=[e];let s;if(!t)return a;for(;a!==!1&&o.indexOf(a)===-1;){if(!isNumberFinite(a))return a;if(s=n[a],!s)return!1;if(s.visible)return a;o.push(a),a=s.fill}return!1}function _decodeFill(n,e,t){const r=parseFillOption(n);if(isObject(r))return isNaN(r.value)?!1:r;let a=parseFloat(r);return isNumberFinite(a)&&Math.floor(a)===a?decodeTargetIndex(r[0],e,a,t):["origin","start","end","stack","shape"].indexOf(r)>=0&&r}function decodeTargetIndex(n,e,t,r){return(n==="-"||n==="+")&&(t=e+t),t===e||t<0||t>=r?!1:t}function _getTargetPixel(n,e){let t=null;return n==="start"?t=e.bottom:n==="end"?t=e.top:isObject(n)?t=e.getPixelForValue(n.value):e.getBasePixel&&(t=e.getBasePixel()),t}function _getTargetValue(n,e,t){let r;return n==="start"?r=t:n==="end"?r=e.options.reverse?e.min:e.max:isObject(n)?r=n.value:r=e.getBaseValue(),r}function parseFillOption(n){const e=n.options,t=e.fill;let r=valueOrDefault(t&&t.target,t);return r===void 0&&(r=!!e.backgroundColor),r===!1||r===null?!1:r===!0?"origin":r}function _buildStackLine(n){const{scale:e,index:t,line:r}=n,a=[],o=r.segments,s=r.points,l=getLinesBelow(e,t);l.push(_createBoundaryLine({x:null,y:e.bottom},r));for(let c=0;c<o.length;c++){const f=o[c];for(let d=f.start;d<=f.end;d++)addPointsBelow(a,s[d],l)}return new LineElement({points:a,options:{}})}function getLinesBelow(n,e){const t=[],r=n.getMatchingVisibleMetas("line");for(let a=0;a<r.length;a++){const o=r[a];if(o.index===e)break;o.hidden||t.unshift(o.dataset)}return t}function addPointsBelow(n,e,t){const r=[];for(let a=0;a<t.length;a++){const o=t[a],{first:s,last:l,point:c}=findPoint(o,e,"x");if(!(!c||s&&l)){if(s)r.unshift(c);else if(n.push(c),!l)break}}n.push(...r)}function findPoint(n,e,t){const r=n.interpolate(e,t);if(!r)return{};const a=r[t],o=n.segments,s=n.points;let l=!1,c=!1;for(let f=0;f<o.length;f++){const d=o[f],p=s[d.start][t],_=s[d.end][t];if(_isBetween(a,p,_)){l=a===p,c=a===_;break}}return{first:l,last:c,point:r}}class simpleArc{constructor(e){this.x=e.x,this.y=e.y,this.radius=e.radius}pathSegment(e,t,r){const{x:a,y:o,radius:s}=this;return t=t||{start:0,end:TAU},e.arc(a,o,s,t.end,t.start,!0),!r.bounds}interpolate(e){const{x:t,y:r,radius:a}=this,o=e.angle;return{x:t+Math.cos(o)*a,y:r+Math.sin(o)*a,angle:o}}}function _getTarget(n){const{chart:e,fill:t,line:r}=n;if(isNumberFinite(t))return getLineByIndex(e,t);if(t==="stack")return _buildStackLine(n);if(t==="shape")return!0;const a=computeBoundary(n);return a instanceof simpleArc?a:_createBoundaryLine(a,r)}function getLineByIndex(n,e){const t=n.getDatasetMeta(e);return t&&n.isDatasetVisible(e)?t.dataset:null}function computeBoundary(n){return(n.scale||{}).getPointPositionForValue?computeCircularBoundary(n):computeLinearBoundary(n)}function computeLinearBoundary(n){const{scale:e={},fill:t}=n,r=_getTargetPixel(t,e);if(isNumberFinite(r)){const a=e.isHorizontal();return{x:a?r:null,y:a?null:r}}return null}function computeCircularBoundary(n){const{scale:e,fill:t}=n,r=e.options,a=e.getLabels().length,o=r.reverse?e.max:e.min,s=_getTargetValue(t,e,o),l=[];if(r.grid.circular){const c=e.getPointPositionForValue(0,o);return new simpleArc({x:c.x,y:c.y,radius:e.getDistanceFromCenterForValue(s)})}for(let c=0;c<a;++c)l.push(e.getPointPositionForValue(c,s));return l}function _drawfill(n,e,t){const r=_getTarget(e),{chart:a,index:o,line:s,scale:l,axis:c}=e,f=s.options,d=f.fill,p=f.backgroundColor,{above:_=p,below:b=p}=d||{},y=a.getDatasetMeta(o),E=getDatasetClipArea(a,y);r&&s.points.length&&(clipArea(n,t),doFill(n,{line:s,target:r,above:_,below:b,area:t,scale:l,axis:c,clip:E}),unclipArea(n))}function doFill(n,e){const{line:t,target:r,above:a,below:o,area:s,scale:l,clip:c}=e,f=t._loop?"angle":e.axis;n.save();let d=o;o!==a&&(f==="x"?(clipVertical(n,r,s.top),fill(n,{line:t,target:r,color:a,scale:l,property:f,clip:c}),n.restore(),n.save(),clipVertical(n,r,s.bottom)):f==="y"&&(clipHorizontal(n,r,s.left),fill(n,{line:t,target:r,color:o,scale:l,property:f,clip:c}),n.restore(),n.save(),clipHorizontal(n,r,s.right),d=a)),fill(n,{line:t,target:r,color:d,scale:l,property:f,clip:c}),n.restore()}function clipVertical(n,e,t){const{segments:r,points:a}=e;let o=!0,s=!1;n.beginPath();for(const l of r){const{start:c,end:f}=l,d=a[c],p=a[_findSegmentEnd(c,f,a)];o?(n.moveTo(d.x,d.y),o=!1):(n.lineTo(d.x,t),n.lineTo(d.x,d.y)),s=!!e.pathSegment(n,l,{move:s}),s?n.closePath():n.lineTo(p.x,t)}n.lineTo(e.first().x,t),n.closePath(),n.clip()}function clipHorizontal(n,e,t){const{segments:r,points:a}=e;let o=!0,s=!1;n.beginPath();for(const l of r){const{start:c,end:f}=l,d=a[c],p=a[_findSegmentEnd(c,f,a)];o?(n.moveTo(d.x,d.y),o=!1):(n.lineTo(t,d.y),n.lineTo(d.x,d.y)),s=!!e.pathSegment(n,l,{move:s}),s?n.closePath():n.lineTo(t,p.y)}n.lineTo(t,e.first().y),n.closePath(),n.clip()}function fill(n,e){const{line:t,target:r,property:a,color:o,scale:s,clip:l}=e,c=_segments(t,r,a);for(const{source:f,target:d,start:p,end:_}of c){const{style:{backgroundColor:b=o}={}}=f,y=r!==!0;n.save(),n.fillStyle=b,clipBounds(n,s,l,y&&_getBounds(a,p,_)),n.beginPath();const E=!!t.pathSegment(n,f);let C;if(y){E?n.closePath():interpolatedLineTo(n,r,_,a);const D=!!r.pathSegment(n,d,{move:E,reverse:!0});C=E&&D,C||interpolatedLineTo(n,r,p,a)}n.closePath(),n.fill(C?"evenodd":"nonzero"),n.restore()}}function clipBounds(n,e,t,r){const a=e.chart.chartArea,{property:o,start:s,end:l}=r||{};if(o==="x"||o==="y"){let c,f,d,p;o==="x"?(c=s,f=a.top,d=l,p=a.bottom):(c=a.left,f=s,d=a.right,p=l),n.beginPath(),t&&(c=Math.max(c,t.left),d=Math.min(d,t.right),f=Math.max(f,t.top),p=Math.min(p,t.bottom)),n.rect(c,f,d-c,p-f),n.clip()}}function interpolatedLineTo(n,e,t,r){const a=e.interpolate(t,r);a&&n.lineTo(a.x,a.y)}var index={id:"filler",afterDatasetsUpdate(n,e,t){const r=(n.data.datasets||[]).length,a=[];let o,s,l,c;for(s=0;s<r;++s)o=n.getDatasetMeta(s),l=o.dataset,c=null,l&&l.options&&l instanceof LineElement&&(c={visible:n.isDatasetVisible(s),index:s,fill:_decodeFill(l,s,r),chart:n,axis:o.controller.options.indexAxis,scale:o.vScale,line:l}),o.$filler=c,a.push(c);for(s=0;s<r;++s)c=a[s],!(!c||c.fill===!1)&&(c.fill=_resolveTarget(a,s,t.propagate))},beforeDraw(n,e,t){const r=t.drawTime==="beforeDraw",a=n.getSortedVisibleDatasetMetas(),o=n.chartArea;for(let s=a.length-1;s>=0;--s){const l=a[s].$filler;l&&(l.line.updateControlPoints(o,l.axis),r&&l.fill&&_drawfill(n.ctx,l,o))}},beforeDatasetsDraw(n,e,t){if(t.drawTime!=="beforeDatasetsDraw")return;const r=n.getSortedVisibleDatasetMetas();for(let a=r.length-1;a>=0;--a){const o=r[a].$filler;_shouldApplyFill(o)&&_drawfill(n.ctx,o,n.chartArea)}},beforeDatasetDraw(n,e,t){const r=e.meta.$filler;!_shouldApplyFill(r)||t.drawTime!=="beforeDatasetDraw"||_drawfill(n.ctx,r,n.chartArea)},defaults:{propagate:!0,drawTime:"beforeDatasetDraw"}};const getBoxSize=(n,e)=>{let{boxHeight:t=e,boxWidth:r=e}=n;return n.usePointStyle&&(t=Math.min(t,e),r=n.pointStyleWidth||Math.min(r,e)),{boxWidth:r,boxHeight:t,itemHeight:Math.max(e,t)}},itemsEqual=(n,e)=>n!==null&&e!==null&&n.datasetIndex===e.datasetIndex&&n.index===e.index;class Legend extends Element$1{constructor(e){super(),this._added=!1,this.legendHitBoxes=[],this._hoveredItem=null,this.doughnutMode=!1,this.chart=e.chart,this.options=e.options,this.ctx=e.ctx,this.legendItems=void 0,this.columnSizes=void 0,this.lineWidths=void 0,this.maxHeight=void 0,this.maxWidth=void 0,this.top=void 0,this.bottom=void 0,this.left=void 0,this.right=void 0,this.height=void 0,this.width=void 0,this._margins=void 0,this.position=void 0,this.weight=void 0,this.fullSize=void 0}update(e,t,r){this.maxWidth=e,this.maxHeight=t,this._margins=r,this.setDimensions(),this.buildLabels(),this.fit()}setDimensions(){this.isHorizontal()?(this.width=this.maxWidth,this.left=this._margins.left,this.right=this.width):(this.height=this.maxHeight,this.top=this._margins.top,this.bottom=this.height)}buildLabels(){const e=this.options.labels||{};let t=callback(e.generateLabels,[this.chart],this)||[];e.filter&&(t=t.filter(r=>e.filter(r,this.chart.data))),e.sort&&(t=t.sort((r,a)=>e.sort(r,a,this.chart.data))),this.options.reverse&&t.reverse(),this.legendItems=t}fit(){const{options:e,ctx:t}=this;if(!e.display){this.width=this.height=0;return}const r=e.labels,a=toFont(r.font),o=a.size,s=this._computeTitleHeight(),{boxWidth:l,itemHeight:c}=getBoxSize(r,o);let f,d;t.font=a.string,this.isHorizontal()?(f=this.maxWidth,d=this._fitRows(s,o,l,c)+10):(d=this.maxHeight,f=this._fitCols(s,a,l,c)+10),this.width=Math.min(f,e.maxWidth||this.maxWidth),this.height=Math.min(d,e.maxHeight||this.maxHeight)}_fitRows(e,t,r,a){const{ctx:o,maxWidth:s,options:{labels:{padding:l}}}=this,c=this.legendHitBoxes=[],f=this.lineWidths=[0],d=a+l;let p=e;o.textAlign="left",o.textBaseline="middle";let _=-1,b=-d;return this.legendItems.forEach((y,E)=>{const C=r+t/2+o.measureText(y.text).width;(E===0||f[f.length-1]+C+2*l>s)&&(p+=d,f[f.length-(E>0?0:1)]=0,b+=d,_++),c[E]={left:0,top:b,row:_,width:C,height:a},f[f.length-1]+=C+l}),p}_fitCols(e,t,r,a){const{ctx:o,maxHeight:s,options:{labels:{padding:l}}}=this,c=this.legendHitBoxes=[],f=this.columnSizes=[],d=s-e;let p=l,_=0,b=0,y=0,E=0;return this.legendItems.forEach((C,D)=>{const{itemWidth:M,itemHeight:F}=calculateItemSize(r,t,o,C,a);D>0&&b+F+2*l>d&&(p+=_+l,f.push({width:_,height:b}),y+=_+l,E++,_=b=0),c[D]={left:y,top:b,col:E,width:M,height:F},_=Math.max(_,M),b+=F+l}),p+=_,f.push({width:_,height:b}),p}adjustHitBoxes(){if(!this.options.display)return;const e=this._computeTitleHeight(),{legendHitBoxes:t,options:{align:r,labels:{padding:a},rtl:o}}=this,s=getRtlAdapter(o,this.left,this.width);if(this.isHorizontal()){let l=0,c=_alignStartEnd(r,this.left+a,this.right-this.lineWidths[l]);for(const f of t)l!==f.row&&(l=f.row,c=_alignStartEnd(r,this.left+a,this.right-this.lineWidths[l])),f.top+=this.top+e+a,f.left=s.leftForLtr(s.x(c),f.width),c+=f.width+a}else{let l=0,c=_alignStartEnd(r,this.top+e+a,this.bottom-this.columnSizes[l].height);for(const f of t)f.col!==l&&(l=f.col,c=_alignStartEnd(r,this.top+e+a,this.bottom-this.columnSizes[l].height)),f.top=c,f.left+=this.left+a,f.left=s.leftForLtr(s.x(f.left),f.width),c+=f.height+a}}isHorizontal(){return this.options.position==="top"||this.options.position==="bottom"}draw(){if(this.options.display){const e=this.ctx;clipArea(e,this),this._draw(),unclipArea(e)}}_draw(){const{options:e,columnSizes:t,lineWidths:r,ctx:a}=this,{align:o,labels:s}=e,l=defaults.color,c=getRtlAdapter(e.rtl,this.left,this.width),f=toFont(s.font),{padding:d}=s,p=f.size,_=p/2;let b;this.drawTitle(),a.textAlign=c.textAlign("left"),a.textBaseline="middle",a.lineWidth=.5,a.font=f.string;const{boxWidth:y,boxHeight:E,itemHeight:C}=getBoxSize(s,p),D=function(B,g,q){if(isNaN(y)||y<=0||isNaN(E)||E<0)return;a.save();const G=valueOrDefault(q.lineWidth,1);if(a.fillStyle=valueOrDefault(q.fillStyle,l),a.lineCap=valueOrDefault(q.lineCap,"butt"),a.lineDashOffset=valueOrDefault(q.lineDashOffset,0),a.lineJoin=valueOrDefault(q.lineJoin,"miter"),a.lineWidth=G,a.strokeStyle=valueOrDefault(q.strokeStyle,l),a.setLineDash(valueOrDefault(q.lineDash,[])),s.usePointStyle){const Z={radius:E*Math.SQRT2/2,pointStyle:q.pointStyle,rotation:q.rotation,borderWidth:G},te=c.xPlus(B,y/2),ne=g+_;drawPointLegend(a,Z,te,ne,s.pointStyleWidth&&y)}else{const Z=g+Math.max((p-E)/2,0),te=c.leftForLtr(B,y),ne=toTRBLCorners(q.borderRadius);a.beginPath(),Object.values(ne).some(Q=>Q!==0)?addRoundedRectPath(a,{x:te,y:Z,w:y,h:E,radius:ne}):a.rect(te,Z,y,E),a.fill(),G!==0&&a.stroke()}a.restore()},M=function(B,g,q){renderText(a,q.text,B,g+C/2,f,{strikethrough:q.hidden,textAlign:c.textAlign(q.textAlign)})},F=this.isHorizontal(),P=this._computeTitleHeight();F?b={x:_alignStartEnd(o,this.left+d,this.right-r[0]),y:this.top+d+P,line:0}:b={x:this.left+d,y:_alignStartEnd(o,this.top+P+d,this.bottom-t[0].height),line:0},overrideTextDirection(this.ctx,e.textDirection);const H=C+d;this.legendItems.forEach((B,g)=>{a.strokeStyle=B.fontColor,a.fillStyle=B.fontColor;const q=a.measureText(B.text).width,G=c.textAlign(B.textAlign||(B.textAlign=s.textAlign)),Z=y+_+q;let te=b.x,ne=b.y;c.setWidth(this.width),F?g>0&&te+Z+d>this.right&&(ne=b.y+=H,b.line++,te=b.x=_alignStartEnd(o,this.left+d,this.right-r[b.line])):g>0&&ne+H>this.bottom&&(te=b.x=te+t[b.line].width+d,b.line++,ne=b.y=_alignStartEnd(o,this.top+P+d,this.bottom-t[b.line].height));const Q=c.x(te);if(D(Q,ne,B),te=_textX(G,te+y+_,F?te+Z:this.right,e.rtl),M(c.x(te),ne,B),F)b.x+=Z+d;else if(typeof B.text!="string"){const Ee=f.lineHeight;b.y+=calculateLegendItemHeight(B,Ee)+d}else b.y+=H}),restoreTextDirection(this.ctx,e.textDirection)}drawTitle(){const e=this.options,t=e.title,r=toFont(t.font),a=toPadding(t.padding);if(!t.display)return;const o=getRtlAdapter(e.rtl,this.left,this.width),s=this.ctx,l=t.position,c=r.size/2,f=a.top+c;let d,p=this.left,_=this.width;if(this.isHorizontal())_=Math.max(...this.lineWidths),d=this.top+f,p=_alignStartEnd(e.align,p,this.right-_);else{const y=this.columnSizes.reduce((E,C)=>Math.max(E,C.height),0);d=f+_alignStartEnd(e.align,this.top,this.bottom-y-e.labels.padding-this._computeTitleHeight())}const b=_alignStartEnd(l,p,p+_);s.textAlign=o.textAlign(_toLeftRightCenter(l)),s.textBaseline="middle",s.strokeStyle=t.color,s.fillStyle=t.color,s.font=r.string,renderText(s,t.text,b,d,r)}_computeTitleHeight(){const e=this.options.title,t=toFont(e.font),r=toPadding(e.padding);return e.display?t.lineHeight+r.height:0}_getLegendItemAt(e,t){let r,a,o;if(_isBetween(e,this.left,this.right)&&_isBetween(t,this.top,this.bottom)){for(o=this.legendHitBoxes,r=0;r<o.length;++r)if(a=o[r],_isBetween(e,a.left,a.left+a.width)&&_isBetween(t,a.top,a.top+a.height))return this.legendItems[r]}return null}handleEvent(e){const t=this.options;if(!isListened(e.type,t))return;const r=this._getLegendItemAt(e.x,e.y);if(e.type==="mousemove"||e.type==="mouseout"){const a=this._hoveredItem,o=itemsEqual(a,r);a&&!o&&callback(t.onLeave,[e,a,this],this),this._hoveredItem=r,r&&!o&&callback(t.onHover,[e,r,this],this)}else r&&callback(t.onClick,[e,r,this],this)}}function calculateItemSize(n,e,t,r,a){const o=calculateItemWidth(r,n,e,t),s=calculateItemHeight(a,r,e.lineHeight);return{itemWidth:o,itemHeight:s}}function calculateItemWidth(n,e,t,r){let a=n.text;return a&&typeof a!="string"&&(a=a.reduce((o,s)=>o.length>s.length?o:s)),e+t.size/2+r.measureText(a).width}function calculateItemHeight(n,e,t){let r=n;return typeof e.text!="string"&&(r=calculateLegendItemHeight(e,t)),r}function calculateLegendItemHeight(n,e){const t=n.text?n.text.length:0;return e*t}function isListened(n,e){return!!((n==="mousemove"||n==="mouseout")&&(e.onHover||e.onLeave)||e.onClick&&(n==="click"||n==="mouseup"))}var plugin_legend={id:"legend",_element:Legend,start(n,e,t){const r=n.legend=new Legend({ctx:n.ctx,options:t,chart:n});layouts.configure(n,r,t),layouts.addBox(n,r)},stop(n){layouts.removeBox(n,n.legend),delete n.legend},beforeUpdate(n,e,t){const r=n.legend;layouts.configure(n,r,t),r.options=t},afterUpdate(n){const e=n.legend;e.buildLabels(),e.adjustHitBoxes()},afterEvent(n,e){e.replay||n.legend.handleEvent(e.event)},defaults:{display:!0,position:"top",align:"center",fullSize:!0,reverse:!1,weight:1e3,onClick(n,e,t){const r=e.datasetIndex,a=t.chart;a.isDatasetVisible(r)?(a.hide(r),e.hidden=!0):(a.show(r),e.hidden=!1)},onHover:null,onLeave:null,labels:{color:n=>n.chart.options.color,boxWidth:40,padding:10,generateLabels(n){const e=n.data.datasets,{labels:{usePointStyle:t,pointStyle:r,textAlign:a,color:o,useBorderRadius:s,borderRadius:l}}=n.legend.options;return n._getSortedDatasetMetas().map(c=>{const f=c.controller.getStyle(t?0:void 0),d=toPadding(f.borderWidth);return{text:e[c.index].label,fillStyle:f.backgroundColor,fontColor:o,hidden:!c.visible,lineCap:f.borderCapStyle,lineDash:f.borderDash,lineDashOffset:f.borderDashOffset,lineJoin:f.borderJoinStyle,lineWidth:(d.width+d.height)/4,strokeStyle:f.borderColor,pointStyle:r||f.pointStyle,rotation:f.rotation,textAlign:a||f.textAlign,borderRadius:s&&(l||f.borderRadius),datasetIndex:c.index}},this)}},title:{color:n=>n.chart.options.color,display:!1,position:"center",text:""}},descriptors:{_scriptable:n=>!n.startsWith("on"),labels:{_scriptable:n=>!["generateLabels","filter","sort"].includes(n)}}};class Title extends Element$1{constructor(e){super(),this.chart=e.chart,this.options=e.options,this.ctx=e.ctx,this._padding=void 0,this.top=void 0,this.bottom=void 0,this.left=void 0,this.right=void 0,this.width=void 0,this.height=void 0,this.position=void 0,this.weight=void 0,this.fullSize=void 0}update(e,t){const r=this.options;if(this.left=0,this.top=0,!r.display){this.width=this.height=this.right=this.bottom=0;return}this.width=this.right=e,this.height=this.bottom=t;const a=isArray(r.text)?r.text.length:1;this._padding=toPadding(r.padding);const o=a*toFont(r.font).lineHeight+this._padding.height;this.isHorizontal()?this.height=o:this.width=o}isHorizontal(){const e=this.options.position;return e==="top"||e==="bottom"}_drawArgs(e){const{top:t,left:r,bottom:a,right:o,options:s}=this,l=s.align;let c=0,f,d,p;return this.isHorizontal()?(d=_alignStartEnd(l,r,o),p=t+e,f=o-r):(s.position==="left"?(d=r+e,p=_alignStartEnd(l,a,t),c=PI*-.5):(d=o-e,p=_alignStartEnd(l,t,a),c=PI*.5),f=a-t),{titleX:d,titleY:p,maxWidth:f,rotation:c}}draw(){const e=this.ctx,t=this.options;if(!t.display)return;const r=toFont(t.font),o=r.lineHeight/2+this._padding.top,{titleX:s,titleY:l,maxWidth:c,rotation:f}=this._drawArgs(o);renderText(e,t.text,0,0,r,{color:t.color,maxWidth:c,rotation:f,textAlign:_toLeftRightCenter(t.align),textBaseline:"middle",translation:[s,l]})}}function createTitle(n,e){const t=new Title({ctx:n.ctx,options:e,chart:n});layouts.configure(n,t,e),layouts.addBox(n,t),n.titleBlock=t}var plugin_title={id:"title",_element:Title,start(n,e,t){createTitle(n,t)},stop(n){const e=n.titleBlock;layouts.removeBox(n,e),delete n.titleBlock},beforeUpdate(n,e,t){const r=n.titleBlock;layouts.configure(n,r,t),r.options=t},defaults:{align:"center",display:!1,font:{weight:"bold"},fullSize:!0,padding:10,position:"top",text:"",weight:2e3},defaultRoutes:{color:"color"},descriptors:{_scriptable:!0,_indexable:!1}};const map=new WeakMap;var plugin_subtitle={id:"subtitle",start(n,e,t){const r=new Title({ctx:n.ctx,options:t,chart:n});layouts.configure(n,r,t),layouts.addBox(n,r),map.set(n,r)},stop(n){layouts.removeBox(n,map.get(n)),map.delete(n)},beforeUpdate(n,e,t){const r=map.get(n);layouts.configure(n,r,t),r.options=t},defaults:{align:"center",display:!1,font:{weight:"normal"},fullSize:!0,padding:0,position:"top",text:"",weight:1500},defaultRoutes:{color:"color"},descriptors:{_scriptable:!0,_indexable:!1}};const positioners={average(n){if(!n.length)return!1;let e,t,r=new Set,a=0,o=0;for(e=0,t=n.length;e<t;++e){const l=n[e].element;if(l&&l.hasValue()){const c=l.tooltipPosition();r.add(c.x),a+=c.y,++o}}return o===0||r.size===0?!1:{x:[...r].reduce((l,c)=>l+c)/r.size,y:a/o}},nearest(n,e){if(!n.length)return!1;let t=e.x,r=e.y,a=Number.POSITIVE_INFINITY,o,s,l;for(o=0,s=n.length;o<s;++o){const c=n[o].element;if(c&&c.hasValue()){const f=c.getCenterPoint(),d=distanceBetweenPoints(e,f);d<a&&(a=d,l=c)}}if(l){const c=l.tooltipPosition();t=c.x,r=c.y}return{x:t,y:r}}};function pushOrConcat(n,e){return e&&(isArray(e)?Array.prototype.push.apply(n,e):n.push(e)),n}function splitNewlines(n){return(typeof n=="string"||n instanceof String)&&n.indexOf(`
`)>-1?n.split(`
`):n}function createTooltipItem(n,e){const{element:t,datasetIndex:r,index:a}=e,o=n.getDatasetMeta(r).controller,{label:s,value:l}=o.getLabelAndValue(a);return{chart:n,label:s,parsed:o.getParsed(a),raw:n.data.datasets[r].data[a],formattedValue:l,dataset:o.getDataset(),dataIndex:a,datasetIndex:r,element:t}}function getTooltipSize(n,e){const t=n.chart.ctx,{body:r,footer:a,title:o}=n,{boxWidth:s,boxHeight:l}=e,c=toFont(e.bodyFont),f=toFont(e.titleFont),d=toFont(e.footerFont),p=o.length,_=a.length,b=r.length,y=toPadding(e.padding);let E=y.height,C=0,D=r.reduce((P,H)=>P+H.before.length+H.lines.length+H.after.length,0);if(D+=n.beforeBody.length+n.afterBody.length,p&&(E+=p*f.lineHeight+(p-1)*e.titleSpacing+e.titleMarginBottom),D){const P=e.displayColors?Math.max(l,c.lineHeight):c.lineHeight;E+=b*P+(D-b)*c.lineHeight+(D-1)*e.bodySpacing}_&&(E+=e.footerMarginTop+_*d.lineHeight+(_-1)*e.footerSpacing);let M=0;const F=function(P){C=Math.max(C,t.measureText(P).width+M)};return t.save(),t.font=f.string,each(n.title,F),t.font=c.string,each(n.beforeBody.concat(n.afterBody),F),M=e.displayColors?s+2+e.boxPadding:0,each(r,P=>{each(P.before,F),each(P.lines,F),each(P.after,F)}),M=0,t.font=d.string,each(n.footer,F),t.restore(),C+=y.width,{width:C,height:E}}function determineYAlign(n,e){const{y:t,height:r}=e;return t<r/2?"top":t>n.height-r/2?"bottom":"center"}function doesNotFitWithAlign(n,e,t,r){const{x:a,width:o}=r,s=t.caretSize+t.caretPadding;if(n==="left"&&a+o+s>e.width||n==="right"&&a-o-s<0)return!0}function determineXAlign(n,e,t,r){const{x:a,width:o}=t,{width:s,chartArea:{left:l,right:c}}=n;let f="center";return r==="center"?f=a<=(l+c)/2?"left":"right":a<=o/2?f="left":a>=s-o/2&&(f="right"),doesNotFitWithAlign(f,n,e,t)&&(f="center"),f}function determineAlignment(n,e,t){const r=t.yAlign||e.yAlign||determineYAlign(n,t);return{xAlign:t.xAlign||e.xAlign||determineXAlign(n,e,t,r),yAlign:r}}function alignX(n,e){let{x:t,width:r}=n;return e==="right"?t-=r:e==="center"&&(t-=r/2),t}function alignY(n,e,t){let{y:r,height:a}=n;return e==="top"?r+=t:e==="bottom"?r-=a+t:r-=a/2,r}function getBackgroundPoint(n,e,t,r){const{caretSize:a,caretPadding:o,cornerRadius:s}=n,{xAlign:l,yAlign:c}=t,f=a+o,{topLeft:d,topRight:p,bottomLeft:_,bottomRight:b}=toTRBLCorners(s);let y=alignX(e,l);const E=alignY(e,c,f);return c==="center"?l==="left"?y+=f:l==="right"&&(y-=f):l==="left"?y-=Math.max(d,_)+a:l==="right"&&(y+=Math.max(p,b)+a),{x:_limitValue(y,0,r.width-e.width),y:_limitValue(E,0,r.height-e.height)}}function getAlignedX(n,e,t){const r=toPadding(t.padding);return e==="center"?n.x+n.width/2:e==="right"?n.x+n.width-r.right:n.x+r.left}function getBeforeAfterBodyLines(n){return pushOrConcat([],splitNewlines(n))}function createTooltipContext(n,e,t){return createContext(n,{tooltip:e,tooltipItems:t,type:"tooltip"})}function overrideCallbacks(n,e){const t=e&&e.dataset&&e.dataset.tooltip&&e.dataset.tooltip.callbacks;return t?n.override(t):n}const defaultCallbacks={beforeTitle:noop,title(n){if(n.length>0){const e=n[0],t=e.chart.data.labels,r=t?t.length:0;if(this&&this.options&&this.options.mode==="dataset")return e.dataset.label||"";if(e.label)return e.label;if(r>0&&e.dataIndex<r)return t[e.dataIndex]}return""},afterTitle:noop,beforeBody:noop,beforeLabel:noop,label(n){if(this&&this.options&&this.options.mode==="dataset")return n.label+": "+n.formattedValue||n.formattedValue;let e=n.dataset.label||"";e&&(e+=": ");const t=n.formattedValue;return isNullOrUndef(t)||(e+=t),e},labelColor(n){const t=n.chart.getDatasetMeta(n.datasetIndex).controller.getStyle(n.dataIndex);return{borderColor:t.borderColor,backgroundColor:t.backgroundColor,borderWidth:t.borderWidth,borderDash:t.borderDash,borderDashOffset:t.borderDashOffset,borderRadius:0}},labelTextColor(){return this.options.bodyColor},labelPointStyle(n){const t=n.chart.getDatasetMeta(n.datasetIndex).controller.getStyle(n.dataIndex);return{pointStyle:t.pointStyle,rotation:t.rotation}},afterLabel:noop,afterBody:noop,beforeFooter:noop,footer:noop,afterFooter:noop};function invokeCallbackWithFallback(n,e,t,r){const a=n[e].call(t,r);return typeof a>"u"?defaultCallbacks[e].call(t,r):a}class Tooltip extends Element$1{static positioners=positioners;constructor(e){super(),this.opacity=0,this._active=[],this._eventPosition=void 0,this._size=void 0,this._cachedAnimations=void 0,this._tooltipItems=[],this.$animations=void 0,this.$context=void 0,this.chart=e.chart,this.options=e.options,this.dataPoints=void 0,this.title=void 0,this.beforeBody=void 0,this.body=void 0,this.afterBody=void 0,this.footer=void 0,this.xAlign=void 0,this.yAlign=void 0,this.x=void 0,this.y=void 0,this.height=void 0,this.width=void 0,this.caretX=void 0,this.caretY=void 0,this.labelColors=void 0,this.labelPointStyles=void 0,this.labelTextColors=void 0}initialize(e){this.options=e,this._cachedAnimations=void 0,this.$context=void 0}_resolveAnimations(){const e=this._cachedAnimations;if(e)return e;const t=this.chart,r=this.options.setContext(this.getContext()),a=r.enabled&&t.options.animation&&r.animations,o=new Animations(this.chart,a);return a._cacheable&&(this._cachedAnimations=Object.freeze(o)),o}getContext(){return this.$context||(this.$context=createTooltipContext(this.chart.getContext(),this,this._tooltipItems))}getTitle(e,t){const{callbacks:r}=t,a=invokeCallbackWithFallback(r,"beforeTitle",this,e),o=invokeCallbackWithFallback(r,"title",this,e),s=invokeCallbackWithFallback(r,"afterTitle",this,e);let l=[];return l=pushOrConcat(l,splitNewlines(a)),l=pushOrConcat(l,splitNewlines(o)),l=pushOrConcat(l,splitNewlines(s)),l}getBeforeBody(e,t){return getBeforeAfterBodyLines(invokeCallbackWithFallback(t.callbacks,"beforeBody",this,e))}getBody(e,t){const{callbacks:r}=t,a=[];return each(e,o=>{const s={before:[],lines:[],after:[]},l=overrideCallbacks(r,o);pushOrConcat(s.before,splitNewlines(invokeCallbackWithFallback(l,"beforeLabel",this,o))),pushOrConcat(s.lines,invokeCallbackWithFallback(l,"label",this,o)),pushOrConcat(s.after,splitNewlines(invokeCallbackWithFallback(l,"afterLabel",this,o))),a.push(s)}),a}getAfterBody(e,t){return getBeforeAfterBodyLines(invokeCallbackWithFallback(t.callbacks,"afterBody",this,e))}getFooter(e,t){const{callbacks:r}=t,a=invokeCallbackWithFallback(r,"beforeFooter",this,e),o=invokeCallbackWithFallback(r,"footer",this,e),s=invokeCallbackWithFallback(r,"afterFooter",this,e);let l=[];return l=pushOrConcat(l,splitNewlines(a)),l=pushOrConcat(l,splitNewlines(o)),l=pushOrConcat(l,splitNewlines(s)),l}_createItems(e){const t=this._active,r=this.chart.data,a=[],o=[],s=[];let l=[],c,f;for(c=0,f=t.length;c<f;++c)l.push(createTooltipItem(this.chart,t[c]));return e.filter&&(l=l.filter((d,p,_)=>e.filter(d,p,_,r))),e.itemSort&&(l=l.sort((d,p)=>e.itemSort(d,p,r))),each(l,d=>{const p=overrideCallbacks(e.callbacks,d);a.push(invokeCallbackWithFallback(p,"labelColor",this,d)),o.push(invokeCallbackWithFallback(p,"labelPointStyle",this,d)),s.push(invokeCallbackWithFallback(p,"labelTextColor",this,d))}),this.labelColors=a,this.labelPointStyles=o,this.labelTextColors=s,this.dataPoints=l,l}update(e,t){const r=this.options.setContext(this.getContext()),a=this._active;let o,s=[];if(!a.length)this.opacity!==0&&(o={opacity:0});else{const l=positioners[r.position].call(this,a,this._eventPosition);s=this._createItems(r),this.title=this.getTitle(s,r),this.beforeBody=this.getBeforeBody(s,r),this.body=this.getBody(s,r),this.afterBody=this.getAfterBody(s,r),this.footer=this.getFooter(s,r);const c=this._size=getTooltipSize(this,r),f=Object.assign({},l,c),d=determineAlignment(this.chart,r,f),p=getBackgroundPoint(r,f,d,this.chart);this.xAlign=d.xAlign,this.yAlign=d.yAlign,o={opacity:1,x:p.x,y:p.y,width:c.width,height:c.height,caretX:l.x,caretY:l.y}}this._tooltipItems=s,this.$context=void 0,o&&this._resolveAnimations().update(this,o),e&&r.external&&r.external.call(this,{chart:this.chart,tooltip:this,replay:t})}drawCaret(e,t,r,a){const o=this.getCaretPosition(e,r,a);t.lineTo(o.x1,o.y1),t.lineTo(o.x2,o.y2),t.lineTo(o.x3,o.y3)}getCaretPosition(e,t,r){const{xAlign:a,yAlign:o}=this,{caretSize:s,cornerRadius:l}=r,{topLeft:c,topRight:f,bottomLeft:d,bottomRight:p}=toTRBLCorners(l),{x:_,y:b}=e,{width:y,height:E}=t;let C,D,M,F,P,H;return o==="center"?(P=b+E/2,a==="left"?(C=_,D=C-s,F=P+s,H=P-s):(C=_+y,D=C+s,F=P-s,H=P+s),M=C):(a==="left"?D=_+Math.max(c,d)+s:a==="right"?D=_+y-Math.max(f,p)-s:D=this.caretX,o==="top"?(F=b,P=F-s,C=D-s,M=D+s):(F=b+E,P=F+s,C=D+s,M=D-s),H=F),{x1:C,x2:D,x3:M,y1:F,y2:P,y3:H}}drawTitle(e,t,r){const a=this.title,o=a.length;let s,l,c;if(o){const f=getRtlAdapter(r.rtl,this.x,this.width);for(e.x=getAlignedX(this,r.titleAlign,r),t.textAlign=f.textAlign(r.titleAlign),t.textBaseline="middle",s=toFont(r.titleFont),l=r.titleSpacing,t.fillStyle=r.titleColor,t.font=s.string,c=0;c<o;++c)t.fillText(a[c],f.x(e.x),e.y+s.lineHeight/2),e.y+=s.lineHeight+l,c+1===o&&(e.y+=r.titleMarginBottom-l)}}_drawColorBox(e,t,r,a,o){const s=this.labelColors[r],l=this.labelPointStyles[r],{boxHeight:c,boxWidth:f}=o,d=toFont(o.bodyFont),p=getAlignedX(this,"left",o),_=a.x(p),b=c<d.lineHeight?(d.lineHeight-c)/2:0,y=t.y+b;if(o.usePointStyle){const E={radius:Math.min(f,c)/2,pointStyle:l.pointStyle,rotation:l.rotation,borderWidth:1},C=a.leftForLtr(_,f)+f/2,D=y+c/2;e.strokeStyle=o.multiKeyBackground,e.fillStyle=o.multiKeyBackground,drawPoint(e,E,C,D),e.strokeStyle=s.borderColor,e.fillStyle=s.backgroundColor,drawPoint(e,E,C,D)}else{e.lineWidth=isObject(s.borderWidth)?Math.max(...Object.values(s.borderWidth)):s.borderWidth||1,e.strokeStyle=s.borderColor,e.setLineDash(s.borderDash||[]),e.lineDashOffset=s.borderDashOffset||0;const E=a.leftForLtr(_,f),C=a.leftForLtr(a.xPlus(_,1),f-2),D=toTRBLCorners(s.borderRadius);Object.values(D).some(M=>M!==0)?(e.beginPath(),e.fillStyle=o.multiKeyBackground,addRoundedRectPath(e,{x:E,y,w:f,h:c,radius:D}),e.fill(),e.stroke(),e.fillStyle=s.backgroundColor,e.beginPath(),addRoundedRectPath(e,{x:C,y:y+1,w:f-2,h:c-2,radius:D}),e.fill()):(e.fillStyle=o.multiKeyBackground,e.fillRect(E,y,f,c),e.strokeRect(E,y,f,c),e.fillStyle=s.backgroundColor,e.fillRect(C,y+1,f-2,c-2))}e.fillStyle=this.labelTextColors[r]}drawBody(e,t,r){const{body:a}=this,{bodySpacing:o,bodyAlign:s,displayColors:l,boxHeight:c,boxWidth:f,boxPadding:d}=r,p=toFont(r.bodyFont);let _=p.lineHeight,b=0;const y=getRtlAdapter(r.rtl,this.x,this.width),E=function(q){t.fillText(q,y.x(e.x+b),e.y+_/2),e.y+=_+o},C=y.textAlign(s);let D,M,F,P,H,B,g;for(t.textAlign=s,t.textBaseline="middle",t.font=p.string,e.x=getAlignedX(this,C,r),t.fillStyle=r.bodyColor,each(this.beforeBody,E),b=l&&C!=="right"?s==="center"?f/2+d:f+2+d:0,P=0,B=a.length;P<B;++P){for(D=a[P],M=this.labelTextColors[P],t.fillStyle=M,each(D.before,E),F=D.lines,l&&F.length&&(this._drawColorBox(t,e,P,y,r),_=Math.max(p.lineHeight,c)),H=0,g=F.length;H<g;++H)E(F[H]),_=p.lineHeight;each(D.after,E)}b=0,_=p.lineHeight,each(this.afterBody,E),e.y-=o}drawFooter(e,t,r){const a=this.footer,o=a.length;let s,l;if(o){const c=getRtlAdapter(r.rtl,this.x,this.width);for(e.x=getAlignedX(this,r.footerAlign,r),e.y+=r.footerMarginTop,t.textAlign=c.textAlign(r.footerAlign),t.textBaseline="middle",s=toFont(r.footerFont),t.fillStyle=r.footerColor,t.font=s.string,l=0;l<o;++l)t.fillText(a[l],c.x(e.x),e.y+s.lineHeight/2),e.y+=s.lineHeight+r.footerSpacing}}drawBackground(e,t,r,a){const{xAlign:o,yAlign:s}=this,{x:l,y:c}=e,{width:f,height:d}=r,{topLeft:p,topRight:_,bottomLeft:b,bottomRight:y}=toTRBLCorners(a.cornerRadius);t.fillStyle=a.backgroundColor,t.strokeStyle=a.borderColor,t.lineWidth=a.borderWidth,t.beginPath(),t.moveTo(l+p,c),s==="top"&&this.drawCaret(e,t,r,a),t.lineTo(l+f-_,c),t.quadraticCurveTo(l+f,c,l+f,c+_),s==="center"&&o==="right"&&this.drawCaret(e,t,r,a),t.lineTo(l+f,c+d-y),t.quadraticCurveTo(l+f,c+d,l+f-y,c+d),s==="bottom"&&this.drawCaret(e,t,r,a),t.lineTo(l+b,c+d),t.quadraticCurveTo(l,c+d,l,c+d-b),s==="center"&&o==="left"&&this.drawCaret(e,t,r,a),t.lineTo(l,c+p),t.quadraticCurveTo(l,c,l+p,c),t.closePath(),t.fill(),a.borderWidth>0&&t.stroke()}_updateAnimationTarget(e){const t=this.chart,r=this.$animations,a=r&&r.x,o=r&&r.y;if(a||o){const s=positioners[e.position].call(this,this._active,this._eventPosition);if(!s)return;const l=this._size=getTooltipSize(this,e),c=Object.assign({},s,this._size),f=determineAlignment(t,e,c),d=getBackgroundPoint(e,c,f,t);(a._to!==d.x||o._to!==d.y)&&(this.xAlign=f.xAlign,this.yAlign=f.yAlign,this.width=l.width,this.height=l.height,this.caretX=s.x,this.caretY=s.y,this._resolveAnimations().update(this,d))}}_willRender(){return!!this.opacity}draw(e){const t=this.options.setContext(this.getContext());let r=this.opacity;if(!r)return;this._updateAnimationTarget(t);const a={width:this.width,height:this.height},o={x:this.x,y:this.y};r=Math.abs(r)<.001?0:r;const s=toPadding(t.padding),l=this.title.length||this.beforeBody.length||this.body.length||this.afterBody.length||this.footer.length;t.enabled&&l&&(e.save(),e.globalAlpha=r,this.drawBackground(o,e,a,t),overrideTextDirection(e,t.textDirection),o.y+=s.top,this.drawTitle(o,e,t),this.drawBody(o,e,t),this.drawFooter(o,e,t),restoreTextDirection(e,t.textDirection),e.restore())}getActiveElements(){return this._active||[]}setActiveElements(e,t){const r=this._active,a=e.map(({datasetIndex:l,index:c})=>{const f=this.chart.getDatasetMeta(l);if(!f)throw new Error("Cannot find a dataset at index "+l);return{datasetIndex:l,element:f.data[c],index:c}}),o=!_elementsEqual(r,a),s=this._positionChanged(a,t);(o||s)&&(this._active=a,this._eventPosition=t,this._ignoreReplayEvents=!0,this.update(!0))}handleEvent(e,t,r=!0){if(t&&this._ignoreReplayEvents)return!1;this._ignoreReplayEvents=!1;const a=this.options,o=this._active||[],s=this._getActiveElements(e,o,t,r),l=this._positionChanged(s,e),c=t||!_elementsEqual(s,o)||l;return c&&(this._active=s,(a.enabled||a.external)&&(this._eventPosition={x:e.x,y:e.y},this.update(!0,t))),c}_getActiveElements(e,t,r,a){const o=this.options;if(e.type==="mouseout")return[];if(!a)return t.filter(l=>this.chart.data.datasets[l.datasetIndex]&&this.chart.getDatasetMeta(l.datasetIndex).controller.getParsed(l.index)!==void 0);const s=this.chart.getElementsAtEventForMode(e,o.mode,o,r);return o.reverse&&s.reverse(),s}_positionChanged(e,t){const{caretX:r,caretY:a,options:o}=this,s=positioners[o.position].call(this,e,t);return s!==!1&&(r!==s.x||a!==s.y)}}var plugin_tooltip={id:"tooltip",_element:Tooltip,positioners,afterInit(n,e,t){t&&(n.tooltip=new Tooltip({chart:n,options:t}))},beforeUpdate(n,e,t){n.tooltip&&n.tooltip.initialize(t)},reset(n,e,t){n.tooltip&&n.tooltip.initialize(t)},afterDraw(n){const e=n.tooltip;if(e&&e._willRender()){const t={tooltip:e};if(n.notifyPlugins("beforeTooltipDraw",{...t,cancelable:!0})===!1)return;e.draw(n.ctx),n.notifyPlugins("afterTooltipDraw",t)}},afterEvent(n,e){if(n.tooltip){const t=e.replay;n.tooltip.handleEvent(e.event,t,e.inChartArea)&&(e.changed=!0)}},defaults:{enabled:!0,external:null,position:"average",backgroundColor:"rgba(0,0,0,0.8)",titleColor:"#fff",titleFont:{weight:"bold"},titleSpacing:2,titleMarginBottom:6,titleAlign:"left",bodyColor:"#fff",bodySpacing:2,bodyFont:{},bodyAlign:"left",footerColor:"#fff",footerSpacing:2,footerMarginTop:6,footerFont:{weight:"bold"},footerAlign:"left",padding:6,caretPadding:2,caretSize:5,cornerRadius:6,boxHeight:(n,e)=>e.bodyFont.size,boxWidth:(n,e)=>e.bodyFont.size,multiKeyBackground:"#fff",displayColors:!0,boxPadding:0,borderColor:"rgba(0,0,0,0)",borderWidth:0,animation:{duration:400,easing:"easeOutQuart"},animations:{numbers:{type:"number",properties:["x","y","width","height","caretX","caretY"]},opacity:{easing:"linear",duration:200}},callbacks:defaultCallbacks},defaultRoutes:{bodyFont:"font",footerFont:"font",titleFont:"font"},descriptors:{_scriptable:n=>n!=="filter"&&n!=="itemSort"&&n!=="external",_indexable:!1,callbacks:{_scriptable:!1,_indexable:!1},animation:{_fallback:!1},animations:{_fallback:"animation"}},additionalOptionScopes:["interaction"]},plugins=Object.freeze({__proto__:null,Colors:plugin_colors,Decimation:plugin_decimation,Filler:index,Legend:plugin_legend,SubTitle:plugin_subtitle,Title:plugin_title,Tooltip:plugin_tooltip});const addIfString=(n,e,t,r)=>(typeof e=="string"?(t=n.push(e)-1,r.unshift({index:t,label:e})):isNaN(e)&&(t=null),t);function findOrAddLabel(n,e,t,r){const a=n.indexOf(e);if(a===-1)return addIfString(n,e,t,r);const o=n.lastIndexOf(e);return a!==o?t:a}const validIndex=(n,e)=>n===null?null:_limitValue(Math.round(n),0,e);function _getLabelForValue(n){const e=this.getLabels();return n>=0&&n<e.length?e[n]:n}class CategoryScale extends Scale{static id="category";static defaults={ticks:{callback:_getLabelForValue}};constructor(e){super(e),this._startValue=void 0,this._valueRange=0,this._addedLabels=[]}init(e){const t=this._addedLabels;if(t.length){const r=this.getLabels();for(const{index:a,label:o}of t)r[a]===o&&r.splice(a,1);this._addedLabels=[]}super.init(e)}parse(e,t){if(isNullOrUndef(e))return null;const r=this.getLabels();return t=isFinite(t)&&r[t]===e?t:findOrAddLabel(r,e,valueOrDefault(t,e),this._addedLabels),validIndex(t,r.length-1)}determineDataLimits(){const{minDefined:e,maxDefined:t}=this.getUserBounds();let{min:r,max:a}=this.getMinMax(!0);this.options.bounds==="ticks"&&(e||(r=0),t||(a=this.getLabels().length-1)),this.min=r,this.max=a}buildTicks(){const e=this.min,t=this.max,r=this.options.offset,a=[];let o=this.getLabels();o=e===0&&t===o.length-1?o:o.slice(e,t+1),this._valueRange=Math.max(o.length-(r?0:1),1),this._startValue=this.min-(r?.5:0);for(let s=e;s<=t;s++)a.push({value:s});return a}getLabelForValue(e){return _getLabelForValue.call(this,e)}configure(){super.configure(),this.isHorizontal()||(this._reversePixels=!this._reversePixels)}getPixelForValue(e){return typeof e!="number"&&(e=this.parse(e)),e===null?NaN:this.getPixelForDecimal((e-this._startValue)/this._valueRange)}getPixelForTick(e){const t=this.ticks;return e<0||e>t.length-1?null:this.getPixelForValue(t[e].value)}getValueForPixel(e){return Math.round(this._startValue+this.getDecimalForPixel(e)*this._valueRange)}getBasePixel(){return this.bottom}}function generateTicks$1(n,e){const t=[],{bounds:a,step:o,min:s,max:l,precision:c,count:f,maxTicks:d,maxDigits:p,includeBounds:_}=n,b=o||1,y=d-1,{min:E,max:C}=e,D=!isNullOrUndef(s),M=!isNullOrUndef(l),F=!isNullOrUndef(f),P=(C-E)/(p+1);let H=niceNum((C-E)/y/b)*b,B,g,q,G;if(H<1e-14&&!D&&!M)return[{value:E},{value:C}];G=Math.ceil(C/H)-Math.floor(E/H),G>y&&(H=niceNum(G*H/y/b)*b),isNullOrUndef(c)||(B=Math.pow(10,c),H=Math.ceil(H*B)/B),a==="ticks"?(g=Math.floor(E/H)*H,q=Math.ceil(C/H)*H):(g=E,q=C),D&&M&&o&&almostWhole((l-s)/o,H/1e3)?(G=Math.round(Math.min((l-s)/H,d)),H=(l-s)/G,g=s,q=l):F?(g=D?s:g,q=M?l:q,G=f-1,H=(q-g)/G):(G=(q-g)/H,almostEquals(G,Math.round(G),H/1e3)?G=Math.round(G):G=Math.ceil(G));const Z=Math.max(_decimalPlaces(H),_decimalPlaces(g));B=Math.pow(10,isNullOrUndef(c)?Z:c),g=Math.round(g*B)/B,q=Math.round(q*B)/B;let te=0;for(D&&(_&&g!==s?(t.push({value:s}),g<s&&te++,almostEquals(Math.round((g+te*H)*B)/B,s,relativeLabelSize(s,P,n))&&te++):g<s&&te++);te<G;++te){const ne=Math.round((g+te*H)*B)/B;if(M&&ne>l)break;t.push({value:ne})}return M&&_&&q!==l?t.length&&almostEquals(t[t.length-1].value,l,relativeLabelSize(l,P,n))?t[t.length-1].value=l:t.push({value:l}):(!M||q===l)&&t.push({value:q}),t}function relativeLabelSize(n,e,{horizontal:t,minRotation:r}){const a=toRadians(r),o=(t?Math.sin(a):Math.cos(a))||.001,s=.75*e*(""+n).length;return Math.min(e/o,s)}class LinearScaleBase extends Scale{constructor(e){super(e),this.start=void 0,this.end=void 0,this._startValue=void 0,this._endValue=void 0,this._valueRange=0}parse(e,t){return isNullOrUndef(e)||(typeof e=="number"||e instanceof Number)&&!isFinite(+e)?null:+e}handleTickRangeOptions(){const{beginAtZero:e}=this.options,{minDefined:t,maxDefined:r}=this.getUserBounds();let{min:a,max:o}=this;const s=c=>a=t?a:c,l=c=>o=r?o:c;if(e){const c=sign(a),f=sign(o);c<0&&f<0?l(0):c>0&&f>0&&s(0)}if(a===o){let c=o===0?1:Math.abs(o*.05);l(o+c),e||s(a-c)}this.min=a,this.max=o}getTickLimit(){const e=this.options.ticks;let{maxTicksLimit:t,stepSize:r}=e,a;return r?(a=Math.ceil(this.max/r)-Math.floor(this.min/r)+1,a>1e3&&(console.warn(`scales.${this.id}.ticks.stepSize: ${r} would result generating up to ${a} ticks. Limiting to 1000.`),a=1e3)):(a=this.computeTickLimit(),t=t||11),t&&(a=Math.min(t,a)),a}computeTickLimit(){return Number.POSITIVE_INFINITY}buildTicks(){const e=this.options,t=e.ticks;let r=this.getTickLimit();r=Math.max(2,r);const a={maxTicks:r,bounds:e.bounds,min:e.min,max:e.max,precision:t.precision,step:t.stepSize,count:t.count,maxDigits:this._maxDigits(),horizontal:this.isHorizontal(),minRotation:t.minRotation||0,includeBounds:t.includeBounds!==!1},o=this._range||this,s=generateTicks$1(a,o);return e.bounds==="ticks"&&_setMinAndMaxByKey(s,this,"value"),e.reverse?(s.reverse(),this.start=this.max,this.end=this.min):(this.start=this.min,this.end=this.max),s}configure(){const e=this.ticks;let t=this.min,r=this.max;if(super.configure(),this.options.offset&&e.length){const a=(r-t)/Math.max(e.length-1,1)/2;t-=a,r+=a}this._startValue=t,this._endValue=r,this._valueRange=r-t}getLabelForValue(e){return formatNumber(e,this.chart.options.locale,this.options.ticks.format)}}class LinearScale extends LinearScaleBase{static id="linear";static defaults={ticks:{callback:Ticks.formatters.numeric}};determineDataLimits(){const{min:e,max:t}=this.getMinMax(!0);this.min=isNumberFinite(e)?e:0,this.max=isNumberFinite(t)?t:1,this.handleTickRangeOptions()}computeTickLimit(){const e=this.isHorizontal(),t=e?this.width:this.height,r=toRadians(this.options.ticks.minRotation),a=(e?Math.sin(r):Math.cos(r))||.001,o=this._resolveTickFontOptions(0);return Math.ceil(t/Math.min(40,o.lineHeight/a))}getPixelForValue(e){return e===null?NaN:this.getPixelForDecimal((e-this._startValue)/this._valueRange)}getValueForPixel(e){return this._startValue+this.getDecimalForPixel(e)*this._valueRange}}const log10Floor=n=>Math.floor(log10(n)),changeExponent=(n,e)=>Math.pow(10,log10Floor(n)+e);function isMajor(n){return n/Math.pow(10,log10Floor(n))===1}function steps(n,e,t){const r=Math.pow(10,t),a=Math.floor(n/r);return Math.ceil(e/r)-a}function startExp(n,e){const t=e-n;let r=log10Floor(t);for(;steps(n,e,r)>10;)r++;for(;steps(n,e,r)<10;)r--;return Math.min(r,log10Floor(n))}function generateTicks(n,{min:e,max:t}){e=finiteOrDefault(n.min,e);const r=[],a=log10Floor(e);let o=startExp(e,t),s=o<0?Math.pow(10,Math.abs(o)):1;const l=Math.pow(10,o),c=a>o?Math.pow(10,a):0,f=Math.round((e-c)*s)/s,d=Math.floor((e-c)/l/10)*l*10;let p=Math.floor((f-d)/Math.pow(10,o)),_=finiteOrDefault(n.min,Math.round((c+d+p*Math.pow(10,o))*s)/s);for(;_<t;)r.push({value:_,major:isMajor(_),significand:p}),p>=10?p=p<15?15:20:p++,p>=20&&(o++,p=2,s=o>=0?1:s),_=Math.round((c+d+p*Math.pow(10,o))*s)/s;const b=finiteOrDefault(n.max,_);return r.push({value:b,major:isMajor(b),significand:p}),r}class LogarithmicScale extends Scale{static id="logarithmic";static defaults={ticks:{callback:Ticks.formatters.logarithmic,major:{enabled:!0}}};constructor(e){super(e),this.start=void 0,this.end=void 0,this._startValue=void 0,this._valueRange=0}parse(e,t){const r=LinearScaleBase.prototype.parse.apply(this,[e,t]);if(r===0){this._zero=!0;return}return isNumberFinite(r)&&r>0?r:null}determineDataLimits(){const{min:e,max:t}=this.getMinMax(!0);this.min=isNumberFinite(e)?Math.max(0,e):null,this.max=isNumberFinite(t)?Math.max(0,t):null,this.options.beginAtZero&&(this._zero=!0),this._zero&&this.min!==this._suggestedMin&&!isNumberFinite(this._userMin)&&(this.min=e===changeExponent(this.min,0)?changeExponent(this.min,-1):changeExponent(this.min,0)),this.handleTickRangeOptions()}handleTickRangeOptions(){const{minDefined:e,maxDefined:t}=this.getUserBounds();let r=this.min,a=this.max;const o=l=>r=e?r:l,s=l=>a=t?a:l;r===a&&(r<=0?(o(1),s(10)):(o(changeExponent(r,-1)),s(changeExponent(a,1)))),r<=0&&o(changeExponent(a,-1)),a<=0&&s(changeExponent(r,1)),this.min=r,this.max=a}buildTicks(){const e=this.options,t={min:this._userMin,max:this._userMax},r=generateTicks(t,this);return e.bounds==="ticks"&&_setMinAndMaxByKey(r,this,"value"),e.reverse?(r.reverse(),this.start=this.max,this.end=this.min):(this.start=this.min,this.end=this.max),r}getLabelForValue(e){return e===void 0?"0":formatNumber(e,this.chart.options.locale,this.options.ticks.format)}configure(){const e=this.min;super.configure(),this._startValue=log10(e),this._valueRange=log10(this.max)-log10(e)}getPixelForValue(e){return(e===void 0||e===0)&&(e=this.min),e===null||isNaN(e)?NaN:this.getPixelForDecimal(e===this.min?0:(log10(e)-this._startValue)/this._valueRange)}getValueForPixel(e){const t=this.getDecimalForPixel(e);return Math.pow(10,this._startValue+t*this._valueRange)}}function getTickBackdropHeight(n){const e=n.ticks;if(e.display&&n.display){const t=toPadding(e.backdropPadding);return valueOrDefault(e.font&&e.font.size,defaults.font.size)+t.height}return 0}function measureLabelSize(n,e,t){return t=isArray(t)?t:[t],{w:_longestText(n,e.string,t),h:t.length*e.lineHeight}}function determineLimits(n,e,t,r,a){return n===r||n===a?{start:e-t/2,end:e+t/2}:n<r||n>a?{start:e-t,end:e}:{start:e,end:e+t}}function fitWithPointLabels(n){const e={l:n.left+n._padding.left,r:n.right-n._padding.right,t:n.top+n._padding.top,b:n.bottom-n._padding.bottom},t=Object.assign({},e),r=[],a=[],o=n._pointLabels.length,s=n.options.pointLabels,l=s.centerPointLabels?PI/o:0;for(let c=0;c<o;c++){const f=s.setContext(n.getPointLabelContext(c));a[c]=f.padding;const d=n.getPointPosition(c,n.drawingArea+a[c],l),p=toFont(f.font),_=measureLabelSize(n.ctx,p,n._pointLabels[c]);r[c]=_;const b=_normalizeAngle(n.getIndexAngle(c)+l),y=Math.round(toDegrees(b)),E=determineLimits(y,d.x,_.w,0,180),C=determineLimits(y,d.y,_.h,90,270);updateLimits(t,e,b,E,C)}n.setCenterPoint(e.l-t.l,t.r-e.r,e.t-t.t,t.b-e.b),n._pointLabelItems=buildPointLabelItems(n,r,a)}function updateLimits(n,e,t,r,a){const o=Math.abs(Math.sin(t)),s=Math.abs(Math.cos(t));let l=0,c=0;r.start<e.l?(l=(e.l-r.start)/o,n.l=Math.min(n.l,e.l-l)):r.end>e.r&&(l=(r.end-e.r)/o,n.r=Math.max(n.r,e.r+l)),a.start<e.t?(c=(e.t-a.start)/s,n.t=Math.min(n.t,e.t-c)):a.end>e.b&&(c=(a.end-e.b)/s,n.b=Math.max(n.b,e.b+c))}function createPointLabelItem(n,e,t){const r=n.drawingArea,{extra:a,additionalAngle:o,padding:s,size:l}=t,c=n.getPointPosition(e,r+a+s,o),f=Math.round(toDegrees(_normalizeAngle(c.angle+HALF_PI))),d=yForAngle(c.y,l.h,f),p=getTextAlignForAngle(f),_=leftForTextAlign(c.x,l.w,p);return{visible:!0,x:c.x,y:d,textAlign:p,left:_,top:d,right:_+l.w,bottom:d+l.h}}function isNotOverlapped(n,e){if(!e)return!0;const{left:t,top:r,right:a,bottom:o}=n;return!(_isPointInArea({x:t,y:r},e)||_isPointInArea({x:t,y:o},e)||_isPointInArea({x:a,y:r},e)||_isPointInArea({x:a,y:o},e))}function buildPointLabelItems(n,e,t){const r=[],a=n._pointLabels.length,o=n.options,{centerPointLabels:s,display:l}=o.pointLabels,c={extra:getTickBackdropHeight(o)/2,additionalAngle:s?PI/a:0};let f;for(let d=0;d<a;d++){c.padding=t[d],c.size=e[d];const p=createPointLabelItem(n,d,c);r.push(p),l==="auto"&&(p.visible=isNotOverlapped(p,f),p.visible&&(f=p))}return r}function getTextAlignForAngle(n){return n===0||n===180?"center":n<180?"left":"right"}function leftForTextAlign(n,e,t){return t==="right"?n-=e:t==="center"&&(n-=e/2),n}function yForAngle(n,e,t){return t===90||t===270?n-=e/2:(t>270||t<90)&&(n-=e),n}function drawPointLabelBox(n,e,t){const{left:r,top:a,right:o,bottom:s}=t,{backdropColor:l}=e;if(!isNullOrUndef(l)){const c=toTRBLCorners(e.borderRadius),f=toPadding(e.backdropPadding);n.fillStyle=l;const d=r-f.left,p=a-f.top,_=o-r+f.width,b=s-a+f.height;Object.values(c).some(y=>y!==0)?(n.beginPath(),addRoundedRectPath(n,{x:d,y:p,w:_,h:b,radius:c}),n.fill()):n.fillRect(d,p,_,b)}}function drawPointLabels(n,e){const{ctx:t,options:{pointLabels:r}}=n;for(let a=e-1;a>=0;a--){const o=n._pointLabelItems[a];if(!o.visible)continue;const s=r.setContext(n.getPointLabelContext(a));drawPointLabelBox(t,s,o);const l=toFont(s.font),{x:c,y:f,textAlign:d}=o;renderText(t,n._pointLabels[a],c,f+l.lineHeight/2,l,{color:s.color,textAlign:d,textBaseline:"middle"})}}function pathRadiusLine(n,e,t,r){const{ctx:a}=n;if(t)a.arc(n.xCenter,n.yCenter,e,0,TAU);else{let o=n.getPointPosition(0,e);a.moveTo(o.x,o.y);for(let s=1;s<r;s++)o=n.getPointPosition(s,e),a.lineTo(o.x,o.y)}}function drawRadiusLine(n,e,t,r,a){const o=n.ctx,s=e.circular,{color:l,lineWidth:c}=e;!s&&!r||!l||!c||t<0||(o.save(),o.strokeStyle=l,o.lineWidth=c,o.setLineDash(a.dash||[]),o.lineDashOffset=a.dashOffset,o.beginPath(),pathRadiusLine(n,t,s,r),o.closePath(),o.stroke(),o.restore())}function createPointLabelContext(n,e,t){return createContext(n,{label:t,index:e,type:"pointLabel"})}class RadialLinearScale extends LinearScaleBase{static id="radialLinear";static defaults={display:!0,animate:!0,position:"chartArea",angleLines:{display:!0,lineWidth:1,borderDash:[],borderDashOffset:0},grid:{circular:!1},startAngle:0,ticks:{showLabelBackdrop:!0,callback:Ticks.formatters.numeric},pointLabels:{backdropColor:void 0,backdropPadding:2,display:!0,font:{size:10},callback(e){return e},padding:5,centerPointLabels:!1}};static defaultRoutes={"angleLines.color":"borderColor","pointLabels.color":"color","ticks.color":"color"};static descriptors={angleLines:{_fallback:"grid"}};constructor(e){super(e),this.xCenter=void 0,this.yCenter=void 0,this.drawingArea=void 0,this._pointLabels=[],this._pointLabelItems=[]}setDimensions(){const e=this._padding=toPadding(getTickBackdropHeight(this.options)/2),t=this.width=this.maxWidth-e.width,r=this.height=this.maxHeight-e.height;this.xCenter=Math.floor(this.left+t/2+e.left),this.yCenter=Math.floor(this.top+r/2+e.top),this.drawingArea=Math.floor(Math.min(t,r)/2)}determineDataLimits(){const{min:e,max:t}=this.getMinMax(!1);this.min=isNumberFinite(e)&&!isNaN(e)?e:0,this.max=isNumberFinite(t)&&!isNaN(t)?t:0,this.handleTickRangeOptions()}computeTickLimit(){return Math.ceil(this.drawingArea/getTickBackdropHeight(this.options))}generateTickLabels(e){LinearScaleBase.prototype.generateTickLabels.call(this,e),this._pointLabels=this.getLabels().map((t,r)=>{const a=callback(this.options.pointLabels.callback,[t,r],this);return a||a===0?a:""}).filter((t,r)=>this.chart.getDataVisibility(r))}fit(){const e=this.options;e.display&&e.pointLabels.display?fitWithPointLabels(this):this.setCenterPoint(0,0,0,0)}setCenterPoint(e,t,r,a){this.xCenter+=Math.floor((e-t)/2),this.yCenter+=Math.floor((r-a)/2),this.drawingArea-=Math.min(this.drawingArea/2,Math.max(e,t,r,a))}getIndexAngle(e){const t=TAU/(this._pointLabels.length||1),r=this.options.startAngle||0;return _normalizeAngle(e*t+toRadians(r))}getDistanceFromCenterForValue(e){if(isNullOrUndef(e))return NaN;const t=this.drawingArea/(this.max-this.min);return this.options.reverse?(this.max-e)*t:(e-this.min)*t}getValueForDistanceFromCenter(e){if(isNullOrUndef(e))return NaN;const t=e/(this.drawingArea/(this.max-this.min));return this.options.reverse?this.max-t:this.min+t}getPointLabelContext(e){const t=this._pointLabels||[];if(e>=0&&e<t.length){const r=t[e];return createPointLabelContext(this.getContext(),e,r)}}getPointPosition(e,t,r=0){const a=this.getIndexAngle(e)-HALF_PI+r;return{x:Math.cos(a)*t+this.xCenter,y:Math.sin(a)*t+this.yCenter,angle:a}}getPointPositionForValue(e,t){return this.getPointPosition(e,this.getDistanceFromCenterForValue(t))}getBasePosition(e){return this.getPointPositionForValue(e||0,this.getBaseValue())}getPointLabelPosition(e){const{left:t,top:r,right:a,bottom:o}=this._pointLabelItems[e];return{left:t,top:r,right:a,bottom:o}}drawBackground(){const{backgroundColor:e,grid:{circular:t}}=this.options;if(e){const r=this.ctx;r.save(),r.beginPath(),pathRadiusLine(this,this.getDistanceFromCenterForValue(this._endValue),t,this._pointLabels.length),r.closePath(),r.fillStyle=e,r.fill(),r.restore()}}drawGrid(){const e=this.ctx,t=this.options,{angleLines:r,grid:a,border:o}=t,s=this._pointLabels.length;let l,c,f;if(t.pointLabels.display&&drawPointLabels(this,s),a.display&&this.ticks.forEach((d,p)=>{if(p!==0||p===0&&this.min<0){c=this.getDistanceFromCenterForValue(d.value);const _=this.getContext(p),b=a.setContext(_),y=o.setContext(_);drawRadiusLine(this,b,c,s,y)}}),r.display){for(e.save(),l=s-1;l>=0;l--){const d=r.setContext(this.getPointLabelContext(l)),{color:p,lineWidth:_}=d;!_||!p||(e.lineWidth=_,e.strokeStyle=p,e.setLineDash(d.borderDash),e.lineDashOffset=d.borderDashOffset,c=this.getDistanceFromCenterForValue(t.reverse?this.min:this.max),f=this.getPointPosition(l,c),e.beginPath(),e.moveTo(this.xCenter,this.yCenter),e.lineTo(f.x,f.y),e.stroke())}e.restore()}}drawBorder(){}drawLabels(){const e=this.ctx,t=this.options,r=t.ticks;if(!r.display)return;const a=this.getIndexAngle(0);let o,s;e.save(),e.translate(this.xCenter,this.yCenter),e.rotate(a),e.textAlign="center",e.textBaseline="middle",this.ticks.forEach((l,c)=>{if(c===0&&this.min>=0&&!t.reverse)return;const f=r.setContext(this.getContext(c)),d=toFont(f.font);if(o=this.getDistanceFromCenterForValue(this.ticks[c].value),f.showLabelBackdrop){e.font=d.string,s=e.measureText(l.label).width,e.fillStyle=f.backdropColor;const p=toPadding(f.backdropPadding);e.fillRect(-s/2-p.left,-o-d.size/2-p.top,s+p.width,d.size+p.height)}renderText(e,l.label,0,-o,d,{color:f.color,strokeColor:f.textStrokeColor,strokeWidth:f.textStrokeWidth})}),e.restore()}drawTitle(){}}const INTERVALS={millisecond:{common:!0,size:1,steps:1e3},second:{common:!0,size:1e3,steps:60},minute:{common:!0,size:6e4,steps:60},hour:{common:!0,size:36e5,steps:24},day:{common:!0,size:864e5,steps:30},week:{common:!1,size:6048e5,steps:4},month:{common:!0,size:2628e6,steps:12},quarter:{common:!1,size:7884e6,steps:4},year:{common:!0,size:3154e7}},UNITS=Object.keys(INTERVALS);function sorter(n,e){return n-e}function parse(n,e){if(isNullOrUndef(e))return null;const t=n._adapter,{parser:r,round:a,isoWeekday:o}=n._parseOpts;let s=e;return typeof r=="function"&&(s=r(s)),isNumberFinite(s)||(s=typeof r=="string"?t.parse(s,r):t.parse(s)),s===null?null:(a&&(s=a==="week"&&(isNumber(o)||o===!0)?t.startOf(s,"isoWeek",o):t.startOf(s,a)),+s)}function determineUnitForAutoTicks(n,e,t,r){const a=UNITS.length;for(let o=UNITS.indexOf(n);o<a-1;++o){const s=INTERVALS[UNITS[o]],l=s.steps?s.steps:Number.MAX_SAFE_INTEGER;if(s.common&&Math.ceil((t-e)/(l*s.size))<=r)return UNITS[o]}return UNITS[a-1]}function determineUnitForFormatting(n,e,t,r,a){for(let o=UNITS.length-1;o>=UNITS.indexOf(t);o--){const s=UNITS[o];if(INTERVALS[s].common&&n._adapter.diff(a,r,s)>=e-1)return s}return UNITS[t?UNITS.indexOf(t):0]}function determineMajorUnit(n){for(let e=UNITS.indexOf(n)+1,t=UNITS.length;e<t;++e)if(INTERVALS[UNITS[e]].common)return UNITS[e]}function addTick(n,e,t){if(!t)n[e]=!0;else if(t.length){const{lo:r,hi:a}=_lookup(t,e),o=t[r]>=e?t[r]:t[a];n[o]=!0}}function setMajorTicks(n,e,t,r){const a=n._adapter,o=+a.startOf(e[0].value,r),s=e[e.length-1].value;let l,c;for(l=o;l<=s;l=+a.add(l,1,r))c=t[l],c>=0&&(e[c].major=!0);return e}function ticksFromTimestamps(n,e,t){const r=[],a={},o=e.length;let s,l;for(s=0;s<o;++s)l=e[s],a[l]=s,r.push({value:l,major:!1});return o===0||!t?r:setMajorTicks(n,r,a,t)}class TimeScale extends Scale{static id="time";static defaults={bounds:"data",adapters:{},time:{parser:!1,unit:!1,round:!1,isoWeekday:!1,minUnit:"millisecond",displayFormats:{}},ticks:{source:"auto",callback:!1,major:{enabled:!1}}};constructor(e){super(e),this._cache={data:[],labels:[],all:[]},this._unit="day",this._majorUnit=void 0,this._offsets={},this._normalized=!1,this._parseOpts=void 0}init(e,t={}){const r=e.time||(e.time={}),a=this._adapter=new adapters._date(e.adapters.date);a.init(t),mergeIf(r.displayFormats,a.formats()),this._parseOpts={parser:r.parser,round:r.round,isoWeekday:r.isoWeekday},super.init(e),this._normalized=t.normalized}parse(e,t){return e===void 0?null:parse(this,e)}beforeLayout(){super.beforeLayout(),this._cache={data:[],labels:[],all:[]}}determineDataLimits(){const e=this.options,t=this._adapter,r=e.time.unit||"day";let{min:a,max:o,minDefined:s,maxDefined:l}=this.getUserBounds();function c(f){!s&&!isNaN(f.min)&&(a=Math.min(a,f.min)),!l&&!isNaN(f.max)&&(o=Math.max(o,f.max))}(!s||!l)&&(c(this._getLabelBounds()),(e.bounds!=="ticks"||e.ticks.source!=="labels")&&c(this.getMinMax(!1))),a=isNumberFinite(a)&&!isNaN(a)?a:+t.startOf(Date.now(),r),o=isNumberFinite(o)&&!isNaN(o)?o:+t.endOf(Date.now(),r)+1,this.min=Math.min(a,o-1),this.max=Math.max(a+1,o)}_getLabelBounds(){const e=this.getLabelTimestamps();let t=Number.POSITIVE_INFINITY,r=Number.NEGATIVE_INFINITY;return e.length&&(t=e[0],r=e[e.length-1]),{min:t,max:r}}buildTicks(){const e=this.options,t=e.time,r=e.ticks,a=r.source==="labels"?this.getLabelTimestamps():this._generate();e.bounds==="ticks"&&a.length&&(this.min=this._userMin||a[0],this.max=this._userMax||a[a.length-1]);const o=this.min,s=this.max,l=_filterBetween(a,o,s);return this._unit=t.unit||(r.autoSkip?determineUnitForAutoTicks(t.minUnit,this.min,this.max,this._getLabelCapacity(o)):determineUnitForFormatting(this,l.length,t.minUnit,this.min,this.max)),this._majorUnit=!r.major.enabled||this._unit==="year"?void 0:determineMajorUnit(this._unit),this.initOffsets(a),e.reverse&&l.reverse(),ticksFromTimestamps(this,l,this._majorUnit)}afterAutoSkip(){this.options.offsetAfterAutoskip&&this.initOffsets(this.ticks.map(e=>+e.value))}initOffsets(e=[]){let t=0,r=0,a,o;this.options.offset&&e.length&&(a=this.getDecimalForValue(e[0]),e.length===1?t=1-a:t=(this.getDecimalForValue(e[1])-a)/2,o=this.getDecimalForValue(e[e.length-1]),e.length===1?r=o:r=(o-this.getDecimalForValue(e[e.length-2]))/2);const s=e.length<3?.5:.25;t=_limitValue(t,0,s),r=_limitValue(r,0,s),this._offsets={start:t,end:r,factor:1/(t+1+r)}}_generate(){const e=this._adapter,t=this.min,r=this.max,a=this.options,o=a.time,s=o.unit||determineUnitForAutoTicks(o.minUnit,t,r,this._getLabelCapacity(t)),l=valueOrDefault(a.ticks.stepSize,1),c=s==="week"?o.isoWeekday:!1,f=isNumber(c)||c===!0,d={};let p=t,_,b;if(f&&(p=+e.startOf(p,"isoWeek",c)),p=+e.startOf(p,f?"day":s),e.diff(r,t,s)>1e5*l)throw new Error(t+" and "+r+" are too far apart with stepSize of "+l+" "+s);const y=a.ticks.source==="data"&&this.getDataTimestamps();for(_=p,b=0;_<r;_=+e.add(_,l,s),b++)addTick(d,_,y);return(_===r||a.bounds==="ticks"||b===1)&&addTick(d,_,y),Object.keys(d).sort(sorter).map(E=>+E)}getLabelForValue(e){const t=this._adapter,r=this.options.time;return r.tooltipFormat?t.format(e,r.tooltipFormat):t.format(e,r.displayFormats.datetime)}format(e,t){const a=this.options.time.displayFormats,o=this._unit,s=t||a[o];return this._adapter.format(e,s)}_tickFormatFunction(e,t,r,a){const o=this.options,s=o.ticks.callback;if(s)return callback(s,[e,t,r],this);const l=o.time.displayFormats,c=this._unit,f=this._majorUnit,d=c&&l[c],p=f&&l[f],_=r[t],b=f&&p&&_&&_.major;return this._adapter.format(e,a||(b?p:d))}generateTickLabels(e){let t,r,a;for(t=0,r=e.length;t<r;++t)a=e[t],a.label=this._tickFormatFunction(a.value,t,e)}getDecimalForValue(e){return e===null?NaN:(e-this.min)/(this.max-this.min)}getPixelForValue(e){const t=this._offsets,r=this.getDecimalForValue(e);return this.getPixelForDecimal((t.start+r)*t.factor)}getValueForPixel(e){const t=this._offsets,r=this.getDecimalForPixel(e)/t.factor-t.end;return this.min+r*(this.max-this.min)}_getLabelSize(e){const t=this.options.ticks,r=this.ctx.measureText(e).width,a=toRadians(this.isHorizontal()?t.maxRotation:t.minRotation),o=Math.cos(a),s=Math.sin(a),l=this._resolveTickFontOptions(0).size;return{w:r*o+l*s,h:r*s+l*o}}_getLabelCapacity(e){const t=this.options.time,r=t.displayFormats,a=r[t.unit]||r.millisecond,o=this._tickFormatFunction(e,0,ticksFromTimestamps(this,[e],this._majorUnit),a),s=this._getLabelSize(o),l=Math.floor(this.isHorizontal()?this.width/s.w:this.height/s.h)-1;return l>0?l:1}getDataTimestamps(){let e=this._cache.data||[],t,r;if(e.length)return e;const a=this.getMatchingVisibleMetas();if(this._normalized&&a.length)return this._cache.data=a[0].controller.getAllParsedValues(this);for(t=0,r=a.length;t<r;++t)e=e.concat(a[t].controller.getAllParsedValues(this));return this._cache.data=this.normalize(e)}getLabelTimestamps(){const e=this._cache.labels||[];let t,r;if(e.length)return e;const a=this.getLabels();for(t=0,r=a.length;t<r;++t)e.push(parse(this,a[t]));return this._cache.labels=this._normalized?e:this.normalize(e)}normalize(e){return _arrayUnique(e.sort(sorter))}}function interpolate(n,e,t){let r=0,a=n.length-1,o,s,l,c;t?(e>=n[r].pos&&e<=n[a].pos&&({lo:r,hi:a}=_lookupByKey(n,"pos",e)),{pos:o,time:l}=n[r],{pos:s,time:c}=n[a]):(e>=n[r].time&&e<=n[a].time&&({lo:r,hi:a}=_lookupByKey(n,"time",e)),{time:o,pos:l}=n[r],{time:s,pos:c}=n[a]);const f=s-o;return f?l+(c-l)*(e-o)/f:l}class TimeSeriesScale extends TimeScale{static id="timeseries";static defaults=TimeScale.defaults;constructor(e){super(e),this._table=[],this._minPos=void 0,this._tableRange=void 0}initOffsets(){const e=this._getTimestampsForTable(),t=this._table=this.buildLookupTable(e);this._minPos=interpolate(t,this.min),this._tableRange=interpolate(t,this.max)-this._minPos,super.initOffsets(e)}buildLookupTable(e){const{min:t,max:r}=this,a=[],o=[];let s,l,c,f,d;for(s=0,l=e.length;s<l;++s)f=e[s],f>=t&&f<=r&&a.push(f);if(a.length<2)return[{time:t,pos:0},{time:r,pos:1}];for(s=0,l=a.length;s<l;++s)d=a[s+1],c=a[s-1],f=a[s],Math.round((d+c)/2)!==f&&o.push({time:f,pos:s/(l-1)});return o}_generate(){const e=this.min,t=this.max;let r=super.getDataTimestamps();return(!r.includes(e)||!r.length)&&r.splice(0,0,e),(!r.includes(t)||r.length===1)&&r.push(t),r.sort((a,o)=>a-o)}_getTimestampsForTable(){let e=this._cache.all||[];if(e.length)return e;const t=this.getDataTimestamps(),r=this.getLabelTimestamps();return t.length&&r.length?e=this.normalize(t.concat(r)):e=t.length?t:r,e=this._cache.all=e,e}getDecimalForValue(e){return(interpolate(this._table,e)-this._minPos)/this._tableRange}getValueForPixel(e){const t=this._offsets,r=this.getDecimalForPixel(e)/t.factor-t.end;return interpolate(this._table,r*this._tableRange+this._minPos,!0)}}var scales=Object.freeze({__proto__:null,CategoryScale,LinearScale,LogarithmicScale,RadialLinearScale,TimeScale,TimeSeriesScale});const registerables=[controllers,elements,plugins,scales];Chart.register(...registerables);class ColorPalette{static PRIMARY=["#1f78b4","#a6cee3","#b2df8a","#33a02c","#fb9a99","#e31a1c","#fdbf6f","#ff7f00","#cab2d6","#6a3d9a","#ffff99","#b15928"]}function renderChart(n,e){const t=document.getElementById(n);if(t!==null){const r=t.getAttribute("data-url");if(r==null)return;fetchChartData(r).then(a=>{e(t,a)}).catch(a=>{console.log("Error loading chart data: "+a);const o=t.getContext("2d");o&&(o.fillStyle="red",o.font="16px Arial",o.fillText("Error loading chart data",10,15))})}}async function fetchChartData(n){try{const e=await fetch(n);if(!e.ok)throw new Error(`HTTP error! status: ${e.status}`);return await e.json()}catch(e){throw console.error("Error fetching data:",e),e}}function getCSSVariable(n){return getComputedStyle(document.documentElement).getPropertyValue(n).trim()}function initPubChart(){renderChart("pubs-by-year-chart",createPubChart)}function createPubChart(n,e){new Chart(n,{type:"bar",data:{labels:e.data.map(t=>t.name),datasets:[{label:"Publications",data:e.data.map(t=>t.total)}]},options:{responsive:!0,maintainAspectRatio:!1,scales:{y:{beginAtZero:!0,suggestedMax:10,ticks:{stepSize:1},grid:{display:!1}},x:{grid:{display:!1}}},plugins:{title:{display:!1},legend:{display:!1}}}})}function initGrantChart(){renderChart("grant-summary-chart",createGrantChart)}function createGrantChart(n,e){new Chart(n,{type:"doughnut",data:{labels:e.data.map(t=>t.name),datasets:[{data:e.data.map(t=>t.total),backgroundColor:ColorPalette.PRIMARY,borderColor:ColorPalette.PRIMARY.map(t=>t+"80"),borderWidth:1}]},options:{radius:"60%",responsive:!0,plugins:{legend:{position:"bottom"},title:{display:!1}}}})}function initAllocationChart(){renderChart("allocation-summary-chart",createAllocationChart)}function createAllocationChart(n,e){new Chart(n,{type:"doughnut",data:{labels:e.data.map(t=>t.name),datasets:[{data:e.data.map(t=>t.total),backgroundColor:ColorPalette.PRIMARY,borderColor:ColorPalette.PRIMARY.map(t=>t+"80"),borderWidth:1}]},options:{radius:"70%",responsive:!0,plugins:{legend:{position:"bottom"},title:{display:!1}}}})}function initResourceChart(){renderChart("resource-summary-chart",createResourceChart)}function createResourceChart(n,e){new Chart(n,{type:"doughnut",data:{labels:e.data.map(t=>t.name),datasets:[{data:e.data.map(t=>t.total),backgroundColor:ColorPalette.PRIMARY,borderColor:ColorPalette.PRIMARY.map(t=>t+"80"),borderWidth:1}]},options:{radius:"70%",responsive:!0,plugins:{legend:{position:"bottom"},title:{display:!1}}}})}function initGaugeChart(){const n=document.querySelectorAll("div.chart-container > canvas.gauge-chart");for(const e of n)if(e!==null){const t=Number(e?.getAttribute("data-used")||0);let r=Number(e?.getAttribute("data-total")||0)-t;const a=String(e?.getAttribute("data-title")||"");r<0&&(r=0),createGaugeChart(e,a,t,r)}}function createGaugeChart(n,e,t,r){new Chart(n,{type:"doughnut",data:{labels:["Used","Available"],datasets:[{data:[t,r],backgroundColor:[getCSSVariable("--bs-success"),getCSSVariable("--bs-secondary")],borderColor:[getCSSVariable("--bs-success"),getCSSVariable("--bs-secondary")],borderWidth:1}]},options:{radius:"70%",rotation:270,circumference:180,responsive:!0,plugins:{legend:{display:!1},title:{display:!0,text:e,position:"bottom"}}}})}function initCharts(){for(const n of[initPubChart,initGrantChart,initAllocationChart,initResourceChart,initGaugeChart])n()}function initDepedencies(){initDataTable()}function initHtmx(){document.addEventListener("htmx:afterSettle",initDepedencies)}function getCookie(n){let e="";if(document.cookie&&document.cookie!=""){const t=document.cookie.split(";");for(let r=0;r<t.length;r++){const a=jQuery.trim(t[r]);if(a.substring(0,n.length+1)==n+"="){e=decodeURIComponent(a.substring(n.length+1));break}}}return e}function*getElementsByQueryGenerator(n,e=document){const t=e.querySelectorAll(n);for(let r=0;r<t.length;r++)yield t[r]}function initTooltips(){for(const n of getElementsByQueryGenerator('[data-bs-toggle="tooltip"]'))new Tooltip$1(n,{container:"body"})}function initPopovers(){for(const n of getElementsByQueryGenerator('[data-bs-toggle="popover"]'))new Popover(n)}function initFilterAccordionIcon(){const n=document.getElementById("collapseOne"),e=document.getElementById("plus_minus");n===null||e===null||(n.addEventListener("show.bs.collapse",()=>{e.classList.replace("fa-plus","fa-minus")}),n.addEventListener("hide.bs.collapse",()=>{e.classList.replace("fa-minus","fa-plus")}))}function initBootstrap(){for(const n of[initTooltips,initPopovers,initFilterAccordionIcon])n()}Object.assign(window,{getCookie:function(n){getCookie(n)},$:jQuery$1,jQuery:jQuery$1});function initDocument(){for(const n of[initDateSelector,initSelect2,initForm,initDataTable,initBootstrap,initCharts,initHtmx])n()}document.readyState!=="loading"?initDocument():document.addEventListener("DOMContentLoaded",initDocument);
