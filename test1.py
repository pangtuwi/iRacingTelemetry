#!python3
import irsdk
ir = irsdk.IRSDK()
ir.startup()
print(ir['Speed'])