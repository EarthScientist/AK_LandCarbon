# finalizing rasterio back-end functionality for processing landcover data
import rasterio, fiona, os, sys
import numpy as np
import scipy as sp


def generate_raster( bounds, resolution, output_filename, crs={}, bands=1, dtype=rasterio.float32,
	driver='GTiff', creation_options=["COMPRESS=LZW"] ):
	'''
	convert a bounding box to a raster with the desired
	spatial resolution.

	arguments:
		bounds = bounding box tuple or list with the form 
			(minX, minY, maxX, maxY)
		resolution = number indicating the desired output 
			resolution of the new raster.
			can be a list/tuple of length 2 or a single value
		crs = rasterio style proj4 string (python dict)
		output_filename = 
		creation_options = gdal-style creation options for a given driver
			defaults to GTiff compression.

	Notes:
		geotransform:
		An affine transformation that maps pixel row/column coordinates to
		coordinates in the specified reference system can be specified using
		the ``transform`` argument. The affine transformation is represented
		by a six-element sequence where th:wqe items are ordered like

		Item 0: X coordinate of the top left corner of the top left pixel 
		Item 1: rate of change of X with respect to increasing column, i.e.
		        pixel width
		Item 2: rotation, 0 if the raster is oriented "north up" 
		Item 3: Y coordinate of the top left corner of the top left pixel 
		Item 4: rotation, 0 if the raster is oriented "north up"
		Item 5: rate of change of Y with respect to increasing row, usually
		        a negative number i.e. -1 * pixel height

		Reference system coordinates can be calculated by the formula

		  X = Item 0 + Column * Item 1 + Row * Item 2
		  Y = Item 3 + Column * Item 4 + Row * Item 5

	Depends:
		rasterio

	'''
	minX, minY, maxX, maxY = bounds

	nrows = (maxY - minY) / resolution
	ncols = (maxX - minX) / resolution

	row_test = ( nrows - int( nrows ) )
	col_test = ( ncols - int( ncols ) )

	if row_test is not 0:
		prop_res = col_test * resolution
		maxY = maxY - prop_res

	if col_test is not 0:
		prop_res = row_test * resolution
		maxX = maxX - prop_res

	# generate a geotrans here
	geotrans = [ maxX, resolution, 0, maxY, 0, ( -1 * resolution ) ]
	# populate a metadata dict from the inputs to pass to file creation
	meta = dict( driver=driver, width=int(ncols), height=int(nrows), \
		 	count=bands, dtype=dtype, crs=crs, transform=geotrans, compress='lzw' )
	return rasterio.open( output_filename, mode='w', **meta )


def reclassify( rasterio_rst, reclass_list, output_filename, band=1, creation_options=dict() ):
	'''
	this functuion will take a raster image as input and
	reclassify its values given in the reclass_list.

	The reclass list is a simple list of lists with the 
	following formatting:
		[[begin_range, end_range, new_value]]
		ie. [ [ 1,3,5 ],[ 3,4,6 ] ]
			* which converts values 1 to 2.99999999 to 5
				and values 3 to 3.99999999 to 6
				all other values stay the same.

	arguments:
		rasterio_rst = raster image instance from rasterio package
		reclass_list = list of reclassification values * see explanation
		band = integer marking which band you wnat to return from the raster
				default is 1.
		creation_options = gdal style creation options, but in the rasterio implementation
			* options must be in a dict where the key is the name of the gdal -co and the 
			  value is the value passed to that flag.  
			  i.e. 
			  	["COMPRESS=LZW"] becomes dict([('compress','lzw')])

	'''
	# this will update the metadata if a creation_options dict is passed as an arg.
	meta = rasterio_rst.meta
	if len( creation_options ) < 0:
		meta.update( creation_options )

	with rasterio.open( output_filename, mode='w', **meta ) as out_rst:
		for idx,window in rasterio_rst.block_windows( 1 ):
			band_arr = rasterio_rst.read_band( band, window=window )
			for rcl in reclass_list:
				band_arr[ np.logical_and( band_arr >= rcl[0], band_arr < rcl[1] ) ] = rcl[2]
				out_rst.write_band( band, band_arr, window=window )
	return rasterio.open( output_filename )


