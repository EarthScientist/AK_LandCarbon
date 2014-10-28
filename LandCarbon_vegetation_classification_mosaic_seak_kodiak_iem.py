import os, sys, re, rasterio

# import my library of functions
os.chdir( '/workspace/Shared/Tech_Projects/AK_LandCarbon/project_data/CODE' )
from final_v2_library import *

version_num = 'v0_3'

input_path = '/workspace/Shared/Tech_Projects/AK_LandCarbon/project_data/input_data'
output_path = '/workspace/Shared/Tech_Projects/AK_LandCarbon/project_data/output_data/data/V7'
os.chdir( output_path )
meta_updater = dict( driver='GTiff', dtype=rasterio.uint8, compress='lzw', crs={'init':'EPSG:3338'}, count=1, nodata=None )

# read in the combined SEAK / KODIAK map at 1km resolution:
seak_combined = os.path.join( output_path, 'LandCarbon_MaritimeVegetation_1km_withSaltwater_' + version_num + '.tif' )
seak_combined_rst = rasterio.open( seak_combined )
akcan = '/Data/Base_Data/ALFRESCO_formatted/ALFRESCO_Master_Dataset/ALFRESCO_Model_Input_Datasets/AK_CAN_Inputs/Landcover/LandCover_alf_2005.tif'
akcan_rst = rasterio.open( akcan ) # this is an *only* 1km product

# reclassify the seak_combined to the FULL IEM Domain LandCover Classification
output_filename = os.path.join( output_path, 'LandCarbon_MaritimeVegetation_1km_iem_rcl_' + version_num + '.tif' )
reclass_list = [ [0,1,255],[1,2,0],[3,4,11],[4,5,12],[5,6,13],[6,7,14],[8,9,4],[9,10,15],[7,8,9],[10,11,5],[2,3,10],[17,18,16] ]
seak_1km_rcl = reclassify( seak_combined_rst, reclass_list, output_filename, band=1 )
seak_1km_rcl.close()

# re-open the file which flushed it to disk and open with read/write
seak_1km_rcl = rasterio.open( seak_1km_rcl.name, mode='r+' )
# iem_qml_sw = os.path.join( output_path, 'QGIS_STYLES', '' )
# ctable = qml_to_ctable( iem_qml_sw )
output_filename = os.path.join( output_path, 'IEM_VegetationCover_ModelInput_withSaltwater_' + version_num + '.tif' )
iem_landcarbon_final = cover(  akcan_rst, seak_1km_rcl, [ 0,8 ], output_filename, nodata=[ 255 ], band=1 )
# iem_landcarbon_final.write_colormap( 1, ctable )

# remove saltwater
iem_qml_final = os.path.join( output_path, 'QGIS_STYLES', 'IEM_LandCarbon_Vegetation_QGIS_STYLE_v1_0.qml' )
ctable = qml_to_ctable( iem_qml_final )
output_filename = os.path.join( output_path, 'IEM_VegetationCover_ModelInput_akcan_' + version_num + '.tif' )
reclass_list = [ [16,17,0] ]
seak_1km_rcl = reclassify( iem_landcarbon_final, reclass_list, output_filename, band=1 )
seak_1km_rcl.close()
seak_1km_rcl = rasterio.open( seak_1km_rcl.name, mode='r+' )
seak_1km_rcl.write_colormap( 1, ctable )

seak_1km_rcl.close()
iem_landcarbon_final.close()

# finally, extract this map to the final IEM extent:
seak_1km_rcl = rasterio.open( seak_1km_rcl.name )

# now we need to crop the data and mask it to the extent of the IEM DOMAIN based on the old Landcover Map
iem_mask = rasterio.open( os.path.join( input_path, 'merge_seak_mask', 'IEM_Mask.tif' ) )
mask_arr = iem_mask.read_band( 1 )

meta = iem_mask.meta
meta.update( meta_updater )

output_filename = os.path.join( output_path, 'IEM_VegetationCover_ModelInput_' + version_num + '.tif' )
output_raster = rasterio.open( output_filename, mode='w', **meta )

window = bounds_to_window( seak_1km_rcl.transform, output_raster.bounds )
seak_arr = seak_1km_rcl.read_band( 1, window=window )
seak_arr[ mask_arr != 1 ] = 255 # mask the data to the accepted IEM extent
seak_arr[ seak_arr == 8 ] = 10 # convert the remaining Temperate Rainforest to Upland (Per Dave McG)

ctable = qml_to_ctable( iem_qml_final )

output_raster.write_band( 1, seak_arr )
output_raster.write_colormap( 1, ctable )
output_raster.close()



