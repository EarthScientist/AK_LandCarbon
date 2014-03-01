#!/usr/bin/env python
#*****************************************************************************
# Generate the LandCarbon 2014 Veg Map Product using Logic derived from 
# Frances Biles and David D'Amour at the USFS in Juneau, AK.
#
# Developed by: Michael Lindgren (malindgren@alaska.edu), Spatial Analyst,
#    Scenarios Network for Alaska & Arctic Planning, Fairbanks, AK.
#  
# developed using open source tools in hopes of learning something about how to 
# use these tools and develop something that may be useful to the community at 
# large without the large monetary overhead dealing with software licensing
#
# version 0.1 alpha --
#
#*****************************************************************************

import os, sys, re, glob, PIL, Image, ImageDraw
from osgeo import gdal as gdal
from osgeo import gdal_array as gdal_array
from osgeo.gdalconst import *
from osgeo import gdalnumeric as gdalnumeric
from osgeo import ogr as ogr
from osgeo import osr as osr
import pandas as pd
import numpy as np


def preprocess(master_raster, input_spatial_file, output_dataset, burn_value=None, filter_query=None, \
	creation_options=["COMPRESS=LZW"], rasterize_options=None):
	"""

	This function will take an input spatial file and return a standardized representation
	of it using the information contained in the master_raster.

	It is really built to work with GTiff I/O, but *may* work with others with some tweaking
	
	This function may be significantly modified using the gdal_calculations library in the very 
	near future.  

	example: ** more metadata to come **
	filter_query = "SUB_REGION = 'Pacific'"

	"""
	# create some output data based on the master
	master_raster.GetDriver()
	xsize = master_raster.RasterXSize
	ysize = master_raster.RasterYSize
	bands = master_raster.RasterCount

	if isinstance(output_dataset, gdal.Dataset):
		# if this file already exists we want to use it to 
		#   again in the case of multiple burn queries
		dst_ds = output_dataset
	else:
		# create new empty raster
		driver = master_raster.GetDriver()
		dst_ds = driver.Create(output_dataset, xsize, ysize, bands, gdal.GDT_Float32, options=creation_options)
		dst_ds.SetProjection(master_raster.GetProjection())
		dst_ds.SetGeoTransform(master_raster.GetGeoTransform())

	if isinstance(input_spatial_file, gdal.Dataset):
		# do raster stuff
		print('ERROR: Raster Processing not yet complete...  Sorry.')
	elif isinstance(input_spatial_file, ogr.DataSource):
		lyr = input_spatial_file.GetLayer()
		if filter_query:
			# set a filter with SQL statement above
			lyr.SetAttributeFilter(filter_query)
		try:
			if rasterize_options:
				# rasterize	
				gdal.RasterizeLayer(dst_ds, [1], lyr, options = rasterize_options)
			else:
				gdal.RasterizeLayer(dst_ds, [1], lyr, burn_values=[burn_value], options=creation_options)
		except:
			sys.exit('ERROR: RasterizeLayer has failed...')
	else:
		print('ERROR: Check Input File Types')

	dst_ds.GetRasterBand(1).ComputeStatistics(0)
	dst_ds.FlushCache()
	return dst_ds


def world2Pixel(geoMatrix, x, y):
	"""
	Uses a gdal geomatrix (gdal.GetGeoTransform()) to calculate
	the pixel location of a geospatial coordinate
	"""
	ulX = geoMatrix[0]
	ulY = geoMatrix[3]
	xDist = geoMatrix[1]
	yDist = geoMatrix[5]
	rtnX = geoMatrix[2]
	rtnY = geoMatrix[4]
	pixel = int((x - ulX) / xDist)
	line = int((ulY - y) / xDist)
	return (pixel, line)


