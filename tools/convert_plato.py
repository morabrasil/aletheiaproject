"""Converte os diálogos de Platão (Perseus, ed. Burnet) para o formato do aletheia project.

Saída: um JSON por obra em OUT/<id>.json:
  {"id","secs":[{"id","paras":[[ref, speaker, text]]}]}
No texto, marcos de Stephanus internos ao parágrafo vêm como \u0001<ref>\u0002 e
quebras de verso como \n. Supressões do editor ficam entre [ ], acréscimos entre ⟨ ⟩.
"""
import glob, json, os, re, sys
import xml.etree.ElementTree as ET

T = '{http://www.tei-c.org/ns/1.0}'
SRC = sys.argv[1]
OUT = sys.argv[2]
os.makedirs(OUT, exist_ok=True)

SKIP = {T + 'bibl', T + 'head', T + 'note'}


class Para:
    def __init__(self, start_ref):
        self.ref = None          # section in force where the paragraph's text starts
        self.start_ref = start_ref
        self.speaker = ''
        self.buf = []
        self.has_text = False

    def text(self, s):
        if not s:
            return
        if s.strip():
            if not self.has_text:
                self.has_text = True
                if self.ref is None:
                    self.ref = self.start_ref
        self.buf.append(s)


def walk(el, para, state):
    tag = el.tag
    if tag in SKIP:
        return
    if tag == T + 'milestone':
        if el.get('unit') == 'section':
            n = el.get('n')
            if para.has_text:
                para.buf.append('\u0001' + n + '\u0002')
            else:
                para.ref = n
            state['ref'] = n
        return
    if tag == T + 'label':
        para.speaker = ''.join(el.itertext()).strip()
        return
    if tag == T + 'gap':
        para.text(' … ')
        return
    if tag == T + 'del':
        para.text('[')
    elif tag == T + 'add':
        para.text('⟨')
    elif tag == T + 'l' and para.has_text:
        para.buf.append('\n')
    para.text(el.text)
    for c in el:
        walk(c, para, state)
        para.text(c.tail)
    if tag == T + 'del':
        para.text(']')
    elif tag == T + 'add':
        para.text('⟩')
    elif tag == T + 'l':
        para.buf.append('\n')


def clean(s):
    s = re.sub(r'[ \t\r]*\n[ \t\r]*', '\n', s)
    # newlines that are just XML formatting inside prose -> space
    parts = s.split('\n')
    s = '\n'.join(parts)
    s = re.sub(r'[ \t\r]+', ' ', s)
    s = re.sub(r'\n{2,}', '\n', s)
    s = re.sub(r' *\n *', '\n', s)
    s = re.sub(r' +([,.;·:\]⟩])', r'\1', s)
    s = re.sub(r'([\[⟨]) +', r'\1', s)
    return s.strip('\n ').strip()


def paragraphs(container, state):
    out = []
    for p in container.iter(T + 'p'):
        para = Para(state['ref'])
        para.text(p.text)
        for c in p:
            walk(c, para, state)
            para.text(c.tail)
        raw = ''.join(para.buf)
        # prose: XML line breaks are not meaningful unless they came from <l>
        has_verse = any(True for _ in p.iter(T + 'l'))
        if not has_verse:
            raw = raw.replace('\n', ' ')
        txt = clean(raw)
        if not txt:
            continue
        out.append([para.ref or state['ref'] or '', para.speaker, txt])
    return out


report = []
for f in sorted(glob.glob(os.path.join(SRC, 'tlg0*/*grc*.xml'))):
    wid = os.path.basename(os.path.dirname(f))
    root = ET.parse(f).getroot()
    body = root.find(f'.//{T}body')
    edition = body.find(f'{T}div')
    state = {'ref': ''}
    tops = [d for d in edition if d.tag == T + 'div' and d.get('subtype') in ('book', 'letter')]
    secs = []
    if tops:
        for d in tops:
            secs.append({'id': d.get('subtype')[0] + d.get('n'), 'paras': paragraphs(d, state)})
    else:
        secs.append({'id': 'text', 'paras': paragraphs(edition, state)})
    data = {'id': wid, 'secs': secs}
    with open(os.path.join(OUT, wid + '.json'), 'w', encoding='utf8') as fh:
        json.dump(data, fh, ensure_ascii=False, separators=(',', ':'))
    # stats for checking
    src_chars = len(re.sub(r'\s+', '', ''.join(
        t for p in body.iter(T + 'p') for t in p.itertext())))
    out_chars = sum(len(re.sub(r'\s+|\u0001[^\u0002]*\u0002|[\[\]⟨⟩…]', '', x[1] + x[2]))
                    for s in secs for x in s['paras'])
    refs = [x[0] for s in secs for x in s['paras']]
    report.append((wid, len(secs), sum(len(s['paras']) for s in secs), refs[0], refs[-1], src_chars, out_chars))

for r in report:
    print(*r, sep='\t')
