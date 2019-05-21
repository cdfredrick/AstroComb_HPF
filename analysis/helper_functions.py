# -*- coding: utf-8 -*-
"""
Created on Fri Apr 12 16:10:41 2019

@author: cdf1
"""

# %% Imports
import math
import numpy as np
import matplotlib as mpl
#mpl.rcParams['agg.path.chunksize'] = int(1000)
mpl.rcParams['savefig.dpi'] = 200
mpl.rcParams["savefig.format"] = 'pdf'
import matplotlib.pyplot as plt

from cycler import cycler
import datetime
import pytz

from scipy.ndimage.filters import gaussian_filter as _gaussian_filter
from scipy.ndimage.filters import median_filter as _median_filter
from scipy.signal import fftconvolve

from analysis import adev


# %% Constants
class Constants():
    pass
constants = Constants()

constants.c = 299792458 #m/s
constants.c_nm_ps = constants.c*1e-3 # nm/ps, or nm THz
constants.h = 6.62607e-34 #J s


# %% Unit Conversion

def nm_to_THz(x):
    return constants.c_nm_ps/x # nm to THz

def m_to_Hz(x):
    return constants.c/x # m to Hz

def dB(x):
    return 10.*np.log10(x)

def dBm_to_W(x):
    return 1e-3*10**(x/10)

# %% Time Zones
utc_tz = pytz.utc
central_tz = pytz.timezone('US/Central')

def utc_to_ct(dt):
    return (utc_tz.localize(dt.replace(tzinfo=None))).astimezone(central_tz)

def ct_to_utc_conv(dt):
    return (central_tz.localize(dt.replace(tzinfo=None))).astimezone(utc_tz)


# %% Filtering

def gaus_avg(x, sig, offsets):
    np_iter = (np.sum(x * (1/(np.sqrt(2*np.pi)*sig))*np.exp(-np.power(x-center, 2)/(2*sig**2))) for center in offsets)
    return np.fromiter(np_iter, np.float, count=len(offsets))

def med_filt(array, filt_size, num=1):
    for itteration in range(num):
        array = _median_filter(array, filt_size)
    return array

def gaus_filt(array, filt_size, num=1):
    for itteration in range(num):
        array = _gaussian_filter(array, filt_size)
    return array


# %% SI Units
def format_eng(num, unit='', places=None, sep=''):
    """ A port from matplotlib.ticker.EngFormatter
    Formats a number in engineering notation, appending a letter
    representing the power of 1000 of the original number.
    Some examples:

    >>> format_eng(0)       # for self.places = 0
    '0'

    >>> format_eng(1000000) # for self.places = 1
    '1.0 M'

    >>> format_eng("-1e-6") # for self.places = 2
    u'-1.00 \N{GREEK SMALL LETTER MU}'

    `num` may be a numeric value or a string that can be converted
    to a numeric value with ``float(num)``.
    """
    # The SI engineering prefixes
    ENG_PREFIXES = {
        -24: "y",
        -21: "z",
        -18: "a",
        -15: "f",
        -12: "p",
         -9: "n",
         -6: "\N{GREEK SMALL LETTER MU}",
         -3: "m",
          0: "",
          3: "k",
          6: "M",
          9: "G",
         12: "T",
         15: "P",
         18: "E",
         21: "Z",
         24: "Y"
    }

    dnum = float(num)
    sign = 1
    fmt = "g" if places is None else ".{:d}g".format(places)

    if dnum < 0:
        sign = -1
        dnum = -dnum

    if dnum != 0:
        pow10 = int(math.floor(math.log10(dnum) / 3) * 3)
    else:
        pow10 = 0
        # Force dnum to zero, to avoid inconsistencies like
        # format_eng(-0) = "0" and format_eng(0.0) = "0"
        # but format_eng(-0.0) = "-0.0"
        dnum = 0.0

    pow10 = np.clip(pow10, min(ENG_PREFIXES), max(ENG_PREFIXES))

    mant = sign * dnum / (10.0 ** pow10)
    # Taking care of the cases like 999.9..., which
    # may be rounded to 1000 instead of 1 k.  Beware
    # of the corner case of values that are beyond
    # the range of SI prefixes (i.e. > 'Y').
    _fmant = float("{mant:{fmt}}".format(mant=mant, fmt=fmt))
    if _fmant >= 1000 and pow10 != max(ENG_PREFIXES):
        mant /= 1000
        pow10 += 3

    prefix = ENG_PREFIXES[int(pow10)]

    formatted = "{mant:{fmt}}{sep}{prefix}{unit}".format(
        mant=mant, sep=sep, prefix=prefix, unit=unit, fmt=fmt)

    return formatted


# %% Plotting Helpers ---------------------------------------------------------

def plot_setup(fig_ind, count, start=0, stop=.95, size=None,
               dpi=None, clear_fig=True, r_color=False):
    # Create Figure
    plt.figure(fig_ind, clear=clear_fig)
    fig = plt.gcf()
    ax = plt.gca()

    # Color Cyler
    if r_color:
        colormap = plt.cm.nipy_spectral_r
        r_start = 1-stop
        r_stop = 1-start
        start = r_start
        stop = r_stop
    else:
        colormap = plt.cm.nipy_spectral
    ax.set_prop_cycle(cycler('color',[colormap(i) for i in np.linspace(start, stop, count)]))

    # Size in Inches
    if not(size is None):
        fig.set_size_inches(size)

    # DPI
    if not(dpi is None):
        fig.set_dpi(dpi)

    return (fig, ax)

def nonlinear_formatter(__call__, transform, inverse_transform=None):
    '''A decorator for "matplotlib.ticker.Formatter.__call__" method.
    '''
    if inverse_transform is None:
        inverse_transform = transform
    def wrapper(x, pos=None):
        x = transform(x)
        return __call__(x, pos=pos)
    return wrapper

def nonlinear_locator(tick_values, transform, inverse_transform=None):
    '''A decorator for "matplotlib.ticker.Locator.tick_values" method.
    '''
    if inverse_transform is None:
        inverse_transform = transform
    def wrapper(vmin, vmax):
        vlims = transform(np.array([vmin, vmax]))
        vlims.sort()
        return inverse_transform(tick_values(vlims[0], vlims[1]))
    return wrapper

def patch_call(instance, func):
    '''Overrides the "__call__" method of "instance" with "func".
    https://stackoverflow.com/a/38541437
    '''
    class _(type(instance)):
        def __call__(self, *arg, **kwarg):
           return func(*arg, **kwarg)
    instance.__class__ = _

def complementary_x_ticks(old_axis, transform, inverse_transform=None,
                          formatter=None, locator=None, nbins=None):
    '''A convenience function that generates a new x axis with major tick marks
    on complementary units. Best called after the original plot has been
    finalized. Returns the new axes object.

    old_axis:
        a matplotlib axes object (plt.gca())
    transform(x):
        The transform function
    inverse_transform(x):
        The inverse of the conversion function:
            inverse_transform(transform(x)) == x.
        If None, it is assumed that conv_func is its own inverse:
            transform(transform(x)) == x
    formator:
        A "matplotlib.ticker.Formatter" object
    locator:
        A "matplotlib.ticker.Locator" object
    '''
# Inverse Function
    if (inverse_transform is None):
        inverse_transform = transform
# New Axis
    new_axis = old_axis.twiny()
# Formatter
    if formatter is None:
        formatter = new_axis.xaxis.get_major_formatter()
    patch_call(formatter, nonlinear_formatter(formatter.__call__, transform, inverse_transform=inverse_transform))
    new_axis.xaxis.set_major_formatter(formatter)
# Locator
    if (locator is None):
        locator = new_axis.xaxis.get_major_locator()
    locator.tick_values = nonlinear_locator(locator.tick_values, transform, inverse_transform=inverse_transform)
    new_axis.xaxis.set_major_locator(locator)
# Limits
    old_xlim = old_axis.get_xlim()
    new_axis.set_xlim(old_xlim)
# Number of Bins
    if not(nbins is None):
        new_axis.locator_params(axis='x', nbins=nbins)
    return new_axis