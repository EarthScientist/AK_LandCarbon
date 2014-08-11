# Processing Steps for the generation of the new landcover map for southeast alaska using logic devised by the partners at the USGS 
#  in Juneau, namely Dave D'Amour & Frances Biles.
# ---------------------------------------------------------------------------------------------------------------------------------

# What I need to perform the below analysis:
# - Map Layers:
# there are some issues with the geoserver at the USGS in Juneau so waiting for that to be solved before
#	I will get the needed data sets

# ---------------------------------------------------------------------------------------------------------------------------------

import os, sys, re, glob, PIL, Image, ImageDraw
from osgeo import gdal as gdal
from osgeo import gdal_array as gdal_array
from osgeo.gdalconst import *
from osgeo import gdalnumeric as gdalnumeric
from osgeo import ogr as ogr
from osgeo import osr as osr
import pandas as pd
import numpy as np

# 1)	Clip extent of NLCD and NLCDCanopy to southeast Alaska (SEAK). Specify the original rasters as the snap raster so resampling of cell values does not occur.
# --> [gdal-python] this is easy to do with the gdal python api clip it with an OGR object
#      main hurdles will be to get the actual data set and get them into the needed processing formats
# see this: http://pcjericks.github.io/py-gdalogr-cookbook/raster_layers.html?highlight=clip#clip-a-geotiff-with-shapefile

# raster_path = '/Data/Base_Data/GIS/GIS_Data/Raster/Land_Cover/Canada_EOSD_Land_Cover/AK_NLCD_2001_land_cover_3-13-08/clipped/ak_nlcd_2001_land_cover_3130_SEAK.tif'

# shapefile_path = '/workspace/UA/malindgren/projects/LandCarbon_2014/EcoRegions/NorthPacificMaritime_Dissolved.shp'


# cp  /Volumes/malindgren/projects/LandCarbon_2014/Frances_Data_012814/AKAlbers/NLCD_canopy_AKNPLCC.tif ./
# cp /Volumes/malindgren/projects/LandCarbon_2014/NorthPacificMaritime_Extent_ALF_Veg/NorthPacificMaritime_Extent_MASTER.shp ./


shapefile_path = '/workspace/UA/malindgren/projects/LandCarbon_2014/NorthPacificMaritime_Extent_ALF_Veg/NorthPacificMaritime_Extent_MASTER_multi.shp'
raster_path = '/workspace/UA/malindgren/projects/LandCarbon_2014/Frances_Data_012814/AKAlbers/NLCD_land_cover_AKNPLCC.tif'

def maskRasterShape(shapefile_path, raster_path, output_filename):
	"""
	a very simple function to convert a shapefile to a 
	GeoTiff (LZW Compressed) with the same 
	extent/res/origin/refsystem as the input raster.

	Be sure that your inputs are actually in the same
	reference system.  It is too much code to deal with 
	it here in a smart way.

	depends osgeo.gdal, osgeo.ogr, osgeo.osr, numpy

	"""
	shp = ogr.Open(shapefile_path)
	lyr = shp.GetLayer(0)
	osrs = lyr.GetSpatialRef()
	rst = gdal.Open(raster_path, gdal.GA_ReadOnly)

	drv = gdal.GetDriverByName('MEM')
	
	mask_rst = drv.Create('mem', 
		rst.RasterXSize, 
		rst.RasterYSize,
		bands = 1, 
		eType = rst.GetRasterBand(1).DataType)

	mask_rst.SetGeoTransform(rst.GetGeoTransform())
	mask_rst.SetProjection(osrs.ExportToWkt())

	gdal.RasterizeLayer(
		mask_rst, 
		[1], 
		lyr, 
		burn_values=[1], 
		options=["COMPRESS=LZW"])
	
	rst_arr = rst.ReadAsArray()
	mask_arr = mask_rst.ReadAsArray()
	
	# mask the array
	rst_arr[mask_arr==0] = 0

	# write the array to a new raster file
	drv = gdal.GetDriverByName('GTiff')

	out_rst = drv.Create(
		output_filename, 
		rst.RasterXSize, 
		rst.RasterYSize,
		bands = 1, 
		eType = rst.GetRasterBand(1).DataType, 
		options = ["COMPRESS=LZW"])

	out_rst.GetRasterBand(1).WriteArray(rst_arr)
	
	mask_rst = None

	return out_rst