def reclassify_raster(gdal_raster, reclass_table, output_filename, output_format='GTiff', gdal_data_type=gdal.GDT_Float32, x_block_size=None, y_block_size=None):
	"""
	reclassify the values in a raster. 

	inputs:
	gdal_raster = a raster object opened using GDAL bindings
	reclass_table = list of lists of reclas range values and the output value
		format : [[ min_range_value, end_range_value, new_value], [ ..., ..., ... ]]

	output_filename = path to the output reclassed raster file
	output_format = a GDAL recognized keyword string representing a data output_format
	gdal_data_type = the output GDAL data type format for the reclassed raster 


	depends:
	gdal, numpy, gdal_array

	"""
	band = gdal_raster.GetRasterBand(1)

	osrs = osr.SpatialReference()
	osrs.ImportFromEPSG(3338)

	if not x_block_size and y_block_size:
		block_sizes = band.GetBlockSize()
		x_block_size = block_sizes[0]
		y_block_size = block_sizes[1]

	xsize = band.XSize
	ysize = band.YSize

	max_value = band.GetMaximum()
	min_value = band.GetMinimum()

	# this just goes in and calculates stats for a band that has no stats calculated
	# and it sets them to the min/max values 
	if max_value == None or min_value == None:
		stats = band.GetStatistics(0, 1)
		max_value = stats[1]
		min_value = stats[0]

	# create a new output raster to reclass to
	driver = gdal.GetDriverByName( output_format )
	dst_ds = driver.Create(output_filename, xsize, ysize, 1, gdal_data_type, options = ["COMPRESS=LZW"])
	dst_ds.SetGeoTransform(gdal_raster.GetGeoTransform())
	dst_ds.SetProjection(osrs.ExportToWkt())

	for i in range(0, ysize, y_block_size):
		if i + y_block_size < ysize:
			rows = y_block_size
		else:
			rows = ysize - i

		for j in range(0, xsize, x_block_size):
			if j + x_block_size < xsize:
				cols = x_block_size
			else:
				cols = xsize

			data = band.ReadAsArray(j, i, cols, rows)
			data_out = np.zeros(data.shape, dtype=np.dtype(float))
		
			for k in reclass_table:
				begin, end, out = k
				data_out[np.logical_and(data >= begin, data < end)] = out

			dst_ds.GetRasterBand(1).WriteArray(data_out,j,i)

	dst_ds.FlushCache()
	dst_ds.GetRasterBand(1).ComputeBandStats()
	dst_ds.GetRasterBand(1).ComputeRasterMinMax()
	dst_ds.GetRasterBand(1).ComputeStatistics(0)
	dst_ds.FlushCache()
	return dst_ds


def combine(in_rst1, in_rst2, combine_hash, output_filename, output_format='GTiff', x_block_size=None, y_block_size=None):
	"""
	
	This function currently takes as input 2 raster files and uses raster 2 to cover raster 1 with a new
	value at specific value location in raster 2.  This function is sort of clunky, but works fairly quickly 
	given the number of pixels we are working with at a given time.  It will be modified to take a different 
	type of input in the next version so it will change significantly in the coming weeks.

	"""
	inrst1_band = in_rst1.GetRasterBand(1)
	inrst2_band = in_rst2.GetRasterBand(1)
	
	if not x_block_size and y_block_size:
		x_block_size, y_block_size = inrst1_band.GetBlockSize()

	xsize = inrst1_band.XSize
	ysize = inrst1_band.YSize

	# create a new output raster 
	driver = gdal.GetDriverByName( output_format )
	dst_ds = driver.Create(output_filename, xsize, ysize, 1, gdal.GDT_Float32, options=["COMPRESS=LZW"])
	dst_ds.SetGeoTransform(in_rst1.GetGeoTransform())
	dst_ds.SetProjection(in_rst1.GetProjection())

	for i in range(0, ysize, y_block_size):
		if i + y_block_size < ysize:
			rows = y_block_size
		else:
			rows = ysize - i

		for j in range(0, xsize, x_block_size):
			if j + x_block_size < xsize:
				cols = x_block_size
			else:
				cols = xsize

			data1 = inrst1_band.ReadAsArray(j, i, cols, rows)
			data2 = inrst2_band.ReadAsArray(j, i, cols, rows)
			out_data = np.copy(data1)

			for k in range(len(combine_hash)):
				rst1_val, rst2_val = [int(item) for item in list(combine_hash.keys()[k])]
				out_val = combine_hash.values()[k]

				out_data[np.logical_and(data1 == rst1_val, data2 == rst2_val)] = out_val

			dst_ds.GetRasterBand(1).WriteArray(out_data,j,i)

	dst_ds.FlushCache()
	dst_ds.GetRasterBand(1).ComputeBandStats()
	dst_ds.GetRasterBand(1).ComputeRasterMinMax()
	dst_ds.GetRasterBand(1).ComputeStatistics(0)
	dst_ds.FlushCache()
	return dst_ds


