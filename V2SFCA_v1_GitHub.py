'''-----------------------------------------------------------------------------
# Name:        V2SFCA_Version_1.0
# Purpose:     Implement the Variable Two-Step Floating Catchment Area method
# Author:      Sagert Sheets
# Created:     December 2017
# Note:        GitHub version. Provided for review purposes only.
#----------------------------------------------------------------------------'''

# Import necessary modules
import numpy
import arcpy
from arcpy import env
env.overwriteOutput = True

# Check for & check out extension (except if license is unavailable)
try:
    if arcpy.CheckExtension("Network") == "Available":
        pass
    else:
        raise Exception
except:
    arcpy.AddError("Network Analyst License is unavailable.")

# Global variables that will appear in multiple functions
accumMinutes = "Total_Minutes"
weightField = "Weight"
doubleType = "DOUBLE"
minutes = "Minutes"

# A function for calculating weights
def gaussianWeights(dist,coefficient):
    '''Weights may be an approximation'''
    weight = numpy.exp(-numpy.power(dist, 2.0)/coefficient)
    return weight

# A function for finding the coefficient, if necessary.
def gaussianSolve(dist,targetWeight):
    '''Coefficient may be an approximation'''
    coefficient = -numpy.power(dist, 2.0)/numpy.log(targetWeight)
    return coefficient

# A function for updating weight values after each step
def writeWeights(ODMatrixTable, distance, coefficient):
    with arcpy.da.UpdateCursor(ODMatrixTable, [accumMinutes,
                                weightField]) as weightWriter:
        for row in weightWriter:
            if (0 < row[0] <= distance) == True:
                row[1] = gaussianWeights(row[0], coefficient)
            else:
                row[1] = 0
            weightWriter.updateRow(row)
    return

# A function for applying weights to volume values
def applyWeights(ODMatrixTable, inField, outField):
    with arcpy.da.UpdateCursor(ODMatrixTable, [inField, weightField,
                                outField]) as weightApplier:
        for row in weightApplier:
            row[2] = row[0] * row[1]
            weightApplier.updateRow(row)
    return

# A function for implementing the user's choice for volume
def writeVolume(inTable, newField, volumeValue):
    arcpy.AddField_management(inTable, newField, "DOUBLE")
    with arcpy.da.UpdateCursor(inTable, newField) as volumeCursor:
        for row in volumeCursor:
            row[0] = volumeValue
            volumeCursor.updateRow(row)
    return newField

