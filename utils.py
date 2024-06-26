import glob
import os
import sys
import subprocess

from configparser import ConfigParser

import numpy as np
import pandas as pd

from astropy import units as u
from astropy.io import ascii
from astropy.io import fits as pyfits
from radio_beam import Beam, Beams, commonbeam

import fits_magic as fm


def load_config(config_object, file_=None):
    """
    Function to load the config file
    """
    config = ConfigParser()  # Initialise the config parser
    config.readfp(open(file_))
    for s in config.sections():
        for o in config.items(s):
            setattr(config_object, o[0], eval(o[1]))
    return config  # Save the loaded config file as defaults for later usage


def set_mosdirs(self):
    """
    Creates the directory names for the subdirectories to make scripting easier
    """
    self.qacontdir = os.path.join(self.qadir, 'continuum')
    self.qapoldir = os.path.join(self.qadir, 'polarisation')

    self.contworkdir = os.path.join(self.basedir, self.obsid, self.mossubdir, self.moscontdir)
    self.contimagedir = os.path.join(self.contworkdir, 'images')
    self.contbeamdir = os.path.join(self.contworkdir, 'beams')
    self.contmosaicdir = os.path.join(self.contworkdir, 'mosaic')

    self.polworkdir = os.path.join(self.basedir, self.obsid, self.mossubdir, self.mospoldir)
    self.polimagedir = os.path.join(self.polworkdir, 'images')
    self.polbeamdir = os.path.join(self.polworkdir, 'beams')
    self.polmosaicdir = os.path.join(self.polworkdir, 'mosaic')

    self.circworkdir = os.path.join(self.basedir, self.obsid, self.mossubdir, self.moscircdir)
    self.circimagedir = os.path.join(self.circworkdir, 'images')
    self.circbeamdir = os.path.join(self.circworkdir, 'beams')
    self.circmosaicdir = os.path.join(self.circworkdir, 'mosaic')


################################
#### CONTINUUM SUBFUNCTIONS ####
################################

def gen_contdirs(self):
    """
    Function to generate the necessary continuum directories
    """
    if os.path.isdir(self.contworkdir):
        pass
    else:
        os.makedirs(self.contworkdir)

    if os.path.isdir(self.contimagedir):
        pass
    else:
        os.makedirs(self.contimagedir)

    if os.path.isdir(self.contbeamdir):
        pass
    else:
        os.makedirs(self.contbeamdir)

    if os.path.isdir(self.contmosaicdir):
        pass
    else:
        os.makedirs(self.contmosaicdir)


