#-------------------------------------------------------------------------------
# Name:        Decay_curve_scripts
# Purpose:     The Project
# Author:      Sagert Sheets
# Created:     11/07/2017
#-------------------------------------------------------------------------------

import numpy
import matplotlib
import matplotlib.pyplot as plt

#Variables for plots
d = numpy.linspace(0, 30)
dx = numpy.linspace(0.1, 30)
g = numpy.exp(-(d**2)/272.0)
i = numpy.power(d, -.72)
e = numpy.exp(-d*(0.09))

plt.plot(d, g, "r", d, e, "b", dx, i, "g")
plt.ylim(0, 1.1)
plt.yticks(numpy.arange(0,1.1,0.1))
plt.show()