"""
Copyright @ 2017, 2020, 2021 United States Government as represented by the Administrator of the National Aeronautics and Space Administration. All Rights Reserved.
This software may be used, reproduced, and provided to others only as permitted under the terms of the agreement under which it was acquired from the U.S. Government. Neither title to, nor ownership of, the software is hereby transferred. This notice shall remain on all copies of the software.
This file is available under the terms of the NASA Open Source Agreement (NOSA), and further subject to the additional disclaimer below:
Disclaimer:
THE SOFTWARE AND/OR TECHNICAL DATA ARE PROVIDED "AS IS" WITHOUT ANY WARRANTY OF ANY KIND, EITHER EXPRESSED, IMPLIED, OR STATUTORY, INCLUDING, BUT NOT LIMITED TO, ANY WARRANTY THAT THE SOFTWARE AND/OR TECHNICAL DATA WILL CONFORM TO SPECIFICATIONS, ANY IMPLIED WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, OR FREEDOM FROM INFRINGEMENT, ANY WARRANTY THAT THE SOFTWARE AND/OR TECHNICAL DATA WILL BE ERROR FREE, OR ANY WARRANTY THAT TECHNICAL DATA, IF PROVIDED, WILL CONFORM TO THE SOFTWARE. IN NO EVENT SHALL THE UNITED STATES GOVERNMENT, OR ITS CONTRACTORS OR SUBCONTRACTORS, BE LIABLE FOR ANY DAMAGES, INCLUDING, BUT NOT LIMITED TO, DIRECT, INDIRECT, SPECIAL OR CONSEQUENTIAL DAMAGES, ARISING OUT OF, RESULTING FROM, OR IN ANY WAY CONNECTED WITH THIS SOFTWARE AND/OR TECHNICAL DATA, WHETHER OR NOT BASED UPON WARRANTY, CONTRACT, TORT, OR OTHERWISE, WHETHER OR NOT INJURY WAS SUSTAINED BY PERSONS OR PROPERTY OR OTHERWISE, AND WHETHER OR NOT LOSS WAS SUSTAINED FROM, OR AROSE OUT OF THE RESULTS OF, OR USE OF, THE SOFTWARE AND/OR TECHNICAL DATA.
THE UNITED STATES GOVERNMENT DISCLAIMS ALL WARRANTIES AND LIABILITIES REGARDING THIRD PARTY COMPUTER SOFTWARE, DATA, OR DOCUMENTATION, IF SAID THIRD PARTY COMPUTER SOFTWARE, DATA, OR DOCUMENTATION IS PRESENT IN THE NASA SOFTWARE AND/OR TECHNICAL DATA, AND DISTRIBUTES IT "AS IS."
RECIPIENT AGREES TO WAIVE ANY AND ALL CLAIMS AGAINST THE UNITED STATES GOVERNMENT AND ITS CONTRACTORS AND SUBCONTRACTORS, AND SHALL INDEMNIFY AND HOLD HARMLESS THE UNITED STATES GOVERNMENT AND ITS CONTRACTORS AND SUBCONTRACTORS FOR ANY LIABILITIES, DEMANDS, DAMAGES, EXPENSES OR LOSSES THAT MAY ARISE FROM RECIPIENT'S USE OF THE SOFTWARE AND/OR TECHNICAL DATA, INCLUDING ANY DAMAGES FROM PRODUCTS BASED ON, OR RESULTING FROM, THE USE THEREOF.
IF RECIPIENT FURTHER RELEASES OR DISTRIBUTES THE NASA SOFTWARE AND/OR TECHNICAL DATA, RECIPIENT AGREES TO OBTAIN THIS IDENTICAL WAIVER OF CLAIMS, INDEMNIFICATION AND HOLD HARMLESS, AGREEMENT WITH ANY ENTITIES THAT ARE PROVIDED WITH THE SOFTWARE AND/OR TECHNICAL DATA.
"""

""" PuMApy
Root directory for the pumapy package.
"""

# utilities
from pumapy.utilities.workspace import Workspace
from pumapy.utilities.logger import Logger, print_warning
from pumapy.utilities.timer import Timer
from pumapy.utilities.isosurface import generate_isosurface
from pumapy.utilities.detect_env import detect_env
from pumapy.utilities.property_maps import IsotropicConductivityMap, AnisotropicConductivityMap, ElasticityMap
from pumapy.utilities.boundary_conditions import ConductivityBC, ElasticityBC

# input/output
from pumapy.io.input import import_3Dtiff, import_bin
from pumapy.io.output import export_vti, export_3Dtiff, export_bin, export_sparta_implicit_surfaces, export_stl
try:
    from pumapy.io.output import export_weave_vtu
except ImportError:
    pass

# material properties
from pumapy.materialproperties.surfacearea import compute_surface_area
from pumapy.materialproperties.volumefraction import compute_volume_fraction
from pumapy.materialproperties.mean_intercept_length import compute_mean_intercept_length
from pumapy.materialproperties.orientation import compute_orientation_st, compute_angular_differences
from pumapy.materialproperties.conductivity import compute_thermal_conductivity, compute_electrical_conductivity
from pumapy.materialproperties.tortuosity import compute_continuum_tortuosity
from pumapy.materialproperties.elasticity import compute_elasticity, compute_stress_analysis
from pumapy.materialproperties.radiation import compute_radiation, compute_extinction_coefficients
try:
    from pumapy.materialproperties.permeability import compute_permeability
except ImportError:
    pass

# filtering
from pumapy.filters.filters import (filter_median, filter_gaussian, filter_edt, filter_mean,
                                    filter_erode, filter_dilate, filter_opening, filter_closing)

# generation
from pumapy.generation.tpms import generate_tpms
from pumapy.generation.sphere import get_sphere
from pumapy.generation.random_spheres import generate_random_spheres
from pumapy.generation.generate_sphere import generate_sphere
from pumapy.generation.generate_2d_square_array import generate_2d_square_array
from pumapy.generation.random_fibers import generate_random_fibers
try:
    from pumapy.generation.weave_3mdcp.weave_3mdcp import generate_3mdcp
except ImportError:  # import it only if installed
    pass

# visualization
try:
    from pumapy.visualization.render import render_volume, render_contour, render_orientation, render_warp
    from pumapy.visualization.render_multiphase import render_contour_multiphase
    from pumapy.io.input import import_vti
except ImportError:
    pass
from pumapy.visualization.slicer import plot_slices, compare_slices

# segmentation
from pumapy.segmentation.label_tows import label_tows_fm
from pumapy.segmentation.porespace import identify_porespace, fill_closed_pores

# add wrapped puma cpp functions
# try:
#     import pumapy.utilities.libPuMA as cpp
# except ImportError:
#     print("libPuMA not found, cannot use pumapy.cpp functions.")
