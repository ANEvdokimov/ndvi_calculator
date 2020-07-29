# -*- coding: utf-8 -*-
"""
/***************************************************************************
 ndvi_calculator
                                 A QGIS plugin
 NDVI calculator
                             -------------------
        begin                : 2020-07-28
        copyright            : (C) 2020 by AN Evdokimov
        email                : an.evdokimov@inbox.ru
        git sha              : $Format:%H$
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load ndvi_calculator class from file ndvi_calculator.

    :param iface: A QGIS interface instance.
    :type iface: QgisInterface
    """
    #
    from .ndvi_calculator import ndvi_calculator
    return ndvi_calculator(iface)
