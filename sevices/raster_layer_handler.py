# -*- coding: utf-8 -*-

import os

import numpy as np
from osgeo import gdal
from osgeo import osr

from calculator_exception import CalculatorException


class RasterLayerHandler:
    # config
    GDAL_DATA_TYPE = gdal.GDT_UInt16
    GEOTIFF_DRIVER_NAME = r'GTiff'

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
            equalized_band_list.append(np.kron(band, np.ones(
                (max_height / band.shape[0], max_width / band.shape[1]))))

        return equalized_band_list

    def merge_bands(self, output_path, layer_list, gdal_data_type=GDAL_DATA_TYPE, gdal_driver_name=GEOTIFF_DRIVER_NAME):
        """
        :param output_path:
        :param layer_list: list of (QgsRasterLayer, band_number), band_number: the number of the band to be extracted to
         combine with others into one file.
        :param gdal_data_type:
        :param gdal_driver_name:
        :return:
        """
        osr.UseExceptions()

        band_list = []
        wkt = layer_list[0][0].crs().toWkt()
        cell_resolution_x = layer_list[0][0].rasterUnitsPerPixelX()
        cell_resolution_y = layer_list[0][0].rasterUnitsPerPixelY()
        x_min = layer_list[0][0].dataProvider().extent().xMinimum()
        x_max = layer_list[0][0].dataProvider().extent().xMaximum()
        y_min = layer_list[0][0].dataProvider().extent().yMinimum()
        y_max = layer_list[0][0].dataProvider().extent().yMaximum()
        for layer in layer_list:
            if wkt == layer[0].crs().toWkt() and \
                    x_min == layer[0].dataProvider().extent().xMinimum() and \
                    x_max == layer[0].dataProvider().extent().xMaximum() and \
                    y_min == layer[0].dataProvider().extent().yMinimum() and \
                    y_max == layer[0].dataProvider().extent().yMaximum():
                if cell_resolution_x > layer[0].rasterUnitsPerPixelX():
                    cell_resolution_x = layer[0].rasterUnitsPerPixelX()
                if cell_resolution_y > layer[0].rasterUnitsPerPixelY():
                    cell_resolution_y = layer[0].rasterUnitsPerPixelY()

                band_list.append(self._layer_to_array(layer[0], layer[1]))
            else:
                raise CalculatorException("Merge error", "mismatched geographic locations")

        band_list = self._equalize_arrays(band_list)
        height, width = band_list[0].shape

        driver = gdal.GetDriverByName(gdal_driver_name)
        output_raster = driver.Create(output_path,
                                      width,
                                      height,
                                      len(band_list),
                                      eType=gdal_data_type)

        geo_transform = (x_min, cell_resolution_x, 0, y_max, 0, -1 * cell_resolution_y)

        output_raster.SetProjection(str(wkt))
        output_raster.SetGeoTransform(geo_transform)

        for index in range(0, len(band_list)):
            output_band = output_raster.GetRasterBand(index + 1)
            output_band.WriteArray(band_list[index])
            output_band.FlushCache()

        if not os.path.exists(output_path):
            raise CalculatorException('Create file error', 'Failed to create file: %s' % output_path)
