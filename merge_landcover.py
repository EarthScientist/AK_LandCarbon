import os, sys, re
import rasterio

# import my library of functions
os.chdir( '/workspace/Shared/Tech_Projects/AK_LandCarbon/project_data/CODE' )
from final_v2_library import *

output_path = '/workspace/Shared/Tech_Projects/AK_LandCarbon/project_data/output_data/data/V3'

kodiak_30m = os.path.join( output_path, 'LandCarbon_Vegetation_KodiakIsland_30m_v0_1.tif' ) # '/workspace/Shared/Tech_Projects/AK_LandCarbon/project_data/output_data/data/V3/LandCarbon_LandCover_KodiakIsland.tif'
kodiak_1km = os.path.join( output_path, 'LandCarbon_Vegetation_KodiakIsland_1km_v0_1.tif' )
seak_30m = os.path.join( output_path, 'LandCarbon_Vegetation_SC_SEAK_30m_v0_1.tif' ) # '/workspace/Shared/Tech_Projects/AK_LandCarbon/project_data/output_data/data/V3/LandCarbon_LandCover_SC_SEAK.tif'
seak_1km = os.path.join( output_path, 'LandCarbon_Vegetation_SC_SEAK_1km_v0_1.tif' )
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

# # # # # #
# common dtypes
kodiak_30m_rst = rasterio.open( kodiak_30m ) # these are currently for test purposes
kodiak_1km_rst = rasterio.open( kodiak_1km )
seak_30m_rst = rasterio.open( seak_30m ) # these are currently for test purposes
seak_1km_rst = rasterio.open( seak_1km )
akcan_rst = rasterio.open( akcan ) # this is an *only* 1km product
# output_filename = seak_rst.name.replace( '.tif', '_dtype_mod.tif' )
# seak_mod = modify_dtype( seak_rst, output_filename, rasterio_dtype=rasterio.uint8, band=1 )


# # # # # # # 
# # run the merge to the SC/SEAK and Kodiak Extent and classification at 30m native NLCD resolution
# # # # # # #
# change saltwater to noveg
kodiak_30m_arr = kodiak_30m_rst.read_band( 1 )
kodiak_30m_arr[ kodiak_30m_arr == 17 ] = 0

# generate a new raster
meta = kodiak_30m_rst.meta 
meta.update( compress='lzw' )

output_filename = kodiak_30m_rst.name.replace( '.tif', '_rcl.tif' )
kodiak_30m_rcl = rasterio.open( output_filename, mode='w', **meta )

kodiak_30m_rcl.write_band( 1, kodiak_30m_arr )
kodiak_30m_rcl.close()

# now run the actual mosaicking at the 30m resolution
output_filename = os.path.join( output_path, 'LandCarbon_Vegetation_30m_full_v0_1.tif' )
if os.path.exists( output_filename ):
	os.remove( output_filename )

driver = 'GTiff'

command = 'gdal_merge.py -o ' + \
		output_filename + \
		' -of ' + driver + \
		' -co "COMPRESS=LZW" ' + \
		'-ps 30 30 -v ' + \
		'-n 255 ' + ' ' + \
		seak_30m + ' ' + kodiak_30m_rcl.name

os.system( command )


# # # # # # # 
# # run the merge to the SC/SEAK and Kodiak Extent and classification to 1km resolution for IEM integration
# # # # # # #

kodiak_1km_arr = kodiak_1km_rst.read_band( 1 )
kodiak_1km_arr[ kodiak_1km_arr == 17 ] = 0

# generate a new raster
meta = kodiak_1km_rst.meta 
meta.update( compress='lzw' )

output_filename = kodiak_1km_rst.name.replace( '.tif', '_rcl.tif' )
kodiak_1km_rcl = rasterio.open( output_filename, mode='w', **meta )

kodiak_1km_rcl.write_band( 1, kodiak_1km_arr )
kodiak_1km_rcl.close()

# now run the actual mosaicking at the 1km resolution
output_filename = os.path.join( output_path, 'LandCarbon_Vegetation_1km_full_v0_1.tif' )
if os.path.exists( output_filename ):
	os.remove( output_filename )

driver = 'GTiff'

command = 'gdal_merge.py -o ' + \
		output_filename + \
		' -of ' + driver + \
		' -co "COMPRESS=LZW" ' + \
		'-ps 1000 1000 -v ' + \
		'-n 255 ' + ' ' + \
		seak_1km + ' ' + kodiak_1km_rcl.name

os.system( command )


