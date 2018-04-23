import arcpy
class ToolValidator(object):
  """Class for validating a tool's parameter values and controlling
  the behavior of the tool's dialog."""

  def __init__(self):
    """Setup arcpy and the list of tool parameters."""
    self.params = arcpy.GetParameterInfo()

  def initializeParameters(self):
    """Refine the properties of a tool's parameters.  This method is
    called when the tool is opened."""
    return

  def updateParameters(self):
    """Modify the values and properties of parameters before internal
    validation is performed.  This method is called whenever a parameter
    has been changed."""
    suppVol = self.params[2].value.upper().replace(" ", "_")
    if suppVol == "VOLUME_FROM_FIELD":
        self.params[3].enabled = True
        self.params[4].enabled = False
    elif suppVol == "CONSTANT_VOLUME_VALUE":
        self.params[3].enabled = False
        self.params[4].enabled = True
    else:
        self.params[3].enabled = False
        self.params[4].enabled = False

    demVol = self.params[6].value.upper().replace(" ", "_")
    if demVol == "VOLUME_FROM_FIELD":
        self.params[7].enabled = True
        self.params[8].enabled = False
    elif demVol == "CONSTANT_VOLUME_VALUE":
        self.params[7].enabled = False
        self.params[8].enabled = True
    else:
        self.params[7].enabled = False
        self.params[8].enabled = False


    coeffWeight = self.params[10].value
    if coeffWeight:
        coeffWeight = coeffWeight.upper().replace(" ", "_")
    if coeffWeight == "USE_COEFFICIENT":
        self.params[11].enabled = True
        self.params[12].enabled = False
    elif coeffWeight == "USE_TARGET_WEIGHT":
        self.params[11].enabled = False
        self.params[12].enabled = True
    else:
        self.params[11].enabled = False
        self.params[12].enabled = False
    return

  def updateMessages(self):
    """Modify the messages created by internal validation for each tool
    parameter.  This method is called after internal validation."""
    return
