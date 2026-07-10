/* Film-grain / TV-static overlay animator.
   Requires a <canvas id="grain"> in the DOM. Self-initialises on load.
   Half-res canvas + a few pre-rendered noise frames cycled for a living grain. */
(function(){
  var grain = document.getElementById('grain');
  if(!grain) return;
  var gctx = grain.getContext('2d');
  var grainBufs = [], gframe = 0;
  var FRAMES = 4;          // more frames = less obvious loop
  var DIVISOR = 2;         // higher = coarser, cheaper grain
  var DELAY = 60;          // ms between frames (~16fps)
  var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  function sizeGrain(){
    grain.width  = Math.max(1, Math.floor(innerWidth / DIVISOR));
    grain.height = Math.max(1, Math.floor(innerHeight / DIVISOR));
    grain.style.width  = innerWidth + 'px';
    grain.style.height = innerHeight + 'px';
  }
  function makeGrain(){
    grainBufs = [];
    for(var k=0;k<FRAMES;k++){
      var id = gctx.createImageData(grain.width, grain.height);
      for(var i=0;i<id.data.length;i+=4){
        var v = Math.random()*255;
        id.data[i]=id.data[i+1]=id.data[i+2]=v; id.data[i+3]=255;
      }
      grainBufs.push(id);
    }
  }
  function tickGrain(){
    gframe = (gframe+1) % grainBufs.length;
    if(grainBufs.length) gctx.putImageData(grainBufs[gframe], 0, 0);
    if(!reduce) setTimeout(function(){ requestAnimationFrame(tickGrain); }, DELAY);
  }

  function boot(){ sizeGrain(); makeGrain(); if(reduce){ gctx.putImageData(grainBufs[0],0,0); } else { tickGrain(); } }
  window.addEventListener('resize', function(){ sizeGrain(); makeGrain(); });
  if(document.readyState !== 'loading') boot(); else document.addEventListener('DOMContentLoaded', boot);
})();
