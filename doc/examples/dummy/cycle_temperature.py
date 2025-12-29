
def setTemperature(param):
    print('Tempe set : %s'%param)
    
def temperatureAtteinte(param):
    if int(param) > 50:
        return True
    else:
        return False
        