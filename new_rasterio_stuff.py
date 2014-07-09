# module functions 
# pre-process
# what does a pre-process require?

def rasterize( self ):
		'''
		rasterize a shapefile to a template raster using a field as
		burn_values.

		gotcha: data must be in the same reference system and overlap.
			welcome to the real world hippies.

		depends:
			gdal, ogr, osr
		'''
		lyr = self.input_shp.GetLayer()
		osrs = lyr.GetSpatialRef()
		self.template_raster.SetProjection( osrs.ExportToWkt() )
		out_rst = self.raster_from_template( template_raster=self.template_raster, \
				output_filename=self.output_filename, output_format=self.output_format )
		gdal.RasterizeLayer( out_rst, [1], 
				lyr, options=["ATTRIBUTE="+id_field] )
		out_rst.FlushCache()
		return out_rst


image = features.rasterize(
	((g, 255) for g, v in shapes),
	out_shape=blue.shape, fill=0, transform=transform )

shp = fiona.open('/workspace/Shared/Tech_Projects/AK_LandCarbon/project_data/input_data/Frances_Data_022714/AKNPLCC_Saltwater.shp')

# how to copy a raster dataset using rasterio...  that was not very intuitive and not flexible.
with rasterio.drivers():
	rasterio.copy( rst2.name, '/workspace/UA/malindgren/temporary/LandCarbon_LandCover_SEAK_v2_1km_current_finalmap_TEST.tif', driver='GTiff' )


# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# how to resample a raster to a different grid

# read the datasets
rst = rasterio.open('/workspace/Shared/Tech_Projects/AK_LandCarbon/project_data/input_data/From_Frances_Extracted/TNFCoverType.tif')
rst2 = rasterio.open('/workspace/Shared/Tech_Projects/AK_LandCarbon/project_data/output_data/data/V2/LandCarbon_LandCover_SEAK_v2_1km_current_finalmap.tif')

band = rst.read_band(1)
band2 = rst2.read_band(1)

# a make an all zeros copy of the band 2 
band2 = np.zeros_like( band2 )

# set a common crs (in this case it is the same as I want to regrid not reproject)
crs = {'init':'EPSG:3338'}
src_transform = rst.transform
dst_transform = rst2.transform

# run the resampling using nearest neighbor resampling
reproject( band, band2, src_transform=src_transform, src_crs=crs, dst_transform=dst_transform, \
			dst_crs=crs, resampling=RESAMPLING.nearest )

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

# select the data
with fiona.open("file.shp") as src:
    filtered = filter( lambda f: f['properties']['foo'] == 'bar', src )

# THIS IS THE NEW VERSION OF THE CODE FOR THE SEAK LANDCOVER MAP

# load some modules to do the work
import rasterio
import fiona
from rasterio import features
from sklearn.utils import resample
import scipy.ndimage

# pre-process the data
# file_path = '/workspace/Shared/Tech_Projects/AK_LandCarbon/project_data/input_data/From_Frances_Extracted'
# master_raster=rasterio.open(os.path.join(file_path,'NLCD_canopy_AKNPLCC.tif'))

# # Saltwater
# input_spatial_file = os.path.join(file_path,'AKNPLCC_Saltwater.shp')
# output_dataset = os.path.join(file_path,'AKNPLCC_Saltwater.tif')

# with rasterio.drivers():
# 	with fiona.collection( input_spatial_file ) as shp:
# 		tmp = map(lambda x: (x['geometry'], 1), shp) # this is where we subset out the data

# 		new = filter( lambda x: x['REV_DATE'], shp)
# 		tmp = [ ( x['geometry'], 1 ) for x in shp ]

# 		test = rasterio.features.rasterize( tmp, transform=rst.get_transform(), out_shape=rst.shape, fill=0 )




# new working functions...
def reclassify( rasterio_rst, reclass_list, band=1 ):
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

	with rasterio.open( output_filename, 
						mode='w', 
						driver='GTiff', 
						width=meta['width'], 
						height=meta['height'], 
						count=meta['count'], 
						dtype=meta['dtype'], 
						nodata=meta['nodata'], 
						crs=meta['crs'], 
						transform=meta['transform'] ) as out_rst:
	for idx,window in rasterio_rst_1.block_windows( 1 ):
		band = rasterio_rst.read_band( band, window=window )
		for rcl in reclass_list:
			band[ np.logical_and( band >= rcl[0], band < rcl[1] ) ] = rcl[2]
			out_rst.write_band( band, window=window )
	return rasterio.open( output_filename )


