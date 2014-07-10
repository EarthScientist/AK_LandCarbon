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

	return rasterio.open( output_filename, mode='w', driver=driver, width=int(ncols), 
		height=int(nrows), count=bands, dtype=dtype, crs=crs, transform=geotrans )


def reclassify( rasterio_rst, reclass_list, output_filename, band=1 ):
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

	'''
	meta = rasterio_rst.meta

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