new_raster = maskRasterShape(shapefile_path, raster_path, '/workspace/UA/malindgren/projects/LandCarbon_2014/working/test_masked_gdal.tif')


reclass_table = np.matrix([[1, 2, 999], [2,9,888]])

# CLASSIFY A RASTER
# RECLASSIFICATION OF RASTER VALUES -- NOT YET WORKING
 
def reclass(raster_path, reclass_table):
	"""
	reclassify the values in a raster.  

	Currently can take as input a raster path and 
	returns a new raster with the values of the 
	raster classified.

	takes as input a numpy matrix with 3 cols and
	a row for each unique classification needed.
	example:
	np.matrix([[1,5,1],[6,10,2],[11,15,3]])

	format:
	> currrently inclusive of the values set <
	[[value_range_begin, value_range_end, new_value]]

	"""

rst = gdal.Open(raster_path, gdal.GA_ReadOnly)
band = rst.GetRasterBand(1)  

#Reading the raster properties  
projectionfrom = rst.GetProjection()  
geotransform = rst.GetGeoTransform()  
xsize = band.XSize  
ysize = band.YSize  
datatype = band.DataType

# get the raster values
# values = band.ReadRaster( 0, 0, xsize, ysize, xsize, ysize, datatype )
values = band.ReadAsArray()

#Now that the raster is into an array, let's classify it
out_str = ''
for value in values:
    index = 0
    for cl_value in classification_values:
        if value <= cl_value:
            out_str = out_str + struct.pack('B',classification_output_values[index])
            break
        index = index + 1


for value in values:
	for row in rcl:
		row = row.tolist()[0]




#Once classified, write the output raster
drv = gdal.GetDriverByName('GTiff') 
output_rst = drv.Create(output_file, xsize, ysize, 4)
output_rst.SetProjection(projectionfrom)
output_rst.SetGeoTransform(geotransform)

	return output_rst.GetRasterBand(1).WriteRaster( 0, 0, xsize, ysize, out_str )
	



########################################################################

mask = gdalnumeric.LoadFile('/workspace/UA/malindgren/projects/LandCarbon_2014/working/test_rasterized_gdal.tif')

clip = gdalnumeric.choose(mask, (clip, 0)).astype(gdalnumeric.uint8)


mask = gdal.Open('/workspace/UA/malindgren/projects/LandCarbon_2014/working/test_rasterized_gdal.tif' )
rst = gdal.Open(raster_path)

mask_band = mask.GetRasterBand(1)
rst_band = rst.GetRasterBand(1)

rst_arr = rst_band.ReadAsArray(xoff=0, yoff=0, win_xsize=rst.RasterXSize, win_ysize=rst.RasterYSize )
mask_arr = mask_band.ReadAsArray(xoff=0, yoff=0, win_xsize=mask.RasterXSize, win_ysize=mask.RasterYSize )


rst_arr = rst_band.ReadAsArray(xoff=0, yoff=0, win_xsize=rst.RasterXSize, win_ysize=rst.RasterYSize )
mask_arr = mask_band.ReadAsArray(xoff=0, yoff=0, win_xsize=mask.RasterXSize, win_ysize=mask.RasterYSize )

# first we need to loop through the data that is part of the multipolygon layers


# try to remove the data from that raster in a new loop

# attempt to clip it by the full bbox extent of the raster













nlcd = gdal.Open(raster_path)
shp = ogr.Open(shapefile_path)

nlcd_canopy = gdal.Open('') # get from frances

