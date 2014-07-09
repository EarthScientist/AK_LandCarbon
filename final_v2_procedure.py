# # # # # # # 
# LandCarbon LandCover SEAK Classification PREPROCESSING version 2.0

import pprint
import os, sys, rasterio, fiona
from rasterio import features
import numpy as np
import scipy as sp

file_path = '/workspace/Shared/Tech_Projects/AK_LandCarbon/project_data/input_data/From_Frances_Extracted'
output_path = '/workspace/Shared/Tech_Projects/AK_LandCarbon/project_data/output_data/data/V3'
master_raster = rasterio.open( os.path.join( file_path,'NLCD_canopy_AKNPLCC.tif' ) )
meta = master_raster.meta

# consider rasterizing this and making it the final map
full_extent_shape = fiona.open( '/workspace/Shared/Tech_Projects/AK_LandCarbon/project_data/input_data/\
							Frances_ExtendedShoreline_060914/AKNPLCC_Saltwater_with_Kodiak.shp' )

output_filename = os.path.join( output_path, 'LandCarbon_LandCover_SEAK_v3.tif' )
full_extent_raster = generate_raster( full_extent_shape.bounds, 1000, output_filename, 
							crs={'init', 'EPSG:3338'}, bands=1, dtype=rasterio.int32, 
							driver='GTiff', creation_options=["COMPRESS=LZW"] )

## saltwater
saltwater = fiona.open( os.path.join( file_path,'AKNPLCC_Saltwater.shp' ) )

# set the crs to the correct one.  There is some software of lib that we use in R that 
# has botched all of the coord systems for some reason.  This solves is and sets it at 
# the EPSG:3338 that is standard
crs = saltwater.crs # will be the base coordsys for this preprocessing
meta.update( crs=crs )
meta.update( dtype=rasterio.int32 )
sw_raster = rasterio.open( os.path.join( output_path, 'saltwater_version2.tif'), 'w', **meta )

sw_image = features.rasterize(
			( ( g['geometry'], 1 ) for g in saltwater ),
			out_shape=master_raster.shape,
			transform=master_raster.transform, 
			fill=0 )

# place the new output ndarray into sw_raster
sw_image = sw_image.astype( np.int32 )
sw_raster.write_band( 1, sw_image )
sw_raster.flush()
del sw_image, saltwater


## tnf_covertype
covertype = fiona.open(os.path.join(file_path,'TNFCoverType_OtherVeg_and_Alpine_MLedit.shp'))
output_dataset = os.path.join(file_path,'TNFCoverType_OtherVeg_and_Alpine_MLedit.tif')
filter_query_list = [ "NFCON='A' OR NFCON='B' OR NFCON='S' OR NFCON='T' OR NFCON='W'", "NFCON='H'" ]
# create a new output raster with some modified params
meta = master_raster.meta
meta.update( crs=crs )
meta.update( dtype=rasterio.int32 )
ct_raster = rasterio.open( os.path.join( output_path, 'tnf_covertype_version2.tif'), 'w', **meta )

def filter_cover_type( x ):
	if x['properties']['NFCON'] != u'H':
		hold = ( x['geometry'], 5 )
	elif x['properties']['NFCON'] == u'H':
		hold = ( x['geometry'], 6 )
	else:
		BaseException( 'ERROR' )
	return hold

ct_image = features.rasterize(
			( filter_cover_type( g ) for g in covertype ),
			out_shape=ct_raster.shape, 
			transform=ct_raster.transform, 
			fill=0)

# place the new output ndarray into ct_raster
ct_image = ct_image.astype( np.int32 )
ct_raster.write_band( 1, ct_image )
ct_raster.flush()
del ct_image, covertype


## seak_2nd_growth
seak2nd = fiona.open( os.path.join( file_path,'AKNPLCC_2ndGrowth.shp' ) )
meta = master_raster.meta
meta.update( crs=crs )
meta.update( dtype=rasterio.int32 )
s2_raster = rasterio.open( os.path.join( output_path, 'seak2nd_growth_version2'.tif, 'w', **meta ) )

years = [ int(g['properties']['year']) for g in seak2nd ]
years_classed = dict([ ( value, key ) for key, value in enumerate( np.unique( np.array( years ) ).tolist() ) ])
reclassed = [ ( g['geometry'], years_classed[ int( g['properties']['year'] ) ] ) for g in seak2nd ]

s2_image = features.rasterize(
			reclassed,
			out_shape=master_raster.shape,
			transform=master_raster.transform,
			fill=0 )

# change the dtypes so they are compatible
# write the new array into the container with the years passed back in...
s2_image.astype( np.int32 )
for year in years_classed.keys():
	s2_image[ s2_image == years_classed[ year ] ] = year

