# KODIAK ISLAND NLCD RECLASSIFICATION BASED ON A CROSS-WALK PROPOSED BY 
#  DAVE McGUIRE & THE SPATIAL ECOLOGY LAB (SEL) FOR USE IN THE ALASKA
#  LANDCARBON PROJECT.
#
# CODE DEVELOPED BY: MICHAEL LINDGREN (malindgren@alaska.edu), SENIOR 
#  SPATIAL ANALYST AT SCENARIOS NETWORK FOR ALASKA & ARCTIC PLANNING
#  (SNAP), INTERNATIONAL ARCTIC RESEARCH CENTER (IARC), UNIVERSITY OF 
#  ALASKA FAIRBANKS.
## ## ## ## ## ##
# 	NLCD Type                          TEM Parameterization
# 	-------------------------------    -------------------------------------------------
# 	11 Open Water                       No Veg/Not Modeled
# 	12 Perennial ic e/snow               No Veg/Not Modeled
# 	22 Developed, Low Intensity         No Veg/Not Modeled
# 	23 Developed, Medium intensity      No Veg/Not Modeled
# 	31 Barren Land                      Heath
# 	41 Deciduous Forest                 Alder (note that sum of grids from 41 and 52 below match the sum from shrub in NALCMS)
# 	42 Evergreen Forest                 Upland Forest (similar to southeast and southcentral)
# 	51 Dwarf Shrub                      Shrub tundra
# 	52 Shrub/Scrub                      Alder
# 	71 Grassland/Herbaceous             Graminoid Tundra
# 	72 Sedge/Herbaceous                 Graminoid Tundra
# 	90 Woody Wetland                    Forested Wetland ( similar to southeast and southcentral )
# 	95 Emergent Herbaceous Wetlands     Fens ( similar to southeast and southcentral )

# # # # # 

import os, sys, rasterio, fiona
from rasterio import features
from rasterio.warp import RESAMPLING, reproject
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

# set up some ouput sub-dirs for the intermediates and the rasterized
intermediate_path = os.path.join( output_path, 'intermediates' )
rasterized_path = os.path.join( output_path, 'rasterized' )
if not os.path.exists( intermediate_path ):
	os.mkdir( intermediate_path )

if not os.path.exists( rasterized_path ):
	os.mkdir( rasterized_path )

lc_path = os.path.join( input_path, 'KodiakIsland','ak_nlcd_2001_land_cover_3130_KodiakIsland_3338.tif' ) 
landcover = rasterio.open( lc_path )

output_filename = os.path.join( intermediate_path, 'NLCD_land_cover_KodiakIsland_RCL.tif' )

# reclassify NLCD landcover raster
# the below reclass list is for converting from the NLCD over Kodiak to the classification devised by D.MCGUIRE Lab
reclass_list = [ [0, 1, 255],[11, 24, 1], [31, 32, 7], \
				 [41, 42, 9], [42, 43, 2], [51, 52, 8], \
				 [52, 53, 9], [71, 73, 10], [90, 91, 3], \
				 [95, 96, 4] ] 

landcover_rcl = reclassify( landcover, reclass_list, output_filename, band=1 )

# remove the saltwater from the resulting raster
# this is currently incorrect, but is a perfect base case for developing the new code.
#  reclassify erroneous values in Saltwater
sw_raster = rasterio.open( os.path.join( rasterized_path, 'saltwater_kodiak.tif' ) )
output_filename = os.path.join( output_path, 'LandCarbon_CoastalVegetation_KodiakIsland_30m_' + version_num + '.tif' )
sw_removed = overlay_modify( landcover_rcl, sw_raster, in_cover_values=[1], out_cover_values=[17], \
				output_filename=output_filename, rst_base_band=1, rst_cover_band=1 )
sw_removed.close()

# # resampling to the 1km grid 
# output_filename = os.path.join( output_path, 'LandCarbon_CoastalVegetation_KodiakIsland_1km_' + version_num + '.tif' )

# if os.path.exists( output_filename ):
# 	os.remove( output_filename )

# # this is the regridding fix I am using currently. It is not perfect and a band-aid fix but it works correctly for now
# command = 'gdalwarp -tr 1000 1000 -r near -srcnodata None -dstnodata None -multi '+ sw_removed.name + ' ' + output_filename
# os.system( command )

print('reclassification complete.')

