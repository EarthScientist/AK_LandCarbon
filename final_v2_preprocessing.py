# # # # # # # 
# LandCarbon LandCover SEAK Classification PREPROCESSING version 2.0
import pprint
import os, sys, rasterio, fiona
from rasterio import features
from rasterio.warp import reproject, RESAMPLING
import numpy as np
import scipy as sp

# import my library of functions
os.chdir( '/workspace/Shared/Tech_Projects/AK_LandCarbon/project_data/CODE' )
from final_v2_library import *

file_path = '/workspace/Shared/Tech_Projects/AK_LandCarbon/project_data/input_data/From_Frances_Extracted'
output_path = '/workspace/Shared/Tech_Projects/AK_LandCarbon/project_data/output_data/data/V4'
master_raster = rasterio.open( os.path.join( file_path,'NLCD_canopy_AKNPLCC.tif' ) )
meta = master_raster.meta

# set up some ouput sub-dirs for the intermediates and the rasterized
rasterized_path = os.path.join( output_path, 'rasterized' )
if not os.path.exists( rasterized_path ):
	os.mkdir( rasterized_path )

## saltwater
saltwater = fiona.open( os.path.join( file_path,'AKNPLCC_Saltwater.shp' ) )

# set the crs to the correct one.  There is some software of lib that we use in R that 
# has botched all of the coord systems for some reason.  This solves is and sets it at 
# the EPSG:3338 that is standard
crs = saltwater.crs # will be the base coordsys for this preprocessing
meta.update( crs=crs, dtype=rasterio.int32, compress='lzw')
sw_raster = rasterio.open( os.path.join( rasterized_path, 'saltwater_seak.tif' ), 'w', **meta )

sw_image = features.rasterize(
			( ( g['geometry'], 1 ) for g in saltwater ),
			out_shape=master_raster.shape,
			transform=master_raster.transform, 
			fill=0 )

# place the new output ndarray into sw_raster
sw_image = sw_image.astype( np.int32 )
sw_raster.write_band( 1, sw_image )
sw_raster.close()
del sw_image, saltwater, sw_raster

## tnf_covertype
covertype = fiona.open( os.path.join( file_path,'TNFCoverType_OtherVeg_and_Alpine_MLedit.shp' ) )
output_dataset = os.path.join( file_path,'TNFCoverType_OtherVeg_and_Alpine_MLedit.tif' )
filter_query_list = [ "NFCON='A' OR NFCON='B' OR NFCON='S' OR NFCON='T' OR NFCON='W'", "NFCON='H'" ]

# create a new output raster with some modified params
meta.update( crs=crs, dtype=rasterio.int32, compress='lzw')
ct_raster = rasterio.open( os.path.join( rasterized_path, 'tnf_covertype_seak.tif'), 'w', **meta )

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
ct_raster.close()
del ct_image, covertype


## seak_2nd_growth
seak2nd = fiona.open( os.path.join( file_path,'AKNPLCC_2ndGrowth.shp' ) )
meta = master_raster.meta
meta.update( crs=crs, dtype=rasterio.int32, compress='lzw')
s2_raster = rasterio.open( os.path.join( rasterized_path, 'seak2nd_growth_seak.tif'), 'w', **meta )

years = [ int(g['properties']['year']) for g in seak2nd ]
years_classed = dict([ ( value, key ) for key, value in enumerate( np.unique( np.array( years ) ).tolist() ) ])
reclassed = [ ( g['geometry'], years_classed[ int( g['properties']['year'] ) ] ) for g in seak2nd ]

s2_image = features.rasterize(
			reclassed,
			out_shape=s2_raster.shape,
			transform=s2_raster.transform,
			fill=0 )

# change the dtypes so they are compatible
# write the new array into the container with the years passed back in...
s2_image = s2_image.astype( np.int32 )
for year in years_classed.keys():
	s2_image[ s2_image == (years_classed[ year ] + 1 )] = year # +1 is to deal with zero anchored numbering in python

s2_raster.write_band( 1, s2_image )
s2_raster.close()
del s2_image, seak2nd

# PREPROCESSING COMPLETE!