# raster 1 is the landcover and raster 2 is the canopy
combine_list = [[1,1,1],[1,2,2],[2,1,3],[2,2,4],[3,1,5],[3,2,6],[5,1,7],[5,2,8]]

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

	with rasterio.open( output_filename, 
						mode='w', 
						driver='GTiff', 
						width=meta['width'], 
						height=meta['height'], 
						count=meta['count'], 
						dtype=meta['dtype'], 
						nodata=meta['nodata'], 
						crs=meta['crs'], 
						transform=meta['transform'] ) as out_rst:

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


# run it
%time test_combine = combine( rasterio_rst_1, rasterio_rst_2, combine_list, output_filename )



def overlay_cover( rasterio_rst_base, rasterio_rst_cover, in_cover_value, out_cover_value, output_filename, rst_base_band=1, rst_cover_band=1 ):
	'''
	we need to be able to overlay a set of polygons on a raster and burn in the values we want to 
	the raster image at those locations
	
	'''
	meta = rasterio_rst_base.meta

	with rasterio.open( output_filename, 
						mode='w', 
						driver='GTiff', 
						width=meta['width'], 
						height=meta['height'], 
						count=meta['count'], 
						dtype=meta['dtype'], 
						nodata=meta['nodata'], 
						crs=meta['crs'], 
						transform=meta['transform'] ) as out_rst:

		# get the band information
		for idx,window in rasterio_rst_1.block_windows( 1 ):
			# out_band = out_rst.read_band( rst_base_band, window=window ) 
			base_band = rasterio_rst_base.read_band( rst_base_band, window=window )
			cover_band = rasterio_rst_cover.read_band( rst_cover_band, window=window )

			# out_band = np.copy( base_band )
			base_band[cover_band == in_cover_value] = out_cover_value
			out_rst.write_band( 1, base_band, window=window )

	return rasterio.open( output_filename )


# this function is a temporary fix for a broken tool in the scikit-learn package that will be fixed next week, but I need functionality now
# def resample(gdal_raster, epsg_code, output_filename, method='mode', x_res=None, y_res=None, \
# 	output_width=None, output_height=None, output_format="GTiff", output_datatype=gdal.GDT_Float32, \
# 	creation_options=["COMPRESS=LZW"]):
# 	"""
# 	a wrapper around a couple of other boilerplate gdal functions to have a one-off way of 
# 	resampling a dataset

# 	This function is going to be considered deprecated very soon, as there are scipy ways of doing
# 	this sort of resampling.  I will be using that much more idiomatic approach very soon. 

# 	"""
# 	input_extent = raster_bbox(gdal_raster.GetGeoTransform(), 
# 			size=[gdal_raster.RasterXSize, gdal_raster.RasterYSize])
	
# 	out = generate_raster(input_extent, 
# 			epsg_code=3338, 
# 			output_filename=output_filename, 
# 			x_res=x_res, 
# 			y_res=y_res, 
# 			output_width=output_width, 
# 			output_height=output_height, 
# 			output_format=output_format, 
# 			output_datatype=output_datatype, 
# 			creation_options=creation_options)

# 	gdal.RegenerateOverview ( gdal_raster.GetRasterBand(1), out.GetRasterBand(1), method )
# 	out.GetRasterBand(1).ComputeStatistics(0)
# 	out.FlushCache()
# 	return out




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

	with rasterio.open( output_filename, 
						mode='w', 
						driver='GTiff', 
						width=meta['width'], 
						height=meta['height'], 
						count=meta['count'], 
						dtype=meta['dtype'], 
						nodata=meta['nodata'], 
						crs=meta['crs'], 
						transform=meta['transform'] ) as out_rst:

		for idx,window in rasterio_rst_1.block_windows( 1 ):
			base_band = rasterio_rst_base.read_band( rst_base_band, window=window )
			cover_band = rasterio_rst_cover.read_band( rst_cover_band, window=window )
			for rcl in zip( in_cover_values, out_cover_values ):
				base_band[cover_band == rcl[0]]  = rcl[1]
			out_rst.write_band( 1, base_band, window=window )

	return rasterio.open( output_filename )





