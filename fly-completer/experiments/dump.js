const fs=require('fs');const FC=require('../js/completer.js');
const c=require('../../fly-core/data/mb_circuit.json'),a=require('../data/alphabet.json');
const opt=JSON.parse(process.argv[2]);const f=new FC(c,a,opt);
function positions(text){const pos=[];let ls=true;for(let i=1;i<text.length;i++){const ch=text[i-1];if(ch==='\n')ls=true;else if(ch!==' ')ls=false;if(ls&&text[i]===' ')continue;if(f.charToUnit.has(text[i]))pos.push(i);}return pos;}
for(const [name,n] of [['train',3000],['test',1000]]){const t=fs.readFileSync('corpus/'+name+'.py','utf8');const P=positions(t);const step=Math.floor(P.length/n);
const X=[],y=[],ctx=[];for(let k=0;k<n;k++){const i=P[k*step];const s=t.slice(Math.max(0,i-8),i);const p=f.predict(s);X.push(Array.from(f.mb.kc.count));y.push(f.charToUnit.get(t[i]));ctx.push(f.context(s).join(''));}
fs.writeFileSync('./out/'+(process.argv[3]||'')+name+'.json',JSON.stringify({X,y,ctx}));}
