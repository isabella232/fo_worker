# -*- coding: utf-8 -*-
"""
Created on Thu Jun 30 09:55:06 2016

@author: kenneth.l.sylvain
"""
import numpy as np
import pandas as pd

# Need to change functions to allow for TFC as result of Future Space/ Brand Entry
# Need to create a max & min for category level informaiton to be passed as bounds in a long table format // Matching format to Bounding Info that is added to job context

# import os
''''
class SampleFile(object):

    src_path = os.path.dirname(__file__)
    test_files_path = os.path.join(os.path.dirname(src_path),
                                   'test/test_optimizer_files')

    @classmethod
    def get(cls, filename):
        return os.path.join(cls.test_files_path, filename)

'''
def calcPen(metric):
    return metric.div(metric.sum(axis=1),axis='index')
    
def getColumns(df):
    # print(df[[ *np.arange(len(df.columns))[0::9] ]].drop(df.index[[0]]).convert_objects(convert_numeric=True).columns)
    return df[[ *np.arange(len(df.columns))[0::9] ]].drop(df.index[[0]]).convert_objects(convert_numeric=True).columns

# def calcPen(metric,master_columns):
#     metric.columns = master_columns
#     return metric.div(metric.sum(axis=1),axis='index')

def spreadCalc(sales,boh,receipt,master_columns,salesPenetrationThreshold):
     # storing input sales and inventory data in separate 2D arrays
	 # finding sales penetration, GAFS and spread for each brand in given stores
	 # calculate adjusted penetration
     #Not necessary -- sales.columns = master_columns
     boh.columns = master_columns
     receipt.columns = master_columns
     inv=boh + receipt
     return calcPen(sales) + ((calcPen(sales) - calcPen(inv)) * float(salesPenetrationThreshold))

def spCalc(metric,master_columns):
    # storing input sales data in an array
    # finding sales penetration for each brand in given stores
    # calculate adjusted penetration
    metric.columns = master_columns
    return calcPen(metric)

def metric_per_fixture(metric1,metric2,salesPenetrationThreshold,master_columns,newSpace):
    # storing input sales data in an array
		# finding penetration for each brand in given stores
		# calculate adjusted penetration
    metric1.columns = master_columns
    # metric2.columns = master_columns
    spacePen = metric2.div(newSpace,axis='index')
    return calcPen(metric1) + ((calcPen(metric1) - spacePen) * float(salesPenetrationThreshold))

def metric_per_metric(metric1,metric2,salesPenetrationThreshold,master_columns):
    # storing input sales data in an array
		# finding penetration for each brand in given stores
		# calculate adjusted penetration
    metric1.columns = master_columns
    metric2.columns = master_columns
    return calcPen(metric1) + ((calcPen(metric1) - calcPen(metric2)) * float(salesPenetrationThreshold))

def invTurn_Calc(sold_units,boh_units,receipts_units,master_columns):
    sold_units.columns = master_columns
    boh_units.columns = master_columns
    receipts_units.columns = master_columns
    calcPen(sold_units)
    calcPen(boh_units+receipts_units)
    inv_turn = calcPen(sold_units).div(calcPen(boh_units+receipts_units),axis='index')
    inv_turn[np.isnan(inv_turn)] = 0
    inv_turn[np.isinf(inv_turn)] = 0
    return calcPen(inv_turn)
    
def roundArray(array,increment):
    rounded=np.copy(array)
    for i in range(len(array)):
        for j in range(len(list(array[0,:]))):
            if np.mod(np.around(array[i][j], 0), increment) > increment/2:
                rounded[i][j] = np.around(array[i][j], 0) + (increment-(np.mod(np.around(array[i][j], 0), increment)))
            else:         
                rounded[i][j] = np.around(array[i][j], 0) - np.mod(np.around(array[i][j], 0), increment)
    return rounded

def roundDF(array,increment):
    rounded = array.copy(True)
    for i in array.index:
        for j in array.columns:
            if np.mod(np.around(array[j].loc[i], 3), increment) > increment/2:
                rounded[j].loc[i] = np.around(array[j].loc[i], 3) + (increment-(np.mod(np.around(array[j].loc[i], 3), increment)))
            else:         
                rounded[j].loc[i] = np.around(array[j].loc[i], 3) - np.mod(np.around(array[j].loc[i], 3), increment)
    return rounded

def futureSpace(spaceData,futureFixt):
    for (i,Store) in Stores:
        if isinstance(futureFixt['Future Space'].iloc[i],str)==True:
            futureFixt['New Space'].iloc[i]=futureFixt['Future Space']
        else:
            futureFixt['New Space'].iloc[i]=spaceData.sum(axis=1).iloc[i]

    
    return futureFixt['New Space']