# this is only the coastal rainforest and coast mountain transitionfrom level 2 nowacki
# this should be directly brought back from the data that I created for the rest of the state.
# what we have called NorthPacMaritime in the old verstion of ALF_Veg.tif

seak = ogr.Open(shapefile_path) 


# 2)	Re-project all GIS data sets to Alaska Albers, NAD83(1986).
# a.	The NLCD grids are in WGS84. In ArcMap, use the WGS_1984_To_NAD_1983_5 transformation method. Make sure resampling is set to Nearest Neighbor. Cell size = 30m.
# --> [gdal-python] obviously this is quite simple using the gdal.ReprojectImage() method in the gdal python bindings

# **In all subsequent raster processing, be sure to specify these re-projected grids as the snap raster so the grid cells remain in alignment and do not go through additional resampling. 

# 3)	Reclassify NLCDCanopy raster values:
# --> [gdal-python] simply get the raster as an array and use some simple lookup functions to reclass the values in the raster map

# 4)	Reclassify NLCD raster:
# --> [gdal-python] simply get the raster as an array and use some simple lookup functions to reclass the values in the raster map

# 5)	Combine the 2 reclassed rasters (ArcMap “combine”). The operation creates a new raster with an attribute table containing a value for each unique combination of reclassed NLCD land cover type and percent canopy cover:
# --> [pure-python] combine these rsts by creating a numpy ndimensional array OR possibly make a new raster with the 2 inputs as bands and do math on that

# 6)	Reclass the combined raster from step 5:
# --> [pain point] write a set of functions that are able to do this sort of combination of maps in gdal python numpy

# 7)	Using MHWShore, change all cell values in the raster output from Step 6 that fall below mhw to 1 (no veg).  
# 	a.	Delete all the land polygons from the shore layer so that only the saltwater polygon remains
# --> [gdal-python / Shapely(GEOS)-python] should be easy enough using the OGR library or the GEOS library

#	b.	Create a new field in the saltwater polygon attribute table, e.g., covcls.  
# --> [gdal-python / Shapely(GEOS)-python] should be easy enough using the OGR library or the GEOS library

#	i.	Code covcls = 1 for the saltwater polygon.
# --> [gdal-python / Shapely(GEOS)-python] should be easy enough using the OGR library or the GEOS library

#	c.	Convert the MHWShore polygon feature class to a raster. Choose the “covcls” field to assign values to the output raster. 
#		Set the cell size to 30m. Specify the reclassed raster from step 6 (or any of the re-projected NLCD rasters) as the snap and extent raster. 
#		Use Nearest Neighbor for resample method. All areas outside the saltwater polygon will be assigned a NoData value. 
# --> [gdal-python] rasterize the shapefile to a raster at the resolution of the above data

#	d.	Use the Raster Calculator to create an expression to create a new raster where all the cells coincident with saltwater will have a 
#		value=1 (i.e., no veg).
# --> [gdal-python] take the new raster and use the gdal calculator to do this needed and simple map math
	
	# an example of the way we are not going to do it: Con(IsNull(NameOfSaltwaterRaster), NameOfRasterFromStep6, 1)
	# That is, where the saltwater raster is equal to NoData, use the grid cell value from the raster output from Step6. Otherwise assign a grid 
	# 	cell value of 1. Don’t forget to specify the snap & extent raster

# 8)	Using TNFCoverType, identify areas of alder, alpine, high elevation forest, brush, slide zones, and rock in the raster from Step 7.  
# 	Change these cell values to No Veg (1) or Other Veg (5).
# 	a.	Create a new field in the TNFCoverType called “covcls.”  
# --> [ogr-Fiona-python / Shapely(GEOS)-python] This is possible using the OGR or the GEOS bindings.  Learn how to do it and write a function to do it.

# 		i.	Code covcls = 1 (i.e., no veg) where NFCON = R.  Translation: “non-forested condition = rock.”
# --> [pure-python] this should be as easy as changing the values in a table based on conditionals