def overlay_cover(base_rst, cover_rst, cover_value, out_cover_value, output_filename, data_type=gdal.GDT_Float32, creation_options=["COMPRESS=LZW"], x_block_size=None, y_block_size=None):
	"""
	a function to overlay 2 raster maps and change the values on a 
	copy of the base_rst based on a value in the cover_rst. The 
	value can be changed to any the user desires.  The variables
	cover_value and out_cover_value can be lists of values to be 
	modified.  The 2 lists must be of the same length as the 
	function will loop through them iteratively changing values
	at the location of the base_rst that coincide with cover_value
	in the cover_rst, where those values are changes in the base_rst
	to the output_cover_value at the same list index position.


	depends: gdal, numpy
	"""
	base_rst_band = base_rst.GetRasterBand(1)
	cover_rst_band = cover_rst.GetRasterBand(1)
	
	if not x_block_size and y_block_size:
		x_block_size, y_block_size = base_rst_band.GetBlockSize()

	xsize = base_rst_band.XSize
	ysize = base_rst_band.YSize

	# create a new output raster 
	driver = base_rst.GetDriver()
	dst_ds = driver.Create(output_filename, xsize, ysize, 1, base_rst_band.DataType, options=creation_options)
	dst_ds.SetGeoTransform(base_rst.GetGeoTransform())
	dst_ds.SetProjection(base_rst.GetProjection())

	# block walk
	for i in range(0, ysize, y_block_size):
		if i + y_block_size < ysize:
			rows = y_block_size
		else:
			rows = ysize - i

		for j in range(0, xsize, x_block_size):
			if j + x_block_size < xsize:
				cols = x_block_size
			else:
				cols = xsize

			base_arr = base_rst_band.ReadAsArray(j, i, cols, rows)
			cover_arr = cover_rst_band.ReadAsArray(j, i, cols, rows)
			out_arr = np.copy(base_arr)

			if isinstance(out_cover_value, list):
				for k in range(len(out_cover_value)):
					out_arr[cover_arr == cover_value[k]] = out_cover_value[k]
			else:
				out_arr[cover_arr == cover_value] = out_cover_value

			dst_ds.GetRasterBand(1).WriteArray(out_arr, j, i)

	dst_ds.GetRasterBand(1).ComputeStatistics(0)
	dst_ds.FlushCache()
	return dst_ds


def raster_bbox( geotransform, size ):
	"""

	return the extent of a raster in the standard bbox format 
	found in ogr.GetLayer().GetExtent().

	argumments:
	geotransform = a gdal geotransform obtained through 
				rst.GetGeoTransform() on a gdal dataset

	size = list() where the elements are [xsize,ysize]
				typically obtained through:
				[rst.RasterXSize, rst.RasterYSize]

	"""

	east1 = geotransform[0]
	east2 = geotransform[0] + (geotransform[1] * size[0])
	west1 = geotransform[3] + (geotransform[5] * size[1])
	west2 = geotransform[3]
	return [east1, east2, west1, west2]


