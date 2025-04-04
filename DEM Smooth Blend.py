import time
from pathlib import Path
from datetime import datetime
startTime = time.time()


"""
##########################################################
User options
"""

#Initial variable assignment
baseDEM         = 'C:/GIS Work/QGIS Scripts/DEM Smooth Blend/OrigDEM.tif'      #The extent of this DEM must fully contain the newDEM
newDEM          = 'C:/GIS Work/QGIS Scripts/DEM Smooth Blend/NewDEMV2.tif'     #Any extent of this DEM outside the base DEM will be clipped off
blendDistance   = 50
roundCorners    = True


#Options for compressing the images, ZSTD gives the best speed but LZW allows you to view the thumbnail in windows explorer
compressOptions     = 'COMPRESS=LZW|NUM_THREADS=ALL_CPUS|PREDICTOR=1|BIGTIFF=IF_SAFER|TILED=YES'



"""
##########################################################
Set up some variables
"""

#If round corners is on, then create the radius value of the round corners
roundDistance = 0
if roundCorners: roundDistance = blendDistance

#Set up the layer names for the raster calculations
baseDEMName = baseDEM.split("/")
baseDEMName = baseDEMName[-1]
baseDEMName = baseDEMName[:len(baseDEMName)-4]
newDEMName = newDEM.split("/")
newDEMName = newDEMName[-1]
newDEMName = newDEMName[:len(newDEMName)-4]

#Making a folder for processing
rootProcessDirectory = str(Path(origDEM).parent.absolute()).replace('\\','/') + '/'
processDirectory = rootProcessDirectory + origDEMName + 'BlendProcess' + '/'
if not os.path.exists(processDirectory):        os.mkdir(processDirectory)

#Get the pixel size and coordinate system of the raster
ras = QgsRasterLayer(origDEM)
pixelSizeX = ras.rasterUnitsPerPixelX()
pixelSizeY = ras.rasterUnitsPerPixelY()
rasExtent = ras.extent()
xminRas = rasExtent.xMinimum()
xmaxRas = rasExtent.xMaximum()
yminRas = rasExtent.yMinimum()
ymaxRas = rasExtent.yMaximum()
rasCrs = ras.crs().authid()
rasExtentParameter = str(xminRas) + ',' + str(xmaxRas) + ',' + str(yminRas) + ',' + str(ymaxRas) + ' [' + rasCrs + ']'

"""
##########################################################
Preparation of new DEM
"""

#Bring the new DEM out to the extent of the original
processing.run("gdal:warpreproject", {'INPUT':newDEM,'SOURCE_CRS':None,'TARGET_CRS':None,'RESAMPLING':0,'NODATA':None,'TARGET_RESOLUTION':None,'OPTIONS':compressOptions,'DATA_TYPE':0,
    'TARGET_EXTENT':rasExtentParameter,'TARGET_EXTENT_CRS':None,'MULTITHREADING':True,'EXTRA':'','OUTPUT':processDirectory + 'NewDEMFull.tif'})
    
#Remove nodata for a later raster calculation
processing.run("gdal:warpreproject", {'INPUT':processDirectory + 'NewDEMFull.tif','SOURCE_CRS':None,'TARGET_CRS':None,'RESAMPLING':0,'NODATA':None,'TARGET_RESOLUTION':None,'OPTIONS':'','DATA_TYPE':0,'TARGET_EXTENT':None,
    'TARGET_EXTENT_CRS':None,'MULTITHREADING':True,'EXTRA':'-srcnodata None','OUTPUT':processDirectory + 'NewDEMFullNoNull.tif'})

#Create a new raster where there is a value of -1 where the new DEM has data, and a value of 1 where the new DEM has no data
processing.run("gdal:rastercalculator", {'INPUT_A':processDirectory + 'NewDEMFull.tif','BAND_A':1,'INPUT_B':None,'BAND_B':None,'INPUT_C':None,'BAND_C':None,'INPUT_D':None,'BAND_D':None,'INPUT_E':None,'BAND_E':None,'INPUT_F':None,'BAND_F':None,
    'FORMULA':'-1','NO_DATA':1,'EXTENT_OPT':0,'PROJWIN':None,'RTYPE':1,'OPTIONS':compressOptions,'EXTRA':'','OUTPUT':processDirectory + 'NewDEMFullNegative.tif'})

"""
##########################################################
Corner rounding
"""

#Get the polygonal extent of the new DEM
processing.run("gdal:polygonize", {'INPUT':processDirectory + 'NewDEMFullNegative.tif','BAND':1,'FIELD':'DN','EIGHT_CONNECTEDNESS':False,'EXTRA':'','OUTPUT':processDirectory + 'NewDEMFullNegativePolygon.gpkg'})

