# KODIAK ISLAND NLCD RECLASSIFICATION BASED ON A CROSS-WALK PROPOSED BY 
#  DAVE McGUIRE & THE SPATIAL ECOLOGY LAB (SEL) FOR USE IN THE ALASKA
#  LANDCARBON PROJECT.
#
# CODE DEVELOPED BY: MICHAEL LINDGREN (malindgren@alaska.edu), SENIOR 
#  SPATIAL ANALYST AT SCENARIOS NETWORK FOR ALASKA & ARCTIC PLANNING
#  (SNAP), INTERNATIONAL ARCTIC RESEARCH CENTER (IARC), UNIVERSITY OF 
#  ALASKA FAIRBANKS.
# # # # # 

import os, sys, rasterio, fiona
from rasterio import features
from rasterio.warp import RESAMPLING, reproject
import numpy as np
import scipy as sp

# import my library of functions
os.chdir( '/workspace/Shared/Tech_Projects/AK_LandCarbon/project_data/CODE' )
from final_v2_library import *

file_path = '/workspace/Shared/Tech_Projects/AK_LandCarbon/project_data/input_data/KodiakIsland'
output_path = '/workspace/Shared/Tech_Projects/AK_LandCarbon/project_data/output_data/data/V4'
landcover = rasterio.open( os.path.join( file_path,'ak_nlcd_2001_land_cover_3130_KodiakIsland_3338.tif' ), crs={'init':'EPSG:3338'} )
meta = landcover.meta

# PRE-PROCESS:
# saltwater
saltwater = fiona.open( '/workspace/Shared/Tech_Projects/AK_LandCarbon/project_data/input_data/Frances_ExtendedShoreline_060914/AKNPLCC_Saltwater_with_Kodiak.shp' )

# set the crs to the correct one.  There is some software of lib that we use in R that 
# has botched all of the coord systems for some reason.  This solves is and sets it at 
# the EPSG:3338 that is standard
crs = saltwater.crs # will be the base coordsys for this preprocessing
meta.update( crs=crs, dtype=rasterio.int32, compress='lzw' )
sw_raster = rasterio.open( os.path.join( output_path, 'rasterized', 'saltwater_kodiak.tif' ), 'w', **meta )

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

output_filename = os.path.join( output_path, 'intermediates', 'NLCD_land_cover_KodiakIsland_RCL.tif' )
# reclassify NLCD landcover raster
# the below reclass list is for converting from the NLCD over Kodiak to the classification devised by D.MCGUIRE Lab
reclass_list = [ [0, 1, 255],[11, 24, 1], [31, 32, 7], [41, 42, 9], [42, 43, 2], [51, 52, 8], [52, 53, 9], \
					[71, 73, 10], [90, 91, 3], [95, 96, 4] ] 
landcover_rcl = reclassify( landcover, reclass_list, output_filename, band=1 )

# remove the saltwater from the resulting raster
# this is currently incorrect, but is a perfect base case for developing the new code.
#  reclassify erroneous values in Saltwater
sw_raster = rasterio.open( os.path.join( output_path, 'rasterized', 'saltwater_kodiak.tif' ) )
output_filename = os.path.join( output_path, 'LandCarbon_Vegetation_KodiakIsland_30m_v0_1.tif' )
sw_removed = overlay_modify( landcover_rcl, sw_raster, in_cover_values=[1], out_cover_values=[17], \
				output_filename=output_filename, rst_base_band=1, rst_cover_band=1 )
sw_removed.close()

# resampling to the 1km grid 
output_filename = os.path.join( output_path, 'LandCarbon_Vegetation_KodiakIsland_1km_v0_1.tif' )

if os.path.exists( output_filename ):
	os.remove( output_filename )

# this is the regridding fix I am using currently. It is not perfect and a band-aid fix but it works correctly for now
command = 'gdalwarp -tr 1000 1000 -r near '+ sw_removed.name + ' ' + output_filename
os.system( command )

print('reclassification complete.')

