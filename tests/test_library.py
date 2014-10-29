# tests
import rasterio
from rasterio import Affine
import itertools, os
import numpy as np

os.chdir( '/workspace/Shared/Tech_Projects/AK_LandCarbon/project_data/CODE' )
from geolib_snap import *

test_folder = '/workspace/Shared/Tech_Projects/AK_LandCarbon/project_data/working_folder/test_data'

def create_dummy_stripes( num_list, output_filename, dtype=np.uint8 ):
	'''
	generate a dummy file with stripes of integers across it for testing 
	'''
	output = [ [ i for i in itertools.repeat( num, 30 ) ] for num in num_list ]
	new = np.asarray( output, dtype=dtype )

	meta = {'affine': Affine(1000.0, 0.0, 0.0,
	       0.0, -1000.0, 20.0),
	 'count': 1,
	 'crs': {},
	 'driver': u'GTiff',
	 'dtype': dtype,
	 'height': 20,
	 'nodata': 255.0,
	 'transform': (0.0, 1000.0, 0.0, 20.0, 0.0, -1000.0),
	 'width': 30}

	rst_out = rasterio.open( output_filename, mode='w', **meta )
	rst_out.write_band(1, new.astype( dtype ) )
	rst_out.close()
	return rasterio.open( rst_out.name, mode='r' ) # for file flushy things


# # # reclassify
num_list = range( 20 )
output_filename = os.path.join( test_folder, 'stripe_test.tif' ) 
rst = create_dummy_stripes( num_list, output_filename, dtype=np.int16 )

uniques = np.unique( rst.read_band( 1 ) )
reclass_list = [ [ i,i+1,i+20 ] for i in uniques ] # add 20 to each input val

output_filename = os.path.join( test_folder, 'stripe_test_rcl.tif' ) 

rcl = reclassify( rst, reclass_list, output_filename=output_filename, band=1, creation_options=dict([('compress','lzw')]) )

uniques_rcl = np.unique(rcl.read_band(1))

assert ( uniques_rcl - uniques ).data.tolist() == [ i for i in itertools.repeat( 20, 20 )]


# # # combine
num_list = range( 20 )
output_filename = os.path.join( test_folder, 'stripe_test_combine_1.tif' ) 
comb1 = create_dummy_stripes( num_list, output_filename, dtype=np.int16 )

num_list2 = num_list[:]
num_list2.reverse()
output_filename = os.path.join( test_folder, 'stripe_test_combine_2.tif' )
comb2 = create_dummy_stripes( num_list2, output_filename, dtype=np.int16 )

combine_list = [ [i,j,i-j] for i,j in zip( num_list, num_list2 ) ]

output_filename = os.path.join( test_folder, 'stripe_test_combined.tif' )
comb = combine( comb1, comb2, combine_list, output_filename )
comb_uniques = np.unique(comb.read_band(1))
combine_list_uniques = np.unique([k for i,j,k in combine_list ])

assert (combine_list_uniques - comb_uniques).all() == 0


# # # overlay_modify
num_list = range( 20 )
output_filename = os.path.join( test_folder, 'stripe_test_overlay_modify_1.tif' ) 
over1 = create_dummy_stripes( num_list, output_filename, dtype=np.int16 )

num_list2 = num_list[:]
num_list2.reverse()
output_filename = os.path.join( test_folder, 'stripe_test_overlay_modify_2.tif' )
over2 = create_dummy_stripes( num_list2, output_filename, dtype=np.int16 )

in_cover_values = [2,4,6,8,10]
out_cover_values = [95,96,97,98,99]
output_filename = os.path.join( test_folder, 'stripe_test_overlay_modified.tif' )

over = overlay_modify( over1, over2, in_cover_values, out_cover_values, output_filename, rst_base_band=1, rst_cover_band=1 )
test_covered = [ 19-i for i in in_cover_values ]
over_uniques = np.unique(over.read_band(1))

assert np.unique([ i in over_uniques for i in test_covered ]).all() == False


# # # overlay_cover
num_list = range( 20 )
output_filename = os.path.join( test_folder, 'stripe_test_overlay_cover_1.tif' ) 
cover1 = create_dummy_stripes( num_list, output_filename, dtype=np.int16 )

num_list2 = num_list[:]
num_list2.reverse()
output_filename = os.path.join( test_folder, 'stripe_test_overlay_cover_2.tif' )
cover2 = create_dummy_stripes( num_list2, output_filename, dtype=np.int16 )

in_cover_value = 11
out_cover_value = -9999
output_filename = os.path.join( test_folder, 'stripe_test_overlay_covered.tif' )

cover = overlay_cover( cover1, cover2, in_cover_value, out_cover_value, output_filename, rst_base_band=1, rst_cover_band=1 )
cover_uniques = np.unique( cover.read_band(1) )

list_pairs = zip( num_list, num_list2 )
covered_value = [ j for i,j in list_pairs if i == in_cover_value ][0]

assert covered_value not in cover_uniques.tolist() # is that covered value in the output uniques?
assert out_cover_value in cover_uniques.tolist() # is the new value present?


