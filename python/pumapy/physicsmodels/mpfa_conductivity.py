from pumapy.physicsmodels.anisotropic_conductivity_utils import (pad_domain, add_nondiag, divP, find_unstable_vox,
                                                                 fill_flux_matrices, flatten_Kmat)
from pumapy.physicsmodels.mpxa_matrices import fill_Ampfa, fill_Bmpfa, fill_Cmpfa, fill_Dmpfa, create_mpfa_indices
from pumapy.physicsmodels.conductivity_parent import Conductivity, SolverDisplay
from pumapy.utilities.logger import print_warning
import numpy as np
from scipy.sparse import csr_matrix, diags
from scipy.sparse.linalg import bicgstab, spsolve, cg, gmres
import sys


class AnisotropicConductivity(Conductivity):
    def __init__(self, workspace, cond_map, direction, side_bc, prescribed_bc, tolerance, maxiter, solver_type,
                 display_iter, print_matrices):
        super().__init__(workspace, cond_map, direction, side_bc, prescribed_bc, tolerance, maxiter, solver_type, display_iter)
        self.print_matrices = print_matrices
        self.mat_cond = dict()
        self.need_to_orient = False  # changes if conductivities (k_axial, k_radial) detected
        self.orient_pad = None

    def compute(self):
        self.__initialize()
        self.__assemble_bvector()
        self.__assemble_Amatrix()
        if not self.__solve():
            return
        self.__compute_effective_coefficient()

    def __initialize(self):
        print("Initializing and padding domains ... ", flush=True, end='')

        # Rotating domain to avoid cases and padding
        shape = [self.len_x + 2, self.len_y + 2, self.len_z + 2]
        reorder = [0, 1, 2]
        reorder_nondiagcond = [3, 4, 5]
        if self.direction == 'y':
            shape = [self.len_y + 2, self.len_x + 2, self.len_z + 2]
            reorder = [1, 0, 2]
            reorder_nondiagcond = [3, 5, 4]
        elif self.direction == 'z':
            shape = [self.len_z + 2, self.len_y + 2, self.len_x + 2]
            reorder = [2, 1, 0]
            reorder_nondiagcond = [5, 4, 3]

        self.ws_pad = np.zeros(shape, dtype=np.uint16)
        self.ws_pad[1:-1, 1:-1, 1:-1] = self.ws.matrix.transpose(reorder)

        if self.need_to_orient:
            self.orient_pad = np.zeros(shape + [3], dtype=float)
            self.orient_pad[1:-1, 1:-1, 1:-1, :] = self.ws.orientation.transpose(reorder + [3])[:, :, :, reorder]

        for key in self.mat_cond.keys():
            tmp_cond = list(self.mat_cond[key])
            if len(tmp_cond) == 6:
                self.mat_cond[key] = tuple([x for _, x in sorted(zip(reorder + reorder_nondiagcond, tmp_cond))])

        self.len_x, self.len_y, self.len_z = shape
        self.len_xy = self.len_x * self.len_y
        self.len_xyz = self.len_x * self.len_y * self.len_z

        # Padding domain, imposing symmetric or periodic BC on faces
        pad_domain(self.ws_pad, self.orient_pad, self.need_to_orient, self.len_x, self.len_y, self.len_z, self.side_bc)

        # Segmenting padded domain
        for i in range(self.cond_map.get_size()):
            low, high, _ = self.cond_map.get_material(i)
            self.ws_pad[np.logical_and(self.ws_pad >= low, self.ws_pad <= high)] = i

        # Placing True on dirichlet boundaries to skip them
        self.dir_vox = np.zeros(shape, dtype=bool)
        self.dir_vox[[1, -2], 1:-1, 1:-1] = True
        if self.prescribed_bc is not None:
            self.dir_vox[1:-1, 1:-1, 1:-1][self.prescribed_bc.dirichlet != np.Inf] = True
        print("Done")

    def __assemble_bvector(self):
        print("Assembling b vector ... ", flush=True, end='')

        I, V = ([] for _ in range(2))

        if self.prescribed_bc is not None:
            for i in range(1, self.len_x - 1):
                for j in range(1, self.len_y - 1):
                    for k in range(1, self.len_z - 1):
                        if self.prescribed_bc[i - 1, j - 1, k - 1] != np.Inf:
                            I.append(self.len_x * (self.len_y * k + j) + i)
                            V.append(self.prescribed_bc[i - 1, j - 1, k - 1])
        else:
            # Setting unit temperature
            i = self.len_x - 2
            for j in range(1, self.len_y - 1):
                for k in range(1, self.len_z - 1):
                    I.append(self.len_x * (self.len_y * k + j) + i)
                    V.append(1.)

        # Setting linear temperature on the boundaries if Dirichlet
        if self.side_bc == 'd':
            x = np.linspace(0, 1, self.len_x - 2)
            for j in [1, self.len_y - 2]:
                for i in range(1, self.len_x - 1):
                    for k in range(1, self.len_z - 1):
                        I.append(self.len_x * (self.len_y * k + j) + i)
                        V.append(x[i - 1])
            for k in [1, self.len_z - 2]:
                for i in range(2, self.len_x - 2):
                    for j in range(2, self.len_y - 2):
                        I.append(self.len_x * (self.len_y * k + j) + i)
                        V.append(x[i - 1])

        self.bvec = csr_matrix((V, (I, np.zeros(len(I)))), shape=(self.len_xyz, 1))

        if self.print_matrices[0]:
            self._print_b(self.print_matrices[0])
        print("Done")

    def __compute_Kmat(self, i, i_cv):
        # Reset layer of Cmat
        self.Kmat[i].fill(0)

        for key, value in self.mat_cond.items():
            mask = self.ws_pad[i_cv] == key
            if len(value) == 6:
                self.Kmat[i, mask] = value
            else:
                phi = np.arctan2(self.orient_pad[i_cv, mask, 1], self.orient_pad[i_cv, mask, 0])
                theta = np.arcsin(self.orient_pad[i_cv, mask, 2])

                size = np.sum(mask)
                Rz_kinit = np.zeros((size, 3, 3), dtype=float)
                Ry_krot = np.zeros((size, 3, 3), dtype=float)

                Rz_kinit[:, 0, 0] = np.cos(phi)
                Rz_kinit[:, 1, 1] = Rz_kinit[:, 0, 0]
                Rz_kinit[:, 1, 0] = np.sin(phi)
                Rz_kinit[:, 0, 1] = -Rz_kinit[:, 1, 0]
                Rz_kinit[:, 2, 2] = 1
                Ry_krot[:, 1, 1] = 1
                Ry_krot[:, 0, 0] = np.cos(theta)
                Ry_krot[:, 2, 2] = Ry_krot[:, 0, 0]
                Ry_krot[:, 0, 2] = np.sin(theta)
                Ry_krot[:, 2, 0] = -Ry_krot[:, 0, 2]

                R = Rz_kinit @ Ry_krot

                Rz_kinit.fill(0)
                Rz_kinit[:, [0, 1, 2], [0, 1, 2]] = [value[0], value[1], value[1]]

                Ry_krot = R @ Rz_kinit @ np.linalg.inv(R)
                self.Kmat[i, mask] = Ry_krot[:, [0, 1, 2, 0, 0, 1], [0, 1, 2, 1, 2, 2]]

    def __compute_transmissibility(self, i, i_cv):
        # Reset layers
        self.Emat[i].fill(0)
        self.unstable[i].fill(0)
        self.kf.fill(0)
        flatten_Kmat(i, self.len_y, self.len_z, self.Kmat[i:i + 2], self.kf)

        # C becomes singular sometimes when there are air voxels
        self.mpfa12x12.fill(0)
        self.mpfa12x12[:, :, self.Cind[0], self.Cind[1]] = fill_Cmpfa(self.kf)
        det = np.linalg.det(self.mpfa12x12)
        if np.min(det) == 0:
            self.unstable[i, det == 0] = True

        # Computing transmissibility matrix as: A @ (Cinv @ D) + B
        if not np.all(self.unstable[i]):
            self.Emat[i, :, :, self.Dind[0], self.Dind[1]] = fill_Dmpfa(self.kf)
            self.Emat[i, self.unstable[i]] = 0

            self.mpfa12x12[~self.unstable[i]] = np.linalg.inv(self.mpfa12x12[~self.unstable[i]])  # Cinv

            self.Emat[i, ~self.unstable[i]] = (self.mpfa12x12[~self.unstable[i]] @
                                               self.Emat[i, ~self.unstable[i]])  # (Cinv @ D)

            self.mpfa12x12.fill(0)
            self.mpfa12x12[:, :, self.Aind[0], self.Aind[1]] = fill_Ampfa(self.kf)
            self.Emat[i, ~self.unstable[i]] = (self.mpfa12x12[~self.unstable[i]] @
                                               self.Emat[i, ~self.unstable[i]])  # A @ (Cinv @ D)

            self.Emat[i, ~self.unstable[i]] += fill_Bmpfa(self.kf, self.zeros)[~self.unstable[i]]  # + B

        if self.print_matrices[1]:
            self._print_E(i, i_cv, self.print_matrices[1])

    def __initialize_MPFA(self):
        # Initialize matrix slice of conductivities
        self.Kmat = np.zeros((3, self.len_y, self.len_z, 6), dtype=float)  # per CV
        self.__compute_Kmat(0, 0)  # Computing first layer of Kmat
        self.__compute_Kmat(1, 1)  # Computing second layer of Kmat

        # Initialize MPFA variables
        self.kf = np.zeros((48, self.len_y - 1, self.len_z - 1), dtype=float)  # per IV
        self.Emat = np.zeros((2, self.len_y - 1, self.len_z - 1, 12, 8), dtype=float)
        self.unstable = np.zeros((2, self.len_y - 1, self.len_z - 1), dtype=bool)
        self.mpfa12x12 = np.zeros((self.len_y - 1, self.len_z - 1, 12, 12), dtype=float)  # A, C
        self.zeros = np.zeros(self.kf[0].shape)
        self.Aind, self.Cind, self.Dind = create_mpfa_indices()
        self.__compute_transmissibility(0, 0)  # Computing first layer of E

    def __creating_indices(self, i):
        # Finding all indices for slice
        i_indices = np.ones_like(self.ws_pad[i], dtype=np.uint32)
        i_indices[[0, -1], :] = 0
        i_indices[:, [0, -1]] = 0
        i_indices = np.where(i_indices > 0)
        i_indices = self.len_x * (self.len_y * i_indices[1] + i_indices[0]) + np.full(i_indices[0].size, i)

        # Removing dirichlet voxels
        i_dirvox = np.where(self.dir_vox[i])
        i_dirvox = self.len_x * (self.len_y * i_dirvox[1] + i_dirvox[0]) + np.full(i_dirvox[0].size, i)
        i_indices = i_indices[~np.in1d(i_indices, i_dirvox)]

        # Duplicating the voxel indices where divergence happens
        i_indices = np.repeat(i_indices, 27)
        return i_indices, i_dirvox  # returning dirichlet voxel indices

    def __assemble_Amatrix(self):
        print("Initializing large data structures ... ", flush=True, end='')
        I, J = np.zeros((2, 27 * self.len_xyz), dtype=np.uint32)
        V = np.zeros(27 * self.len_xyz, dtype=float)
        counter = 0
        I_dirvox = []
        self.__initialize_MPFA()
        j_indices = np.zeros((27 * (self.len_y - 2) * (self.len_z - 2)), dtype=np.uint32)
        values = np.zeros((27 * (self.len_y - 2) * (self.len_z - 2)), dtype=float)
        self.dir_vox = self.dir_vox.astype(np.uint8)
        print("Done")

        # Iterating through interior
        for i in range(1, self.len_x - 1):
            self.__compute_Kmat(2, i + 1)  # Computing third layer of Kmat
            self.__compute_transmissibility(1, i)  # Computing second layer of E

            # If all surrounding IV are unstable (i.e. partly or all gaseous), then put middle CV as Dirichlet
            find_unstable_vox(i, self.len_y, self.len_z, self.dir_vox, self.unstable)

            # Creating j indices and divergence values for slice
            j_indices.fill(0)
            values.fill(np.NaN)
            divP(i, self.len_x, self.len_y, self.len_z, self.dir_vox, j_indices, values, self.Emat)

            # Creating i indices for slice
            i_indices, i_dirvox = self.__creating_indices(i)
            if i_indices.size > 0:
                I[counter:counter + i_indices.size] = i_indices
            I_dirvox.extend(i_dirvox)

            if j_indices[j_indices != 0].size > 0:
                J[counter:counter + i_indices.size] = j_indices[~np.isnan(values)]
                V[counter:counter + i_indices.size] = values[~np.isnan(values)]
                counter += i_indices.size

            # Passing second layer to first
            self.Emat[0] = self.Emat[1]
            self.Kmat[:2] = self.Kmat[1:]
            sys.stdout.write("\rAssembling A matrix ... {:.1f}% ".format(i / (self.len_x - 2) * 100))

        # Clear unnecessary variables before creating A
        del self.Emat, self.kf, self.Kmat, self.unstable
        del self.dir_vox, i_indices, j_indices, values, i_dirvox, i

        # Adding all dirichlet voxels
        I[counter:counter + len(I_dirvox)] = I_dirvox
        J[counter:counter + len(I_dirvox)] = I_dirvox
        V[counter:counter + len(I_dirvox)] = 1
        counter += len(I_dirvox)
        del I_dirvox

        # Add diagonal 1s for exterior voxels
        diag_1s = np.ones_like(self.ws_pad, dtype=int)
        diag_1s[1:-1, 1:-1, 1:-1] = 0
        ind = np.array(np.where(diag_1s > 0))
        diag_1s = self.len_x * (self.len_y * ind[2] + ind[1]) + ind[0]
        diag_1s = diag_1s.astype(np.uint32)
        del ind
        I[counter:counter + diag_1s.size] = diag_1s
        J[counter:counter + diag_1s.size] = diag_1s
        V[counter:counter + diag_1s.size] = 1
        counter += diag_1s.size

        # Add non-diagonal 1s for exterior voxels
        if self.side_bc is not "d":
            I[counter:counter + diag_1s.size] = diag_1s
            add_nondiag(diag_1s, self.len_x, self.len_y, self.len_z, self.side_bc)
            J[counter:counter + diag_1s.size] = diag_1s
            V[counter:counter + diag_1s.size] = -1
            counter += diag_1s.size
        del diag_1s, counter

        # Assemble sparse A matrix
        self.Amat = csr_matrix((V, (I, J)), shape=(self.len_xyz, self.len_xyz))

        # Simple preconditioner
        diag = self.Amat.diagonal()
        if np.any(diag == 0):
            self.M = None  # identity matrix if singularity has happened in MPFA
        else:
            self.M = diags(1. / self.Amat.diagonal(), 0).tocsr()

        if self.print_matrices[2]:
            self._print_A(self.print_matrices[2])
        print("Done")

    def __solve(self):
        print("Solving Ax=b system ... ", end='')

        info = 0
        if self.solver_type == 'direct':
            print("Direct solver", end='')
            try:
                import scikits.umfpack
                x = spsolve(self.Amat, self.bvec, use_umfpack=True)
            except ImportError:
                x = spsolve(self.Amat, self.bvec)


        else:  # iterative solvers
            Tinitial_guess = np.zeros((self.len_x, self.len_y, self.len_z), dtype=float)
            for i in range(self.len_x - 1):
                Tinitial_guess[i] = i / (self.len_x - 2.)
            Tinitial_guess = Tinitial_guess.flatten('F')

            if self.solver_type == 'gmres':
                print("gmres:")
                if self.display_iter:
                    x, info = gmres(self.Amat, self.bvec.todense(), x0=Tinitial_guess, atol=self.tolerance,
                                    maxiter=self.maxiter, callback=SolverDisplay(), M=self.M)
                else:
                    x, info = gmres(self.Amat, self.bvec.todense(), x0=Tinitial_guess, atol=self.tolerance,
                                    maxiter=self.maxiter, M=self.M)

            elif self.solver_type == 'cg':
                print("Conjugate Gradient:")
                if self.display_iter:
                    x, info = cg(self.Amat, self.bvec.todense(), x0=Tinitial_guess, atol=self.tolerance,
                                 maxiter=self.maxiter, callback=SolverDisplay(), M=self.M)
                else:
                    x, info = cg(self.Amat, self.bvec.todense(), x0=Tinitial_guess, atol=self.tolerance,
                                 maxiter=self.maxiter, M=self.M)

            else:
                if self.solver_type != 'bicgstab':
                    print_warning("Unrecognized solver, defaulting to bicgstab.")
                print("Bicgstab:")
                if self.display_iter:
                    x, info = bicgstab(self.Amat, self.bvec.todense(), x0=Tinitial_guess, atol=self.tolerance,
                                       maxiter=self.maxiter, M=self.M, callback=SolverDisplay())
                else:
                    x, info = bicgstab(self.Amat, self.bvec.todense(), x0=Tinitial_guess, atol=self.tolerance,
                                       maxiter=self.maxiter, M=self.M)

        if info != 0:
            raise Exception("Solver error: " + str(info))

        del self.Amat, self.bvec
        self.T = x.reshape([self.len_x, self.len_y, self.len_z], order='F')

        # Mirroring boundaries for flux computation
        self.T[0] = self.T[1]
        self.T[-1] = self.T[-2]
        if self.side_bc == "d":
            self.T[:, 0] = self.T[:, 1]
            self.T[:, -1] = self.T[:, -2]
            self.T[:, :, 0] = self.T[:, :, 1]
            self.T[:, :, -1] = self.T[:, :, -2]
        return True, print(" ... Done")

    def __compute_effective_coefficient(self):
        self.__compute_fluxes()

        # Accumulating and volume averaging stresses
        fluxes = [np.sum(self.q[:, :, :, i]) / ((self.len_x - 2) * (self.len_y - 2) * (self.len_z - 2))
                  for i in range(3)]
        self.keff = [-fluxes[i] * (self.len_x - 2) * self.ws.voxel_length for i in range(3)]

        # Rotating output back
        if self.direction == 'y':
            self.T = self.T.transpose(1, 0, 2)
            self.q = self.q.transpose(1, 0, 2, 3)[:, :, :, [1, 0, 2]]
            self.keff = [self.keff[1], self.keff[0], self.keff[2]]
        elif self.direction == 'z':
            self.T = self.T.transpose(2, 1, 0)
            self.q = self.q.transpose(2, 1, 0, 3)[:, :, :, [2, 1, 0]]
            self.keff = [self.keff[2], self.keff[1], self.keff[0]]

    def __compute_fluxes(self):
        # Initialize required data structures
        self.q = np.zeros((self.len_x - 2, self.len_y - 2, self.len_z - 2, 3), dtype=float)
        self.__initialize_MPFA()
        T_sw, T_se, T_nw, T_ne, T_tsw, T_tse, T_tnw, T_tne = np.zeros((8, self.len_y - 2, self.len_z - 2, 8))
        E_sw, E_se, E_nw, E_ne, E_tsw, E_tse, E_tnw, E_tne = np.zeros((8, self.len_y - 2, self.len_z - 2, 12, 8))

        # Iterating through interior
        for i in range(1, self.len_x - 1):
            self.__compute_Kmat(2, i + 1)  # Computing third layer of Kmat
            self.__compute_transmissibility(1, i)  # Computing second layer of E

            # filling eight IVs
            fill_flux_matrices(i, self.len_x, self.len_y, self.len_z, self.T[i - 1:i + 2], self.Emat,
                               E_sw, E_se, E_nw, E_ne, E_tsw, E_tse, E_tnw, E_tne,
                               T_sw, T_se, T_nw, T_ne, T_tsw, T_tse, T_tnw, T_tne)

            # Computing fluxes by computing E x T
            q_sw = np.squeeze(E_sw @ T_sw[:, :, :, np.newaxis])
            q_se = np.squeeze(E_se @ T_se[:, :, :, np.newaxis])
            q_nw = np.squeeze(E_nw @ T_nw[:, :, :, np.newaxis])
            q_ne = np.squeeze(E_ne @ T_ne[:, :, :, np.newaxis])
            q_tsw = np.squeeze(E_tsw @ T_tsw[:, :, :, np.newaxis])
            q_tse = np.squeeze(E_tse @ T_tse[:, :, :, np.newaxis])
            q_tnw = np.squeeze(E_tnw @ T_tnw[:, :, :, np.newaxis])
            q_tne = np.squeeze(E_tne @ T_tne[:, :, :, np.newaxis])

            # Summing fluxes CV-wise
            self.q[i - 1, :, :, 0] = (q_se[:, :, 3] + q_ne[:, :, 2] + q_tse[:, :, 1] + q_tne[:, :, 0] +
                                      q_sw[:, :, 3] + q_nw[:, :, 2] + q_tsw[:, :, 1] + q_tnw[:, :, 0]) / 4
            self.q[i - 1, :, :, 1] = (q_nw[:, :, 7] + q_ne[:, :, 6] + q_tnw[:, :, 5] + q_tne[:, :, 4] +
                                      q_sw[:, :, 7] + q_se[:, :, 6] + q_tsw[:, :, 5] + q_tse[:, :, 4]) / 4
            self.q[i - 1, :, :, 2] = (q_tsw[:, :, 11] + q_tse[:, :, 10] + q_tnw[:, :, 9] + q_tne[:, :, 8] +
                                      q_sw[:, :, 11] + q_se[:, :, 10] + q_nw[:, :, 9] + q_ne[:, :, 8]) / 4

            # Passing second layer to first
            self.Emat[0] = self.Emat[1]
            self.Kmat[0:2] = self.Kmat[1:3]
            sys.stdout.write("\rComputing fluxes ... {:.1f}% ".format(i / (self.len_x - 2) * 100))
        del self.Emat, self.kf, self.Kmat, self.unstable

        # Extract only interior temperature, ignoring exterior used as bc
        self.T = self.T[1:-1, 1:-1, 1:-1]
        self.q /= self.ws.voxel_length

        if self.print_matrices[3]:
            print_T(self.T, self.print_matrices[3])
        if self.print_matrices[4]:
            print_flux(self.q, self.print_matrices[4])
        print("Done")

    def error_check(self):
        if Conductivity.error_check(self):
            return False

        # cond_map checks
        ws_tmp_tocheck = self.ws.matrix.copy()
        for i in range(self.cond_map.get_size()):
            low, high, k = self.cond_map.get_material(i)
            self.mat_cond[i] = k

            if len(k) == 2:
                self.need_to_orient = True
                if self.ws.orientation.shape[:3] != self.ws.matrix.shape or \
                        not 0.9 < np.min(np.linalg.norm(self.ws.orientation[np.logical_and(self.ws.matrix >= low,
                                                                                           self.ws.matrix <= high)],
                                                        axis=1)) < 1.1:
                    raise Exception("The Workspace needs an orientation in order to align the conductivities.")

            # segmenting tmp domain to check if all values covered by mat_cond
            ws_tmp_tocheck[np.logical_and(self.ws.matrix >= low, self.ws.matrix <= high)] = i

        unique_matrixvalues = np.unique(ws_tmp_tocheck)
        if (unique_matrixvalues.size != self.cond_map.get_size() or
                np.all(np.array(list(self.mat_cond.keys()), dtype=np.uint16) != unique_matrixvalues)):
            raise Exception("All values in workspace must be included in ConductivityMap.")

        # print_matrices checks
        if type(self.print_matrices) is not tuple or len(self.print_matrices) != 5:
            raise Exception("Print_matrices must be a tuple with 5 booleans.")
        return False

    # Printing functions of system matrices
    def _print_E(self, i, i_cv, dec=4):
        np.set_printoptions(precision=dec)
        for j in range(self.len_y - 1):
            for k in range(self.len_z - 1):
                print()
                print("index {},{},{}".format(i_cv, j, k))
                print(self.Emat[i, j, k])

    def _print_A(self, dec=4):
        np.set_printoptions(linewidth=10000)
        np.set_printoptions(threshold=sys.maxsize)
        np.set_printoptions(formatter={'float': lambda x: "{:.{}f}".format(x, dec).rstrip('0').rstrip('.')})
        print()
        print("A matrix:")
        print(self.Amat.toarray())

    def _print_b(self, dec=1):
        vector = self.bvec.toarray()
        print()
        print("b vector:")
        for k in range(self.len_z):
            for i in range(self.len_x):
                for j in range(self.len_y):
                    print('{:.{}f}'.format(vector[self.len_x * (self.len_y * k + j) + i, 0], dec), end=' ')
                print()
            print()


def print_T(temperature, dec=4):
    print()
    print("Temperature:")
    for k in range(temperature.shape[2]):
        for i in range(temperature.shape[0]):
            for j in range(temperature.shape[1]):
                print('{:.{}f}'.format(temperature[i, j, k], dec), end=' ')
            print()
        print()


def print_flux(flux, dec=4):
    print()
    print("Flux:")
    for k in range(flux.shape[2]):
        for i in range(flux.shape[0]):
            for j in range(flux.shape[1]):
                print('({:.{}f}, {:.{}f}, {:.{}f})'.format(flux[i, j, k, 0], dec,
                                                           flux[i, j, k, 1], dec,
                                                           flux[i, j, k, 2], dec), end=' ')
            print()
        print()