def copy_contimages(self):
    """
    Function to copy the continuum images to the working directory
    """
    if self.cont_mode == 'all':
        # copy all the images from the continuum directory
        print('Copying images for all available beams')
        for image in range(40):
            os.system('cp ' + os.path.join(self.basedir, self.obsid) + '/' + str(image).zfill(2) + '/continuum/image_mf_*.fits ' + self.contimagedir + '/I' + str(image).zfill(2) + '.fits')
    elif self.cont_mode == 'qa':
        # Load the qa-continuum file and only copy the images with good quality
        c_arr = np.full(40, True)
        if os.path.isfile(os.path.join(self.qacontdir, self.obsid, 'dynamicRange.dat')):
            data = ascii.read(os.path.join(self.qacontdir, self.obsid, 'dynamicRange.dat'))
            c_arr[np.where(data['col2'] == 'X')] = False
            for image in range(40):
                if c_arr[image]:
                    os.system('cp ' + os.path.join(self.basedir, self.obsid) + '/' + str(image).zfill(2) + '/continuum/image_mf_*.fits ' + self.contimagedir + '/I' + str(image).zfill(2) + '.fits')
                else:
                    print('Image for beam ' + str(image).zfill(2) + ' not available or validated as bad!')
        else:
            print('No continuum quality assurance available for observation id ' + str(self.obsid) + '. Copying all available images.')
            for image in range(40):
                os.system('cp ' + os.path.join(self.basedir, self.obsid) + '/' + str(image).zfill(2) + '/continuum/image_mf_*.fits ' + self.contimagedir + '/I' + str(image).zfill(2) + '.fits')
    elif self.cont_mode == 'param':
        # Copy all images fullfilling the criteria given for the continuum mosaic
        print('Copying all images with a synthesised beam with a maximum size of bmaj=' +  str(self.cont_bmaj) + ' and bmin=' + str(self.cont_bmin) + ' and a maximum image rms of ' + str(self.cont_rmsclip))
        for image in range(40):
            os.system('cp ' + os.path.join(self.basedir, self.obsid) + '/' + str(image).zfill(2) + '/continuum/image_mf_*.fits ' + self.contimagedir + '/I' + str(image).zfill(2) + '.fits')
            if os.path.isfile(self.contimagedir + '/I' + str(image).zfill(2) + '.fits'):
                bmaj, bmin = fm.get_beam(self.contimagedir + '/I' + str(image).zfill(2) + '.fits')
                rms = fm.get_rms(self.contimagedir + '/I' + str(image).zfill(2) + '.fits')
                if (bmaj*3600.0 > self.cont_bmaj) or (bmin*3600.0 > self.cont_bmin) or (rms > self.cont_rmsclip):
                    print('Total power image of Beam ' + str(image).zfill(2) + ' exceeds the specified parameters and is not used!')
                    os.remove(self.contimagedir + '/I' + str(image).zfill(2) + '.fits')
                else:
                    pass
            else:
                print('Image for Beam ' + str(image).zfill(2) + ' is not available!')
    elif self.cont_mode == 'fixed':
        # Copy all beams, which do not exceed the given synthesised beam size
        print('Copying all images with a synthesised beam size smaller than ' + str(self.cont_mode_fixed_fwhm) + ' arcseconds!')
        for image in range(40):
            os.system('cp ' + os.path.join(self.basedir, self.obsid) + '/' + str(image).zfill(2) + '/continuum/image_mf_*.fits ' + self.contimagedir + '/I' + str(image).zfill(2) + '.fits')
            if os.path.isfile(self.contimagedir + '/I' + str(image).zfill(2) + '.fits'):
                bmaj, bmin = fm.get_beam(self.contimagedir + '/I' + str(image).zfill(2) + '.fits')
                if (bmaj*3600.0 > self.cont_mode_fixed_fwhm) or (bmin*3600.0 > self.cont_mode_fixed_fwhm):
                    print('Total power image of Beam ' + str(image).zfill(2) + ' exceeds the specified parameters and is not used!')
                    os.remove(self.contimagedir + '/I' + str(image).zfill(2) + '.fits')
                else:
                    pass
            else:
                print('Image for Beam ' + str(image).zfill(2) + ' is not available!')
    elif (type(self.cont_mode) == list):
        # Copy only the beams given as a list
        for image in self.cont_mode:
            os.system('cp ' + os.path.join(self.basedir, self.obsid) + '/' + str(image).zfill(2) + '/continuum/image_mf_*.fits ' + self.contimagedir + '/I' + str(image).zfill(2) + '.fits')
    if os.path.isfile(self.contimagedir + '/I00.fits'):
        if self.cont_use00:
            print('Using Beam 00 for mosaicking!')
        else:
            print('Not using Beam 00 for mosiacking!')
            os.remove(self.contimagedir + '/I00.fits')
    else:
        pass


