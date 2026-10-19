"""Fidimag zero-field thin-film relaxation teaching example.

Requires a working Fidimag installation. Parameters are hypothetical.
Run from a new results directory: python /path/to/thinfilm_fidimag.py
API checked against official sources on 2026-10-19; not executed with Fidimag here.
"""
import json
import math
import warnings
from importlib.metadata import version, PackageNotFoundError
import numpy as np
from fidimag.common import CuboidMesh
from fidimag.micro import Sim, UniformExchange, UniaxialAnisotropy, Demag, Zeeman

MU0 = 4*math.pi*1e-7
MS, A, KU = 3e5, 5e-12, 8e4
# 200 nm x 200 nm x 4 nm. Open boundaries; not a periodic film.
mesh = CuboidMesh(nx=100, ny=100, nz=2,
                  dx=2, dy=2, dz=2, unit_length=1e-9)
sim = Sim(mesh, name='teaching_thinfilm', driver='llg')
sim.Ms = MS
sim.driver.alpha = 0.5
sim.driver.gamma = 2.21e5
sim.driver.do_precession = False  # Numerical relaxation, not physical time.
sim.driver.set_tols(rtol=1e-8, atol=1e-10)
sim.add(UniformExchange(A=A))
sim.add(UniaxialAnisotropy(Ku=KU, axis=(0, 0, 1)))
sim.add(Demag())
sim.add(Zeeman((0, 0, 0)))  # Fidimag micro expects A/m.
sim.set_m((0.01, 0, 1), normalise=True)

# Convert max_steps warnings into errors rather than delivering an unconverged state.
with warnings.catch_warnings():
    warnings.simplefilter('error', RuntimeWarning)
    sim.relax(dt=1e-12, stopping_dmdt=0.01, max_steps=20000,
              save_m_steps=None, save_vtk_steps=None)

sim.save_m()
sim.save_vtk()
m = sim.spin.reshape((-1, 3))
sim.compute_effective_field(sim.driver.t)
heff = sim.field.reshape((-1, 3))
# Independent instantaneous RHS check, avoids confusing observation intervals
# with the adaptive solver's internal time steps.
torque = np.cross(m, heff)
alpha = 0.5
rhs = -sim.driver.gamma/(1+alpha**2)*alpha*np.cross(m, torque)
max_rate_deg_ns = float(np.max(np.linalg.norm(rhs, axis=1))*1e-9*180/math.pi)
if max_rate_deg_ns > 0.01:
    raise RuntimeError(f'Instantaneous RHS is {max_rate_deg_ns:.4g} deg/ns; refine relaxation')
energies = {term.name: float(term.compute_energy()) for term in sim.interactions}
try:
    fidimag_version = version('fidimag')
except PackageNotFoundError:
    fidimag_version = 'record checkout commit manually'
summary = dict(
    model='hypothetical teaching parameters, zero temperature',
    fidimag_version=fidimag_version,
    Ms_A_per_m=MS, A_J_per_m=A, Ku_J_per_m3=KU,
    cell_nm=[2,2,2], cells=[100,100,2],
    alpha_relax=alpha, precession=False,
    mean_m=m.mean(axis=0).tolist(),
    max_norm_error=float(np.max(np.abs(np.linalg.norm(m,axis=1)-1))),
    instantaneous_max_rate_deg_per_ns=max_rate_deg_ns,
    energies_J=energies)
with open('thinfilm_summary.json','w',encoding='utf-8') as f:
    json.dump(summary,f,ensure_ascii=False,indent=2)
print(json.dumps(summary,ensure_ascii=False,indent=2))
