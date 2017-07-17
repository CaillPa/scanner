"""
    Structures contenant les parametres du telemetre
    Les valeurs doivent etre des entiers, pas des octets
"""
# configuration du telemetre
class scanCfg():
    def __init__(self):
        self.scaningFrequency = 5000
        self.angleResolution = 5000
        self.startAngle = -50000
        self.stopAngle = 1850000

# configuration des donnees du telemetre
class scanDataCfg():
    def __init__(self):
        self.remission = 1
        self.resolution = 1
        self.encoder = 0
        self.position = 0
        self.deviceName = 0
        self.timestamp = 1
        self.outputinterval = 1
