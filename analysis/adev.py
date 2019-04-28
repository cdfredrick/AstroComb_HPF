# %% Imports

import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import UnivariateSpline as interpolate

from scipy.signal import fftconvolve
from astropy.stats import LombScargle


# %% Allan Deviation
def a_dev_fft(t, freq, sampling='octave', error=False):
    max_n = int(freq.size/2)
    dt = np.mean(np.diff(t))
    if sampling == 'octave':
        samples = np.append(np.power(2,np.arange(1+int(np.log2(max_n)))), max_n)
        taus = dt*samples
    elif isinstance(sampling, int) or isinstance(sampling, float):
        samples = np.unique(np.power(max_n,np.linspace(0, 1, int(sampling))).astype(np.int))
        taus = dt*samples
    # Calculate Adev
    adev_generator = (
            1./((freq.size - 2*n + 1))
            * np.sum(1./2. * fftconvolve(freq,
                                         1./n * np.append(-np.ones(n), np.ones(n)),
                                         mode='valid')**2.)
            for n in samples)
    adev = np.sqrt(np.fromiter(adev_generator, np.float, samples.size))
    if error:
    # The Total Deviation Approach to Long-Term Characterization of Frequency Stability, David A. Howe
        edf = t.size/samples - 1
        adev_err = adev / np.sqrt(2.*edf)
        log10_adev_err = 1./(adev*np.log(10.))*adev_err
        return np.array([taus, adev, adev_err, log10_adev_err])
    else:
        return np.array([taus, adev])


# %% Total Deviation
def tot_dev_fft(t, freq, sampling='octave', error=False):
    max_n = int(freq.size/2)
    freq = np.concatenate((freq[1:][::-1],freq,freq[:-2][::-1]))
    dt = np.mean(np.diff(t))
    if sampling == 'octave':
        samples = np.append(np.power(2,np.arange(1+int(np.log2(max_n)))), max_n)
        taus = dt*samples
    elif isinstance(sampling, int) or isinstance(sampling, float):
        samples = np.unique(np.power(max_n,np.linspace(0, 1, int(sampling))).astype(np.int))
        taus = dt*samples
    # Calculate Adev
    adev_generator = (
            1./((freq.size - 2*n + 1))
            * np.sum(1./2. * fftconvolve(freq,
                                         1./n * np.append(-np.ones(n), np.ones(n)),
                                         mode='valid')**2.)
            for n in samples)
    adev = np.sqrt(np.fromiter(adev_generator, np.float, samples.size))
    if error:
    # The Total Deviation Approach to Long-Term Characterization of Frequency Stability, David A. Howe
        slope = np.diff(np.log10(adev))/np.diff(np.log10(taus))
        slope = np.append(slope, slope[-1])
        #a = np.interp(slope, [-.5, 0, .5], [0, 0.481, 0.750])
        b = np.interp(slope, [-.5, 0, .5], [1.500, 1.168, 0.927])
        c = np.interp(slope, [-.5, 0, .5], [0, 0.222, 0.358])
        T = dt*t.size
        edf = b*T/taus - c
        #nbias = -a*taus/T #not sure what to do with the bias
        adev_err = adev*1./np.sqrt(2*edf)
        log10_adev_err = 1./(adev*np.log(10.))*adev_err
        return np.array([taus, adev, adev_err, log10_adev_err])
    else:
        return np.array([taus, adev])


# %% Uneven Spaced Allan Deviation (Lomb Scargle Frequency Estimator)
def a_dev_ls(t, f, gate=None, sampling='octave', error=False, samples_per_peak=5, psd=False):
    if (gate==None):
        gate = np.median(np.diff(t))
    max_freq = 1./(2.*gate)
    max_n = int((t.max()-t.min())/(2*gate))
    if sampling == 'octave':
        samples = np.append(np.power(2,np.arange(1+int(np.log2(max_n)))), max_n)
        taus = gate*samples
    elif isinstance(sampling, int) or isinstance(sampling, float):
        samples = np.unique(np.power(max_n,np.linspace(0, 1, int(sampling))).astype(np.int))
        taus = gate*samples
        
    # Considerations on the Measurement of the Stability of Oscillators with Frequency Counters, Samuel T. Dawkins
    # Calculate Periodigram
    freq, power = LombScargle(t, f).autopower(maximum_frequency=max_freq, samples_per_peak=samples_per_peak)
    power = power*np.var(f)/np.sum(power)
    # Calculate Adev (completely in frequency domain)
    adev_generator = ((power * 2 * (np.pi * freq * tau)**2 * np.sinc(freq * tau)**4).sum() for tau in taus )
    adev = np.sqrt(np.fromiter(adev_generator, np.float, taus.size))
    if psd:
        return np.array([taus, adev, freq, power])
    else:
        return np.array([taus, adev])