# Main function
def v2sfca():
    # Parameters retrieved as variables
    arcpy.AddMessage("Retrieving paramters...")
    # Network Dataset - REQUIRED
    inputND = arcpy.GetParameterAsText(0)
    # Supply(Resource) Points - REQUIRED
    inputSupply = arcpy.GetParameterAsText(1)
    # Volume of Supply (e.g. beds per hospital) - REQUIRED
    supplyVolumeOpt = arcpy.GetParameterAsText(2)    #Choice
    supplyVolumeField = arcpy.GetParameterAsText(3)    #Field
    supplyVolumeValue = float(arcpy.GetParameter(4))    #Class value
    # Demand (Population) Points - REQUIRED
    inputDemand = arcpy.GetParameterAsText(5)
    # Volume of Demand (e.g. population)
    demandVolumeOpt = arcpy.GetParameterAsText(6)    #Choice
    demandVolumeField = arcpy.GetParameterAsText(7)    #Field
    demandVolumeValue = float(arcpy.GetParameter(8))    #Class value
    # Distance threshold
    distance = float(arcpy.GetParameter(9))
    #Use coefficient or calculate based on weight
    coeffOrWeight = arcpy.GetParameterAsText(10)    #Choice
    coefficient = float(arcpy.GetParameter(11))    #Coefficient value
    targetWeight = float(arcpy.GetParameter(12))    #Target weight value
    #Output features
    outputFC = arcpy.GetParameterAsText(13)
    #Output report
    report = arcpy.GetParameterAsText(14)

    #Check weighting method
    if coeffOrWeight == "Use target weight":
        coefficient = gaussianSolve(distance, targetWeight)
    else:
        pass

    # Make working feature layers based on supply & demand inputs
    arcpy.AddMessage("Preparing input features...")
    workingSupplyLayer = "workingSupplyLayer"
    workingDemandLayer = "workingDemandLayer"
    workingSupply = arcpy.MakeFeatureLayer_management(inputSupply, workingSupplyLayer)
    workingDemand = arcpy.MakeFeatureLayer_management(inputDemand, workingDemandLayer)

    # Check if Volume fields exist or if Volume values should be applied...
    if supplyVolumeOpt == "Constant volume value":
        supplyVolumeField = writeVolume(workingSupply, "Supply_Vol", supplyVolumeValue)
    elif supplyVolumeOpt == "Volume from field":
        pass
    if demandVolumeOpt == "Constant volume value":
        demandVolumeField = writeVolume(workingDemand, "Demand_Vol", demandVolumeValue)
    elif demandVolumeOpt == "Volume from field":
        pass

    # Prepare extra fields for weights & calculations
    weightedSupply = "WghtSupply"
    weightedDemand = "WghtDemand"
    step1Score = "Step1_Score"
    step2Score = "Step2_Score"
    sparField = "SPAR"
    # Add fields to Supply
    arcpy.AddField_management(workingSupply, step1Score, doubleType)
    # Add fields to Demand
    arcpy.AddField_management(workingDemand, step2Score, doubleType)
    arcpy.AddField_management(workingDemand, sparField, doubleType)

    #Get ObjectID fields
    supplyOID = arcpy.Describe(inputSupply).OIDFieldName
    demandOID = arcpy.Describe(inputDemand).OIDFieldName
    #Prepare for using ODMatrix ID Fields
    originID = "OriginID"
    destID = "DestinationID"

    # Step 1
    # Create OD Matrix Layer
    arcpy.AddMessage("Creating First Origin-Destination Matrix...")
    try:
        arcpy.CheckOutExtension("Network")
        step1NALayer = arcpy.na.MakeODCostMatrixLayer(inputND, "step1NALayer", minutes,
                                                    distance, "", [minutes])
        # Get layer object
        step1Layer = step1NALayer.getOutput(0)
        # Identify sub-layers
        step1subLayers = arcpy.na.GetNAClassNames(step1Layer)
        # Variables for easy use of Origins & Desintations & Lines layers
        step1origins = step1subLayers["Origins"]
        step1destinations = step1subLayers["Destinations"]
        step1lines = step1subLayers["ODLines"]
        # Get location fields
        step1fieldsO = arcpy.ListFields(inputSupply)
        step1fieldsD = arcpy.ListFields(inputDemand)
        # Origins
        step1Ofieldmap = arcpy.na.NAClassFieldMappings(step1Layer, step1origins, True, step1fieldsO)
        # Add Locations for Origins
        arcpy.AddMessage("Adding Origins...")
        arcpy.na.AddLocations(step1Layer, step1origins, inputSupply, step1Ofieldmap, "")
        # Destinations
        step1Dfieldmap = arcpy.na.NAClassFieldMappings(step1Layer, step1destinations, True, step1fieldsD)
        # Add locations for Destinations
        arcpy.AddMessage("Adding Destinations...")
        arcpy.na.AddLocations(step1Layer, step1destinations, inputDemand, step1Dfieldmap, "")
        # Solve
        arcpy.AddMessage("Solving Origin-Destination Matrix...")
        arcpy.na.Solve(step1Layer)
        # Dictionary for accessing to solved sublayers
        step1LyrDict = dict((lyr.datasetName, lyr) for lyr in arcpy.mapping.ListLayers(step1Layer)[1:])
        step1LinesTable = step1LyrDict["ODLines"]
        # I think this variable will help
        step1matrix = "step1matrix"
        arcpy.MakeTableView_management(step1LinesTable, step1matrix)
    except:
        ODMatrixError = arcpy.GetMessages(2)
        arcpy.AddMessage(ODMatrixError)
        arcpy.AddError("The first O-D Matrix could not be completed.")
    finally:
        arcpy.CheckInExtension("Network")

    # Join layers
    arcpy.AddMessage("Joining layers...")
    arcpy.JoinField_management(step1matrix, destID, workingDemand, demandOID, demandVolumeField)
    arcpy.AddField_management(step1matrix, weightField, doubleType, 15, 14)
    arcpy.AddField_management(step1matrix, weightedDemand, doubleType, 15, 14)

    # Use weight functions
    arcpy.AddMessage("First Step: Applying weights...")
    writeWeights(step1matrix, distance, coefficient)
    applyWeights(step1matrix, demandVolumeField, weightedDemand)

    arcpy.AddMessage("First Step: Calculating scores...")
    # Using cursors to assign a score for Step 1
    with arcpy.da.UpdateCursor(workingSupply, [supplyOID, supplyVolumeField, step1Score]) as scoreWriter:
        for item in scoreWriter:
            with arcpy.da.SearchCursor(step1matrix, [originID, weightedDemand]) as popReader:
                score = 0
                for demand in popReader:
                    if item[0] == demand[0]:
                        score += demand[1]
                        continue
                    else:
                        continue
                item[2] = item[1]/score #multiplier removed here
                scoreWriter.updateRow(item)
    del demand, popReader, item, scoreWriter

    # Second step
    arcpy.AddMessage("Creating Second Origin-Destination Matrix...")
    # Create OD Matrix Layer
    try:
        arcpy.CheckOutExtension("Network")
        step2NALayer = arcpy.na.MakeODCostMatrixLayer(inputND, "step2NALayer", minutes,
                                                    distance, "", [minutes])
        # Get layer object
        step2Layer = step2NALayer.getOutput(0)
        # Identify sub-layers
        step2subLayers = arcpy.na.GetNAClassNames(step2Layer)
        # Variables for easy use of Origins & Desintations & Lines layers
        step2origins = step2subLayers["Origins"]
        step2destinations = step2subLayers["Destinations"]
        step2lines = step2subLayers["ODLines"]
        # Get location fields
        step2fieldsO = arcpy.ListFields(inputDemand)
        step2fieldsD = arcpy.ListFields(inputSupply)
        # Origins
        step2Ofieldmap = arcpy.na.NAClassFieldMappings(step2Layer, step2origins, True, step2fieldsO)
        # Add Locations for Origins
        arcpy.AddMessage("Adding Origins...")
        arcpy.na.AddLocations(step2Layer, step2origins, inputDemand, step2Ofieldmap, "")
        # Destinations
        step2Dfieldmap = arcpy.na.NAClassFieldMappings(step2Layer, step2destinations, True, step2fieldsD)
        # Add locations for Destinations
        arcpy.AddMessage("Adding Destinations...")
        arcpy.na.AddLocations(step2Layer, step2destinations, inputSupply, step2Dfieldmap, "")
        # Solve
        arcpy.AddMessage("Solving Origin-Destination Matrix...")
        arcpy.na.Solve(step2Layer)
        # Dictionary for accessing to solved sublayers
        step2LyrDict = dict((lyr.datasetName, lyr) for lyr in arcpy.mapping.ListLayers(step2Layer)[1:])
        step2LinesTable = step2LyrDict["ODLines"]
        # I think this variable will help
        step2matrix = "step2matrix"
        arcpy.MakeTableView_management(step2LinesTable, step2matrix)
    except:
        ODMatrixError = arcpy.GetMessages(2)
        arcpy.AddMessage(ODMatrixError)
        arcpy.AddError("The second O-D Matrix could not be completed.")
    finally:
        arcpy.CheckInExtension("Network")

    arcpy.AddMessage("Joining layers...")
    arcpy.JoinField_management(step2matrix, destID, workingSupply, supplyOID, step1Score)
    arcpy.AddField_management(step2matrix, weightField, doubleType, 15, 14)
    arcpy.AddField_management(step2matrix, weightedSupply, doubleType, 15, 14)

    arcpy.AddMessage("Second Step: Applying weights... ")
    writeWeights(step2matrix, distance, coefficient)
    applyWeights(step2matrix, step1Score, weightedSupply)

    arcpy.AddMessage("Second Step: Calculating scores... ")
    # Using cursors to assign a score for Step 2
    with arcpy.da.UpdateCursor(workingDemand, [demandOID, step2Score]) as scoreUpdater:
        for place in scoreUpdater:
            with arcpy.da.SearchCursor(step2matrix, [originID, weightedSupply]) as scoreChecker:
                score = 0
                for supply in scoreChecker:
                    if place[0] == supply[0]:
                        score += supply[1]
                        continue
                    else:
                        continue
                place[1] = score
                scoreUpdater.updateRow(place)
    del supply, scoreChecker, place, scoreUpdater

    arcpy.AddMessage("Calculating SPAR...")
    # Find the average SPAI (v2sfca score)
    totalSpai = 0
    totalScores = 0
    scoreSet = set()
    scoreAdder = arcpy.da.SearchCursor(workingDemand, [step2Score])
    for row in scoreAdder:
        totalSpai += row[0]
        totalScores += 1
        if row[0] > 0:
            scoreSet.add(row[0])
    uniqueValues = len(scoreSet)
    avgSpai = totalSpai/totalScores
    del row, scoreAdder

    # Use an update cursor to ratio individual scores to average (SPAR)
    with arcpy.da.UpdateCursor(workingDemand, [step2Score, sparField]) as sparWriter:
        totalSpar = 0
        for row in sparWriter:
            row[1] = row[0]/avgSpai
            totalSpar += row[1]
            sparWriter.updateRow(row)
    del row, sparWriter

    arcpy.AddMessage("Saving output features...")
    # Copy working layer to user-defined Output
    arcpy.CopyFeatures_management(workingDemand, outputFC)

    # Begin generating report (try/except since report is optional):
    arcpy.AddMessage("Writing output report...")
    try:
        file = open(report, "w")
        file.write("V2SFCA Report\n\nINPUTS:\n\n")
        file.write("Network Dataset: %s\n\n"%inputND)
        file.write("Supply:\nPoints: %s\n"%inputSupply)
        file.write("Volume: %s\nField: %s\nValue: %s\n"%(supplyVolumeOpt, supplyVolumeField, supplyVolumeValue))
        file.write("Demand:\nPoints: %s\n"%inputDemand)
        file.write("Volume: %s\nField: %s\nValue: %s"%(demandVolumeOpt, demandVolumeField, demandVolumeValue))
        file.write("\n\nDistances and Weights:\n")
        file.write("Catchment threshold: %s\n"%distance)
        file.write("Coefficient or Target Weight: %s\n\n"%coeffOrWeight)
        file.write("Coefficient: %s\nTarget weight: %s\n"%(coefficient, targetWeight))
        file.write("SCORES:\n\nMean V2SFCA Score: %s\n"%avgSpai)
        file.write("Number of unique scores: %s\n"%uniqueValues)
        meanSpar = totalSpar/totalScores
        file.write("Mean Spatial Access Ratio (SPAR): %s "%meanSpar)
        file.write("(A mean SPAR of 1.0 indicates that the ratio was calculated correctly)\n\n")
        file.write("OUTPUT:\n\nOutput points: %s\n\nReport end."%outputFC)
        # CLose the file to save it
        file.close()
    except:
        pass

    # End the function
    return

# A standard python protocol to check before running the module's main funcion.
if __name__ == '__main__':
    v2sfca()