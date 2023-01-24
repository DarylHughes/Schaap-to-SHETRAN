# -*- coding: utf-8 -*-
"""
Date created:   2023.01.23
Last modified:  2023.01.24
@author:        Daryl Hughes


This script:
    - reads 5km soil parameter .asc grids and translates these for SHETRAN setup
    - generates Soil Categories (map of spatially-distributed categories)
    - generates Soil Properties (lines corresponding to each soil type 
                                 with parameters θSat, θRes, K, alpha, n)
    - generates Soil Details    (lines containing depth profiles of soil types 
                                 within each category)
    
NB the 5 Maulem-van Genuchten soil parameters come from the 0.25° global grid 
(Montzka et al., 2017). Each parameter was extracted from the NetCDF file using
QGIS, clipped to the Essequibo River basin and reprojected to 5km resolution.

Units:
    VG_ThetaS, cm3 cm-3
    VG_ThetaR, cm3 cm-3
    VG_Ksat,   cm d-1. NB SHETRAN needs m d-1
    VG_Alpha', cm-1
    VG_N',     -


The user must define:
    - 'FunctionsLibrary' which contains custom functions
    - 'DirectoryIn' which contains the ASC files
    - 'ResolutionKM' wich contains the resolution size in the ASC file name
    - 'DirectoryOut' which contains the output TXT files
    - 'SuperCatsOut' which names an output TXT file
    - 'SoilPropertiesOut' which names an output TXT file
    - 'SoilDetailsOut' which names an output TXT file


"""

#%% User-defined variables

FunctionsLibrary    = 'C:/Users/DH/OneDrive - Heriot-Watt University/Documents/HydrosystemsModellerRA/Writing(Shared)/Paper1/Code' # Set to directory containing CustomFunctionsToSHETRAN.py
DirectoryIn         = 'C:/Users/DH/OneDrive - Heriot-Watt University/Documents/HydrosystemsModellerRA/HydroModelling/HydroInputData/GeologyAndSoil/Hydraul_Param_SoilGrids_Schaap_0/DataGIS/' # Set to directory containing GIS-processed data. NB string must terminate with '/'
ResolutionKM        = '5km'
DirectoryOut        = 'C:/Users/DH/Downloads/'
SuperCatsOut        = 'SoilCats_3Layer'
SoilPropertiesOut   = 'SoilProperties_3Layer'
SoilDetailsOut      = 'SoilDetails_3Layer'


#%% Import modules and functions

import os
import numpy as np
import pandas as pd
import glob
import re

os.chdir(FunctionsLibrary)                                                      # Sets working directory to enable custom functions to be used
from CustomFunctionsToSHETRAN import ASCtoDfParam


#%% Read in each soil parameter ASC grid and specify its size

PathList    = glob.glob(DirectoryIn + '*' + ResolutionKM + '*' + '.asc')        # Create list of files with full path names and extensions

# Find size of ASC by searching through ASC metadata

# Open the first ASC file
File = open(PathList[0])

# Read the content of the file opened
Lines = File.readlines()

# Find metadata lines containing array sizes and return integer
NColsString = "ncols"
NRowsString = "nrows"

for LineNo in range(len(Lines)):
    
    if Lines[LineNo].find(NColsString) != -1:
        Ncols = [int(Num) for Num in re.findall('-?\d+\.?\d*', Lines[LineNo])][0]
        
    elif Lines[LineNo].find(NRowsString) != -1:
        Nrows = [int(Num) for Num in re.findall('-?\d+\.?\d*', Lines[LineNo])][0]
        
    else:
        ''


#%% Create a subgrid of soil categories (i.e. each ASC grid cell)

# Create blank DataFrame to match the ASC array size
DfSubCats = pd.DataFrame(np.zeros([Nrows,Ncols]))

# Populate DataFrame with sequential subgrid numbers (NB including NoData cells)
for Row in range(len(DfSubCats)):                                               # Loop over rows
    for Col in range(len(DfSubCats.columns)):                                   # Loop over cols
        SubCats                 = int(1 + (Ncols * Row) + Col)                  # Create sequential SubCats numbers starting at 1
        DfSubCats.iloc[Row,Col] = SubCats                                       # Save SubCats (integers) to df

# Convert DataFrame to integer
DfSubCats = DfSubCats.astype(int)


#%% Read VanGenuchten parameters from ASCs

# Call ASCtoDfParam function on each ASC
DfVG_ThetaS = ASCtoDfParam(PathList[0], Nrows, Ncols)
DfVG_ThetaR = ASCtoDfParam(PathList[1], Nrows, Ncols)
DfVG_Ksat   = ASCtoDfParam(PathList[2], Nrows, Ncols)
DfVG_Alpha  = ASCtoDfParam(PathList[3], Nrows, Ncols)
DfVG_N      = ASCtoDfParam(PathList[4], Nrows, Ncols)