def generate_raster(input_extent, epsg_code, output_filename, x_res=None, y_res=None, \
	output_width=None, output_height=None, output_format="GTiff", \
	output_datatype=gdal.GDT_Float32, creation_options=["COMPRESS=LZW"]):
	"""
	this script takes as input an extent object and x/y cell resolution OR the number of pixels  to create a new 
	empty raster at the given spatial resolutuon

	--> considered alpha state at the moment <--
	Code modified from GDAL FAQ: 
	https://trac.osgeo.org/gdal/wiki/FAQRaster#
		HowcanIcreateablankrasterbasedonavectorfilesextentsforusewithgdal_rasterizeGDAL1.8.0
	"""
	import math
	# generate a spatial ref object
	osrs = osr.SpatialReference()
	osrs.ImportFromEPSG(epsg_code)

	# setup the driver for the output raster
	driver = gdal.GetDriverByName(output_format)

	# which generation method to use?
	if x_res:
		# Alternative A: Calculate raster dataset dimensions from desired pixel resolution
		tiff_width = int(math.ceil(abs(input_extent[1] - input_extent[0]) / x_res))
		tiff_height = int(math.ceil(abs(input_extent[3] - input_extent[2]) / y_res))
	elif output_width:
		# Alternative B: Calculate pixel resolution from desired dataset dimensions
		x_res = (input_extent[1] - input_extent[0]) / tiff_width
		y_res = (input_extent[3] - input_extent[2]) / tiff_height
	else:
		print('Must have both x_res & y_res OR \noutput_width and output_height')

	# create a GeoTransform for the new raster
	geoTransform = [ input_extent[0], x_res, 0.0, input_extent[3], 0.0, -y_res ]
	dst_ds = driver.Create( output_filename, tiff_width, tiff_height, 1, output_datatype )
	dst_ds.SetGeoTransform( geoTransform )
	dst_ds.SetProjection( osrs.ExportToWkt() )
	return dst_ds


def resample(gdal_raster, epsg_code, output_filename, method='mode', x_res=None, y_res=None, \
	output_width=None, output_height=None, output_format="GTiff", output_datatype=gdal.GDT_Float32, \
	creation_options=["COMPRESS=LZW"]):
	"""
	a wrapper around a couple of other boilerplate gdal functions to have a one-off way of 
	resampling a dataset
	"""
	input_extent = raster_bbox(gdal_raster.GetGeoTransform(), 
			size=[gdal_raster.RasterXSize, gdal_raster.RasterYSize])
	
	out = generate_raster(input_extent, 
			epsg_code=3338, 
			output_filename=output_filename, 
			x_res=x_res, 
			y_res=y_res, 
			output_width=output_width, 
			output_height=output_height, 
			output_format=output_format, 
			output_datatype=output_datatype, 
			creation_options=creation_options)

	gdal.RegenerateOverview ( gdal_raster.GetRasterBand(1), out.GetRasterBand(1), method )
	out.GetRasterBand(1).ComputeStatistics(0)
	out.FlushCache()
	return out

#######################################################

# pre-process
file_path = '/workspace/Shared/Tech_Projects/AK_LandCarbon/project_data/input_data/From_Frances_Extracted'
# file_query_list = [['AKNPLCC_2ndGrowth.shp',],['AKNPLCC_Saltwater.shp',],['TNFCoverType.shp',]]
creation_options=["COMPRESS=LZW"]
master_raster=gdal.Open(os.path.join(file_path,'NLCD_canopy_AKNPLCC.tif'), gdal.GA_ReadOnly)
# osrs.ImportFromEPSG(3338)

# Saltwater
input_spatial_file = ogr.Open(os.path.join(file_path,'AKNPLCC_Saltwater.shp'))

osrs = osr.SpatialReference()
osrs.ImportFromWkt(input_spatial_file.GetLayer().GetSpatialRef().ExportToWkt())
master_raster.SetProjection(osrs.ExportToWkt())

output_dataset = os.path.join(file_path,'AKNPLCC_Saltwater.tif')
filter_query = None
rasterized_out = preprocess( master_raster, 
		input_spatial_file, 
		output_dataset, 
		burn_value=1, 
		filter_query=None, 
		creation_options=creation_options, 
		rasterize_options=None )


# TNFCoverType -- this involves 2 queries and burning into the same dataset
input_spatial_file = ogr.Open(os.path.join(file_path,'TNFCoverType.shp'))
output_dataset = os.path.join(file_path,'TNFCoverType.tif')
burn_value_list = [5,6]
filter_query_list = [ "NFCON='A' OR NFCON='B' OR NFCON='S' OR NFCON='T' OR NFCON='W'", "NFCON='H'" ]