def brandExit(spaceData,brandExit,Stores,Categories):
    # brandExit.index.apply(lambda x: if(brandExit[Category].iloc[x]==1: spaceData[Category].iloc[x]=0))
    newSpace=pd.DataFrame(index=Stores,columns=Categories)
    for (i,Store) in enumerate(Stores):
        for (j,Category) in enumerate(Categories):
            if brandExit[Category].iloc[i] == 1:
                newSpace[Category].iloc[i] = 0
    return newSpace

def preoptimize(Stores,Categories,spaceData,data,metricAdjustment,salesPenetrationThreshold,optimizedMetrics,increment,newSpace=None,brandExitArtifact=None):
# def preoptimize(fixture_data,data,newSpace=None,metricAdjustment,salesPenetrationThreshold,optimizedMetrics,increment):
    fixture_data=spaceData.drop(spaceData.columns[[0,1]],axis=1)
    # spaceData.drop(spaceData.columns[[0,1]],axis=1,inplace=True) 
    # fixture_data.drop(fixture_data.columns[[0,1]],axis=1,inplace=True) # Access Columns dynamically
    bfc = fixture_data[[ *np.arange(len(fixture_data.columns))[0::1] ]].convert_objects(convert_numeric=True)
    sales = data[[ *np.arange(len(data.columns))[0::9] ]].convert_objects(convert_numeric=True)
    boh = data[[ *np.arange(len(data.columns))[1::9] ]].convert_objects(convert_numeric=True)
    receipt = data[[ *np.arange(len(data.columns))[2::9] ]].convert_objects(convert_numeric=True)
    sold_units = data[[ *np.arange(len(data.columns))[3::9] ]].convert_objects(convert_numeric=True)
    boh_units = data[[ *np.arange(len(data.columns))[4::9] ]].convert_objects(convert_numeric=True)
    receipts_units = data[[ *np.arange(len(data.columns))[5::9] ]].convert_objects(convert_numeric=True)
    profit = data[[ *np.arange(len(data.columns))[6::9] ]].convert_objects(convert_numeric=True)
    gm_perc = data[[ *np.arange(len(data.columns))[7::9] ]].convert_objects(convert_numeric=True)
    
    if newSpace is None:
        newSpace=bfc.sum(axis=1)
        print("We don't have futureSpace.")
    else:
        print("We have futureSpace!")
        newSpace=futureSpace(fixture_data,newSpace)
        
    if brandExitArtifact is not None:
        print("We have brandExitArtifact!")    
        # newSpace=brandExit(fixture_data,brandExitArtifact,Stores,Categories)
    else:
        print("We don't have brandExitArtifact")

    salesPenetrationThreshold=float(salesPenetrationThreshold)
    adj_p = int(optimizedMetrics['spread'])*spreadCalc(sales,boh,receipt,getColumns(data),salesPenetrationThreshold) + int(optimizedMetrics['salesPenetration'])*spCalc(sales,getColumns(data)) + int(optimizedMetrics['salesPerSpaceUnit'])*metric_per_fixture(sales,bfc,salesPenetrationThreshold,getColumns(data),newSpace) + int(optimizedMetrics['grossMargin'])*spCalc(gm_perc,getColumns(data)) + int(optimizedMetrics['inventoryTurns'])*invTurn_Calc(sold_units,boh_units,receipts_units,getColumns(data))
    

    # adj_p.fillna(np.float(0))
    # adj_p[np.isnan(adj_p)] = 0
    # adj_p.where(adj_p < metricAdjustment, 0, inplace=True)
    for i in adj_p.index:
        for j in adj_p.columns:
            if adj_p[j].loc[i] < metricAdjustment:
                adj_p[j].loc[i] = 0
    adj_p=calcPen(adj_p)
    adj_p.fillna(0)    
    # adj_p[np.isnan(adj_p)] = 0
        
    #Create Code to make adjustments to adj_p
    opt_amt = roundDF(adj_p.multiply(newSpace,axis='index'),increment)
    print(adj_p.index)
    print(opt_amt.index)
    return (adj_p,opt_amt)

'''
#For Testing 
metricAdjustment=0
salesPenetrationThreshold=0
metric=6
increment=.25
adj_p = metric_creation(transaction_data, bfc,metricAdjustment,salesPenetrationThreshold,metric,increment)
adj_p.head()
'''
#opt_amt=adj_p.multiply(bfc.sum(axis=1),axis='index').as_matrix()