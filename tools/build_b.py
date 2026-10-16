"""Monta a edição B (1787) da Crítica da razão pura:
texto do Project Gutenberg (nº 6343, grafia modernizada) + quebras de página B
tiradas do OCR do exemplar de 1787 digitalizado (Internet Archive, bub_gb_qZEPAAAAQAAJ).
"""
import re, json, bisect, sys
sys.path.insert(0, '/home/claude/src/kantB')
from align import skel, anchors

ROM = [(1000,'M'),(900,'CM'),(500,'D'),(400,'CD'),(100,'C'),(90,'XC'),(50,'L'),(40,'XL'),(10,'X'),(9,'IX'),(5,'V'),(4,'IV'),(1,'I')]
def roman(n):
    s=''
    for v,r in ROM:
        while n>=v: s+=r; n-=v
    return s
def unroman(s):
    vals={'I':1,'V':5,'X':10,'L':50}; t=0
    for i,c in enumerate(s):
        v=vals[c]; t+= -v if i+1<len(s) and vals[s[i+1]]>v else v
    return t

# ---------------- OCR: page headers ----------------
ocr = open('ocr.txt', encoding='utf8').read().split('\n')
HEADW = re.compile(r'(Elementar|Clementar|Slementar|Methoden|Abſchn|Abschn|Abfchn|Hauptſt|Hauptst|Hauptft|Einleitung|Antinomie|Antithetik|Antithetif|Th\.|Abth|Buch|Disciplin|Difeiplin|Canon|Architect|Geſchichte|Geschichte|Gefchic|Paralog|Analytik|Analytif|Dialektik|Dialectik|Dialeetif|Logik|Aeſthetik|Aesthetik|Ideal|Anhang|Grundſ|Syſtem|System|Vorrede)')

cands = []
for i, l in enumerate(ocr):
    s = l.strip()
    if len(s) < 3: continue
    # verso (even) pages: number first; recto (odd): number last. Running head may be merged with text.
    m = re.match(r'^(\d{1,3})\s+\S', s)
    if m and (len(s) <= 80 or HEADW.search(s[:60])) and int(m.group(1)) % 2 == 0 and 1 <= int(m.group(1)) <= 884:
        cands.append((i, int(m.group(1)))); continue
    m = re.search(r'\S\s+(\d{1,3})\.?$', s)
    if m and len(s) <= 80 and int(m.group(1)) % 2 == 1 and 1 <= int(m.group(1)) <= 884:
        cands.append((i, int(m.group(1))))
n = len(cands); dp = [1]*n; prev = [-1]*n
for j in range(n):
    for k in range(j):
        d = cands[j][1]-cands[k][1]
        if 1 <= d <= 45 and dp[k]+1 > dp[j]: dp[j] = dp[k]+1; prev[j] = k
j = max(range(n), key=lambda x: dp[x]); chain = []
while j != -1: chain.append(cands[j]); j = prev[j]
chain = chain[::-1]

# arabic pages: exact headers, gaps filled by header-like lines when the count fits, else approximate
pages = {}   # page number -> (ocr line index of header, exact?)
for ln, p in chain: pages[p] = (ln, True)
nums = [p for _, p in chain]
for a, b in zip(nums, nums[1:]):
    if b - a <= 1: continue
    la, lb = pages[a][0], pages[b][0]
    hs = [i for i in range(la+1, lb) if len(ocr[i].strip()) < 80 and HEADW.search(ocr[i])]
    if len(hs) == b-a-1:
        for k, i in enumerate(hs): pages[a+1+k] = (i, True)
    else:
        # proportional by characters
        tot = sum(len(ocr[i]) for i in range(la+1, lb))
        acc = 0; targets = [tot*(k+1)/(b-a) for k in range(b-a-1)]; t = 0
        for i in range(la+1, lb):
            acc += len(ocr[i])
            while t < len(targets) and acc >= targets[t]:
                pages[a+1+t] = (i+1, False); t += 1
        while t < len(targets): pages[a+1+t] = (lb, False); t += 1
