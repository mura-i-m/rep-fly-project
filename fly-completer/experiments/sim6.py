import json,numpy as np,sys
c=json.load(open('../../fly-core/data/mb_circuit.json'));a=json.load(open('../data/alphabet.json'))
nK=len(c['kc']['body']);nM=len(c['mbon']['body'])
S=np.zeros((nK,nM))
for k,m,x in c['kc_mbon']: S[k,m]+=x
S/=S.sum(0,keepdims=True)
U=30;nmb=np.array([len(o['mbons']) for o in a['output']])
N=np.stack([S[:,o['mbons']].sum(1) for o in a['output']])
P=sys.argv[1];tr=json.load(open(P+'train.json'));te=json.load(open(P+'test.json'))
X=(np.array(tr['X'])>0).astype(float);Xt=(np.array(te['X'])>0).astype(float);y=np.array(tr['y']);yt=np.array(te['y'])
def run(lr,lru,norm,anat=True,ep=5,soft=True):
  Nn=N if anat else np.ones_like(N)
  if norm=='nmb': Z=nmb[:,None]*np.ones((1,1))
  W=np.ones((U,nK))
  def sc(x):
    drop=(Nn*(1-W))@x
    if norm=='nmb': drop=drop/nmb
    if norm=='ratio': drop=drop/np.maximum(Nn@x,1e-9)
    return drop
  for e in range(ep):
    for i in np.random.RandomState(e).permutation(len(y)):
      x=X[i];t=y[i];s=sc(x);s2=s.copy();s2[t]=-1e9;p=np.argmax(s2)
      if s[t]<=s[p]:
        if soft: W[t]-=lr*x*W[t]; W[p]+=lru*x*(1-W[p])
        else: W[t]=np.maximum(0,W[t]-lr*x); W[p]=np.minimum(1,W[p]+lru*x)
    acc=np.mean([np.argmax(sc(x))==t for x,t in zip(Xt,yt)])
    print(lr,lru,norm,anat,soft,e,round(acc,3),flush=True)
for args in [(0.01,0.01,'none',True),(0.01,0.01,'nmb',True),(0.01,0.01,'ratio',True),(0.002,0.002,'nmb',True),(0.01,0.01,'none',False)]:
  run(*args)
