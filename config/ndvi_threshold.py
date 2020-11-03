class NdviThreshold:
    def __init__(self):
        max_uint16 = pow(2, 16) - 1
        max_int16 = pow(2, 16) / 2 - 1
        max_uint32 = pow(2, 32) - 1
        max_int32 = pow(2, 32) / 2 - 1
        self.dataTypes = {
            1: self.DataType(1, "Byte", 127, 159, 191, 223, 255),
            2: self.DataType(2, "UInt16", round(0.5 * max_uint16), round(0.625 * max_uint16), round(0.75 * max_uint16),
                             round(0.875 * max_uint16), max_uint16),
            3: self.DataType(3, "Int16", 0, round(0.25 * max_int16), round(0.2 * max_int16), round(0.27 * max_int16),
                             max_int16),
            4: self.DataType(2, "UInt32", round(0.5 * max_uint32), round(0.625 * max_uint32), round(0.75 * max_uint32),
                             round(0.875 * max_uint32), max_uint32),
            5: self.DataType(3, "Int32", 0, round(0.25 * max_int32), round(0.2 * max_int32), round(0.27 * max_int32),
                             max_int32),
            6: self.DataType(6, "Float32", 0, 0.25, 0.5, 0.75, 1),
            7: self.DataType(7, "Float64", 0, 0.25, 0.5, 0.75, 1)
        }

    class DataType:
        def __init__(self, number, name, ndvi0, ndvi025, ndvi05, ndvi075, ndvi1):
            self.number = number
            self.name = name
            self.ndvi0 = ndvi0
            self.ndvi025 = ndvi025
            self.ndvi05 = ndvi05
            self.ndvi075 = ndvi075
            self.ndvi1 = ndvi1
