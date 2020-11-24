# -*- coding: utf-8 -*-

import logging

from PyQt4 import QtCore
from qgis.analysis import QgsRasterCalculatorEntry, QgsRasterCalculator


class NdviCalculator(QtCore.QObject):
    finished = QtCore.pyqtSignal(str)

    def __init__(self, red_raster_layer, infrared_raster_layer, red_band_number, infrared_band_number,
                 output_file_name):
        """
        NDVI calculator
        Calculates NDVI based on the QgsRasterCalculator.

        :param red_raster_layer: QgsRasterLayer with a red band.
        :type: QgsRasterLayer

        :param infrared_raster_layer: QgsRasterLayer with a infrared band.
        :type: QgsRasterLayer

        :param red_band_number: A number of a red band in the red_raster_layer.
        :type: int

        :param infrared_band_number: A number of a infrared band in the infrared_raster_layer.
        :type: int

        :param output_file_name: Path to a file to save the calculation results.
        :type: unicode
        """

        self.LOGGER = logging.getLogger("calculator_logger")

        self.LOGGER.debug("creating NdviCalculator")

        QtCore.QObject.__init__(self)
        self.red_raster_layer = red_raster_layer
        self.infrared_raster_layer = infrared_raster_layer
        self.red_band_number = red_band_number
        self.infrared_band_number = infrared_band_number
        self.output_file_name = output_file_name

    def run(self):
        """
        Start of calculation.
        A GTiff-file is created in the process.
        """

        self.LOGGER.debug("start NDVI calculation")

        r = QgsRasterCalculatorEntry()
        ir = QgsRasterCalculatorEntry()

        r.raster = self.red_raster_layer
        ir.raster = self.infrared_raster_layer

        r.bandNumber = self.red_band_number
        ir.bandNumber = self.infrared_band_number

        r.ref = self.red_raster_layer.name() + "@" + str(self.red_band_number)
        ir.ref = self.infrared_raster_layer.name() + "@" + str(self.infrared_band_number)

        references = (ir.ref, r.ref, ir.ref, r.ref)
        formula_string = '("%s" - "%s") / ("%s" + "%s")' % references

        output_format = "GTiff"
        output_extent = self.red_raster_layer.extent()
        n_output_columns = self.red_raster_layer.width()
        n_output_rows = self.red_raster_layer.height()
        raster_entries = [ir, r]

        ndvi_raster_calculator = QgsRasterCalculator(formula_string,
                                                     self.output_file_name,
                                                     output_format,
                                                     output_extent,
                                                     n_output_columns,
                                                     n_output_rows,
                                                     raster_entries)
        ndvi_raster_calculator.processCalculation()
        self.finished.emit(self.output_file_name)
