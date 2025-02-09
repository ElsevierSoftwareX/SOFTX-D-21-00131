import unittest
import numpy as np
import pumapy as puma
from skimage import io


class TestIsosurface(unittest.TestCase):

    def test_fiberform(self):
        ws = puma.Workspace.from_array(io.imread("testdata/200_FiberForm.tif"))
        mesh = puma.generate_isosurface(ws, (90, 255), True, False)

        np.testing.assert_equal(len(mesh.values), 665453)
        np.testing.assert_equal(mesh.faces.shape, (1330866, 3))


if __name__ == '__main__':
    unittest.main()
