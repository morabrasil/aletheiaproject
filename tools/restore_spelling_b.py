"""Restaura a grafia de 1787 no texto modernizado da edição B.
Léxico de formas originais: KrV A (1781) e KU (1790) do DTA. Desempate pelo OCR do exemplar de 1787."""
import json, re, sys, collections, bisect
sys.path.insert(0, '/home/claude/src/kantB')
from align import skel, anchors

def words_of(path):
    d = json.load(open(path, encoding='utf8'))
    for s in d['secs']:
        for p in s['paras']:
            t = re.sub(r'\u0001[^\u0002]*\u0002|[\u0003\u0004]', ' ', p[2])
            yield from re.findall(r"[A-Za-zÄÖÜäöüß]+", t)

lex = collections.Counter()
for f in ['/home/claude/src/out/kant/krv_a.json', '/home/claude/src/out/kant/ku_a.json']:
    lex.update(words_of(f))

def variants(o):
    """possible modern spellings (lowercase) of an original-spelling word"""
    w = o.lower()
    out = {w}
    def apply(fn):
        nonlocal out
        new = set()
        for x in out: new |= fn(x)
        out = new
    apply(lambda x: {x, x.replace('transscend', 'transzend').replace('transcend', 'transzend')})
    apply(lambda x: {x, re.sub(r'^ae', 'ä', x), re.sub(r'^oe', 'ö', x), re.sub(r'^ue', 'ü', x)})
    apply(lambda x: {x, x.replace('th', 't')})
    apply(lambda x: {x, re.sub(r'c(?=[aoulrtk])', 'k', x).replace('ck', 'ck'), re.sub(r'c(?=[eiy])', 'z', x),
                     re.sub(r'c(?=[eiy])', 'z', re.sub(r'c(?=[aoulrt])', 'k', x))})
    apply(lambda x: {x, x.replace('ey', 'ei'), x.replace('ey', 'ei').replace('y', 'i')})
    apply(lambda x: {x, re.sub(r'niß$', 'nis', x), re.sub(r'nisse', 'nisse', x)})
    apply(lambda x: {x, re.sub(r'ir(en|t|te|ten|ung)$', r'ier\1', x)})
    apply(lambda x: {x, re.sub(r'(?<=[aeiouäöü])ß', 'ss', x)})
    apply(lambda x: {x, x.replace('kenntniß', 'kenntnis').replace('kentniß', 'kenntnis').replace('kentnis', 'kenntnis')})
    return {x for x in out if x != w}

modern2orig = collections.defaultdict(collections.Counter)
for o, n in lex.items():
    for v in variants(o):
        modern2orig[v][o] += n

def lev(a, b):
    if a == b: return 0
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j-1] + 1, prev[j-1] + (ca != cb)))
        prev = cur
    return prev[-1]
def ocrnorm(w): return w.lower().replace('ſ', 's').replace('f', 's').replace('ͤ', 'e')

# OCR alignment to break ties
ocr = open('ocr.txt', encoding='utf8').read()
O = ocr.split(); SO = [skel(x) for x in O]
data = json.load(open('krv_b.json', encoding='utf8'))
G = []
for si, s in enumerate(data['secs']):
    for pi, p in enumerate(s['paras']):
        t = re.sub(r'\u0001[^\u0002]*\u0002', ' ', p[2])
        G.extend(re.findall(r'\S+', t))
SG = [skel(x) for x in G]
an = anchors(SO, SG); bo = [b for _, b in an]; ao = [a for a, _ in an]
def ocr_word_near(gi):
    j = bisect.bisect_left(bo, gi)
    cands = []
    for k in (j-1, j):
        if 0 <= k < len(an):
            oi = ao[k] + (gi - bo[k])
            for d in (-1, 0, 1):
                if 0 <= oi + d < len(O): cands.append(O[oi + d])
    return cands

