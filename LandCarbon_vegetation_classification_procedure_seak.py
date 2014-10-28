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
meta_updater = dict( driver='GTiff', dtype=rasterio.int16, compress='lzw', crs={'init':'EPSG:3338'}, count=1, nodata=None )

# set up some ouput sub-dirs for the intermediates and the rasterized
intermediate_path = os.path.join( output_path, 'intermediates' )
rasterized_path = os.path.join( output_path, 'rasterized' )
# parent
if not os.path.exists( output_path ):
	os.mkdir( output_path )
# subs
if not os.path.exists( intermediate_path ):
	os.mkdir( intermediate_path )
if not os.path.exists( rasterized_path ):
	os.mkdir( rasterized_path )

# bring in the multibanded prepped file
#  >>> current layer order is: saltwater, tnf_covertype, seak_2ndGrowth
ancillary_prepped = rasterio.open( os.path.join( rasterized_path, 'LandCarbon_vegetation_classification_ancillary_' + version_num + '.tif' ) )

meta = ancillary_prepped.meta # get the meta information from the master_raster
meta.update( meta_updater )

# reclassify NLCD 2001 Canopy 
canopy = rasterio.open( os.path.join( input_path, 'NLCD_canopy_AKNPLCC.tif' ) )
output_filename = os.path.join( intermediate_path, 'NLCD_canopy_AKNPLCC_RCL.tif' )
reclass_list = [ [0, 20, 1],
				 [20, 101, 2] ]
canopy_rcl = reclassify( canopy, reclass_list, output_filename, band=1 )
canopy.close()

# reclassify the NLCD 2001 Land Cover
landcover = rasterio.open( os.path.join( input_path, 'NLCD_land_cover_AKNPLCC.tif' ) )
output_filename = os.path.join( intermediate_path, 'NLCD_land_cover_AKNPLCC_RCL.tif' )
reclass_list = [ [0, 1, 255],
				 [21, 32, 22],
				 [11, 12, 20],
				 [12, 13, 21],
				 [41, 42, 3],
				 [42, 43, 2],
				 [43, 73, 3],
				 [90, 96, 3],
				 [81, 83, 5] ]
landcover_rcl = reclassify( landcover, reclass_list, output_filename, band=1 )
# create some helper classes of nodata and noveg for later overlays
landcover_arr = landcover_rcl.read_band( 1 ) # get the reclassed landcover array
# close it temporarily
landcover_rcl.close()

# make some masks and pass into a banded mask image
output_filename = os.path.join( intermediate_path, 'mask_nodata_noveg_seak.tif' )
mask_meta = meta
mask_meta.update( meta_updater )
mask_meta.update( count=2 )
mask_notmodeled = rasterio.open( output_filename, mode='w', **mask_meta )
# make a noveg
no_veg = np.logical_and( landcover_arr > 20, landcover_arr < 255 ).astype( np.int16 )
mask_notmodeled.write_band( 1, no_veg )
# make a nodata
no_data = ( landcover_arr == 20 ).astype( np.int16 )
mask_notmodeled.write_band( 2, no_data )
mask_notmodeled.close()

del no_veg, no_data

# collapse the out of bounds and nodata pixels we pulled out into a temporary 1 (noveg) class
landcover_arr[ np.logical_and( landcover_arr >= 20, landcover_arr < 255 ) ] = 1
landcover_rcl = rasterio.open( landcover_rcl.name, mode='r+' )
landcover_rcl.write_band( 1, landcover_arr )
# [NeedsSolving] close and open the file due to weirdness in losing the blocking information
landcover_rcl.close()
landcover_rcl = rasterio.open( landcover_rcl.name )

# combine the above nlcd landcover and canopy reclassified rasters
output_filename = os.path.join( intermediate_path, 'nlcd_landcover_canopy_combined.tif' )
# combine_list = [[255,1,255],[255,2,255],[2,1,3],[2,2,4],[3,1,5],[3,2,6],[5,1,7],[5,2,8],[0,1,255]] # trying the old line below and seeing if it will cut the mustard
combine_list = [[1,1,1],[1,2,2],[2,1,3],[2,2,4],[3,1,5],[3,2,6],[5,1,7],[5,2,8]] # this is the error line.  figure it out.
combined = combine( landcover_rcl, canopy_rcl, combine_list, output_filename )