def copy_contbeams(self):
    """
    Find the right beam models in time and frequency for the appropriate beams and copy them over to the working directory
    """
    if self.cont_pbtype == 'drift':
        # Get the right directory with the minimum difference in time with regard to the observation
        beamtimes = sorted(glob.glob(self.beamsrcdir + '*'))
        beamtimes_arr = [float(bt.split('/')[-1][:6]) for bt in beamtimes]
        bt_array = np.unique(beamtimes_arr)
        obstime = float(self.obsid[:6])
        deltat = np.abs(bt_array - obstime)
        loc_min = np.argmin(deltat)
        rightbeamdir = beamtimes[loc_min]

        # Get the frequencies of the beam models
        channs = sorted(glob.glob(os.path.join(rightbeamdir, 'beam_models/chann_[0-9]')))
        freqs = np.full(len(channs), np.nan)
        for b, beam in enumerate(channs):
            hdul = pyfits.open(os.path.join(beam, rightbeamdir.split('/')[-1] + '_00_I_model.fits'))
            freqs[b] = hdul[0].header['CRVAL3']
            hdul.close()

        # Copy the beam models with the right frequency over to the working directory and regrid them to the image size
        for beam in range(40):
            if os.path.isfile(self.contimagedir + '/I' + str(beam).zfill(2) + '.fits'):
                hdulist = pyfits.open(self.contimagedir + '/I' + str(beam).zfill(2) + '.fits')
                freq = hdulist[0].header['CRVAL3']
                nchann = np.argmin(np.abs(freqs - freq)) + 1
                os.system('cp ' + os.path.join(rightbeamdir, 'beam_models/chann_' + str(nchann) + '/') + rightbeamdir.split('/')[-1] + '_' + str(beam).zfill(2) + '_I_model.fits ' + self.contbeamdir + '/B' + str(beam).zfill(2) + '.fits')
    elif self.cont_pbtype == 'gaussian':
        for beam in range(40):
            if os.path.isfile(self.contimagedir + '/I' + str(beam).zfill(2) + '.fits'):
                # Get the frequency from the image
                hdu_cont = pyfits.open(self.contimagedir + '/I' + str(beam).zfill(2) + '.fits')
                freq = hdu_cont[0].header['CRVAL3']
                # Get the cellsize from the beam images and recalculate it based on the frequency of the image
                hdu_beam = pyfits.open(self.beamsrcdir + str(beam).zfill(2) + '_gp_avg_orig.fits')
                hdu_beam_hdr = hdu_beam[0].header
                hdu_beam_data = hdu_beam[0].data
                cs1 = hdu_beam_hdr['CDELT1']
                cs2 = hdu_beam_hdr['CDELT2']
                new_cs1 = cs1 * (1.36063551903e09 / freq)
                new_cs2 = cs2 * (1.36063551903e09 / freq)
                hdu_beam_hdr['CDELT1'] = new_cs1
                hdu_beam_hdr['CDELT2'] = new_cs2
                # Write the new not regridded beam to a temporary file
                pyfits.writeto(self.contbeamdir + '/B' + str(beam).zfill(2) + '.fits', data=hdu_beam_data, header=hdu_beam_hdr, overwrite=True)
    else:
        print('Mode ' + str(self.cont_pbtype) + ' is not supported. Exiting script!')
        sys.exit()


def get_contfiles(self):
    """
    Get a list of the continuum images and pbimages in the continuum working directory
    """
    images = sorted(glob.glob(self.contimagedir + '/I[0-9][0-9].fits'))
    pbimages = sorted(glob.glob(self.contbeamdir + '/B[0-9][0-9].fits'))
    return images, pbimages


def clean_contmosaic_tmp_data(self):
    os.system('rm -rf ' + self.contimagedir + '/*_reconv_tmp.fits')
    os.system('rm -rf ' + self.contimagedir + '/*_reconv_tmp_pbcorr.fits')
    os.system('rm -rf ' + self.contimagedir + '/*_mos.fits')
    os.system('rm -rf ' + self.contimagedir + '/*_reconv_tmp_uncorr.fits')
    os.system('rm -rf ' + self.contimagedir + '/*_uncorr.fits')


##########################################
#### LINEAR POLARISATION SUBFUNCTIONS ####
##########################################

def gen_poldirs(self):
    """
    Function to generate the necessary polarisation directories
    """
    if os.path.isdir(self.polworkdir):
        pass
    else:
        os.makedirs(self.polworkdir)

    if os.path.isdir(self.polimagedir):
        pass
    else:
        os.makedirs(self.polimagedir)

    if os.path.isdir(self.polbeamdir):
        pass
    else:
        os.makedirs(self.polbeamdir)

    if os.path.isdir(self.polmosaicdir):
        pass
    else:
        os.makedirs(self.polmosaicdir)


