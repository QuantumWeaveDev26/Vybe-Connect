'use strict';
// Keep the visible land silhouette centered, rather than centering the equator.
(function(root){
 function worldLayout(width,height,points){
  let minX=1,maxX=0,minY=1,maxY=0;
  for(let i=0;i<points.length;i+=2){minX=Math.min(minX,points[i]);maxX=Math.max(maxX,points[i]);minY=Math.min(minY,points[i+1]);maxY=Math.max(maxY,points[i+1])}
  if(maxX<=minX||maxY<=minY){minX=minY=0;maxX=maxY=1}
  const padding=Math.min(24,width*.06,height*.06);
  const mapWidth=Math.min(1600,(width-2*padding)/(maxX-minX),(height-2*padding)*2/(maxY-minY));
  return {x:width/2-(minX+maxX)*mapWidth/2,y:height/2-(minY+maxY)*mapWidth/4,width:mapWidth,height:mapWidth/2};
 }
 function splashWorldLayout(width,height,points){
  if(width<=600&&height>=600){const map=worldLayout(width,height*.28,points);map.y+=height*.29;return map}
  return worldLayout(width,height,points);
 }
 if(typeof module!=='undefined'&&module.exports)module.exports={worldLayout,splashWorldLayout};
 else root.VybeLaunchLayout={worldLayout,splashWorldLayout};
})(globalThis);
