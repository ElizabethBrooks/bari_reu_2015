############################################################################################################################
# author: Hayden Fuss
# last edited: Tuesday, July 14, 2015
#
# Module for plotting data over a map of greater Boston using census data. Given a tuple/list of dictionaries, which
# have 'lat' and 'lon' key/value pairs, these classes can plot the data over the map. There are both scatter
# and density plotters.
#
# source for making maps: http://sensitivecities.com/so-youd-like-to-make-a-map-using-python-EN.html#.VZGG_VyZ65Y
#
# mass. census tracts: 
#   source: http://catalog.data.gov/dataset/tiger-line-shapefile-2014-state-massachusetts-current-census-tract-state-based-shapefile   07/06/2015
#   date accessed: 07/06/2015
#
# cb tracts: 
#   source: https://www.census.gov/geo/maps-data/data/cbf/cbf_tracts.html
#   date accessed: 07/06/2015
#
##########################################################################################################################

import matplotlib.pyplot as plt
from mpl_toolkits.basemap import Basemap
import numpy as np
import pandas as pd
import fiona
from itertools import chain
from matplotlib.collections import PatchCollection
from shapely.geometry import Point, Polygon, MultiPoint, MultiPolygon
from descartes import PolygonPatch
from pysal.esda.mapclassify import Natural_Breaks as nb
from shapely.prepared import prep
import matplotlib.colors as mplc
from matplotlib.collections import PatchCollection
import matplotlib.cm as cm
# uses os and inspect to determine path to module
import os
import inspect
myDir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))

bostonTracts = '/boston/Tracts_Boston_2010_BARI'
stateTracts = '/mass_cb/gz_2010_25_140_00_500k'
# stateTracts = '/mass_tiger/tl_2014_25_tract'

# list of counties with INCITS: https://en.wikipedia.org/wiki/List_of_counties_in_Massachusetts
countyColors = {'017':'#A64345', '001':'#075B1F', '003':'#FEA39D', '005':'#2AFA7C', 
                '007':'#7E7125', '009':'#4E65EF', '011':'#BC4638', '013':'#C8C736', 
                '015':'#F0BF26', '021':'#02896F', '025':'#6E95A3', '023':'#50658C',
                '027':'#32B126', '019':'#B66497'}
suffolkID = '025'

#####################################################################################################################

class BostonMap(object):
  def __init__(self):
    shp = fiona.open(myDir + bostonTracts + '.shp')
    bds = shp.bounds
    shp.close()
    self.extra = 0.01
    self.ll = (bds[0], bds[1])
    self.ur = (bds[2], bds[3])
    self.coords = list(chain(self.ll, self.ur))
    self.w, self.h = self.coords[2] - self.coords[0], self.coords[3] - self.coords[1]
    return

  def loadBasemap(self):
    self.fig = plt.figure()
    self.ax = self.fig.add_subplot(111)
    self.map = Basemap(
      projection='tmerc',
      lon_0=(self.coords[0] + self.coords[2])/2,
      lat_0=(self.coords[3] + self.coords[1])/2,
      llcrnrlon=self.coords[0] - self.extra * self.w,
      llcrnrlat=self.coords[1] - self.extra + 0.01 * self.h,
      urcrnrlon=self.coords[2] + self.extra * self.w,
      urcrnrlat=self.coords[3] + self.extra + 0.01 * self.h,
      lat_ts=0,
      resolution='h',
      area_thresh=0.01,
      suppress_ticks=True)
    self.loadShapeFile()
    return

  def loadShapeFile(self):
    self.map.readshapefile(
      myDir + stateTracts,
      'boston',
      color='none',
      zorder=2)
    return

  def mapDF(self):
    # set up a map dataframe
    self.df_map = pd.DataFrame({
      'poly': [Polygon(xy) for xy in self.map.boston],
      'land_info': [info for info in self.map.boston_info]})

    self.df_map['area_m'] = self.df_map['poly'].map(lambda x: x.area)
    self.df_map['area_km'] = self.df_map['area_m'] / 100000
    
    return

  def patchesDF(self):
    # draw tract patches from polygons
    self.df_map['patches'] = self.df_map['poly'].map(lambda x: PolygonPatch(
      x,
      fc='#000055',
      ec='#787878', lw=.25, alpha=.9,
      zorder=4))
    return

  # virtual function to be overridden
  def dataDF(self):
    return

  def buildDFs(self):
    self.mapDF()
    self.dataDF()
    self.patchesDF()
    return

  def leverettG(self):
    # plot leverett g tower for fun
    x,y = self.map(-71.1161, 42.3692)
    self.map.plot(x, y, 'go', markersize=5)
    return

  def mapScale(self):
    # Draw a map scale
    self.map.drawmapscale(
      self.coords[0] + self.w/4, self.coords[3],
      self.coords[0], self.coords[1],
      2.,
      barstyle='fancy', labelstyle='simple',
      fillcolor1='w', fillcolor2='#000055',
      fontcolor='#000055',
      zorder=5,
      units='mi')
    return

  def colorScale(self):
    return

  def tracts(self):
    # plot tracts by adding the PatchCollection to the axes instance
    self.ax.add_collection(PatchCollection(self.df_map['patches'].values, match_original=True))
    return

  # virtual function to be overridden
  def data(self):
    self.leverettG()
    return

  def makePlot(self, outname, title):
    plt.title(title)
    self.fig.set_size_inches(10, (self.h/self.w)*10)
    plt.savefig(outname + '.png', dpi=100, alpha=True)
    return

  def plotMap(self, outname='boston', title='Boston'):
    self.loadBasemap()
    self.buildDFs()
    self.mapScale()
    self.colorScale()
    self.tracts()
    self.data()
    self.makePlot(outname, title)
    return