# # # # # # #
# # create an intermediary SC/SEAK extent classification with the full extent classification for visualization
# # # # # # #
#  seak reclass 
output_filename = seak_1km_rst.name.replace('.tif', '_rcl_fullclass.tif')
reclass_list = [[0,1,255],[1,2,17],[2,3,10],[3,4,11],[4,5,12],[5,6,13],[6,7,14],[8,9,4],[9,10,15],[7,8,9],[10,11,5]]
seak_1km_rcl = reclassify( seak_1km_rst, reclass_list, output_filename, band=1 )

#  kodiak reclass
output_filename = kodiak_1km_rst.name.replace('.tif', '_rcl_fullclass.tif')
reclass_list = [[0,1,255],[1,2,17],[2,3,10],[3,4,11],[4,5,12],[5,6,13],[6,7,14],[8,9,4],[9,10,15],[7,8,9],[10,11,5]]
kodiak_1km_rcl = reclassify( kodiak_1km_rst, reclass_list, output_filename, band=1 )

output_1km_filename = os.path.join( output_path, 'LandCarbon_Vegetation_1km_full_v0_1_fullclassification.tif' )

if os.path.exists( output_filename ):
	os.remove( output_filename )

driver = 'GTiff'

command = 'gdal_merge.py -o ' + \
		output_filename + \
		' -of ' + driver + \
		' -co "COMPRESS=LZW" ' + \
		'-ps 1000 1000 -v ' + \
		'-n 255 ' + \
		seak_1km_rcl.name + ' ' + kodiak_1km_rcl.name

os.system( command )



# # # # # #
# run the merge to the full AK_Canada Extent and classification
# # # # # #
# image reclassifications
#  akcan reclass
output_filename = os.path.join(output_path, os.path.basename(akcan_rst.name).replace('.tif', '_rcl_full.tif') )
reclass_list = [[0,1,16]] # good
akcan_rcl = reclassify( akcan_rst, reclass_list, output_filename, band=1 )
# mask out Kodiak Island 
kodiak_mask_path = '/workspace/Shared/Tech_Projects/AK_LandCarbon/project_data/input_data/merge_seak_mask/kodiak_mask.tif'
kodiak_mask = rasterio.open( kodiak_mask_path )
kodiak_mask_arr = kodiak_mask.read_band( 1 )
akcan_rcl_arr = akcan_rcl.read_band( 1 )
akcan_rcl_arr[ kodiak_mask_arr == 1 ] = 255

# generate a new output file to place the modified outputs in mode='w'
meta = akcan_rcl.meta
meta.update( compress='lzw' )
output_filename = os.path.join(output_path, os.path.basename(akcan_rst.name).replace('.tif', '_rcl_full_kodiakmasked.tif') )
akcan_rcl_final = rasterio.open( output_filename, mode='w', **meta )
akcan_rcl_final.write_band( 1, akcan_rcl_arr )
akcan_rcl_final.close()

# this was already done above...
#  seak 1km reclass 
# output_filename = seak_1km_rst.name.replace('.tif', '_rcl_full.tif')
# reclass_list = [[0,1,255],[1,2,17],[2,3,10],[3,4,11],[4,5,12],[5,6,13],[6,7,14],[8,9,4],[9,10,15],[7,8,9],[10,11,5]]
# seak_rcl = reclassify( seak_rst, reclass_list, output_filename, band=1 )
# seak_rcl.close()

#  kodiak 1km reclass
# output_filename = kodiak_1km_rst.name.replace('.tif', '_rcl_full.tif')
# reclass_list = [[0,1,255],[1,2,17],[2,3,10],[3,4,11],[4,5,12],[5,6,13],[6,7,14],[8,9,4],[9,10,15],[7,8,9],[10,11,5]]
# kodiak_rcl = reclassify( kodiak_rst, reclass_list, output_filename, band=1 )
# kodiak_rcl.close()

output_filename = os.path.join( output_path, 'IEM_LandCarbon_Vegetation_FullExtent_1km_Step1.tif' )
if os.path.exists( output_filename ):
	os.remove( output_filename )

driver = 'GTiff'

command = 'gdal_merge.py -o ' + \
		output_filename + \
		' -of ' + driver + \
		' -co "COMPRESS=LZW" ' + \
		'-ps 1000 1000 -v ' + \
		'-n 255 ' + \
		kodiak_1km_rcl.name + ' ' + akcan_rcl_final.name + ' ' + seak_1km_rcl.name

os.system( command )


# # This is what seems to be the way to do it
# create a mask of the areas of data to nodata in the NLCD from FRANCES
nlcd = rasterio.open('/workspace/Shared/Tech_Projects/AK_LandCarbon/project_data/input_data/From_Frances_Extracted/NLCD_land_cover_AKNPLCC.tif')
arr  = nlcd.read_band(1)
arr[ np.logical_or( arr != 0, arr != 255 ) ] = 1
arr[ np.logical_and( arr == 0, arr == 255 ) ] = 0

