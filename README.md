This is a PyQGIS script

What will often happen when you produce a mosaicked DEM is that later on new data will come through that you may want to use to override the existing elevation data

Simply sitting the new DEM over the top of the existing DEM will leave a rough edge at the bounds of the new DEM

This script allows you to put a new DEM on top of a base DEM and blend the edges in

The extent of the new DEM must be fully contained in the extent of the base DEM for this to work

Additionally, the pixel sizes must be the same

Any improvements on this script, let me know
