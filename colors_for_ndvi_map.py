from PyQt4.QtGui import QColor


class ColorsForNdviMap:
    colorSchemes = {
        "1": {
            "ndvi_0": QColor(4, 18, 60, 255),
            "ndvi_0.25": QColor(148, 114, 60, 255),
            "ndvi_0.5": QColor(148, 182, 20, 255),
            "ndvi_0.75": QColor(60, 134, 4, 255),
            "ndvi_1": QColor(4, 38, 4, 255)
        },
        "2": {
            "ndvi_0": QColor(99, 0, 1, 255),
            "ndvi_0.25": QColor(237, 118, 0, 255),
            "ndvi_0.5": QColor(255, 226, 0, 255),
            "ndvi_0.75": QColor(0, 211, 10, 255),
            "ndvi_1": QColor(4, 38, 4, 255)
        },
        "3": {
            "ndvi_0": QColor(0, 0, 99, 255),
            "ndvi_0.25": QColor(0, 62, 255, 255),
            "ndvi_0.5": QColor(0, 255, 227, 255),
            "ndvi_0.75": QColor(239, 249, 0, 255),
            "ndvi_1": QColor(250, 103, 44, 255)
        }
    }

    def getColorScheme(self, color_scheme_name):
        return self.colorSchemes[color_scheme_name]
