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
import os.path

from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication
from PyQt4.QtGui import QAction, QIcon, QColor
from qgis.analysis import QgsRasterCalculatorEntry, QgsRasterCalculator
from qgis.core import (QgsMapLayerRegistry,
                       QgsRasterLayer,
                       QgsRaster,
                       QgsContrastEnhancement,
                       QgsRasterShader,
                       QgsColorRampShader,
                       QgsSingleBandPseudoColorRenderer)

# Import the code for the dialog
from ndvi_calculator_dialog import ndvi_calculatorDialog


class ndvi_calculator:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgisInterface
        """
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
        self.menu = self.tr(u'&NDVI Calculator')
        # We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'ndvi_calculator')
        self.toolbar.setObjectName(u'ndvi_calculator')

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
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
            text=self.tr(u'Calculate NDVI'),
            callback=self.run,
            parent=self.iface.mainWindow())

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginRasterMenu(
                self.tr(u'&NDVI Calculator'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar

    def run(self):
        """Run method that performs all the real work"""
        map_layer_registry = QgsMapLayerRegistry.instance()
        layers = map_layer_registry.mapLayers()
        self.dlg.cbx_layers.clear()

        for name, raster_layer in layers.iteritems():
            self.dlg.cbx_layers.addItem(raster_layer.name())

        # show the dialog
        self.dlg.show()
        # Run the dialog event loop
        result = self.dlg.exec_()

        # See if OK was pressed
        if result:
            if not self.dlg.led_output_file.text():
                self.dlg.show_file_name_error()
                return

            raster_layer = map_layer_registry.mapLayersByName(str(self.dlg.cbx_layers.currentText()))[0]
            ndvi_layers_list = self.calculateNdvi(raster_layer)
            for layer in ndvi_layers_list:
                map_layer_registry.addMapLayer(layer)

    def calculateNdvi(self, raster_layer):
        r = QgsRasterCalculatorEntry()
        ir = QgsRasterCalculatorEntry()

        r.raster = raster_layer
        ir.raster = raster_layer

        r.bandNumber = 3
        ir.bandNumber = 4

        r.ref = raster_layer.name() + "@3"
        ir.ref = raster_layer.name() + "@4"

        references = (ir.ref, r.ref, ir.ref, r.ref)
        formula_string = "(%raster_shader - %raster_shader) / (%raster_shader + %raster_shader)" % references

        output_file = self.dlg.led_output_file.text()
        output_format = "GTiff"
        output_extent = raster_layer.extent()
        n_output_columns = raster_layer.width()
        n_output_rows = raster_layer.height()
        raster_entries = [ir, r]

        ndvi_raster_calculator = QgsRasterCalculator(formula_string,
                                                     output_file,
                                                     output_format,
                                                     output_extent,
                                                     n_output_columns,
                                                     n_output_rows,
                                                     raster_entries)
        ndvi_raster_calculator.processCalculation()

        ndvi0_raster_layer = QgsRasterLayer(output_file, "NDVI - <0")
        ndvi025_raster_layer = QgsRasterLayer(output_file, "NDVI - 0-0.25")
        ndvi05_raster_layer = QgsRasterLayer(output_file, "NDVI - 0.25-0.5")
        ndvi075_raster_layer = QgsRasterLayer(output_file, "NDVI - 0.5-0.75")
        ndvi1_raster_layer = QgsRasterLayer(output_file, "NDVI - 0.75-1")

        algorithm = QgsContrastEnhancement.StretchToMinimumMaximum
        limits = QgsRaster.ContrastEnhancementMinMax
        ndvi0_raster_layer.setContrastEnhancement(algorithm, limits)
        ndvi025_raster_layer.setContrastEnhancement(algorithm, limits)
        ndvi05_raster_layer.setContrastEnhancement(algorithm, limits)
        ndvi075_raster_layer.setContrastEnhancement(algorithm, limits)
        ndvi1_raster_layer.setContrastEnhancement(algorithm, limits)

        ndvi0_raster_layer.setRenderer(
            self.getRenderer(ndvi0_raster_layer.dataProvider(), self.getColorMapForNdvi0()))
        ndvi025_raster_layer.setRenderer(
            self.getRenderer(ndvi025_raster_layer.dataProvider(), self.getColorMapForNdvi025()))
        ndvi05_raster_layer.setRenderer(
            self.getRenderer(ndvi05_raster_layer.dataProvider(), self.getColorMapForNdvi05()))
        ndvi075_raster_layer.setRenderer(
            self.getRenderer(ndvi075_raster_layer.dataProvider(), self.getColorMapForNdvi075()))
        ndvi1_raster_layer.setRenderer(
            self.getRenderer(ndvi1_raster_layer.dataProvider(), self.getColorMapForNdvi1()))

        return [ndvi0_raster_layer, ndvi025_raster_layer, ndvi05_raster_layer, ndvi075_raster_layer, ndvi1_raster_layer]

    def getRenderer(self, layer_data_provider, color_map):
        raster_shader = QgsRasterShader()
        color_ramp_shader = QgsColorRampShader()
        color_ramp_shader.setColorRampType(QgsColorRampShader.DISCRETE)

        color_ramp_shader.setColorRampItemList(color_map)
        raster_shader.setRasterShaderFunction(color_ramp_shader)
        return QgsSingleBandPseudoColorRenderer(layer_data_provider, 1, raster_shader)

    def getColorMapForNdvi0(self):
        color_list = []
        qri = QgsColorRampShader.ColorRampItem
        color_list.append(qri(0, QColor(4, 18, 60, 255), "<0"))
        color_list.append(qri(1, QColor(0, 0, 0, 0), ">0"))
        return color_list

    def getColorMapForNdvi025(self):
        color_list = []
        qri = QgsColorRampShader.ColorRampItem
        color_list.append(qri(0, QColor(0, 0, 0, 0), "<0"))
        color_list.append(qri(0.25, QColor(148, 114, 60, 255), "0-0.25"))
        color_list.append(qri(1, QColor(0, 0, 0, 0), ">0.25"))
        return color_list

    def getColorMapForNdvi05(self):
        color_list = []
        qri = QgsColorRampShader.ColorRampItem
        color_list.append(qri(0.25, QColor(0, 0, 0, 0), "<0.25"))
        color_list.append(qri(0.5, QColor(148, 182, 20, 255), "0.25-0.5"))
        color_list.append(qri(1, QColor(0, 0, 0, 0), ">0.5"))
        return color_list

    def getColorMapForNdvi075(self):
        color_list = []
        qri = QgsColorRampShader.ColorRampItem
        color_list.append(qri(0.5, QColor(0, 0, 0, 0), "<0.5"))
        color_list.append(qri(0.75, QColor(60, 134, 4, 255), "0.5-0.75"))
        color_list.append(qri(1, QColor(0, 0, 0, 0), ">0.75"))
        return color_list

    def getColorMapForNdvi1(self):
        color_list = []
        qri = QgsColorRampShader.ColorRampItem
        color_list.append(qri(0.75, QColor(0, 0, 0, 0), "<0.75"))
        color_list.append(qri(1, QColor(4, 38, 4, 255), ">0.75"))
        return color_list
