const fs=require('fs');const FC=require('../js/completer.js');
const c=require('../../fly-core/data/mb_circuit.json'),a=require('../data/alphabet.json');
const opt=JSON.parse(process.argv[2]);const f=new FC(c,a,opt);const words=require('./words.json');
for(const [name,n] of [['train',3000],['test',1000]]){const t=fs.readFileSync('../corpus/'+name+'.py','utf8');
const re=new RegExp('\\b('+words.join('|')+')\\b','g');const occ=[];let m;while((m=re.exec(t)))occ.push([m.index,words.indexOf(m[1])]);
const X=[],y=[],ctx=[];const rnd=require('../../fly-core/js/mb_spiking.js').mulberry32(name=='train'?1:2);
for(let k=0;k<n;k++){const [i,wi]=occ[Math.floor(rnd()*occ.length)];const L=1+Math.floor(rnd()*3);const s=t.slice(Math.max(0,i-3),i+Math.min(L,words[wi].length-1));
f.predict(s);X.push(Array.from(f.mb.kc.count));y.push(wi);ctx.push(f.context(s).join(''));}
fs.writeFileSync('./out/W'+name+'.json',JSON.stringify({X,y,ctx}));}