first_arabic_line = pages[min(pages)][0]

# roman pages of the Vorrede (VII–XLIV): running heads "N Vorrede" / "zur zweyten Auflage N"
def lenient_roman(t):
    t = t.strip(' .,;:|“"\'-—').upper().replace('U', 'II').replace('H', 'II').replace('R', 'X').replace('K', 'X').replace('L', 'L')
    t = t.replace('1', 'I').replace('l', 'I')
    return unroman(t) if t and re.fullmatch(r'[XVIL]+', t) else None
rc = []
for i, l in enumerate(ocr[:first_arabic_line]):
    s = l.strip()
    if i < 19 or not re.search(r"([VB]orrede|Auflage)", s[:60]): continue
    m = re.match(r'^(\S+)\s+[—\-:]?\s*[VB]orrede', s)
    if m:
        p = lenient_roman(m.group(1)); rc.append((i, p if p and p % 2 == 0 else None)); continue
    if len(s) > 60: continue
    m = re.search(r'Auflage\S*\s+(.+)$', s)
    p = lenient_roman(m.group(1)) if m else None
    rc.append((i, p if p and p % 2 == 1 else None))
rpages = {}
lastp = 7
for i, p in rc:
    if p is not None and lastp < p <= 44 and p - lastp <= 4: rpages[p] = (i, True); lastp = p
vor = next((i for i, l in enumerate(ocr[19:first_arabic_line], 19) if re.match(r'^\s*[VB]orrede', l.strip()) and len(l.strip()) < 30), None)
if vor is not None: rpages[7] = (vor, True)
# unparsed head lines between known pages: use them in order if the count fits
known = sorted(rpages)
heads = [i for i, _ in rc]
for a, b in zip(known, known[1:]):
    if b - a <= 1: continue
    la, lb = rpages[a][0], rpages[b][0]
    hs = [i for i in heads if la < i < lb]
    if len(hs) == b - a - 1:
        for k, i in enumerate(hs): rpages[a+1+k] = (i, True)
    else:
        tot = sum(len(ocr[i]) for i in range(la+1, lb)); acc = 0
        targets = [tot*(k+1)/(b-a) for k in range(b-a-1)]; t = 0
        for i in range(la+1, lb):
            acc += len(ocr[i])
            while t < len(targets) and acc >= targets[t]:
                rpages[a+1+t] = (i+1, False); t += 1
# B 1: first page of the Einleitung has no running head
ein = next((i for i, l in enumerate(ocr[:first_arabic_line+5]) if re.match(r'^\s*Einleitung\.?\s*$', l)), None)
if ein is not None and 1 not in pages: pages[1] = (ein, True)
print('roman pages', len(rpages), sorted(rpages)[:5], 'exact', sum(1 for v in rpages.values() if v[1]), file=sys.stderr)

# ---------------- OCR tokens with header lines removed ----------------
header_lines = {ln for ln, _ in list(pages.values()) + list(rpages.values()) if ln < len(ocr) and len(ocr[ln].strip()) <= 60}
O = []; line_start = {}
for i, l in enumerate(ocr):
    line_start[i] = len(O)
    if i in header_lines: continue
    O.extend(l.split())
line_start[len(ocr)] = len(O)

# ---------------- Gutenberg ----------------
gl = open('pg6343.txt', encoding='utf8').read().replace('\r','').split('\n')
body_start = next(i for i, l in enumerate(gl) if l.strip().startswith('Instauratio magna'))
toc_start = next(i for i, l in enumerate(gl) if l.strip() == 'Inhalt')
end = next(i for i, l in enumerate(gl) if l.startswith('*** END'))
toc_lines = gl[toc_start+1:body_start]

