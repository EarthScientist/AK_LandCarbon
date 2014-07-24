## This is a really quick and dirty way to run all of the needed procedure for the creation of the new SC/SEAK LandCarbon Vegetation Map 
##  along with the merged map into the larger IEM ALFRESCO VEGETATION.  

## preprocess -- only run once
# screen ipython2.7 /workspace/Shared/Tech_Projects/AK_LandCarbon/project_data/CODE/final_v2_preprocessing.py

# run seak (from v1)
screen ipython2.7 -i /workspace/Shared/Tech_Projects/AK_LandCarbon/project_data/CODE/final_v2_procedure.py
# run kodiak ( from Dave McGuire and Team - 2014 )
screen ipython2.7 -i /workspace/Shared/Tech_Projects/AK_LandCarbon/project_data/CODE/kodiak_reclassification_procedure.py

## run the merge code:
screen ipython2.7 -i /workspace/Shared/Tech_Projects/AK_LandCarbon/project_data/CODE/merge_landcover.py

