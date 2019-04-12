# -*- coding: utf-8 -*-
"""
Created on Mon Apr  1 11:11:34 2019

@author: cdf1
"""

# %%
import sys
import time
import numpy as np
import matplotlib.pyplot as plt
import skopt
import skopt.plots

from modules.optimizer import Minimizer

# %%
a = 1
b = 1
c = b**2/(4*a)
x0 = -b/(2*a)
print(x0)

def measure(x, x_noise=True, y_noise=True, x_std=.1, y_std=.5):
    try:
        n = len(x)
        x = np.array(x)
    except TypeError:
        n = 1
        x = np.array([x])
    if x_noise:
        if n == 1:
            x = x + np.random.randn()*x_std
        else:
            x = x + np.random.rand(n)*x_std
    y = a*x**2 + b*x + c
    if y_noise:
        if n == 1:
            y += np.random.randn()*y_std
        else:
            y += np.random.randn(n)*y_std
    if n ==1:
        return y[0]
    else:
        return y

# %% Test
dims = (-2, 2.)
n_init = 5

opt = Minimizer([dims], n_initial_points=n_init, sig=10)
new_x = opt.ask()

best_x = []
best_y = []
std_y = []
std_resid = []

idx = 0

conv_count = 0

search = True
while search:
    # Ask for new point
    new_x = opt.ask()

    # Measure new point
    new_y = measure(*new_x)
    opt_x, diag = opt.tell(new_x, new_y, diagnostics=True)

    # Record FOMs
    best_x.append(opt_x)
    best_y.append(diag["optimum y"])
    std_y.append(diag["optimum y std"])
    std_resid.append(diag["residuals std"])

    if opt.convergence_count >= 3:
        search = False

# %

plt.figure(1)
plt.clf()

x_samp = np.linspace(opt.dims[0][0], opt.dims[0][1], 1000)

y_pred, y_std = opt.predict(x_samp[:, np.newaxis].tolist(), return_std=True)
plt.plot(x_samp, y_pred)
plt.fill_between(x_samp, (y_pred+y_std), (y_pred-y_std), alpha=.1)

plt.plot(x_samp, np.fromiter((measure(x, noise=False) for x in x_samp), np.float, x_samp.size))

plt.plot(opt.x, opt.y, '.')

exp_min = opt.optimum_x()
print(exp_min[0], measure(exp_min[0], x_noise=False, y_noise=False))
#plt.plot()

# %
plt.figure(2)
plt.clf()
plt.plot(np.array(std_y), label='STD: y mdl')
plt.plot(std_resid, label='STD: y rsd')
plt.plot(np.fromiter((measure(x[0], x_noise=False, y_noise=False) for x in best_x), np.float, len(best_x)), label='y error')
plt.grid()
plt.legend()
test = np.concatenate([std_y, std_resid, [0]])
ylim = plt.ylim((np.nanmin(test), np.nanmax(test)))

# %% Stats 1D
dims = (-5, 5.)
n_init = 5

y_error = []
n_samps = []
for idx in range(100):
    print(idx)
    search = True
    opt = Minimizer([dims], n_initial_points=n_init, sig=3)
    while search:
        # Ask for new point
        new_x = opt.ask()

        # Measure new point
        new_y = measure(*new_x)
        opt_x, diag = opt.tell(new_x, new_y, diagnostics=True)

        if opt.convergence_count >= 3:
            search = False
    n_samps.append(len(opt.y))
    y_error.append(measure(opt_x[0], x_noise=False, y_noise=False))


print(np.mean(y_error), np.std(y_error), np.max(y_error), np.min(y_error), np.median(y_error))
print(np.mean(n_samps), np.std(n_samps), np.max(n_samps), np.min(n_samps), np.median(n_samps))


# %% Stats ND
from modules.optimizer import Minimizer

n_init = 10
n_dims = 7
sig = 3
sample_size = 10

y_error = []
n_samps = []
run_time = []
for idx in range(sample_size):
    print(idx)
    search = True
    dims = [(1, 5.)]*n_dims
    opt = Minimizer(dims, n_initial_points=n_init, sig=sig)
    start_time = time.time()
    while search:
        # Ask for new point
        if opt.n_obs==0:
            new_x = [2]*n_dims
        else:
            new_x = opt.ask()

        # Measure new point
        new_y = np.sum(measure(new_x,  x_noise=True, y_noise=False)) + measure(x0,  x_noise=False, y_noise=True)
        opt_x, diag = opt.tell(new_x, new_y, diagnostics=True)
        print('\r', '\t\t\t\t\t\t\t\t', end='\r')
        print('\r', opt.n_obs, "{:.3g}".format(diag["residuals std"]/diag["optimum y std"]), "{:.3g}s".format(time.time()-start_time), end='\r')

        if opt.convergence_count >= 3:
            search = False
    print()
    stop_time = time.time()
    run_time.append(stop_time - start_time)
    n_samps.append(len(opt.y))
    y_error.append(measure(opt_x, x_noise=False, y_noise=False))

# %
print("Individual Dims. Error")
if n_dims > 1:
    y_err = np.array(y_error).T
else:
    y_err = np.array([y_error])

for y in y_err:
    print("\t Average: {:.4g} +- {:.2g}".format(np.mean(y), np.std(y)))
print("All Dims. Error")
print("\t Average: {:.4g} +- {:.2g}".format(np.mean(y_err), np.std(y_err)))
print("Samples")
print("\t Average: {:.4g} +- {:.2g}".format(np.mean(n_samps), np.std(n_samps)))
print("\t Per Dim: {:.4g} +- {:.2g}".format(np.mean(n_samps)/n_dims, np.std(n_samps)/n_dims))
print("Time")
print("\t Average: {:.4g} +- {:.2g}".format(np.mean(run_time), np.std(run_time)))
print("\t Per Dim: {:.4g} +- {:.2g}".format(np.mean(run_time)/n_dims, np.std(run_time)/n_dims))