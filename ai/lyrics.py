# /// script
# requires-python = ">=3.10"
# dependencies = ["faster-whisper", "av<16"]
# ///
# Split by lyrics with Whisper: fragments = sung lines, periods = runs of lines separated by an instrumental gap.
# Usage: uv run ai/lyrics.py data/<id>.mp3  → prints the periods as JSON (checkpoint format).
import json
import sys

GAP = 8  # seconds without singing that start a new period


def cp(name, start, end):
    return {'name': name, 'start': start, 'end': end, 'children': []}


def periods(lines, end):
    # lines: [(start, end, text)] → periods covering the whole song; long gaps become "Instrumental"
    out, t, n = [], 0.0, 0
    for s, e, text in lines:
        if not out or s - t > GAP:
            if s - t > GAP:
                out.append(cp('Instrumental', t, s))
                t = s
            n += 1
            out.append(cp(f'Parte {n}', t, e))
        out[-1]['end'] = e
        out[-1]['children'].append(cp(text.strip()[:60] or '…', s, e))
        t = e
    if end - t > GAP:
        out.append(cp('Instrumental', t, end))
    elif out:
        out[-1]['end'] = end
    return out


def test():
    p = periods([(10, 12, ' a'), (12.5, 14, 'b'), (40, 42, 'c')], 43)
    assert [(x['name'], x['start'], x['end'], len(x['children'])) for x in p] == \
        [('Instrumental', 0, 10, 0), ('Parte 1', 10, 14, 2), ('Instrumental', 14, 40, 0), ('Parte 2', 40, 43, 1)], p
    assert p[1]['children'][0]['name'] == 'a'
    assert periods([(1, 2, 'x')], 3) == [cp('Parte 1', 0, 3) | {'children': [cp('x', 1, 2)]}]
    assert periods([], 100) == [cp('Instrumental', 0, 100)]


if __name__ == '__main__':
    if sys.argv[1] == '--test':
        sys.exit(test())
    from faster_whisper import WhisperModel
    # no vad_filter: Silero VAD drops sung vocals. Word timestamps tighten each line's edges.
    segs, info = WhisperModel('small', compute_type='int8').transcribe(sys.argv[1], word_timestamps=True)
    lines = [(s.words[0].start, s.words[-1].end, s.text) for s in segs if s.words and any(c.isalpha() for c in s.text)]
    print(json.dumps(periods(lines, info.duration)))
