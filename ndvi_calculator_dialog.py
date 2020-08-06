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

        self.btn_output_file.clicked.connect(self.handler_btn_output_file)

    def handler_btn_output_file(self):
        file_name = QtGui.QFileDialog().getSaveFileNameAndFilter(self, "Save file", filter="*.tif")[0]
        self.led_output_file.setText(file_name)

    @staticmethod
    def show_file_name_error():
        message_box = QtGui.QMessageBox()
        message_box.setText("empty file name")
        message_box.setWindowTitle("Error")
        message_box.setStandardButtons(QtGui.QMessageBox.Ok)
        message_box.exec_()