def copy_polimages(self, veri):
    """
    Function to copy the polarisation images of a specific subband to the working directory
    """
    for b in range(40):
        for sb in range(self.pol_start_sb, self.pol_end_sb + 1):
            if veri[b, sb]:
                qcube = pyfits.open(os.path.join(self.basedir, self.obsid, str(b).zfill(2), 'polarisation/Qcube.fits'))
                ucube = pyfits.open(os.path.join(self.basedir, self.obsid, str(b).zfill(2), 'polarisation/Ucube.fits'))
                qhdu = qcube[0]
                uhdu = ucube[0]
                qhdr = qhdu.header
                uhdr = uhdu.header
                qplane = qhdu.data[sb,:,:]
                uplane = uhdu.data[sb,:,:]
                newqfreq = qhdr['CRVAL3'] + float(sb) * qhdr['CDELT3']
                newufreq = uhdr['CRVAL3'] + float(sb) * uhdr['CDELT3']
                qhdr.update(NAXIS3=1, CRVAL3=newqfreq)
                uhdr.update(NAXIS3=1, CRVAL3=newufreq)
                # Get the synthesised beam parameters and put them into the header
                qbmaj = get_param(self, 'polarisation_B' + str(b).zfill(2) + '_targetbeams_qu_beamparams')[:, 0, 0][sb]
                qbmin = get_param(self, 'polarisation_B' + str(b).zfill(2) + '_targetbeams_qu_beamparams')[:, 1, 0][sb]
                qbpa = get_param(self, 'polarisation_B' + str(b).zfill(2) + '_targetbeams_qu_beamparams')[:, 2, 0][sb]
                ubmaj = get_param(self, 'polarisation_B' + str(b).zfill(2) + '_targetbeams_qu_beamparams')[:, 0, 1][sb]
                ubmin = get_param(self, 'polarisation_B' + str(b).zfill(2) + '_targetbeams_qu_beamparams')[:, 1, 1][sb]
                ubpa = get_param(self, 'polarisation_B' + str(b).zfill(2) + '_targetbeams_qu_beamparams')[:, 2, 1][sb]
                qhdr.update(BMAJ=qbmaj / 3600.0, BMIN=qbmin / 3600.0, BPA=qbpa)
                uhdr.update(BMAJ=ubmaj / 3600.0, BMIN=ubmin / 3600.0, BPA=ubpa)
                pyfits.writeto(self.polimagedir + '/Q_B' + str(b).zfill(2) + '_SB' + str(sb).zfill(2) + '.fits', data=qplane, header=qhdr, overwrite=True)
                pyfits.writeto(self.polimagedir + '/U_B' + str(b).zfill(2) + '_SB' + str(sb).zfill(2) + '.fits', data=uplane, header=uhdr, overwrite=True)
    qlist = glob.glob(self.polimagedir + '/Q_B00_SB*.fits')
    ulist = glob.glob(self.polimagedir + '/U_B00_SB*.fits')
    if len(qlist) == 0 and len(ulist) == 0:
        pass
    else:
        if self.pol_use00:
            print('Using Beam 00 for polarisation mosaicking!')
        else:
            print('Not using Beam 00 for polarisation mosaicking!')
            for qim in qlist:
                os.remove(qim)
            for uim in ulist:
                os.remove(uim)


def copy_polbeams(self):
    """
    Find the right beam models in time and frequency for the appropriate beams and copy them over to the working directory
    """
    if self.pol_pbtype == 'drift':
        # Get the right directory with the minimum difference in time with regard to the observation
        beamtimes = sorted(glob.glob(self.beamsrcdir + '*'))
        beamtimes_arr = [float(bt.split('/')[-1][:6]) for bt in beamtimes]
        bt_array = np.unique(beamtimes_arr)
        obstime = float(self.obsid[:6])
        deltat = np.abs(bt_array - obstime)
        loc_min = np.argmin(deltat)
        rightbeamdir = beamtimes[loc_min]

        # Get the frequencies of the beam models
        channs = sorted(glob.glob(os.path.join(rightbeamdir, 'beam_models/chann_[0-9]')))
        freqs = np.full(len(channs), np.nan)
        for b, beam in enumerate(channs):
            hdul = pyfits.open(os.path.join(beam, rightbeamdir.split('/')[-1] + '_00_I_model.fits'))
            freqs[b] = hdul[0].header['CRVAL3']
            hdul.close()

        # Copy the beam models with the right frequency over to the working directory
        for b in range(40):
            for sb in range(self.pol_start_sb, self.pol_end_sb + 1):
                if os.path.isfile(self.polimagedir + '/Q_B' + str(b).zfill(2) + '_SB' + str(sb).zfill(2) + '.fits'):
                    hdulist = pyfits.open(self.polimagedir + '/Q_B' + str(b).zfill(2) + '_SB' + str(sb).zfill(2) + '.fits')
                    freq = hdulist[0].header['CRVAL3']
                    nchann = np.argmin(np.abs(freqs - freq)) + 1
                    os.system('cp ' + os.path.join(rightbeamdir, 'beam_models/chann_' + str(nchann) + '/') + rightbeamdir.split('/')[-1] + '_' + str(b).zfill(2) + '_I_model.fits ' + self.polbeamdir + '/PB_B' + str(b).zfill(2) + '_SB' + str(sb).zfill(2) + '.fits')
    elif self.pol_pbtype == 'gaussian':
        for b in range(40):
            for sb in range(self.pol_start_sb, self.pol_end_sb + 1):
                if os.path.isfile(self.polimagedir + '/Q_B' + str(b).zfill(2) + '_SB' + str(sb).zfill(2) + '.fits'):
                    # Get the frequency from the image
                    hdu_pol = pyfits.open(self.polimagedir + '/Q_B' + str(b).zfill(2) + '_SB' + str(sb).zfill(2) + '.fits')
                    freq = hdu_pol[0].header['CRVAL3']
                    # Get the cellsize from the beam images and recalculate it based on the frequency of the image
                    hdu_beam = pyfits.open(self.beamsrcdir + str(b).zfill(2) + '_gp_avg_orig.fits')
                    hdu_beam_hdr = hdu_beam[0].header
                    hdu_beam_data = hdu_beam[0].data
                    cs1 = hdu_beam_hdr['CDELT1']
                    cs2 = hdu_beam_hdr['CDELT2']
                    new_cs1 = cs1 * (1.36063551903e09 / freq)
                    new_cs2 = cs2 * (1.36063551903e09 / freq)
                    hdu_beam_hdr['CDELT1'] = new_cs1
                    hdu_beam_hdr['CDELT2'] = new_cs2
                    # Write the new not regridded beam to a temporary file
                    pyfits.writeto(self.polbeamdir + '/PB_B' + str(b).zfill(2) + '_SB' + str(sb).zfill(2) + '.fits', data=hdu_beam_data, header=hdu_beam_hdr, overwrite=True)