def combine( rasterio_rst_1, rasterio_rst_2, combine_list, output_filename ):
	"""
	combine 2 rasterio raster images in a similar fashion to ArcMap's Combine

	arguments:
		rasterio_rst_1 = rasterio raster object 
		rasterio_rst_2 = rasterio raster object
		combine_list = list of lists with 3 elements in each sublist
			ex. [[1,1,1],[1,2,2],[2,1,3],[2,2,4],[3,1,5],[3,2,6],[5,1,7],[5,2,8]]
			*where each sublist elements are [ [ val_in_raster1, val_in_raster2, new_val ] ]
		output_filename = string representation of raster filename as a path

	"""
	meta = rasterio_rst_1.meta

	with rasterio.open( output_filename, mode='w', **meta ) as out_rst:

		assert len(set(rasterio_rst_1.block_shapes)) == 1

		for idx,window in rasterio_rst_1.block_windows( 1 ):
			out_band = out_rst.read_band( 1, window=window ) 
			out_band[ out_band != 0 ] = 0
			rst1_band = rasterio_rst_1.read_band( 1, window=window )
			rst2_band = rasterio_rst_2.read_band( 1, window=window )
			
			for comb in combine_list:
				out_band[ np.logical_and( rst1_band == comb[0], rst2_band == comb[1] ) ] = comb[2]
			
			out_rst.write_band( 1, out_band, window=window )
	return rasterio.open( output_filename )


def overlay_modify( rasterio_rst_base, rasterio_rst_cover, in_cover_values, out_cover_values, \
											output_filename, rst_base_band=1, rst_cover_band=1 ):
	'''
	modify a list of values in the base raster with a cover raster typically derived from 
	rasterizing a polygon shapefile depicting some locations in space where those list of 
	values need to be modified to other values, but only in those locations (patches).

	arguments:
		rasterio_rst_base = rasterio raster instance of base raster to be updated
		rasterio_rst_cover = rasterio raster instance of a cover raster used to guide
							value updating in the base raster.
		in_cover_values = list of values to be modified
		out_cover_values = list of values for cover values to be changed to
		output_filename = string path to the newly created output raster
		rst_base_band = integer indicating the band of the input base raster to be used
		rst_cover_band = integer indicating the band of the cover raster to be used

	Notes:
		it is important to note that the in_cover_values and the out_cover_values lists must be 
		of the same length. (they are essentially paired lists)
		ex.: 
			in_cover_values = [1,2,3]
			out_cover_values = [5,5,6]

	'''
	# get the known raster metadata
	meta = rasterio_rst_base.meta

	with rasterio.open( output_filename, mode='w', **meta ) as out_rst:
		for idx,window in rasterio_rst_base.block_windows( 1 ):
			base_band = rasterio_rst_base.read_band( rst_base_band, window=window )
			cover_band = rasterio_rst_cover.read_band( rst_cover_band, window=window )
			for rcl in zip( in_cover_values, out_cover_values ):
				base_band[cover_band == rcl[0]]  = rcl[1]
			out_rst.write_band( 1, base_band, window=window )

	return rasterio.open( output_filename )


def overlay_cover( rasterio_rst_base, rasterio_rst_cover, in_cover_value, 
					out_cover_value, output_filename, rst_base_band=1, rst_cover_band=1 ):
	'''
	we need to be able to overlay a set of polygons on a raster and burn in the 
	values we want to the raster image at those locations
	
	'''
	meta = rasterio_rst_base.meta
	meta.update( count=1, compress='lzw' )

	with rasterio.open( output_filename, mode='w', **meta ) as out_rst:
		# get the band information
		for idx,window in rasterio_rst_base.block_windows( 1 ):
			# out_band = out_rst.read_band( rst_base_band, window=window ) 
			base_band = rasterio_rst_base.read_band( rst_base_band, window=window )
			cover_band = rasterio_rst_cover.read_band( rst_cover_band, window=window )

			# out_band = np.copy( base_band )
			base_band[cover_band == in_cover_value] = out_cover_value
			out_rst.write_band( 1, base_band, window=window )

	return rasterio.open( output_filename )


def cover( large_rst, small_rst, large_rst_fill_vals, output_filename, nodata = [ None ], band=1 ):
	'''
	function that will fill by covering over certain values in the map in a loop.

	[ MORE DOC TO COME ]
	
	'''
	window = bounds_to_window( large_rst.transform, small_rst.bounds )
	large_arr_window = large_rst.read_band( band, window=window ).data # watch this .data stuff (for masks...)
	small_arr = small_rst.read_band( band ).data
	for i in np.unique( small_arr ):
		if i not in nodata:
			for j in large_rst_fill_vals:
				large_arr_window[ np.logical_and( small_arr == i, large_arr_window == j ) ] = i
	meta = large_rst.meta
	meta.update( compress='lzw', nodata=None )
	out = rasterio.open( output_filename, mode='w', **meta )
	large_arr = large_rst.read_band( 1 )
	out.write_band( band, large_arr )
	out.write_band( band, large_arr_window, window=window )
	return out

