# -*- coding: utf-8 -*-
"""
/***************************************************************************
 ndvi_calculator
                                 A QGIS plugin
 NDVI calculator
                              -------------------
        begin                : 2020-07-28
        git sha              : $Format:%H$
        copyright            : (C) 2020 by AN Evdokimov
        email                : an.evdokimov@inbox.ru
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
import collections
import copy
import locale
import logging
import os.path
import re
from logging.handlers import RotatingFileHandler

from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication, QThread, QObject
from PyQt4.QtGui import QAction, QIcon, QColor, QPixmap, QPainter
from qgis.core import (QgsMapLayerRegistry,
                       QgsRasterLayer,
                       QgsRaster,
                       QgsContrastEnhancement,
                       QgsRasterShader,
                       QgsColorRampShader,
                       QgsSingleBandPseudoColorRenderer)

from config.colors_for_ndvi_map import ColorsForNdviMap
from config.ndvi_threshold import NdviThreshold
from ndvi_calculator_dialog import ndvi_calculatorDialog
from sevices.band_information import BandInformation
from sevices.calculator_exception import CalculatorException
from sevices.ndvi_calculator import NdviCalculator
from sevices.raster_layer_handler import RasterLayerHandler

locale.setlocale(locale.LC_ALL, "")


class ndvi_calculator_ui_handler(QObject):
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgisInterface
        """
        super(ndvi_calculator_ui_handler, self).__init__()
        self.calculation_thread = QThread(self)
        self.calculation_worker = None

        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'ndvi_calculator_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.actions = []
        self.menu = self.getTranslation(u'&NDVI Calculator')
        # We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'ndvi_calculator')
        self.toolbar.setObjectName(u'ndvi_calculator')

        self.LOGGER = logging.getLogger("calculator_logger")
        if len(self.LOGGER.handlers) == 0:
            format_log = \
                "%(asctime)s - [%(levelname)s] -  %(name)s - (%(filename)s).%(funcName)s(%(lineno)d) - %(message)s"
            fh = RotatingFileHandler(filename=os.path.join(self.plugin_dir, "calculator.log"),
                                     maxBytes=5 * 1024 * 1024,
                                     backupCount=5)
            fh.setFormatter(logging.Formatter(format_log))
            self.LOGGER.addHandler(fh)
            self.LOGGER.setLevel(logging.DEBUG)

    # noinspection PyMethodMayBeStatic
    def getTranslation(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('ndvi_calculator', message)

    def add_action(
            self,
            icon_path,
            text,
            callback,
            enabled_flag=True,
            add_to_menu=True,
            add_to_toolbar=True,
            status_tip=None,
            whats_this=None,
            parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        # Create the dialog (after translation) and keep reference
        self.dlg = ndvi_calculatorDialog()
        self.initHandlers()

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToRasterMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = os.path.join(self.plugin_dir, 'icon.png')
        self.add_action(
            icon_path,
            text=self.getTranslation(u'Calculate NDVI'),
            callback=self.run,
            parent=self.iface.mainWindow())

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginRasterMenu(
                self.getTranslation(u'&NDVI Calculator'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar

    def initHandlers(self):
        self.LOGGER.debug("init handlers")

        self.dlg.accepted.connect(self.startCalculation)

        self.dlg.cbx_ndvi_redLayer.currentIndexChanged.connect(self.showLayerBandsForNdviRed)
        self.dlg.cbx_ndvi_infraredLayer.currentIndexChanged.connect(self.showLayerBandsForNdviInfrared)
        self.dlg.cbx_agr_swirLayer.currentIndexChanged.connect(self.showLayerBandsForAgroSwir)
        self.dlg.cbx_agr_nnirLayer.currentIndexChanged.connect(self.showLayerBandsForAgroNnir)
        self.dlg.cbx_agr_blueLayer.currentIndexChanged.connect(self.showLayerBandsForAgroBlue)

    def run(self):
        """Run method that performs all the real work"""
        logging.info("start")

        layers = QgsMapLayerRegistry.instance().mapLayers()

        self.showLayersLists(layers)
        self.showColorSchemes()

        # show the dialog
        self.LOGGER.debug("show the dialog")
        self.dlg.show()
        self.LOGGER.debug("run the dialog event loop")
        # Run the dialog event loop
        result = self.dlg.exec_()
        self.LOGGER.info("end")

    def showLayersLists(self, layers):
        self.LOGGER.debug("showing layers lists")

        self.dlg.cbx_ndvi_redLayer.clear()
        self.dlg.cbx_ndvi_infraredLayer.clear()
        self.dlg.cbx_agr_swirLayer.clear()
        self.dlg.cbx_agr_nnirLayer.clear()
        self.dlg.cbx_agr_blueLayer.clear()

        layer_names = []
        for name, layer in layers.iteritems():
            if layer.type() == 1:  # 1 = raster layer
                layer_names.append(layer.name())

        layer_names.sort(cmp=locale.strcoll)

        self.dlg.cbx_ndvi_redLayer.addItems(layer_names)
        self.dlg.cbx_ndvi_infraredLayer.addItems(layer_names)
        self.dlg.cbx_agr_swirLayer.addItems(layer_names)
        self.dlg.cbx_agr_nnirLayer.addItems(layer_names)
        self.dlg.cbx_agr_blueLayer.addItems(layer_names)

    def showLayerBandsForNdviRed(self, index):
        self.LOGGER.debug("showing bands of the red layer (NDVI)")

        layer_name = self.dlg.cbx_ndvi_redLayer.itemText(index)
        self.showLayerBands(self.dlg.lstw_ndvi_redBands, layer_name, 3)  # 3 = red

    def showLayerBandsForNdviInfrared(self, index):
        self.LOGGER.debug("showing bands of the infrared layer (NDVI)")

        layer_name = self.dlg.cbx_ndvi_infraredLayer.itemText(index)
        self.showLayerBands(self.dlg.lstw_ndvi_infraredBands, layer_name, 0)  # 0 = undefined color

    def showLayerBandsForAgroSwir(self, index):
        self.LOGGER.debug("showing bands of the SWIR layer (agriculture and HV)")

        layer_name = self.dlg.cbx_agr_swirLayer.itemText(index)
        self.showLayerBands(self.dlg.lstw_agr_swirBands, layer_name, 0)  # 0 = undefined color

    def showLayerBandsForAgroNnir(self, index):
        self.LOGGER.debug("showing bands of the NNIR layer (agriculture and HV)")

        layer_name = self.dlg.cbx_agr_nnirLayer.itemText(index)
        self.showLayerBands(self.dlg.lstw_agr_nnirBands, layer_name, 0)  # 0 = undefined color

    def showLayerBandsForAgroBlue(self, index):
        self.LOGGER.debug("showing bands of the blue layer (agriculture and HV)")

        layer_name = self.dlg.cbx_agr_blueLayer.itemText(index)
        self.showLayerBands(self.dlg.lstw_agr_blueBands, layer_name, 5)  # 5 = blue

    def showLayerBands(self, qListWidjet, layer_name, color_interpretation=None):
        self.LOGGER.debug("showing bands of %s", layer_name)

        try:
            raster_layer = QgsMapLayerRegistry.instance().mapLayersByName(layer_name)[0]
        except IndexError:
            return
        bands_dictionary = self.getBandsFromLayer(raster_layer)
        sorted(bands_dictionary)

        qListWidjet.clear()

        index = 0
        band_number = None
        for band_information in bands_dictionary.values():
            qListWidjet.addItem(band_information.full_name)
            if band_number is None and band_information.color_interpretation == color_interpretation:
                band_number = index
            index += 1

        if band_number is not None:
            qListWidjet.setCurrentRow(band_number)
        else:
            qListWidjet.setCurrentRow(0)

    def getBandsFromLayer(self, raster_layer):
        self.LOGGER.debug("getting bands of %s", raster_layer.name())

        layer_data_provider = raster_layer.dataProvider()

        bands = {}
        for band_number in range(1, raster_layer.bandCount() + 1):
            band = BandInformation(layer_data_provider.colorInterpretationName(band_number),
                                   band_number,
                                   layer_data_provider.colorInterpretation(band_number))
            bands[band.full_name] = band

        return collections.OrderedDict(sorted(bands.items()))

    def showColorSchemes(self):
        self.LOGGER.debug("showing color schemes")

        self.dlg.cbx_color_schemes.clear()
        color_schemes = ColorsForNdviMap().colorSchemes
        for color_scheme_name in color_schemes:
            color_scheme = color_schemes[color_scheme_name]
            icon_pixmap = QPixmap(50, 20)
            painter = QPainter(icon_pixmap)

            painter.fillRect(0, 0, 10, 20, color_scheme["ndvi_0"])
            painter.fillRect(10, 0, 20, 20, color_scheme["ndvi_0.25"])
            painter.fillRect(20, 0, 30, 20, color_scheme["ndvi_0.5"])
            painter.fillRect(30, 0, 40, 20, color_scheme["ndvi_0.75"])
            painter.fillRect(40, 0, 50, 20, color_scheme["ndvi_1"])
            painter.end()

            icon = QIcon(icon_pixmap)
            self.dlg.cbx_color_schemes.addItem(icon, color_scheme_name)

    def startCalculation(self):
        self.LOGGER.debug("start calculation")

        if self.calculation_thread.isRunning() is True:
            return

        if self.dlg.tabw_content.currentIndex() == 0:  # NDVI
            if self.dlg.rbtn_calculateNdvi.isChecked():
                self.calculateNdvi()
            elif self.dlg.rbtn_openNdviFile.isChecked():
                try:
                    input_file_name = self.dlg.led_ndvi_inputFile.text()
                    self.validateInputFilePath(input_file_name)
                except CalculatorException as exp:
                    self.LOGGER.info(exp.message)
                    self.dlg.show_error_message(exp.title, exp.message)
                    return
                self.openNdviFile(input_file_name)
        elif self.dlg.tabw_content.currentIndex() == 1:  # Agriculture and HV
            self.calculateAgricultureOrHv()

    def calculateAgricultureOrHv(self):
        self.LOGGER.info("start agriculture or hv calculation")
        self.LOGGER.info("Agriculture: %s", self.dlg.rbtn_agr_agriculture.isChecked())
        self.LOGGER.info("HV: %s", self.dlg.rbtn_agr_hv.isChecked())

        if self.dlg.cbx_agr_swirLayer.count() == 0 or \
                self.dlg.cbx_agr_nnirLayer.count() == 0 or \
                self.dlg.cbx_agr_blueLayer.count() == 0:
            self.LOGGER.info("Layers not found")
            self.dlg.show_error_message("error", "layers not found")
            return

        self.LOGGER.info("SWIR: %s", self.dlg.cbx_agr_swirLayer.currentText())
        self.LOGGER.info("NNIR: %s", self.dlg.cbx_agr_nnirLayer.currentText())
        self.LOGGER.info("blue: %s", self.dlg.cbx_agr_blueLayer.currentText())

        output_file_name = self.dlg.led_agr_outputFile.text()

        try:
            self.validateOutputFilePath(output_file_name)
            swir_layer = self.getLayerByName(self.dlg.cbx_agr_swirLayer.currentText())
            nnir_layer = self.getLayerByName(self.dlg.cbx_agr_nnirLayer.currentText())
            blue_layer = self.getLayerByName(self.dlg.cbx_agr_blueLayer.currentText())

            swir_band = self.getBandsFromLayer(swir_layer)[self.getCurrentBandName(self.dlg.lstw_agr_swirBands)]
            nnir_band = self.getBandsFromLayer(nnir_layer)[self.getCurrentBandName(self.dlg.lstw_agr_nnirBands)]
            blue_band = self.getBandsFromLayer(blue_layer)[self.getCurrentBandName(self.dlg.lstw_agr_blueBands)]
        except CalculatorException as exp:
            self.LOGGER.info(exp.message)
            self.dlg.show_error_message(exp.title, exp.message)
            return

        if self.dlg.rbtn_agr_agriculture.isChecked():
            layer_list = [(swir_layer, swir_band.serial_number),
                          (nnir_layer, nnir_band.serial_number),
                          (blue_layer, blue_band.serial_number)]
        elif self.dlg.rbtn_agr_hv.isChecked():
            layer_list = [(nnir_layer, nnir_band.serial_number),
                          (swir_layer, swir_band.serial_number),
                          (blue_layer, blue_band.serial_number)]
        else:
            return

        self.dlg.enable_load_mode()

        self.calculation_worker = RasterLayerHandler(output_file_name, layer_list)
        self.calculation_worker.moveToThread(self.calculation_thread)
        self.calculation_thread.started.connect(self.calculation_worker.merge_bands)
        self.calculation_worker.warning.connect(self.showWarning)
        self.calculation_worker.finished.connect(self.finishAgricultureOrHvCalculation)
        self.calculation_thread.start()

    def calculateNdvi(self):
        self.LOGGER.info("start NDVI calculation")

        if self.dlg.cbx_ndvi_redLayer.count() == 0 or \
                self.dlg.cbx_ndvi_infraredLayer.count() == 0:
            self.LOGGER.info("Layers not found")
            self.dlg.show_error_message("error", "layers not found")
            return

        self.LOGGER.info("red: %s", self.dlg.cbx_ndvi_redLayer.currentText())
        self.LOGGER.info("red band number: %s", self.dlg.lstw_ndvi_redBands.currentItem().text())
        self.LOGGER.info("IR: %s", self.dlg.cbx_ndvi_infraredLayer.currentText())
        self.LOGGER.info("IR band number: %s", self.dlg.lstw_ndvi_infraredBands.currentItem().text)

        output_file_name = self.dlg.led_ndvi_outputFile.text()

        try:
            self.validateOutputFilePath(output_file_name)
            red_layer_for_calculation = self.getCurrentLayerWithRedBand()
            infrared_layer_for_calculation = self.getCurrentLayerWithInfraredBand()

            bands = self.getBandsFromLayer(red_layer_for_calculation)
            red_band = bands[self.getCurrentBandName(self.dlg.lstw_ndvi_redBands)]

            bands = self.getBandsFromLayer(infrared_layer_for_calculation)
            infrared_band = bands[self.getCurrentBandName(self.dlg.lstw_ndvi_infraredBands)]
        except CalculatorException as exp:
            self.LOGGER.info(exp.message)
            self.dlg.show_error_message(exp.title, exp.message)
            return

        self.dlg.enable_load_mode()

        self.calculation_worker = NdviCalculator(red_layer_for_calculation, infrared_layer_for_calculation,
                                                 red_band.serial_number, infrared_band.serial_number, output_file_name)
        self.calculation_worker.moveToThread(self.calculation_thread)
        self.calculation_thread.started.connect(self.calculation_worker.run)
        self.calculation_worker.finished.connect(self.finishCalculationNdvi)
        self.calculation_thread.start()

    def getCurrentLayerWithRedBand(self):
        self.LOGGER.debug("getting current a layer with red band")

        layer_name = self.dlg.cbx_ndvi_redLayer.currentText()
        return self.getLayerByName(layer_name)

    def getCurrentLayerWithInfraredBand(self):
        self.LOGGER.debug("getting current a layer with IR band")

        layer_name = self.dlg.cbx_ndvi_infraredLayer.currentText()
        return self.getLayerByName(layer_name)

    def getLayerByName(self, layer_name):
        self.LOGGER.debug("getting a layer by name: %s", layer_name)

        try:
            return QgsMapLayerRegistry.instance().mapLayersByName(layer_name)[0]
        except IndexError:
            raise CalculatorException("Layer not found", "Layer with name \"%s\" not found" % layer_name)

    def getCurrentBandName(self, lstw_ndv):
        self.LOGGER.debug("getting current band name from the UI. Band name: %s", lstw_ndv.currentItem().text())

        return lstw_ndv.currentItem().text()

    def validateInputFilePath(self, file_path):
        self.LOGGER.debug("validating input file path: %s", file_path)

        if not os.path.exists(file_path):
            self.LOGGER.info("input file - file do not exist")
            raise CalculatorException("file error", "file do not exist")

    def validateOutputFilePath(self, file_path):
        self.LOGGER.debug("validating output file path: %s", file_path)

        if not file_path:
            self.LOGGER.info("output file - file path is None")
            raise CalculatorException("file error", "file path is None")

        file_path_copy = copy.copy(file_path)
        pattern = re.compile(ur"/(?u)\w+.tif$")

        try:
            file_name = pattern.search(file_path_copy).group(0)
        except AttributeError:
            self.LOGGER.info("output file - incorrect file name")
            raise CalculatorException("file error", "incorrect file name")

        directory_name = pattern.sub(u"", file_path_copy)
        if not os.path.isdir(directory_name):
            self.LOGGER.info("output file - incorrect directory name")
            raise CalculatorException("file error", "incorrect directory name")

    def finishCalculationNdvi(self, output_file_name):
        self.LOGGER.debug("end of NDVI calculation")

        self.calculation_thread.quit()
        self.dlg.disable_load_mode()
        self.openNdviFile(output_file_name)

    def openNdviFile(self, file_name):
        self.LOGGER.info("opening NDVI file: %s", file_name)

        try:
            self.validateInputFilePath(file_name)
        except CalculatorException as e:
            self.LOGGER.info(e.message)
            self.dlg.show_error_message(e.title, e.message)
            return

        ndvi0_raster_layer = QgsRasterLayer(file_name, "NDVI - <0")

        layer_data_type = ndvi0_raster_layer.dataProvider().dataType(1)
        ndvi_thresholds = NdviThreshold().dataTypes.get(layer_data_type)
        if ndvi_thresholds is None:
            self.LOGGER.info("NDVI file - unknown data type")
            self.dlg.show_error_message("ndvi file open error", "unknown data type")
            ndvi_raster_layer = QgsRasterLayer(file_name, "NDVI")
            map_layer_registry = QgsMapLayerRegistry.instance()
            map_layer_registry.addMapLayer(ndvi_raster_layer)
            return

        ndvi025_raster_layer = QgsRasterLayer(file_name, "NDVI - 0-0.25")
        ndvi05_raster_layer = QgsRasterLayer(file_name, "NDVI - 0.25-0.5")
        ndvi075_raster_layer = QgsRasterLayer(file_name, "NDVI - 0.5-0.75")
        ndvi1_raster_layer = QgsRasterLayer(file_name, "NDVI - 0.75-1")

        algorithm = QgsContrastEnhancement.StretchToMinimumMaximum
        limits = QgsRaster.ContrastEnhancementMinMax
        ndvi0_raster_layer.setContrastEnhancement(algorithm, limits)
        ndvi025_raster_layer.setContrastEnhancement(algorithm, limits)
        ndvi05_raster_layer.setContrastEnhancement(algorithm, limits)
        ndvi075_raster_layer.setContrastEnhancement(algorithm, limits)
        ndvi1_raster_layer.setContrastEnhancement(algorithm, limits)

        colors_scheme = ColorsForNdviMap().getColorScheme(self.dlg.cbx_color_schemes.currentText())
        ndvi0_raster_layer.setRenderer(
            self.getRenderer(ndvi0_raster_layer.dataProvider(),
                             self.getColorMapForNdvi0(colors_scheme, ndvi_thresholds)))
        ndvi025_raster_layer.setRenderer(
            self.getRenderer(ndvi025_raster_layer.dataProvider(),
                             self.getColorMapForNdvi025(colors_scheme, ndvi_thresholds)))
        ndvi05_raster_layer.setRenderer(
            self.getRenderer(ndvi05_raster_layer.dataProvider(),
                             self.getColorMapForNdvi05(colors_scheme, ndvi_thresholds)))
        ndvi075_raster_layer.setRenderer(
            self.getRenderer(ndvi075_raster_layer.dataProvider(),
                             self.getColorMapForNdvi075(colors_scheme, ndvi_thresholds)))
        ndvi1_raster_layer.setRenderer(
            self.getRenderer(ndvi1_raster_layer.dataProvider(),
                             self.getColorMapForNdvi1(colors_scheme, ndvi_thresholds)))

        map_layer_registry = QgsMapLayerRegistry.instance()
        map_layer_registry.addMapLayer(ndvi0_raster_layer)
        map_layer_registry.addMapLayer(ndvi025_raster_layer)
        map_layer_registry.addMapLayer(ndvi05_raster_layer)
        map_layer_registry.addMapLayer(ndvi075_raster_layer)
        map_layer_registry.addMapLayer(ndvi1_raster_layer)

    def getRenderer(self, layer_data_provider, color_map):
        self.LOGGER.debug("getting renderer")

        raster_shader = QgsRasterShader()
        color_ramp_shader = QgsColorRampShader()
        color_ramp_shader.setColorRampType(QgsColorRampShader.DISCRETE)

        color_ramp_shader.setColorRampItemList(color_map)
        raster_shader.setRasterShaderFunction(color_ramp_shader)
        return QgsSingleBandPseudoColorRenderer(layer_data_provider, 1, raster_shader)

    def getColorMapForNdvi0(self, colors_scheme, ndvi_thresholds):
        self.LOGGER.debug("getting color map for NDVI 0")

        color_list = []
        qri = QgsColorRampShader.ColorRampItem
        color_list.append(qri(ndvi_thresholds.ndvi0, colors_scheme["ndvi_0"], "<0"))
        color_list.append(qri(ndvi_thresholds.ndvi1, QColor(0, 0, 0, 0), ">0"))
        return color_list

    def getColorMapForNdvi025(self, colors_scheme, ndvi_thresholds):
        self.LOGGER.debug("getting color map for NDVI 0.25")

        color_list = []
        qri = QgsColorRampShader.ColorRampItem
        color_list.append(qri(ndvi_thresholds.ndvi0, QColor(0, 0, 0, 0), "<0"))
        color_list.append(qri(ndvi_thresholds.ndvi025, colors_scheme["ndvi_0.25"], "0-0.25"))
        color_list.append(qri(ndvi_thresholds.ndvi1, QColor(0, 0, 0, 0), ">0.25"))
        return color_list

    def getColorMapForNdvi05(self, colors_scheme, ndvi_thresholds):
        self.LOGGER.debug("getting color map for NDVI 0.5")

        color_list = []
        qri = QgsColorRampShader.ColorRampItem
        color_list.append(qri(ndvi_thresholds.ndvi025, QColor(0, 0, 0, 0), "<0.25"))
        color_list.append(qri(ndvi_thresholds.ndvi05, colors_scheme["ndvi_0.5"], "0.25-0.5"))
        color_list.append(qri(ndvi_thresholds.ndvi1, QColor(0, 0, 0, 0), ">0.5"))
        return color_list

    def getColorMapForNdvi075(self, colors_scheme, ndvi_thresholds):
        self.LOGGER.debug("getting color map for NDVI 0.75")

        color_list = []
        qri = QgsColorRampShader.ColorRampItem
        color_list.append(qri(ndvi_thresholds.ndvi05, QColor(0, 0, 0, 0), "<0.5"))
        color_list.append(qri(ndvi_thresholds.ndvi075, colors_scheme["ndvi_0.75"], "0.5-0.75"))
        color_list.append(qri(ndvi_thresholds.ndvi1, QColor(0, 0, 0, 0), ">0.75"))
        return color_list

    def getColorMapForNdvi1(self, colors_scheme, ndvi_thresholds):
        self.LOGGER.debug("getting color map for NDVI 1")

        color_list = []
        qri = QgsColorRampShader.ColorRampItem
        color_list.append(qri(ndvi_thresholds.ndvi075, QColor(0, 0, 0, 0), "<0.75"))
        color_list.append(qri(ndvi_thresholds.ndvi1, colors_scheme["ndvi_1"], ">0.75"))
        return color_list

    def showWarning(self, message):
        self.LOGGER.debug("showing warning dialog. message: %s", message)

        self.dlg.show_error_message("warning", message)

    def finishAgricultureOrHvCalculation(self, status, message, output_file_name):
        self.LOGGER.debug("end of agriculture or HV calculation")

        self.calculation_thread.quit()
        self.dlg.disable_load_mode()

        if status is False:
            self.dlg.show_error_message("Calculation error", message)
        else:
            self.openAgricultureOrHvFile(output_file_name)

    def openAgricultureOrHvFile(self, output_file_name):
        self.LOGGER.info("opening agriculture or HV file %s", output_file_name)

        if self.dlg.rbtn_agr_agriculture.isChecked():
            layer_name = "Agriculture"
        elif self.dlg.rbtn_agr_hv.isChecked():
            layer_name = "Healthy_Vegetation"
        else:
            return

        raster_layer = QgsRasterLayer(output_file_name, layer_name)
        map_layer_registry = QgsMapLayerRegistry.instance()
        map_layer_registry.addMapLayer(raster_layer)