toc = []
for l in toc_lines:
    if not l.strip(): continue
    ind = len(l) - len(l.lstrip())
    if toc and ind > toc[-1][0] + 2 and not re.match(r'\s*(§|\d+\.|[IVX]+\.|[A-D]\.)', l) and toc[-1][1][-1:] not in '.':
        # wrapped continuation of the previous entry
        if not re.match(r'\s*(Erst|Zweit|Dritt|Viert|Einleitung|Anhang|Widerlegung|Allgemeine|Anmerkung|Beschluß)', l):
            toc[-1][1] += ' ' + l.strip(); continue
    toc.append([ind, l.strip()])

def normh(s): return re.sub(r'[^a-zäöüß0-9§]', '', s.lower())

# blocks, with the number of blank lines before each
blocks = []   # [kind, text, blank_before, lines]
cur = []; blanks = 0; pend_blank = 0
def flush():
    global pend_blank
    if not cur: return
    first = cur[0]
    txt = ' '.join(x.strip() for x in cur)
    if re.match(r'\*+ ', first):
        kind = 'n'
    elif first.startswith('  ') and blocks and blocks[-1][0] == 'n' and not first.startswith('      '):
        kind = 'n'
    else:
        kind = ''
    blocks.append([kind, txt, pend_blank, [x.strip() for x in cur]]); cur.clear()
for l in gl[body_start:end]:
    if not l.strip():
        if cur: flush(); blanks = 0
        blanks += 1
    else:
        if not cur: pend_blank = blanks; blanks = 0
        cur.append(l)
flush()

def toc_level(lines):
    last = normh(lines[-1])
    best = None
    for ind, t in toc:
        nt = normh(t)
        if last and (nt.endswith(last) or last.endswith(nt)):
            best = ind; break
    return best

def headingish(b):
    ls = b[3]
    return len(ls) <= 5 and all(len(x) <= 80 for x in ls) and not re.search(r'[,;]$', ls[-1]) \
        and re.match(r'^[A-ZÄÖÜ§0-9IVX]', ls[0]) and not (len(ls) == 1 and len(ls[0]) > 60 and ls[0].endswith('.'))
for b in blocks:
    if b[0]: continue
    if b[2] >= 3 and headingish(b):
        b[0] = 'H'; lv = toc_level(b[3]); b.append(lv if lv is not None else 8)
        parts = [x.strip() for x in b[3]]
        t = parts[0]
        for x in parts[1:]:
            brk = re.match(r'(Erst|Zweit|Dritt|Viert|Fünft|Sechst|Siebent|Acht|Neunt|Von |Vom |Die |Der |Das |Des |Dem |Den |Transz|§|\(|Kritik|Analytik|Dialektik|Ästhetik|Logik|Anhang|Allgemeine|Methodenlehre|Elementarlehre|Systematische|System|Widerlegung|Auflösung|Erläuterung|Schlußanmerkung)', x)
            t = (t.rstrip('.') + '. ' + x) if brk and not re.search(r'[,(]$', t) else (t + ' ' + x)
        b[1] = t
    elif headingish(b) and (len(b[3]) > 1 or len(b[1]) < 70) and not b[1].endswith('.') or re.match(r'^§ \d+', b[1]) and len(b[1]) < 120:
        b[0] = 'h'
print('major headings', sum(1 for b in blocks if b[0]=='H'), 'blocks', len(blocks), file=sys.stderr)

# Gutenberg tokens with back-reference to block/offset
G = []; Gpos = []
for bi, b in enumerate(blocks):
    for m in re.finditer(r'\S+', b[1]):
        G.append(m.group()); Gpos.append((bi, m.start()))

# ---------------- alignment ----------------
SO = [skel(x) for x in O]; SG = [skel(x) for x in G]
an = anchors(SO, SG)
ao = [a for a, _ in an]; bo = [b for _, b in an]
def map_o2g(k):
    j = bisect.bisect_left(ao, k)
    if j < len(an) and ao[j] - k <= 3: return bo[j] - (ao[j] - k)
    if j > 0 and k - ao[j-1] <= 3: return bo[j-1] + (k - ao[j-1])
    if 0 < j < len(an):
        a0, b0 = an[j-1]; a1, b1 = an[j]
        return round(b0 + (k - a0) * (b1 - b0) / max(1, a1 - a0))
    return bo[min(j, len(bo)-1)]

