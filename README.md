# tropomi-l2-to-l3
Merge and re-grid multiple TROPOMI l2 files to one l3 file.

## Usage
### Installation
Needed python packages are listed in `environment.yml` file, which can be used to setup conda environment for running the code.

Setup conda environment: `$ conda env create -f environment.yml -n tropomi`

Activate conda environment: `$ conda activate tropomi`

### Running

Run the code: `$ python tropomi-l2-to-l3.py --var="no2-nrti" --date="20221102"`

Input parameters are:
- `var`: variable name, which is used to find correct configuration .json file
- `date`: date to plot

### Configurations
Configurations for each variable are located in `/conf` directory. Configuration .json files are called `variable.json` (e.g. `no2-nrti.json`). Separate input and output configurations can be given for daily/monthly averaged data.

#### Input configurations
- `path`: path for input files
- `filename`: input filenames to be merged (containing placeholder inside {} for date and star as a wildcard)

#### Variable configurations 
- `harp_var_name`: variable name in HARP
- `unit`: units to which harp converts input data
- `validity_min`: minimum data validity/qa_value for merged data (data below this validity is excluded in merging)
- `lat_min`: minimum latitude for data to be merged
- `lat_max`: maximum latitude for data to be merged
- `lat_step`: output resolution in latitude degrees
- `lon_min`: minimum longitude for data to be merged
- `lon_max`: maximum longitude for data to be merged
- `lon_step`: output resolution in longitude degrees

#### Output configurations
- `path`: output path
- `filename`: filename for merged l3 product (containing date placeholder inside {})