def get_polfiles(self, sb):
    """
    Get a list of the images and pbimages in the polarisation working directory
    """
    qimages = sorted(glob.glob(self.polimagedir + '/Q_B[0-9][0-9]_SB' + str(sb).zfill(2) + '.fits'))
    uimages = sorted(glob.glob(self.polimagedir + '/U_B[0-9][0-9]_SB' + str(sb).zfill(2) + '.fits'))
    pbimages = sorted(glob.glob(self.polbeamdir + '/PB_B[0-9][0-9]_SB' + str(sb).zfill(2) + '.fits'))
    return qimages, uimages, pbimages


############################################
#### CIRCULAR POLARISATION SUBFUNCTIONS ####
############################################

def gen_circdirs(self):
    """
    Function to generate the necessary circular polarisation directories
    """
    if os.path.isdir(self.circworkdir):
        pass
    else:
        os.makedirs(self.circworkdir)

    if os.path.isdir(self.circimagedir):
        pass
    else:
        os.makedirs(self.circimagedir)

    if os.path.isdir(self.circbeamdir):
        pass
    else:
        os.makedirs(self.circbeamdir)

    if os.path.isdir(self.circmosaicdir):
        pass
    else:
        os.makedirs(self.circmosaicdir)


def copy_circimages(self):
    """
    Function to copy the circular polarisation images to the working directory
    """
    if self.circ_mode == 'all':
        # copy all the images from the Stokes V directory
        print('Copying images for all available beams')
        for image in range(40):
            os.system('cp ' + os.path.join(self.basedir, self.obsid) + '/' + str(image).zfill(2) + '/' + self.mospoldir + '/image_mf_V.fits ' + self.circimagedir + '/V' + str(image).zfill(2) + '.fits')
    elif self.circ_mode == 'qa':
        print('QA mode not supported yet!')
        # # Load the qa-polarisation file and only copy the images with good quality
        # c_arr = np.full(40, True)
        # if os.path.isfile(os.path.join(self.qacontdir, self.obsid, 'dynamicRange.dat')):
        #     data = ascii.read(os.path.join(self.qacontdir, self.obsid, 'dynamicRange.dat'))
        #     c_arr[np.where(data['col2'] == 'X')] = False
        #     for image in range(40):
        #         if c_arr[image]:
        #             os.system('cp ' + os.path.join(self.basedir, self.obsid) + '/' + str(image).zfill(2) + '/continuum/image_mf_*.fits ' + self.contimagedir + '/I' + str(image).zfill(2) + '.fits')
        #         else:
        #             print('Image for beam ' + str(image).zfill(2) + ' not available or validated as bad!')
        # else:
        #     print('No continuum quality assurance available for observation id ' + str(self.obsid) + '. Copying all available images.')
        #     for image in range(40):
        #         os.system('cp ' + os.path.join(self.basedir, self.obsid) + '/' + str(image).zfill(2) + '/continuum/image_mf_*.fits ' + self.contimagedir + '/I' + str(image).zfill(2) + '.fits')
    elif self.circ_mode == 'param':
        # Copy all images fullfilling the criteria given for the continuum mosaic
        print('Copying all Stokes V images with a synthesised beam with a maximum size of bmaj=' +  str(self.circ_bmaj) + ' and bmin=' + str(self.circ_bmin) + ' and a maximum image rms of ' + str(self.circ_rmsclip))
        for image in range(40):
            os.system('cp ' + os.path.join(self.basedir, self.obsid) + '/' + str(image).zfill(2) + '/' + self.mospoldir + '/image_mf_V.fits ' + self.circimagedir + '/V' + str(image).zfill(2) + '.fits')
            if os.path.isfile(self.circimagedir + '/V' + str(image).zfill(2) + '.fits'):
                bmaj, bmin = fm.get_beam(self.circimagedir + '/V' + str(image).zfill(2) + '.fits')
                rms = fm.get_rms(self.circimagedir + '/V' + str(image).zfill(2) + '.fits')
                if (bmaj*3600.0 > self.circ_bmaj) or (bmin*3600.0 > self.circ_bmin) or (rms > self.circ_rmsclip):
                    print('Stokes V image of Beam ' + str(image).zfill(2) + ' exceeds the specified parameters and is not used!')
                    os.remove(self.circimagedir + '/V' + str(image).zfill(2) + '.fits')
                else:
                    pass
            else:
                print('Stokes V image for Beam ' + str(image).zfill(2) + ' is not available!')
    elif self.cont_mode == 'fixed':
        # Copy all beams, which do not exceed the given synthesised beam size
        print('Copying all Stokes V images with a synthesised beam size smaller than ' + str(self.circ_mode_fixed_fwhm) + ' arcseconds!')
        for image in range(40):
            os.system('cp ' + os.path.join(self.basedir, self.obsid) + '/' + str(image).zfill(2) + '/' + self.mospoldir + '/image_mf_V.fits ' + self.circimagedir + '/V' + str(image).zfill(2) + '.fits')
            if os.path.isfile(self.circimagedir + '/V' + str(image).zfill(2) + '.fits'):
                bmaj, bmin = fm.get_beam(self.circimagedir + '/V' + str(image).zfill(2) + '.fits')
                if (bmaj*3600.0 > self.circ_mode_fixed_fwhm) or (bmin*3600.0 > self.circ_mode_fixed_fwhm):
                    print('Stokes V image of Beam ' + str(image).zfill(2) + ' exceeds the specified parameters and is not used!')
                    os.remove(self.circimagedir + '/V' + str(image).zfill(2) + '.fits')
                else:
                    pass
            else:
                print('Stokes V image for Beam ' + str(image).zfill(2) + ' is not available!')
    elif (type(self.circ_mode) == list):
        # Copy only the beams given as a list
        for image in self.circ_mode:
            os.system('cp ' + os.path.join(self.basedir, self.obsid) + '/' + str(image).zfill(2) + '/' + self.mospoldir + '/image_mf_V.fits ' + self.circimagedir + '/V' + str(image).zfill(2) + '.fits')
    if os.path.isfile(self.circimagedir + '/V00.fits'):
        if self.circ_use00:
            print('Using Beam 00 for Stokes V mosaicking!')
        else:
            print('Not using Beam 00 for Stokes V mosaicking!')
            os.remove(self.circimagedir + '/V00.fits')
    else:
        pass


