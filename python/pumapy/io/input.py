from skimage.io import imread
import numpy as np
import pickle
from pumapy import Workspace
from os import path
from glob import glob
import sys


def import_3Dtiff(filename, voxel_length=1e-6, import_ws=True):
    """ Function to io 3D tiff

    :param filename: filepath and name
    :type filename: string
    :param voxel_length: size of a voxel side
    :type voxel_length: float, optional
    :param import_ws: if True returns a puma.Workspace, otherwise a ndarray
    :type import_ws: bool, optional
    :return: domain
    :rtype: Workspace or ndarray
    """
    print("Importing " + filename + " ... ", end='')

    if not path.exists(filename):
        raise Exception("File " + filename + " not found.")

    nparray = imread(filename).astype(np.uint16)

    if nparray.ndim == 2:
        nparray = nparray[:, :, np.newaxis]
    else:
        nparray = nparray.transpose(2, 1, 0)
    print("Done")

    if import_ws:
        ws = Workspace.from_array(nparray)
        ws.set_voxel_length(voxel_length)
        return ws
    return nparray


def import_bin(filename):
    """ Import a puma.Workspace to binary (.pumapy extension)

    :param filename: filepath and name
    :type filename: string
    :return: True if successful, False otherwise.
    :rtype: bool
    """
    print("Importing " + filename + " ... ", end='')

    if not path.exists(filename):
        raise Exception("File " + filename + " not found.")

    pumapy_file = open(filename, 'rb')
    ws = pickle.load(pumapy_file)
    pumapy_file.close()
    print("Done")
    return ws


