# # # # # # # 
# LandCarbon LandCover SEAK Classification PROCEDURE version 2.0
import pprint
import os, sys, rasterio, fiona
from rasterio import features
from rasterio.warp import reproject, RESAMPLING
import numpy as np
import scipy as sp

# import local library of functions
os.chdir( '/workspace/Shared/Tech_Projects/AK_LandCarbon/project_data/CODE' )
from final_v2_library import *

# some initial setup
version_num = 'v0_3'
input_path = '/workspace/Shared/Tech_Projects/AK_LandCarbon/project_data/input_data/From_Frances_Extracted'
output_path = '/workspace/Shared/Tech_Projects/AK_LandCarbon/project_data/output_data/data/V7'
os.chdir( output_path )
meta_updater = dict( driver='GTiff', dtype=rasterio.int16, compress='lzw', crs={'init':'EPSG:3338'}, count=3, nodata=None )

# set up some ouput sub-dirs for the intermediates and the rasterized
intermediate_path = os.path.join( output_path, 'intermediates' )
rasterized_path = os.path.join( output_path, 'rasterized' )
if not os.path.exists( intermediate_path ):
	os.mkdir( intermediate_path )

if not os.path.exists( rasterized_path ):
	os.mkdir( rasterized_path )

master_raster = rasterio.open( os.path.join( input_path, 'NLCD_canopy_AKNPLCC.tif' ) )
meta = master_raster.meta
meta.update( meta_updater )
master_raster.close()
del master_raster

# here we are going to take the input master raster and use it to inform a multibanded output GTiff
# used to store all of the 30m input data in a single file.  This may aid in future computations.
#  >>> current layer order is: saltwater, tnf_covertype, seak_2ndGrowth
output_filename = os.path.join( rasterized_path, 'LandCarbon_vegetation_classification_ancillary' + version_num + '.tif' )
ancillary_prepped = rasterio.open( output_filename, mode='w', **meta )

## saltwater
saltwater = fiona.open( os.path.join( input_path,'AKNPLCC_Saltwater.shp' ) )

sw_image = features.rasterize(
			( ( g['geometry'], 1 ) for g in saltwater ),
			out_shape=ancillary_prepped.shape,
			transform=ancillary_prepped.transform, 
			fill=0 )

# place the new output ndarray into the ancillary raster band 1
sw_image = sw_image.astype( np.int16 )
ancillary_prepped.write_band( 1, sw_image )
del sw_image, saltwater


## tnf_covertype
covertype = fiona.open( os.path.join( input_path,'TNFCoverType_OtherVeg_and_Alpine_MLedit.shp' ) )
output_dataset = os.path.join( input_path,'TNFCoverType_OtherVeg_and_Alpine_MLedit.tif' )
filter_query_list = [ "NFCON='A' OR NFCON='B' OR NFCON='S' OR NFCON='T' OR NFCON='W'", "NFCON='H'" ]

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
			out_shape=ancillary_prepped.shape, 
			transform=ancillary_prepped.transform, 
			fill=0)

# place the new output ndarray into ancillary raster band 2
ct_image = ct_image.astype( np.int16 )
ancillary_prepped.write_band( 2, ct_image )
del ct_image, covertype


## seak_2nd_growth
seak2nd = fiona.open( os.path.join( input_path,'AKNPLCC_2ndGrowth.shp' ) )

years = [ int(g['properties']['year']) for g in seak2nd ]
years_classed = dict([ ( value, key ) for key, value in enumerate( np.unique( np.array( years ) ).tolist() ) ])
reclassed = [ ( g['geometry'], years_classed[ int( g['properties']['year'] ) ] ) for g in seak2nd ]

s2_image = features.rasterize(
			reclassed,
			out_shape=ancillary_prepped.shape,
			transform=ancillary_prepped.transform,
			fill=0 )

# change the dtypes so they are compatible
# write the new array into the container with the years passed back in...
s2_image = s2_image.astype( np.int16 )
for year in years_classed.keys():
	s2_image[ s2_image == ( years_classed[ year ] + 1 ) ] = year # +1 is to deal with zero anchored numbering in python

ancillary_prepped.write_band( 3, s2_image )
ancillary_prepped.close()
del s2_image, seak2nd, ancillary_prepped

print( 'preprocessing complete.' )