#####################################################################################################################

class BostonScatter(BostonMap):
  def __init__(self, dataPoints):
    self.dataPoints = dataPoints
    # call parent constructor
    super(BostonScatter, self).__init__()
    return

  def dataDF(self):
    output = {'lon':[], 'lat':[]}
    for d in self.dataPoints:
      for each in ('lon', 'lat'):
        output[each].append(d[each])
    df = pd.DataFrame(output)
    df[['lon', 'lat']] = df[['lon', 'lat']].astype(float)
    self.dataPoints = pd.Series(
      [Point(self.map(mapped_x, mapped_y)) for mapped_x, mapped_y in zip(df['lon'], df['lat'])])
    return

  def data(self):
    self.map.scatter(
      [geom.x for geom in self.dataPoints],
      [geom.y for geom in self.dataPoints],
      10, marker='o', lw=.25,
      facecolor='#33ccff', edgecolor='w',
      alpha=0.9, antialiased=True, zorder=3)
    return

  def patchesDF(self):
    self.df_map['patches'] = [PolygonPatch(row['poly'],
      fc=countyColors[row['land_info']['COUNTY']], ec='k',
      lw=0.25 if (row['land_info']['COUNTY'] != suffolkID) else 0.8,
      alpha=.9, zorder=4) for i,row in self.df_map.iterrows()]
    return

#####################################################################################################################

class CoastlineBostonScatter(BostonScatter):
  def __init__(self, dataPoints):
    super(GreaterBostonScatter, self).__init__(dataPoints)
    return

  # override so polygon patches arent added
  def tracts(self):
    return

  def mapScale(self):
    super(BostonScatter, self).mapScale()
    return

  # override so dataframe of map isnt made, instead draw boundaries and fill in colors
  def mapDF(self):
    self.map.drawmapboundary(color='w', fill_color='aqua')
    self.map.drawcoastlines()
    self.map.fillcontinents(color='coral', lake_color='aqua')
    return

  # overriden
  def patchesDF(self):
    return

  def loadShapeFile(self):
    self.map.readshapefile(
      myDir + stateTracts,
      'boston',
      zorder=2)
    return

#####################################################################################################################

# Convenience functions for working with colour ramps and bars
# from map-making source
def colorbar_index(ncolors, cmap, labels=None, **kwargs):
    """
    This is a convenience function to stop you making off-by-one errors
    Takes a standard colour ramp, and discretizes it,
    then draws a colour bar with correctly aligned labels
    """
    cmap = cmap_discretize(cmap, ncolors)
    mappable = cm.ScalarMappable(cmap=cmap)
    mappable.set_array([])
    mappable.set_clim(-0.5, ncolors+0.5)
    colorbar = plt.colorbar(mappable, **kwargs)
    colorbar.set_ticks(np.linspace(0, ncolors, ncolors))
    colorbar.set_ticklabels(range(ncolors))
    if labels:
      colorbar.set_ticklabels(labels)
    return colorbar

def cmap_discretize(cmap, N):
    """
    Return a discrete colormap from the continuous colormap cmap.

        cmap: colormap instance, eg. cm.jet. 
        N: number of colors.

    Example
        x = resize(arange(100), (5,100))
        djet = cmap_discretize(cm.jet, 5)
        imshow(x, cmap=djet)

    """
    if type(cmap) == str:
      cmap = get_cmap(cmap)
    colors_i = np.concatenate((np.linspace(0, 1., N), (0., 0., 0., 0.)))
    colors_rgba = cmap(colors_i)
    indices = np.linspace(0, 1., N + 1)
    cdict = {}
    for ki, key in enumerate(('red', 'green', 'blue')):
      cdict[key] = [(indices[i], colors_rgba[i - 1, ki], colors_rgba[i, ki]) for i in xrange(N + 1)]
    return mplc.LinearSegmentedColormap(cmap.name + "_%d" % N, cdict, 1024)

##########################################################################################################################

