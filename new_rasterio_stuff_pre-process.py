
# import some modules
import os, fiona, rasterio
from rasterio import features
import numpy as np
import scipy as sp

# pre-process the shapefiles
full_extent_shape = '/workspace/Shared/Tech_Projects/AK_LandCarbon/project_data/input_data/Frances_ExtendedShoreline_060914/AKNPLCC_Saltwater_with_Kodiak.shp'

file_path = '/workspace/Shared/Tech_Projects/AK_LandCarbon/project_data/input_data/From_Frances_Extracted'
creation_options = ["COMPRESS=LZW"]
master_raster= rasterio.open( os.path.join( file_path,'NLCD_canopy_AKNPLCC.tif' ) )

input_spatial_file = fiona.open( os.path.join( file_path,'AKNPLCC_Saltwater.shp' ) )

test = features.rasterize( ((i['geometry'], 5) for i in input_spatial_file), out_shape=master_raster.shape, fill=0, output=None, transform=master_raster.transform, all_touched=False )

shore = fiona.open(full_extent_shape, mode='w')


minX, minY, minX, maxY = shore.bounds
nrows = (maxY - minY) / master_raster.res[0]
ncols = (maxX - minX) / master_raster.res[0]
(nrows, ncols)

rasterio.open('test_new.tif', driver='GTiff')

rasterio.open(path, mode='r', driver=None, width=None, height=None, count=None, dtype=None, nodata=None, crs=None, transform=None, **kwargs)
new = generate_raster( master_raster.bounds, output_filename='tmp_remove.tif', resolution=master_raster.res[0], crs=crs, dtype=rasterio.uint8 )


# # # # # # # 
# LandCarbon LandCover SEAK Classification PREPROCESSING version 2.0

import pprint
import os, sys, rasterio, fiona
from rasterio import features
import numpy as np
import scipy as sp

file_path = '/workspace/Shared/Tech_Projects/AK_LandCarbon/project_data/input_data/From_Frances_Extracted'
output_path = '/workspace/Shared/Tech_Projects/AK_LandCarbon/project_data/output_data'
master_raster = rasterio.open( os.path.join( file_path,'NLCD_canopy_AKNPLCC.tif' ) )
meta = master_raster.meta

# consider rasterizing this and making it the final map
full_extent_shape = '/workspace/Shared/Tech_Projects/AK_LandCarbon/project_data/input_data/Frances_ExtendedShoreline_060914/AKNPLCC_Saltwater_with_Kodiak.shp'

## saltwater
saltwater = fiona.open( os.path.join( file_path,'AKNPLCC_Saltwater.shp' ) )

# set the crs to the correct one.  There is some software of lib that we use in R that 
# has botched all of the coord systems for some reason.  This solves is and sets it at 
# the EPSG:3338 that is standard
crs = saltwater.crs # will be the base coordsys for this preprocessing
meta.update( crs=crs )
meta.update( dtype=rasterio.int32 )
sw_raster = rasterio.open( os.path.join( output_path, 'saltwater_version2.tif'), 'w', **meta )

sw_image = features.rasterize(
			( ( g['geometry'], 1 ) for g in saltwater ),
			out_shape=master_raster.shape,
			transform=master_raster.transform, 
			fill=0 )

# place the new output ndarray into sw_raster
sw_image = sw_image.astype( np.int32 )
sw_raster.write_band( 1, sw_image )
sw_raster.close()
del sw_image, saltwater


## tnf_covertype
covertype = fiona.open(os.path.join(file_path,'TNFCoverType_OtherVeg_and_Alpine_MLedit.shp'))
output_dataset = os.path.join(file_path,'TNFCoverType_OtherVeg_and_Alpine_MLedit.tif')
filter_query_list = [ "NFCON='A' OR NFCON='B' OR NFCON='S' OR NFCON='T' OR NFCON='W'", "NFCON='H'" ]
# create a new output raster with some modified params
meta = master_raster.meta
meta.update( crs=crs )
meta.update( dtype=rasterio.int32 )
ct_raster = rasterio.open( os.path.join( output_path, 'tnf_covertype_version2.tif'), 'w', **meta )

def filter_cover_type( x ):
	if x['properties']['NFCON'] != u'H':
		hold = ( x['geometry'], 5 )
	elif x['properties']['NFCON'] == u'H':
		hold = ( x['geometry'], 6 )
	else:
		BaseException( 'ERROR' )
	return hold

ct_image = features.rasterize(
			( filter_cover_type( g ) for g in covertype ),
			out_shape=ct_raster.shape, 
			transform=ct_raster.transform, 
			fill=0)

# place the new output ndarray into ct_raster
ct_image = ct_image.astype( np.int32 )
ct_raster.write_band( 1, ct_image )
ct_raster.close()
del ct_image, covertype


## seak_2nd_growth
seak2nd = fiona.open( os.path.join( file_path,'AKNPLCC_2ndGrowth.shp' ) )
meta = master_raster.meta
meta.update( crs=crs )
meta.update( dtype=rasterio.int32 )
s2_raster = rasterio.open( os.path.join( output_path, 'seak2nd_growth_version2'.tif, 'w', **meta )

years = [ int(g['properties']['year']) for g in seak2nd ]
years_classed = dict([ ( value, key ) for key, value in enumerate(np.unique( np.array(years) ).tolist()) ])
reclassed = [ ( g['geometry'], years_classed[ int(g['properties']['year']) ] ) for g in seak2nd ]

s2_image = features.rasterize(
			reclassed,
			out_shape=master_raster.shape,
			transform=master_raster.transform,
			fill=0 )

# change the dtypes so they are compatible
# write the new array into the container with the years passed back in...
s2_image.astype(np.int32)
for year in years_classed.keys():
	s2_image[ s2_image == years_classed[ year ] ] = year

s2_raster.write_band( 1, s2_image )
s2_raster.close()
del s2_image, seak2nd

# PREPROCESSING COMPLETE!

# # # # # # # # # 






