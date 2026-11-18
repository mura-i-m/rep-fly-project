import json,numpy as np,sys,re
exec(open('sim6.py').read().split("def run")[0])
ctx=te['ctx'];chars=json.load(open('words.json')) if P=='W' else [o['char'] for o in a['output']]
def train(anat,lr=0.01,ep=5):
  Nn=N if anat else np.ones_like(N);W=np.ones((U,nK));Ws=np.zeros_like(W)
  sc=lambda W,x:(Nn*(1-W))@x
  for e in range(ep):
    for i in np.random.RandomState(e).permutation(len(y)):
      x=X[i];t=y[i];s=sc(W,x);s2=s.copy();s2[t]=-1e9;p=np.argmax(s2)
      if s[t]<=s[p]: W[t]-=lr*x*W[t]; W[p]+=lr*x*(1-W[p])
      Ws+=W
  Ws/=ep*len(y)
  pr=np.array([np.argmax(sc(Ws,x)) for x in Xt])
  tot=np.mean(pr==yt)
  kw=[i for i,c in enumerate(ctx) if re.search(r'(de|ret|retu|sel|self|imp|for|els|Non|tru|fals|in)$',c)]
  print('anat',anat,'all',round(tot,3),'keyword-ish',len(kw),round(np.mean(pr[kw]==yt[kw]),3))
  for i in kw[:12]: print('  ',repr(ctx[i]),'->',repr(chars[pr[i]]),'(正解',repr(chars[yt[i]])+')')
train(True);train(False)
