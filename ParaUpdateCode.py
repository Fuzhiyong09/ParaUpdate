# coding: utf-8
import numpy as np
#from scipy.linalg import cholesky
#from pyDOE import *
#from scipy.stats.distributions import norm

# import the system module
from dbfread import DBF
import pandas as pd
import os
import gc

# import the arcgis module
import arcpy
from arcpy import env
from arcpy.sa import *

## ----------主要用于参数反演解决参数不匹配问题-------- ##


# 1.1 读取参数
Path = r"D:/software/arcgis/BeforAndPara/TestFile"
Litho = r"D:/software/arcgis/BeforAndPara/Relitho.tif"
FrSuscep = r"D:\SarFile\Gis_file\Wenchuan\PreDisSuscepWen.tif"
Slope = r"D:/software/arcgis/BeforAndPara/Slope.tif"

# 栅格化
FrSuscep = arcpy.Raster(FrSuscep)
Slope = arcpy.Raster(Slope)
ArcSlope = Slope * 3.1415 / 180
arcpy.env.overwriteOutput = True

# 定义全局格点和坐标系
arcpy.env.snapRaster = FrSuscep
arcpy.env.outputCoordinateSystem = FrSuscep
cellSize = 30

# 1.2 定义参数
ReduceCoe = [1, 1, 1, 1, 1]  # 折减系数
ReduceCoeAfter = [2.5, 2.5, 3, 2, 2]  #调整折减系数
Cohesions = [140, 140, 150, 50, 140]  # 粘聚力
Phis = [0.49, 0.49, 0.53, 0.19, 0.49]  # 内摩擦角
Gamas = [22, 22, 27, 15, 22] # 容重
Depth =  4 # 定义滑面深度
DesignA = 0.2

LithoArc= arcpy.Raster(Litho)
FOSs = LithoArc # 定义安全系数
LithoStableBefor = [] #震前稳定样本比例
LithoFailurBefor = [] #震前破坏样本比例

# 1.3 计算失效概率
#MinFrSuscep =eval(arcpy.GetRasterProperties_management(FrSuscep, "Minimum").getOutput(0))
#MaxFrSuscep = eval(arcpy.GetRasterProperties_management(FrSuscep, "Maximum").getOutput(0))
#PossBefore = (FrSuscep - MinFrSuscep) / (MaxFrSuscep - MinFrSuscep)
FailBefor = Con(FrSuscep > 5.9, 1, 0) # 转换成 0, 1

# 1.4 获取分类统计
inZoneData = Litho  # 分类统计表
zoneField = "Value"
inClassData = FailBefor
classField = "Value"
OutTable = r"D:/software/arcgis/BeforAndPara/TestFile/AccuBefor.dbf"
TabulateArea(inZoneData, zoneField, inClassData, classField, OutTable, cellSize)  # 获取不同地层岩性计算结果

# 计算不同岩性正负样本概率
# 读取计算结果
CurAccubefor = arcpy.da.SearchCursor(OutTable, ['Value_0', 'Value_1'])
for rows in CurAccubefor:
    LithoStableBefor.append(rows[0] / (rows[0] + rows[1]))
    LithoFailurBefor.append(rows[1] / (rows[0] + rows[1]))

##-------2 计算稳定性系数----------##
# 2.1 定义准确率并获取重分类栅格数据

LithoValue = []
LithoCount = []

Cur = arcpy.da.SearchCursor(Litho, ['Value', 'Count'])
for rows in Cur:
    LithoValue.append(rows[0])
    LithoCount.append(rows[1])

LithoAccu = [0, 0, 0, 0, 0]

for i in range(40):
    LithoAccuAfter = []  # 强度折减后准确率
    LithoClassfy = []

    LithoAccuFailAfter = []  #稳定预测准确率
    LithoFailClassfy = []

    #计算迭代稳定性系数
    for iter in range(len(ReduceCoeAfter)):
        FOSs = Con(Slope > 10, Con(LithoArc == iter, Cohesions[iter] / (Gamas[iter] * ReduceCoeAfter[iter] * Depth * (Sin(ArcSlope) + DesignA*Cos(ArcSlope))) + (Phis[iter] * (Cos(ArcSlope) - DesignA *Sin(ArcSlope)))/ (ReduceCoeAfter[iter] * (Sin(ArcSlope) + DesignA * Cos(ArcSlope))), FOSs), 2) # 计算稳定性系数

    print(FOSs)

    #FOSs.save(r"D:/software/arcgis/BeforAndPara/TestFile/foss1")
    FailAfter = Con(FOSs > 1.2, 0, 1)  # 对稳定性系数进行判断
    AllAccu = Con(Slope < 10,1,(Con(FailAfter == FailBefor, 1, 0)))  # 对比震前震后判断结果

    ##------3 计算不同区域预测准确率 -------------##
    # 3.1 获取震前震后最初匹配率

    ReAllAccu = Reclassify(AllAccu, 'Value', RemapValue([[0, 0],[1, 1]])) #重分类

    inZoneData = Litho  #分类统计表
    zoneField = "Value"
    inClassData = ReAllAccu
    classField = "Value"
    OutTable = r"D:/software/arcgis/BeforAndPara/TestFile/AccuResult.dbf"
    TabulateArea(inZoneData, zoneField, inClassData, classField, OutTable, cellSize) # 获取不同地层岩性计算结果

    # 读取计算结果
    CurAccu = arcpy.da.SearchCursor(OutTable, ['Value_0', 'Value_1'])
    for rows in CurAccu:
        LithoClassfy.append(rows[1])

    # 获取准确率
    for num in range(len(LithoClassfy)):
        LithoAccuAfter.append(LithoClassfy[num] / (900 * LithoCount[num]))

    # 3.2 进行强度折减
    for num in range(len(LithoClassfy)):

        if LithoAccuAfter[num] > LithoAccu[num]:
            ReduceCoe[num] = ReduceCoeAfter[num]
            LithoAccu[num] = LithoAccuAfter[num]
        else:
            ReduceCoeAfter[num] = ReduceCoeAfter[num] - 0.1
    print(ReduceCoe, LithoAccu)
FOSs = Con(FOSs>10, 10, FOSs)
#FOSs.save(r"D:/software/arcgis/BeforAndPara/TestFile/Foss_test")
