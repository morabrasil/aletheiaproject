import re,json,bisect
def skel(w):
    w=w.lower().replace('ſ','s').replace('ß','ss').replace('ͤ','e')
    w=w.replace('ä','a').replace('ö','o').replace('ü','u').replace('aͤ','a').replace('oͤ','o').replace('uͤ','u')
    w=re.sub(r'[^a-z]','',w)
    w=w.replace('f','s').replace('th','t').replace('h','').replace('c','k').replace('z','k').replace('y','i').replace('v','f')
    w=re.sub(r'(.)\1+',r'\1',w)
    return w
def tokens(text): return re.findall(r"[^\s]+",text)
def anchors(A,B,n=3):
    def grams(S):
        d={}
        for i in range(len(S)-n+1):
            g=tuple(S[i:i+n])
            if any(len(x)<2 for x in g): continue
            d.setdefault(g,[]).append(i)
        return {g:v[0] for g,v in d.items() if len(v)==1}
    ga,gb=grams(A),grams(B)
    pairs=sorted((ga[g],gb[g]) for g in ga if g in gb)
    # LIS on b
    import bisect
    tails=[];idx=[];prev=[-1]*len(pairs)
    for k,(a,b) in enumerate(pairs):
        j=bisect.bisect_left(tails,b)
        if j==len(tails): tails.append(b); idx.append(k)
        else: tails[j]=b; idx[j]=k
        prev[k]=idx[j-1] if j>0 else -1
    out=[];k=idx[-1] if idx else -1
    while k!=-1: out.append(pairs[k]); k=prev[k]
    return out[::-1]
