#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Created on Thu Jun  2 11:33:51 2016

@author: kenneth.l.sylvain
"""

from pulp import *
import numpy as np
import pandas as pd
import datetime as dt


def create_output_artifact_from_dataframe(dataframe, *args, **kwargs):
    """
    Returns the bson.objectid.ObjectId of the resulting GridFS artifact

    """
    return fs.put(dataframe.to_csv().encode(), **kwargs)


def createLevels(mergedPreOptCF, increment):
    minLevel = mergedPreOptCF.loc[:, 'Lower_Limit'].min()
    maxLevel = mergedPreOptCF.loc[:, 'Upper_Limit'].max()
    Levels = list(np.arange(minLevel, maxLevel + increment, increment))
    if 0.0 not in Levels:
        Levels.append(np.abs(0.0))


    return Levels


# Helper function for createSPUByLevel function, to forecast weighted combination of sales, profit, and units
# str_cat is the row of the curve-fitting output for an individual store and category
# variable can take on the values of "Sales", "Profit", or "Units"
def forecast(str_cat, space, variable):
    if space < str_cat["Scaled_BP_" + variable]:
        value = space * (str_cat["Scaled_Alpha_" + variable] * (erf(
            (str_cat["Scaled_BP_" + variable] - str_cat["Scaled_Shift_" + variable]) / (
                math.sqrt(2) * str_cat["Scaled_Beta_" + variable]))) / str_cat["Scaled_BP_" + variable])
    else:
        value = str_cat["Scaled_Alpha_" + variable] * erf(
            (space - str_cat["Scaled_Shift_" + variable]) / (math.sqrt(2) * str_cat["Scaled_Beta_" + variable]))

    return value


# Helper function for optimize function, to create objective function of SPU by level for Enhanced optimizations
def createNegSPUByLevel(Stores, Categories, Levels, curveFittingOutput, enhMetrics):
    # Create n-dimensional array to store Estimated SPU by level
    est_neg_spu_by_lev = np.zeros((len(Stores), len(Categories), len(Levels)))

    sU = "Sales"
    pU = "Profit"
    uU = "Units"
    sL = "sales"
    pL = "profits"

    # Calculate SPU by level
    for (i, Store) in enumerate(Stores):
            for (k, Level) in enumerate(Levels):
                str_cat = curveFittingOutput.loc[Store, Category]
                est_neg_spu_by_lev[i][j][k] = - (
                    (enhMetrics[sL] / 100) * forecast(str_cat, Level, sU) + (enhMetrics[pL] / 100) * forecast(str_cat,
                                                                                                              Level,
                                                                                                              pU) + (
                        enhMetrics[uL] / 100) * forecast(str_cat, Level, uU))

    return est_neg_spu_by_lev


# Helper function for optimize function, to create objective function of error by level for Traditional optimizations
def createErrorByLevel(Stores, Categories, Levels, mergedCurveFitting):
    # Create n-dimensional array to store error by level
    error = np.zeros((len(Stores), len(Categories), len(Levels)))

    # Calculate error by level
    for (i, Store) in enumerate(Stores):
        for (j, Category) in enumerate(Categories):
            for (k, Level) in enumerate(Levels):
                error[i][j][k] = np.absolute(mergedCurveFitting.loc[Store, Category]["Optimal Space"] - Level)
    return error

def optimize(jobName,Stores,Categories,tierCounts,spaceBound,increment,dataMunged):
    """
    Run an LP-based optimization

    Side-effects:
        - creates file: Fixture_Optimization.lp (constraints)
        - creates file: solvedout.csv <= to be inserted into db
        - creates file: solvedout.text

    Synopsis:
        I just wrapped the script from Ken in a callable - DCE
    """
    dataMunged = dataMunged.apply(lambda x: pd.to_numeric(x, errors='ignore'))
    start_time = dt.datetime.today().hour*60*60+ dt.datetime.today().minute*60 + dt.datetime.today().second
    opt_amt=dataMunged.pivot(index='Store', columns='Category', values='Optimal Space') #preOpt[1]
    brandExitArtifact = dataMunged.pivot(index='Store', columns='Category', values='Exit Flag')

    print("HEY I'M IN THE OPTIMIZATION!!!!!!!")
    ###############################################################################################
    # Reading in of Files & Variable Set Up|| Will be changed upon adoption into tool
    ###############################################################################################

    ##########################################################################################
    ##################Vector Creation ||May be moved to another module/ program in the future
    ##########################################################################################
    # opt_amt.index=opt_amt.index.values.astype(int)
    # Stores = opt_amt.index.tolist()
    # Setting up the Selected Tier Combinations -- Need to redo if not getting or creating data for all possible levels
    # Categories = opt_amt.columns.values
    minLevel = min(min(spaceBound.values())) # min(opt_amt.min())
    maxLevel = max(max(spaceBound.values()))  # max(opt_amt.max())
    Levels = list(np.arange(minLevel, maxLevel + increment, increment))
    if 0.0 not in Levels:
        Levels.insert(0,0.0)
    print(Levels)
    b = .05
    bI = .1

    # Create a Vectors & Arrays of required variables
    # Calculate Total fixtures(TotFixt) per store by summing up the individual fixture counts
    W = opt_amt.sum(axis=1).sum(axis=0)
    TFC = opt_amt.sum(axis=1)
    ct = LpVariable.dicts('CT', (Categories, Levels), 0, upBound=1,cat='Binary')
    st = LpVariable.dicts('ST', (Stores, Categories, Levels), 0,upBound=1, cat='Binary')

    NewOptim = LpProblem(jobName, LpMinimize)  # Define Optimization Problem/

    # Brand Exit Enhancement
    # if brandExitArtifact is None:
    #     print("No Brand Exit in the Optimization")
    # else:
    #     for (i, Store) in enumerate(Stores):
    #         for (j, Category) in enumerate(Categories):
    #             if (brandExitArtifact[Category].loc[Store] != 0):
    #                 upper_bound[Category].loc[Store] = 0
    #                 lower_bound[Category].loc[Store] = 0
                    # opt_amt[Category].loc[Store] = 0
                    # NewOptim += st[Store][Category][0.0] == 1
                    # NewOptim += ct[Category][0.0] == 1
                    # spaceBound[Category][0] = 0


        # for (j, Category) in enumerate(Categories):
        #     if (sum(brandExitArtifact[Category].values()) > 0):
        #         tier_count["Upper_Bound"][Category] += 1
    BA = np.zeros((len(Stores), len(Categories), len(Levels)))
    error = np.zeros((len(Stores), len(Categories), len(Levels)))
    for (i, Store) in enumerate(Stores):
        for (j, Category) in enumerate(Categories):
            for (k, Level) in enumerate(Levels):
                BA[i][j][k] = opt_amt[Category].iloc[i]
                error[i][j][k] = np.absolute(BA[i][j][k] - Level)

    NewOptim += lpSum([(st[Store][Category][Level] * error[i][j][k]) for (i, Store) in enumerate(Stores) for (j, Category) in enumerate(Categories) for (k, Level) in enumerate(Levels)]), ""

###############################################################################################################
############################################### Constraints
###############################################################################################################
#Makes is to that there is only one Selected tier for each Store/ Category Combination
    for (i,Store) in enumerate(Stores):
#Conditional for Balance Back regarding if in Fixtures || 2 Increment Min & Max instead
        if TFC[Store] > increment * 5:
            NewOptim += lpSum([(st[Store][Category][Level]) * Level for (j, Category) in enumerate(Categories) for (k, Level) in enumerate(Levels)]) <= TFC[Store] * (1 + bI)#, "Upper Bound for Fixtures per Store"
            NewOptim += lpSum([(st[Store][Category][Level]) * Level for (j, Category) in enumerate(Categories) for (k, Level) in enumerate(Levels)]) >= TFC[Store] * (1 - bI)#, "Lower Bound for Fixtures per Store"
        else:
            NewOptim += lpSum([(st[Store][Category][Level]) * Level for (j, Category) in enumerate(Categories) for (k, Level) in enumerate(Levels)]) <= TFC[Store] + (increment * 2)#, "Upper Bound for Fixtures per Store"
            NewOptim += lpSum([(st[Store][Category][Level]) * Level for (j, Category) in enumerate(Categories) for (k, Level) in enumerate(Levels)]) >= TFC[Store] - (increment * 2)#, "Lower Bound for Fixtures per Store"
        
#One Space per Store Category
    #Makes sure that the number of fixtures, by store, does not go above or below some percentage of the total number of fixtures within the store 
        for (j,Category) in enumerate(Categories):
            NewOptim += lpSum([st[Store][Category][Level] for (k,Level) in enumerate(Levels)]) == 1#, "One_Level_per_Store-Category_Combination"
        # Test Again to check if better performance when done on ct level
            NewOptim += lpSum([st[Store][Category][Level] * Level for (k,Level) in enumerate(Levels)]) <= spaceBound[Category][1]         
            # if brandExitArtifact is not None:
            #     if brandExitArtifact[Category].iloc[int(i)] == 0:
            #         NewOptim += lpSum([st[Store][Category][Level] * Level for (k,Level) in enumerate(Levels)]) >= spaceBound[Category][0] + increment
            #     else:
            #         NewOptim += lpSum([st[Store][Category][Level] * Level for (k,Level) in enumerate(Levels)]) >= spaceBound[Category][0]
            # else:
            NewOptim += lpSum([st[Store][Category][Level] * Level for (k,Level) in enumerate(Levels)]) >= spaceBound[Category][0]
            
#Store Category Level Bounding
        #NewOptim += lpSum([st[Store][Category][Level] * Level for (k,Level) in enumerate(Levels)] ) >= lower_bound[Category][Store]#,
        #NewOptim += lpSum([st[Store][Category][Level] * Level for (k,Level) in enumerate(Levels)] ) <= upper_bound[Category][Store]#,

#Tier Counts Enhancement
    totalTiers=0
    for (j,Category) in enumerate(Categories):
        totalTiers=totalTiers+tierCounts[Category][1]
        NewOptim += lpSum([ct[Category][Level] for (k,Level) in enumerate(Levels)]) >= tierCounts[Category][0] #, "Number_of_Tiers_per_Category"
        NewOptim += lpSum([ct[Category][Level] for (k,Level) in enumerate(Levels)]) <= tierCounts[Category][1]
#Relationship between Selected Tiers & Created Tiers
    #Verify that we still cannot use a constraint if not using a sum - Look to improve efficiency   
        for (k,Level) in enumerate(Levels):
            NewOptim += lpSum([st[Store][Category][Level] for (i,Store) in enumerate(Stores)])/len(Stores) <= ct[Category][Level]#, "Relationship between ct & st"
   
    NewOptim += lpSum([ct[Category][Level] for (j,Category) in enumerate(Categories) for (k,Level) in enumerate(Levels)]) <= totalTiers #len(Categories)*sum(tier_count[Category][1].values())

#Global Balance Back  
    NewOptim += lpSum(
        [st[Store][Category][Level] * Level for (i, Store) in enumerate(Stores) for (j, Category) in enumerate(Categories) for
         (k, Level) in enumerate(Levels)]) >= W * (1 - b)
    NewOptim += lpSum(
        [st[Store][Category][Level] * Level for (i, Store) in enumerate(Stores) for (j, Category) in enumerate(Categories) for
         (k, Level) in enumerate(Levels)]) <= W * (1 + b)
    # NewOptim.writeLP("Fixture_Optimization.lp")
    # LpSolverDefault.msg = 1
    print("The problem has been formulated")

#Solving the Problem
    # NewOptim.writeLP("Fixture_Optimization.lp")
    # NewOptim.writeMPS("Fixture_Optimization.mps")
    # NewOptim.msg=1
    # NewOptim.solve(pulp.PULP_CBC_CMD(msg=1))
    NewOptim.solve()    
    # NewOptim.solve(pulp.COIN_CMD(msg=1))
    
#Debugging
    print("#####################################################################")
    print(LpStatus[NewOptim.status])
    print("#####################################################################")
    # Debugging
    NegativeCount = 0
    LowCount = 0
    TrueCount = 0
    OneCount = 0
    for (i, Store) in enumerate(Stores):
        for (j, Category) in enumerate(Categories):
            for (k, Level) in enumerate(Levels):
                if value(st[Store][Category][Level]) == 1:
                    # print(st[Store][Category][Level]) #These values should only be a one or a zero
                    OneCount += 1
                elif value(st[Store][Category][Level]) > 0:
                    # print(st[Store][Category][Level],"Value is: ",value(st[Store][Category][Level])) #These values should only be a one or a zero
                    TrueCount += 1
                elif value(st[Store][Category][Level]) == 0:
                    # print(value(st[Store][Category][Level])) #These values should only be a one or a zero
                    LowCount += 1
                elif value(st[Store][Category][Level]) < 0:
                    # print(st[Store][Category][Level],"Value is: ",value(st[Store][Category][Level])) #These values should only be a one or a zero
                    NegativeCount += 1
    
    ctNegativeCount = 0
    ctLowCount = 0
    ctTrueCount = 0
    ctOneCount = 0
    
    for (j, Category) in enumerate(Categories):
        for (k, Level) in enumerate(Levels):
            if value(ct[Category][Level]) == 1:
                # print(value(ct[Store][Category][Level])) #These values should only be a one or a zero
                ctOneCount += 1
            elif value(ct[Category][Level]) > 0:
                # print(ct[Store][Category][Level],"Value is: ",value(st[Store][Category][Level])) #These values should only be a one or a zero
                ctTrueCount += 1
            elif value(ct[Category][Level]) == 0:
                # print(value(ct[Category][Level])) #These values should only be a one or a zero
                ctLowCount += 1
            elif value(ct[Category][Level]) < 0:
                # print(ct[Category][Level],"Value is: ",value(st[Store][Category][Level])) #These values should only be a one or a zero
                ctNegativeCount += 1

    print("Status:", LpStatus[NewOptim.status])
    print("---------------------------------------------------")
    print("For Selected Tiers")
    print("Number of Negatives Count is: ", NegativeCount)
    print("Number of Zeroes Count is: ", LowCount)
    print("Number Above 0 and Below 1 Count is: ", TrueCount)
    print("Number of Selected Tiers: ", OneCount)
    print("---------------------------------------------------")
    print("For Created Tiers")
    print("Number of Negatives Count is: ", ctNegativeCount)
    print("Number of Zeroes Count is: ", ctLowCount)
    print("Number Above 0 and Below 1 Count is: ", ctTrueCount)
    print("Number of Created Tiers: ", ctOneCount)
    print("Creating Outputs")

    Results=pd.DataFrame(index=Stores,columns=Categories)
    for (i,Store) in enumerate(Stores):
        for (j,Category) in enumerate(Categories):
            for (k,Level) in enumerate(Levels):
                if value(st[Store][Category][Level]) == 1:
                    Results[Category][Store] = Level
    Results.reset_index(inplace=True)
    Results.columns.values[0]='Store'
    Results = pd.melt(Results.reset_index(), id_vars=['Store'], var_name='Category', value_name='Result Space')
    Results=Results.apply(lambda x: pd.to_numeric(x, errors='ignore'))
    dataMunged=pd.merge(dataMunged,Results,on=['Store','Category'])
    print(dataMunged.columns)
    return (LpStatus[NewOptim.status],dataMunged) #(longOutput)#,wideOutput)

# if __name__ == '__main__':
#     df = pd.DataFrame(np.random.randn(10, 5), columns=['a', 'b', 'c', 'd', 'e'])
#     create_output_artifact_from_dataframe(df, filename='hello.csv')
