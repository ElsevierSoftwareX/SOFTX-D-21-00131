import numpy as np
from skimage import measure
from pumapy.utilities.generic_checks import check_ws_cutoff


def identify_porespace(workspace, solid_cutoff):
    """ Identify the porespace

        :param workspace: domain
        :type workspace: Workspace
        :param solid_cutoff: specify the solid range to discard from pores identification
        :type solid_cutoff: tuple(int, int)
        :return: porespace marked as: 0 solid, 1 largest pore (likely open porosity), > 1 other pores
        :rtype: ndarray
    """

    # error check
    check_ws_cutoff(workspace, solid_cutoff)
    ws = workspace.copy()

    ws.binarize_range(solid_cutoff)

    pore_labels = measure.label(ws.matrix, background=1)

    unique_pore_ids, unique_id_counts = np.unique(pore_labels[pore_labels != 0], return_counts=True)

    sorted_unique_pore_ids = unique_pore_ids[np.argsort(unique_id_counts)[::-1]]

    keyarray = np.arange(np.max(pore_labels) + 1)
    keyarray[sorted_unique_pore_ids] = unique_pore_ids

    return keyarray[pore_labels]


def fill_closed_pores(workspace, solid_cutoff, fill_value, return_pores=False):
    """ Identify the porespace and fill closed porosity

        :param workspace: domain
        :type workspace: Workspace
        :param solid_cutoff: specify the solid range to discard from pores identification
        :type solid_cutoff: tuple(int, int)
        :param fill_value: value to fill open porosity with
        :type fill_value: int
        :param return_pores: specifies whether to return identified pores
        :type return_pores: bool, optional
        :return: new workspace with filled open porosity
            (if return_pores==True, then it also returns the porespace marked as:
            0 solid, 1 largest pore (likely open porosity), > 1 other pores)
        :rtype: Workspace
    """

    pores = identify_porespace(workspace, solid_cutoff)

    if isinstance(pores, bool):
        return False

    ws = workspace.copy()
    ws.binarize_range(solid_cutoff)

    ws[np.where(pores > 1)] = np.uint16(fill_value)

    if return_pores:
        return ws, pores
    else:
        return ws
