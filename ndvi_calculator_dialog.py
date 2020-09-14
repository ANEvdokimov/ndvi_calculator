# -*- coding: utf-8 -*-
"""
/***************************************************************************
 ndvi_calculatorDialog
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

import os

from PyQt4 import QtGui, uic

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'ndvi_calculator_dialog_base.ui'))


class ndvi_calculatorDialog(QtGui.QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super(ndvi_calculatorDialog, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)

        self.btn_ndvi_outputFile.clicked.connect(self.handler_btn_ndvi_outputFile)
        self.btn_ndvi_inputFile.clicked.connect(self.handler_btn_ndvi_inputFile)

        self.rbtn_calculateNdvi.clicked.connect(self.change_ndvi_calculation_mode)
        self.rbtn_openNdviFile.clicked.connect(self.change_ndvi_calculation_mode)
        self.change_ndvi_calculation_mode()
        self.prb_loading.setVisible(False)

    def handler_btn_ndvi_outputFile(self):
        users_home_directory = os.path.expanduser("~")
        file_name = QtGui.QFileDialog().getSaveFileNameAndFilter(self, "Save file", filter="*.tif",
                                                                 directory=users_home_directory)[0]
        self.led_ndvi_outputFile.setText(file_name)

    def handler_btn_ndvi_inputFile(self):
        users_home_directory = os.path.expanduser("~")
        file_name = QtGui.QFileDialog().getOpenFileNameAndFilter(self, "Open file", filter="*.tif",
                                                                 directory=users_home_directory)[0]
        self.led_ndvi_inputFile.setText(file_name)

    def show_error_message(self, error_title, error_message):
        message_box = QtGui.QMessageBox()
        message_box.setText(error_message)
        message_box.setWindowTitle(error_title)
        message_box.setStandardButtons(QtGui.QMessageBox.Ok)
        message_box.exec_()

    def enable_load_mode(self):
        self.tabw_content.setEnabled(False)
        self.button_box.button(QtGui.QDialogButtonBox.Ok).setEnabled(False)
        self.prb_loading.setVisible(True)

    def disable_load_mode(self):
        self.tabw_content.setEnabled(True)
        self.button_box.button(QtGui.QDialogButtonBox.Ok).setEnabled(True)
        self.prb_loading.setVisible(False)

    def change_ndvi_calculation_mode(self):
        if self.rbtn_calculateNdvi.isChecked():
            self.frm_calculateNdvi.setEnabled(True)
            self.frm_openNdviFile.setEnabled(False)
        elif self.rbtn_openNdviFile.isChecked():
            self.frm_calculateNdvi.setEnabled(False)
            self.frm_openNdviFile.setEnabled(True)

    def accept(self):
        self.accepted.emit()
