# Copyright 2022 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""A model of a waveguide bend, in ceviche."""

from typing import Tuple, List

from ceviche_challenges import defs
from ceviche_challenges import jax_model_base as model_base
from ceviche_challenges import modes
from ceviche_challenges import params as _params
from ceviche_challenges import units as u
from ceviche_challenges.waveguide_bend import spec as _spec

import numpy as np


class WaveguideBendModel(model_base.Model):
  """A planar waveguide bend with one design region, in ceviche."""

  def __init__(
      self,
      params: _params.CevicheSimParams,
      spec: _spec.WaveguideBendSpec,
  ):
    """Initializes a new waveguide bend model.

    See the module docstring in spec.py for more details on the specification
    of the waveguide bend model.

    Args:
      params: Parameters for the ceviche simulation.
      spec: Specification of the waveguide bend geometry.
    """
    self.params = params
    self.spec = spec
    extent_i, extent_j = spec.extent_ij(params.resolution)
    self._shape = (
        u.resolve(extent_i, params.resolution),
        u.resolve(extent_j, params.resolution),
    )
    self._make_bg_density_and_ports()

  def _make_bg_density_and_ports(self, init_design_region: bool = False):
    """Initializes background density and ports for the model.

    Args:
      init_design_region: `bool` specifying whether the pixels in the background
        density distribution that lie within the design region should be
        initialized to a non-zero value. If `True`, the pixels are initialized
        to a value of `1.0`.
    Side effects: Initializes `_density_bg`, an `np.ndarray` specifying the
      background material density distribution of the device. Initalizes
      `ports`, a `List[Port]` that specifies the ports of the device.
    """
    p = self.params
    s = self.spec

    density = np.zeros(self.shape)

    monitor_offset = u.resolve(s.input_monitor_offset, p.resolution)

    wg_extent = s.pml_width + u.resolve(s.wg_length, p.resolution)

    wg_center_x = s.wg_length + s.variable_region_size[0] / 2
    wg_min_x = s.pml_width + u.resolve(wg_center_x - s.wg_width / 2,
                                       p.resolution)
    wg_max_x = s.pml_width + u.resolve(wg_center_x + s.wg_width / 2,
                                       p.resolution)

    density[wg_min_x:wg_max_x, :wg_extent] = 1.0

    wg_center_y = s.wg_length + s.variable_region_size[1] / 2
    wg_min_y = s.pml_width + u.resolve(wg_center_y - s.wg_width / 2,
                                       p.resolution)
    wg_max_y = s.pml_width + u.resolve(wg_center_y + s.wg_width / 2,
                                       p.resolution)
    density[:wg_extent, wg_min_y:wg_max_y] = 1.0

    port1 = modes.WaveguidePort(
        x=s.pml_width + u.resolve(s.port_pml_offset, p.resolution),
        y=s.pml_width + u.resolve(wg_center_y, p.resolution),
        width=u.resolve(s.wg_width + 2 * s.wg_mode_padding, p.resolution),
        order=1,
        dir=defs.Direction.X_POS,
        offset=monitor_offset)
    port2 = modes.WaveguidePort(
        x=s.pml_width + u.resolve(wg_center_x, p.resolution),
        y=s.pml_width + u.resolve(s.port_pml_offset, p.resolution),
        width=u.resolve(s.wg_width + 2 * s.wg_mode_padding, p.resolution),
        order=1,
        dir=defs.Direction.Y_POS,
        offset=monitor_offset)

    if init_design_region:
      density[self.design_region] = 1.0

    self._density_bg = density
    self._ports = [port1, port2]

  @property
  def design_region_coords(self) -> Tuple[int, int, int, int]:
    """The coordinates of the design region as (x_min, y_min, x_max, y_max)."""
    s = self.spec
    p = self.params
    x_min = s.pml_width + u.resolve(s.wg_length, p.resolution)
    x_max = x_min + u.resolve(s.variable_region_size[0], p.resolution)
    y_min = s.pml_width + u.resolve(s.wg_length, p.resolution)
    y_max = y_min + u.resolve(s.variable_region_size[1], p.resolution)
    return (x_min, y_min, x_max, y_max)

  @property
  def shape(self) -> Tuple[int, int]:
    """Shape of the simulation domain, in grid units."""
    return self._shape

  @property
  def density_bg(self) -> np.ndarray:
    """The background density distribution of the model."""
    return self._density_bg

  @property
  def slab_permittivity(self) -> float:
    """The slab permittivity of the model."""
    s = self.spec
    return s.slab_permittivity

  @property
  def cladding_permittivity(self) -> float:
    """The cladding permittivity of the model."""
    s = self.spec
    return s.cladding_permittivity

  @property
  def dl(self) -> float:
    """The grid resolution of the model."""
    p = self.params
    return p.resolution.to_value('m')

  @property
  def pml_width(self) -> int:
    """The width of the PML region, in grid units."""
    s = self.spec
    return s.pml_width

  @property
  def ports(self) -> List[modes.Port]:
    """A list of the device ports."""
    return self._ports

  @property
  def output_wavelengths(self) -> List[float]:
    """A list of the wavelengths, in nm, to output fields and s-parameters."""
    return u.Array(self.params.wavelengths).to_value(u.nm)
