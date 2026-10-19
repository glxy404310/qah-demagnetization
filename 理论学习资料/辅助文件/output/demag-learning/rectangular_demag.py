"""Uniform-M, open-boundary rectangular-prism magnetometric factors (SI).

Full side lengths, in any ONE common unit. Educational Newell self-term
expression, mathematically equivalent to the uniform-M Aharoni factors.
No micromagnetic relaxation is performed. Python standard library only.
Reference: Newell et al., doi:10.1029/93JB00694; OOMMF demagcoef.cc.
This compact double-precision expression is limited to aspect ratios <=1000
because cancellation degrades precision for very thin/elongated prisms.
Do not replace it with an ellipsoid approximation at larger aspect ratios.
"""
import argparse
import json
import math
from itertools import product

MU0 = 4 * math.pi * 1e-7  # Conventional micromagnetic value, H in A/m.


def newell_f(x, y, z):
    """Even Newell primitive, with zero-coordinate limits handled explicitly."""
    x, y, z = abs(x), abs(y), abs(z)
    r = math.hypot(x, y, z)
    terms = [(2*x*x-y*y-z*z)*r/6]
    if x*y*z:
        terms.append(-x*y*z*math.atan2(y*z, x*r))
    if y and math.hypot(x, z):
        terms.append(y*(z*z-x*x)/2*math.asinh(y/math.hypot(x, z)))
    if z and math.hypot(x, y):
        terms.append(z*(y*y-x*x)/2*math.asinh(z/math.hypot(x, y)))
    return math.fsum(terms)


def rectangular_factors(lx, ly, lz):
    """Return (Nx, Ny, Nz), without enforcing/renormalizing their sum."""
    dims = (lx, ly, lz)
    if any(not math.isfinite(v) or v <= 0 for v in dims):
        raise ValueError('All three full side lengths must be finite and positive')
    if max(dims)/min(dims) > 1000*(1+1e-12):
        raise ValueError('Aspect ratio >1000: use a stable/high-precision implementation')
    # N depends on ratios only; rescaling also prevents dimensional overflow.
    x, y, z = (v/max(dims) for v in dims)

    def nx(a, b, c):
        # Collapse the even 27-term second difference into eight corners.
        terms = [(-1)**(i+j+k)*newell_f(i*a, j*b, k*c)
                 for i, j, k in product((0, 1), repeat=3)]
        return 2*math.fsum(terms)/(math.pi*a*b*c)

    return nx(x, y, z), nx(y, x, z), nx(z, x, y)


def center_factors(lx, ly, lz):
    """Local center-point factors; NOT the volume-average energy factors."""
    x, y, z = (v/max(lx, ly, lz) for v in (lx, ly, lz))
    r = math.hypot(x, y, z)
    return tuple(2/math.pi*math.atan2(b*c, a*r)
                 for a, b, c in ((x, y, z), (y, x, z), (z, x, y)))


def check():
    """Compare against OOMMF's independently published Maple reference data."""
    references = [((1, 1, 1), 1/3),
                  ((50, 10, 1), 0.0218295764587138116277173625565),
                  ((1, 2, 3), 0.5387903059237144478495904059064),
                  ((2, 1, 3), 0.2783917160358925554090446248392),
                  ((3, 2, 1), 0.1828179780403929967413649692544)]
    reference_error = max(abs(rectangular_factors(*d)[0]-n) for d, n in references)
    if reference_error > 1e-10:
        raise AssertionError(f'Reference mismatch: {reference_error}')
    max_trace_error = 0.0
    for dims in ((1, 1, 1), (200, 200, 4), (400, 100, 4),
                 (1000, 1000, 1), (1000, 1, 1), (1, 30, 10)):
        n = rectangular_factors(*dims)
        max_trace_error = max(max_trace_error, abs(math.fsum(n)-1))
        assert all(0 <= v <= 1 for v in n), (dims, n)
        scaled = rectangular_factors(*(v*1e-9 for v in dims))
        assert max(abs(a-b) for a, b in zip(n, scaled)) < 1e-8
        swapped = rectangular_factors(dims[1], dims[0], dims[2])
        assert max(abs(a-b) for a, b in zip(n, (swapped[1], swapped[0], swapped[2]))) < 1e-8
    assert max_trace_error < 1e-8, max_trace_error
    return dict(reference_max_abs_error=reference_error,
                sampled_max_trace_error=max_trace_error,
                status='passed; analytic implementation only, no micromagnetic solver run')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('size_nm', nargs=3, type=float, metavar=('LX', 'LY', 'T'))
    parser.add_argument('--ms', type=float, default=3e5, help='Uniform Ms in A/m')
    parser.add_argument('--check', action='store_true', help='Also run reference checks')
    args = parser.parse_args()
    if not math.isfinite(args.ms) or args.ms <= 0:
        parser.error('--ms must be finite and positive')
    n = rectangular_factors(*args.size_nm)
    volume = math.prod(v*1e-9 for v in args.size_nm)
    result = dict(full_size_nm=args.size_nm, Ms_A_per_m=args.ms,
                  N_magnetometric=dict(zip('xyz', n)), sum_N=math.fsum(n),
                  N_center_point=dict(zip('xyz', center_factors(*args.size_nm))),
                  mean_Hd_A_per_m_for_separate_xyz_states=[-args.ms*v for v in n],
                  Ed_J_for_separate_xyz_states=[0.5*MU0*args.ms**2*volume*v for v in n])
    if args.check:
        result['verification'] = check()
    print(json.dumps(result, indent=2))