# reclassify the above combined raster
output_filename = os.path.join( intermediate_path, 'combined_NLCD_RCL.tif' )
reclass_list = [ [4,5,2],[3,4,4],[6,7,3],[5,6,4],[7,9,5],[0,1,255] ]
combined_rcl = reclassify( combined, reclass_list, output_filename, band=1 )

# we are going to hold this one until we need it later when we are adding back in the nodata / no veg difference.  VERY IMPORTANT!
# combined_rcl_breakout = breakout( combined_rcl, os.path.join( rasterized_path, 'NLCD_land_cover_AKNPLCC_RCL_breakout.tif' ) )

# overlay with the TNF Cover Type
output_filename = os.path.join( intermediate_path, 'overlay_combinercl_ctraster.tif' )
tnf_cover_added = overlay_modify( combined_rcl, ancillary_prepped, in_cover_values=[5,6], 
									out_cover_values=[5,6], output_filename=output_filename, 
									rst_base_band=1, rst_cover_band=2 ) # band 2 is the tnf_covertype


# we also need to solve an issue where the pixels with values not upland coincident
#  with the harvest to upland. -- SEAK_2ndGrowth = SEAK_2ndGrowth_noveg
output_filename = os.path.join( intermediate_path, 'second_growth_removed_seak.tif' )
tnf_ct_band = tnf_cover_added.read_band(1)

second_growth_band = ancillary_prepped.read_band( 3 ) # band 3 is the covertype raster
tnf_ct_copy = np.copy( tnf_ct_band )
tnf_ct_copy[ np.logical_and( tnf_ct_band < 6, second_growth_band > 0 )] = 2 # convert harvested area to upland

meta.update( meta_updater )
second_growth_removed = rasterio.open( output_filename, mode='w', **meta )
tnf_ct_copy = tnf_ct_copy.astype( rasterio.int16 )
second_growth_removed.write_band( 1, tnf_ct_copy )
second_growth_removed.close()

second_growth_removed = rasterio.open( second_growth_removed.name )
# reclassify 'erroneous' values in Saltwater 
output_filename = os.path.join( intermediate_path, 'saltwater_added_seak.tif' ) 
sw_added = overlay_cover( second_growth_removed, ancillary_prepped, in_cover_value=1, out_cover_value=17, \
							output_filename=output_filename, rst_base_band=1, rst_cover_band=1 ) # band 1 is the saltwater raster


sw_added_arr = sw_added.read_band( 1 )
second_growth_removed.close()
sw_added.close()
del second_growth_removed, sw_added

output_filename = os.path.join( output_path, 'LandCarbon_MaritimeVegetation_SC_SEAK_30m_'+ version_num +'.tif' ) 
no_veg_fix = rasterio.open( output_filename, mode='w', **meta )

# lets add back in the noveg and oob data values
# noveg
mask_notmodeled = rasterio.open( mask_notmodeled.name ) # noveg is band 1 nodata is band 2
no_veg = mask_notmodeled.read_band( 1 )
sw_added_arr[ no_veg == 1 ] = 1 # give no veg the value 1
del no_veg
# nodata
# sw_added_arr[ np.logical_and( no_data == 1, sw_added_arr ] = 255 # give the no data the value 255

# create a mask of the areas of data to nodata in the NLCD rasters from FRANCES BILES
arr  = landcover.read_band( 1 ).astype( np.int16 )
arr[ arr == 255 ] = 0
arr[ arr != 0 ] = 1

nlcd_mask = rasterio.open( os.path.join( intermediate_path, 'nlcd_mask.tif' ), mode='w',  **meta )
nlcd_mask.write_band( 1, arr )
nlcd_mask.close()

# now convert all of the 255 values in the mask (open terrestrial water bodies) to no veg (1)
sw_added_arr[ np.logical_and( arr == 1, sw_added_arr == 255) ] = 1

no_veg_fix.write_band( 1, sw_added_arr )
no_veg_fix.close()
