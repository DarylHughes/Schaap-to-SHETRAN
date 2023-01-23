# -*- coding: utf-8 -*-
"""
Date created:   2023.01.23
Last modified:  2023.01.23
@author:        Daryl Hughes


This class contains the following functions (modules):
    - NetCDFPlotter             # Plots a variable in space and time
    - NetCDFToSHETRAN           # Wrangles NetCDF data into SHETRAN format
    - WFDE5NetCDFClipper        # Clips raw WFDE5 data in NetCDF format to extent of interest
    - ASCtoDfParam              # Reads in ASC data and writes as DataFrame
        
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from netCDF4 import Dataset


#%%
# Plots a variable in space and time

def NetCDFPlotter(Variable,
                  Data,
                  Time,
                  Lon,
                  Lat,
                  South,
                  North,
                  West,
                  East,
                  UnitConversion,
                  ):
    TimeData    = Data.variables[Variable][:,Lon,Lat]*UnitConversion                      # get time series data for a given lon, lat point
    SpaceData   = Data.variables[Variable][Time,:,:]*UnitConversion                       # get spatial map data for a given time point

    
    # Plot time series
    fig, axes   = plt.subplots(ncols=2, nrows=1, figsize=(12, 5))
    axes[0].plot(TimeData)
    axes[0].set_xlabel('Timestep [hours]')
    axes[0].set_ylabel('Precipitation [mm]')
    axes[0].set_title('Precipitation at point ' + str(Lon) + ',' + str(Lat))
    axes[0].grid(True)
    
    # Plot map
    mp          = axes[1].imshow(SpaceData)
    axes[1].set_xlim(West,East)                                                 # define x extent limits to plot
    axes[1].set_ylim(South,North)                                               # define y extent limits to plot
    axes[1].set_xlabel('Longitude')
    axes[1].set_ylabel('Latitude')
    axes[1].invert_yaxis()
    
    fig.colorbar(mp, ax=axes[1], label ='Precipitation [mm]')
    
    axes[1].grid(True)
    axes[1].scatter(Lon,Lat,s=100, color ='red')                                # plot point

    plt.title(Variable)


#%%
# Wrangles NetCDF data into CSV format for SHETRAN
# NB numbers cells ascending from Row 0 to Row N, Col 0 to Col N
# NB for ERA5 , this is north to south, west to east
# NB for WFDE5, this is south to north, west to 
# NB for MSWEP, this is north to south, west to east?


def NetCDFToSHETRAN(Data,
                    Variable,
                    LongitudeName,
                    LatitudeName,
                    Path,
                    File,
                    UnitConversion,
                    ):
    # Unmask NoData cells
    for k in Data.variables:
          Data.variables[k].set_auto_mask(False)
    
    # Loop through each cell in grid (e.g. 53 cols, 72 rows = 3816 cells)
    NCols = len(Data.variables[LongitudeName])
    NRows = len(Data.variables[LatitudeName])
    
    VarTimeSeriesCells = []
    
    for Lat in range(NRows):                                                    # Loop through Lat
        for Lon in range(NCols):                                                # Loop through Lon
            #CellNo = 1 + Lat * NCols + Lon                                      # Initialise at 1, then count position in grid
            #print('CellNo', CellNo, 'Lat', Lat,'Lon', Lon)                      # Print to check numbering makes sense
            VarTimeSeries = Data.variables[Variable][:,Lat,Lon]
            VarTimeSeries = VarTimeSeries * UnitConversion                      # Convert
            VarTimeSeries = np.round(VarTimeSeries,1)
            #print(VarTimeSeries)
            VarTimeSeriesCells.append(VarTimeSeries)
    #print('NetCDFToSHETRAN: Loop finished')
    
    # Add to Df and add datetime index
    DfVarTimeSeriesCells = pd.DataFrame(data = VarTimeSeriesCells).transpose()
    DfVarTimeSeriesCells.index = Data.variables['time'][:]                      # Add datetime index, to allow time series concatenation
    #print('NetCDFToSHETRAN: Var time series added to df')


    # Write Df to CSV (where each cell has its own col, ready for SHETRAN)
    DfVarTimeSeriesCells.to_csv(path_or_buf=(Path + File))
    #print('NetCDFToSHETRAN: Df written to CSV')
    
    return DfVarTimeSeriesCells


#%%
# Clip WFDE5 NetCDF data from globe to specified extent
def WFDE5NetCDFClipper(Path,
                       FileRaw,
                       IdxWest,
                       IdxEast,
                       IdxNorth,
                       IdxSouth,
                       FileClipped
                       ):
    # From raw WFDE5 NetCDF data, extract arrays of each variable and clip to extent of interest
    WFDE5ClipTime    = FileRaw.variables['time'][:]
    WFDE5ClipLon     = FileRaw.variables['lon'][IdxWest:IdxEast]
    WFDE5ClipLat     = FileRaw.variables['lat'][IdxSouth:IdxNorth]
    WFDE5ClipRainf   = FileRaw.variables['Rainf'][:,IdxSouth:IdxNorth,IdxWest:IdxEast]
    
    # Create blank NetCDF root group to store clipped data array
    WFDE5Clip = Dataset(FileClipped, "w", format="NETCDF4")
    
    # Within the root group, create blank dimension names (time, lon, lat, Rainf) of any size
    WFDE5Clip.createDimension('time',  None)
    WFDE5Clip.createDimension('lon',   None)
    WFDE5Clip.createDimension('lat',   None)
    WFDE5Clip.createDimension('Rainf', None)
    
    # Populate variable dimensions with clipped data
    VarTime     = WFDE5Clip.createVariable('time', 'int',     ('time'));
    #VarTime[:]  = WFDE5ClipTime
    VarTime.setncattr('units','hours since 1900-01-01');VarTime[:] = WFDE5ClipTime
    
    VarLon      = WFDE5Clip.createVariable('lon',  'float',   ('lon'));
    #VarLon[:]   = WFDE5ClipLon
    VarLon.setncattr('units','degrees_east');VarLon[:] = WFDE5ClipLon
    
    VarLat      = WFDE5Clip.createVariable('lat',  'float',   ('lat'));
    #VarLat[:]   = WFDE5ClipLat
    VarLat.setncattr('units','degrees_north');VarLat[:] = WFDE5ClipLat
    
    VarRainf    = WFDE5Clip.createVariable('Rainf','float',   ('Rainf','lat','lon'));
    VarRainf.setncattr('units','kg m-2 s-1');VarRainf[:] = WFDE5ClipRainf
    
    # Close WFDE5Clip NetCDF file
    WFDE5Clip.close()
    
    print('WFDE5NetCDFClipper: Clipped WFDE5 written to:', Path + FileClipped)


#%%
# Reads ASC data and writes as DataFrame
def ASCtoDfParam(Path,
                 Nrows,
                 Ncols):
    with open(Path) as File:                                                    # Read in each line from file
        Lines = File.readlines()
        Lines = [Line.rstrip() for Line in Lines]
        
    # Remove metadata rows
    Lines = Lines [6:]
    
    # Create blank DfParam to store values at x and y
    DfParam = pd.DataFrame(np.zeros([Nrows,Ncols]))
    
    # Split out each parameter string (Ncols) in each line string (Nrows)
    for Line in range(len(Lines)):                                              # Loop over lines
        ColList = (Lines[Line].split())                                         # ColList is a list of string parameters in a line
        
        for Col in range(len(ColList)):                                         # Loop over Cols
            ParamStr                = ColList[Col]                              # ParamStr is a parameter string for a given col in a line
            DfParam.iloc[Line,Col]  = ParamStr                                  # Write to DfParam
        
    # Convert parameter strings to floats
    DfParam.iloc[:,:] = np.float64(DfParam.iloc[:,:])
    
    return(DfParam)

