import os, sys, re
import rasterio, fiona, shapely, math
from itertools import izip

# import my library of functions
os.chdir( '/workspace/Shared/Tech_Projects/AK_LandCarbon/project_data/CODE' )
from final_v2_library import *

version_num = 'v0_3'

output_path = '/workspace/Shared/Tech_Projects/AK_LandCarbon/project_data/output_data/data/V5'

seak_30m = os.path.join( output_path, 'LandCarbon_Vegetation_SC_SEAK_30m_' + version_num + '.tif' )
kodiak_30m = os.path.join( output_path, 'LandCarbon_Vegetation_KodiakIsland_30m_' + version_num + '.tif' ) 

# open the rasters
seak_30m_rst = rasterio.open( seak_30m )
kodiak_30m_rst = rasterio.open( kodiak_30m )

# get the arrays
seak_30m_arr = seak_30m_rst.read_band( 1 )
kodiak_30m_arr = kodiak_30m_rst.read_band( 1 )

# do some reclassification to get to the final required classes
#	change saltwater to noveg
seak_30m_arr[ seak_30m_arr == 17 ] = 255
kodiak_30m_arr[ kodiak_30m_arr == 17 ] = 255

# dump those changes into a new map since they are soo darn large:
# 	then read them back in for further processsing
seak_meta = seak_30m_rst.meta
seak_meta.update( compress='lzw', crs={ 'init':'EPSG:3338' }, nodata=None, count=1 )
seak_rcl = rasterio.open( os.path.join( output_path, 'LandCarbon_Vegetation_SC_SEAK_30m_' + version_num + '_rcl.tif' ), mode='w', **seak_meta )
seak_rcl.write_band( 1, seak_30m_arr )
seak_rcl.close()
seak_30m_rst.close() # close the original output data
del seak_30m_rst

kodiak_meta = kodiak_30m_rst.meta
kodiak_meta.update( compress='lzw', crs={ 'init':'EPSG:3338' }, nodata=None, count=1 )
kodiak_rcl = rasterio.open( os.path.join( output_path, 'LandCarbon_Vegetation_SC_kodiak_30m_' + version_num + '_rcl.tif' ), mode='w', **kodiak_meta )
kodiak_rcl.write_band( 1, kodiak_30m_arr )
kodiak_rcl.close()
kodiak_30m_rst.close() # close the original output data
del kodiak_30m_rst

output_map_path = os.path.join( output_path, 'LandCarbon_CoastalVegetation_30m_'+ version_num +'.tif' )
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
	arr = arr.data.astype( np.uint8 )
	output_lc.write_band( 1, arr, window=window )
	rst = None
	arr = None

# generate a colortable for the map and pass it in:
qml = '/workspace/Shared/Tech_Projects/AK_LandCarbon/project_data/output_data/data/QGIS_STYLES/SEAK_LandCarbon_Vegetation_QGIS_STYLE_v1_0.qml'
ctable = qml_to_ctable( qml )
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
output_filename = os.path.join( output_path, 'LandCarbon_CoastalVegetation_1km_' + version_num + '.tif' )

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



