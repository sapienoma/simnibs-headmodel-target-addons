# SPDX-License-Identifier: GPL-3.0-only
# SimNIBS Head-Model Tools Suite; license notices added 2026-10-27.
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3 only.
# This program is distributed WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the accompanying LICENSE file for the full license text.
# Existing third-party copyright and license notices remain applicable.
"""Coordinate transformation glue; uses only the current subject's toMNI warps."""
from ui_language import tr
from pathlib import Path
import numpy as np

def transform_mni(mni,m2m):
    from simnibs import mni2subject_coords,subject2mni_coords
    p=np.asarray(mni,float)
    if p.shape!=(3,) or not np.isfinite(p).all():raise ValueError(tr('Enter three finite MNI mm coordinates.'))
    m2m=Path(m2m)
    if not (m2m/'toMNI').is_dir():raise ValueError(tr('No toMNI transforms in this m2m. A .msh alone cannot transform MNI coordinates.'))
    native=np.asarray(mni2subject_coords(p,str(m2m),transformation_type='nonl'),float).reshape(3)
    if not np.isfinite(native).all():raise ValueError(tr('Nonlinear transform returned invalid values.'))
    back=np.asarray(subject2mni_coords(native,str(m2m),transformation_type='nonl'),float).reshape(3)
    error=float(np.linalg.norm(back-p))
    if not np.isfinite(error):raise ValueError(tr('Coordinate round-trip check failed.'))
    return native,dict(type='nonl',MNI_mm=p.tolist(),native_brain_mm=native.tolist(),
                       roundtrip_MNI_mm=back.tolist(),roundtrip_error_mm=error,
                       m2m=str(m2m.resolve()),note='Geometric scalp projection is not E-field optimization.')
