# -*- coding: utf-8 -*-
import sys, os
from os.path import join

sys.path.insert(0, join(os.getcwd(), "PuLP-1.4.7/src"))
print sys.path

from pulp import *
from pulp.odict import OrderedDict

import time, csv

class Data(object):    
    def __init__(self, data=None):
        self._odict = OrderedDict()

        if data:
            for d in data:
                self[d[:-1]] = d[-1]

    def __setitem__(self, key, value):
        if not isinstance(key, tuple):
            self._odict[key] = value

        od = self._odict
        for i in key[:-1]:
            if i not in od:
                od[i] = OrderedDict()
            od = od[i]
        od[key[-1]] = value

    def __getitem__(self, key):
        if not isinstance(key, tuple):
            return self._odict[key]

        od = self._odict
        for i in key[:-1]:
            od = od[i]
        return od[key[-1]]

    def __repr__(self):
        return 'Data(%s)' % repr(self._odict)



def loadProblem(problemname):
    """
    load problem data objects for either exercise or full problem
    """
    
    if problemname == "exercise":
        LOCOS = ['L1', 'L2']
        TRAINS = ['T1', 'T2']
        YARDS = ['Y1', 'Y2', 'Y3', 'Y4']
        SCHEDULE = [
            ('T1', 'Y1', 1, 1),
            ('T1', 'Y2', 2, 1),
            ('T1', 'Y3', 3, 1),
            ('T1', 'Y4', 4, 1),
            ('T2', 'Y4', 1, 1),
            ('T2', 'Y2', 2, 1),
            ('T2', 'Y1', 3, 1),
        ]


        DISTANCES = Data([
            ('Y1', 'Y2', 106),
            ('Y2', 'Y3', 146),
            ('Y3', 'Y4', 16),
            ('Y2', 'Y4', 162),
            ('Y2', 'Y1', 106),
            ('Y3', 'Y2', 146),
            ('Y4', 'Y3', 16),
            ('Y4', 'Y2', 162),
        ])

        ASSIGNMENTS = Data([
            ('L1', 1, 'T1'),
            ('L1', 2, 'T2'),
            ('L1', 3, 'T1'),
            ('L1', 4, 'T2'),
            ('L1', 5, 'T1'),
            ('L1', 6, 'T2'),
            ('L1', 7, 'T1'),
            ('L1', 8, 'T2'),
            ('L1', 9, 'T1'),
            ('L1', 10, 'T2'),
            ('L1', 11, 'T1'),
            ('L1', 12, 'T2'),
            ('L1', 13, 'T1'),
            ('L1', 14, 'T2'),
            ('L2', 1, 'T2'),
            ('L2', 2, 'T1'),
            ('L2', 3, 'T2'),
            ('L2', 4, 'T1'),
            ('L2', 5, 'T2'),
            ('L2', 6, 'T1'),
            ('L2', 7, 'T2'),
            ('L2', 8, 'T1'),
            ('L2', 9, 'T2'),
            ('L2', 10, 'T1'),
            ('L2', 11, 'T2'),
            ('L2', 12, 'T1'),
            ('L2', 13, 'T2'),
            ('L2', 14, 'T1'),
        ])

        FUEL_COST = Data([
            ('Y1', 3.25),
            ('Y2', 3.05), 
            ('Y3', 3.15), 
            ('Y4', 3.15), 
        ])

        STOP_COST = 250
        TRUCK_CAPACITY = 25000
        TIME_HORIZON_WEEKS = 2 
        LOCO_CAPACITY = 4500
        FUEL_RATE = 3.5
        TRUCK_CONTRACT_COST = 4000
        MAX_STOPS = 2

    elif problemname == "full":
        
        LOCOS = ['L'+str(i) for i in range(1, 215)] #214 locos
        TRAINS = ['T'+str(i) for i in range(1, 215)] #214 trains 
        YARDS = ['Y'+str(i) for i in range(1, 74)] #73 yards
       
        
        f = open("schedule.txt", "r")
        SCHEDULE = []
        for l in f.readlines():
            line = l.strip().split('\t')
            SCHEDULE += [tuple(line[:2] + [int(line[2])] + [int(line[3])])]
        f.close()
        

        #TODO: INEFFICIENT WAY OF STORING DUE TO COMMUTATIVITY
        f = open("dist.txt", "r")
        distdata = []
        for l in f.readlines():
            line = l.strip().split('\t')
            distdata += [tuple(line[:2] + [int(line[2])])]
        f.close()
        
        DISTANCES = Data(distdata)


        f = open("assign.txt", "r")
        assigndata = []
        for l in f.readlines():
            line = l.strip().split('\t')
            assigndata += [tuple([line[0]] + [int(line[2])] + [line[1]])]
        f.close()
        
        ASSIGNMENTS = Data(assigndata)

        f = open("fuelcost.txt", "r")
        fuelcost = []
        for l in f.readlines():
            line = l.strip().split('\t')
            fuelcost += [tuple([line[0]] + [float(line[1][1:])])]
        f.close()
        
        FUEL_COST = Data(fuelcost)

        STOP_COST = 250
        TRUCK_CAPACITY = 25000
        TIME_HORIZON_WEEKS = 2 
        LOCO_CAPACITY = 4500
        FUEL_RATE = 3.5
        TRUCK_CONTRACT_COST = 4000
        MAX_STOPS = 2
    else:
        raise "Problem name can be either \"example\" or \"full\""

    return LOCOS, TRAINS, YARDS, SCHEDULE, DISTANCES, ASSIGNMENTS, FUEL_COST, STOP_COST, TRUCK_CAPACITY, TIME_HORIZON_WEEKS, LOCO_CAPACITY, FUEL_RATE, TRUCK_CONTRACT_COST, MAX_STOPS