# 		ii.	Code covcls = 5 (i.e., other veg) where FPROD = A, H, or S, and where NFCON = A, B, H, or S.  That is, where Forest Productivity 
# --> [pure-python] this should be as easy as changing the values in a table based on conditionals
# 		is low due to alder, high elevation forest, or recurrent slide zones; and where non-forested condition is alder brush, brush, alpine, 
# 		or recurrent slide zone.
	
# 	b.	Convert the TNFCoverType polygon feature class to a raster.  Choose the “covcls” field to assign values to the output raster. Set the 
# 		cell size to 30m. Specify the raster output from step 7 (or any of the re-projected NLCD rasters) as the snap and extent raster. Use 
# 		Nearest Neighbor for resample method. All polygons without a covcls value will be assigned a NoData value.
# --> [gdal-python] rasterize the shapefile to a raster at the resolution of the above data

# 	c.	Use the Raster Calculator to create an expression to output a new raster where all the cells coincident with a coded value in the 
# 		TNFCoverType raster will have a value=1 or 5.
# --> [gdal-python] use the gdal calculator to do this

	# 	what we are not going to do: Con(IsNull(NameOfTNFCoverTypeRaster), NameOfRasterFromStep7, NameOfTNFCoverTypeRaster)
	# 	That is, where the TNFCoverType raster is equal to NoData, use the grid cell value from the raster output from Step7. 
	#	Otherwise use the grid cell value from the TNFCoverType raster. Don’t forget to specify the snap & extent raster.

# 9)	Convert the raster output from Step 8 to have a pixel bit depth of 16-bit unsigned integer (or something similar that can contain a 4-digit integer value). 
# 	In ArcMap, use the CopyRaster tool. Set the snap raster. Can assign 65535 as NoData value.
# --> [gdal-python] this is an uneeded step due to us having complete control over the data when it is not in ArcGIS.

# 10)	Using TNFHarvest, identify harvested areas on the raster output from Step 9. Code these grid cells with the 4-digit year in which the harvest occurred.

#	a.	Delete all polygons with a DATE_ORIGIN = 0.
# --> [gdal-python / Shapely(GEOS)-python / Fiona-python]

#	b.	Create a new field in TNF harvest called “year.”  
#		i.	Populate the year field with the first 4 digits from the existing DATE_ORIGIN field. In ArcMap, can enter a python expression 
#			in the field calculator for “Pre-logic Script Code”:
# 			def toNum(inValue):
# 						   try:
# 								outValue = str(inValue)
# 						outYr = int(outValue[0:3])
# 						return outYr
# 						  except:
# 						return -99
# --> [pure-python] this seems as simple as changing the values in a table based on some conditonals 
#	Then for “year =”  toNum(!DATE_ORIGIN!)

#	c.	Convert the TNFHarvest polygon feature class to a raster.  Choose the “year” field to assign values to the output raster. 
#		Set the cell size to 30m. Specify the raster output from step 9 (or any of the re-projected NLCD rasters) as the snap and extent 
#		raster. Use Nearest Neighbor for resample method. All polygons without a year value will be assigned a NoData value.
# --> [gdal-python] rasterize the shapefile to the resolution of the above rasters using gdal.ReprojectImage()

#	d.	Use the Raster Calculator to create an expression to output a new raster where all the cells coincident with a coded value in the
#		TNFHarvest raster will have a value equal to the harvest year.
# --> [gdal-python] use the calulator to do this

	#	what we are not going to do: Con(IsNull(NameOfTNFHarvestRaster), NameOfRasterFromStep9, NameOfTNFHarvestRaster)
	#	That is, where the TNFHarvest raster is equal to NoData, use the grid cell value from the raster output from Step9. 
	#	Otherwise use the grid cell value from the TNFHarvest raster. Don’t forget to specify the snap & extent raster.


# # complete the data set write # # 