# %% Running Median Deglitch
def deglitch(dataX, dataY, sig=10, bins=100, plot=False, const=False, detrend=False):
    # Needs -----------------------------------------------------------------
    # numpy as np,
    # matplotlib.pyplot as plt
    # scipy.interpolate.InterpolatedUnivariateSpline as interpolate
    
    # Format Data -------------------------------------------------------------
    dataX = np.array(dataX)
    dataY = np.array(dataY)
    sort_ind = np.argsort(dataX)
    dataX = dataX[sort_ind]
    dataY = dataY[sort_ind]
    size = dataY.size
    
    # Detrend -----------------------------------------------------------------
    window = int(size/bins) # points
    roll_med = np.empty((2, bins), np.float64)
    roll_med_dev = np.empty((2, bins), np.float64)
    samp_inds = np.linspace(0, size - window, num=bins).astype(np.int)
    for ind in range(samp_inds.size):
        samp_ind = samp_inds[ind]
        temp_X = dataX[(samp_ind):(samp_ind+window)]
        temp_Y = dataY[(samp_ind):(samp_ind+window)]
        roll_med[:, ind] = np.array([np.mean(temp_X), np.median(temp_Y)])
        roll_med_dev[:, ind] = np.array([np.mean(temp_X), np.sqrt(np.median(np.square(temp_Y - np.median(temp_Y))))])
    trend_Y = interpolate(roll_med[0], roll_med[1], w=1./roll_med_dev[1], k=3)
    detrend_Y = dataY - trend_Y(dataX)
    
    # Deglitch ----------------------------------------------------------------
    med_dev = np.sqrt(np.median(np.square(detrend_Y - np.median(detrend_Y))))
    if const:
        sig_mask = (np.abs(dataY - np.median(dataY)) < sig*med_dev)
    else:
        sig_mask = (np.abs(detrend_Y) < sig*med_dev)
        
    # Plot Results ------------------------------------------------------------
    if plot:
        dataX_0 = dataX[0]
        plt.figure(num=0)
        plt.clf()
        plt.plot(dataX-dataX_0, dataY)
        plt.plot(dataX[sig_mask]-dataX_0, dataY[sig_mask])
        plt.plot(dataX-dataX_0, trend_Y(dataX))
        #print('Threshold is +-{:}'.format(sig*med_dev))
        if const:
            plt.plot(dataX-dataX_0, np.ones(dataX.size) * np.median(dataY)+sig*med_dev)
            plt.plot(dataX-dataX_0, np.ones(dataX.size) * np.median(dataY)-sig*med_dev)
            x1, x2, y1, y2 = plt.axis()
            plt.axis([x1, x2, np.median(dataY)-2*sig*med_dev, np.median(dataY)+2*sig*med_dev])
        else:
            plt.plot(dataX-dataX_0, trend_Y(dataX)+sig*med_dev)
            plt.plot(dataX-dataX_0, trend_Y(dataX)-sig*med_dev)
            x1, x2, y1, y2 = plt.axis()
            plt.axis([x1, x2, np.min(trend_Y(dataX))-2.*sig*med_dev, np.max(trend_Y(dataX))+2.*sig*med_dev])
    if detrend:
        return [np.array([dataX[sig_mask], dataY[sig_mask]]), [trend_Y(dataX), sig_mask]]
    else:
        return np.array([dataX[sig_mask], dataY[sig_mask]])