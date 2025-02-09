from skimage.filters import gaussian
from scipy.ndimage import distance_transform_edt, median_filter
from scipy.ndimage.filters import uniform_filter
from skimage.morphology import erosion, dilation, opening, closing, ball
from pumapy import Workspace
from pumapy.utilities.logger import print_warning
import numpy as np


def filter_median(ws, size):
    """ 3D Median filter

    :param ws: input workspace
    :type ws: Workspace
    :param size: size of window
    :type size: int
    :return: True if successful, False otherwise.
    :rtype: bool
    """
    if not isinstance(ws, Workspace):
        raise Exception("Workspace must be passed.")

    ws.log.log_section("Median Filter:")
    ws.log.log_line("Window Size: " + str(size))
    ws.log.write_log()

    ws.matrix = median_filter(ws.matrix, size)
    return True


def filter_gaussian(ws, sigma=1, apply_on_orientation=False):
    """ 3D Gaussian filter

        :param ws: input workspace
        :type ws: Workspace
        :param sigma: size of kernel
        :type sigma: int
        :param apply_on_orientation: specify whether to apply filter on orientation field
        :type apply_on_orientation: bool, optional
        :return: True if successful, False otherwise.
        :rtype: bool
    """
    if not isinstance(ws, Workspace):
        raise Exception("Workspace must be passed.")

    ws.log.log_section("Gaussian Filter:")
    ws.log.log_line("Sigma: " + str(sigma))
    ws.log.write_log()

    ws.matrix = gaussian(ws.matrix, sigma=sigma, preserve_range=True).astype(np.uint16)

    if apply_on_orientation:
        if ws.orientation.shape[:3] == ws.matrix.shape:
            unprocessed_orientation = ws.orientation.copy()
            ws.orientation = gaussian(ws.orientation, sigma=sigma, multichannel=True, preserve_range=True)
            # recreate unit vectors
            magnitude = np.linalg.norm(ws.orientation, axis=3)
            with np.errstate(divide='ignore', invalid='ignore'):  # temporarily ignore divide by 0 warnings
                ws.orientation = ws.orientation / magnitude[:, :, :, np.newaxis]
            ws.orientation[np.isnan(ws.orientation)] = unprocessed_orientation[np.isnan(ws.orientation)]
        else:
            print_warning("To apply filter on orientation field, it has to have same shape as ws.matrix.")
    return True


def filter_edt(ws, cutoff):
    """ 3D Exact euclidean distance transform.

    :param ws: input workspace
    :type ws: Workspace
    :param cutoff: cutoff to binarize image
    :type cutoff: tuple(int, int)
    :return: True if successful, False otherwise.
    :rtype: bool
    """
    if not isinstance(ws, Workspace):
        raise Exception("Workspace must be passed")

    ws.log.log_section("Euclidean Distance Transform Filter")
    ws.log.write_log()

    ws.matrix = distance_transform_edt(np.logical_and(ws.matrix >= cutoff[0], ws.matrix <= cutoff[1]))
    return True


def filter_mean(ws, size=5):
    """ 3D Mean filter.

    :param ws: input workspace
    :type ws: Workspace
    :param size: size of window
    :type size: int, optional
    :return: True if successful, False otherwise.
    :rtype: bool
    """
    if not isinstance(ws, Workspace):
        raise Exception("Workspace must be passed")

    ws.log.log_section("Mean Filter")
    ws.log.log_line("Window Size: " + str(size))
    ws.log.write_log()

    ws.matrix = uniform_filter(ws.matrix, size)
    return True


def filter_erode(ws, cutoff, size=5):
    """ 3D morphological erosion filter.

    :param ws: input workspace
    :type ws: Workspace
    :param cutoff: cutoff to binarize image
    :type cutoff: tuple(int, int)
    :param size: size of the spherical windows used
    :type size: int, optional
    :return: True if successful, False otherwise.
    :rtype: bool
    """
    if not isinstance(ws, Workspace):
        raise Exception("Workspace must be passed")

    ws.log.log_section("Erode Filter")
    ws.log.log_line("Spherical Window Size: " + str(size))
    ws.log.write_log()

    ws.binarize_range(cutoff)

    ws.matrix = erosion(ws.matrix, ball(size))
    return True


def filter_dilate(ws, cutoff, size=5):
    """ 3D morphological dilation filter.

    :param ws: input workspace
    :type ws: Workspace
    :param cutoff: cutoff to binarize image
    :type cutoff: tuple(int, int)
    :param size: size of the spherical windows used
    :type size: int, optional
    :return: True if successful, False otherwise.
    :rtype: bool
    """
    if not isinstance(ws, Workspace):
        raise Exception("Workspace must be passed")

    ws.log.log_section("Dilation Filter")
    ws.log.log_line("Spherical Window Size: " + str(size))
    ws.log.write_log()

    ws.binarize_range(cutoff)

    ws.matrix = dilation(ws.matrix, ball(size))
    return True


def filter_opening(ws, cutoff, size=5):
    """ 3D morphological opening filter (i.e. dilation first and then erosion).

    :param ws: input workspace
    :type ws: Workspace
    :param cutoff: cutoff to binarize image
    :type cutoff: tuple(int, int)
    :param size: size of the spherical windows used
    :type size: int, optional
    :return: True if successful, False otherwise.
    :rtype: bool
    """
    if not isinstance(ws, Workspace):
        raise Exception("Workspace must be passed")

    ws.log.log_section("Opening Filter")
    ws.log.log_line("Spherical Window Size: " + str(size))
    ws.log.write_log()

    ws.binarize_range(cutoff)

    ws.matrix = opening(ws.matrix, ball(size))
    return True


def filter_closing(ws, cutoff, size=5):
    """ 3D morphological closing filter (i.e. erosion first and then dilation).

    :param ws: input workspace
    :type ws: Workspace
    :param cutoff: cutoff to binarize image
    :type cutoff: tuple(int, int)
    :param size: size of the spherical windows used
    :type size: int, optional
    :return: True if successful, False otherwise.
    :rtype: bool
    """
    if not isinstance(ws, Workspace):
        raise Exception("Workspace must be passed")

    ws.log.log_section("Closing Filter")
    ws.log.log_line("Spherical Window Size: " + str(size))
    ws.log.write_log()

    ws.binarize_range(cutoff)

    ws.matrix = closing(ws.matrix, ball(size))
    return True