stats = collections.Counter()
STEMS = [('Kritik','Critik'),('kritik','critik'),('Kritisch','Critisch'),('kritisch','critisch'),
         ('transzendental','transscendental'),('Transzendental','Transscendental'),
         ('Urteil','Urtheil'),('urteil','urtheil'),('Teil','Theil'),('teil','theil'),
         ('Prinzip','Princip'),('prinzip','princip'),('Kategorie','Categorie'),('kategorie','categorie'),
         ('kenntnis','kenntniß'),('Erkenntnis','Erkenntniß'),('Spekulati','Speculati'),('spekulati','speculati'),
         ('Objekt','Object'),('objekt','object'),('Subjekt','Subject'),('subjekt','subject'),
         ('Kosmolog','Cosmolog'),('kosmolog','cosmolog'),('Disziplin','Disciplin'),('Prädikat','Prädicat'),('prädikat','prädicat'),
         ('Tätigkeit','Thätigkeit'),('tätigkeit','thätigkeit'),('notwendig','nothwendig'),('Notwendig','Nothwendig')]
def stem_rules(w):
    for a, b in STEMS:
        if a in w:
            w = w.replace(a, b)
    w = re.sub(r'kenntnißs', 'kenntniss', w)
    return w
gi = 0
def fix_word(m):
    global gi
    w = m.group(0)
    me = gi; gi += 0  # index advanced by caller per token
    return w

def restore_text(t):
    global gi
    out = []
    for part in re.split(r'(\u0001[^\u0002]*\u0002)', t):
        if part.startswith('\u0001'):
            out.append(part); continue
        toks = re.split(r'(\s+)', part)
        for tok in toks:
            if not tok or tok.isspace():
                out.append(tok); continue
            m = re.match(r'^([^A-Za-zÄÖÜäöüß]*)([A-Za-zÄÖÜäöüß]+)(.*)$', tok)
            if not m:
                out.append(tok); gi += 1; continue
            pre, w, post = m.groups()
            low = w.lower()
            cand = modern2orig.get(low)
            if cand and low not in {k.lower() for k in lex if False}:
                # keep the modern word if it is itself frequent in the originals (e.g. "und", "der")
                own = lex.get(w, 0) + lex.get(w.lower(), 0) + lex.get(w.capitalize(), 0)
                best = cand.most_common()
                if own: best = best + [(w, own)]      # the modern form may itself be a period spelling
                near = ocr_word_near(gi)
                def score(c):
                    o, n = c
                    d = min((lev(ocrnorm(o), ocrnorm(x)) for x in near), default=9)
                    return (d, -n)
                choice = min(best, key=score)[0]
                if w[0].isupper() and not choice[0].isupper(): choice = choice[0].upper() + choice[1:]
                if w[0].islower() and choice[0].isupper():
                    choice = choice[0].lower() + choice[1:]
                    if choice.startswith(('oe','ae','ue')) and not lex.get(choice): choice = {'oe':'ö','ae':'ä','ue':'ü'}[choice[:2]] + choice[2:]
                if w.isupper() and len(w) > 1: choice = choice.upper()
                out.append(pre + choice + post); stats['restored'] += 1
            else:
                w2 = stem_rules(w)
                if w2 != w: stats['stem'] += 1
                else: stats['unchanged'] += 1
                out.append(pre + w2 + post)
            gi += 1
    return ''.join(out)

for s in data['secs']:
    s['title'] = restore_text(s['title']) if False else s['title']
    for p in s['paras']:
        p[2] = restore_text(p[2])
# section titles: restore separately (no OCR context needed)
gi_backup = gi
for s in data['secs']:
    gi = 0
    s['title'] = re.sub(r'[A-Za-zÄÖÜäöüß]+', lambda m: (lambda w: (lambda c: (c[0].upper()+c[1:] if w[0].isupper() else c) if c else w)(modern2orig[w.lower()].most_common(1)[0][0] if w.lower() in modern2orig and (lex.get(w,0)+lex.get(w.lower(),0)+lex.get(w.capitalize(),0)) < sum(modern2orig[w.lower()].values()) else None))(m.group(0)), s['title'])
json.dump(data, open('krv_b_orig.json', 'w', encoding='utf8'), ensure_ascii=False, separators=(',', ':'))
print(stats, file=sys.stderr)
