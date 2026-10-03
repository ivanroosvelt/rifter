# /// script
# requires-python = ">=3.10,<3.13"
# dependencies = ["allin1==1.1.0", "madmom @ git+https://github.com/CPJKU/madmom", "torch", "torchaudio<2.9"]
# [tool.uv]
# override-dependencies = ["natten; sys_platform == 'never'"]  # replaced by the shim below
# ///
# Song structure with allin1: periods = sections (verse, chorus…), fragments = groups of BARS bars.
# Usage: uv run ai/structure.py data/<id>.mp3  → prints the periods as JSON (checkpoint format).
import json
import os
import sys
import tempfile
import types

import torch

BARS = 4  # ponytail: fixed bars per fragment, make it a query param if people ask
NAMES = {'intro': 'Intro', 'verse': 'Estrofa', 'chorus': 'Estribillo', 'bridge': 'Puente', 'inst': 'Instrumental',
         'solo': 'Solo', 'outro': 'Outro', 'break': 'Break'}


# --- natten shim: the natten builds that allin1 imports from don't compile anymore, so this is
# the same neighborhood attention in plain torch (gather-based, more memory, same result).
def _window(n, k, d):
    # key indices (n, k) and relative-position-bias indices (n, k) along one axis, natten semantics:
    # positions attend within their dilation group, windows are shifted (not cropped) at the edges
    i = torch.arange(n)
    g, j = i % d, i // d
    glen = (n - g + d - 1) // d
    start = (j - k // 2).clamp(min=0).minimum(glen - k)
    kj = start[:, None] + torch.arange(k)
    return g[:, None] + kj * d, kj - j[:, None] + k - 1


def natten1dqkrpb(q, k, rpb, kernel_size, dilation):
    idx, b = _window(q.shape[2], kernel_size, dilation)
    return torch.einsum('bhld,bhlkd->bhlk', q, k[:, :, idx]) + rpb[:, b]


def natten1dav(attn, v, kernel_size, dilation):
    idx, _ = _window(v.shape[2], kernel_size, dilation)
    return torch.einsum('bhlk,bhlkd->bhld', attn, v[:, :, idx])


def natten2dqkrpb(q, k, rpb, kernel_size, dilation):
    (ix, bx), (iy, by) = _window(q.shape[2], kernel_size, dilation), _window(q.shape[3], kernel_size, dilation)
    s = torch.einsum('nhxyd,nhxaybd->nhxyab', q, k[:, :, ix][:, :, :, :, iy])
    s = s + rpb[:, bx[:, None, :, None], by[None, :, None, :]]
    return s.flatten(-2)


def natten2dav(attn, v, kernel_size, dilation):
    ix, _ = _window(v.shape[2], kernel_size, dilation)
    iy, _ = _window(v.shape[3], kernel_size, dilation)
    a = attn.unflatten(-1, (kernel_size, kernel_size))
    return torch.einsum('nhxyab,nhxaybd->nhxyd', a, v[:, :, ix][:, :, :, :, iy])


def install_shim():
    fn = types.ModuleType('natten.functional')
    fn.natten1dqkrpb, fn.natten1dav, fn.natten2dqkrpb, fn.natten2dav = natten1dqkrpb, natten1dav, natten2dqkrpb, natten2dav
    sys.modules['natten'] = types.ModuleType('natten')
    sys.modules['natten.functional'] = fn


def periods(r):
    out, seen = [], {}
    for s in r.segments:
        if s.label in ('start', 'end') or s.end - s.start < 1:
            continue  # silence before/after the song
        seen[s.label] = seen.get(s.label, 0) + 1
        bars = [t for t in r.downbeats if s.start - 0.2 <= t < s.end]  # sections start ~on a downbeat
        cuts = [s.start] + bars[BARS::BARS]
        if len(cuts) > 1 and s.end - cuts[-1] < (cuts[-1] - cuts[-2]) / 2:
            cuts.pop()  # a short leftover joins the previous fragment
        cuts.append(s.end)
        out.append({
            'name': f"{NAMES.get(s.label, s.label.capitalize())} {seen[s.label]}",
            'start': s.start, 'end': s.end,
            'children': [{'name': f'Compases {i * BARS + 1}–{(i + 1) * BARS}', 'start': a, 'end': b, 'children': []}
                         for i, (a, b) in enumerate(zip(cuts, cuts[1:]))] if len(cuts) > 2 else [],
        })
    return out


if __name__ == '__main__':
    install_shim()
    import allin1
    out = os.dup(1)
    os.dup2(2, 1)  # demucs runs as a subprocess and prints to stdout; keep stdout for the JSON only
    device = 'cuda' if torch.cuda.is_available() else 'mps' if torch.backends.mps.is_available() else 'cpu'
    with tempfile.TemporaryDirectory() as tmp:
        r = allin1.analyze(sys.argv[1], device=device, demix_dir=f'{tmp}/demix', spec_dir=f'{tmp}/spec', multiprocess=False)
    os.write(out, json.dumps(periods(r)).encode())