s2_raster.write_band( 1, s2_image )
s2_raster.flush()
del s2_image, seak2nd

# PREPROCESSING COMPLETE!

# # # # # # # # # 

# BEGIN RECLASSIFICATION PROCEDURE:
# some initial base filename setup
# output_name = 'LandCarbon_LandCover_SEAK_v3.tif'

## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## 

# step 3 reclassify NLCD Canopy raster
canopy = rasterio.open( os.path.join( file_path,'NLCD_canopy_AKNPLCC.tif' ) )
output_filename = os.path.join( output_path, 'NLCD_canopy_AKNPLCC_RCL_version2.tif' )
reclass_list = [[1, 20, 1],[20, 101, 2]]
canopy_rcl = reclassify( canopy, reclass_list, output_filename, band=1 )

## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## 

# step 4 reclassify NLCD raster
landcover = rasterio.open( os.path.join( file_path, 'NLCD_land_cover_AKNPLCC.tif' ) )
output_filename = os.path.join( output_path, 'NLCD_land_cover_AKNPLCC_RCL_version2.tif' )
reclass_list = [[0, 32, 1],[42, 43, 2],[41, 42, 3],[43, 73, 3],[90, 96, 3], [81, 83, 5]]
landcover_rcl = reclassify( landcover, reclass_list, output_filename, band=1 )

## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## 

# step 5 combine the above reclassed rasters
output_filename = os.path.join( output_path, 'nlcd_landcover_canopy_combined_version2.tif' )
combine_list = [[1,1,1],[1,2,2],[2,1,3],[2,2,4],[3,1,5],[3,2,6],[5,1,7],[5,2,8]]
combined = combine( landcover_rcl, canopy_rcl, combine_list, output_filename )

## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## 

# step 6 reclassify the above combined map
output_filename = os.path.join( output_path, 'combined_NLCD_RCL_version2.tif' )
reclass_list = [[1,3,1],[3,4,4],[4,5,2],[5,6,4],[6,7,3],[7,9,5]]
combined_rcl = reclassify( combined, reclass_list, output_filename, band=1 )

## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## 
# step 8 
# overlay with the TNF Cover Type
output_filename = os.path.join( output_path, 'overlay_combinercl_ctraster.tif' )
tnf_cover_added = overlay_modify( combined_rcl, ct_raster, in_cover_values=[5,6], 
									out_cover_values=[5,6], output_filename=output_filename, 
									rst_base_band=1, rst_cover_band=1 )

## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## 
# we also need to solve an issue where the pixels with values not upland coincident
#  with the harvest to upland.
# SEAK_2ndGrowth = SEAK_2ndGrowth_noveg
output_filename = os.path.join( output_path, 'seak2nd_growth_version2_removed.tif' )
tnf_ct_band = tnf_cover_added.read_band(1)
s2_band = s2_raster.read_band(1)
tnf_ct_copy = np.copy( tnf_ct_band )
tnf_ct_copy[ np.logical_and( np.logical_or(TNF_cover_added_arr > 1, TNF_cover_added_arr < 5 ), \
		SEAK_2ndGrowth_arr > 0 )] = 2 # convert harvested area to upland
s2_removed = rasterio.open( output_filename, mode='w', **meta )


## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## 

# ** Changed to final step prior to resampling. **
#  reclassify erroneous values in Saltwater
output_filename = os.path.join( output_path, 'remove_saltwater_version2.tif' )
base_rst = SEAK_2ndGrowth_upland
cover_rst = gdal.Open( os.path.join( file_path,'AKNPLCC_Saltwater.tif' ) )
cover_value = 1
out_cover_value = 1
sw_removed = overlay_modify( s2_removed, sw_raster, in_cover_values=[1], out_cover_values=[1], \
				output_filename=output_filename, rst_base_band=1, rst_cover_band=1 )


## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## 
# resampling to the 1km grid 

# get the raster bands to be regridded as arrays
band1 = sw_raster.read_band( 1 )
band2 = full_extent_raster.read_band( 1 )

# a make an all zeros copy of the band 2 
band2 = np.zeros_like( band2 )

# set a common crs (in this case it is the same as I want to regrid not reproject)
crs = {'init':'EPSG:3338'}
src_transform = sw_raster.transform
dst_transform = full_extent_raster.transform

# run the resampling using nearest neighbor resampling
reproject( band1, band2, src_transform=src_transform, src_crs=crs, dst_transform=dst_transform, \
			dst_crs=crs, resampling=RESAMPLING.nearest )


# cleanup the file handles before loading into a  GIS


