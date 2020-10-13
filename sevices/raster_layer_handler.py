# -*- coding: utf-8 -*-

import os

import numpy as np
from PIL import Image
from PyQt4 import QtCore
from osgeo import gdal
from osgeo import osr


class RasterLayerHandler(QtCore.QObject):
    finished = QtCore.pyqtSignal(bool, str, str)

    def __init__(self, output_path, layer_list, gdal_data_type=gdal.GDT_UInt16, gdal_driver_name=r'GTiff'):
        """
        :param output_path:
        :param layer_list:  list of (QgsRasterLayer, band_number), band_number: the number of the band to be extracted
         to combine with others into one file.
        :param gdal_data_type:
        :param gdal_driver_name:
        """
        QtCore.QObject.__init__(self)
        self.output_path = output_path
        self.layer_list = layer_list
        self.gdal_data_type = gdal_data_type
        self.gdal_driver_name = gdal_driver_name

    def _layer_to_array(self, layer, band_number):
        dataset = gdal.Open(str(layer.source()))
        array = dataset.ReadAsArray()

        if dataset.RasterCount == 1:
            return array
        else:
            return array[band_number - 1]

    def _equalize_arrays(self, band_list):
        max_width = 0
        max_height = 0

        for band in band_list:
            height, width = band.shape
            if height > max_height:
                max_height = height
            if width > max_width:
                max_width = width

        equalized_band_list = []
        for band in band_list:
            image = Image.fromarray(band)
            equalized_band_list.append(np.array(image.resize((max_width, max_height))))

        return equalized_band_list

    def merge_bands(self):
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
                return

            if x_min != layer[0].dataProvider().extent().xMinimum() or \
                    x_max != layer[0].dataProvider().extent().xMaximum() or \
                    y_min != layer[0].dataProvider().extent().yMinimum() or \
                    y_max != layer[0].dataProvider().extent().yMaximum():
                self.finished.emit(False, "size does not match", None)

            if cell_resolution_x > layer[0].rasterUnitsPerPixelX():
                cell_resolution_x = layer[0].rasterUnitsPerPixelX()
            if cell_resolution_y > layer[0].rasterUnitsPerPixelY():
                cell_resolution_y = layer[0].rasterUnitsPerPixelY()
            band_list.append(self._layer_to_array(layer[0], layer[1]))

        band_list = self._equalize_arrays(band_list)
        height, width = band_list[0].shape

        driver = gdal.GetDriverByName(self.gdal_driver_name)
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
            self.finished.emit(False, "File was not created", None)

        self.finished.emit(True, "Success", self.output_path)