def world2Pixel( geotransform, x, y ):
	"""
	Uses a geotransform (gdal.GetGeoTransform(), or rasterio equivalent)
	to calculate the pixel location of a geospatial coordinate
	"""
	ulX = geotransform[0]
	ulY = geotransform[3]
	xDist = geotransform[1]
	yDist = geotransform[5]
	rtnX = geotransform[2]
	rtnY = geotransform[4]
	pixel = int((x - ulX) / xDist)
	line = int((ulY - y) / xDist)
	return ( pixel, line )

def pixel2World(geotransform, x, y):
	'''
	Uses a geotransform (gdal.GetGeoTransform(), or rasterio equivalent)
	to calculate the centroid location of pixel row/col.

	'''
	ulX = geotransform[0]
	ulY = geotransform[3]
	xDist = geotransform[1]
	yDist = geotransform[5]
	coorX = ( ulX + ( x * xDist ) )
	coorY = ( ulY + ( y * yDist ) )
	return ( coorX, coorY )

def centroids( rasterio_rst ):
	'''
	takes a rasterio raster instance and will return
	the centroids to all pixel values in a list.

	** this is a convenience function wrapping the 
	pixel2World() function.

	NOTE: returns centroids in C-order (row-major)
		* I may build in more order support if there 
		  is interest from users. *

	depends:
		rasterio

	'''
	a,b = [ range(i)  for i in rasterio_rst.shape ]
	return [ pixel2World( rasterio_rst.transform, ia, ib ) for ia in a for ib in b ]
	
def bounds_to_window( geotransform, rasterio_bounds ):
	'''
	return a rasterio window tuple-of-tuples used to read a subset
	of a rasterio raster file into a numpy array.  This is done by 
	passing the window argument in the:
		 dataset.read_band() or dataset.write_band()

	This function returns an object acceptable for use as a window 
	passed to the window argument.

	Notes:
	A window is a view onto a rectangular subset of a raster dataset
	and is described in rasterio by a pair of range tuples.
	window = ((row_start, row_stop), (col_start, col_stop))

	arguments:
		geotransform = 6-element rasterio transform 
			* typically from dataset.transform
		rasterio_bounds = (lower left x, lower left y, upper right x, upper right y)
			* typically from dataset.bounds in rasterio
	** This also requires the world2Pixel function.

	Depends:
		rasterio

	'''
	ll = rasterio_bounds[:2]
	ur = rasterio_bounds[2:]
	ll_xy, ur_xy = [ world2Pixel( geotransform, x, y ) for x, y in [ll, ur] ]
	return (( ur_xy[1], ll_xy[1]), ( ll_xy[0], ur_xy[0]))


def modify_dtype( in_rasterio_rst, output_filename, rasterio_dtype=rasterio.float32, band=1 ):
	'''
	this helper function will modify the raster dtype on copy
	to a new dataset.

	MORE DOC NEEDED HERE.
	'''
	arr = in_rasterio_rst.read_band( band )
	arr = arr.astype( rasterio_dtype )
	meta = in_rasterio_rst.meta
	meta.update( dtype = rasterio_dtype )
	out = rasterio.open( output_filename, mode='w', **meta ) 
	out.write_band( band, arr )
	return out


def breakout( rasterio_rst, output_filename, band=1 ):
	'''
	break all classes from an input rasterio raster object to a 
	new rasterio raster object with bands representing each class
	andn value.

	arguments:
		rasterio_rst = a rasterio instatiated raster object to be 
						run through breakout.
		output_filename = string representation of the output file path 
							for the new output file.
		band = band number of layer in raster to be broken out.  
				default: 1
	depends:
		rasterio, numpy

	'''
	import numpy as np
	import rasterio

	# anonymous function to write the class into a new band in output raster.
	def f( arr, class_val ):
		arr[ arr != class_val ] = 0	
		return arr

	arr = rasterio_rst.read_band( band )
	classes = np.unique( arr )

	meta = rasterio_rst.meta
	meta.update( compress='lzw', count=len(classes) )
	out_rasterio_rst = rasterio.open( output_filename, mode='w', **meta )
	[ out_rasterio_rst.write_band( ( band + 1 ), f( arr, class_val )  )\
					 for band, class_val in enumerate( classes ) ]
	return out_rasterio_rst