breaks = []  # (gutenberg token index, label, exact)
for p, (ln, ex) in rpages.items():
    breaks.append((map_o2g(line_start[ln+1] if ln in header_lines else line_start[ln]), f'B {roman(p)}', ex))
for p, (ln, ex) in pages.items():
    k = line_start[ln+1] if ln in header_lines else line_start[ln]
    breaks.append((map_o2g(k), f'B {p}', ex))
breaks.sort()
def lkey(lab):
    v = lab[2:]
    return unroman(v) - 1000 if re.fullmatch(r'[XVIL]+', v) else int(v)
clean = []
for gi, lab, ex in breaks:
    k = lkey(lab)
    while clean and lkey(clean[-1][1]) >= k and ex and not clean[-1][2]:
        clean.pop()
    if clean and (lkey(clean[-1][1]) >= k or clean[-1][0] > gi):
        continue
    clean.append((gi, lab, ex))
breaks = clean
print('breaks', len(breaks), 'exact', sum(1 for b in breaks if b[2]), file=sys.stderr)

# insert markers into blocks
ins = {}
for gi, lab, ex in breaks:
    if gi >= len(Gpos): continue
    bi, off = Gpos[gi]
    ins.setdefault(bi, []).append((off, lab if ex else lab + '~'))

out_blocks = []
page = 'B I'
for bi, b in enumerate(blocks):
    txt = b[1]; marks = sorted(ins.get(bi, []))
    ref = page
    if marks and marks[0][0] == 0:
        ref = marks[0][1]; marks = marks[1:]
    pieces = []; pos = 0
    for off, lab in marks:
        pieces.append(txt[pos:off]); pieces.append('\u0001' + lab + '\u0002'); pos = off
    pieces.append(txt[pos:])
    t = ''.join(pieces).strip()
    allm = ins.get(bi, [])
    if allm: page = sorted(allm)[-1][1]
    out_blocks.append([ref, b[0], t] + b[4:])

# sections: TOC headings with indent <= 12 open a new section; deeper ones stay as in-text headings
secs = []
for ref, kind, t, *extra in out_blocks:
    if kind == 'H':
        title = re.sub(r'\u0001[^\u0002]*\u0002', '', t)
        lv = 1 if re.match(r'^(Vorrede|Einleitung$|Kritik der reinen Vernunft|I\. Transz|II\. Transz)', title) else \
             2 if re.search(r'(Teil|Abteilung)\b', title) and 'Hauptst' not in title and 'Abschnitt' not in title else \
             3 if re.search(r'\bBuch\b', title) and 'Hauptst' not in title and 'Abschnitt' not in title else \
             4 if 'Hauptst' in title and 'Abschnitt' not in title else \
             2 if re.match(r'^[IVX]+\. ', title) else 5 if re.match(r'^(§|[A-D]\. |\d+\. )', title) else 4
        secs.append({'title': title, 'level': lv, 'paras': []}); continue
    if not secs: secs.append({'title': 'Titelblatt', 'level': 1, 'paras': []})
    k = {'H': 'h', 'h': 'h', 'n': 'n', '': ''}[kind]
    secs[-1]['paras'].append([ref, k, t])
for i, s in enumerate(secs): s['id'] = f's{i+1}'
json.dump({'secs': secs}, open('krv_b.json', 'w', encoding='utf8'), ensure_ascii=False, separators=(',', ':'))
for s in secs:
    r = [p[0] for p in s['paras']]
    print(s['id'], '  '*(s['level']-1) + s['title'][:70], '|', len(s['paras']), '|', r[0] if r else '-', '–', r[-1] if r else '-')
