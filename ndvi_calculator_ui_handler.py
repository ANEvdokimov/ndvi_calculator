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
import os.path
import re

from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication, QThread, QObject
from PyQt4.QtGui import QAction, QIcon, QColor, QPixmap, QPainter
from qgis.core import (QgsMapLayerRegistry,
                       QgsRasterLayer,
                       QgsRaster,
                       QgsContrastEnhancement,
                       QgsRasterShader,
                       QgsColorRampShader,
                       QgsSingleBandPseudoColorRenderer)

from band_information import BandInformation
from calculator_exception import CalculatorException
from colors_for_ndvi_map import ColorsForNdviMap
from ndvi_calculator import NdviCalculator
from ndvi_calculator_dialog import ndvi_calculatorDialog


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

        icon_path = ':/plugins/ndvi_calculator/icon.png'
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

    def run(self):
        """Run method that performs all the real work"""
        try:
            self.dlg.accepted.disconnect(self.startCalculation)
        except TypeError:
            # if the TypeError was thrown, then there was not the connection (at first start)
            pass

        self.dlg.accepted.connect(self.startCalculation)

        layers = QgsMapLayerRegistry.instance().mapLayers()

        self.showLayersListForNdvi(layers)
        self.showColorSchemes()

        self.dlg.btn_debug.clicked.connect(self.debug_f)

        # show the dialog
        self.dlg.show()
        # Run the dialog event loop
        result = self.dlg.exec_()

    def showLayersListForNdvi(self, layers):
        self.dlg.cbx_ndvi_redLayer.clear()
        self.dlg.cbx_ndvi_infraredLayer.clear()

        self.dlg.cbx_ndvi_redLayer.currentIndexChanged.connect(self.cbx_ndvi_redLayer_handler)
        self.dlg.cbx_ndvi_infraredLayer.currentIndexChanged.connect(self.ccbx_ndvi_infraredLayer_handler)

        for name, layer in layers.iteritems():
            if layer.type() == 1:  # 1 = raster layer
                self.dlg.cbx_ndvi_redLayer.addItem(layer.name())
                self.dlg.cbx_ndvi_infraredLayer.addItem(layer.name())

    def cbx_ndvi_redLayer_handler(self, index):
        layer_name = self.dlg.cbx_ndvi_redLayer.itemText(index)
        try:
            current_layer = QgsMapLayerRegistry.instance().mapLayersByName(layer_name)[0]
        except IndexError:
            return

        bands_dictionary = self.getBandsFromLayer(current_layer)
        sorted(bands_dictionary)

        self.dlg.lstw_ndvi_redBands.clear()

        index = 0
        for band_information in bands_dictionary.values():
            self.dlg.lstw_ndvi_redBands.addItem(band_information.full_name)
            if band_information.color_interpretation == 3:
                self.dlg.lstw_ndvi_redBands.setCurrentRow(index)
            index += 1

    def ccbx_ndvi_infraredLayer_handler(self, index):
        layer_name = self.dlg.cbx_ndvi_infraredLayer.itemText(index)

        try:
            current_layer = QgsMapLayerRegistry.instance().mapLayersByName(layer_name)[0]
        except IndexError:
            return

        bands_dictionary = self.getBandsFromLayer(current_layer)
        sorted(bands_dictionary)

        self.dlg.lstw_ndvi_infraredBands.clear()

        index = 0
        for band_information in bands_dictionary.values():
            self.dlg.lstw_ndvi_infraredBands.addItem(band_information.full_name)
            if band_information.color_interpretation == 0:
                self.dlg.lstw_ndvi_infraredBands.setCurrentRow(index)
            index += 1

    def getBandsFromLayer(self, raster_layer):
        layer_data_provider = raster_layer.dataProvider()

        bands = {}
        for band_number in range(1, raster_layer.bandCount() + 1):
            band = BandInformation(layer_data_provider.colorInterpretationName(band_number),
                                   band_number,
                                   layer_data_provider.colorInterpretation(band_number))
            bands[band.full_name] = band

        return collections.OrderedDict(sorted(bands.items()))

    def showColorSchemes(self):
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
        if self.calculation_thread.isRunning() is True:
            return

        if self.dlg.rbtn_calculateNdvi.isChecked():
            self.calculateNdvi()
        elif self.dlg.rbtn_openNdviFile.isChecked():
            try:
                input_file_name = self.dlg.led_ndvi_inputFile.text()
                self.validateInputFilePath(input_file_name)
            except CalculatorException as exp:
                self.dlg.show_error_message(exp.title, exp.message)
                return
            self.outputNdviLayers(input_file_name)

    def calculateNdvi(self):
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
            self.dlg.show_error_message(exp.title, exp.message)
            return

        self.dlg.enable_load_mode()

        self.calculation_worker = NdviCalculator(red_layer_for_calculation, infrared_layer_for_calculation,
                                                 red_band.serial_number, infrared_band.serial_number, output_file_name)
        self.calculation_worker.moveToThread(self.calculation_thread)
        self.calculation_thread.started.connect(self.calculation_worker.run)
        self.calculation_worker.finished.connect(self.finishCalculationThread)
        self.calculation_thread.start()

    def getCurrentLayerWithRedBand(self):
        layer_name = self.dlg.cbx_ndvi_redLayer.currentText()
        return self.getLayerByName(layer_name)

    def getCurrentLayerWithInfraredBand(self):
        layer_name = self.dlg.cbx_ndvi_infraredLayer.currentText()
        return self.getLayerByName(layer_name)

    def getLayerByName(self, layer_name):
        try:
            return QgsMapLayerRegistry.instance().mapLayersByName(layer_name)[0]
        except IndexError:
            raise CalculatorException("Layer not found", "Layer with name \"%s\" not found" % layer_name)

    def getCurrentBandName(self, lstw_ndv):
        return lstw_ndv.currentItem().text()

    def validateInputFilePath(self, file_path):
        if not os.path.exists(file_path):
            raise CalculatorException("file error", "file do not exist")

    def validateOutputFilePath(self, file_path):
        if not file_path:
            raise CalculatorException("file error", "file path is None")

        file_path_copy = copy.copy(file_path)
        pattern = re.compile(ur"/(?u)\w+.tif$")

        try:
            file_name = pattern.search(file_path_copy.decode("utf8")).group(0)
        except AttributeError:
            raise CalculatorException("file error", "incorrect file name")

        directory_name = pattern.sub(u"", file_path_copy.decode("utf8"))
        if not os.path.isdir(directory_name):
            raise CalculatorException("file error", "incorrect directory name")

    def finishCalculationThread(self, output_file_name):
        self.calculation_thread.quit()
        self.dlg.disable_load_mode()
        self.outputNdviLayers(output_file_name)

    def outputNdviLayers(self, file_name):
        ndvi0_raster_layer = QgsRasterLayer(file_name, "NDVI - <0")
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
            self.getRenderer(ndvi0_raster_layer.dataProvider(), self.getColorMapForNdvi0(colors_scheme)))
        ndvi025_raster_layer.setRenderer(
            self.getRenderer(ndvi025_raster_layer.dataProvider(), self.getColorMapForNdvi025(colors_scheme)))
        ndvi05_raster_layer.setRenderer(
            self.getRenderer(ndvi05_raster_layer.dataProvider(), self.getColorMapForNdvi05(colors_scheme)))
        ndvi075_raster_layer.setRenderer(
            self.getRenderer(ndvi075_raster_layer.dataProvider(), self.getColorMapForNdvi075(colors_scheme)))
        ndvi1_raster_layer.setRenderer(
            self.getRenderer(ndvi1_raster_layer.dataProvider(), self.getColorMapForNdvi1(colors_scheme)))

        map_layer_registry = QgsMapLayerRegistry.instance()
        map_layer_registry.addMapLayer(ndvi0_raster_layer)
        map_layer_registry.addMapLayer(ndvi025_raster_layer)
        map_layer_registry.addMapLayer(ndvi05_raster_layer)
        map_layer_registry.addMapLayer(ndvi075_raster_layer)
        map_layer_registry.addMapLayer(ndvi1_raster_layer)

    def getRenderer(self, layer_data_provider, color_map):
        raster_shader = QgsRasterShader()
        color_ramp_shader = QgsColorRampShader()
        color_ramp_shader.setColorRampType(QgsColorRampShader.DISCRETE)

        color_ramp_shader.setColorRampItemList(color_map)
        raster_shader.setRasterShaderFunction(color_ramp_shader)
        return QgsSingleBandPseudoColorRenderer(layer_data_provider, 1, raster_shader)

    def getColorMapForNdvi0(self, colors_scheme):
        color_list = []
        qri = QgsColorRampShader.ColorRampItem
        color_list.append(qri(0, colors_scheme["ndvi_0"], "<0"))
        color_list.append(qri(1, QColor(0, 0, 0, 0), ">0"))
        return color_list

    def getColorMapForNdvi025(self, colors_scheme):
        color_list = []
        qri = QgsColorRampShader.ColorRampItem
        color_list.append(qri(0, QColor(0, 0, 0, 0), "<0"))
        color_list.append(qri(0.25, colors_scheme["ndvi_0.25"], "0-0.25"))
        color_list.append(qri(1, QColor(0, 0, 0, 0), ">0.25"))
        return color_list

    def getColorMapForNdvi05(self, colors_scheme):
        color_list = []
        qri = QgsColorRampShader.ColorRampItem
        color_list.append(qri(0.25, QColor(0, 0, 0, 0), "<0.25"))
        color_list.append(qri(0.5, colors_scheme["ndvi_0.5"], "0.25-0.5"))
        color_list.append(qri(1, QColor(0, 0, 0, 0), ">0.5"))
        return color_list

    def getColorMapForNdvi075(self, colors_scheme):
        color_list = []
        qri = QgsColorRampShader.ColorRampItem
        color_list.append(qri(0.5, QColor(0, 0, 0, 0), "<0.5"))
        color_list.append(qri(0.75, colors_scheme["ndvi_0.75"], "0.5-0.75"))
        color_list.append(qri(1, QColor(0, 0, 0, 0), ">0.75"))
        return color_list

    def getColorMapForNdvi1(self, colors_scheme):
        color_list = []
        qri = QgsColorRampShader.ColorRampItem
        color_list.append(qri(0.75, QColor(0, 0, 0, 0), "<0.75"))
        color_list.append(qri(1, colors_scheme["ndvi_1"], ">0.75"))
        return color_list

    def debug_f(self):
        self.dlg.lbl_debug.setText(self.getCurrentLayerFromDialogWindow().name().encode("utf8").decode("utf8"))
        with open("c:/Users/evdok/Desktop/test.txt", "w") as file2:
            file2.write(self.getCurrentLayerFromDialogWindow().name().encode("utf8"))
