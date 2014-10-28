# 
import os, sys, re
import rasterio, fiona, shapely, math
from itertools import izip

# import my library of functions
os.chdir( '/workspace/Shared/Tech_Projects/AK_LandCarbon/project_data/CODE' )
from final_v2_library import *

version_num = 'v0_3'

output_path = '/workspace/Shared/Tech_Projects/AK_LandCarbon/project_data/output_data/data/V7'
os.chdir( output_path )
meta_updater = dict( driver='GTiff', dtype=rasterio.uint8, compress='lzw', crs={'init':'EPSG:3338'}, count=1, nodata=None )

seak_30m = os.path.join( output_path, 'LandCarbon_MaritimeVegetation_SC_SEAK_30m_' + version_num + '.tif' )
kodiak_30m = os.path.join( output_path, 'LandCarbon_MaritimeVegetation_KODIAK_30m_' + version_num + '.tif' ) 

# open the rasters
seak_30m_rst = rasterio.open( seak_30m )
kodiak_30m_rst = rasterio.open( kodiak_30m )

# get the arrays
seak_30m_arr = seak_30m_rst.read_band( 1 )
kodiak_30m_arr = kodiak_30m_rst.read_band( 1 )

# dump those changes into a new map since they are soo darn large:
# 	then read them back in for further processsing
seak_meta = seak_30m_rst.meta
seak_meta.update( meta_updater )
seak_rcl = rasterio.open( os.path.join( output_path, 'LandCarbon_Vegetation_SC_SEAK_30m_' + version_num + '_rcl.tif' ), mode='w', **seak_meta )
seak_rcl.write_band( 1, seak_30m_arr.astype( rasterio.uint8 ) )
seak_rcl.close()
seak_30m_rst.close() # close the original output data
del seak_30m_rst

kodiak_meta = kodiak_30m_rst.meta
kodiak_meta.update( meta_updater )
kodiak_rcl = rasterio.open( os.path.join( output_path, 'LandCarbon_Vegetation_SC_kodiak_30m_' + version_num + '_rcl.tif' ), mode='w', **kodiak_meta )
kodiak_rcl.write_band( 1, kodiak_30m_arr.astype( rasterio.uint8 ) )
kodiak_rcl.close()
kodiak_30m_rst.close() # close the original output data
del kodiak_30m_rst

output_map_path = os.path.join( output_path, 'LandCarbon_MaritimeVegetation_30m_withSaltwater_'+ version_num +'.tif' )
crs = { 'init':'EPSG:3338' }
output_lc = union_raster_extents( seak_rcl, kodiak_rcl, output_filename=output_map_path, dtype=rasterio.uint8, crs=crs )
output_lc_arr = output_lc.read_band( 1 )
output_lc_arr.fill( 255 )
output_lc.write_band( 1, output_lc_arr )
output_lc.close()
output_lc = rasterio.open( output_lc.name, mode='r+' )

del output_map_path, output_lc_arr

# put the data in the new map
for rst in [ seak_rcl, kodiak_rcl ]:
	print rst.name
	rst = rasterio.open( rst.name )
	window = bounds_to_window( output_lc.transform.to_gdal(), rst.bounds )
	arr = rst.read_band( 1 )
	arr = arr.astype( np.uint8 )
	output_lc.write_band( 1, arr, window=window )
	rst = None
	arr = None

# generate a colortable for the map and pass it in:
seak_qml_sw = os.path.join( output_path, 'QGIS_STYLES', 'SEAK_LandCarbon_Vegetation_QGIS_STYLE_v1_0_withSaltwater.qml' )
ctable = qml_to_ctable( seak_qml_sw )
output_lc.write_colormap( 1, ctable )
output_lc.close()

# # # # TEST # # # #
# output_filename = os.path.join( output_path, 'GDAL_MERGED_TEST_CASE.tif' )
# command = 'gdal_merge.py -o ' + output_filename + ' -of  GTiff -ot Byte -n 255 -a_nodata 255 -init 255 ' + seak_30m_rst.name + ' ' + kodiak_30m_rst.name
# os.system( command )
# # # # TEST # # # #

# resample this newly generated 30m map to 1km resolution using a mode resampling 
#  --> currently employing gdalwarp ( GDAL 1.10+ )for this task and the mode resampler
# resample the rasters to the 1000m resolution used by the IEM project
output_filename = os.path.join( output_path, 'LandCarbon_MaritimeVegetation_1km_withSaltwater_' + version_num + '.tif' )

# TEMPORARY FIX FOR RESAMPLING
if os.path.exists( output_filename ):
	os.remove( output_filename )

# this is the regridding fix I am using currently.  It is not perfect and a band-aid fix but it works correctly for now
# THIS WILL ONLY WORK WITH GDAL 1.10+ since that is when the mode filter was introduced
command = 'gdalwarp -tr 1000 1000 -r mode -srcnodata None -dstnodata None -multi -co "COMPRESS=LZW" '+ output_lc.name + ' ' + output_filename
os.system( command )

# now we need to pass that color table back into the file using rasterio.  This is a clunky hack fix due to some issues
#  using the built-in rasterio reproject/resampling ( needs solving )...
output_lc = rasterio.open( output_filename, mode='r+' )
output_lc.write_colormap( 1, ctable )
output_lc.close()

# now that we created the above maps for Merging purposes with the other IEM map at large we want to remove the saltwater
# class from the final output for distribution of the 1km Map:
# 30m
seak_qml_final = os.path.join( output_path, 'QGIS_STYLES', 'SEAK_LandCarbon_Vegetation_QGIS_STYLE_v1_0.qml' )
seak_30m_sw = rasterio.open( os.path.join( output_path, 'LandCarbon_MaritimeVegetation_30m_withSaltwater_'+ version_num +'.tif' ) )
meta = seak_30m_sw.meta
meta.update( meta_updater )
ctable = qml_to_ctable( seak_qml_final )
seak_30m_sw_arr = seak_30m_sw.read_band( 1 )
seak_30m_sw_arr[ seak_30m_sw_arr == 17 ] = 255
seak_30m_final = rasterio.open( os.path.join( output_path, 'LandCarbon_MaritimeVegetation_30m_'+ version_num +'.tif' ), mode='w', **meta )
seak_30m_final.write_band( 1, seak_30m_sw_arr )
seak_30m_final.write_colormap( 1, ctable )
seak_30m_final.close()

# 1km
output_lc = rasterio.open( output_lc.name )
meta = output_lc.meta
meta.update( meta_updater )
output_lc_arr = output_lc.read_band( 1 )
# do some reclassification to get to the final required classes
#	change saltwater to noveg
output_lc_arr[ output_lc_arr == 17 ] = 255
lc_1k = rasterio.open( os.path.join( output_path, 'LandCarbon_MaritimeVegetation_1km_' + version_num + '.tif' ), mode='w', **meta )
lc_1k.write_band( 1, output_lc_arr )
lc_1k.write_colormap( 1, ctable )
lc_1k.close()





