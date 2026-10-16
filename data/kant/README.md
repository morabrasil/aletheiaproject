# Kant — German text (first editions)

Source: Deutsches Textarchiv (DTA), https://www.deutschestextarchiv.de — TEI-P5 transcriptions of the first editions:
- `krv_a.json`: *Critik der reinen Vernunft*, Riga: Hartknoch, 1781 (A). DTA id `kant_rvernunft_1781`.
- `ku_a.json`: *Critik der Urtheilskraft*, Berlin und Libau: Lagarde und Friederich, 1790 (A). DTA id `kant_urtheilskraft_1790`.

The DTA transcriptions are distributed under Creative Commons Attribution-ShareAlike 4.0 (CC BY-SA 4.0); these derived files are distributed under the same license.
Changes (`tools/convert_dta.py`): XML converted to JSON; running heads and catchwords removed; end-of-line hyphenation joined; long s (ſ) and vowels with superscript e normalized (ä, ö, ü); editorial corrections (<corr>) used instead of printing errors. Original spelling otherwise kept. Page numbers of the original edition kept as reference markers.

## Critique of Pure Reason, 2nd edition (B, 1787) — `krv_b.json`

- Text: Project Gutenberg eBook #6343 (*Kritik der reinen Vernunft*, 2nd ed.), derived from Projekt Gutenberg-DE (prepared by Gerd Bouillon); public domain. Spelling: the 1787 period spelling was restored automatically (`tools/restore_spelling_b.py`): each modern word is replaced by its period form found in Kant's first editions (KrV A 1781, KU 1790, DTA); when several forms exist, the OCR of the 1787 scan decides. Isolated modern forms may remain.
- B pagination: transferred automatically (`tools/build_b.py`, `tools/align.py`) from the OCR of a scan of the 1787 edition (Ghent University copy, digitized by Google, Internet Archive item `bub_gb_qZEPAAAAQAAJ`, Public Domain Mark). The running heads of the scan give the page numbers; the two texts are aligned word by word to place each break. About 12% of the breaks could not be read from the scan and are interpolated; they carry a `~` flag and are shown as approximate.
