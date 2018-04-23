'''-----------------------------------------------------------------------------
# Name:        E2SFCA_Version_1.0
# Purpose:     Implement the Enhanced Two-Step Floating Catchment Area method
# Author:      Sagert Sheets
# Created:     October 2017
# Note:        GitHub version. Provided for review purposes only.
#----------------------------------------------------------------------------'''


# Import necessary modules
import numpy
import arcpy
from arcpy import env

arcpy.CheckOutExtension("Network")

# Main function
def e2sfca():

    arcpy.AddMessage("Retrieving parameters...")
    arcpy.SetProgressor("default", "Retrieving parameters...")
    # Get parameters from ArcGIS interface
    #Network Dataset - REQUIRED
    inputND = arcpy.GetParameterAsText(0)
    #Supply(Resource) Points - REQUIRED
    inputSupply = arcpy.GetParameterAsText(1)
    #Volume of Supply (e.g. beds per hospital) - REQUIRED
        #Choice
    supplyVolumeOpt = arcpy.GetParameterAsText(2)
        #Field
    supplyVolumeField = arcpy.GetParameterAsText(3)
        #Class value
    supplyVolumeValue = float(arcpy.GetParameter(4))
    #Unique ID - REQUIRED
    inputSupplyID = arcpy.GetParameterAsText(5)
    #Multiplier (in case, e.g. low facility to high pop. ratio) - OPTIONAL
    supplyMultiplier = float(arcpy.GetParameter(6))
    #Demand (Population) Points - REQUIRED
    inputDemand = arcpy.GetParameterAsText(7)
    #Volume of Demand (e.g. population) - REQUIRED
        #Choice
    demandVolumeOpt = arcpy.GetParameterAsText(8)
        #Field
    demandVolumeField = arcpy.GetParameterAsText(9)
        #Class value
    demandVolumeValue = float(arcpy.GetParameter(10))
    #Unique ID - REQUIRED
    inputDemandID = arcpy.GetParameterAsText(11)
    #Distance of regions - REQUIRED
    distList = arcpy.GetParameter(12)                       # Returns a list
    #How distance is used in Decay Function
    distanceMethod = arcpy.GetParameterAsText(13)
    #Use coefficient or calculate based on weight
        #Choice
    coeffOrWeight = arcpy.GetParameterAsText(14)
        #Coefficient value
    coefficient = float(arcpy.GetParameter(15))
        #Target weight value
    targetWeight = float(arcpy.GetParameter(16))
    #Output features - REQUIRED
    outputFC = arcpy.GetParameterAsText(17)
    #Output report
    report = arcpy.GetParameterAsText(18)

    # Begin generating report:
    file = open(report, "w")
    file.write("E2SFCA Report\n\nINPUTS:\n\n")
    file.write("Network Dataset: %s\n\n"%inputND)
    file.write("Supply:\nPoints: %s\nUnique IDs: %s\n"%(inputSupply,inputSupplyID))
    file.write("Volume: %s\nField: %s\nValue: %s\n"%(supplyVolumeOpt, supplyVolumeField, supplyVolumeValue))
    file.write("Volume multiplier: %s (This value is reflected in Step 2 scores)\n\n"%supplyMultiplier)
    file.write("Demand:\n")
    file.write("Points: %s\nUnique IDs: %s\n"%(inputDemand, inputDemandID))
    file.write("Volume: %s\nField: %s\nValue: %s"%(demandVolumeOpt, demandVolumeField, demandVolumeValue))
    # Report closes in case script terminates due to error:
    file.close()

