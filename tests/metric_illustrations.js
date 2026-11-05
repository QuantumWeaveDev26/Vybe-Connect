const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const c=vm.createContext({document:{addEventListener(){}}});vm.runInContext(fs.readFileSync('static/visuals.js','utf8'),c);
assert.equal(vm.runInContext('typeof metricIllustration',c),'function');
const art=vm.runInContext('["Total contacts","Campaigns","Queued messages","Opted-in audience"].map(metricIllustration)',c);
assert.equal(new Set(art).size,4);for(const svg of art){assert.match(svg,/metric-character-v2/);assert.match(svg,/aria-hidden="true"/);assert.doesNotMatch(svg,/concept-portrait|<image|https:/)}
assert.equal(vm.runInContext('metricIllustration("Unknown")',c),'');
console.log('Four distinct approved 3D character positions, no external assets and stable unknown fallback passed.');