meta = nlcd.meta
meta.update( compress='lzw' )

nlcd_new = rasterio.open( '/workspace/Shared/Tech_Projects/AK_LandCarbon/project_data/output_data/data/V3/nlcd_mask.tif', mode='w',  **meta )
nlcd_new.write_band( 1, arr )
nlcd_new.close()

full_ext_filename = os.path.join( output_path, 'IEM_LandCarbon_Vegetation_FullExtent_1km_Step1.tif' )
final = rasterio.open( full_ext_filename )
meta = final.meta
meta.update( compress='lzw' )

full_new_filename = os.path.join( output_path, 'IEM_LandCarbon_Vegetation_1km_FullExtent_Step2.tif' )
final_new = rasterio.open( full_new_filename, mode='w', **meta )


# not sure what this even is...
# output_filename = '/workspace/Shared/Tech_Projects/AK_LandCarbon/project_data/output_data/data/V3/nlcd_mask_1km.tif'
# if os.path.exists( output_filename ):
# 	os.remove( output_filename )
# os.system( 'gdalwarp -ot Byte -of GTiff -co "COMPRESS=LZW" -tr 1000 1000 -s_srs "EPSG:3338" -t_srs "EPSG:3338"  /workspace/Shared/Tech_Projects/AK_LandCarbon/project_data/output_data/data/V3/nlcd_mask.tif ' + output_filename )


# Merged together the Kodiak Mask and the SC/SEAK nlcd mask just created using QGIS merge
mask_filename = '/workspace/Shared/Tech_Projects/AK_LandCarbon/project_data/input_data/merge_seak_mask/SEAK_KODIAK_MASK_FullExtent.tif'

nlcd_1k = rasterio.open( mask_filename )

new_arr = nlcd_1k.read_band( 1 )
final_arr = final.read_band( 1 )
final_new.write_band( 1, final_arr )

window = bounds_to_window( final_new.transform, nlcd_1k.bounds )

final_new_arr = final_new.read_band( 1, window=window )
final_new_arr[np.logical_and(final_new_arr == 8, new_arr == 1)] = 16
final_new.write_band( 1, final_new_arr, window=window)
final_new.close()


# Now we must modify the pixels of the new map that are value 17 to 255 (out of bounds),
#  then we must modify all pixels of the new map that are 0 to 255 (out of bounds),
#  THEN finally we must change all the values of 16 to 0 (no veg).

#  final reclass
final_rst = rasterio.open( final_new.name )
output_filename = os.path.join( output_path, 'IEM_LandCarbon_Vegetation_v0_1_fullextent.tif' )
reclass_list = [[17,18,0],[0,1,255],[16,17,0]]
final_rcl = reclassify( final_rst, reclass_list, output_filename, band=1 )
final_rcl.close()

# now we need to crop the data and mask it to the extent of the IEM DOMAIN based on the old Landcover Map
iem_lc = rasterio.open('/workspace/Shared/Tech_Projects/Alaska_IEM/project_data/LandCover_iem_2005.tif')

# return the array and modify the values to a boolean mask
# 255 is the OOB value all others are desired.
iem_arr = iem_lc.read_band(1)
iem_arr[ iem_arr != 255 ] = 1
iem_arr[ iem_arr != 1 ] = 0

meta = iem_lc.meta
meta.update(compress='lzw')
iem_mask = rasterio.open( '/workspace/Shared/Tech_Projects/AK_LandCarbon/project_data/input_data/merge_seak_mask/IEM_Mask.tif', mode='w', **meta )
iem_mask.write_band( 1, iem_arr )
iem_mask.close()

# crop it
final_veg = rasterio.open( os.path.join( output_path, 'IEM_LandCarbon_Vegetation_v0_1_fullextent.tif' ) )
iem_mask = rasterio.open( iem_mask.name )
window = bounds_to_window( final_veg.transform, iem_mask.bounds )

# read it
final_veg_arr = final_veg.read_band( 1, window=window )
iem_mask_arr = iem_mask.read_band( 1 )

# mask it
final_veg_arr[ iem_mask_arr != 1 ] = 255

# new output ds based on the mask meta
meta = iem_mask.meta
meta.update( compress = 'lzw' )

output_filename = os.path.join( output_path, 'IEM_LandCarbon_Vegetation_v0_1.tif')
if os.path.exists( output_filename ):
	os.remove( output_filename )

# write it out
output_final_veg = rasterio.open( output_filename, mode='w', **meta )

output_final_veg.write_band( 1, final_veg_arr.astype( rasterio.uint8 ) )
output_final_veg.close()


