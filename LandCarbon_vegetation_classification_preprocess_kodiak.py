# KODIAK ISLAND NLCD RECLASSIFICATION BASED ON A CROSS-WALK PROPOSED BY 
#  DAVE McGUIRE & THE SPATIAL ECOLOGY LAB (SEL) FOR USE IN THE ALASKA
#  LANDCARBON PROJECT.
#
# CODE DEVELOPED BY: MICHAEL LINDGREN (malindgren@alaska.edu), SENIOR 
#  SPATIAL ANALYST AT SCENARIOS NETWORK FOR ALASKA & ARCTIC PLANNING
#  (SNAP), INTERNATIONAL ARCTIC RESEARCH CENTER (IARC), UNIVERSITY OF 
#  ALASKA FAIRBANKS (UAF).
# # # # # 
import os, sys, rasterio, fiona
from rasterio import features
import numpy as np
import scipy as sp

# import local library of functions
os.chdir( '/workspace/Shared/Tech_Projects/AK_LandCarbon/project_data/CODE' )
from final_v2_library import *

# some initial setup
version_num = 'v0_3'
input_path = '/workspace/Shared/Tech_Projects/AK_LandCarbon/project_data/input_data'
output_path = '/workspace/Shared/Tech_Projects/AK_LandCarbon/project_data/output_data/data/V6'
os.chdir( output_path )
meta_updater = dict( driver='GTiff', dtype=rasterio.int16, compress='lzw', crs={'init':'EPSG:3338'}, count=3, nodata=None )

# set up some ouput sub-dirs for the intermediates and the rasterized
intermediate_path = os.path.join( output_path, 'intermediates' )
rasterized_path = os.path.join( output_path, 'rasterized' )
if not os.path.exists( intermediate_path ):
	os.mkdir( intermediate_path )

if not os.path.exists( rasterized_path ):
	os.mkdir( rasterized_path )


lc_path = os.path.join( input_path, 'KodiakIsland','ak_nlcd_2001_land_cover_3130_KodiakIsland_3338.tif' ) 
landcover = rasterio.open( lc_path )
meta = landcover.meta
meta.update( meta_updater )

# saltwater
saltwater = fiona.open( os.path.join( input_path,'Frances_ExtendedShoreline_060914','AKNPLCC_Saltwater_with_Kodiak.shp' ) )

# set the crs to the correct one.  There is some software of lib that we use in R that 
# has botched all of the coord systems for some reason.  This solves is and sets it at 
# the EPSG:3338 that is standard
# crs = saltwater.crs # will be the base coordsys for this preprocessing
# meta.update( crs=crs, dtype=rasterio.int32, compress='lzw' )
sw_raster = rasterio.open( os.path.join( rasterized_path, 'saltwater_kodiak.tif' ), 'w', **meta )

sw_image = features.rasterize(
			( ( g['geometry'], 1 ) for g in saltwater ),
			out_shape=landcover.shape,
			transform=landcover.transform, 
			fill=0 )

# place the new output ndarray into sw_raster
sw_image = sw_image.astype( np.int32 )
sw_raster.write_band( 1, sw_image )
sw_raster.close()
del sw_image, saltwater

