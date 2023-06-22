import argparse
import json
import logging
import time
import glob
import os

import harp
import numpy as np
import netCDF4 as nc


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


def merge_and_regrid(conf, infiles, timeperiod, variable):
    """ Regrid and merge multiple l2 input files into one l3 output file.

    Keyword arguments:
    conf -- config dictionary
    infiles -- input filenames, contains star as a wildcard character
    timeperiod -- timeperiod to merge, day|month
    variable -- variable to merge

    Return:
    merged -- regridded and merged data
    """
    bin_spatial_string = get_bin_spatial_string(conf)

    first_input_file = glob.glob(infiles)[0]

    data = harp.import_product(first_input_file)

    if timeperiod == "day":
        
        logger.debug('Merging one day of data.')

        if "no2" in variable or "co-" in variable:
            operations = ";".join([
                f'{conf["variable"]["harp_var_name"]}_validity>{conf["variable"]["validity_min"]}',
                "derive(solar_hour_angle {time})", f"solar_hour_angle>{22.5-65}", f"solar_hour_angle<{22.5+65}",
                f'keep(latitude_bounds,longitude_bounds,datetime_start,datetime_length,{conf["variable"]["harp_var_name"]},{conf["variable"]["harp_var_name"]}_uncertainty)',
                f'derive({conf["variable"]["harp_var_name"]} float [{conf["variable"]["unit"]}])',
                f'derive({conf["variable"]["harp_var_name"]}_uncertainty float [{conf["variable"]["unit"]}])',
                "derive(datetime_stop {time} [days since 2000-01-01])",
                "derive(datetime_start [days since 2000-01-01])",
                "exclude(datetime_length)",
                bin_spatial_string,
                "derive(latitude float {latitude})",
                "derive(longitude float {longitude})"
            ])

        else:            
            operations = ";".join([
                f'{conf["variable"]["harp_var_name"]}_validity>{conf["variable"]["validity_min"]}',
                f'keep(latitude_bounds,longitude_bounds,datetime_start,datetime_length,{conf["variable"]["harp_var_name"]},{conf["variable"]["harp_var_name"]}_uncertainty)',
                f'derive({conf["variable"]["harp_var_name"]} float [{conf["variable"]["unit"]}])',
                f'derive({conf["variable"]["harp_var_name"]}_uncertainty float [{conf["variable"]["unit"]}])',
                "derive(datetime_stop {time} [days since 2000-01-01])",
                "derive(datetime_start [days since 2000-01-01])",
                "exclude(datetime_length)",
                bin_spatial_string,
                "derive(latitude float {latitude})",
                "derive(longitude float {longitude})"
            ])

        reduce_operations = 'squash(time, (latitude, longitude, latitude_bounds, longitude_bounds));set("propagate_uncertainty", "correlated");bin()'
        post_operations = "exclude(weight, longitude_bounds, latitude_bounds)"

        logger.debug(f'Merging files {infiles} into one')
        try:
            if conf["variable"]["harp_options"]:
                merged = harp.import_product(infiles, operations, reduce_operations = reduce_operations, post_operations = post_operations, options=conf["variable"]["harp_options"])
            else:
                merged = harp.import_product(infiles, operations, reduce_operations = reduce_operations, post_operations = post_operations)
        except Exception as e:
            logger.error(f'Error while merging files with HARP')
            logger.error(e)
        
    elif timeperiod == "month":
        logger.debug(f'Merging one month of data and using already merged l3 data as input.')
        
        post_operations = "squash(time, (latitude, longitude));bin()"
        
        logger.debug(f'Merging files {infiles} into one')
        try:
            merged = harp.import_product(infiles, post_operations = post_operations)
        except Exception as e:
            logger.error(f'Error while merging files with HARP')
            logger.error(e)
            
    else:
        raise ValueError(f"Given timeperiod {timeperiod} is not valid.")
        
    return merged


def read_attributes_from_file(netcdf_file):
    """ Read extra attributes (not supported by HARP) 
    from first input file.
    
    Keyword arguments:
    netcdf_file -- input file

    Return:
    processor_version -- processor_version attribute

    """
    
    with nc.Dataset(netcdf_file, 'r', format='NETCDF4') as nc_file:        
        processor_version = nc_file.getncattr('processor_version')

    return processor_version


def edit_netcdf_file(netcdf_file, processor_version):
    """ Add extra attributes to file using netCDF4 library. 
    Has to be done separately because HARP does not support this.

    Keyword arguments:
    netcdf_file -- merged output file
    processor_version -- processor_version attribute

    Return:
    nc_file -- output file with added attributes
    """

    logger.debug(f'Adding extra attributes to file {netcdf_file}')
    try:
        with nc.Dataset(netcdf_file, 'a', format='NETCDF4') as nc_file:
            # Add global attributes
            nc_file.data_provider = "Finnish Meteorological Institute"
            nc_file.data_origin = "Copernicus Sentinel-5P/TROPOMI"
            nc_file.legal_notice = "Contains modified Copernicus Sentinel data processed by Finnish Meteorological Institute."
            nc_file.processor_version = processor_version
            
    except Exception as e:
        logger.error(f'Error while writing attribute to file {netcdf_file}')
        logger.error(e)
            
    return nc_file


def main():

    # Get config
    config_file = f"conf/{options.var}.json"
    logger.debug(f'Reading config file {config_file}')
    try:
        with open(config_file, "r") as jsonfile:
            conf = json.load(jsonfile)
    except Exception as e:
        logger.error(f'Error while reading the configuration file {config_file}')
        logger.error(e)

    # Merge and re-grid files
    infiles = f'{conf["input"][options.timeperiod]["path"]}/{conf["input"][options.timeperiod]["filename"].format(date=options.date)}'
    outfile = f'{conf["output"][options.timeperiod]["path"]}/{conf["output"][options.timeperiod]["filename"].format(date=options.date)}'
    merged = merge_and_regrid(conf, infiles, options.timeperiod, options.var)
    
    # Write merged data to l3 output file
    logger.debug(f'Writing merged product to file {outfile}')
    harp.export_product(merged, outfile)

    # Read attributes from netcdf file using netCDF4 reader
    first_input_file = glob.glob(infiles)[0]
    processor_version = read_attributes_from_file(first_input_file)
    
    # Add extra attributes to output file
    outfile = edit_netcdf_file(outfile, processor_version)

    
if __name__ == '__main__':
    #Parse commandline arguments       
    parser = argparse.ArgumentParser()
    parser.add_argument('--var',
                        type = str,
                        default = 'no2-nrti',
                        help = 'Tropomi variable to regrid and plot. Options: no2-nrti, so2-nrti, co-nrti, o3-nrti')
    parser.add_argument('--date',
                        type = str,
                        default = '20221101',
                        help = 'Date to regrid and plot.')
    parser.add_argument('--timeperiod',
                        type = str,
                        default = 'day',
                        help = 'Time period to merge. Options: day|month')
    parser.add_argument('--loglevel',
                        default='info',
                        help='minimum severity of logged messages,\
                        options: debug, info, warning, error, critical, default=info')

    options = parser.parse_args()

    # Setup logger
    loglevel_dict={'debug':logging.DEBUG,
                   'info':logging.INFO,
                   'warning':logging.WARNING,
                   'error':logging.ERROR,
                   'critical':logging.CRITICAL}
    logger = logging.getLogger("logger")
    logger.setLevel(loglevel_dict[options.loglevel])
    formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s | (%(filename)s:%(lineno)d)','%Y-%m-%d %H:%M:%S')
    logging.Formatter.converter = time.gmtime # use utc                                                      
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    main()
