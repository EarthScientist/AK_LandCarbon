# # # # # # # 
# LandCarbon LandCover SEAK Classification PROCEDURE version 2.0
import pprint
import os, sys, rasterio, fiona
from rasterio import features
from rasterio.warp import reproject, RESAMPLING
import numpy as np
import scipy as sp

# import my library of functions
os.chdir( '/workspace/Shared/Tech_Projects/AK_LandCarbon/project_data/CODE' )
from final_v2_library import *

# some initial setup
file_path = '/workspace/Shared/Tech_Projects/AK_LandCarbon/project_data/input_data/From_Frances_Extracted'
output_path = '/workspace/Shared/Tech_Projects/AK_LandCarbon/project_data/output_data/data/V4'
master_raster = rasterio.open( os.path.join( file_path,'NLCD_canopy_AKNPLCC.tif' ) )
meta = master_raster.meta
meta.update( dtype=rasterio.int32, compress='lzw' )
master_raster.close()
del master_raster

# set up some ouput sub-dirs for the intermediates and the rasterized
intermediate_path = os.path.join( output_path, 'intermediates' )
rasterized_path = os.path.join( output_path, 'rasterized' )
if not os.path.exists( intermediate_path ):
	os.mkdir( intermediate_path )

if not os.path.exists( rasterized_path ):
	os.mkdir( rasterized_path )


# # # # # # # # # 
# BEGIN RECLASSIFICATION PROCEDURE:
## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## 

# step 3 reclassify NLCD Canopy raster
canopy = rasterio.open( os.path.join( file_path, 'NLCD_canopy_AKNPLCC.tif' ) )
output_filename = os.path.join( intermediate_path, 'NLCD_canopy_AKNPLCC_RCL.tif' )
reclass_list = [[1, 20, 1],[20, 101, 2]]
canopy_rcl = reclassify( canopy, reclass_list, output_filename, band=1 )

## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## 

# step 4 reclassify NLCD raster
landcover = rasterio.open( os.path.join( file_path, 'NLCD_land_cover_AKNPLCC.tif' ) )
output_filename = os.path.join( intermediate_path, 'NLCD_land_cover_AKNPLCC_RCL.tif' )
reclass_list = [[0,1,255],[1, 32, 1],[42, 43, 2],[41, 42, 3],[43, 73, 3],[90, 96, 3], [81, 83, 5]]
landcover_rcl = reclassify( landcover, reclass_list, output_filename, band=1 )

## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## 

# step 5 combine the above reclassed rasters
output_filename = os.path.join( intermediate_path, 'nlcd_landcover_canopy_combined.tif' )
combine_list = [[1,1,1],[1,2,2],[2,1,3],[2,2,4],[3,1,5],[3,2,6],[5,1,7],[5,2,8]]
combined = combine( landcover_rcl, canopy_rcl, combine_list, output_filename )

## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## 

# step 6 reclassify the above combined map
output_filename = os.path.join( intermediate_path, 'combined_NLCD_RCL.tif' )
reclass_list = [[1,3,1],[3,4,4],[4,5,2],[5,6,4],[6,7,3],[7,9,5]]
combined_rcl = reclassify( combined, reclass_list, output_filename, band=1 )

## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## 

# step 8 
# overlay with the TNF Cover Type
ct_raster = rasterio.open( os.path.join( rasterized_path, 'tnf_covertype_seak.tif') )
output_filename = os.path.join( intermediate_path, 'overlay_combinercl_ctraster.tif' )
tnf_cover_added = overlay_modify( combined_rcl, ct_raster, in_cover_values=[5,6], 
									out_cover_values=[5,6], output_filename=output_filename, 
									rst_base_band=1, rst_cover_band=1 )

## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## 
# we also need to solve an issue where the pixels with values not upland coincident
#  with the harvest to upland.
# SEAK_2ndGrowth = SEAK_2ndGrowth_noveg
output_filename = os.path.join( intermediate_path, 'seak2nd_growth_removed_seak.tif' )
tnf_ct_band = tnf_cover_added.read_band(1)
s2_raster = rasterio.open( os.path.join( rasterized_path, 'seak2nd_growth_seak.tif') )
s2_band = s2_raster.read_band(1)
tnf_ct_copy = np.copy( tnf_ct_band )
tnf_ct_copy[ np.logical_and( np.logical_or(tnf_ct_band > 1, tnf_ct_band < 5 ), \
		s2_band > 0 )] = 2 # convert harvested area to upland
s2_removed = rasterio.open( output_filename, mode='w', **meta )
tnf_ct_copy = tnf_ct_copy.astype( rasterio.int32 )
s2_removed.write_band( 1, tnf_ct_copy )
s2_removed.close()

## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## 

# ** Changed to final step prior to resampling. **
#  reclassify erroneous values in Saltwater
output_filename = os.path.join( output_path, 'LandCarbon_Vegetation_SC_SEAK_30m_v0_1.tif' ) 
s2_removed = rasterio.open( os.path.join( intermediate_path, 'seak2nd_growth_removed_seak.tif' ) )
sw_raster = rasterio.open( os.path.join( rasterized_path, 'saltwater_seak.tif' ) )
sw_added = overlay_cover( s2_removed, sw_raster, in_cover_value=1, out_cover_value=17, \
							output_filename=output_filename, rst_base_band=1, rst_cover_band=1 )
sw_added.close()

## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## 

output_filename = os.path.join( output_path, 'LandCarbon_Vegetation_SC_SEAK_1km_v0_1.tif' )

# TEMPORARY FIX FOR resampling
if os.path.exists( output_filename ):
	os.remove( output_filename )

# this is the regridding fix I am using currently.  It is not perfect and a band-aid fix but it works correctly for now
command = 'gdalwarp -tr 1000 1000 -r near '+ sw_added.name + ' ' + output_filename
os.system( command )

print('reclassification complete.')



