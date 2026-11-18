import json,numpy as np,sys
P=sys.argv[1];tr=json.load(open(P+'train.json'));te=json.load(open(P+'test.json'))
Xb=(np.array(tr['X'])>0).astype(float);Xtb=(np.array(te['X'])>0).astype(float);y=np.array(tr['y']);yt=np.array(te['y'])
U=30;cnt=np.bincount(y,minlength=U)
ov=Xtb@Xb.T;sz=Xb.sum(1)[None,:];szt=Xtb.sum(1)[:,None];J=ov/np.maximum(sz+szt-ov,1)
out=[f"KC%={Xb.mean()*100:.1f}"]
for p,al in [(1,0.5),(2,0.5),(8,0)]:
  K=J**p;S=np.stack([K[:,y==u].sum(1)/max(cnt[u],1)**al for u in range(U)],1);out.append(f"p{p}a{al}:{np.mean(S.argmax(1)==yt):.3f}")
# same-ctx reliability
print(P,' '.join(out))
