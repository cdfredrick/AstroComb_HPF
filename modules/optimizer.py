# -*- coding: utf-8 -*-
"""
Created on Mon Apr  1 11:11:34 2019

@author: cdf1
"""

# %% Modules

import numpy as np
from scipy.optimize import minimize
import skopt


# %% Minimizer Class

class Minimizer():
    def __init__(self, dimensions, n_initial_points=5, abs_bounds=None, sig=1.):
        # Arguments
        assert isinstance(dimensions , list)
        self.dims = dimensions
        self.n_dims = len(self.dims)
        assert isinstance(n_initial_points, int)
        self.n_init = n_initial_points
        if abs_bounds is None:
            self.abs_bounds = [(np.nan, np.nan) for bound in dimensions]
        else:
            assert len(dimensions) == len(abs_bounds)
            self.abs_bounds = abs_bounds
        self.sig = sig

        # Internal Variables
        self.x = []
        self.x_range = [x_max-x_min for (x_min, x_max) in self.dims]
        self.y = []
        self.y_avg = np.nan
        self.y_scl = np.nan
        self.n_obs = len(self.x)
        self.optimizer = skopt.Optimizer(self.dims,
                                         n_initial_points=self.n_init)
        self.convergence_count = 0

    @classmethod
    def new_model(cls, new_x, new_y, dimensions, n_initial_points=5, abs_bounds=None, sig=1.):
        '''Initialize the `Minimizer` class with an existing data set.'''
        assert isinstance(new_x, list)
        assert isinstance(new_y, list)
        # Multiple points entered
        assert all([isinstance(x, list) for x in new_x])
        # Determine Boundaries
        assert all([len(x)==len(dimensions) for x in new_x])
        # Create new Minimizer class
        optimizer = cls(dimensions, n_initial_points=n_initial_points,
                        abs_bounds=abs_bounds, sig=sig)
        # Add data
        optimizer.tell(new_x, new_y)
        return optimizer

    def check_bounds(self, x, fract=0):
        '''Check if the test point is within the defined boundaries'''
        assert isinstance(x, list)
        assert len(x)==len(self.dims)
        upper_edge = []
        lower_edge = []
        for idx in range(self.n_dims):
            x_min, x_max = self.dims[idx]
            x_range = self.x_range[idx]
            upper_edge.append(x[idx] > x_max - x_range*fract)
            lower_edge.append(x[idx] < x_min + x_range*fract)
        return lower_edge, upper_edge

    def ask(self):
        '''Calculate a new test point
        '''
        new_x = self.optimizer.ask()
        return new_x

    def tell(self, new_x, new_y, diagnostics=False):
        '''Enter a new observations into the model.

        This method updates the current model with the input data
        and gives a measure of the model's convergence. This method extends the
        model space (up to the absolute boundaries) if the new optimum point is
        too close to the current boundary.
        '''
        assert isinstance(new_x, list)
        if isinstance(new_y, list):
            # Multiple points entered
            assert all([isinstance(x, list) for x in new_x])
            assert all([len(x)==len(self.dims) for x in new_x])
            self.x.extend(new_x)
            self.y.extend(new_y)
        else:
            # Single point entered
            assert len(new_x)==len(self.dims)
            self.x.append(new_x)
            self.y.append(new_y)
        self.n_obs = len(self.x)



        # Expand the model
        if self.n_obs < self.n_init:
            # Update the current model
            self.model = self.optimizer.tell(new_x, new_y)

            # Calculate optimum
            opt_x = self.optimum_x()

        elif ((self.y_avg is np.nan) or (self.y_scl is np.nan)) and (self.n_obs >= self.n_init):
            # Scale the input data
            self.y_avg = np.average(self.y)
            self.y_scl = np.std(self.y)
            x_mdl = self.x
            y_mdl = ((np.array(self.y) - self.y_avg)/self.y_scl).tolist()

            # Create a new model
            self.optimizer = skopt.Optimizer(self.dims,
                                             n_initial_points=self.n_init)
            self.model = self.optimizer.tell(x_mdl, y_mdl)

            # Calculate optimum
            opt_x = self.optimum_x()

        else:
            # Scale the input data
            x_mdl = new_x
            y_mdl = ((np.array(new_y) - self.y_avg)/self.y_scl).tolist()

            # Update the current model
            self.model = self.optimizer.tell(x_mdl, y_mdl)

            # Calculate optimum
            opt_x = self.optimum_x()

            # Update boundaries
            update_model = False
            lower_edge, upper_edge = self.check_bounds(opt_x, fract=.1)
            for idx in range(self.n_dims):
                x_min, x_max = self.dims[idx]
                abs_x_min, abs_x_max = self.abs_bounds[idx]
                x_range = self.x_range[idx]
                if upper_edge[idx] or lower_edge[idx]:
                    if upper_edge[idx]:
                        new_x_max = x_max + x_range/4
                        if new_x_max > abs_x_max:
                            new_x_max = abs_x_max
                        new_dim = (x_min, new_x_max)
                    else:
                        new_x_min = x_min - x_range/4
                        if new_x_min < abs_x_min:
                            new_x_min = abs_x_min
                        new_dim = (new_x_min, x_max)
                    change_detected = (self.dims[idx] != new_dim)
                    self.dims[idx] = new_dim
                    self.x_range[idx] = new_dim[1] - new_dim[0]
                    update_model = (update_model or change_detected)
            if update_model:
                # Scale the input data
                self.y_avg = np.average(self.y)
                self.y_scl = np.std(self.y)
                x_mdl = self.x
                y_mdl = ((np.array(self.y) - self.y_avg)/self.y_scl).tolist()
                self.optimizer = skopt.Optimizer(self.dims,
                                                 n_initial_points=self.n_init)
                self.model = self.optimizer.tell(x_mdl,
                                                 y_mdl)
                # Reset convergenc count
                self.convergence_count = 0
                # Calculate optimum
                opt_x = self.optimum_x()

        # Calculate fitness diagnostics
        fit = self.fitness(test_x=opt_x)
        opt_y_std = fit["optimum y std"]
        resid_std = fit["residuals std"]

        # Check convergence of the model
        if (self.n_obs >= self.n_init) and (opt_y_std*self.sig < resid_std):
            self.convergence_count += 1
        else:
            self.convergence_count = 0

        if diagnostics:
            return opt_x, fit
        else:
            return opt_x

    def optimum_x(self):
        '''Calculate the optimal x value from the current model.'''
        opt_x = self.x[np.argmin(self.y)]
        if self.n_obs < self.n_init:
            return opt_x
        else:
            opt_y = np.inf
            for x in self.x:
                # Test all sample points
                result = minimize(self.predict, x, bounds=self.dims)
                if result.fun < opt_y:
                    opt_y = result.fun
                    opt_x = result.x.tolist()
            return opt_x

    def predict(self, x, return_std=False):
        '''Use the current model to predict the value at a specified point.'''
        if isinstance(x, np.ndarray):
            x = x.tolist()
        assert isinstance(x, list)
        if len(np.array(x).shape) > 1:
            assert all([isinstance(x_i, list) for x_i in x])
            assert all([len(x_i)==len(self.dims) for x_i in x])
        else:
            assert len(x)==len(self.dims)
            x = [x]

        if len(self.model.models):
            # Ensure that all sample points are within range
            for samp_idx in range(len(x)):
                lower_edge, upper_edge = self.check_bounds(x[samp_idx])
                for idx in range(self.n_dims):
                    x_min, x_max = self.dims[idx]
                    if upper_edge[idx] or lower_edge[idx]:
                        if upper_edge[idx]:
                            x[samp_idx][idx] = x_max
                        else:
                            x[samp_idx][idx] = x_min

            x_samp_model = self.model.space.transform(x)

            if return_std:
                y_pred, y_pred_std = self.model.models[-1].predict(
                    x_samp_model,
                    return_std=True)
            else:
                y_pred = self.model.models[-1].predict(
                    x_samp_model,
                    return_std=False)

            y_pred = y_pred*self.y_scl + self.y_avg
            if len(x)==1:
                y_pred = y_pred[0]

            if return_std:
                y_pred_std *= self.y_scl
                if len(x)==1:
                    y_pred_std = y_pred_std[0]
                return y_pred, y_pred_std
            else:
                return y_pred
        else:
            if len(x)==1:
                y_pred = np.nan
                y_pred_std = np.nan
            else:
                y_pred = np.array([np.nan]*len(x))
                y_pred_std = np.array([np.nan]*len(x))
            if return_std:
                return y_pred, y_pred_std
            else:
                return y_pred

    def fitness(self, test_x=None):
        '''Calculate measures of the model's fitness.'''
        if self.n_obs < self.n_init:
            # No model has been fit yet
            fitness = {"optimum y": np.min(self.y),
                       "optimum y std": np.nan,
                       "residuals": np.array([np.nan]*self.n_obs).tolist(),
                       "residuals std": np.nan,
                       "predicted std": np.array([np.nan]*self.n_obs).tolist(),
                       "significance":np.nan,
                       "domains":self.dims,
                       "abs domains":self.abs_bounds}
        else:
            if test_x is not None:
                assert isinstance(test_x, list)
                assert len(test_x)==len(self.dims)
                opt_x = test_x
            else:
                # Calculate the optimum
                opt_x = self.optimum_x()

            # Calculate the optimum's error
            opt_y, opt_y_std = self.predict(opt_x, return_std=True)

            # Calculate residuals
            y_pred, y_pred_std = self.predict(self.x, return_std=True) # np.array
            residuals = (y_pred - self.y)
            resid_std = np.std(residuals)

            fitness = {
                "optimum y": opt_y,
                "optimum y std": opt_y_std,
                "residuals": residuals.tolist(),
                "residuals std": resid_std,
                "predicted std": y_pred_std.tolist(),
                "significance":resid_std/opt_y_std,
                "domains":self.dims,
                "abs domains":self.abs_bounds}
        return fitness