class BostonDensity(BostonScatter):
  def __init__(self, dataPoints):
    super(BostonDensity, self).__init__(dataPoints)
    return

  def dataDF(self):
    super(BostonDensity, self).dataDF()

    self.df_map['count'] = self.df_map['poly'].map(lambda x: int(len(filter(prep(x).contains, self.dataPoints))))
    self.df_map['density_m'] = self.df_map['count'] / self.df_map['area_m']
    self.df_map['density_km'] = self.df_map['count'] / self.df_map['area_km']
    # it's easier to work with NaN values when classifying
    self.df_map.replace(to_replace={'density_m': {0: np.nan}, 'density_km': {0: np.nan}}, inplace=True)

    self.breaks = nb(
      self.df_map[self.df_map['density_km'].notnull()].density_km.values,
      initial=300,
      k=5)
    # the notnull method lets us match indices when joining
    jb = pd.DataFrame({'jenks_bins': self.breaks.yb}, index=self.df_map[self.df_map['density_km'].notnull()].index)
    self.df_map = self.df_map.join(jb)
    self.df_map.jenks_bins.fillna(-1, inplace=True)

    return

  def patchesDF(self):
    # use a blue colour ramp - we'll be converting it to a map using cmap()
    self.cmap = plt.get_cmap('Blues')
    # draw tracts with black outline. make suffolk (boston) thicker
    self.df_map['patches'] = [PolygonPatch(row['poly'], ec='k',
      lw=0.25 if (row['land_info']['COUNTY'] != suffolkID) else 0.8,
      alpha=.9, zorder=4) for i,row in self.df_map.iterrows()]

    self.jenks_labels = ["<= %0.1f/km$^2$(%s tracts)" % (b, c) for b, c in zip(
    self.breaks.bins, self.breaks.counts)]
    self.jenks_labels.insert(0, '<= 0.0/km$^2$(%s tracts)' % len(self.df_map[self.df_map['density_km'].isnull()]))
    return

  def data(self):
    highest = '\n'.join([row['land_info']['TRACT'] + " => " + 
                        str(row['density_km']) for i, row in self.df_map[
                        (self.df_map['jenks_bins'] == 4)][:30].sort(columns='density_km',
                        ascending=False).iterrows()])
    highest = 'Most Dense Wards:\n\n' + highest
    print highest
    for each in self.df_map['land_info'][0:10]:
      print

    return

  def tracts(self):
    self.pc = PatchCollection(self.df_map['patches'], match_original=True)
    # impose our colour map onto the patch collection
    norm = mplc.Normalize()
    self.pc.set_facecolor(self.cmap(norm(self.df_map['jenks_bins'].values)))
    self.ax.add_collection(self.pc)
    return

  def colorScale(self):
    # Add a colour bar
    cb = colorbar_index(ncolors=len(self.jenks_labels), cmap=self.cmap, shrink=0.5, labels=self.jenks_labels)
    cb.ax.tick_params(labelsize=6)
    return

#########################################################################################################################

class GreaterBostonScatter(BostonScatter):
  def __init__(self, dataPoints):
    self.dataPoints = dataPoints
    self.extra = 0.01
    self.ll = (-71.5457, 42.1697)
    self.ur = (-70.8975, 42.4014)
    self.coords = list(chain(self.ll, self.ur))
    self.w, self.h = self.coords[2] - self.coords[0], self.coords[3] - self.coords[1]
    return

  def makePlot(self, outname, title):
    plt.title(title)
    self.fig.set_size_inches((self.w/self.h)*10, 10)
    plt.savefig(outname + '.png', dpi=100, alpha=True)
    return

#########################################################################################################################

class GreaterBostonDensity(BostonDensity):
  def __init__(self, dataPoints):
    self.dataPoints = dataPoints
    self.extra = 0.01
    self.ll = (-71.5457, 42.1697)
    self.ur = (-70.8975, 42.4014)
    self.coords = list(chain(self.ll, self.ur))
    self.w, self.h = self.coords[2] - self.coords[0], self.coords[3] - self.coords[1]
    return

  def makePlot(self, outname, title):
    plt.title(title)
    self.fig.set_size_inches((self.w/self.h)*10, 10)
    plt.savefig(outname + '.png', dpi=100, alpha=True)
    return

#######################################################################################################################

def testMap():
  out = raw_input("Enter name of output png: ")
  boston = BostonMap()
  boston.plotMap(outname=out)

def testScatter():
  out = raw_input("Enter name of output png: ")
  testData = [
    {'lon':'-71.0120751', 'lat':'42.27090738'},
    {'lon':'-71.1864942', 'lat':'42.36610796'},
    {'lon':'-71.0530936', 'lat':'42.35931187'}
  ]
  boston = GreaterBostonScatter(testData)
  boston.plotMap(outname=out, title='Scatterplot Over Boston')
  return

#####################################################################################################################

if __name__ == "__main__":
  testScatter()
  plt.show()