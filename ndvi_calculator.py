# -*- coding: utf-8 -*-

from PyQt4 import QtCore
from qgis.analysis import QgsRasterCalculatorEntry, QgsRasterCalculator


class NdviCalculator(QtCore.QObject):
    finished = QtCore.pyqtSignal()

    def __init__(self, raster_layer, red_band_number, infrared_band_number, output_file_name):
        QtCore.QObject.__init__(self)
        self.killed = False

        self.raster_layer = raster_layer
        self.red_band_number = red_band_number
        self.infrared_band_number = infrared_band_number
        self.output_file_name = output_file_name

    def run(self):
        r = QgsRasterCalculatorEntry()
        ir = QgsRasterCalculatorEntry()

        r.raster = self.raster_layer
        ir.raster = self.raster_layer

        r.bandNumber = self.red_band_number
        ir.bandNumber = self.infrared_band_number

        r.ref = self.raster_layer.name() + "@" + str(self.red_band_number)
        ir.ref = self.raster_layer.name() + "@" + str(self.infrared_band_number)

        references = (ir.ref, r.ref, ir.ref, r.ref)
        formula_string = "(%s - %s) / (%s + %s)" % references

        output_format = "GTiff"
        output_extent = self.raster_layer.extent()
        n_output_columns = self.raster_layer.width()
        n_output_rows = self.raster_layer.height()
        raster_entries = [ir, r]

        ndvi_raster_calculator = QgsRasterCalculator(formula_string,
                                                     self.output_file_name,
                                                     output_format,
                                                     output_extent,
                                                     n_output_columns,
                                                     n_output_rows,
                                                     raster_entries)
        ndvi_raster_calculator.processCalculation()
        self.finished.emit()