#Buffer it out then in to round the corners
processing.run("native:buffer", {'INPUT':processDirectory + 'NewDEMFullNegativePolygon.gpkg','DISTANCE':-1 * roundDistance,'SEGMENTS':5,'END_CAP_STYLE':0,'JOIN_STYLE':0,'MITER_LIMIT':2,'DISSOLVE':False,'SEPARATE_DISJOINT':False,
    'OUTPUT':processDirectory + 'NewDEMFullNegativePolygonInBuff.gpkg'})
processing.run("native:buffer", {'INPUT':processDirectory + 'NewDEMFullNegativePolygonInBuff.gpkg','DISTANCE':roundDistance,'SEGMENTS':5,'END_CAP_STYLE':0,'JOIN_STYLE':0,'MITER_LIMIT':2,'DISSOLVE':False,'SEPARATE_DISJOINT':False,
    'OUTPUT':processDirectory + 'NewDEMFullNegativePolygonInBuffOutBuff.gpkg'})

#Clip the negative raster so that the blend corners will be smooth
processing.run("gdal:cliprasterbymasklayer", {'INPUT':processDirectory + 'NewDEMFullNegative.tif','MASK':processDirectory + 'NewDEMFullNegativePolygonInBuffOutBuff.gpkg','SOURCE_CRS':None,'TARGET_CRS':None,'TARGET_EXTENT':None,
    'NODATA':None,'ALPHA_BAND':False,'CROP_TO_CUTLINE':False,'KEEP_RESOLUTION':False,'SET_RESOLUTION':False,'X_RESOLUTION':None,'Y_RESOLUTION':None,'MULTITHREADING':True,'OPTIONS':compressOptions,'DATA_TYPE':0,'EXTRA':'',
    'OUTPUT':processDirectory + 'NewDEMFullNegativeClipped.tif'})

"""
##########################################################
Final blending of DEMs
"""

#Flip the negative raster so that the -1 values are nodata
processing.run("gdal:warpreproject", {'INPUT':processDirectory + 'NewDEMFullNegativeClipped.tif','SOURCE_CRS':None,'TARGET_CRS':None,'RESAMPLING':0,'NODATA':-1,'TARGET_RESOLUTION':None,'OPTIONS':'','DATA_TYPE':0,'TARGET_EXTENT':None,
    'TARGET_EXTENT_CRS':None,'MULTITHREADING':True,'EXTRA':'-srcnodata None','OUTPUT':processDirectory + 'NewDEMFullNegativeFlipped.tif'})

#Create a blend weighting raster starting from the edge of the new DEM inwards
processing.run("gdal:proximity", {'INPUT':processDirectory + 'NewDEMFullNegativeFlipped.tif','BAND':1,'VALUES':'1','UNITS':1,'MAX_DISTANCE':blendDistance,'REPLACE':None,'NODATA':blendDistance,
    'OPTIONS':compressOptions,'EXTRA':'','DATA_TYPE':1,'OUTPUT':processDirectory + 'NewDEMFullNegativeFlippedProx.tif'})

#Smooth off the edges of the blend using a cosine curve
processing.run("gdal:rastercalculator", {'INPUT_A':processDirectory + 'NewDEMFullNegativeFlippedProx.tif','BAND_A':1,
    'FORMULA':'(-0.5 *'+ str(blendDistance) + ' * numpy.cos(A * (numpy.pi / '+ str(blendDistance) + '))) + (0.5 * '+ str(blendDistance) + ')','NO_DATA':None,'EXTENT_OPT':0,'PROJWIN':None,'RTYPE':5,'OPTIONS':compressOptions,
    'EXTRA':'','OUTPUT':processDirectory + 'NewDEMFullNegativeFlippedProxSmooth.tif'})

#Bring the base and the new DEM together, using the blend weighting raster to determine values
processing.run("gdal:rastercalculator", {'INPUT_A':baseDEM,'BAND_A':1,'INPUT_B':processDirectory + 'NewDEMFullNoNull.tif','BAND_B':1,'INPUT_C':processDirectory + 'NewDEMFullNegativeFlippedProxSmooth.tif','BAND_C':1,'INPUT_D':None,'BAND_D':None,'INPUT_E':None,'BAND_E':None,'INPUT_F':None,'BAND_F':None,
    'FORMULA':'(B*(C/'+ str(blendDistance) + ')) + (A*(1-(C/'+ str(blendDistance) + ')))','NO_DATA':None,'EXTENT_OPT':0,'PROJWIN':None,'RTYPE':5,'OPTIONS':compressOptions,'EXTRA':'','OUTPUT':rootProcessDirectory + origDEMName + 'Blended.tif'})


"""
#######################################################################
"""

#All done
endTime = time.time()
totalTime = endTime - startTime
print("Done, this took " + str(int(totalTime)) + " seconds")
