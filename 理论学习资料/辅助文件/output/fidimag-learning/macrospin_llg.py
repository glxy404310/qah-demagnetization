"""One-spin LLG benchmark. Standard library only; no Fidimag required.

Run: python macrospin_llg.py
Writes CSV, an SVG figure, and a numerical verification report next to this file.
This is a zero-temperature, constant-field teaching model, not a thin-film model.
"""
from pathlib import Path
import csv
import json
import math

MU0 = 4 * math.pi * 1e-7
GAMMA_H = 2.21e5  # m/(A s); pair with H in A/m
B_APPLIED = 0.1   # T; means mu0 * H_applied
H = (0.0, 0.0, B_APPLIED / MU0)
T_END = 2e-9

def cross(a, b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2],
            a[0]*b[1]-a[1]*b[0])

def rhs(m, alpha):
    p = cross(m, H)
    d = cross(m, p)
    return tuple(-GAMMA_H/(1+alpha*alpha)*(p[i]+alpha*d[i])
                 for i in range(3))

def add(a, b, c):
    return tuple(a[i]+c*b[i] for i in range(3))

def integrate(alpha, dt):
    m = (1.0, 0.0, 0.0)
    n = round(T_END/dt)
    rows = [(0.0, *m)]
    for j in range(n):
        k1 = rhs(m, alpha)
        k2 = rhs(add(m, k1, dt/2), alpha)
        k3 = rhs(add(m, k2, dt/2), alpha)
        k4 = rhs(add(m, k3, dt), alpha)
        m = tuple(m[i]+dt*(k1[i]+2*k2[i]+2*k3[i]+k4[i])/6
                  for i in range(3))
        # No projection: monitor length conservation independently.
        rows.append(((j+1)*dt, *m))
    return rows

def exact(t, alpha):
    omega = GAMMA_H*H[2]/(1+alpha*alpha)
    transverse = 1/math.cosh(alpha*omega*t)
    return (transverse*math.cos(omega*t),
            transverse*math.sin(omega*t), math.tanh(alpha*omega*t))

def main():
    out = Path(__file__).resolve().parent / 'macrospin_results'
    out.mkdir(exist_ok=True)
    summary = {}
    for alpha in (0.0, 0.1, 0.5):
        rows = integrate(alpha, 1e-13)
        fine = integrate(alpha, 5e-14)
        err = max(max(abs(row[i+1]-exact(row[0],alpha)[i])
                      for i in range(3)) for row in rows)
        drift = max(abs(math.sqrt(sum(x*x for x in row[1:]))-1)
                    for row in rows)
        refine = max(max(abs(a[i]-b[i]) for i in (1,2,3))
                     for a,b in zip(rows,fine[::2]))
        energy_increase = max(-(rows[j+1][3]-rows[j][3])
                              for j in range(len(rows)-1))
        summary[str(alpha)] = dict(max_component_error=err,
                                   max_length_error=drift,
                                   dt_halving_difference=refine,
                                   max_increase_normalised_zeeman=energy_increase,
                                   final_m=rows[-1][1:])
        assert err < 1e-8 and drift < 1e-8 and refine < 1e-8
        assert energy_increase < 1e-10
        with (out/f'alpha_{alpha:g}.csv').open('w',newline='') as f:
            w=csv.writer(f); w.writerow(['t_s','mx','my','mz']); w.writerows(rows)
    (out/'verification.json').write_text(json.dumps(summary,indent=2))
    # Deterministic scientific plot of the calculated trajectories.
    parts=['<svg xmlns="http://www.w3.org/2000/svg" width="900" height="330" viewBox="0 0 900 330">',
           '<rect width="900" height="330" fill="white"/>',
           '<g font-family="Arial,sans-serif" font-size="15" fill="#222">']
    for offset,component,title in [(0,1,'Precession and damping: mx'),(455,3,'Alignment with field: mz')]:
        x0,y0,w,h=offset+60,40,355,225
        for val in (-1,0,1):
            yy=y0+h*(1-val)/2
            parts.append(f'<path d="M{x0},{yy}H{x0+w}" stroke="#ddd"/>')
            parts.append(f'<text x="{x0-12}" y="{yy+5}" text-anchor="end">{val}</text>')
        parts.append(f'<text x="{x0}" y="22">{title}</text>')
        for alpha,color in [(0.0,'#9a9a9a'),(0.1,'#1b668c'),(0.5,'#bc5b2d')]:
            data=integrate(alpha,1e-12)
            points=' '.join(f'{x0+r[0]/T_END*w:.2f},{y0+(1-r[component])*h/2:.2f}' for r in data[::4])
            parts.append(f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="1.8"/>')
        for ns in (0,1,2):
            xx=x0+ns/2*w
            parts.append(f'<text x="{xx}" y="286" text-anchor="middle">{ns}</text>')
        parts.append(f'<text x="{x0+w/2}" y="309" text-anchor="middle">Time (ns)</text>')
    parts.append('<text x="450" y="329" text-anchor="middle">alpha = 0 (grey), 0.1 (blue), 0.5 (orange); applied mu0 H = 0.1 T</text></g></svg>')
    (out/'llg_trajectory.svg').write_text(''.join(parts),encoding='utf-8')
    print(json.dumps(summary,indent=2))

if __name__ == '__main__':
    main()