def copy_circbeams(self):
    """
    Find the right beam models in time and frequency for the appropriate beams and copy them over to the working directory
    """
    if self.circ_pbtype == 'drift':
        # Get the right directory with the minimum difference in time with regard to the observation
        beamtimes = sorted(glob.glob(self.beamsrcdir + '*'))
        beamtimes_arr = [float(bt.split('/')[-1][:6]) for bt in beamtimes]
        bt_array = np.unique(beamtimes_arr)
        obstime = float(self.obsid[:6])
        deltat = np.abs(bt_array - obstime)
        loc_min = np.argmin(deltat)
        rightbeamdir = beamtimes[loc_min]

        # Get the frequencies of the beam models
        channs = sorted(glob.glob(os.path.join(rightbeamdir, 'beam_models/chann_[0-9]')))
        freqs = np.full(len(channs), np.nan)
        for b, beam in enumerate(channs):
            hdul = pyfits.open(os.path.join(beam, rightbeamdir.split('/')[-1] + '_00_I_model.fits'))
            freqs[b] = hdul[0].header['CRVAL3']
            hdul.close()

        # Copy the beam models with the right frequency over to the working directory and regrid them to the image size
        for beam in range(40):
            if os.path.isfile(self.contimagedir + '/I' + str(beam).zfill(2) + '.fits'):
                hdulist = pyfits.open(self.contimagedir + '/I' + str(beam).zfill(2) + '.fits')
                freq = hdulist[0].header['CRVAL3']
                nchann = np.argmin(np.abs(freqs - freq)) + 1
                os.system('cp ' + os.path.join(rightbeamdir, 'beam_models/chann_' + str(nchann) + '/') + rightbeamdir.split('/')[-1] + '_' + str(beam).zfill(2) + '_I_model.fits ' + self.circbeamdir + '/B' + str(beam).zfill(2) + '.fits')
    elif self.circ_pbtype == 'gaussian':
        for beam in range(40):
            if os.path.isfile(self.circimagedir + '/V' + str(beam).zfill(2) + '.fits'):
                # Get the frequency from the image
                hdu_cont = pyfits.open(self.circimagedir + '/V' + str(beam).zfill(2) + '.fits')
                freq = hdu_cont[0].header['CRVAL3']
                # Get the cellsize from the beam images and recalculate it based on the frequency of the image
                hdu_beam = pyfits.open(self.beamsrcdir + str(beam).zfill(2) + '_gp_avg_orig.fits')
                hdu_beam_hdr = hdu_beam[0].header
                hdu_beam_data = hdu_beam[0].data
                cs1 = hdu_beam_hdr['CDELT1']
                cs2 = hdu_beam_hdr['CDELT2']
                new_cs1 = cs1 * (1.36063551903e09 / freq)
                new_cs2 = cs2 * (1.36063551903e09 / freq)
                hdu_beam_hdr['CDELT1'] = new_cs1
                hdu_beam_hdr['CDELT2'] = new_cs2
                # Write the new not regridded beam to a temporary file
                pyfits.writeto(self.circbeamdir + '/B' + str(beam).zfill(2) + '.fits', data=hdu_beam_data, header=hdu_beam_hdr, overwrite=True)
    else:
        print('Mode ' + str(self.cont_pbtype) + ' is not supported. Exiting script!')
        sys.exit()