# Flatten each 2D DataFrame to a 1D Series
SubCats     = pd.Series(DfSubCats.values.flatten())
VG_ThetaS   = pd.Series(DfVG_ThetaS.values.flatten())
VG_ThetaR   = pd.Series(DfVG_ThetaR.values.flatten())
VG_Ksat     = pd.Series(DfVG_Ksat.values.flatten())
VG_Ksat     = VG_Ksat.apply(lambda x: x if x == -999 else x * 0.01 )            # Unit conversion from cm/d to m/d, ignoring NoData -999s
VG_Alpha    = pd.Series(DfVG_Alpha.values.flatten())
VG_N        = pd.Series(DfVG_N.values.flatten())


#%% Create a supergrid of soil categories matching the ASCs

# Use the sets of unique parameters to identify the supergrids
VG_ThetaS_unique            = pd.DataFrame(VG_ThetaS.unique(),columns=['ParamValue'])           # Extract unique values
VG_ThetaS_unique['SubCats'] = VG_ThetaS_unique.index                                            # Add subcats (index by default)
VG_ThetaS_unique_dict       = VG_ThetaS_unique.set_index('ParamValue')['SubCats'].to_dict()     # Create dict with unique ParamValue keys and SubCats values

SuperCats = []                                                                                  # Create list to store supergrid SubCats numbers

# Replace each ParamValue with corresponding SubCats in VG_ThetaS_unique_dict e.g. all -999s = 1
for Item in range(len(VG_ThetaS)):
    Value = VG_ThetaS[Item]
    SuperCats.append(VG_ThetaS_unique_dict.get(Value))                          # Find corresponding SubCats

SuperCats = pd.Series(SuperCats)

# Create DfSuperCats
DfSuperCats = pd.DataFrame().reindex_like(DfSubCats)
DfSuperCats = pd.DataFrame(SuperCats.values.reshape(Nrows,Ncols))

# Write DfSuperCats map to .txt file
DfSuperCats.to_csv(path_or_buf = DirectoryOut + SuperCatsOut + '.txt',
                   index    = False,
                   header   = False,
                   sep      = ' '
                   )


#%% Create supergrid of SoilProperties

# Convert DataFrames to numpy arrays, flatten, then to pandas series
SuperCats       = pd.Series(SuperCats.unique())

VG_SuperThetaS  = pd.Series(DfVG_ThetaS.values.flatten()).unique()
VG_SuperThetaR  = pd.Series(DfVG_ThetaR.values.flatten()).unique()
VG_SuperKsat    = pd.Series(DfVG_Ksat.values.flatten()).unique()
VG_SuperAlpha   = pd.Series(DfVG_Alpha.values.flatten()).unique()
VG_SuperN       = pd.Series(DfVG_N.values.flatten()).unique()


# Create DfSoilProperties with DfSoilSuperCats and VG parameters as columns
DfSoilSuperProperties                    = pd.DataFrame()
DfSoilSuperProperties['SoilProperty']    = pd.Series("<SoilProperty>", index=np.arange(len(SuperCats)))
DfSoilSuperProperties['SuperCats']       = SuperCats
DfSoilSuperProperties['SoilType']        = SuperCats
DfSoilSuperProperties['VG_ThetaS']       = VG_SuperThetaS
DfSoilSuperProperties['VG_ThetaR']       = VG_SuperThetaR
DfSoilSuperProperties['VG_Ksat']         = VG_SuperKsat
DfSoilSuperProperties['VG_alpha']        = VG_SuperAlpha
DfSoilSuperProperties['VG_n']            = VG_SuperN
DfSoilSuperProperties['</SoilProperty>'] = '</SoilProperty>'

# Write DfSoilSuperProperties to CSV file for SHETRAN library file
DfSoilSuperProperties.to_csv(path_or_buf = DirectoryOut + SoilPropertiesOut + '.txt',
                        index = False,
                        header = True,
                        sep = ','
                        )


#%% Create SoilDetails corresponding to SoilProperties for SHETRAN library file

# Create DfSuperDetails
DfSuperDetails                   = pd.DataFrame()
DfSuperDetails['<SoilDetails>']  = pd.Series("<SoilDetail>", index=np.arange(len(SuperCats)))
DfSuperDetails['SuperCats']      = SuperCats
DfSuperDetails['SoilLayer']      = 1
DfSuperDetails['SoilType']       = SuperCats
DfSuperDetails['Depth[m]']       = 2.0
DfSuperDetails['</SoilDetails>'] = pd.Series("</SoilDetail>", index=np.arange(len(SuperCats)))


# Write DfSuperDetails to CSV file for SHETRAN library file
DfSuperDetails.to_csv(path_or_buf = DirectoryOut + SoilDetailsOut + '.txt',
                      index = False,
                      header = True,
                      sep = ','
                      )







