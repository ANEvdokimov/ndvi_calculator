# -*- coding: utf-8 -*-

import logging
import os

import numpy as np
from PIL import Image
from PyQt4 import QtCore
from osgeo import gdal
from osgeo import osr


class RasterLayerHandler(QtCore.QObject):
    warning = QtCore.pyqtSignal(str)
    finished = QtCore.pyqtSignal(bool, str, str)

    def __init__(self, output_path, layer_list, gdal_data_type=gdal.GDT_UInt16, gdal_driver_name=r'GTiff'):
        """
        Service for combining several raster layers into a separate file.

        :param output_path: Path to a file to save the combination results.
        :type: unicode

        :param layer_list:  list of (QgsRasterLayer, band_number), band_number: the number of the band to be extracted
         to combine with others into one file.
        :type: [(QgsRasterLayer, int), ...]

        :param gdal_data_type: GDAL data type for a creating a result file.

        :param gdal_driver_name: GDAL driver name for a creating a result file.
        """
        self.LOGGER = logging.getLogger("calculator_logger")

        self.LOGGER.debug("creating RasterLayerHandler")

        QtCore.QObject.__init__(self)
        self.output_path = output_path
        self.layer_list = layer_list
        self.gdal_data_type = gdal_data_type
        self.gdal_driver_name = gdal_driver_name

    def _layer_to_array(self, layer, band_number):
        """
        Convert a band of QgsRasterLayer to array.

        :param layer: A layer to convert.
        :type: QgsRasterLayer

        :param band_number: A number of the band
        :type: int

        :return: A converted layer.
        :type: two-dimensional array
        """

        self.LOGGER.debug("converting band of QGis layer to array. layer: %s, band_number: %s", layer.name(),
                          band_number)

        self.LOGGER.info("opening file: %s", unicode(layer.source()))
        dataset = gdal.Open(unicode(layer.source()))

        self.LOGGER.debug("reading as array")
        array = dataset.ReadAsArray()

        if dataset.RasterCount == 1:
            return array
        else:
            return array[band_number - 1]

    def _equalize_arrays(self, band_list):
        """
        Equalize the sizes of two arrays.
        A smaller array is stretched to a larger size.
        The ratio of the number of rows and columns must be the same for all arrays.

        :param band_list: A List of bands to equalize.
        :type: list of two-dimensional arrays

        :return: Equalized bands.
        :type: list of two-dimensional arrays
        """

        self.LOGGER.debug("equalizing array sizes")

        max_width = 0
        max_height = 0

        # getting max width and height
        for band in band_list:
            height, width = band.shape
            if height > max_height:
                max_height = height
            if width > max_width:
                max_width = width

        # stretching all bands to maximum size
        equalized_band_list = []
        for band in band_list:
            image = Image.fromarray(band)
            equalized_band_list.append(np.array(image.resize((max_width, max_height))))

        return equalized_band_list

    def combine_bands(self):
        """
        Start combining the bands.
        A file is created in the process.
        """

        self.LOGGER.debug("merging bands to one file")

        osr.UseExceptions()

        band_list = []
        wkt = self.layer_list[0][0].crs().toWkt()
        cell_resolution_x = self.layer_list[0][0].rasterUnitsPerPixelX()
        cell_resolution_y = self.layer_list[0][0].rasterUnitsPerPixelY()
        x_min = self.layer_list[0][0].dataProvider().extent().xMinimum()
        x_max = self.layer_list[0][0].dataProvider().extent().xMaximum()
        y_min = self.layer_list[0][0].dataProvider().extent().yMinimum()
        y_max = self.layer_list[0][0].dataProvider().extent().yMaximum()
        for layer in self.layer_list:
            if wkt != layer[0].crs().toWkt():
                self.finished.emit(False, "WKT does not match", None)
                self.LOGGER.info("WKT does not match")
                return

            # location comparison
            if x_min != layer[0].dataProvider().extent().xMinimum() or \
                    x_max != layer[0].dataProvider().extent().xMaximum() or \
                    y_min != layer[0].dataProvider().extent().yMinimum() or \
                    y_max != layer[0].dataProvider().extent().yMaximum():
                self.LOGGER.info("size does not match")
                self.warning.emit("size does not match")

            # finding the highest resolution
            if cell_resolution_x > layer[0].rasterUnitsPerPixelX():
                cell_resolution_x = layer[0].rasterUnitsPerPixelX()
            if cell_resolution_y > layer[0].rasterUnitsPerPixelY():
                cell_resolution_y = layer[0].rasterUnitsPerPixelY()

            band_list.append(self._layer_to_array(layer[0], layer[1]))

        band_list = self._equalize_arrays(band_list)

        height, width = band_list[0].shape

        self.LOGGER.debug("getting driver by name: self.gdal_driver_name")
        driver = gdal.GetDriverByName(self.gdal_driver_name)

        self.LOGGER.debug("creating output_raster")
        output_raster = driver.Create(self.output_path,
                                      width,
                                      height,
                                      len(band_list),
                                      eType=self.gdal_data_type)

        geo_transform = (x_min, cell_resolution_x, 0, y_max, 0, -1 * cell_resolution_y)

        output_raster.SetProjection(str(wkt))
        output_raster.SetGeoTransform(geo_transform)

        for index in range(0, len(band_list)):
            output_band = output_raster.GetRasterBand(index + 1)
            output_band.WriteArray(band_list[index])
            output_band.FlushCache()

        if not os.path.exists(self.output_path):
            self.LOGGER.warning("File %s was not created", self.output_path)
            self.finished.emit(False, "File was not created", None)

        self.finished.emit(True, "Success", self.output_path)