def get_circfiles(self):
    """
    Get a list of the Stokes V images and pbimages in the continuum working directory
    """
    images = sorted(glob.glob(self.circimagedir + '/V[0-9][0-9].fits'))
    pbimages = sorted(glob.glob(self.circbeamdir + '/B[0-9][0-9].fits'))
    return images, pbimages


def clean_circmosaic_tmp_data(self):
    os.system('rm -rf ' + self.circimagedir + '/*_reconv_tmp.fits')
    os.system('rm -rf ' + self.circimagedir + '/*_reconv_tmp_pbcorr.fits')
    os.system('rm -rf ' + self.circimagedir + '/*_mos.fits')


##############################
#### ADDITIONAL FUNCTIONS ####
##############################


def get_common_psf(self, veri, format='fits'):
    """
    Common psf for the list of fits files
    """
    beams = []

    if format == 'fits':
        bmajes = []
        bmines = []
        bpas = []
        for f in veri:
            ih = pyfits.getheader(f)
            bmajes.append(ih['BMAJ'])
            bmines.append(ih['BMIN'])
            bpas.append(ih['BPA'])
        bmajarr = np.array(bmajes)
        bminarr = np.array(bmines)
        bpaarr = np.array(bpas)
        for i in range(0, len(bmajes) - 1):
            ni = i + 1
            beams = Beams((bmajarr[[i, ni]]) * u.deg, (bminarr[[i, ni]]) * u.deg, bpaarr[[i, ni]] * u.deg)
            common = commonbeam.commonbeam(beams)
            bmajarr[ni] = common.major/u.deg
            bminarr[ni] = common.minor / u.deg
            bpaarr[ni] = common.pa / u.deg
            common = Beam.__new__(Beam, major=common.major * 1.01, minor=common.minor * 1.01, pa=common.pa)
            print('Increased final smallest common beam by 1 %')
            print('The final smallest common beam is ' + str(common))
    elif format == 'array':
        bmajes = np.empty(0)
        bmines = np.empty(0)
        bpas = np.empty(0)
        for b in range(40):
            for sb in range(self.pol_start_sb, self.pol_end_sb + 1):
                if veri[b,sb]:
                    bmajes = np.append(bmajes, (get_param(self, 'polarisation_B' + str(b).zfill(2) + '_targetbeams_qu_beamparams')[:, 0, 0][sb]))
                    bmines = np.append(bmines, (get_param(self, 'polarisation_B' + str(b).zfill(2) + '_targetbeams_qu_beamparams')[:, 1, 0][sb]))
                    bpas = np.append(bpas, (get_param(self, 'polarisation_B' + str(b).zfill(2) + '_targetbeams_qu_beamparams')[:, 2, 0][sb]))
        bmajarr = bmajes[~pd.isnull(bmajes)]
        bminarr = bmines[~pd.isnull(bmines)]
        bpaarr = bpas[~pd.isnull(bpas)]
        for i in range(0, len(bmajarr) - 1):
            ni = i + 1
            beams = Beams((bmajarr[[i,ni]]/3600.0) * u.deg, (bminarr[[i,ni]]/3600.0) * u.deg, bpaarr[[i,ni]] * u.deg)
            common = commonbeam.commonbeam(beams)
            bmajarr[ni] = (common.major / u.deg) * 3600.0
            bminarr[ni] = (common.minor / u.deg) * 3600.0
            bpaarr[ni] = common.pa / u.deg
            common = Beam.__new__(Beam, major=common.major * 1.01, minor=common.minor * 1.01, pa=common.pa)
            print('Increased final smallest common beam by 1 %')
            print('The final smallest common beam is ' + str(common))
    elif format == 'cont-fixed':
        common = Beam((self.cont_mode_fixed_fwhm/3600.0)*u.deg, (self.cont_mode_fixed_fwhm/3600.0)*u.deg, 0.0*u.deg)
    elif format == 'pol-fixed':
        common = Beam((self.pol_mode_fixed_fwhm/3600.0)*u.deg, (self.pol_mode_fixed_fwhm/3600.0)*u.deg, 0.0*u.deg)
    return common


