import argparse
import json

import harp
import numpy as np
#import matplotlib.pyplot as plt
#import cartopy.crs as ccrs
#from cmcrameri import cm


def get_bin_spatial_string(conf):
    """ Construct bin_spatial input string for harp.
    
    Keyword arguments:
    conf -- config dictionary

    Return:
    bin_spatial_string -- input string for harp
    """

    lat_min = conf["variable"]["lat_min"]
    lat_max = conf["variable"]["lat_max"]
    lat_step = conf["variable"]["lat_step"]
    lon_min = conf["variable"]["lon_min"]
    lon_max = conf["variable"]["lon_max"]
    lon_step = conf["variable"]["lon_step"]

    lat_edge_length = int(abs(lat_max - lat_min)/lat_step+1)
    lon_edge_length = int(abs(lon_max - lon_min)/lon_step+1)

    bin_spatial_string = f"bin_spatial({lat_edge_length}, {lat_min}, {lat_step}, {lon_edge_length}, {lon_min}, {lon_step})"

    return bin_spatial_string
    

def merge_and_regrid(conf, infiles):
    """ Regrid and merge multiple l2 input files into one l3 output file.

    Code is originally from Atmospheric tool box harp tutorial:
    https://atmospherictoolbox.org/usecases/Usecase_2_S5P_AAI_Siberia_Smoke/

    Keyword arguments:
    conf -- config dictionary
    infiles -- input filenames, contains star as a wildcard character

    Return:
    merged -- regridded and merged data
    """
    
    bin_spatial_string = get_bin_spatial_string(conf)

    operations = ";".join([
        f'{conf["variable"]["harp_var_name"]}_validity>{conf["variable"]["validity_min"]}',
        f'keep(latitude_bounds,longitude_bounds,datetime_start,datetime_length,{conf["variable"]["harp_var_name"]})',
        "derive(datetime_stop {time} [days since 2000-01-01])",
        "derive(datetime_start [days since 2000-01-01])",
        "exclude(datetime_length)",
        bin_spatial_string,
        "derive(latitude {latitude})",
        "derive(longitude {longitude})",
    ])
    
    reduce_operations = "squash(time, (latitude, longitude, latitude_bounds, longitude_bounds));bin()"
    merged = harp.import_product(infiles, operations, reduce_operations=reduce_operations)

    return merged
    

def main():

    # Get config
    config_file = f"conf/{options.var}.json"
    with open(config_file, "r") as jsonfile:
        conf = json.load(jsonfile)

    # Merge and re-grid files
    infiles = f'{conf["input"]["path"]}/{conf["input"]["filename"].format(date=options.date)}'
    outfile = f'{conf["output"]["path"]}/{conf["output"]["filename"].format(date=options.date)}'
    merged = merge_and_regrid(conf, infiles, outfile)

    # Write merged data to l3 output file
    harp.export_product(merged, outfile)    

    
if __name__ == '__main__':
    #Parse commandline arguments       
    parser = argparse.ArgumentParser()
    parser.add_argument('--var',
                        type = str,
                        default = 'o3-nrti',
                        help = 'Tropomi variable to regrid and plot. Options: no2-nrti, so2-nrti, co-nrti, o3-nrti')
    parser.add_argument('--date',
                        type = str,
                        default = '20221013',
                        help = 'Date to regrid and plot.')

    options = parser.parse_args()
    main()
