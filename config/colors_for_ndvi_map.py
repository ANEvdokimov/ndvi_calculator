from PyQt4.QtGui import QColor


class ColorsForNdviMap:
    colorSchemes = {
        "1.RdGr": {
            "ndvi_0": QColor(99, 0, 1, 255),
            "ndvi_0.25": QColor(237, 118, 0, 255),
            "ndvi_0.5": QColor(255, 226, 0, 255),
            "ndvi_0.75": QColor(0, 211, 10, 255),
            "ndvi_1": QColor(4, 38, 4, 255)
        },
        "2.BlGr": {
            "ndvi_0": QColor(44, 10, 121, 255),
            "ndvi_0.25": QColor(245, 10, 0, 255),
            "ndvi_0.5": QColor(250, 125, 0, 255),
            "ndvi_0.75": QColor(246, 253, 3, 255),
            "ndvi_1": QColor(31, 119, 0, 255)
        },
        "3.BlRd": {
            "ndvi_0": QColor(0, 0, 99, 255),
            "ndvi_0.25": QColor(0, 62, 255, 255),
            "ndvi_0.5": QColor(0, 255, 227, 255),
            "ndvi_0.75": QColor(239, 249, 0, 255),
            "ndvi_1": QColor(250, 103, 44, 255)
        },
        "4.Spectral": {
            "ndvi_0": QColor(215, 25, 28, 255),
            "ndvi_0.25": QColor(253, 174, 97, 255),
            "ndvi_0.5": QColor(255, 255, 191, 255),
            "ndvi_0.75": QColor(171, 221, 164, 255),
            "ndvi_1": QColor(43, 131, 186, 255)
        }
    }

    def getColorScheme(self, color_scheme_name):
        return self.colorSchemes[color_scheme_name]
