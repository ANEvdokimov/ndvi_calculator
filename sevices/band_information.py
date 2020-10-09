class BandInformation:
    name = None
    full_name = None
    serial_number = None
    color_interpretation = None

    def __init__(self, band_name, serial_number, color_interpretation):
        self.name = band_name
        self.full_name = str(serial_number) + " - " + band_name
        self.serial_number = serial_number
        self.color_interpretation = color_interpretation
