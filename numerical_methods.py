# Author: Landon Schultz
# Date: 5-4-26

import math

from route_solver import linear_interp, scooter_speed_from_distance


### Numerical methods helper functions for the campus route project
#This file is mostly here to show the numerical methods pieces from the proposal.
#The bisection function is based on the same bisection style I used in HW3_Prob3.py
#and the error analysis idea follows the error checking style from Lab4/error_analysis.py.


#Function for comparing interpolated scooter speed to a direct test equation
#This gives a percent error just like the homework/lab error analysis problems
def interpolation_error_analysis():

    #test points in meters
    test_distances = [20, 60, 120, 250, 350]

    #direct equation used only for checking the interpolation
    #it smoothly approaches about 12 mph as distance gets longer
    def direct_speed(distance_m):
        return 5 + 7 * (1 - math.exp(-distance_m / 120))

    errors = []

    #loop through the test distances and calculate error, cause we love loops
    for distance_m in test_distances:
        interp_speed = scooter_speed_from_distance(distance_m)
        true_speed = direct_speed(distance_m)
        error_percent = abs(interp_speed - true_speed) / true_speed * 100
        errors.append([distance_m, interp_speed, true_speed, error_percent])

    return errors


#Bisection root finding for when scooter and walking times are equal
#This is adapted from my HW3_Prob3 bisection function, but changed to only return
#the root and number of iterations instead of storing all history for a plot.
def bisection_root(func, xl, xu, stop_param=1e-8, max_iter=1000):

    fl = func(xl)
    fu = func(xu)

    if fl * fu > 0:
        raise ValueError("Initial bracket does not contain a sign change.")

    #start of the bisection looping, cause we love loops
    for iteration in range(max_iter):
        xm = (xl + xu) / 2
        fm = func(xm)

        if abs(fm) < stop_param or abs(xu - xl) < stop_param:
            return xm, iteration + 1

        if fl * fm < 0:
            xu = xm
            fu = fm
        else:
            xl = xm
            fl = fm

    raise RuntimeError("Bisection method did not converge.")


#Function for finding where a scooter becomes faster than walking
#This uses bisection to solve walk_time - scooter_time = 0
def scooter_walk_break_even(walk_speed_mps, scooter_start_delay=45.0):

    #walking time minus scooter time
    def time_difference(distance_m):
        walk_time = distance_m / walk_speed_mps
        scooter_speed_mps = scooter_speed_from_distance(distance_m) * 1609.344 / 3600
        scooter_time = scooter_start_delay + distance_m / scooter_speed_mps
        return walk_time - scooter_time

    return bisection_root(time_difference, 10, 1000)
