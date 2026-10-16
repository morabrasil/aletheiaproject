"""Converte um texto TEI-P5 do Deutsches Textarchiv (DTA) para o formato do aletheia project.

Uso: python3 convert_dta.py ENTRADA.xml SAIDA.json PREFIXO_PAGINA [OFFSET_ROMANO]
  PREFIXO_PAGINA: "A" ou "B" para a Crítica da razão pura, por exemplo.
  OFFSET_ROMANO: para páginas preliminares sem número, página = nº do fac-símile - OFFSET.

Saída: {"secs":[{"id","title","level","paras":[[ref, tipo, texto]]}]}
  tipo: "" parágrafo, "h" título interno, "n" nota de rodapé, "i" item de lista.
  No texto: \u0001<pág>\u0002 marca quebra de página; \u0003…\u0004 marca ênfase.
Normalização: ſ→s, vogal + e sobrescrito → trema, ꝛc. → etc., hifenização de fim de linha desfeita.
A grafia do original (Critik, Urtheil, seyn) é mantida.
"""
import json, re, sys
import xml.etree.ElementTree as ET

T = '{http://www.tei-c.org/ns/1.0}'
src, out, prefix = sys.argv[1], sys.argv[2], sys.argv[3]
roman_offset = int(sys.argv[4]) if len(sys.argv) > 4 else None
MIN_PAGES_TO_SPLIT = 30

ROM = [(1000,'M'),(900,'CM'),(500,'D'),(400,'CD'),(100,'C'),(90,'XC'),(50,'L'),(40,'XL'),(10,'X'),(9,'IX'),(5,'V'),(4,'IV'),(1,'I')]
def roman(n):
    s = ''
    for v, r in ROM:
        while n >= v:
            s += r; n -= v
    return s

def norm_text(s):
    s = s.replace('ſ', 's').replace('ꝛc.', 'etc.').replace('ꝛ', 'r')
    s = re.sub(r'([aouAOU])ͤ', lambda m: {'a':'ä','o':'ö','u':'ü','A':'Ä','O':'Ö','U':'Ü'}[m.group(1)], s)
    return s.replace('ͤ', '')

LABELS = {}
def precompute_pages(text):
    pbs = list(text.iter(T + 'pb'))
    def facs(pb):
        m = re.search(r'(\d+)$', pb.get('facs', '')); return int(m.group(1)) if m else None
    def arabic(pb):
        n = (pb.get('n') or '').strip('[]')
        return int(n) if n.isdigit() else None
    for i, pb in enumerate(pbs):
        n = pb.get('n')
        if n:
            LABELS[id(pb)] = f'{prefix} {n.strip("[]")}'; continue
        f = facs(pb); lab = ''
        if f is not None:
            nxt = next((q for q in pbs[i+1:] if arabic(q) is not None and facs(q) is not None), None)
            if nxt is not None:
                guess = arabic(nxt) - (facs(nxt) - f)
                if guess >= 1:
                    lab = f'{prefix} {guess}'
            if not lab and roman_offset is not None and f - roman_offset >= 1:
                lab = f'{prefix} {roman(f - roman_offset)}'
        LABELS[id(pb)] = lab

def page_label(pb):
    return LABELS.get(id(pb), '')

state = {'page': ''}
SKIP = {T + 'fw', T + 'figure', T + 'ref'}
EMPH = {'#g', '#i', '#b'}

class Block:
    def __init__(self, kind=''):
        self.kind = kind
        self.ref = None
        self.buf = []
        self.has_text = False
        self.notes = []
    def text(self, s):
        if not s: return
        if s.strip() and not self.has_text:
            self.has_text = True
            if self.ref is None: self.ref = state['page']
        self.buf.append(s)

def inline(el, blk):
    tag = el.tag
    if tag in SKIP: return
    if tag == T + 'pb':
        lab = page_label(el)
        if lab:
            if blk.has_text: blk.buf.append('\u0001' + lab + '\u0002')
            else: blk.ref = lab
            state['page'] = lab
        return
    if tag == T + 'lb':
        blk.buf.append('\n'); return
    if tag == T + 'note':
        mark = el.get('n') or '*'
        blk.text(mark)
        nb = Block('n'); nb.ref = state['page']; nb.text(mark + ' ')
        for c in [el]:
            nb.text(c.text)
            for cc in c: inline(cc, nb); nb.text(cc.tail)
        blk.notes.append(nb)
        return
    if tag == T + 'choice':
        corr = el.find(T + 'corr')
        reg = el.find(T + 'reg')
        use = corr if corr is not None else reg if reg is not None else el.find(T + 'sic')
        if use is not None:
            blk.text(use.text)
            for c in use: inline(c, blk); blk.text(c.tail)
        return
    if tag == T + 'gap':
        blk.text(' … '); return
    emph = tag == T + 'hi' and bool(EMPH & set((el.get('rendition') or '').split()))
    if emph: blk.buf.append('\u0003')
    blk.text(el.text)
    for c in el:
        inline(c, blk); blk.text(c.tail)
    if emph: blk.buf.append('\u0004')

def finish(blk):
    s = ''.join(blk.buf)
    s = re.sub(r'[-¬]\s*\n\s*(?=[a-zäöüßſ\u0003\u0001])', '', s)   # end-of-line hyphenation
    s = re.sub(r'[-¬]\s*\n\s*(\u0001[^\u0002]*\u0002)\s*', r'\1', s)
    s = s.replace('\n', ' ')
    s = re.sub(r'(\w)[-¬]\s*(\u0001[^\u0002]*\u0002)\s*(?=[a-zäöüßſ])', r'\1\2', s)
    s = norm_text(s)
    s = re.sub(r'\s+', ' ', s).strip()
    s = re.sub(r'\u0003\s*\u0004', '', s)
    s = re.sub(r'\s+([,.;:!?)])', r'\1', s)
    return s

