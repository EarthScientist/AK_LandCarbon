import os, sys, re
import rasterio

# import my library of functions
os.chdir( '/workspace/Shared/Tech_Projects/AK_LandCarbon/project_data/CODE' )
from final_v2_library import *

kodiak = '/workspace/Shared/Tech_Projects/AK_LandCarbon/project_data/output_data/data/V3/LandCarbon_LandCover_KodiakIsland.tif'
seak = '/workspace/Shared/Tech_Projects/AK_LandCarbon/project_data/output_data/data/V3/LandCarbon_LandCover_SEAK_v3.tif'
akcan = '/Data/Base_Data/ALFRESCO_formatted/ALFRESCO_Master_Dataset/ALFRESCO_Model_Input_Datasets/AK_CAN_Inputs/Landcover/LandCover_alf_2005.tif'

# modify dtype raster band
def modify_dtype( in_rasterio_rst, output_filename, rasterio_dtype=rasterio.float32, band=1 ):
	'''
	this function will modify the raster dtype on copy
	to a new dataset.


	'''
	arr = in_rasterio_rst.read_band( band )
	arr = arr.astype( rasterio_dtype )
	meta = in_rasterio_rst.meta
	meta.update( dtype = rasterio_dtype )
	out = rasterio.open( output_filename, mode='w', **meta ) 
	out.write_band( band, arr )
	return out

# we are going to need to open these files and do some reclassing into a 
#  common full reclassification list for all the new classes.

# # # # # #
# common dtypes
kodiak_rst = rasterio.open( kodiak )
seak_rst = rasterio.open( seak )
akcan_rst = rasterio.open( akcan )
output_filename = seak_rst.name.replace( '.tif', '_dtype_mod.tif' )
seak_mod = modify_dtype( seak_rst, output_filename, rasterio_dtype=rasterio.uint8, band=1 )


# # # # # # 
# run the merge to the SC/SEAK and Kodiak Extent and classification
# # # # # #

output_filename = '/workspace/Shared/Tech_Projects/AK_LandCarbon/project_data/output_data/data/V3/LandCarbon_LandCover_SEAKExtent.tif'
if os.path.exists( output_filename ):
	os.remove( output_filename )

driver = 'GTiff'

command = 'gdal_merge.py -o ' + \
		output_filename + \
		' -of ' + driver + \
		' -co "COMPRESS=LZW" ' + \
		'-ps 1000 1000 -v ' + \
		'-n 0 ' + ' ' + \
		seak + ' ' + kodiak

os.system( command )


# # # # # #
# run the merge to the full AK_Canada Extent and classification
# # # # # #
# image reclassifications
#  akcan reclass
# output_filename = akcan_rst.name.replace('.tif', '_rcl_full.tif')
# reclass_list = [[,,],[,,],[,,],[,,],[,,]]
# akcan_rcl = reclassify( , reclass_list, output_filename, band=1 )

#  seak reclass 
output_filename = seak_rst.name.replace('.tif', '_rcl_full.tif')
reclass_list = [[1,2,0],[2,3,10],[3,4,11],[4,5,12],[5,6,13],[6,7,14],[8,9,4],[9,10,15],[7,8,9],[10,11,5]]
seak_rcl = reclassify( seak_rst, reclass_list, output_filename, band=1 )

#  kodiak reclass
output_filename = kodiak_rst.name.replace('.tif', '_rcl_full.tif')
reclass_list = [[1,2,0],[2,3,10],[3,4,11],[4,5,12],[5,6,13],[6,7,14],[8,9,4],[9,10,15],[7,8,9],[10,11,5]]
kodiak_rcl = reclassify( kodiak_rst, reclass_list, output_filename, band=1 )

output_filename = '/workspace/Shared/Tech_Projects/AK_LandCarbon/project_data/output_data/data/V3/LandCarbon_LandCover_FullExtent.tif'
if os.path.exists( output_filename ):
	os.remove( output_filename )

driver = 'GTiff'

command = 'gdal_merge.py -o ' + \
		output_filename + \
		' -of ' + driver + \
		' -co "COMPRESS=LZW" ' + \
		'-ps 1000 1000 -v ' + \
		'-n 0 ' + \
		akcan + ' ' + seak + ' ' + kodiak

os.system( command )


