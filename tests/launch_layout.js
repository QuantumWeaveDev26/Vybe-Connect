const assert=require('node:assert/strict');
const fs=require('node:fs');
const {worldLayout}=require('../static/launch-layout.js');
const points=JSON.parse(fs.readFileSync(require('node:path').join(__dirname,'../static/world-dots.json'),'utf8'));
for(const [width,height] of [[1920,1080],[1366,768],[390,844],[320,568],[844,390],[2560,600]]){
 const layout=worldLayout(width,height,points);
 const xs=[],ys=[];
 for(let i=0;i<points.length;i+=2){xs.push(layout.x+points[i]*layout.width);ys.push(layout.y+points[i+1]*layout.height)}
 const left=Math.min(...xs),right=Math.max(...xs),top=Math.min(...ys),bottom=Math.max(...ys);
 assert.ok(Math.abs((left+right)/2-width/2)<.01,`horizontal center at ${width}x${height}`);
 assert.ok(Math.abs((top+bottom)/2-height/2)<.01,`vertical center at ${width}x${height}`);
 assert.ok(left>=15&&right<=width-15&&top>=15&&bottom<=height-15,`contained at ${width}x${height}`);
 assert.equal(layout.width,layout.height*2,'preserve the projection aspect ratio');
}
for(const points of [[],[0,0,1,1]]){
 const layout=worldLayout(390,844,points);
 assert.ok(Object.values(layout).every(Number.isFinite));
}
console.log('World map geometry: centered and contained at six viewport sizes.');
