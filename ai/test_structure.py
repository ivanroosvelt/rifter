# /// script
# requires-python = ">=3.10"
# dependencies = ["torch"]
# ///
# Checks the natten shim against natten's own window rule (get_window_start / get_pb_start in its C++ kernels)
# and against brute-force neighborhood attention. Run: uv run ai/test_structure.py
import torch
from structure import _window, natten1dqkrpb, natten1dav, natten2dqkrpb, natten2dav


def natten_start(i, n, k, d):  # transcribed from natten's CPU kernel
    ns = k // 2
    if d <= 1:
        return max(i - ns, 0) + (i + ns >= n) * (n - i - ns - 1)
    if i - ns * d < 0:
        return i % d
    if i + ns * d >= n:
        a = n // d * d
        return n - (n - a) + i % d - 2 * ns * d if i % d < n - a else a + i % d - k * d
    return i - ns * d


for n, k, d in [(5, 5, 1), (12, 5, 1), (23, 5, 2), (40, 5, 4), (31, 3, 3), (10, 5, 2)]:
    idx, b = _window(n, k, d)
    for i in range(n):
        assert idx[i].tolist() == [natten_start(i, n, k, d) + t * d for t in range(k)], (n, k, d, i)
        assert all(0 <= x < 2 * k - 1 for x in b[i].tolist())
        assert [(idx[i, t].item() - i) // d + k - 1 for t in range(k)] == b[i].tolist()

torch.manual_seed(0)
B, H, L, D, k, d = 2, 3, 17, 4, 5, 2
q, kk, v, rpb = torch.randn(B, H, L, D), torch.randn(B, H, L, D), torch.randn(B, H, L, D), torch.randn(H, 2 * k - 1)
s, idx = natten1dqkrpb(q, kk, rpb, k, d), _window(L, k, d)[0]
for i in range(L):
    for t, j in enumerate(idx[i].tolist()):
        assert torch.allclose(s[:, :, i, t], (q[:, :, i] * kk[:, :, j]).sum(-1) + rpb[:, (j - i) // d + k - 1], atol=1e-5)
a = s.softmax(-1)
assert torch.allclose(natten1dav(a, v, k, d)[:, :, 3], sum(a[:, :, 3, t, None] * v[:, :, j] for t, j in enumerate(idx[3].tolist())), atol=1e-5)

X, Y = 6, 11
q, kk, v, rpb = torch.randn(1, H, X, Y, D), torch.randn(1, H, X, Y, D), torch.randn(1, H, X, Y, D), torch.randn(H, 2 * k - 1, 2 * k - 1)
s = natten2dqkrpb(q, kk, rpb, k, 1)
ix, iy = _window(X, k, 1)[0], _window(Y, k, 1)[0]
x, y = 4, 9
for a_, i in enumerate(ix[x].tolist()):
    for b_, j in enumerate(iy[y].tolist()):
        want = (q[0, :, x, y] * kk[0, :, i, j]).sum(-1) + rpb[:, i - x + k - 1, j - y + k - 1]
        assert torch.allclose(s[0, :, x, y, a_ * k + b_], want, atol=1e-5)
a = s.softmax(-1)
want = sum(a[0, :, x, y, a_ * k + b_, None] * v[0, :, i, j] for a_, i in enumerate(ix[x].tolist()) for b_, j in enumerate(iy[y].tolist()))
assert torch.allclose(natten2dav(a, v, k, 1)[0, :, x, y], want, atol=1e-5)
print('ok')
