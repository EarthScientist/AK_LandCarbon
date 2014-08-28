# this script is a hack to temporarily solve an issue with the new IEM veg map, where we lost a class
# I am working on developing a new procedure that will properly rectify these issues but as of now this 
# is a hack to get the data working as we would have wanted in the first place.  
# the missing class was Upland in Kodiak.  So I have hacked together a solution that grabbed the values from 
# version 1 of the map and passd them into version2 of the map.
# August 5, 2014
# # # # # # # 

																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																															'gdalwarp -s_srs EPSG:3338 -t_srs EPSG:3338 -tr 1000 1000 /workspace/Shared/Tech_Projects/AK_LandCarbon/project_data/output_data/data/V4/nlcd_mask.tif /workspace/Shared/Tech_Projects/AK_LandCarbon/project_data/output_data/data/V4/nlcd_mask_1km.tif'


import rasterio
import numpy as np
import os

# import my library of functions
os.chdir( '/workspace/Shared/Tech_Projects/AK_LandCarbon/project_data/CODE' )
from final_v2_library import *

os.chdir( '/workspace/Shared/Tech_Projects/AK_LandCarbon/project_data/output_data/data/V4' )

# input maps
seak = rasterio.open('/workspace/Shared/Tech_Projects/AK_LandCarbon/project_data/output_data/data/V2/LandCarbon_LandCover_SEAK_v2_1km_current_finalmap.tif')
full = rasterio.open('/workspace/Shared/Tech_Projects/AK_LandCarbon/project_data/output_data/data/V4/IEM_LandCarbon_Vegetation_v0_1_akcan.tif')
iem = rasterio.open('/workspace/Shared/Tech_Projects/AK_LandCarbon/project_data/output_data/data/V4/IEM_LandCarbon_Vegetation_v0_1.tif' )

window = bounds_to_window(iem.transform, seak.bounds)
iem_window = iem.read_band(1, window=window)

reclass_list = [(2,10), (3,11), (4,12), (5,13), (6,14), (7,9), (8,4), (9,15), (10,5)] #(1,0),

# turn all of the reclass list stuff in that aoi to 255
for i,j in reclass_list:
	iem_window[ seak.read_band(1) == i ] = 255

iem_meta = iem.meta
iem_meta.update(compress='lzw')
iem2 = rasterio.open('/workspace/Shared/Tech_Projects/AK_LandCarbon/project_data/output_data/data/V4/IEM_LandCarbon_Vegetation_v0_3_hack_blank.tif', mode='w', **iem_meta)

iem2.write_band(1, iem.read_band(1))
iem2.write_band(1, iem_window, window=window)
iem2.close()


# remove any leftover erroneous values left in the map:
erroneous_list = [ 1,2,3,4,5,6,7,9,15 ]
nlcd_mask = rasterio.open('/workspace/Shared/Tech_Projects/AK_LandCarbon/project_data/output_data/data/V4/nlcd_mask_1km.tif')
nlcd_mask_arr = nlcd_mask.read_band(1, window=window)

for i in erroneous_list:
	iem_window[ np.logical_and( nlcd_mask_arr == 1, iem_window == i ) ] = 255
iem_meta = iem.meta
iem_meta.update(compress='lzw')

iem2 = rasterio.open('/workspace/Shared/Tech_Projects/AK_LandCarbon/project_data/output_data/data/V4/IEM_LandCarbon_Vegetation_v0_3_hack_removederror.tif', mode='w', **iem_meta)
iem2.write_band(1, iem.read_band(1))
iem2.write_band(1, iem_window, window=window)
iem2.close()


# now pass back in the values we want.
for i,j in reclass_list:
	iem_window[ seak.read_band(1) == i ] = j


iem_meta = iem.meta
iem_meta.update(compress='lzw')

iem2 = rasterio.open('/workspace/Shared/Tech_Projects/AK_LandCarbon/project_data/output_data/data/V4/IEM_LandCarbon_Vegetation_v0_3_hack.tif', mode='w', **iem_meta)

iem2.write_band(1, iem.read_band(1))
iem2.write_band(1, iem_window, window=window)
iem2.close()