for i in range(len(filter_query_list)):
	output_dataset = preprocess(master_raster, 
			input_spatial_file, 
			output_dataset, 
			burn_value=burn_value_list[i], 
			filter_query=filter_query_list[i], 
			creation_options=creation_options, 
			rasterize_options=None)

# SEAK_2ndGrowth
input_spatial_file = ogr.Open(os.path.join(file_path,'AKNPLCC_2ndGrowth.shp'))
output_dataset = os.path.join(file_path,'SEAK_2ndGrowth.tif')

# just to remove the testing raster which is the same name.  the preprocess code is not that smart
if os.path.exists(output_dataset):
	os.unlink(output_dataset)

filter_query = None
rasterize_options = ["ATTRIBUTE=year"]

rasterized_out = preprocess(master_raster, 
		input_spatial_file, 
		output_dataset, 
		burn_value=None, 
		filter_query=None, 
		creation_options=creation_options, 
		rasterize_options=rasterize_options)



#######################################################

# PROCEDURE WORKING VERSION:  this will evolve into the main()

# some initial base filename setup
output_path = '/workspace/Shared/Tech_Projects/AK_LandCarbon/project_data/output_data'
output_name = 'LandCarbon_LandCover_SEAK_v1.tif'

## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## 

# step 3 reclassify NLCD Canopy raster
reclass_table = [[1, 20, 1],[20, 101, 2]]
canopy = gdal.Open(os.path.join(file_path,'NLCD_canopy_AKNPLCC.tif'), gdal.GA_ReadOnly)
canopy_rcl = reclassify_raster( canopy, 
		reclass_table, 
		output_filename=os.path.join(output_path, output_name.replace('.tif','_canopy_rcl.tif')), 
		output_format='GTiff',
		x_block_size=canopy.RasterXSize, 
		y_block_size=canopy.RasterYSize )


## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## 

# step 4 reclassify NLCD raster
reclass_table = [[0, 32, 1],[42, 43, 2],[41, 42, 3],[43, 73, 3],[90, 96, 3], [81, 83, 5]]
landcover = gdal.Open(os.path.join(file_path,'NLCD_land_cover_AKNPLCC.tif'), gdal.GA_ReadOnly)
landcover_rcl = reclassify_raster(landcover, 
		reclass_table,  
		output_filename=os.path.join(output_path, output_name.replace('.tif','_landcover_rcl.tif')), 
		output_format='GTiff', 
		x_block_size=landcover.RasterXSize, 
		y_block_size=landcover.RasterYSize)


## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## 

# step 5 combine the above reclassed rasters
# what was done here was the stringing the rst1 val and rst2 val together and 
# returing the value of the new pixel
combine_hash = {'11':1,'12':2,'21':3,'22':4,'31':5,'32':6,'51':7,'52':8}
combined = combine(landcover_rcl, 
		canopy_rcl, 
		combine_hash, 
		os.path.join(output_path, output_name.replace('.tif','_combined.tif')), 
		output_format='GTiff',
		x_block_size=landcover_rcl.RasterXSize, 
		y_block_size=landcover_rcl.RasterYSize )


## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## 

# step 6 reclassify the above combined map
reclass_table = [[1,3,1],[3,4,4],[4,5,2],[5,6,4],[6,7,3],[7,9,5]]
combined_rcl = reclassify_raster(combined, 
		reclass_table, 
		output_filename=os.path.join(output_path, output_name.replace('.tif','_combined_rcl.tif')), 
		output_format='GTiff',
		x_block_size=combined.RasterXSize, 
		y_block_size=combined.RasterYSize)


## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## 
# step 8 
# overlay with the TNF Cover Type

base_rst = combined_rcl
cover_rst = gdal.Open(os.path.join(file_path,'TNFCoverType.tif'))
cover_value = [5,6]
out_cover_value = [5,6]
output_filename = os.path.join(output_path, output_name.replace('.tif','_add_TNFCoverType.tif'))

if os.path.exists(os.path.join(output_path, output_name.replace('.tif','_add_TNFCoverType.tif'))):
	os.unlink(os.path.join(output_path, output_name.replace('.tif','_add_TNFCoverType.tif')))

