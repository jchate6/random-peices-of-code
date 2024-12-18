"""
Creates a guide frame movie gif when given a series of guide frames
Based on code written by Adam Tedeschi for NeoExchange
Date: 8/10/2018

Edited 2018/09/04 by Joey Chatelain
Edited 2018/09/10 by Joey Chatelain -- fix Bounding boxes, clean bottom axis, add frame numbers
Edited 2018/09/18 by Joey Chatelain -- print Request number rather than tracking number. Make Filename more specific.
Edited 2018/10/09 by Joey Chatelain -- accomodate older guide frames (from May 2018)
Edited 2019/05/10 by Joey Chatelain -- eliminate projection warning, add progress bar.
Edited 2019/08/14 by Joey Chatelain -- Add postage stamp option
"""

import sys
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as colors
from matplotlib.animation import FuncAnimation
from astropy.io import fits
from astropy.wcs import WCS
from astropy.wcs._wcs import InvalidTransformError
from astropy.visualization import ZScaleInterval
from datetime import datetime
import os
from glob import glob
import argparse
import warnings


def print_progress_bar(iteration, total, prefix='', suffix='', decimals=1, length=100, fill='█', time_in=None):
    """
    Call in a loop to create terminal progress bar
    @params:
        iteration   - Required  : current iteration (Int)
        total       - Required  : total iterations (Int)
        prefix      - Optional  : prefix string (Str)
        suffix      - Optional  : suffix string (Str)
        decimals    - Optional  : positive number of decimals in percent complete (Int)
        length      - Optional  : character length of bar (Int)
        fill        - Optional  : bar fill character (Str)
        time_in     - Optional  : if given, will estimate time remaining until completion (Datetime object)
    """
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filled_length = int(length * iteration // total)
    bar = fill * filled_length + '-' * (length - filled_length)
    if time_in is not None:
        now = datetime.now()
        delta_t = now-time_in
        delta_t = delta_t.total_seconds()
        total_time = delta_t/iteration*(float(total)-iteration)
        # print(total_time, delta_t, iteration, float(total))
        if total_time > 90:
            time_left = '| {0:.1f} min remaining |'.format(total_time/60)
        elif total_time > 5400:
            time_left = '| {0:.1f} hrs remaining |'.format(total_time/60/60)
        else:
            time_left = '| {0:.1f} sec remaining |'.format(total_time)
    else:
        time_left = ' '
    print('\r%s |%s| %s%%%s%s' % (prefix, bar, percent, time_left, suffix), end='\r')
    # Print New Line on Complete
    if iteration == total:
        print()


def make_gif(frames, title=None, sort=True, fr=100, init_fr=1000, tr=False, center=False, progress=False):
    """
    takes in list of .fits guide frames and turns them into a moving gif.
    <frames> = list of .fits frame paths
    <title> = [optional] string containing gif title, set to empty string or False for no title
    <sort> = [optional] bool to sort frames by title (Which usually corresponds to date)
    <fr> = frame rate for output gif in ms/frame [default = 100 ms/frame or 10fps]
    <init_fr> = frame rate for first 5 frames in ms/frame [default = 1000 ms/frame or 1fps]
    output = savefile (path of gif)
    """
    if sort is True:
        fits_files = np.sort(frames)
    else:
        fits_files = frames
    path = os.path.dirname(frames[0]).lstrip(' ')

    start_frames = 5
    copies = 1
    if init_fr and init_fr > fr and len(fits_files) > start_frames:
        copies = init_fr // fr
        i = 0
        while i < start_frames * copies:
            c = 1
            while c < copies:
                fits_files = np.insert(fits_files, i, fits_files[i])
                i += 1
                c += 1
            i += 1

    # pull header information from first fits file
    with fits.open(fits_files[0], ignore_missing_end=True) as hdul:
        try:
            header = hdul['SCI'].header
        except KeyError:
            try:
                header = hdul['COMPRESSED_IMAGE'].header
            except KeyError:
                header = hdul[0].header
        # create title
        obj = header['OBJECT']
        try:
            rn = header['REQNUM'].lstrip('0')
        except KeyError:
            rn = 'UNKNOWN'
        try:
            site = header['SITEID'].upper()
        except KeyError:
            site = ' '
        try:
            inst = header['INSTRUME'].upper()
        except KeyError:
            inst = ' '

    if title is None:
        # title = 'Request Number {} -- {} at {} ({})'.format(rn, obj, site, inst)
        title = 'LCOGT 1 meter Telescope at SAAO South Africa'

    fig = plt.figure(figsize=(10, 10))
    if title:
        fig.suptitle(title, size='25', y=.93)

    time_in = datetime.now()

    def update(n):
        """ this method is required to build FuncAnimation
        <file> = frame currently being iterated
        output: return plot.
        """

        # get data/Header from Fits
        with fits.open(fits_files[n], ignore_missing_end=True) as hdul:
            try:
                header_n = hdul['SCI'].header
                data = hdul['SCI'].data
            except KeyError:
                try:
                    header_n = hdul['COMPRESSED_IMAGE'].header
                    data = hdul['COMPRESSED_IMAGE'].data
                except KeyError:
                    header_n = hdul[0].header
                    data = hdul[0].data
        if center:
            shape = data.shape
            x_frac = int(shape[0]/2.5)
            y_frac = int(shape[1]/2.5)
            data = data[x_frac:-x_frac, y_frac:-y_frac]
            header_n['CRPIX1'] = header_n['CRPIX1'] - x_frac
            header_n['CRPIX2'] = header_n['CRPIX2'] - y_frac

        # dat_med = np.median(data)
        # data -= dat_med
        # pull Date from Header
        try:
            date_obs = header_n['DATE-OBS']
        except KeyError:
            date_obs = header_n['DATE_OBS']
        try:
            date = datetime.strptime(date_obs, '%Y-%m-%dT%H:%M:%S.%f')
        except ValueError:
            date = datetime.strptime(date_obs, '%Y-%m-%dT%H:%M:%S')
        # reset plot
        ax = plt.gca()
        ax.clear()
        ax.axis('off')
        z_interval = ZScaleInterval().get_limits(data)  # set z-scale
        try:
            # set wcs grid/axes
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                wcs = WCS(header_n)  # get wcs transformation
                ax = plt.gca(projection=wcs)
            dec = ax.coords['dec']
            dec.set_major_formatter('dd:mm')
            dec.set_ticks_position('br')
            dec.set_ticklabel_position('br')
            dec.set_ticklabel(fontsize=10, exclude_overlapping=True)
            ra = ax.coords['ra']
            ra.set_major_formatter('hh:mm:ss')
            ra.set_ticks_position('lb')
            ra.set_ticklabel_position('lb')
            ra.set_ticklabel(fontsize=10, exclude_overlapping=True)
            ax.coords.grid(color='black', ls='solid', alpha=0.5)
        except (InvalidTransformError, AttributeError):
            pass
        # finish up plot
        current_count = len(np.unique(fits_files[:n+1]))
        ax.set_title('UT Date: {} ({} of {})'.format(date.strftime('%x %X'), current_count, int(len(fits_files)-(copies-1)*start_frames)), pad=10, size='25')

        # norm = colors.SymLogNorm(linthresh=np.std(data), linscale=.1, vmin=z_interval[0], vmax=z_interval[1])
        # norm = colors.SymLogNorm(linthresh=np.std(data), linscale=.5, vmin=-50, vmax=70)
        norm = colors.PowerNorm(gamma=1, vmin=z_interval[0], vmax=z_interval[1])
        plt.imshow(data, cmap='gray', norm=norm)

        # If first few frames, add 5" and 15" reticle
        if (current_count < 6 and fr != init_fr) and tr:
            circle_5arcsec = plt.Circle((header_n['CRPIX1'], header_n['CRPIX2']), 5/header_n['PIXSCALE'], fill=False, color='limegreen', linewidth=1.5)
            circle_15arcsec = plt.Circle((header_n['CRPIX1'], header_n['CRPIX2']), 15/header_n['PIXSCALE'], fill=False, color='lime', linewidth=1.5)
            ax.add_artist(circle_5arcsec)
            ax.add_artist(circle_15arcsec)

        if progress:
            print_progress_bar(n+1, len(fits_files), prefix='Creating Gif: Frame {}'.format(current_count), time_in=time_in)
        return ax

    ax1 = update(0)
    plt.tight_layout(pad=4)

    # takes in fig, update function, and frame rate set to fr
    anim = FuncAnimation(fig, update, frames=len(fits_files), blit=False, interval=fr)

    savefile = os.path.join(path, obj.replace(' ', '_').replace('/', '_') + '_' + rn + '_guidemovie.gif')
    anim.save(savefile, dpi=90, writer='imagemagick')

    return savefile


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("path", help="Path to directory containing .fits or .fits.fz files", type=str)
    parser.add_argument("--fr", help="Frame rate in ms/frame (Defaults to 100 ms/frame or 10 frames/second", default=100, type=float)
    parser.add_argument("--ir", help="Frame rate in ms/frame for first 5 frames (Defaults to 1000 ms/frame or 1 frames/second", default=1000, type=float)
    parser.add_argument("--tr", help="Add target circle at crpix values?", default=False, action="store_true")
    parser.add_argument("--C", help="Only include Center Snapshot", default=False, action="store_true")
    args = parser.parse_args()
    path = args.path
    fr = args.fr
    ir = args.ir
    tr = args.tr
    center = args.C
    print("Base Framerate: {}".format(fr))
    if path[-1] != '/':
        path += '/'
    files = np.sort(glob(path+'*.fits.fz'))
    if len(files) < 1:
        files = np.sort(glob(path+'*.fits'))
    if len(files) >= 1:
        gif_file = make_gif(files, fr=fr, init_fr=ir, tr=tr, center=center, progress=True)
        print("New gif created: {}".format(gif_file))
    else:
        print("No files found.")


