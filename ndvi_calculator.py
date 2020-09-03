from qgis.analysis import QgsRasterCalculatorEntry, QgsRasterCalculator

class NdviCalculator:
    @staticmethod
    def calculateNdvi(raster_layer, red_band_number, infrared_band_number, output_file_name):
        r = QgsRasterCalculatorEntry()
        ir = QgsRasterCalculatorEntry()

        r.raster = raster_layer
        ir.raster = raster_layer

        r.bandNumber = red_band_number
        ir.bandNumber = infrared_band_number

        r.ref = raster_layer.name() + "@" + str(red_band_number)
        ir.ref = raster_layer.name() + "@" + str(infrared_band_number)

        references = (ir.ref, r.ref, ir.ref, r.ref)
        formula_string = "(%s - %s) / (%s + %s)" % references

        output_format = "GTiff"
        output_extent = raster_layer.extent()
        n_output_columns = raster_layer.width()
        n_output_rows = raster_layer.height()
        raster_entries = [ir, r]

        ndvi_raster_calculator = QgsRasterCalculator(formula_string,
                                                     output_file_name,
                                                     output_format,
                                                     output_extent,
                                                     n_output_columns,
                                                     n_output_rows,
                                                     raster_entries)
        ndvi_raster_calculator.processCalculation()
