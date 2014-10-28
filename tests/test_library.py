# tests
import rasterio
from rasterio import Affine
import itertools, os
import numpy as np

os.chdir( '/workspace/Shared/Tech_Projects/AK_LandCarbon/project_data/CODE' )
from geolib_snap import *

test_folder = '/workspace/Shared/Tech_Projects/AK_LandCarbon/project_data/working_folder/test_data'

def create_dummy_stripes( output_filename ):
	'''
	generate a dummy file with stripes of integers across it for testing 
	'''
	num_list = range( 20 )
	output = [ [ i for i in itertools.repeat( num, 30 ) ] for num in num_list ]
	new = np.asarray( output, dtype=int )

	meta = {'affine': Affine(1000.0, 0.0, 0.0,
	       0.0, -1000.0, 20.0),
	 'count': 1,
	 'crs': {},
	 'driver': u'GTiff',
	 'dtype': np.uint8,
	 'height': 20,
	 'nodata': 255.0,
	 'transform': (0.0, 1000.0, 0.0, 20.0, 0.0, -1000.0),
	 'width': 30}

	rst_out = rasterio.open( output_filename , mode='w', **meta )
	rst_out.write_band(1, new.astype(rasterio.uint8) )
	rst_out.close()
	return rasterio.open( rst_out.name, mode='r' ) # for file flushy things


# # # reclassify
output_filename = os.path.join( test_folder, 'stripe_test.tif' ) 
rst = create_dummy_stripes( output_filename )

uniques = np.unique( rst.read_band( 1 ) )
reclass_list = [ [ i,i+1,i+20 ] for i in uniques ] # add 20 to each input val

output_filename = os.path.join( test_folder, 'stripe_test_rcl.tif' ) 

rcl = reclassify( rst, reclass_list, output_filename=output_filename, band=1, creation_options=dict([('compress','lzw')]) )

uniques_rcl = np.unique(rcl.read_band(1))

assert ( uniques_rcl - uniques ).data.tolist() == [ i for i in itertools.repeat( 20, 20 )]


# # # combine