data_type=gdal.GDT_Float32
creation_options=["COMPRESS=LZW"]

TNF_cover_added = overlay_cover(base_rst, 
		cover_rst, 
		cover_value, 
		out_cover_value, 
		output_filename, 
		data_type=gdal.GDT_Float32, 
		creation_options=["COMPRESS=LZW"], 
		x_block_size=base_rst.RasterXSize, 
		y_block_size=base_rst.RasterYSize )

## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## 

# ** Changed to final step prior to resampling. **
#  reclassify erroneous values in Saltwater
base_rst = TNF_cover_added
cover_rst = gdal.Open(os.path.join(file_path,'AKNPLCC_Saltwater.tif'))
cover_value = 1
out_cover_value = 1
output_filename = os.path.join(output_path, output_name.replace('.tif','_remove_saltwater.tif'))

if os.path.exists(os.path.join(output_path, output_name.replace('.tif','_remove_saltwater.tif'))):
	os.unlink(os.path.join(output_path, output_name.replace('.tif','_remove_saltwater.tif')))

data_type=gdal.GDT_Float32
creation_options=["COMPRESS=LZW"]

saltwater_removed = overlay_cover(base_rst, 
		cover_rst, 
		cover_value, 
		out_cover_value, 
		output_filename, 
		data_type=gdal.GDT_Float32, 
		creation_options=["COMPRESS=LZW"],
		x_block_size=base_rst.RasterXSize, 
		y_block_size=base_rst.RasterYSize )

## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## 

# RESAMPLE OUTPUT TO 1KM
if os.path.exists('/workspace/Shared/Tech_Projects/AK_LandCarbon/project_data/output_data/resampled_test_new.tif'):
	os.unlink('/workspace/Shared/Tech_Projects/AK_LandCarbon/project_data/output_data/resampled_test_new.tif')

resampled_1k = resample( gdal_raster=gdal.Open('/workspace/Shared/Tech_Projects/AK_LandCarbon/project_data/output_data/LandCarbon_LandCover_BETA_v1_add_TNFCoverType.tif'),
		epsg_code=3338,
		output_filename='/workspace/Shared/Tech_Projects/AK_LandCarbon/project_data/output_data/resampled_test_new.tif',
		method='mode',
		x_res=1000,
		y_res=1000,
		output_width=None,
		output_height=None,
		output_format="GTiff",
		output_datatype=gdal.GDT_Float32,
		creation_options=["COMPRESS=LZW"] )

## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## 

# cleanup the file handles before loading into a  GIS
canopy_rcl.FlushCache()
landcover_rcl.FlushCache()
combined.FlushCache()
combined_rcl.FlushCache()
saltwater_removed.FlushCache() 
TNF_cover_added.FlushCache()
resampled_1k.FlushCache()

# some cleanup -- very important for file flushing
canopy_rcl = None
landcover_rcl = None
combined = None
combined_rcl = None
saltwater_removed = None
TNF_cover_added = None
resampled_1k = None


## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## 
# step 9 
# some kind of data type conversion -- SKIPPED 

## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## 
# step 10
# SEAK 2nd Growth inclusion
# 
# --> This is not a working function and is still in development.
#  I am honestly not sure how to integrate this into the larger
#  landcover map and will wait instruction from others regarding how to do it
#  as it stands the data have been rasterized to the same raster size / res / etc
#  as the output landcover map at 30m spatial resolution.
#
# unique_vals = np.unique(rst.GetRasterBand(1).ReadAsArray().ravel())
# unique_vals = [int(i) for i in unique_vals[unique_vals > 0].tolist()]

# data_type=gdal.GDT_Float32
# creation_options=["COMPRESS=LZW"]

# seak_2ndGrowth_added = overlay_cover(base_rst, 
# 		cover_rst, 
# 		cover_value, 
# 		out_cover_value, 
# 		output_filename, 
# 		data_type=gdal.GDT_Float32, 
# 		creation_options=["COMPRESS=LZW"])



# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -


