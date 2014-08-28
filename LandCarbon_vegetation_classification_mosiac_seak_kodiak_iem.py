import os, sys, re, rasterio

# import my library of functions
os.chdir( '/workspace/Shared/Tech_Projects/AK_LandCarbon/project_data/CODE' )
from final_v2_library import *

version_num = 'v0_3'

output_path = '/workspace/Shared/Tech_Projects/AK_LandCarbon/project_data/output_data/data/V5'

# read in the combined SEAK / KODIAK map at 1km resolution:
seak_combined = os.path.join( output_path, 'LandCarbon_CoastalVegetation_1km_' + version_num + '.tif' )
seak_combined_rst = rasterio.open( seak_combined )
akcan = '/Data/Base_Data/ALFRESCO_formatted/ALFRESCO_Master_Dataset/ALFRESCO_Model_Input_Datasets/AK_CAN_Inputs/Landcover/LandCover_alf_2005.tif'
akcan_rst = rasterio.open( akcan ) # this is an *only* 1km product


# reclassify the seak_combined to the FULL IEM Domain LandCover Classification



def cover( large_rst, small_rst, large_rst_fill_vals, output_filename, band=1 ):
	'''
	function that will fill by covering over certain values in the map in a loop.

	[ MORE DOC TO COME ]
	
	'''
	window = bounds_to_window( large_rst.transform.to_gdal(), small_rst.bounds )
	large_arr_window = large_rst.read_band( band, window=window )
	small_arr = small_rst.read_band( band )
	for i in np.unique( small_arr ):
		for j in large_rst_fill_vals:
			large_arr_window[ np.logical_and( small_arr == i, large_arr_window == j ) ] = i
	meta = large_rst.meta
	meta.update( compress='lzw' )
	out = rasterio.open( output_filename, mode='w', **meta )
	large_arr = large_rst.read_band( 1 )
	out.write_band( band, large_arr )
	out.write_band( band, large_arr_window, window=window )
	return out


iem_landcarbon_final = cover(  akcan_rst, seak_combined_rst, [ 0,8,255 ], output_filename, band=1 )

iem_landcover_final.close()