def collect_paramfiles(self):
    """
    Check if single param.npy files are available and combine them into one if yes
    """
    paramfiles = sorted(glob.glob(os.path.join(self.basedir, self.obsid, 'param_[0-9][0-9].npy')))
    if len(paramfiles)==0:
        if os.path.isfile(os.path.join(self.basedir, self.obsid, 'param.npy')):
            print('Main parameter file found and used')
        else:
            print('Main parameter file not found! Further operations not possible!')
            sys.exit()
    else:
        pfirst = np.load(paramfiles[0], allow_pickle=True, encoding='latin1').item()
        for p, pnext in enumerate(paramfiles):
            if pfirst == pnext:
                continue
            else:
                pnext = np.load(paramfiles[p], allow_pickle=True, encoding='latin1').item()
                pfirst.update(pnext)
        np.save(os.path.join(self.basedir, self.obsid, 'param.npy'), pfirst)


def get_param(self, pmname):
    """
    Load a keyword of the parameter file into a variable
    """
    d = np.load(os.path.join(self.basedir, self.obsid, 'param.npy'), allow_pickle=True, encoding='latin1').item()
    values = d[pmname]
    return values


def clean_polmosaic_tmp_data(self):
    os.system('rm -rf ' + self.polimagedir + '/*_reconv_tmp.fits')
    os.system('rm -rf ' + self.polimagedir + '/*_reconv_tmp_pbcorr.fits')
    os.system('rm -rf ' + self.polimagedir + '/*_mos.fits')
    os.system('rm -rf ' + self.polimagedir + '/*_reconv_tmp_uncorr.fits')
    os.system('rm -rf ' + self.polimagedir + '/*_uncorr.fits')


def make_tmp_copy(fname):
    base, ext = os.path.splitext(fname)
    tempname = fname.replace(ext, '_tmp{}'.format(ext))
    subprocess.call('cp {} {}'.format(fname, tempname), shell=True)
    return tempname