# Derive values & calculate weights
    arcpy.AddMessage("Calculating weights...")
    arcpy.SetProgressor("default", "Calculating weights...")
    #Remove duplicate values from distance list
    distSet = set(distList)
    #Ensure they run from low to high
    distance = sorted(distSet)
    #Get outermost distance
    distLimit = distance[2]

    #Check Distance method & determine region values for weighting
    if distanceMethod == "OUTSIDE":
        catch3 = float(distance[2])
        catch2 = float(distance[1])
        catch1 = float(distance[0])
    elif distanceMethod == "INSIDE":
        catch3 = float(distance[1])
        catch2 = float(distance[0])
        catch1 = 0.0
    else:
        catch3 = ((float(distance[1]) + float(distance[2])) / 2)
        catch2 = ((float(distance[0]) + float(distance[1])) / 2)
        catch1 = (float(distance[0]) / 2)
    catch = [catch1, catch2, catch3]

    #Check weighting method & calculate all 3 weights
    if coeffOrWeight == "Use coefficient":
        weight1 = gaussianWeights(catch1, coefficient)
        weight2 = gaussianWeights(catch2, coefficient)
        weight3 = gaussianWeights(catch3, coefficient)
    elif coeffOrWeight == "Use target weight":
        coefficient = gaussianSolve(catch3, targetWeight)
        weight1 = gaussianWeights(catch1, coefficient)
        weight2 = gaussianWeights(catch2, coefficient)
        weight3 = targetWeight
    weights = [weight1, weight2, weight3]

    # Update (append) report:
    file = open(report, "a")
    file.write("\n\nDistances and Weights:\n")
    file.write("Zone limits: %s (The third value is considered the catchment)\n"%distance)
    file.write("Distance method: %s\n"%distanceMethod)
    file.write("Coefficient or Target Weight: %s\n\n"%coeffOrWeight)
    file.write("COEFFICIENT AND WEIGHTS:\n\n")
    file.write("Coefficient: %s\nTarget weight: %s\n"%(coefficient, targetWeight))
    file.write("First zone weighting distance and weight: %s, %s\n"%(catch1, weight1))
    file.write("Second zone weighting distance and weight: %s, %s\n"%(catch2, weight2))
    file.write("Third zone weighting distance and weight: %s, %s\n\n"%(catch3, weight3))
    file.close()

# Make working feature layers based on supply & demand inputs
    arcpy.AddMessage("Preparing input features...")
    arcpy.SetProgressor("default", "Preparing input features...")

    # Variables for new layers
    workingSupplyName = "WorkingSupplyLayer"
    workingDemandName = "WorkingDemandLayer"
    workingSupply = arcpy.MakeFeatureLayer_management(inputSupply, workingSupplyName)
    workingDemand = arcpy.MakeFeatureLayer_management(inputDemand, workingDemandName)

    # Check if Volume fields exist or if Volume values should be applied...
    if supplyVolumeOpt == "Constant volume value":
        supplyVolumeField = "Supply_Vol"
        arcpy.AddField_management(workingSupply, supplyVolumeField, "DOUBLE")
        writeVolume = arcpy.da.UpdateCursor(workingSupply, supplyVolumeField)
        for row in writeVolume:
            row[0] = supplyVolumeValue
            writeVolume.updateRow(row)
        del writeVolume, row
    elif supplyVolumeOpt == "Volume from field":
        pass
    if demandVolumeOpt == "Constant volume value":
        demandVolumeField = "Demand_Vol"
        arcpy.AddField_management(workingDemand, demandVolumeField, "DOUBLE")
        writeVolume = arcpy.da.UpdateCursor(workingDemand, demandVolumeField)
        for row in writeVolume:
            row[0] = demandVolumeValue
            writeVolume.updateRow(row)
        del writeVolume, row
    elif demandVolumeOpt == "Volume from field":
        pass

# Prepare extra fields for weights & calculations
    weightField = "Weight"
    weightedSupply = "WghtSupply"
    weightedDemand = "WghtDemand"
    step1Score = "Step1_Score"
    step2Score = "Step2_Score"
    sparField = "SPAR"
    doubleType = "DOUBLE"

    #Supply
    arcpy.AddField_management(workingSupply, weightField, doubleType)
    arcpy.AddField_management(workingSupply, weightedSupply, doubleType)
    arcpy.AddField_management(workingSupply, step1Score, doubleType)

    #Demand
    arcpy.AddField_management(workingDemand, weightedDemand, doubleType)
    arcpy.AddField_management(workingDemand, step2Score, doubleType)
    arcpy.AddField_management(workingDemand, sparField, doubleType)