def computeVariables(problemdata):
    """
    compute useful odicts from problem data for use in modelling MIP
    """

    LOCOS, TRAINS, YARDS, SCHEDULE, DISTANCES, ASSIGNMENTS, FUEL_COST, STOP_COST, TRUCK_CAPACITY, TIME_HORIZON_WEEKS, LOCO_CAPACITY, FUEL_RATE, TRUCK_CONTRACT_COST, MAX_STOPS = problemdata
    
    ####################
    # Computed Data
    #
    # A note about indexing:
    #   days (d) are 1-based, values indexed over days are stored in OrderedDicts
    #   sequence indexes (s) are 0-based, values indexed over these are stored in
    #   normal Python lists.

    # DAYS = 1-based sequence of days
    DAYS = range(1, (7*TIME_HORIZON_WEEKS)+1)

    ###################
    # TRAIN_YARD_SEQ[t] = sequence of yards visited by train t
    # TRAIN_DAY_SEQ[t] = sequence of days for train t, meaning that the sth yard
    # that train t visits is TRAIN_YARD_SEQ[t][s] on day TRAIN_DAY_SEQ[t][s]
    # Days are 1-based.

    TRAIN_YARD_SEQ = OrderedDict()
    TRAIN_DAY_SEQ = OrderedDict()
    for train in TRAINS:
        TRAIN_YARD_SEQ[train] = []
        TRAIN_DAY_SEQ[train] = []

    for train, yard, seq, day in SCHEDULE:
        # we ignore sequence information in SCHEDULE and assume it's
        # sequentially ordered
        TRAIN_YARD_SEQ[train].append(yard)
        TRAIN_DAY_SEQ[train].append(day)

    ###################
    # LOCO_TRAIN_SEQ[j] = sequence of trains for loco j
    LOCO_TRAIN_SEQ = OrderedDict()
    for loco in LOCOS:
        # assumes ASSIGNMENT has data in order, ignores sequence column
        LOCO_TRAIN_SEQ[loco] = ASSIGNMENTS[loco].values()

    ####################
    # The following two correspond to TRAIN_YARD_SEQ and TRAIN_DAY_SEQ
    # LOCO_YARD_SEQ[j] = sequence of yards visited by loco j
    # LOCO_DAY_SEQ[j] = sequence of days for loco j, meaning that the sth yard
    # that train t visits is LOCO_YARD_SEQ[j][s] on day LOCO_DAY_SEQ[t][s]
    # Days are 1-based.
    #
    # LOCO_TRAINS_INDEXES[j] = list of sequence of indexes, each sequence corresponding to
    # a train pulled by loco j, containing the indexes of the yards visited


    LOCO_YARD_SEQ = OrderedDict()
    LOCO_DAY_SEQ = OrderedDict()
    LOCO_TRAINS_INDEXES = OrderedDict()
    for loco in LOCOS:
        LOCO_YARD_SEQ[loco] = []
        LOCO_DAY_SEQ[loco] = []
        LOCO_TRAINS_INDEXES[loco] = []

        day = 0
        i = 0
        for train in LOCO_TRAIN_SEQ[loco]:
            # append all yards except for destination
            train_indexes = []
            for s in range(len(TRAIN_YARD_SEQ[train]) - 1):
                LOCO_YARD_SEQ[loco].append(TRAIN_YARD_SEQ[train][s])
                
                if day + TRAIN_DAY_SEQ[train][s] != 15: #regular rule
                    LOCO_DAY_SEQ[loco].append(day + TRAIN_DAY_SEQ[train][s])
                else: ##EDIT
                    LOCO_DAY_SEQ[loco].append(1)
                
                ## WILL PROBABLY BE OUT OF ORDER
                
                
                train_indexes.append(i)
                i += 1
            LOCO_TRAINS_INDEXES[loco].append(train_indexes)

            # advance day to day of destination yard
            ###EDIT##day += TRAIN_DAY_SEQ[train][-1]
            day += 1
            
            
            if loco == 'L1':
                print day

    print [TRAIN_DAY_SEQ['T2'][s] for s in range(len(TRAIN_YARD_SEQ['T2']) - 1)]
    print LOCO_TRAIN_SEQ['L1']
    print LOCO_DAY_SEQ['L1']

    ####################
    # LOCO_DISTANCE_PREVIOUS[j][s] = distance between s-1 and sth station of loco j
    LOCO_DISTANCE_PREVIOUS = OrderedDict()
    for loco in LOCOS:

        # distance for the first yard wraps around
        data = [
            DISTANCES[ LOCO_YARD_SEQ[loco][-1] ][ LOCO_YARD_SEQ[loco][0] ]
        ]

        # remaining yard
        for s in range(1, len(LOCO_YARD_SEQ[loco])):
            data.append(
                DISTANCES[ LOCO_YARD_SEQ[loco][s-1] ][ LOCO_YARD_SEQ[loco][s] ]
            )
        LOCO_DISTANCE_PREVIOUS[loco] = data


    ####################
    # YARD_VISITS[i][d] = a set of (j, s) tuples, meaning that on
    # day d, loco j visits yard i as the s'th station in it sequence

    YARD_VISITS = OrderedDict()
    for yard in YARDS:
        YARD_VISITS[yard] = OrderedDict()
        for day in DAYS:
            YARD_VISITS[yard][day] = []

    for loco in LOCOS:
        print loco
        for s, (yard, day) in enumerate(zip(LOCO_YARD_SEQ[loco],
                                            LOCO_DAY_SEQ[loco])):
            print s, yard, day ##EDIT
            YARD_VISITS[yard][day].append((loco, s))

    return DAYS, TRAIN_YARD_SEQ, TRAIN_DAY_SEQ, LOCO_TRAIN_SEQ, LOCO_YARD_SEQ, LOCO_DAY_SEQ, LOCO_TRAINS_INDEXES, LOCO_DISTANCE_PREVIOUS, YARD_VISITS
