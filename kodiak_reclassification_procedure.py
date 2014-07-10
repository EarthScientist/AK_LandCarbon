# KODIAK ISLAND NLCD RECLASSIFICATION BASED ON A CROSS-WALK PROPOSED BY 
#  DAVE McGUIRE & THE SPATIAL ECOLOGY LAB (SEL) FOR USE IN THE ALASKA
#  LANDCARBON PROJECT.
#
# CODE DEVELOPED BY: MICHAEL LINDGREN (malindgren@alaska.edu), SENIOR 
#  SPATIAL ANALYST AT SCENARIOS NETWORK FOR ALASKA & ARCTIC PLANNING
#  (SNAP), INTERNATIONAL ARCTIC RESEARCH CENTER (IARC), UNIVERSITY OF 
#  ALASKA FAIRBANKS.
# # # # # 

import pprint
import os, sys, rasterio, fiona
from rasterio import features
import numpy as np
import scipy as sp

file_path = '/workspace/Shared/Tech_Projects/AK_LandCarbon/project_data/input_data/From_Frances_Extracted'
output_path = '/workspace/Shared/Tech_Projects/AK_LandCarbon/project_data/output_data/data/V3'
master_raster = rasterio.open( os.path.join( file_path,'NLCD_canopy_AKNPLCC.tif' ) )
meta = master_raster.meta

# open the extent polygon encompassing Kodiak Island
full_extent_shape = fiona.open( '' )

saltwater = fiona.open( '/workspace/Shared/Tech_Projects/AK_LandCarbon/project_data/input_data/\
							Frances_ExtendedShoreline_060914/AKNPLCC_Saltwater_with_Kodiak.shp' )
# PRE-PROCESS:
# saltwater
saltwater = fiona.open( os.path.join( file_path,'AKNPLCC_Saltwater.shp' ) )

# set the crs to the correct one.  There is some software of lib that we use in R that 
# has botched all of the coord systems for some reason.  This solves is and sets it at 
# the EPSG:3338 that is standard
crs = saltwater.crs # will be the base coordsys for this preprocessing
meta.update( crs=crs )
meta.update( dtype=rasterio.int32 )
sw_raster = rasterio.open( os.path.join( output_path, 'saltwater_kodiak.tif' ), 'w', **meta )

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

# reclassify NLCD raster
landcover = rasterio.open( os.path.join( file_path, 'NLCD_land_cover_AKNPLCC.tif' ) )
output_filename = os.path.join( output_path, 'NLCD_land_cover_KodiakIsland_RCL.tif' )
# the below needs to be corrected...
reclass_list = [[0, 32, 1],[42, 43, 2],[41, 42, 3],[43, 73, 3],[90, 96, 3], [81, 83, 5]]
landcover_rcl = reclassify( landcover, reclass_list, output_filename, band=1 )

# remove the saltwater from the resulting raster
# this is currently incorrect, but is a perfect base case for developing the new code.
#  reclassify erroneous values in Saltwater
output_filename = os.path.join( output_path, 'remove_saltwater_version2.tif' )
base_rst = SEAK_2ndGrowth_upland
cover_rst = gdal.Open( os.path.join( file_path,'AKNPLCC_Saltwater.tif' ) )
cover_value = 1
out_cover_value = 1
sw_removed = overlay_modify( s2_removed, sw_raster, in_cover_values=[1], out_cover_values=[1], \
				output_filename=output_filename, rst_base_band=1, rst_cover_band=1 )


# resample the raster to 1km 

# output the raster and close all the file handles	