# Creation of an Origin-Destination matrix layer & preparation of variables
# and inputs.
    arcpy.AddMessage("Preparing Origin-Destination Matrix...")
    arcpy.SetProgressor("default", "Preparing Origin-Destination Matrix...")
    # Impedance and accumulation are in minutes
    minutes = "Minutes"
    accumMinutes = "Total_Minutes"

    # Create OD Matrix Layer
    odNALayer = arcpy.na.MakeODCostMatrixLayer(inputND, "odMatrix_1", minutes,
                                                distLimit, "", [minutes])
    # Get layer object
    odLayer = odNALayer.getOutput(0)

    # Identify sub-layers
    sublayers = arcpy.na.GetNAClassNames(odLayer)

    # Variables for easy use of Origins & Desintations & Lines layers
    originsLayer = sublayers["Origins"]
    destinationsLayer = sublayers["Destinations"]
    linesLayer = sublayers["ODLines"]

    # Add fields for joining data & calculations
    supplyID = "Supply_ID"
    demandID = "Demand_ID"
    textField = "TEXT"

    arcpy.AddMessage("Adding Locations...")
    arcpy.SetProgressor("default", "Adding Locations...")
    # Get location fields
    candidateFieldsS = arcpy.ListFields(inputSupply)
    candidateFieldsD = arcpy.ListFields(inputDemand)
    # Origins
    arcpy.na.AddFieldToAnalysisLayer(odLayer, originsLayer, "Supply_ID", "TEXT", "", "", 200)
    oFieldmap = arcpy.na.NAClassFieldMappings(odLayer, originsLayer, True, candidateFieldsS)
    oFieldmap["Supply_ID"].mappedFieldName = inputSupplyID

    # Add Locations for Origins
    arcpy.na.AddLocations(odLayer, originsLayer, workingSupply, oFieldmap, "")

    # Destinations
    arcpy.na.AddFieldToAnalysisLayer(odLayer, destinationsLayer, "Demand_ID", "TEXT", "", "", 200)
    dFieldmap = arcpy.na.NAClassFieldMappings(odLayer, destinationsLayer, True, candidateFieldsD)
    dFieldmap["Demand_ID"].mappedFieldName = inputDemandID

    # Add locations for Destinations
    arcpy.na.AddLocations(odLayer, destinationsLayer, workingDemand, dFieldmap, "")

    arcpy.AddMessage("Solving Origin-Destination Matrix...")
    arcpy.SetProgressor("default", "Solving Origin-Destination Matrix...")
    # Solve
    arcpy.na.Solve(odLayer)

    arcpy.AddMessage("Joining layers...")
    arcpy.SetProgressor("default", "Joining layers...")
    # Dictionary for accessing to solved sublayers
    subLayers = dict((lyr.datasetName, lyr) for lyr in arcpy.mapping.ListLayers(odLayer)[1:])
    originsSubLayer = subLayers["Origins"]
    destinationsSubLayer = subLayers["Destinations"]
    linesSubLayer = subLayers["ODLines"]

    # Fields to join to lines (travel time outcomes)
    supplyFieldsJoin = [inputSupplyID, weightField, supplyVolumeField, weightedSupply]
    demandFieldsJoin = [inputDemandID, demandVolumeField, weightedDemand]

    # Join ID fields to the lines layer to allow joins from inputs
    arcpy.JoinField_management(linesSubLayer, "OriginID", originsSubLayer, "ObjectID", "Supply_ID")
    arcpy.JoinField_management(linesSubLayer, "DestinationID", destinationsSubLayer, "ObjectID", "Demand_ID")

    # Use unique IDs to join fields for calculations based on travel times
    arcpy.JoinField_management(linesSubLayer, "Supply_ID", workingSupply, inputSupplyID, supplyFieldsJoin)
    arcpy.JoinField_management(linesSubLayer, "Demand_ID", workingDemand, inputDemandID, demandFieldsJoin)

    arcpy.AddMessage("First Step: Applying weights...")
    arcpy.SetProgressor("default", "First Step: Applying weights...")
    # Using an update cursor to check & assign weights
    weightWriter = arcpy.da.UpdateCursor(linesSubLayer, ["Total_Minutes", "Weight"])
    for row in weightWriter:
        if (0 < row[0] <= distance[0]) == True:
            row[1] = weight1
        elif (distance[0] < row[0] <= distance[1]) == True:
            row[1] = weight2
        elif (distance[1] < row[0] <= distance[2]) == True:
            row[1] = weight3
        else:
            row[1] = 0
        weightWriter.updateRow(row)
    del row, weightWriter

    # Using an update cursor to weight demand
    demandWeighter = arcpy.da.UpdateCursor(linesSubLayer, [demandVolumeField,
                                                            weightField,
                                                            weightedDemand])
    for row in demandWeighter:
        row[2] = row[0] * row[1]
        demandWeighter.updateRow(row)
    del row, demandWeighter

    arcpy.AddMessage("First Step: Calculating scores...")
    arcpy.SetProgressor("default", "First Step: Calculating scores...")
    # Using cursors to assigne a scor for Step 1
    with arcpy.da.UpdateCursor(workingSupply, [inputSupplyID, supplyVolumeField, step1Score]) as scoreWriter:
        for item in scoreWriter:
            uniqueID = item[0]
            with arcpy.da.SearchCursor(linesSubLayer, [supplyID, weightedDemand]) as popReader:
                score = 0
                for demand in popReader:
                    if item[0] == demand[0]:
                        score += demand[1]
                        continue
                    else:
                        continue
                item[2] = supplyMultiplier * (item[1]/score)
                scoreWriter.updateRow(item)
    del demand, popReader, item, scoreWriter, uniqueID

    # Step 1 scores need to be joined to the lines table for more calculations
    arcpy.JoinField_management(linesSubLayer, supplyID, workingSupply, inputSupplyID, step1Score)

    arcpy.AddMessage("Second Step: Applying weights... ")
    arcpy.SetProgressor("default", "Second Step: Applying weights...")
    # Using an update cursor to weight Step 1 score
    supplyWeighter = arcpy.da.UpdateCursor(linesSubLayer, [weightField, step1Score, weightedSupply])
    for line in supplyWeighter:
        line[2] = line[0] * line[1]
        supplyWeighter.updateRow(line)
    del line, supplyWeighter

    arcpy.AddMessage("Second Step: Calculating scores... ")
    arcpy.SetProgressor("default", "Second Step: Calculating scores...")
    # Using cursors to assign a score for Step 2
    with arcpy.da.UpdateCursor(workingDemand, [inputDemandID, step2Score]) as scoreUpdater:
        for place in scoreUpdater:
            uniqueID = place[0]
            with arcpy.da.SearchCursor(linesSubLayer, [demandID, weightedSupply]) as scoreChecker:
                score = 0
                for supply in scoreChecker:
                    if place[0] == supply[0]:
                        score += supply[1]
                        continue
                    else:
                        continue
                place[1] = score
                scoreUpdater.updateRow(place)
    del supply, scoreChecker, place, scoreUpdater, uniqueID

    arcpy.AddMessage("Calculating SPAR...")
    arcpy.SetProgressor("default", "Calculating SPAR...")

    # Replace NULL values with 0 scores
    nullFinder = arcpy.da.UpdateCursor(workingDemand, [step2Score])
    for value in nullFinder:
        if value[0] == [None]:
            value[1] = 0
            nullFinder.updateRow(value)
        else:
            break
    del value, nullFinder

    # Find the average SPAI (e2sfca score)
    totalSpai = 0
    totalScores = 0
    scoreAdder = arcpy.da.SearchCursor(workingDemand, [step2Score])
    for row in scoreAdder:
        totalSpai += row[0]
        totalScores += 1
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
    arcpy.SetProgressor("default", "Saving output features...")
    # Copy working layer to user-defined Output
    arcpy.CopyFeatures_management(workingDemand, outputFC)

    file = open(report, "a")
    file.write("SCORES:\n\nMean E2SFCA Score: %s\n"%avgSpai)
    deflatedAvgSpai = avgSpai/supplyMultiplier
    file.write("Mean E2SFCA Score without multiplier: %s\n"%deflatedAvgSpai)
    meanSpar = totalSpar/totalScores
    file.write("Mean Spatial Access Ratio (SPAR): %s "%meanSpar)
    file.write("(A mean SPAR of 1.0 indicates that the ratio was calculated correcctly)\n\n")
    file.write("OUTPUT:\n\nOutput points: %s\n\nReport end."%outputFC)
    # CLose the file to save it
    file.close()

    # Check in the Network Analyst extension
    arcpy.CheckInExtension("Network")

    arcpy.ResetProgressor()

    # End the function
    return

# A function for calculating weights
def gaussianWeights(catch,coefficient):
    '''Weights may be an approximation'''
    weight = numpy.exp(-numpy.power(catch, 2.0)/coefficient)
    return weight

# A function for finding the coefficient, if necessary.
def gaussianSolve(catch,targetWeight):
    '''Coefficient may be an approximation'''
    coefficient = -numpy.power(catch, 2.0)/numpy.log(targetWeight)
    return coefficient

# A standard python protocol to check before running the module's main funcion.
if __name__ == '__main__':
    e2sfca()