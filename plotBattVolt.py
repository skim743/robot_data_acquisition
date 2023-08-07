import vizier.vizier
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


def main():
    timeArray = np.array([])
    voltArray = np.array([])
    
    # Initialize the vizier node for Robot 1
    v = vizier.vizier.Vizier('192.168.1.15', 1884, '1')
    try:
        v.start()
    except Exception as e:
        print(type(e), ':', e)
        try:
            v.stop()
        except Exception:
            pass
        return

    startTime = time.time()
    endTime = startTime + 120 * 60
    previousTime = time.time()

    while time.time() < endTime:
        if time.time() - previousTime >= 10:
            # Acquire voltage readings from the robot
            response = v.get('1/status')
            body = response['body']
            bodyDict = json.loads(body)
            batt_volt = bodyDict['batt_volt']
            
            timeArray = np.append(timeArray, [time.time() - startTime])
            voltArray = np.append(voltArray, [batt_volt])
            previousTime = time.time()

            dataArray = np.stack((timeArray,voltArray),axis=1)
            df = pd.DataFrame(dataArray)
            df.to_csv("voltageData.csv")

            plt.plot(timeArray, voltArray)
            plt.xlabel("Elapsed Time (s)")
            plt.ylabel("Battery Voltage (mV)")
            plt.savefig("battVoltPlot.png")

    # print(batt_volt)
    # plt.plot(timeArray, voltArray)
    # plt.xlabel("Elapsed Time (s)")
    # plt.ylabel("Battery Voltage (mV)")
    # plt.savefig("battVoltPlot.png")

    # dataArray = np.stack((timeArray,voltArray),axis=1)
    # df = pd.DataFrame(dataArray)
    # df.to_csv("voltageData.csv")

    v.stop()

    return


if __name__ == '__main__':
    main()
