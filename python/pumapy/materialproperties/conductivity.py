from pumapy.physicsmodels.isotropic_conductivity import IsotropicConductivity
from pumapy.physicsmodels.mpfa_conductivity import AnisotropicConductivity
from pumapy.utilities.property_maps import IsotropicConductivityMap, AnisotropicConductivityMap


def compute_thermal_conductivity(workspace, cond_map, direction, side_bc='s', prescribed_bc=None, tolerance=1e-4,
                                 maxiter=10000, solver_type='bicgstab', display_iter=True, print_matrices=(0, 0, 0, 0, 0)):
    """ Compute the thermal conductivity

    :param workspace: domain
    :type workspace: Workspace
    :param cond_map: local constituents themal conductivities
    :type cond_map: IsotropicConductivityMap or AnisotropicConductivityMap
    :param direction: direction for solve ('x','y', or 'z')
    :type direction: string
    :param side_bc: side boundary conditions can be symmetric ('s'), periodic ('p') or dirichlet ('d')
    :type side_bc: string, optional
    :param prescribed_bc: 3D array holding dirichlet BC.
    :type prescribed_bc: ConductivityBC, optional
    :param tolerance: tolerance for iterative solver
    :type tolerance: float, optional
    :param maxiter: maximum Iterations for solver
    :type maxiter: int, optional
    :param solver_type: solver type, options: 'bicgstab', 'cg', 'gmres', 'direct'
    :type solver_type: string, optional
    :param display_iter: display iterations and residual
    :type display_iter: bool, optional
    :param print_matrices: corresponding to b, E, A, T, q decimal places. If 0, they are not printed
    :type print_matrices: tuple(5 bools), optional
    :return: thermal conductivity, temperature field, flux
    :rtype: tuple(tuple(float, float, float), ndarray, ndarray)
    """
    if isinstance(cond_map, IsotropicConductivityMap):
        solver = IsotropicConductivity(workspace, cond_map, direction, side_bc, prescribed_bc, tolerance, maxiter,
                                       solver_type, display_iter)
    elif isinstance(cond_map, AnisotropicConductivityMap):
        solver = AnisotropicConductivity(workspace, cond_map, direction, side_bc, prescribed_bc, tolerance, maxiter,
                                         solver_type, display_iter, print_matrices)
    else:
        raise Exception("cond_map has to be an IsotropicConductivityMap or AnisotropicConductivityMap")

    solver.error_check()

    solver.log_input()
    solver.compute()
    solver.log_output()
    return solver.keff, solver.T, solver.q


def compute_electrical_conductivity(workspace, cond_map, direction, side_bc='p', prescribed_bc=None, tolerance=1e-4,
                                    maxiter=10000, solver_type='bicgstab', display_iter=True, print_matrices=(0, 0, 0, 0, 0)):
    """ Compute the electrical conductivity

    :param workspace: domain
    :type workspace: Workspace
    :param cond_map: local constituents electrical conductivities
    :type cond_map: IsotropicConductivityMap or AnisotropicConductivityMap
    :param direction: direction for solve ('x','y', or 'z')
    :type direction: string
    :param side_bc: side boundary conditions can be symmetric ('s'), periodic ('p') or dirichlet ('d')
    :type side_bc: string, optional
    :param prescribed_bc: 3D array holding dirichlet BC
    :type prescribed_bc: ConductivityBC, optional
    :param tolerance: tolerance for iterative solver
    :type tolerance: float, optional
    :param maxiter: maximum Iterations for solver
    :type maxiter: int, optional
    :param solver_type: solver type, options: 'bicgstab', 'cg', 'gmres', 'direct'
    :type solver_type: string, optional
    :param display_iter: display iterations and residual
    :type display_iter: bool, optional
    :param print_matrices: corresponding to E, A, b, T, q decimal places. If 0, they are not printed
    :type print_matrices: tuple(5 bools), optional
    :return: electrical conductivity, potential field, flux
    :rtype: tuple(tuple(float, float, float), ndarray, ndarray)
    """
    return compute_thermal_conductivity(workspace, cond_map, direction, side_bc, prescribed_bc, tolerance, maxiter,
                                        solver_type, display_iter, print_matrices)