def hex_to_rgb( hex ):
	'''
	borrowed and modified from Matthew Kramer's blog:
		http://codingsimplicity.com/2012/08/08/python-hex-code-to-rgb-value/

	function to take a hex value and convert it into an RGB(A) representation.

	This is useful for generating color tables for a rasterio GTiff from a QGIS 
	style file (qml).  Currently tested for the QGIS 2.0+ style version.

	arguments:
		hex = hex code as a string

	returns:
		a tuple of (r,g,b,a), where the alpha (a) is ALWAYS 1.  This may need
		additional work in the future, but is good for the current purpose.
		** we need to figure out how to calculate that alpha value correctly.

	'''
	hex = hex.lstrip('#')
	hlen = len(hex)
	rgb = [ int( hex[i:i+hlen/3], 16 ) for i in range(0, hlen, hlen/3) ]
	rgb.insert(len(rgb)+1, 1)
	return rgb


def qml_to_ctable( qml ):
	'''
	take a QGIS style file (.qml) and converts it into a 
	rasterio-style GTiff color table for passing into a file.

	arguments:
		qml = path to a QGIS style file with .qml extension
	returns:
		dict of id as key and rgba as the values

	'''
	import xml.etree.cElementTree as ET
	tree = ET.ElementTree( file=qml  )
	return { int( i.get( 'value' ) ) : tuple( hex_to_rgb( i.get('color') ) ) for i in tree.iter( tag='item' ) }


def resample( src, src_crs, dst_crs, output_resolution, output_filename=None, rasterio_resample_method=None, band=1 ):
	'''
	take a raster at one resolution and return a new GTiff in a new
	spatial resolution as indicated by the user.

	src = rasterio instantiated raster object
	src_crs = rasterio-style proj4 dict
	dst_crs = rasterio-style proj4 dict
	output_resolution = list of values to set for output resolution.  
			* can be a single value in a list or 2 values in a list.
	output_filename = a string representation of a file path and name (GTiff only!)
	rasterio_resample_method = Not yet included...  NN only

	* if no output_filename is given the output will be a numpy ndarray
	if there is an output_filename, the returned will be a rasterio raster 
	object.

	'''
	import numpy as np
	from math import trunc
	from rasterio.warp import reproject, RESAMPLING
	from string import letters

	if len( output_resolution ) == 1:
		output_resolution = [ output_resolution[0], output_resolution[0] ]
	elif len( output_resolution ) == 2:
		output_resolution = [ output_resolution[0], output_resolution[1] ]
	else:
		print('wrong number of resolution elements. reset and try again')

	src_transform = src.transform
	A.to_gdal( { i:j for i,j in zip( list( letters[:6] ), src_transform ) } )
 	dst_transform = src_transform
 	dst_transform[1], dst_transform[5] = output_resolution[0], output_resolution[1]

	xmin, ymin, xmax, ymax = src.bounds
	dst_width = trunc( abs( (ymax - ymin) / output_resolution[0]) )
	dst_height = trunc( abs( (xmax - xmin) / output_resolution[1]) )

	dst = np.empty( ( dst_height, dst_width ), dtype=src.meta['dtype'] )
	reproject( src.read_band( band ), dst, src_transform, src_crs, dst_transform, dst_crs )

	if output_filename is not None:
		# get the source file metadata
		dst_meta = src.meta
		dst_meta.update( compress='lzw', crs=dst_crs, transform=dst_transform, height=dst_height, width=dst_width )
		out_rst = rasterio.open( output_filename, mode='w', **dst_meta )
		out_rst.write_band( 1, dst )
		out = out_rst
	else:
		out = dst
	return  out

def union_raster_extents( rasterio_rst_1, rasterio_rst_2, output_filename, dtype=rasterio.uint8, crs={} ):
	'''
	make a new raster with the unioned extents of the 2 inputs
	and return it as a GTiff with lzw compression

	depends:
		shapely, rasterio

	'''
	import shapely, math
	from shapely.geometry import box
	
	resolution = rasterio_rst_1.res[0]
	box1 = box( *rasterio_rst_1.bounds )
	box2 = box( *rasterio_rst_2.bounds )
	
	full_ext = box1.union( box2 )
	left, bottom, right, top = full_ext.exterior.bounds
	ncols = math.ceil( ( right - left ) / resolution )
	nrows = math.ceil( ( top - bottom ) / resolution )
	new_transform = [ left, resolution, 0.0, top, 0.0, -resolution ]
	meta = dict(
				affine=rasterio.Affine.from_gdal( *new_transform ),
				driver='GTiff', 
				width=ncols, 
				height=nrows, 
				count=1, 
				crs=crs, 
				transform=new_transform, 
				dtype=dtype, 
				nodata=None
			)
	return rasterio.open( output_filename, mode='w', **meta )