try:
    import vtk
    from paraview import numpy_support

    def import_vti(filename, voxel_length=None, import_ws=True):
        """ Function to import either legacy VTK file (.vtk) or vtkImageData (.vti)

        :param filename: filepath and name
        :type filename: string
        :param voxel_length: voxel_length. If None, voxel_length from the vtk file is used
        :type voxel_length: float, optional
        :param import_ws: True returns a puma.Workspace, otherwise a list of ndarrays
        :type import_ws: bool, optional
        :return: if import_ws is True, then it returns a Workspace.
            if import_ws is False, it returns a dictionary of ndarrays as {"name1": data1, "name2": data2 ...}
        :rtype: Workspace or dict(string: ndarray)
        """
        print("Importing " + filename + " ... ", end='')

        if not path.exists(filename):
            raise Exception("File " + filename + " not found.")

        if filename[-4:] == ".vti":
            reader = vtk.vtkXMLImageDataReader()
            reader.SetFileName(filename)
            reader.Update()
            vtkobject = reader.GetOutput()

        elif filename[-4:] == ".vtk":
            reader = vtk.vtkDataSetReader()
            reader.SetFileName(filename)
            reader.ReadAllScalarsOn()
            reader.ReadAllColorScalarsOn()
            reader.ReadAllNormalsOn()
            reader.ReadAllTCoordsOn()
            reader.ReadAllVectorsOn()
            reader.Update()  # reading
            vtkobject = reader.GetOutputDataObject(0)

        else:
            raise Exception("File of an unrecognized extension, only .vti and .vtk supported.")

        shape = vtkobject.GetDimensions()
        orientation = None

        if vtkobject.GetPointData().GetNumberOfArrays() == 0 and vtkobject.GetCellData().GetNumberOfArrays() == 0:
            raise Exception("No CELL_DATA or POINT_DATA arrays detected in file.")

        if import_ws:

            if vtkobject.GetCellData().GetNumberOfArrays() + vtkobject.GetPointData().GetNumberOfArrays() > 2:
                raise Exception("More than two arrays in file detected: set the import_ws to False to import it.")

            # checking for CELL_DATA
            if vtkobject.GetCellData().GetNumberOfArrays() > 0:
                if vtkobject.GetCellData().GetNumberOfArrays() == 1:  # if one array, could either be orientation or matrix
                    nparray = numpy_support.vtk_to_numpy(vtkobject.GetCellData().GetArray(0))
                    if nparray.ndim == 2:  # if orientation
                        orientation = nparray.copy()
                        nparray = None
                else:
                    nparray = numpy_support.vtk_to_numpy(vtkobject.GetCellData().GetArray(0))
                    orientation = numpy_support.vtk_to_numpy(vtkobject.GetCellData().GetArray(1))

            # checking for POINT_DATA
            else:
                if vtkobject.GetPointData().GetNumberOfArrays() == 1:  # if one array, could either be orientation or matrix
                    nparray = numpy_support.vtk_to_numpy(vtkobject.GetPointData().GetArray(0))
                    if nparray.ndim == 2:  # if orientation
                        orientation = nparray.copy()
                        nparray = None
                else:
                    nparray = numpy_support.vtk_to_numpy(vtkobject.GetPointData().GetArray(0))
                    orientation = numpy_support.vtk_to_numpy(vtkobject.GetPointData().GetArray(1))

            if nparray is not None:
                nparray = nparray.reshape(shape[0] - 1, shape[1] - 1, shape[2] - 1, order="F")
            if orientation is not None:
                orientation = orientation.reshape(shape[0] - 1, shape[1] - 1, shape[2] - 1, 3, order="F")
            print("Done")

            if nparray is None:
                ws = Workspace.from_shape((shape[0] - 1, shape[1] - 1, shape[2] - 1))
            else:
                ws = Workspace.from_array(nparray)
            if orientation is not None:
                ws.set_orientation(orientation)
            if voxel_length is None:
                ws.set_voxel_length(vtkobject.GetSpacing()[0])
            else:
                ws.set_voxel_length(voxel_length)
            return ws

        else:
            nparray_list = dict()
            for i in range(vtkobject.GetCellData().GetNumberOfArrays()):
                tmp = numpy_support.vtk_to_numpy(vtkobject.GetCellData().GetArray(i))
                if tmp.ndim == 1:
                    tmp = tmp.reshape(shape[0] - 1, shape[1] - 1, shape[2] - 1, order="F")
                else:
                    tmp = tmp.reshape(shape[0] - 1, shape[1] - 1, shape[2] - 1, 3, order="F")
                nparray_list[vtkobject.GetCellData().GetArrayName(i)] = tmp
            for i in range(vtkobject.GetPointData().GetNumberOfArrays()):
                tmp = numpy_support.vtk_to_numpy(vtkobject.GetPointData().GetArray(i))
                if tmp.ndim == 1:
                    tmp = tmp.reshape(shape[0] - 1, shape[1] - 1, shape[2] - 1, order="F")
                else:
                    tmp = tmp.reshape(shape[0] - 1, shape[1] - 1, shape[2] - 1, 3, order="F")
                nparray_list[vtkobject.GetPointData().GetArrayName(i)] = tmp
            print("Done")
            return nparray_list


    def import_weave_vtu(filename):
        """ Import TexGen vtu weave in a Workspace

        :param filename: file path and name
        :type filename: string
        :return: voxelized weave from TexGen
        :rtype: Workspace
        """

        if not path.exists(filename):
            filename = glob(filename + '*.vtu')
            if len(filename) == 0:
                raise Exception("File " + filename + " not found.")
            else:
                filename = filename[0]
        print("Importing " + filename + " ... ", end='')

        reader = vtk.vtkXMLUnstructuredGridReader()
        reader.SetFileName(filename)
        reader.Update()  # reading
        vtkobject = reader.GetOutputDataObject(0)

        dims = path.split(filename[:-4])[1].split('_')[-3:]

        # ORIGINAL TEXGEN
        # Number Of Arrays: 6
        # Array 0 name = YarnIndex  <-- transfering to ws
        # Array 1 name = YarnTangent
        # Array 2 name = Location
        # Array 3 name = VolumeFraction
        # Array 4 name = SurfaceDistance
        # Array 5 name = Orientation  <-- transfering to ws
        # yarn_index = numpy_support.vtk_to_numpy(vtkobject.GetCellData().GetArray(0)) + 1
        # orientation = numpy_support.vtk_to_numpy(vtkobject.GetCellData().GetArray(5))
        # yarn_index = yarn_index.reshape(int(dims[0]), int(dims[1]), int(dims[2]), order="F")
        # orientation = orientation.reshape(int(dims[0]), int(dims[1]), int(dims[2]), 3, order="F")

        # MODIFIED TEXGEN
        # Number Of Arrays: 6
        # Array 0 name = YarnIndex  <-- transfering to ws
        # Array 1 name = Orientation  <-- depends on has_orientation
        yarn_index = numpy_support.vtk_to_numpy(vtkobject.GetCellData().GetArray(0)) + 1
        yarn_index = yarn_index.reshape(int(dims[0]), int(dims[1]), int(dims[2]), order="F")
        ws = Workspace.from_array(yarn_index)

        if vtkobject.GetCellData().GetNumberOfArrays() == 2:
            orientation = numpy_support.vtk_to_numpy(vtkobject.GetCellData().GetArray(1))
            orientation = orientation.reshape(int(dims[0]), int(dims[1]), int(dims[2]), 3, order="F")
            ws.set_orientation(orientation)

        print("Done")
        return ws
except ImportError:
    pass