def blocks_of(el, out_list):
    """Walk block-level content of a div (not entering child divs)."""
    for c in el:
        tag = c.tag
        if tag == T + 'div':
            continue
        if tag == T + 'pb':
            lab = page_label(c)
            if lab: state['page'] = lab
            continue
        if tag in SKIP or tag == T + 'lb' or tag == T + 'milestone':
            continue
        if tag in (T + 'p', T + 'head', T + 'item', T + 'salute', T + 'byline', T + 'dateline', T + 'docAuthor', T + 'titlePart', T + 'docImprint', T + 'docDate'):
            kind = {T + 'head': 'h', T + 'item': 'i'}.get(tag, '')
            blk = Block(kind)
            blk.text(c.text)
            for cc in c: inline(cc, blk); blk.text(cc.tail)
            txt = finish(blk)
            if txt: out_list.append([blk.ref or state['page'], kind, txt])
            for nb in blk.notes:
                nt = finish(nb)
                if nt: out_list.append([nb.ref or state['page'], 'n', nt])
            continue
        # containers: list, opener, closer, titlePage, docTitle, quote, lg ...
        blocks_of(c, out_list)

def head_text(div):
    h = div.find(T + 'head')
    if h is None:
        return ''
    b = Block(); b.text(h.text)
    for c in h:
        if c.tag == T + 'pb' or c.tag == T + 'note': continue
        inline(c, b); b.text(c.tail)
    return re.sub(r'[\u0001-\u0004]|\u0001[^\u0002]*\u0002', '', finish(b))

def pages_in(div):
    return sum(1 for _ in div.iter(T + 'pb'))

secs = []
def add_section(div, level, title):
    paras = []
    blocks_of(div, paras)
    # first paragraph that only repeats the section heading is dropped (shown as section title)
    if paras and paras[0][1] == 'h' and title and paras[0][2].strip() == title.strip():
        paras = paras[1:]
    return paras

def splittable(div):
    kids = [c for c in div if c.tag == T + 'div']
    if not kids or pages_in(div) <= MIN_PAGES_TO_SPLIT or len(kids) > 15:
        return False
    return all(head_text(k) for k in kids)

def collect(div, paras):
    """All content of div in document order, child divs flattened (their heads become 'h' paragraphs)."""
    for c in div:
        if c.tag == T + 'div':
            collect(c, paras)
        else:
            fake = ET.Element('x'); fake.append(c)
            blocks_of(fake, paras)

def walk(container, level):
    for c in container:
        if c.tag != T + 'div':
            fake = ET.Element('x'); fake.append(c)
            tmp = []
            blocks_of(fake, tmp)
            if tmp and secs: secs[-1]['paras'].extend(tmp)
            continue
        div = c
        title = head_text(div) or {'dedication': 'Zueignung', 'contents': 'Inhalt'}.get(div.get('type'), '')
        if not title and secs:
            collect(div, secs[-1]['paras'])          # untitled block: continue previous section
            continue
        if splittable(div):
            sec = {'title': title, 'level': level, 'paras': []}
            secs.append(sec)
            # own content before the first child div, then children in order
            for cc in div:
                if cc.tag == T + 'div':
                    break
                fake = ET.Element('x'); fake.append(cc)
                blocks_of(fake, sec['paras'])
            rest = []
            started = False
            sub = ET.Element('x')
            for cc in div:
                if cc.tag == T + 'div': started = True
                if started: sub.append(cc)
            walk(sub, level + 1)
        else:
            paras = []
            collect(div, paras)
            secs.append({'title': title, 'level': level, 'paras': paras})
        sec = secs[-1] if False else None
        for s_ in secs[-1:]:
            if s_['paras'] and s_['paras'][0][1] == 'h' and re.sub(r'[\u0001-\u0004]','',s_['paras'][0][2]) == s_['title']:
                s_['paras'] = s_['paras'][1:]

root = ET.parse(src).getroot()
text = root.find(f'.//{T}text')
precompute_pages(text)
front = text.find(T + 'front'); body = text.find(T + 'body'); back = text.find(T + 'back')
# initial page state from pbs before the body
for part in [front, body, back]:
    if part is None: continue
    # stray pb/content directly in front (title page etc.)
    tp = part.find(T + 'titlePage')
    if tp is not None:
        for pb in part.iter(T + 'pb'):
            lab = page_label(pb)
            if lab: state['page'] = lab
            break
        paras = []
        blocks_of(tp, paras)
        secs.append({'title': 'Titelblatt', 'level': 1, 'paras': paras})
    walk(part, 1)

# drop empty sections without text, assign ids
clean = []
for i, s in enumerate(secs):
    if not s['paras']:
        if s['title'] and i + 1 < len(secs) and secs[i + 1]['level'] > s['level']:
            s['paras'] = []
        else:
            continue
    clean.append(s)
for i, s in enumerate(clean):
    s['id'] = f's{i + 1}'
json.dump({'secs': clean}, open(out, 'w', encoding='utf8'), ensure_ascii=False, separators=(',', ':'))
for s in clean:
    refs = [p[0] for p in s['paras']]
    print(s['id'], '  ' * (s['level'] - 1) + s['title'][:70], '|', len(s['paras']), '|', refs[0] if refs else '-', '–', refs[-1] if refs else '-')
