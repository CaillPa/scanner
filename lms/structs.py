# Values should be integers

class scanCfg():
    def __init__(self):
        self.scaningFrequency = 5000
        self.angleResolution = 5000
        self.startAngle = -50000
        self.stopAngle = 1850000

class scanDataCfg():
    def __init__(self):
        self.remission = 1
        self.resolution = 1
        self.encoder = 0
        self.position = 0
        self.deviceName = 0
        self.timestamp = 1
        self.outputinterval = 1
